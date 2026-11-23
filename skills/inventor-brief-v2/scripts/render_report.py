#!/usr/bin/env python3
"""Validate an analyzed Inventor Brief v2.0 and render matching JSON, Markdown, and offline HTML.
The host assistant supplies analysis and research. This script makes no network or model calls.
"""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
BASIS = {'inventor_stated', 'ai_inferred', 'externally_supported', 'unknown'}
BASIS_LABELS = {'inventor_stated': 'Inventor’s description', 'ai_inferred': 'AI interpretation — please confirm', 'externally_supported': 'Public source', 'unknown': 'Unknown'}
LEVELS = {'high', 'medium', 'low', 'unresolved'}
COLLECTIONS = ('executive_summary', 'problem', 'solution', 'advantages', 'core_concepts',
               'related_concepts', 'landscape', 'questions', 'sources', 'research_log')
SECTIONS = [('summary', 'Executive summary'), ('disclosure', 'Problem, solution & advantage'),
            ('concepts', 'Core technical concepts'), ('related', 'Clarify & differentiate'),
            ('landscape', 'Products & innovators'), ('questions', 'Founder questions'), ('sources', 'Sources & scope')]
PATENT_STATUSES = {'too_early': 'Too early to assess', 'early_potential': 'Early potential — unverified', 'concerns': 'Material questions to resolve'}
DIMENSIONS = {'technical_detail', 'differentiation', 'benefit_support', 'novelty', 'nonobviousness', 'eligibility'}
NOTICE = 'An invention-development brief for discussion with patent counsel. This is not a prior-art search or a finding of novelty, patentability, infringement, or freedom to operate.'


def safe_url(value):
    if not isinstance(value, str) or re.search(r'[\s<>"\\]', value):
        return None
    try:
        parts = urlsplit(value)
        return value if parts.scheme in ('http', 'https') and parts.hostname and not parts.username else None
    except ValueError:
        return None


