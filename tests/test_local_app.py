import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock

from local_app.storage import Store
from local_app.server import App, make_server, open_interface
from local_app.pipeline import analyze, assemble
from local_app.research import destination, fetch_public, PinnedHTTPS
from local_app.runtime import Runtime
from local_fixtures import FakeRuntime, EXTRACTION, ASSESSMENT

DESCRIPTION='A fictional controller watches water flow while away and closes a valve after a selected time.'

class StoreTests(unittest.TestCase):
 def test_private_store_and_immutable_snapshots(self):
  with tempfile.TemporaryDirectory() as folder:
   s=Store(folder);pid=s.create('Fictional',DESCRIPTION)
   self.assertEqual(Path(folder).stat().st_mode & 0o777,0o700)
   self.assertEqual((Path(folder)/'projects.sqlite3').stat().st_mode & 0o777,0o600)
   s.commit(pid,0,{'saved':'original'},'model')
   with self.assertRaises(ValueError):s.commit(pid,0,{'saved':'overwritten'},'model')
   self.assertEqual(s.revision(pid,1),{'saved':'original'})
   s.add_input(pid,'A clarification.');self.assertEqual(len(s.get(pid)['inputs']),2);s.close()
   s=Store(folder);self.assertEqual(s.revision(pid,1),{'saved':'original'});s.close()

 def test_repository_data_and_oversized_updates_rejected(self):
  with self.assertRaisesRegex(ValueError,'outside'):Store(Path(__file__).resolve().parents[1]/'private-test-data')
  with tempfile.TemporaryDirectory() as folder:
   s=Store(folder);pid=s.create('Fictional',DESCRIPTION)
   with self.assertRaisesRegex(ValueError,'Nothing was saved or truncated'):s.add_input(pid,'x'*200000)
   self.assertEqual(len(s.get(pid)['inputs']),1);s.close()

class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.s=Store(self.temp.name);self.pid=self.s.create('Fictional',DESCRIPTION);self.runtime=FakeRuntime()
 def tearDown(self):self.s.close();self.temp.cleanup()
 def run_analysis(self,previous=None):return analyze(self.s.get(self.pid),self.runtime,'llama3.2:3b',threading.Event(),lambda x:None,previous)
 def test_real_renderer_accepts_locally_assembled_report_and_history(self):
  d=self.run_analysis();self.assertEqual(len(self.runtime.calls),3)
  self.assertEqual(d['landscape'],[])
  for topic in d['patent_assessment']['dimensions']:
   if topic['topic'] in ('novelty','nonobviousness','eligibility'):self.assertEqual(topic['status'],'unknown')
  self.s.commit(self.pid,0,d,'llama3.2:3b');self.s.add_input(self.pid,'The exact timer rule is still undecided.')
  newer=self.run_analysis(d)
  self.assertEqual(newer['patent_assessment']['revision'],2)
  self.assertEqual(newer['patent_assessment']['previous_review_id'],d['review_id'])
  self.assertEqual(newer['patent_assessment']['history'][0]['status'],'too_early')
  self.assertEqual(self.s.revision(self.pid,1),d)
 def test_unsupported_product_quote_prevents_report(self):
  source={'url':'https://example.com/product','title':'Example Widget','text':'P1: Example Widget monitors flow. '*20,'digest':'test','accessed':'2026-01-01'}
  self.s.add_source(self.pid,source)
  real=self.runtime.generate
  def response(model,prompt,schema,cancel):
   d=real(model,prompt,schema,cancel)
   if 'landscape' in d:d['landscape']=[{'source_index':0,'name':'Invented','organization':'Invented','activity':'unverified','quote':'A quote that does not exist','connection':'unknown','unknowns':'unknown'}]
   return d
  self.runtime.generate=response
  with self.assertRaisesRegex(ValueError,'matching source quotation'):self.run_analysis()
  self.assertEqual(self.s.get(self.pid)['revisions'],[])
 def test_cancellation_and_failure_do_not_commit(self):
  event=threading.Event();event.set()
  with self.assertRaisesRegex(RuntimeError,'Cancelled'):analyze(self.s.get(self.pid),self.runtime,'llama3.2:3b',event,lambda x:None)
  self.runtime.fail=True
  with self.assertRaises(RuntimeError):self.run_analysis()
  self.assertEqual(self.s.get(self.pid)['revisions'],[])
 def test_potential_status_needs_technical_and_difference_support(self):
  a=copy.deepcopy(ASSESSMENT);a['status']='early_potential'
  d=assemble(self.s.get(self.pid),EXTRACTION,{'related':[],'landscape':[]},a,None,'llama3.2:3b')
  self.assertEqual(d['patent_assessment']['status'],'too_early')

