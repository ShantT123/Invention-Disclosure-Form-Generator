# Local browser prototype · 0.1.3

The operator receives client information, enters it locally, reviews the AI interpretation, adds client answers, and downloads an HTML report to send separately. This does not email, host, file, or share a report automatically. Both existing skills are preserved.

## What works in the prototype

- Chrome interface for creating and reopening projects, entering descriptions and follow-ups, and generating an Inventor Brief v2.0.
- Three bounded local-model stages: extract the mechanism; compare related concepts and approved source excerpts; prepare the concise brief and provisional issue assessment.
- Existing v2.0 renderer and validator, expandable report preview, HTML/Markdown/JSON downloads, printing, and sources.
- Private SQLite storage outside the repository. Each successful generation creates an immutable report revision and retains the previous assessment and its history. Original inputs and corrections remain separate records.
- A single app-managed Ollama process, one job at a time, model download progress, cancellation, and errors that do not replace earlier reports.
- Optional public research through a finite list of broad topic queries and explicitly imported public HTTPS pages. No automatic invention-based queries or autonomous model tool calls.

This is a text-only English prototype. It accepts up to 200,000 UTF-8 bytes of inventor text across a project’s inputs, three public pages, and bounded source excerpts. The HTTP request limit is a separate 2 MB. Visible byte counters and specific errors explain these limits before submission. It does not silently truncate inventor inputs. PDFs, OCR, drawings, arbitrarily long histories, and multi-user access are not supported. The 4K inference context remains bounded: text over the direct-input budget is split losslessly into sections of at most 3,600 UTF-8 bytes. Each section is summarized locally, then summaries are consolidated in bounded pairs before the existing three analysis stages. For long-text summaries, the model selects short numbered excerpt IDs from an allowed list. The app attaches the literal source text, original source ID, and character offsets; consolidation selects from the same verified evidence. The model never supplies these quotations, and unknown IDs are rejected. Interpretations can still be wrong. The full original text and a section-summary ledger remain in the report JSON; the dashboard states processing coverage and the risk of omissions. Long specifications can take many minutes on a small model. Every section being submitted does not establish that every important detail was understood or retained. This does not turn the founder brief into a claim chart or a complete patent review.

## Run on your own machine

