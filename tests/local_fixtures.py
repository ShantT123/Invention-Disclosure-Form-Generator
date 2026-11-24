"""Explicitly synthetic inference responses for integration tests; never used by the application."""
import copy
from local_app.pipeline import EXTRACT, COMPARE

EXTRACTION = {'problem': 'Water may keep flowing while nobody is home.', 'solution': 'Watch continuous flow while away and close a valve after a selected duration.', 'advantage': 'Intended reduction in water released before intervention; untested.', 'advantage_evidence_needed': 'Measure timing, false alarms, and water released.',
 'concepts': [{'name': 'Duration-based flow trigger', 'explanation': 'Compare continuous flow duration with a selected limit.', 'role': 'Determines when intervention is requested.', 'why_core': 'It defines a decision rule.', 'missing': 'Threshold and reset behavior are unknown.'}],
 'questions': [{'question': 'What resets the timer?', 'why': 'This determines the decision rule.', 'provide': 'A state diagram and example timeline.'}]}
ASSESSMENT = {'understanding': 'The proposed water controller watches continuous flow while away and closes a valve after a selected duration. The exact rules and demonstrated advantage remain unknown.', 'status': 'too_early', 'headline': 'The functional idea is clear; implementation and differentiation remain unresolved.', 'signal': 'A physical control sequence is described.', 'gap': 'The exact trigger, reset, and failure rules are unknown.', 'next_evidence': 'A state diagram and example input timelines.', 'change_summary': 'Reconsidered supplied inputs; no validated test or legal conclusion added.',
 'technical_detail': 'Decision rules remain incomplete.', 'differentiation': 'Actual differences are not established.', 'benefit_support': 'No performance result supplied.', 'technical_detail_status': 'incomplete', 'differentiation_status': 'unknown', 'benefit_support_status': 'incomplete'}

class FakeRuntime:
    def __init__(self): self.calls=[];self.running=True;self.fail=False
    def status(self):return {'installed':True,'running':self.running,'models':['llama3.2:3b'],'allowed_models':['llama3.2:3b','qwen3:4b'],'local_only':True}
    def start(self):self.running=True
    def stop(self):self.running=False
    def pull(self,model,progress,cancel):self.running=True;progress('Synthetic download test')
    def generate(self,model,prompt,schema,cancel):
        self.calls.append((prompt,schema))
        if self.fail:raise RuntimeError('Synthetic test failure')
        if schema is EXTRACT:return copy.deepcopy(EXTRACTION)
        if set(schema.get('properties', {})) == {'related', 'landscape'}:return {'related':[{'name':'Flow monitoring','concept_index':0,'shared':'Both observe flow before responding.','differences':'Actual differences are unknown.','question':'What specific rule distinguishes this design?'}],'landscape':[]}
        return copy.deepcopy(ASSESSMENT)