class ResearchTests(unittest.TestCase):
 def test_rejects_private_destinations_and_signed_links(self):
  for url in ['http://example.com','https://user:pass@example.com/a','https://example.com/a?token=secret','https://example.com:444/a']:
   with self.assertRaises(ValueError):destination(url)
  with patch('local_app.research.socket.getaddrinfo',return_value=[(None,None,None,None,('127.0.0.1',443))]):
   with self.assertRaisesRegex(ValueError,'Private'):destination('https://example.com')
 def test_all_dns_answers_must_be_public(self):
  answers=[(None,None,None,None,(ip,443)) for ip in ['8.8.8.8','192.168.1.1']]
  with patch('local_app.research.socket.getaddrinfo',return_value=answers):
   with self.assertRaises(ValueError):destination('https://example.com')
 def test_redirect_is_revalidated(self):
  response=MagicMock(status=302);response.getheader.return_value='https://127.0.0.1/private'
  connection=MagicMock();connection.getresponse.return_value=response
  with patch('local_app.research.socket.getaddrinfo',side_effect=[[(None,None,None,None,('8.8.8.8',443))],[(None,None,None,None,('127.0.0.1',443))]]),patch('local_app.research.PinnedHTTPS',return_value=connection):
   with self.assertRaisesRegex(ValueError,'Private'):fetch_public('https://example.com')
   self.assertEqual(connection.request.call_count,1)
 def test_connection_pins_validated_address_with_tls_hostname(self):
  connection=PinnedHTTPS('example.com','8.8.8.8')
  with patch('local_app.research.socket.create_connection') as create,patch.object(connection,'_context') as context:
   connection.connect();create.assert_called_once_with(('8.8.8.8',443),15)
   context.wrap_socket.assert_called_once_with(create.return_value,server_hostname='example.com')

class HTTPTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.app=App(self.temp.name,FakeRuntime());self.server=make_server(self.app)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.port=self.server.server_port
 def tearDown(self):self.server.shutdown();self.server.server_close();self.app.close();self.temp.cleanup()
 def request(self,path,body=None,auth=True,origin=True,host=None,cookie=None):
  connection=http.client.HTTPConnection('127.0.0.1',self.port)
  headers={'Content-Type':'application/json','Host':host or f'127.0.0.1:{self.port}'}
  if auth:headers['X-Local-Token']=self.app.token
  if origin:headers['Origin']=f'http://127.0.0.1:{self.port}'
  if cookie:headers['Cookie']=cookie
  connection.request('GET' if body is None else 'POST',path,json.dumps(body) if body is not None else None,headers)
  r=connection.getresponse();status=r.status;data=r.read();response_headers=dict(r.getheaders());connection.close();return status,data,response_headers
 def test_session_origin_host_and_cookie_boundaries(self):
  self.assertEqual(self.request('/api/status',auth=False)[0],401)
  self.assertEqual(self.request('/api/status',host='attacker.example')[0],403)
  self.assertEqual(self.request('/api/projects',{},origin=False)[0],403)
  self.assertEqual(self.request('/api/projects',{},auth=False)[0],403)
  status,_,headers=self.request('/api/status');self.assertEqual(status,200)
  self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie'])
 def test_reports_download_as_json_and_private_frame_requires_cookie(self):
  pid=self.app.store.create('Fictional',DESCRIPTION)
  d=analyze(self.app.store.get(pid),self.app.runtime,'llama3.2:3b',threading.Event(),lambda x:None)
  self.app.store.commit(pid,0,d,'llama3.2:3b')
  status,body,_=self.request(f'/api/reports/{pid}/1?format=json')
  self.assertEqual(status,200);self.assertEqual(json.loads(body),d)
  self.assertEqual(self.request(f'/reports/{pid}/1')[0],401)
  status,body,_=self.request(f'/reports/{pid}/1',cookie='local_report='+self.app.token)
  self.assertEqual(status,200);self.assertIn(b'Full disclosure',body)
 def test_public_search_accepts_only_predefined_queries_and_logs_them(self):
  pid=self.app.store.create('Fictional',DESCRIPTION)
  self.assertEqual(self.request(f'/api/projects/{pid}/search',{'topic':'secret invention detail'})[0],400)
  status,body,_=self.request(f'/api/projects/{pid}/search',{'topic':'UV air treatment'})
  self.assertEqual(status,200);self.assertNotIn('fictional',body.decode().lower())
  self.assertEqual(self.app.store.get(pid)['searches'][0]['query'],'UV air treatment products research')

 def test_evidence_mutation_blocked_while_job_active(self):
  pid=self.app.store.create('Fictional',DESCRIPTION)
  self.app.active='synthetic-job'
  status,_,_=self.request(f'/api/projects/{pid}/inputs',{'text':'new info'})
  self.assertEqual(status,400);self.assertEqual(len(self.app.store.get(pid)['inputs']),1)
  self.app.active=None

