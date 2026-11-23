import copy
import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/inventor-brief-v2/scripts/render_report.py'
spec = importlib.util.spec_from_file_location('report', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Page(HTMLParser):
    def __init__(self, body):
        super().__init__(); self.ids=[]; self.links=[]; self.assets=[]; self.payload=''; self.collect=False
        self.feed(body)
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if 'href' in a:self.links.append(a['href'])
        if 'src' in a:self.assets.append(a['src'])
        if tag=='script' and a.get('id')=='report-data':self.collect=True
    def handle_endtag(self, tag):
        if tag=='script':self.collect=False
    def handle_data(self, data):
        if self.collect:self.payload+=data


class InventorV2Tests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'examples/inventor-v2/analyzed-input.json').read_text())

    def test_roundtrip_matching_outputs_and_links(self):
        markdown, html=module.Report(self.data).build(); page=Page(html)
        payload=json.loads(page.payload)
        self.assertEqual(payload['report'], self.data)
        self.assertEqual(payload['markdown'], markdown)
        self.assertEqual(len(page.ids),len(set(page.ids)))
        self.assertTrue(all(link[1:] in page.ids for link in page.links if link.startswith('#')))
        for item in self.data['core_concepts']+self.data['landscape']:
            self.assertIn(item['name'],html);self.assertIn(module.md(item['name']),markdown)
        self.assertIn('not a prior-art search',html)
        self.assertIn('AI',markdown)

    def test_inferences_need_explanations_and_supported_facts_need_evidence(self):
        self.data['problem'][0]['evidence']=[]
        with self.assertRaisesRegex(ValueError,'require evidence'):module.Report(self.data)
        self.setUp(); self.data['executive_summary'][1].pop('inference_reason')
        with self.assertRaisesRegex(ValueError,'inference_reason'):module.Report(self.data)

    def test_concept_and_source_references_must_resolve(self):
        for field in ('source', 'concept'):
            d=copy.deepcopy(self.data)
            if field=='source':d['problem'][0]['evidence'][0]['source_id']='absent'
            else:d['related_concepts'][0]['concept_ids']=['absent']
            with self.assertRaisesRegex(ValueError,'[Uu]nknown'):module.Report(d)

    def test_duplicate_ids_rejected(self):
        self.data['questions'][0]['id']=self.data['core_concepts'][0]['id']
        with self.assertRaisesRegex(ValueError,'globally unique'):module.Report(self.data)

    def test_uninspected_sources_cannot_support_landscape(self):
        self.data['sources'][1]['inspected']=False
        with self.assertRaisesRegex(ValueError,'uninspected'):module.Report(self.data)

    def test_public_source_needs_access_date_and_safe_url(self):
        self.data['sources'][1]['url']='javascript:alert(1)'
        with self.assertRaisesRegex(ValueError,'safe HTTP'):module.Report(self.data)
        self.setUp();self.data['sources'][1].pop('accessed_date')
        with self.assertRaisesRegex(ValueError,'accessed_date'):module.Report(self.data)

    def test_inventor_prose_is_inert_in_both_formats(self):
        attack='</script><script>alert(1)</script><img src=x onerror=alert(2)> [click](javascript:bad)'
        self.data['problem'][0]['text']=attack
        self.data['sources'][0]['url']='file:///etc/passwd'
        markdown,html=module.Report(self.data).build();page=Page(html)
        self.assertNotIn('<script>alert',html);self.assertNotIn('<img src=x',html)
        self.assertNotIn('<script>',markdown);self.assertNotIn('[click](javascript:bad)',markdown)
        self.assertNotIn('file:///etc/passwd',page.links)
        self.assertEqual(json.loads(page.payload)['report'],self.data)

    def test_offline_and_print_fallback(self):
        _,html=module.Report(self.data).build()
        self.assertEqual(Page(html).assets,[])
        for term in ('Content-Security-Policy','connect-src','<noscript>','beforeprint','afterprint','@media print'):
            self.assertIn(term,html)
        self.assertNotIn('fetch(',html)

    def test_no_research_is_a_visible_gap(self):
        self.data['landscape']=[];self.data['related_concepts']=[];self.data['research_log']=[]
        self.data['founder_brief']['comparisons']=[]
        self.data['coverage']['research_status']='External research unavailable'
        markdown,html=module.Report(self.data).build()
        self.assertIn('External research unavailable',html)
        self.assertIn('not evidence that no similar work exists',html)
        self.assertIn('No external research recorded',markdown)

    def test_qualifications_and_all_relationships_are_preserved(self):
        markdown,html=module.Report(self.data).build()
        for item in self.data['related_concepts']:
            for question in item['differentiation_questions']:
                self.assertIn(module.md(question),markdown)
        for item in self.data['landscape']:
            self.assertIn(item['source_claims_note'],html)
            self.assertIn(module.md(item['differences_or_unknowns']),markdown)

    def test_cli_emits_three_files_and_protects_input(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/'input.json';source.write_text(json.dumps(self.data));out=base/'output'
            result=subprocess.run([sys.executable,str(SCRIPT),str(source),str(out)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual({p.name for p in out.iterdir()},{'disclosure.md','disclosure.json','disclosure.html'})
            self.assertEqual(json.loads((out/'disclosure.json').read_text()),self.data)
            result=subprocess.run([sys.executable,str(SCRIPT),str(out/'disclosure.json'),str(out)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(json.loads((out/'disclosure.json').read_text()),self.data)

    def test_research_log_cannot_claim_uninspected_sources(self):
        self.data['research_log'][0]['inspected_source_ids']=['absent']
        with self.assertRaisesRegex(ValueError,'known inspected public sources'):module.Report(self.data)

    def test_malformed_statements_fail_with_a_clear_error(self):
        self.data['problem']=['plain string instead of a statement']
        with self.assertRaisesRegex(ValueError,'Record must be an object'):module.Report(self.data)

    def test_brief_precedes_collapsed_complete_analysis(self):
        markdown, html=module.Report(self.data).build()
        self.assertLess(html.index('id="brief-understanding"'), html.index('id="full-analysis"'))
        self.assertIn('<details id="full-analysis" class="full-analysis">', html)
        self.assertIn(module.md('Initial patent-strength view'), markdown)
        self.assertIn('Too early to assess', html)
        self.assertIn('Full disclosure, evidence and sources', markdown)

    def test_brief_rejects_unresolved_links_and_excess_text(self):
        self.data['founder_brief']['question_ids']=['missing']
        with self.assertRaisesRegex(ValueError,'Unknown brief question'):module.Report(self.data)
        self.setUp();self.data['founder_brief']['understanding']['text']='word '*86
        with self.assertRaisesRegex(ValueError,'85 words'):module.Report(self.data)

    def test_non_search_assessment_cannot_establish_novelty(self):
        topic=next(t for t in self.data['patent_assessment']['dimensions'] if t['topic']=='novelty')
        topic['status']='supporting'
        with self.assertRaisesRegex(ValueError,'cannot establish novelty'):module.Report(self.data)

    def test_assessment_updates_require_history_and_prior_id(self):
        a=self.data['patent_assessment'];a['revision']=2
        with self.assertRaisesRegex(ValueError,'previous review ID'):module.Report(self.data)
        a['previous_review_id']='PRIOR-REPORT'
        with self.assertRaisesRegex(ValueError,'retained history'):module.Report(self.data)
        a['history']=[{'review_id':'PRIOR-REPORT','as_of':'2026-11-22','status':'too_early','change_summary':'Original mechanism incomplete; this fixture adds no technical evidence.','evidence':[]}]
        _,html=module.Report(self.data).build()
        self.assertIn('PRIOR-REPORT',html)
        self.assertIn('Revision 2',html)
        self.assertEqual(a['status'],'too_early')

    def test_legacy_report_does_not_infer_a_patent_assessment(self):
        self.data.pop('patent_assessment');self.data.pop('founder_brief')
        _,html=module.Report(self.data).build()
        self.assertIn('Not assessed in this older report',html)

    def test_render_does_not_mutate_analysis(self):
        original=copy.deepcopy(self.data);module.Report(self.data).build();self.assertEqual(self.data,original)


if __name__=='__main__':unittest.main()
