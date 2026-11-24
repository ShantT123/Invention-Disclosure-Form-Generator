# Invention Disclosure Form Generator

Turn an inventor or startup founder's description into a clear **invention disclosure and executive brief**, with matching **Markdown, JSON, and an offline HTML dashboard**.

The report helps founders explain what they are building, identify the technical ideas the AI sees, and prepare a more productive conversation with patent counsel. It is **not a prior-art search** and does not determine patentability, legal coverage, infringement, or freedom to operate.

## New: local Chrome application prototype

For the operator workflow—receive client text, enter it locally, review/update the brief, and give the client an HTML file—there is now a [local browser application](docs/local-app.md). It preserves both skills and uses the v2.0 renderer. Client projects and immutable assessment revisions are stored outside the repository; public research is off unless explicitly used.

Source launch (Python 3.10+; official Ollama Mac app required):

```sh
python3 -m local_app
```

The interface handles runtime startup, local model downloads, descriptions, follow-up answers, report previews, and HTML/Markdown/JSON downloads. It has no cloud inference fallback. Version 0.1.3 accepts pasted English text up to 200,000 UTF-8 bytes per project, with visible counters and sequential local summarization for long specifications. Long-text evidence is attached from app-owned numbered excerpts, so the model does not have to reproduce exact quotations or source IDs. The model context remains bounded; processing may take many minutes and summaries may omit details. PDFs and drawings are not supported. Optional research uses predefined generic queries and explicitly imported public URLs.

A GitHub Actions workflow (PR build or manual run) and Mac build script prepare a downloadable `.app`/`.dmg` without the App Store. Mac packaging, signing/notarization, real-model quality, and 8 GB Mac performance still require Mac validation; this repository does not yet provide a tested/notarized installer. See [setup, privacy, limits, testing, and distribution](docs/local-app.md).

## Choose a skill

| Skill | Audience and format | Install folder |
| --- | --- | --- |
| Existing detailed disclosure skill | Full founder disclosure with core concepts, comparisons, evidence, and research records | [founder-invention-disclosure](skills/founder-invention-disclosure/SKILL.md) |
| **Inventor Brief v2.0** | **Inventor/founder focused:** concise four-part brief with expandable detail and versioned provisional patent-strength screening | [inventor-brief-v2](skills/inventor-brief-v2/SKILL.md) |

The inventor-focused v2.0 is a **separate skill**, not a replacement for the existing detailed workflow or the attorney-focused tools in Patent-Counsel-Agent. Both skills are independently installable and output Markdown, JSON, and offline HTML. Install each entire folder, including references and scripts.

### Inventor Brief v2.0

The default view answers four questions: **What does the AI understand? What similar ideas and innovators exist? What information would help next? What is the provisional patent-strength view?** It shows one short understanding paragraph, at most three comparison cards, and three priority requests. Evidence, confidence reasons, the six-dimension issue screen, and the full disclosure stay behind expandable controls.

The patent view separates technical detail and benefit evidence from unresolved novelty, nonobviousness, and eligibility questions. It uses qualitative statuses and missing facts, not a patentability score. When new inventor data arrives, rerun the skill: retain the prior assessment and source dates, record a new revision, explain changed findings, and refresh priority requests. More detail does not automatically mean a stronger patent case. See [assessment and update guidance](skills/inventor-brief-v2/references/assessment-updates.md).

> Use $inventor-brief-v2 on this invention description. Give me the concise inventor-focused brief, three priority requests, similar technologies/products/innovators with sources, and a provisional patent-strength view. Generate Markdown, JSON, and HTML with evidence in expandable detail. When I provide more information, issue a new revision and explain what changed.

Try the separate v2.0 example: [HTML](examples/inventor-v2/report/disclosure.html), [Markdown](examples/inventor-v2/report/disclosure.md), [JSON](examples/inventor-v2/report/disclosure.json), or [editable analyzed input](examples/inventor-v2/analyzed-input.json). The founder input is fictional; the qualified public product references are real.

```sh
python3 skills/inventor-brief-v2/scripts/render_report.py examples/inventor-v2/analyzed-input.json /tmp/inventor-v2-report
```

The renderer displays supplied analysis; host tools perform reasoning, document reading, and research. Older version-1 JSON is supported, with an explicit message when no patent assessment was authored. The skill release version is 2.0; the compatible JSON envelope remains schema version 1.