def validate(d):
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    def text(obj, key):
        require(isinstance(obj, dict), 'Record must be an object')
        require(isinstance(obj.get(key), str) and bool(obj[key].strip()), key + ' requires nonempty text')
    require(isinstance(d, dict), 'Report must be an object')
    require(d.get('schema_version') == '1', 'schema_version must be "1"')
    for key in ('review_id', 'title', 'as_of', 'input_summary'):
        text(d, key)
    for key in COLLECTIONS:
        require(isinstance(d.get(key), list), key + ' must be an array')
    require(isinstance(d.get('coverage'), dict), 'coverage must be an object')
    for key in ('materials_reviewed', 'unreadable_materials', 'limitations'):
        require(isinstance(d['coverage'].get(key), list), 'coverage.' + key + ' must be an array')
    text(d['coverage'], 'research_status')
    require(bool(d['executive_summary']), 'Executive summary cannot be empty')
    for key in ('problem', 'solution', 'advantages'):
        require(bool(d[key]), key + ' needs a statement; explicitly record unknowns')
    identifiers = []
    for key in ('core_concepts', 'related_concepts', 'landscape', 'questions', 'sources'):
        for item in d[key]:
            require(isinstance(item, dict), key + ' entries must be objects')
            text(item, 'id')
            identifiers.append(item['id'])
    require(len(identifiers) == len(set(identifiers)), 'All record IDs must be globally unique')
    sources = {s['id']: s for s in d['sources']}
    concepts = {c['id'] for c in d['core_concepts']}
    for s in d['sources']:
        for key in ('title', 'kind', 'locator'):
            text(s, key)
        require(s['kind'] in ('inventor', 'public'), 'Unknown source kind')
        if s['kind'] == 'public':
            require(bool(safe_url(s.get('url'))), 'Public sources require a safe HTTP(S) URL')
            require(isinstance(s.get('inspected'), bool), 'Public inspection status must be explicit')
            if s['inspected']:
                text(s, 'accessed_date')
    def evidence(item, needed=False):
        refs = item.get('evidence')
        require(isinstance(refs, list), 'Every finding requires an evidence array')
        require(not needed or bool(refs), 'Supported facts require evidence')
        for ref in refs:
            require(isinstance(ref, dict) and ref.get('source_id') in sources, 'Evidence has an unknown source ID')
            text(ref, 'locator')
            if sources[ref['source_id']]['kind'] == 'public':
                require(sources[ref['source_id']]['inspected'], 'An uninspected public source is a lead, not supporting evidence')
    def assessment(item):
        a = item.get('assessment')
        require(isinstance(a, dict) and a.get('level') in LEVELS, 'Assessment requires qualitative confidence')
        text(a, 'reason')
        text(a, 'missing_or_uncertain')
    def concept_refs(item):
        require(isinstance(item.get('concept_ids'), list), 'concept_ids must be an array')
        require(all(cid in concepts for cid in item['concept_ids']), 'Unknown core concept reference')
    for key in ('executive_summary', 'problem', 'solution', 'advantages'):
        for item in d[key]:
            text(item, 'text')
            require(item.get('basis') in BASIS, 'Statement basis must be explicit')
            evidence(item, item['basis'] in ('inventor_stated', 'externally_supported'))
            if item['basis'] == 'ai_inferred':
                text(item, 'inference_reason')
    for c in d['core_concepts']:
        for key in ('name', 'plain_english', 'role_in_solution', 'why_core', 'basis'):
            text(c, key)
        require(c['basis'] in BASIS, 'Invalid concept basis')
        require(isinstance(c.get('founder_confirmation_needed'), bool), 'Founder confirmation must be explicit')
        evidence(c, c['basis'] in ('inventor_stated', 'externally_supported'))
        assessment(c)
    for c in d['related_concepts']:
        for key in ('name', 'shared_idea', 'important_differences', 'difference_status'):
            text(c, key)
        require(c['difference_status'] in BASIS, 'Difference status must be explicit')
        concept_refs(c)
        require(bool(c['concept_ids']), 'Related concepts need an invention concept connection')
        require(isinstance(c.get('differentiation_questions'), list) and bool(c['differentiation_questions']), 'Related concepts need differentiation questions')
        evidence(c, c['difference_status'] in ('inventor_stated', 'externally_supported'))
        assessment(c)
    for entry in d['landscape']:
        for key in ('name', 'entity_type', 'organization', 'what_they_do', 'connection', 'differences_or_unknowns', 'source_claims_note', 'availability_status'):
            text(entry, key)
        require(entry['entity_type'] in ('product', 'company', 'research_group', 'project', 'standards_body'), 'Invalid landscape entity type')
        concept_refs(entry)
        require(bool(entry['concept_ids']), 'Landscape entries need a concrete concept connection')
        evidence(entry, True)
        require(any(sources[r['source_id']]['kind'] == 'public' for r in entry['evidence']), 'Landscape activity requires inspected public evidence')
        assessment(entry)
    for log in d['research_log']:
        for key in ('query', 'purpose', 'date', 'tool', 'status', 'gaps'):
            text(log, key)
        require(isinstance(log.get('inspected_source_ids'), list), 'Research log requires inspected_source_ids')
        for sid in log['inspected_source_ids']:
            require(sid in sources and sources[sid]['kind'] == 'public' and sources[sid]['inspected'], 'Research log may only list known inspected public sources')
    for q in d['questions']:
        for key in ('question', 'why_it_matters', 'suggested_evidence'):
            text(q, key)
        require(q.get('priority') in ('high', 'medium', 'low'), 'Question needs priority')
        concept_refs(q)
    if 'founder_brief' in d:
        brief = d['founder_brief']
        require(isinstance(brief, dict), 'founder_brief must be an object')
        understanding = brief.get('understanding')
        text(understanding, 'text')
        require(len(understanding['text'].split()) <= 85, 'Brief understanding must be at most 85 words')
        require(understanding.get('basis') in BASIS, 'Brief understanding needs an explicit basis')
        evidence(understanding, understanding['basis'] in ('inventor_stated', 'externally_supported'))
        if understanding['basis'] == 'ai_inferred':
            text(understanding, 'inference_reason')
        comparisons = brief.get('comparisons')
        require(isinstance(comparisons, list) and len(comparisons) <= 3, 'Brief allows at most three comparisons')
        targets = {c['id'] for k in ('related_concepts', 'landscape') for c in d[k]}
        require(len({c.get('record_id') for c in comparisons}) == len(comparisons), 'Brief comparisons must be distinct')
        for comparison in comparisons:
            require(comparison.get('record_id') in targets, 'Unknown brief comparison')
            text(comparison, 'summary')
            require(len(comparison['summary'].split()) <= 35, 'Comparison summary must be at most 35 words')
        qids = brief.get('question_ids')
        require(isinstance(qids, list) and len(qids) <= 3 and len(set(qids)) == len(qids), 'Brief allows up to three distinct questions')
        require(all(q in {x['id'] for x in d['questions']} for q in qids), 'Unknown brief question')
    if 'patent_assessment' in d:
        a = d['patent_assessment']
        require(isinstance(a, dict), 'patent_assessment must be an object')
        require(a.get('status') in PATENT_STATUSES, 'Invalid preliminary patent status')
        require(type(a.get('revision')) is int and a['revision'] > 0, 'Patent assessment revision must be a positive integer')
        require(a.get('previous_review_id') is None or isinstance(a['previous_review_id'], str), 'previous_review_id must be text or null')
        if a['revision'] > 1:
            require(bool(a.get('previous_review_id')), 'Updated assessment needs a previous review ID')
        for key in ('headline', 'positive_signal', 'main_gap', 'next_evidence', 'scope_limit'):
            text(a, key)
        for key in ('headline', 'positive_signal', 'main_gap', 'next_evidence'):
            require(len(a[key].split()) <= 35, key + ' must be at most 35 words')
        assessment(a)
        require(isinstance(a.get('changes_since_previous'), list), 'Assessment needs changes_since_previous')
        require(isinstance(a.get('history'), list), 'Assessment needs history')
        if a['revision'] > 1:
            require(bool(a['changes_since_previous']) and bool(a['history']), 'Updates need changes and retained history')
        if a['revision'] > 1:
            require(a['previous_review_id'] != d['review_id'] and a['previous_review_id'] in {old.get('review_id') for old in a['history']}, 'Previous review must resolve in retained history and differ from current review')
        topics = a.get('dimensions')
        require(isinstance(topics, list) and {x.get('topic') for x in topics} == DIMENSIONS and len(topics) == len(DIMENSIONS), 'Assessment must cover all six dimensions once')
        for topic in topics:
            require(topic.get('status') in ('supporting', 'incomplete', 'concern', 'unknown'), 'Invalid assessment dimension status')
            if topic['topic'] in ('novelty', 'nonobviousness'):
                require(topic['status'] in ('unknown', 'concern'), 'Limited orientation cannot establish novelty or nonobviousness')
            text(topic, 'reason')
            evidence(topic)
        for old in a['history']:
            for key in ('review_id', 'as_of', 'change_summary'):
                text(old, key)
            require(old.get('status') in PATENT_STATUSES, 'History requires a valid prior status')
            evidence(old)
    return d