For source use, install Python 3.10+ and the official [Ollama Mac application](https://ollama.com/download/mac). The source app has no third-party Python runtime dependencies:

```sh
python3 -m local_app
```

The launcher opens Chrome (or the system browser if Chrome is unavailable). Click **Start local AI**, select **Llama 3.2 · 3B** initially, and click **Download model**. Downloading contacts the model registry; inventor text is not included. The app uses Ollama's installed binary directly, so no Ollama Terminal setup or CLI symlink is needed. If port 11435 is already occupied, it refuses to attach to an unknown server.

Once a model is downloaded, normal disclosure generation works offline. Qwen3 4B is an alternative to evaluate, not a claimed upgrade in legal reasoning. The app forces its managed process to local-only mode, uses a fixed loopback endpoint and an explicit model allowlist, and never falls back to a cloud model.

For a packaged GitHub download, see [Mac packaging](#mac-packaging). Source running requires Python; the packaged app is intended to remove that requirement. The package still requires installing Ollama through its normal Mac installer. Bundling and maintaining a native inference engine inside the app is deferred.

## Using client material

1. Create a disclosure with a private working title and a short description. No automatic research occurs.
2. Generate the brief. Review the AI's understanding and all source-supported comparisons; the small model is not a substitute for your technical/legal review.
3. Add answers or corrections and generate a new revision. Previous reports remain selectable. A presentation refresh or additional words do not establish stronger patentability.
4. Download the HTML and open it before sending it. It embeds the complete report JSON and Markdown, original inputs, evidence, and assessment history. Collapsed details are not redaction. Do not enter operator-only privileged notes that should be excluded from the client's copy.
5. Use **Quit local app** when done. Closing the Chrome tab alone does not shut down the local server/model process.

No actual client material belongs in repository examples, support tickets, telemetry, screenshots, or automated tests.

## Public research boundary

The app can open a query composed only from one predefined broad topic and “products research”. The exact query is shown before the deliberate click. This is intentionally less flexible than an AI-created search string: no private names, numerical parameters, or distinctive invention combinations are constructed from the description. Search websites still receive ordinary browser metadata/cookies according to your browser settings; the app does not guarantee anonymity.

To add evidence, select a public page yourself and approve its exact URL. Only that URL is sent, without cookies, credentials, referer, or inventor data. The fetcher accepts HTTPS on port 443, rejects query strings/private IPs/reserved destinations, validates each redirect, and pins the validated destination while checking the TLS hostname. It limits response size and extracts text without running page scripts. Some legitimate pages will be rejected or unreadable. Do not use private document-sharing URLs.

Only a bounded excerpt is passed to the local model. Product/company identities must appear in the imported title/excerpt, and a supporting quotation must match the retrieved excerpt exactly. The app records the actual access date and content hash. This prevents invented references from becoming sources; it does **not** prove the model's interpretation of a quotation. Unsupported candidates trigger one bounded repair attempt; if they remain unsupported, generation fails rather than presenting them as verified. With no imported sources, all model-suggested public comparisons are discarded, an explicit gap remains, and the rest of the brief can proceed. Review comparisons before sharing.

Model-memory products are not permitted in the landscape. With no public sources, it remains empty with an explicit research gap; generic related concepts may be presented as AI hypotheses. Imported but unused pages are not marked inspected. There is no prior-art search or legal status verification.

## Storage and local access

Default Mac directory: `~/Library/Application Support/Invention Disclosure Generator`. Other platforms use `~/.local/share/invention-disclosure-generator`. The app refuses a data directory inside its source/bundle directory, creates private directory/database permissions, and uses SQLite transactions. Use `--data-dir /private/local/path` for a separate source-run workspace if needed. Closing/reopening the app preserves inputs and revisions.

Storage is not app-level encrypted. Use FileVault, appropriate user-account access, and backup settings. Exports and backups can leave the computer according to your choices. Model files can consume several GB; do not equate download size with working RAM.

The HTTP service binds only to 127.0.0.1 on a random port. Each launch has a new session token passed in the launch URL fragment (not an HTTP query), removed from the address bar and retained only in that tab's session storage. API requests require the token; mutations additionally require the correct Origin and Host. The report iframe uses a scoped HttpOnly/SameSite cookie, a sandbox, and the existing renderer's restrictive CSP. The UI has no remote scripts, fonts, analytics, request-content logs, or arbitrary cloud endpoints. These measures do not protect against malware or another process already running as the same user.

## Assessment and model limits

The app retains evidence distinctions, qualitative issue assessments, and prior-report links. Novelty, nonobviousness, and eligibility are forced to unknown in this non-search prototype. “Early potential” cannot be selected unless technical specificity and differentiation are both proposed as supporting; this remains unverified issue screening. No patentability score or grant probability is generated. A small model can still misunderstand mechanisms, invent a distinction, or overstate an advantage; code cannot establish substantive correctness. All interpretations are labeled and require review.

The stages are a bounded implementation of the skill workflow, not a claim of behavioral equivalence to a frontier model reading the complete skill and documents. Actual local inference quality, speed, and memory pressure on an 8 GB Mac have **not** been validated by the automated tests. No latency or legal-quality benchmark is claimed.

Before using this with real clients, evaluate on your actual Mac with fictional/public cases: cold/warm start, peak memory pressure and swap, cancellation, failure recovery, long/contradictory inputs, source attribution, unsupported-product rejection, and whether new evidence changes only the supported assessment dimensions. Test with networking disabled after model download. Record chip/macOS/runtime/model versions, inference duration, failures, and attorney review results. Do not use a demonstration fixture as evidence of real model performance.

## Mac packaging

GitHub Actions includes a **Build Mac prototype download** workflow (pull-request build or manual run) targeting an Apple Silicon runner. It builds an app with a bundled Python runtime and resources and produces a DMG and SHA-256 checksum as workflow artifacts. No App Store is involved. The workflow does not publish a release automatically.

For a local Mac build, developers install the pinned packaging dependency and run:

```sh
python3 -m pip install pyinstaller==6.16.0
bash packaging/build_macos.sh
```

`packaging/build_macos.sh` checks the build platform/architecture, creates `.app`/`.dmg`, and supports optional `MAC_SIGN_IDENTITY` and `MAC_NOTARY_PROFILE` settings for signing/notarization with your own Apple credentials. Do not commit credentials. Without them the artifact is explicitly an **unnotarized prototype**, not a polished trusted distribution. GitHub can host a manually reviewed release asset after the Mac build and model-quality checks succeed.

Mac packaging cannot be built or validated in the Linux development environment. The workflow needs to run on GitHub/macOS, and the app must be opened/tested on a real Mac. No notarized installer, bundled model, or tested Mac binary is claimed in this source PR.

## Tests

```sh
python3 -m unittest discover -s tests
python3 tests/browser_check_local.py /tmp/local-app-preview
python3 tests/browser_check_long.py /tmp/long-input-preview
```

The second command requires Playwright and Chromium for development only. It uses **explicitly synthetic runtime responses** to test real application routes, UI, rendering, downloads, follow-ups, and revision preservation. Unit tests check provenance, immutable storage, session/Origin/Host boundaries, unsupported sources, cancellation, and restricted fetching. They do not replace real-model or hardware evaluation.

## Updating from 0.1.0 after a large-paste error

The old “Expected a bounded JSON request” error combined an HTTP size check and content-type check, before the model was called. The old app also imposed a 6,000-byte project limit. Version 0.1.1 separates transport and saved-text limits, provides readable size/type errors, and adds local sequential preparation for longer text. Quit the old local app before opening the updated build. Existing SQLite projects, reports, and model downloads remain in the same data directory; do not delete it to update. Data saved by the new build is backward-readable as SQLite, but the older app will still reject generating from long projects. Failed submissions keep the pasted form text; failed/cancelled generations keep earlier reports.

The long-text path is tested with synthetic inference responses, including original-text preservation, end-of-document coverage, UTF-8 section boundaries, literal excerpt binding, unknown-ID rejection, structured-response recovery, reduction, and cancellation. Real local-model summary quality and runtime on an 8 GB Mac are not benchmarked. Review the full specification and actual claims before relying on the resulting brief.

Version 0.1.2 fixes the long-document failure “A document summary included a quotation not found in its input section.” Earlier builds asked the model to copy quotations and long source IDs exactly; the new excerpt-selection path removes that copying step rather than accepting fuzzy matches. A malformed structured response gets one bounded retry, followed by a stage-specific error if it still fails. Public product-source quotation checks remain unchanged. Quit the old app and replace it with the updated build; existing saved inputs, models, and report revisions remain in place. Regenerate the failed report. No database migration is required.

Version 0.1.3 fixes “Model invented a public source.” Comparison schemas now use the actual concept and public-source counts. With public research off, model-memory product suggestions are removed before assessment and export, and the report records that omission. With imported sources, both source indexes and literal supporting evidence are checked within the bounded retry. It does not treat an empty product list as evidence of novelty. Existing projects, models, and assessment history remain compatible.