## What founders receive

| Section | What it answers |
| --- | --- |
| Executive summary | What is the idea, why does it matter, and what should I clarify next? |
| Problem, solution, intended advantage | Who has the problem, how does the solution work, and what benefits still need evidence? |
| Core technical concepts | Which mechanisms or interactions does the AI believe are central, and why? |
| Clarify and differentiate | Which related technical approaches should I understand, and what actual implementation differences should I explain? |
| Products and innovators | Which sourced public products, companies, or research groups work on related ideas? |
| Founder questions | Which diagrams, examples, rules, alternatives, or test results would make the disclosure clearer? |
| Sources and scope | What was inspected, inferred, left unknown, or not researched? |

Every report distinguishes **inventor statements**, **AI interpretations**, **external sources**, and **unknowns**. Core concepts are proposed interpretations for founder confirmation. Comparisons ask concrete questions; they do not assume an invention is different or promise that a change makes it patentable. Products and companies need inspected supporting sources, a technical connection, and explicit evidence limits. No patentability score is generated.

## Use the skill

Install the complete [skills/founder-invention-disclosure](skills/founder-invention-disclosure) folder in your assistant's skills directory, including its `references/` and `scripts/` files. Read [SKILL.md](skills/founder-invention-disclosure/SKILL.md) for the workflow. In an assistant without skill installation, supply that file and its references as instructions.

Example request:

> Use $founder-invention-disclosure on the description below. Prepare a founder-friendly executive invention disclosure: problem, solution, intended advantages, core technical concepts, related concepts and specific differentiation questions, and sourced products and innovators. Generate disclosure.md, disclosure.json, and disclosure.html. Mark AI interpretations and unknowns clearly. This is not a prior-art search.

A short description is enough to start. Optional drawings, notes, and measurements improve the result. The skill proceeds with available information and asks focused questions rather than fabricating missing details. It does not require the founder to know patent terminology or have a technology taxonomy.

Public terminology/product research uses generalized queries automatically unless restricted. Confidential names, verbatim unpublished passages, proprietary parameters, and distinctive unpublished combinations must stay out of public queries. If research is blocked, the report still ships with explicit gaps. Keep real invention materials and generated reports outside this public repository. No report is automatically hosted, emailed, or filed.

## Try the worked example

The [fictional founder description](examples/founder-input.txt) concerns a household water controller. **The invention and founder input are fictional.** The public Moen and Resideo examples are real, selected references inspected on November 23, 2026; company statements and historical availability are qualified. These references do not establish a novel distinction or constitute a prior-art search.

- [Executive disclosure in Markdown](examples/report/disclosure.md)
- [HTML dashboard](examples/report/disclosure.html) — download the raw file and open it locally; GitHub's source viewer does not run HTML.
- [Structured report JSON](examples/report/disclosure.json)
- [Editable analyzed input](examples/analyzed-input.json)

The HTML has sidebar navigation, source links, concept/product search, Markdown and JSON downloads, and print/save-PDF support. It embeds all assets, requires no server, and makes no external requests on load. Source pages open only when clicked. All report text remains readable without JavaScript.

## Render analyzed JSON

Requires Python 3.10+; no third-party runtime package or API key is needed for rendering.

```sh
python3 skills/founder-invention-disclosure/scripts/render_report.py examples/analyzed-input.json /tmp/founder-report
```

This writes `disclosure.md`, `disclosure.json`, and `disclosure.html`. Choose an output directory separate from the analyzed input file. The renderer validates IDs, evidence links, explicit interpretation status, and important record fields. It does **not** read invention documents, call an AI model, search the web, or automatically verify the truth of submitted analysis. Your host assistant provides those capabilities and follows the skill. Model reasoning quality and host-specific installation remain unvalidated.

See the [output contract](skills/founder-invention-disclosure/references/output-contract.md), [research workflow](skills/founder-invention-disclosure/references/workflow.md), and [presentation guidance](skills/founder-invention-disclosure/references/presentation.md).

## Checks

```sh
python3 -m unittest discover -s tests
```

Renderer tests cover matching structured data, source/ID validation, unsafe content, unsupported claims, empty research, and CLI output. Browser checks cover desktop/mobile layouts, search, downloads, source navigation, printing, and no-JavaScript reading. These checks validate presentation behavior, not patentability or substantive model analysis.
