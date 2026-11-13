# AI implementation status — 2026-11-08

The 0.4.3 patch keeps the host iframe visible with the real shared stylesheet.
The 0.4.2 patch opens the AI host in its own connection dialog, keeping its
controls usable above settings and consumer drawers. The 0.4.1 patch tightens report metric validation and labels imported results as
self-reported, and adds verified engine-free pins for sites without local browser
models. The 0.4.0 baseline evidence below remains dated; publication and
later acceptance receipts are recorded in the source repository’s `todo/ai_plan.md`.

This snapshot describes the implemented **0.4.0 runtime** and the remaining rollout
of [todo/ai_plan.md](../todo/ai_plan.md). The demo was deployed from commit 67b8464.
The runtime and demo passed [Linux CI in Chromium, Firefox and WebKit](https://github.com/curtcox/Tools-for-pages-with-state-in-URL-fragments/actions/runs/42515655778).
AI-host deployment, Python production migration and public model/report uploads
remain open. Published v0.3.5 bytes and release tags have not been changed.

This file is included in immutable kit pins. [The release page](https://github.com/curtcox/Tools-for-pages-with-state-in-URL-fragments/releases/tag/v0.4.0)
and the source repository's `todo/ai_plan.md` hold later publication/deployment
receipts; a generated archive or this snapshot alone does not prove publication.

## Local implementation

- Separate opt-in AI/package entry, deployment validation, normalized model
  catalog, typed provider errors, conservative total/day/month budget reservations.
- Paste handoff, direct OpenRouter/OpenAI/Anthropic/Gemini/local drivers, PKCE
  popup/callback handling, native Jev questions and honest LLM emulation.
- Snapshot proposals, strict edit/full validation, safe text diff, stale rebasing,
  navigation cancellation, refinement, explicit acceptance, undo/history commits.
- Fragment Notes Ask/settings UI, text-search sample fallback, reusable AI chooser,
  blind comparison, local preference votes, verified report import/export.
- Data-only evaluation suites/checks, good/bad reference validation, calibrated
  judge helpers, sequential/resumable runs, Wilson intervals and separate metrics.
- Verified 1 MiB model manifests, bounded/resumable 64 MiB shards, cache read/write
  verification, commit-pinned ranges, explicit download consent, storage deletion.
- Vendored wllama 3.8.1 plus local compatibility JS/WASM, with independently pinned
  engine bytes, one-thread Worker execution and a network allowlist limited to
  verified WASM Blobs. Linked manifests never supply executable code.
- Static AI host, exact-origin MessagePort protocol, same-origin popup-to-frame
  credential handoff, optional per-app host persistence, host-side model consent,
  staged CSP/immutable hashes; gateway client and shared mock conformance checks.
- Manual CLI tools for manifests, evaluation, live browser evidence and host staging.

## Evidence actually obtained

**Local automated tests:** 299 unit tests passed. New browser tests passed in
Chromium and Playwright WebKit, including Pixel 7 and iPhone 14 emulation: reviewed
changes/undo, paste, 360px keyboard layout, all three connection modes, actual host
popup credential handoff, blind comparison/resume/export. App-origin localStorage,
sessionStorage, IndexedDB, Cache Storage, URL, history and drafts were scanned with
probe credentials. The final browser run covers 128 checks across those four projects.

**Live OpenAI, 2026-11-08:** Chromium and Playwright WebKit each completed ordinary
and streaming calls to pinned `gpt-4.1-mini-2025-04-14`, validated a synthetic edit,
and returned usage. Four calls cost $0.0001984. Live Firefox did not run locally: its macOS
Playwright binary exits with “Could not find profile folder”, including a retry
with an alternate temporary directory. WebKit is not a real Safari measurement. Linux CI subsequently passed the mocked runtime/browser acceptance in Chromium, Firefox and WebKit ([run](https://github.com/curtcox/Tools-for-pages-with-state-in-URL-fragments/actions/runs/42515132768)); this is not live-provider or storage evidence for Firefox.

A manual Notes comparison attempted three pinned OpenAI model routes on two
synthetic cases with two repeats. GPT-4.1 and GPT-4.1 mini completed four cases each;
the nano route failed its requests and is not evidence of output quality. No winner
was declared between the successful models.

**Live OpenRouter, 2026-11-08:** the user completed PKCE in Chrome, granting a
verification key with a $0.10 provider limit and one-hour expiry. A native
`typesafe/jev-1.14` choice ranked the three demo samples and selected “Hello,
everywhere” for a multilingual request, reporting probabilities 1/0/0. It cost
$0.000018858; the document and URL were unchanged. The live callback needed a
manual trailing-slash correction; new callbacks name `index.html`, and the preview
server now preserves query parameters when redirecting directories. The already
loaded client also needed JSON-quoted request input; the source now accepts plain
text directly, with a regression test. This verifies a native response, not every
Jev question type or option-count limit.

**Python live comparison:** 25 diverse synthetic changes were checked in fresh
opaque Python sandboxes in Chromium for each of three pinned hosted models:

| Model | Objective successes | Valid proposals | Incurred cost |
| --- | --- | --- | --- |
| GPT-4.1 mini | 25/25 | 25/25 | $0.0037268 |
| GPT-4.1 | 24/25 | 25/25 | $0.0190100 |
| GPT-4o mini | 22/25 | 25/25 | $0.00146775 |

The 95% Wilson intervals overlap: there is not enough evidence to separate them.
The two compatible local reports contain 75 results with matching suite CID,
prompt hash and parameters. They are not published. A combined browser-model /
Python attempt closed before recording a case; this is not a successful on-device
Python comparison or evidence of a particular cause.

**Spending:** known actual model cost is $0.027089008. The conservative ledger
also retains $0.2015466 for unresolved attempts, totaling $0.228635608 used or
reserved against the approved $10 cap. No paid calls run in CI. Raw reports and
the persistent ledger stay in ignored `.ai-local/`; keys are excluded.

**Real browser model:** Chromium ran SmolLM2 135M Instruct Q4_K_M through wllama,
loading 105454432 verified bytes in two shards from local test mirrors. Both first
mirror attempts deliberately returned 404; both second mirror attempts succeeded.
The real model answered “Hello!”, using 37 input/3 output tokens, with 2343 ms
reported for load+generation. This is real WASM/model execution, not a test engine.
It is not a WebGPU, public CID hosting, remote-range or real Safari result. Model
source commit: `bartowski/SmolLM2-135M-Instruct-GGUF@09816acd5d99df7be770d85ea30822623dab342c`.
Manifest generation was local; neither weights nor manifest were published.
A bounded HTTP probe of the commit-pinned Hugging Face GGUF URL followed its
302 redirect, received 206 with `Content-Range: bytes 0-1023/105454432` and final
`Access-Control-Allow-Origin: *`, and matched those 1024 bytes to the verified
local model. This checks the remote range/CORS response, not an additional browser
model run or a persistent guarantee about future CDN behavior.

## Plan phase gates still open

| Phase | Candidate state | Required before marking done |
| --- | --- | --- |
| 0 — evidence | OpenAI success/streaming and real wllama injection verified | Real Safari/Firefox storage; Jev option limits; other-provider successful streams;  permissions across real browsers |
| 1 — contracts/core | Implemented and unit-tested | Candidate integrity checks pass; remote publication is separate |
| 2 — Ask/paste/direct | Implemented; Chromium/WebKit/phone emulation passed | All three engines pass in Linux CI; real-device/provider coverage remains separate |
| 3 — providers/decisions | Drivers, settings, emulation, chooser and fallback implemented | Jev is live-verified; other-provider successful streams and consumer adoption remain |
| 4 — evaluation | Reference-checked runner, metrics, comparison/report APIs and manual live Notes run | Private saved cases and exact-match references are implemented; broader quality evidence and end-user report Publish remain consumer integration work |
| 5 — AI host | Static implementation and staged artifact; real popup protocol tested with mocked provider | [Registry/header draft PR #242](https://github.com/curtcox/hashbin.org/pull/242) prepared; owner-approved deployment, live receipt and real storage/permission measurements remain |
| 6 — browser models | Pinned real engine, verified cache/mirror logic and a real Chromium run | Public manifest/mirror acceptance and real GPU/device evidence |
| 7 — gateway | Client, protocol and shared mocked feature contracts implemented | Any billed/production server is a separate project and is not shipped here |
| 8 — Python pilot | Isolated integration, 25 reference pairs and 75 live hosted results; consumer checks passed | Published-pin gate, PR/review, approved deployment and published comparison report |
| 9 — release | Versioned runtime and demo prepared; all three CI engines pass | Actual remote tag/release receipt; remaining deployment gates stay separate; existing tags never move |

## Deployment artifacts

`node tools/stage-ai-host.mjs` creates the static host plus `_headers` and an
`ai-host-manifest.json` hash list. A local `dist/ai-host-v0.4.0/` was staged for the
exact `https://python.hashbin.page` app origin. It is not a deployed ai.hashbin.page.
The registry and manual deployment integration are reviewable in [hashbin.org PR #242](https://github.com/curtcox/hashbin.org/pull/242). Its 995 unit tests pass; lint has zero errors. The production host must apply the headers; shared GitHub origins use direct mode.

Python pilot work is isolated under `/private/tmp/fragment-ai-python-pilot` on
`codex/ai-pilot`. It uses direct mode on canonical/recovery origins until a real
host is available. Accepting a change suppresses auto-run and returns to opaque
execution. Site checks start fresh opaque sandboxes, bound output, enforce a
30-second setup deadline and retain the existing five-second automatic-run limit.
No shared/API key is embedded or copied into that checkout. Its existing published
v0.3.5 pin is preserved; a local candidate v0.4.0 pin is additional, subject to the published-manifest gate.
Its checks passed: 44 Node tests with package coverage, 19 Python tests, static /
documentation / offline / vendor checks, the existing full Chromium and WebKit
browser suites, and the new AI acceptance/reference test in both. The AI test
confirms acceptance makes no automatic Python run. Firefox did not run locally.
Shared consumer contracts also passed 80 checks in Chromium, WebKit and both phone layouts (48 demo-only AI checks intentionally skipped). The consumer has its own AI reference/acceptance checks. [Python pilot draft PR #5](https://github.com/curtcox/PythonOnline/pull/5) and a local patch are prepared for review; production remains unchanged.

## Sources used to implement drivers

- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [GPT-4.1 mini model/pricing](https://developers.openai.com/api/docs/models/gpt-4.1-mini), [GPT-4.1](https://developers.openai.com/api/docs/models/gpt-4.1), [GPT-4.1 nano](https://developers.openai.com/api/docs/models/gpt-4.1-nano)
- [OpenRouter Decisions reference](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request), [Jev tutorial](https://openrouter.ai/docs/guides/community/jev-tutorial), [PKCE](https://openrouter.ai/docs/guides/overview/auth/oauth)
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages), [Gemini compatibility](https://ai.google.dev/gemini-api/docs/openai)
- [wllama source and MIT licence](https://github.com/ngxson/wllama)
