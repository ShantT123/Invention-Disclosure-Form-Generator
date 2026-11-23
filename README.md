# Invention Disclosure Form Generator

Turn an inventor or startup founder's description into a clear **invention disclosure and executive brief**, with matching **Markdown, JSON, and an offline HTML dashboard**.

The report helps founders explain what they are building, identify the technical ideas the AI sees, and prepare a more productive conversation with patent counsel. It is **not a prior-art search** and does not determine patentability, legal coverage, infringement, or freedom to operate.

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
