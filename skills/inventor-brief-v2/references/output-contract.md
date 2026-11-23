# Founder disclosure JSON contract — version 1

The JSON is the shared source for matching Markdown and HTML. `null` means unknown, never a guessed value. Empty collections mean no supported items recorded; explain substantive gaps in `coverage`. Preserve additional supplied fields in the JSON download. The renderer displays the fields below; put material qualifications in these fields so they remain visible in both readable formats.

Required envelope: `schema_version` ("1"), `review_id`, `title`, `as_of` (actual review date), `input_summary`, `executive_summary`, `problem`, `solution`, `advantages`, `core_concepts`, `related_concepts`, `landscape`, `questions`, `sources`, `research_log`, `coverage`.

All record IDs must be globally unique. Recommended prefixes: C- for core concepts, R- for related concepts, L- for landscape, Q- for questions, and S- for sources. References must resolve. Confidence is high/medium/low/unresolved with evidence-based reasons; never a patentability probability.

## Statements

`executive_summary`, `problem`, `solution`, and `advantages` are arrays of statements, each with:

- `text`: readable plain text; split different evidence bases into separate statements.
- `basis`: `inventor_stated`, `ai_inferred`, `externally_supported`, or `unknown`.
- `evidence`: an array of `{source_id, locator}` references. Inventor-stated and externally supported facts require supporting evidence. Unknowns and inferences may have empty evidence, but record the scope limitation. Include a short `excerpt` or `supports` field when useful for traceability; these remain in JSON.
- `inference_reason`: required for AI-inferred statements; explain the interpretation without hiding uncertainty.
- `evidence_needed`: recommended for advantages, describing how the intended benefit could be evaluated. A test plan is a recommendation, not a result.

Problem, solution, and advantages must have at least one statement; explicitly record unknowns instead of filling them in. The executive summary must be nonempty.

## Core concepts

`core_concepts`: array of `{id, name, plain_english, role_in_solution, why_core, basis, evidence, assessment, founder_confirmation_needed}`. Basis uses the statement vocabulary. `assessment` is `{level, reason, missing_or_uncertain}`; confirmation-needed is boolean, never assumed false because the model is confident. The reason and why-core fields explain the interpretation. Keep concepts narrow enough to compare and broad enough to express a mechanism.

## Related concepts and differentiation

`related_concepts`: array of `{id, concept_ids, name, shared_idea, important_differences, difference_status, differentiation_questions, evidence, assessment}`. `concept_ids` is a nonempty array of core concept IDs. `difference_status` uses the basis vocabulary. `differentiation_questions` is a nonempty list of specific founder-answerable questions, not asserted novelty. `important_differences` includes known distinctions and explicit unknowns; a source page's silence is not a proven absence. Put uncertainty reasons in `assessment`. A core concept can connect to many related concepts and vice versa. Similar outcome does not establish technical equivalence or legal analogous-art status.

## Products and innovators

`landscape`: array of `{id, name, entity_type, organization, concept_ids, what_they_do, connection, differences_or_unknowns, source_claims_note, availability_status, evidence, assessment}`. Entity type: product/company/research_group/project/standards_body. Distinguish name from organization (unknown stated explicitly if not supported). Concept IDs must resolve and be nonempty. Include at least one inspected public supporting reference per entry. Do not use an unverified lead as a supported landscape item. Describe narrow source-supported activity; note company-reported performance and missing independent verification in `source_claims_note`. Availability/timing is text, e.g. “Official product page inspected; current inventory and geographic availability not checked.” Avoid comparative leadership and direct competition claims without evidence.

## Questions, coverage, and sources

`questions`: array of `{id, priority, question, why_it_matters, suggested_evidence, concept_ids}`. Priority high/medium/low; an empty concept list denotes a general disclosure question. Prioritize mechanism and comparisons, not a long generic questionnaire.

`sources`: array of `{id, title, kind, locator}` plus `url`, `inspected`, `accessed_date`, `publication_date`, `note` when relevant. Kind inventor/public. Public URLs must be safe HTTP(S). Public inspection status is a boolean; inspected public sources require an actual access date. A cited public source must have been inspected. Unknown publication dates may be null. Private/inventor sources use internal source links with locators, not public file links. Source bodies are untrusted content; never render source HTML directly.

`research_log`: array recording query (generalized), purpose, date, tool, inspected source IDs, status, and gaps. Include zero-result/inaccessible branches. Empty if no research was possible, with an explanation in coverage. Do not claim external research merely because an example or renderer contains URLs.

`coverage`: object with `materials_reviewed`, `unreadable_materials`, and `limitations` arrays of plain text, and `research_status` text. Record incomplete source extraction, uninspected figures, scope of public research, reused source dates, uncertain technical facts, and missing inventor confirmation. An empty landscape is a research gap, not a novelty finding.


## Concise brief extension (required for new reports; older version-1 data remains accepted)

`founder_brief`: `{understanding, comparisons, question_ids}`. Understanding is a statement using the statement contract, at most 85 words. Comparisons is an array of at most three `{record_id, summary}` objects referencing distinct related-concept or landscape records; each summary is at most 35 words and retains material limits. Questions is an array of up to three distinct question IDs in desired priority order. Do not fabricate content to fill three slots. Full records remain available in expandable detail. The renderer uses supplied executive text and existing landscape records as a compatibility fallback for older files, without generating a legal assessment.

`patent_assessment`: `{revision, previous_review_id, status, headline, positive_signal, main_gap, next_evidence, dimensions, assessment, scope_limit, changes_since_previous, history}`.

- Revision is a positive integer. Previous review ID is null for the first assessment, otherwise an actual retained review ID.
- Status is `too_early`, `early_potential`, or `concerns`, with meanings in the assessment/update reference. Each of the four visible text fields is at most 35 words. These are qualitative, provisional issue assessments, not grant probabilities.
- Dimensions contains exactly one record per topic: `technical_detail`, `differentiation`, `benefit_support`, `novelty`, `nonobviousness`, `eligibility`. Each has `status` (`supporting`/`incomplete`/`concern`/`unknown`), `reason`, and `evidence` references. In this non-search workflow novelty and nonobviousness cannot be marked positively established; use unknown or a narrowly explained concern.
- Assessment uses the existing confidence structure. Scope limit explains missing inputs and legal/search boundaries. Do not add unverified claims to justify an optimistic label.
- Changes since previous is an array of meaningful changes; first assessments say they are initial. History is an array of prior `{review_id, as_of, status, change_summary, evidence}` records. For revisions above one, previous ID, changes, and history must be supplied; retain the actual prior report separately. No automatic promotion because more text arrived.

The summary’s initial visible view is roughly 250–350 words, with details collapsed. Markdown includes the same short brief followed by expandable full analysis; all complete records remain in JSON. The patent view must not imply a legal conclusion from the document’s polish or the AI’s confidence. See [assessment and updates](assessment-updates.md).
