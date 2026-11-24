"""Long-spec intake and sequential coverage regressions; synthetic model responses only."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from local_app.input_text import MAX_INPUT_BYTES, MAX_REQUEST_BYTES, split_text
from local_app.long_text import DIGEST_SCHEMA
from local_app.pipeline import analyze, EXTRACT
from local_app.storage import Store
from local_app.server import App,make_server
from local_fixtures import FakeRuntime


class DigestRuntime(FakeRuntime):
 def __init__(self):super().__init__();self.documents=[];self.extract_prompt=None;self.corrupt=False;self.cancel_on_section=None
 def generate(self,model,prompt,schema,cancel):
  if schema is EXTRACT:self.extract_prompt=prompt
  if set(schema.get('properties',{})) != {'overview','facts','uncertainties'}:return super().generate(model,prompt,schema,cancel)
  payload=json.JSONDecoder().raw_decode(prompt.split('UNTRUSTED EVIDENCE DATA:\n',1)[1])[0]
  if 'section' in payload:
   self.documents.append({**payload['section'],'text': ''.join(x['text'] for x in payload['excerpts'])})
   if self.cancel_on_section==len(self.documents):cancel.set()
  available=[x for x in payload['excerpts'] if x['selectable']]
  selected=available[-1:]
  facts=[{'evidence_id':x['evidence_id'],'meaning':'An inferred mechanism in this local section.'} for x in selected]
  if self.corrupt and facts:facts[0]['evidence_id']='E999'
  return {'overview':'Working local summary of a technical mechanism and its context. '*3,'facts':facts,'uncertainties':'Implementation details and any claim-specific interpretation require review.'}


class LongInputTests(unittest.TestCase):
 def test_unicode_sections_are_lossless_and_bounded(self):
  text=('A paragraph with a valve.\nAnother line: 空気 🌍 café.\n'*1000)+'TAIL'
  chunks=list(split_text(text))
  self.assertEqual(''.join(x[2] for x in chunks),text)
  for start,end,piece in chunks:
   self.assertEqual(text[start:end],piece);self.assertLessEqual(len(piece.encode()),3600)
  self.assertEqual(chunks[-1][1],len(text))

 def test_short_input_uses_original_three_stages(self):
  with tempfile.TemporaryDirectory() as folder:
   s=Store(folder);pid=s.create('Short','A valve closes when the flow threshold is reached.')
   runtime=DigestRuntime();d=analyze(s.get(pid),runtime,'llama3.2:3b',threading.Event(),lambda x:None)
   self.assertEqual(runtime.documents,[]);self.assertNotIn('document_processing',d['generation']);s.close()

 def test_full_document_including_tail_is_submitted_and_original_is_retained(self):
  text=('A fictional specification describes flow sensing, an away-state gate, and a valve.\n'*1400)+'TAILCRITICALMECHANISM'
  self.assertGreater(len(text.encode()),20000)
  with tempfile.TemporaryDirectory() as folder:
   s=Store(folder);pid=s.create('Long specification',text);runtime=DigestRuntime();progress=[]
   d=analyze(s.get(pid),runtime,'llama3.2:3b',threading.Event(),progress.append)
   self.assertEqual(''.join(x['text'] for x in runtime.documents),text)
   self.assertIn('TAILCRITICALMECHANISM',runtime.extract_prompt)
   self.assertEqual(d['input_summary'],text);self.assertEqual(d['sources'][0]['note'],text)
   coverage=d['generation']['document_processing']
   self.assertTrue(coverage['all_sections_submitted']);self.assertGreater(coverage['consolidation_levels'],0)
   self.assertEqual(coverage['sections_processed'],len(runtime.documents))
   self.assertTrue(any('may omit' in x for x in d['coverage']['limitations']))
   self.assertTrue(progress[0].startswith('Reading long text'))
   s.commit(pid,0,d,'llama3.2:3b')
   self.assertEqual(s.get(pid)['revisions'][0]['prompt_version'],d['generation']['prompt_version'])
   s.close()

 def test_unknown_excerpt_choice_aborts_after_bounded_retry(self):
  with tempfile.TemporaryDirectory() as folder:
   s=Store(folder);pid=s.create('Long','Fictional valve specification. '*800);runtime=DigestRuntime();runtime.corrupt=True
   with self.assertRaisesRegex(ValueError,'Reading long text · section 1'):analyze(s.get(pid),runtime,'llama3.2:3b',threading.Event(),lambda x:None)
   self.assertEqual(s.get(pid)['revisions'],[]);s.close()

 def test_cancel_during_document_preparation_leaves_existing_revision(self):
  with tempfile.TemporaryDirectory() as folder:
   s=Store(folder);pid=s.create('Long','Fictional valve specification. '*800)
   s.commit(pid,0,{'prior':'unchanged'},'test');runtime=DigestRuntime();runtime.cancel_on_section=2
   with self.assertRaisesRegex(RuntimeError,'Cancelled'):analyze(s.get(pid),runtime,'llama3.2:3b',threading.Event(),lambda x:None)
   self.assertEqual(s.revision(pid,1),{'prior':'unchanged'});s.close()

 def test_project_limit_is_utf8_bytes_not_characters(self):
  with tempfile.TemporaryDirectory() as folder:
   s=Store(folder)
   with self.assertRaisesRegex(ValueError,'200,000'):s.create('Unicode','🌍'*(MAX_INPUT_BYTES//4+1))
   self.assertEqual(s.list(),[]);s.close()


class IntakeHTTPTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.app=App(self.temp.name,FakeRuntime());self.server=make_server(self.app)
  threading.Thread(target=self.server.serve_forever,daemon=True).start();self.port=self.server.server_port
 def tearDown(self):self.server.shutdown();self.server.server_close();self.app.close();self.temp.cleanup()
 def post(self,body):
  c=http.client.HTTPConnection('127.0.0.1',self.port)
  c.request('POST','/api/projects',json.dumps(body),{'X-Local-Token':self.app.token,'Origin':f'http://127.0.0.1:{self.port}','Content-Type':'application/json'})
  r=c.getresponse();result=r.status,json.loads(r.read());c.close();return result
 def test_patent_sized_request_above_old_wire_limit_is_saved_exactly(self):
  text=('A fictional patent-style paragraph about a valve and controller.\n'*900)
  self.assertGreater(len(json.dumps({'description':text})),20000)
  status,data=self.post({'title':'Spec','description':text})
  self.assertEqual(status,201);self.assertEqual(self.app.store.get(data['id'])['inputs'][0]['text'],text)
 def test_over_project_limit_is_readable_and_saves_nothing(self):
  status,data=self.post({'title':'Too long','description':'x'*(MAX_INPUT_BYTES+1)})
  self.assertEqual(status,400);self.assertIn('200,000',data['error']);self.assertIn('Nothing was saved',data['error'])
  self.assertEqual(self.app.store.list(),[])
 def test_oversized_transport_gets_413_without_uploading_body(self):
  c=http.client.HTTPConnection('127.0.0.1',self.port)
  c.putrequest('POST','/api/projects');c.putheader('X-Local-Token',self.app.token);c.putheader('Origin',f'http://127.0.0.1:{self.port}')
  c.putheader('Content-Type','application/json');c.putheader('Content-Length',str(MAX_REQUEST_BYTES+1));c.endheaders()
  r=c.getresponse();self.assertEqual(r.status,413);self.assertIn('Nothing was saved',json.loads(r.read())['error']);c.close()
 def test_wrong_content_type_is_not_misreported_as_length(self):
  c=http.client.HTTPConnection('127.0.0.1',self.port)
  c.request('POST','/api/projects','{}',{'X-Local-Token':self.app.token,'Origin':f'http://127.0.0.1:{self.port}','Content-Type':'text/plain'})
  r=c.getresponse();self.assertEqual(r.status,415);self.assertIn('requires JSON',json.loads(r.read())['error']);c.close()