def esc(value):
    return html.escape(str(value), quote=True)


def label_topic(value):
    return {'technical_detail': 'Technical detail', 'differentiation': 'Distinctive mechanism', 'benefit_support': 'Evidence for advantages', 'novelty': 'Novelty', 'nonobviousness': 'Nonobviousness', 'eligibility': 'Eligibility considerations'}.get(value, value)


def md(value):
    # All source prose stays literal in Markdown, including raw HTML and link syntax.
    value = html.escape(str(value), quote=False)
    return re.sub(r'([\\`*_{}\[\]()#+.!|>-])', r'\\\1', value).replace('\n', ' ')


class Report:
    def __init__(self, data):
        self.d = validate(data)
        records = [r for key in ('core_concepts', 'related_concepts', 'landscape', 'questions', 'sources') for r in data[key]]
        self.anchors = {r['id']: 'item-' + str(i) for i, r in enumerate(records)}
        self.source_map = {s['id']: s for s in data['sources']}
        self.concepts = {c['id']: c['name'] for c in data['core_concepts']}
        self.h, self.m = [], []

    def p(self, text):
        self.h.append('<p>' + esc(text) + '</p>')
        self.m.append(md(text) + '\n')

    def field(self, label, text):
        self.h.append('<p><span class="label">' + esc(label) + ':</span> ' + esc(text) + '</p>')
        self.m.append('**' + md(label) + ':** ' + md(text) + '\n')

    def section(self, key, title):
        self.h.append('<section id="' + key + '"><h2>' + esc(title) + '</h2>')
        self.m.append('\n## ' + md(title) + '\n')

    def article(self, item, heading, searchable=False):
        attr = ' data-search="' + esc(json.dumps(item).lower()) + '"' if searchable else ''
        self.h.append('<article class="card' + (' searchable' if searchable else '') + '" id="' + self.anchors[item['id']] + '"' + attr + '><h3>' + esc(heading) + '</h3>')
        self.m.append('\n<a id="' + self.anchors[item['id']] + '"></a>\n\n### ' + md(heading) + '\n')

    def refs(self, item):
        if not item.get('evidence'):
            return
        h, m = [], []
        for ref in item['evidence']:
            sid = ref['source_id']; s = self.source_map[sid]
            label = sid + ' · ' + ref['locator']
            h.append('<a href="#' + self.anchors[sid] + '" title="' + esc(s['title']) + '">' + esc(label) + '</a>')
            m.append('[' + md(label) + '](#' + self.anchors[sid] + ')')
            if safe_url(s.get('url')):
                h.append('<a href="' + esc(s['url']) + '" target="_blank" rel="noopener noreferrer">Open source</a>')
                m.append('[Open source](<' + s['url'] + '>)')
        self.h.append('<p class="citations">Sources: ' + ' · '.join(h) + '</p>')
        self.m.append('Sources: ' + ' · '.join(m) + '\n')

    def statement(self, item):
        self.p(item['text'])
        self.field('Basis', BASIS_LABELS[item['basis']])
        if item.get('inference_reason'):
            self.field('Why this interpretation', item['inference_reason'])
        self.refs(item)

    def assessment(self, item):
        a = item['assessment']
        self.field('Confidence in this interpretation', a['level'] + ' — ' + a['reason'])
        self.field('Still uncertain', a['missing_or_uncertain'])
        self.refs(item)

    def names(self, item):
        return '; '.join(self.concepts[cid] for cid in item['concept_ids']) or 'General disclosure'

    def brief(self):
        d = self.d
        saved_h, saved_m = self.h, self.m
        self.h, self.m = [], []
        brief = d.get('founder_brief') or {
            'understanding': d['executive_summary'][0],
            'comparisons': [{'record_id': c['id'], 'summary': c['connection']} for c in d['landscape'][:3]],
            'question_ids': [q['id'] for q in sorted(d['questions'], key=lambda x: ('high', 'medium', 'low').index(x['priority']))[:3]]}
        self.section('brief-understanding', 'What the AI understands')
        self.p(brief['understanding']['text'])
        self.h.append('<p class="micro">AI working understanding · Please confirm or correct</p>')
        self.m.append('AI working understanding — please confirm or correct.\n')
        self.h.append('<details><summary>Why this interpretation?</summary>')
        self.m.append('\n<details><summary>Interpretation and evidence</summary>\n')
        self.field('Basis', BASIS_LABELS[brief['understanding']['basis']])
        if brief['understanding'].get('inference_reason'):
            self.p(brief['understanding']['inference_reason'])
        self.refs(brief['understanding']); self.h.append('</details></section>'); self.m.append('\n</details>\n')
        self.section('brief-similar', 'Similar ideas & innovators')
        targets = {c['id']: c for key in ('related_concepts', 'landscape') for c in d[key]}
        self.h.append('<div class="brief-grid">')
        for comparison in brief['comparisons']:
            c = targets[comparison['record_id']]
            name = c['name'] + (' · ' + c['organization'] if 'organization' in c else '')
            self.h.append('<div class="mini-card"><h3>' + esc(name) + '</h3>')
            self.m.append('### ' + md(name) + '\n')
            self.p(comparison['summary'])
            self.h.append('<a href="#' + self.anchors[c['id']] + '">Compare &amp; see sources</a></div>')
            self.m.append('[Comparison and sources](#' + self.anchors[c['id']] + ')\n')
        self.h.append('</div>')
        if not brief['comparisons']:
            self.p('No supported comparison yet; this is a research gap, not evidence of novelty.')
        self.h.append('</section>')
        self.section('brief-questions', 'What would help next')
        for i, qid in enumerate(brief['question_ids'], 1):
            q = next(q for q in d['questions'] if q['id'] == qid)
            self.h.append('<div class="next-step"><h3>' + str(i) + '. ' + esc(q['question']) + '</h3>')
            self.m.append('### ' + str(i) + '. ' + md(q['question']) + '\n')
            self.field('Send', q['suggested_evidence'])
            self.h.append('</div>')
        if not brief['question_ids']:
            self.p('No next questions recorded; review the evidence gaps with the founder.')
        self.h.append('</section>')
        self.section('brief-strength', 'Initial patent-strength view')
        a = d.get('patent_assessment')
        if a:
            self.h.append('<p class="strength-status">' + esc(PATENT_STATUSES[a['status']]) + '</p>')
            self.m.append('**' + md(PATENT_STATUSES[a['status']]) + '**\n')
            self.p(a['headline'])
            self.field('Promising signal', a['positive_signal'])
            self.field('Main gap', a['main_gap'])
            self.field('What could change the view', a['next_evidence'])
            self.h.append('<p class="micro">Revision ' + str(a['revision']) + ' · ' + esc(d['as_of']) + ' · Provisional, based on supplied information and limited public orientation</p><details><summary>Assessment basis &amp; update history</summary>')
            self.m.append('\n<details><summary>Assessment basis and update history</summary>\n')
            for dimension in a['dimensions']:
                self.field(label_topic(dimension['topic']), dimension['status'] + ' — ' + dimension['reason'])
                self.refs(dimension)
            self.assessment(a)
            self.field('Scope', a['scope_limit'])
            self.field('Revision', str(a['revision']))
            self.field('Previous review', a.get('previous_review_id') or 'Initial assessment')
            for change in a['changes_since_previous']:
                self.field('Change', change)
            for old in a['history']:
                self.field('Prior review', old['review_id'] + ' · ' + old['as_of'] + ' · ' + PATENT_STATUSES[old['status']])
                self.field('Prior assessment context', old['change_summary']); self.refs(old)
            self.h.append('</details>'); self.m.append('\n</details>\n')
        else:
            self.p('Not assessed in this older report. More technical detail and counsel review are needed; no patentability inference is generated by the renderer.')
        self.h.append('</section>')
        result_h, result_m = ''.join(self.h), '\n'.join(self.m)
        self.h, self.m = saved_h, saved_m
        return result_h, result_m

    def build(self):
        d = self.d
        self.m = ['# ' + md(d['title']) + '\n', md(d['review_id'] + ' · As of ' + d['as_of'] + ' · Inventor Brief v2.0') + '\n', md(NOTICE) + '\n']
        self.section('summary', 'Executive summary')
        for item in d['executive_summary']:
            self.statement(item)
        self.h.append('</section>' + '<div class="filter" hidden><label for="search">Find a concept, product, or innovator</label><input id="search" type="search" placeholder="Search technical concepts and public examples"><button id="reset">Reset</button><p id="matches" aria-live="polite"></p></div>')
        self.section('disclosure', 'Problem, solution & advantage')
        self.field('Your description, condensed', d['input_summary'])
        for key, title in [('problem', 'Problem'), ('solution', 'Solution'), ('advantages', 'Intended advantages')]:
            self.h.append('<div class="card"><h3>' + title + '</h3>'); self.m.append('\n### ' + title + '\n')
            for item in d[key]:
                self.statement(item)
                if item.get('evidence_needed'):
                    self.field('Evidence needed', item['evidence_needed'])
            self.h.append('</div>')
        self.h.append('</section>')
        self.section('concepts', 'Core technical concepts')
        self.p('These are the concepts the AI believes make the solution work. Confirm or correct them; a core concept is not automatically novel or patentable.')
        for c in d['core_concepts']:
            self.article(c, 'Concept: ' + c['name'], True)
            for key, title in [('plain_english', 'In plain English'), ('role_in_solution', 'Role in your solution'), ('why_core', 'Why it may be core'), ('basis', 'Basis')]:
                self.field(title, BASIS_LABELS[c[key]] if key == 'basis' else c[key])
            self.field('Founder confirmation needed', 'Yes' if c['founder_confirmation_needed'] else 'No additional confirmation recorded')
            self.assessment(c); self.h.append('</article>')
        if not d['core_concepts']:
            self.p('No core technical concept can yet be identified. Describe how the solution works, step by step.')
        self.h.append('</section>')
        self.section('related', 'Clarify & differentiate')
        self.p('Explain the concrete implementation differences you actually have. These questions help develop the disclosure for counsel; they do not establish that a difference is new, nonobvious, or legally sufficient.')
        for c in d['related_concepts']:
            self.article(c, 'Related concept: ' + c['name'], True)
            self.field('Your invention concept', self.names(c))
            self.field('How related', c['shared_idea'])
            self.field('Differences or open distinctions', c['important_differences'])
            self.field('Status of the comparison', BASIS_LABELS[c['difference_status']])
            for question in c['differentiation_questions']:
                self.field('Question to develop', question)
            self.assessment(c); self.h.append('</article>')
        if not d['related_concepts']:
            self.p('No supported related concepts recorded. See the research limits below.')
        self.h.append('</section>')
        self.section('landscape', 'Products & innovators')
        self.p('Selected public examples for technical orientation, not a complete market map or prior-art search. Similarity does not establish infringement or lack of patentability.')
        for c in d['landscape']:
            self.article(c, c['name'] + ' · ' + c['organization'], True)
            for key, title in [('entity_type', 'Type'), ('what_they_do', 'What the source reports'), ('connection', 'Why relevant'), ('differences_or_unknowns', 'Differences to investigate'), ('source_claims_note', 'Evidence limits'), ('availability_status', 'Availability / timing')]:
                self.field(title, c[key])
            self.field('Related invention concepts', self.names(c)); self.assessment(c); self.h.append('</article>')
        if not d['landscape']:
            self.p('No supported products or innovators recorded. This is a research gap, not evidence that no similar work exists.')
        self.h.append('</section>')
        self.section('questions', 'Founder questions')
        for q in sorted(d['questions'], key=lambda x: ('high', 'medium', 'low').index(x['priority'])):
            self.article(q, q['question'])
            self.field('Priority', q['priority']); self.field('Why it matters', q['why_it_matters'])
            self.field('What to provide', q['suggested_evidence']); self.field('Concepts', self.names(q)); self.h.append('</article>')
        if not d['questions']:
            self.p('No follow-up questions recorded; confirm that this reflects adequate information rather than omitted review.')
        self.h.append('</section>')
        self.section('sources', 'Sources & scope')
        self.field('Research status', d['coverage']['research_status'])
        for key, title in [('materials_reviewed', 'Reviewed'), ('unreadable_materials', 'Not readable / not reviewed'), ('limitations', 'Limitation')]:
            for entry in d['coverage'][key]:
                self.field(title, entry)
        for s in d['sources']:
            self.article(s, s['id'] + ' · ' + s['title'])
            self.field('Type', s['kind']); self.field('Locator', s['locator'])
            if s['kind'] == 'public':
                self.field('Inspected', 'Yes' if s['inspected'] else 'No; research lead only')
                if s.get('accessed_date'):
                    self.field('Accessed', s['accessed_date'])
            if safe_url(s.get('url')):
                self.h.append('<p><a href="' + esc(s['url']) + '" target="_blank" rel="noopener noreferrer">Open ' + esc(s['title']) + '</a></p>')
                self.m.append('[Open source](<' + s['url'] + '>)\n')
            for key, title in [('publication_date', 'Published'), ('note', 'Note')]:
                if s.get(key):
                    self.field(title, s[key])
            self.h.append('</article>')
        self.h.append('<details><summary>Research log</summary>')
        self.m.append('\n### Research log\n')
        if not d['research_log']:
            self.p('No external research recorded.')
        for log in d['research_log']:
            for key, value in log.items():
                self.field(key.replace('_', ' ').capitalize(), json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value)
        self.h.append('</details></section>')
        brief_h, brief_m = self.brief()
        full_h = '<details id="full-analysis" class="full-analysis"><summary>Full disclosure, evidence &amp; sources</summary>' + ''.join(self.h) + '</details>'
        self.h = [brief_h, full_h]
        header_m = '\n'.join(self.m[:3])
        markdown = header_m + '\n' + brief_m + '\n<details><summary>Full disclosure, evidence and sources</summary>\n\n' + '\n'.join(self.m[3:]) + '\n</details>\n'
        payload = json.dumps({'report': d, 'markdown': markdown}, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
        css = (ROOT / 'dashboard.css').read_text()
        js = (ROOT / 'dashboard.js').read_text()
        digest = base64.b64encode(hashlib.sha256(js.encode()).digest()).decode()
        policy = "default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-" + digest + "'; connect-src 'none'; base-uri 'none'; form-action 'none'"
        nav = ''.join('<a href="#' + key + '">' + title + '</a>' for key, title in [('brief-understanding', 'The idea'), ('brief-similar', 'Similar ideas'), ('brief-questions', 'What to send next'), ('brief-strength', 'Patent-strength view'), ('full-analysis', 'Full disclosure')])
        output = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="' + esc(policy) + '"><title>' + esc(d['title']) + '</title><style>' + css + '</style></head><body><a class="skip" href="#main">Skip to report</a><aside><p class="brand">INVENTION<br><small>Inventor brief · v2.0</small></p><nav aria-label="Report sections">' + nav + '</nav></aside><main id="main"><header><p class="eyebrow">Inventor Brief v2.0</p><h1>' + esc(d['title']) + '</h1><p>' + esc(d['review_id'] + ' · As of ' + d['as_of']) + '</p><div class="actions" hidden><button id="download-md">Download Markdown</button><button id="download-json">Download JSON</button><button id="print">Print / save PDF</button></div></header><p class="notice">' + 'Founder disclosure draft · Not a prior-art search or patentability opinion.' + '</p><noscript><p>All content is readable below. Downloads, search, and print controls require JavaScript; companion Markdown and JSON files are included separately.</p></noscript>' + ''.join(self.h) + '<footer>' + NOTICE + '</footer></main><script id="report-data" type="application/json">' + payload + '</script><script>' + js + '</script></body></html>'
        return markdown, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_json', type=Path)
    parser.add_argument('output_dir', type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input_json.read_text(encoding='utf-8'))
        markdown, html_report = Report(data).build()
        paths = [args.output_dir / ('disclosure.' + ext) for ext in ('json', 'md', 'html')]
        if args.input_json.resolve() in [p.resolve() for p in paths]:
            raise ValueError('Input cannot be an output path; choose a separate output directory')
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for path, content in zip(paths, [json.dumps(data, indent=2, ensure_ascii=False) + '\n', markdown, html_report]):
            path.write_text(content, encoding='utf-8')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, 'Cannot render report: ' + str(exc) + '\n')
    print('Wrote disclosure.md, disclosure.json, disclosure.html to ' + str(args.output_dir))


if __name__ == '__main__':
    main()