class RuntimeTests(unittest.TestCase):
 def test_managed_process_is_loopback_and_cloud_disabled(self):
  with tempfile.TemporaryDirectory() as folder:
   runtime=Runtime(folder);runtime.binary=lambda:'/explicit/local/ollama';runtime.request=lambda *a,**k:{}
   with patch('local_app.runtime.subprocess.Popen') as start,patch('socket.socket'):
    start.return_value.poll.return_value=None
    runtime.start()
    args,kwargs=start.call_args
    self.assertEqual(args[0],['/explicit/local/ollama','serve'])
    self.assertEqual(kwargs['env']['OLLAMA_HOST'],'127.0.0.1:11435')
    self.assertEqual(kwargs['env']['OLLAMA_NO_CLOUD'],'1')
    self.assertEqual(kwargs['env']['OLLAMA_NUM_PARALLEL'],'1')
    self.assertEqual(kwargs['env']['OLLAMA_CONTEXT_LENGTH'],'4096')
    self.assertEqual(kwargs['env']['OLLAMA_MODELS'],str(Path(folder)/'models'))
 def test_streamed_local_api_payload_and_truncation_handling(self):
  with tempfile.TemporaryDirectory() as folder:
   runtime=Runtime(folder);runtime.status=lambda:{'models':['llama3.2:3b']};runtime.request=lambda *a,**k:{}
   response=MagicMock(status=200)
   response.readline.side_effect=[json.dumps({'message':{'content':'{"ok":true}'},'done':True,'done_reason':'stop'}).encode()]
   connection=MagicMock();connection.getresponse.return_value=response
   with patch('local_app.runtime.http.client.HTTPConnection',return_value=connection) as factory:
    result=runtime.generate('llama3.2:3b','Synthetic private test',{'type':'object'},threading.Event())
    self.assertEqual(result,{'ok':True});self.assertEqual(factory.call_args.args,('127.0.0.1',11435))
    body=json.loads(connection.request.call_args.args[2]);self.assertNotIn('think',body)
    self.assertEqual(body['options']['num_ctx'],4096)
    response.readline.side_effect=[json.dumps({'done':True,'done_reason':'length'}).encode()]
    with self.assertRaisesRegex(RuntimeError,'reached its limit'):runtime.generate('llama3.2:3b','Synthetic',{},threading.Event())
 def test_cloud_model_metadata_is_rejected_before_chat(self):
  with tempfile.TemporaryDirectory() as folder:
   runtime=Runtime(folder);runtime.status=lambda:{'models':['llama3.2:3b']};runtime.request=lambda *a,**k:{'remote_host':'https://example.com'}
   with patch('local_app.runtime.http.client.HTTPConnection') as connection:
    with self.assertRaisesRegex(RuntimeError,'Cloud models'):runtime.generate('llama3.2:3b','Synthetic',{},threading.Event())
    connection.assert_not_called()


class LauncherTests(unittest.TestCase):
 def test_mac_launch_explicitly_selects_chrome_without_shell(self):
  with patch('local_app.server.sys.platform','darwin'),patch('local_app.server.subprocess.run') as run,patch('local_app.server.webbrowser.open') as fallback:
   open_interface('http://127.0.0.1:12345/#session=synthetic')
   self.assertEqual(run.call_args.args[0][:3],['open','-a','Google Chrome'])
   self.assertNotIn('shell',run.call_args.kwargs)
   fallback.assert_not_called()
