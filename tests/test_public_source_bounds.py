"""Synthetic public-source bounds and recovery; no actual client data or network."""
import copy
import json
import tempfile
import threading
import unittest
from local_app.pipeline import analyze, comparison_schema, check_shape
from local_app.storage import Store
from local_fixtures import FakeRuntime

ENTRY={'source_index':0,'name':'Widget','organization':'Example','activity':'Source reports flow monitoring.','quote':'Example Widget monitors flow.','connection':'Both monitor flow.','unknowns':'Actual distinctions are unknown.'}
SOURCE={'url':'https://example.com/product','title':'Example Widget','text':'Example Widget monitors flow.','digest':'synthetic','accessed':'2026-01-01'}

class PublicSourceTests(unittest.TestCase):
 def test_schema_bounds_follow_actual_inputs(self):
  for count in range(4):
   schema=comparison_schema(1,count)
   self.assertEqual(schema['properties']['landscape']['maxItems'],3 if count else 0)
   index=schema['properties']['landscape']['items']['properties']['source_index']
   self.assertEqual(index['enum'],list(range(count)) or [0])
   with self.assertRaises(ValueError):check_shape(count,index) if count else check_shape(1,index)
   with self.assertRaises(ValueError):check_shape(1,schema['properties']['related']['items']['properties']['concept_index'])

 def run_case(self, entries, sources=0):
  class Responses(FakeRuntime):
   n=0
   def generate(self,model,prompt,schema,cancel):
    result=super().generate(model,prompt,schema,cancel)
    if 'related' in schema.get('properties',{}):
     result['landscape']=copy.deepcopy(entries[min(self.n,len(entries)-1)]);self.n+=1
    return result
  with tempfile.TemporaryDirectory() as folder:
   store=Store(folder);pid=store.create('Fictional','A fictional flow controller closes a valve based on a duration threshold.')
   for _ in range(sources):store.add_source(pid,SOURCE)
   runtime=Responses();progress=[]
   try:report=analyze(store.get(pid),runtime,'llama3.2:3b',threading.Event(),progress.append)
   finally:store.close()
   return report,runtime,progress

 def test_no_sources_discards_invented_products_before_assessment_or_export(self):
  invented=dict(ENTRY,source_index=99,name='UnsupportedSecretBrand')
  report,runtime,_=self.run_case([[invented]])
  self.assertEqual(report['landscape'],[]);self.assertEqual(runtime.n,1)
  self.assertNotIn('UnsupportedSecretBrand',json.dumps(report))
  self.assertNotIn('UnsupportedSecretBrand',runtime.calls[-1][0])
  self.assertTrue(any('discarded' in x for x in report['coverage']['limitations']))
  self.assertTrue(all(x['kind']!='public' for x in report['sources']))

 def test_out_of_range_source_retries_then_retains_verified_source(self):
  report,runtime,progress=self.run_case([[dict(ENTRY,source_index=1)],[ENTRY]],1)
  self.assertEqual(runtime.n,2);self.assertEqual(len(report['landscape']),1)
  self.assertTrue(any('retrying' in x for x in progress))
  evidence=report['landscape'][0]['evidence'][0]
  self.assertEqual(evidence['excerpt'],SOURCE['text'])
  self.assertTrue(any(x['id']==evidence['source_id'] and x['inspected'] for x in report['sources']))

 def test_bad_quote_can_recover_to_explicit_empty_comparisons(self):
  report,runtime,_=self.run_case([[dict(ENTRY,quote='An invented passage.')],[]],1)
  self.assertEqual(runtime.n,2);self.assertEqual(report['landscape'],[])
  self.assertFalse(next(x for x in report['sources'] if x['kind']=='public')['inspected'])

 def test_persistent_invalid_source_fails_without_claiming_evidence(self):
  with self.assertRaisesRegex(ValueError,'Comparing related concepts.*No report was saved'):
   self.run_case([[dict(ENTRY,source_index=-1)]],1)

 def test_persistent_invented_company_is_not_accepted(self):
  with self.assertRaisesRegex(ValueError,'identity was not found'):
   self.run_case([[dict(ENTRY,organization='Unverified Company')]],1)
