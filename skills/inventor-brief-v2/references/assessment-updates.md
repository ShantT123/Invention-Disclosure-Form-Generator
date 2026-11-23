# Provisional patent-strength view and incremental updates

This is a founder-readable issue screen, not a prior-art search or an overall legal-strength determination. Keep the default card short: status, one-sentence headline, positive signal, main gap, and what evidence would change the view. Expandable details show the six dimension assessments, confidence in the analysis, scope, and history.

Assess technical detail, differentiation, and evidence for advantages separately from novelty, nonobviousness, and eligibility. Do not conflate clarity with patentability, a prototype with a legal requirement to have one, testing with proof of nonobviousness, or a close product with an anticipation conclusion. “No test supplied” is an evidence gap, not a declaration that the invention cannot be patented. A physical device can still have unresolved eligibility and claim-drafting issues. Never automatically favor software, hardware, AI, or a technical buzzword.

Qualitative overall statuses:

- `too_early`: material mechanism/distinction information or legal analysis is absent; the card says “Too early to assess”.
- `early_potential`: a concrete, source-supported distinction is described sufficiently for focused counsel investigation; its novelty and nonobviousness remain unverified. Do not use merely because no match was found.
- `concerns`: material ambiguities, contrary evidence, or close disclosed overlap call for targeted clarification. This is not a rejection, invalidity opinion, or finding of no patentable subject matter.

Each dimension is `supporting`, `incomplete`, `concern`, or `unknown`, with a reason and evidence. In this limited workflow, novelty and nonobviousness must stay `unknown` or a qualified `concern`; a positive legal conclusion requires work outside this non-search brief. The card’s confidence refers to the issue screening and its inputs, not probability of obtaining a patent. Jurisdiction, proposed claims, legal search scope, and current status must stay explicit or unknown.

The USPTO’s [Patent essentials](https://www.uspto.gov/patents/basics/essentials) and [Nonprovisional application guide](https://www.uspto.gov/patents/basics/apply/utility-patent) provide US orientation. They are general references, not matter-specific evidence or a substitute for counsel. Verify current primary guidance if giving jurisdiction-specific legal explanations.

## Update on new inventor information

1. Add the actual new description, drawing, data, or correction as a dated source. Keep old versions and actual inspection dates. Separate invented suggestions from inventor-confirmed implementations.
2. Record which concepts, comparisons, advantages, questions, and assessment dimensions changed. A new structure may improve technical specificity without resolving novelty; a test may support an advantage without establishing a patent distinction.
3. Increase `revision`, set `previous_review_id`, and append the prior status/as-of date and meaningful change summary to history. Record changes and retained uncertainties. Preserve source references for the changes in the underlying concept/dimension evidence and prior history where appropriate.
4. Revisit the three priority requests; remove resolved questions from the brief while retaining resolution context in the full records/history. Do not claim answers to unaddressed questions.
5. Save a new review JSON and separate output directory; never overwrite the earlier assessment snapshot. Regenerate all three files from the same updated data. The renderer displays supplied revisions and validates linkage; it does not independently judge new facts, automatically update from external systems, or calculate patent strength.

A presentation refresh without new inventor data must say so. It may create the first formal assessment of already supplied evidence, but must not pretend that technical strength improved.
