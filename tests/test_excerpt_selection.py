"""Provenance regression: the model selects IDs; only the app copies source quotations."""
import tempfile
import threading
import unittest
from local_app.long_text import leaf_payload, reduction_payload, selection_schema, bind_evidence
from local_app.pipeline import analyze, check_shape
from local_app.storage import Store
from test_long_input import DigestRuntime


def chunk(text,source='S-I-test',start=0):
 return {'source_id':source,'input_number':1,'input_created':'2026-01-01','part':1,'start':start,'end':start+len(text),'text':text}


class ExcerptSelectionTests(unittest.TestCase):
 def test_linebreaks_smart_quotes_and_unicode_are_copied_literally(self):
  original='The “air-flow” path includes\n  a UV source, a non-breaking\u00a0space, and a ﬂow valve.\n' * 8
  payload,lookup=leaf_payload(chunk(original,start=70))
  self.assertEqual(''.join(x['text'] for x in payload['excerpts']),original)
  schema=selection_schema(lookup)
  self.assertEqual(schema['properties']['facts']['items']['properties']['evidence_id']['enum'],list(lookup))
  eid=next(iter(lookup))
  result={'overview':'An interpretation.','uncertainties':'Unspecified geometry.','facts':[{'evidence_id':eid,'meaning':'A paraphrase belongs in interpretation, not in the quotation.'}]}
  bound=bind_evidence(result,lookup)['facts'][0]
  self.assertEqual(bound['quote'],original[bound['source_start']-70:bound['source_end']-70])
  self.assertIn('“air-flow”',bound['quote']);self.assertIn('\n',bound['quote'])

 def test_forged_quotes_or_source_ids_cannot_replace_app_owned_values(self):
  _,lookup=leaf_payload(chunk('An exact source statement describing an air inlet and a valve.'))
  eid=next(iter(lookup))
  model={'overview':'Working inference.','uncertainties':'Testing unknown.','facts':[{'evidence_id':eid,'meaning':'Working interpretation.','quote':'Invented quotation','source_id':'invented'}]}
  # Strict model schema rejects extra properties; binding independently ignores them too.
  with self.assertRaises(ValueError):check_shape(model,selection_schema(lookup))
  bound=bind_evidence(model,lookup)['facts'][0]
  self.assertEqual(bound['source_id'],'S-I-test');self.assertNotEqual(bound['quote'],'Invented quotation')

 def test_unknown_id_is_not_fuzzily_matched(self):
  _,lookup=leaf_payload(chunk('An exact source statement with sufficient detail.'))
  result={'overview':'Inference.','uncertainties':'Unknown.','facts':[{'evidence_id':'E999','meaning':'Unsupported.'}]}
  with self.assertRaisesRegex(ValueError,'unknown excerpt'):bind_evidence(result,lookup)

 def test_consolidation_keeps_quote_offsets_and_distinct_source_identity(self):
  groups=[]
  for source,start in [('S-I-one',20),('S-I-two',90)]:
   _,lookup=leaf_payload(chunk('The same exact phrase occurs in more than one document.',source,start))
   groups.append(bind_evidence({'overview':'Working summary.','uncertainties':'Unverified effect.','facts':[{'evidence_id':'E1','meaning':'An interpretation.'}]},lookup))
  payload,lookup=reduction_payload(groups)
  self.assertEqual(len(lookup),2)
  bound=bind_evidence({'overview':'Combined.','uncertainties':'Differences unknown.','facts':[{'evidence_id':'E2','meaning':'A revised interpretation.'}]},lookup)['facts'][0]
  self.assertEqual(bound['source_id'],'S-I-two');self.assertEqual(bound['source_start'],90)
  self.assertEqual(bound['quote'],groups[1]['facts'][0]['quote'])

 def test_nonselectable_short_text_is_context_not_fabricated_evidence(self):
  payload,lookup=leaf_payload(chunk('yes'))
  self.assertEqual(payload['excerpts'][0]['text'],'yes');self.assertEqual(lookup,{})
  schema=selection_schema(lookup);self.assertEqual(schema['properties']['facts']['maxItems'],0)
  check_shape({'overview':'Short answer depends on context.','uncertainties':'Which question?','facts':[]},schema)

 def test_invalid_choice_recovers_once_without_losing_prior_data(self):
  class RetryRuntime(DigestRuntime):
   failed=False
   def generate(self,model,prompt,schema,cancel):
    result=super().generate(model,prompt,schema,cancel)
    if set(schema.get('properties',{}))=={'overview','facts','uncertainties'} and not self.failed:
     self.failed=True;result['facts'][0]['evidence_id']='E999'
    return result
  with tempfile.TemporaryDirectory() as folder:
   store=Store(folder);text='A fictional source describes an air inlet, treatment region, and containment. '*180
   pid=store.create('Recovery',text);progress=[]
   report=analyze(store.get(pid),RetryRuntime(),'llama3.2:3b',threading.Event(),progress.append)
   self.assertTrue(any('retrying' in x for x in progress))
   self.assertEqual(report['input_summary'],text)
   self.assertEqual(report['generation']['document_processing']['evidence_mode'],'app_owned_excerpt_selection')
   for section in report['generation']['document_processing']['section_ledger']:
    for fact in section['summary']['facts']:
     self.assertEqual(fact['quote'],text[fact['source_start']:fact['source_end']])
   store.close()
