# AI adoption (0.4.0 candidate)

AI is optional. The normal `src/index.js` entry never imports it. Import
`src/ai/index.js` (package export `fragment-kit/ai`) and include
`src/ai/ui/ai.css` alongside `src/ui/kit.css`. There is no build step.
The candidate is not a published release or a deployed AI host. See
[AI implementation status](ai-status.md) for actual evidence and remaining gates.

## Minimal integration

Add an `ai` object to the ordinary app config:

```js
ai: {
  deployments: {
    'https://your-app.example/': { connection: 'direct' },
    'https://your-recovery.example/app/': { connection: 'direct' },
  },
  routes: ['paste', 'openai', 'openrouter', 'anthropic', 'gemini', 'local', 'browser'],
  budget: { total: 0, day: 0, month: 0 },
  models: [{
    ref: 'openai:YOUR-PINNED-MODEL', capabilities: ['generate', 'decide'],
    destination: 'OpenAI', pinned: true, prices: null,
  }],
}
```

Sites do not supply shared keys. Users connect their own accounts/keys, choose
models, grant consent and set budgets. Unmatched deployment URLs get paste only.
Unknown prices require a positive per-call confirmed maximum; automated evals
require known prices. Prices are USD per million tokens, not per token.
A local ledger cannot guarantee a provider bill, especially across tabs or devices.
Use provider-side limits as well.

```js
import {
  createAi, createAskPanel, createAiSettings, handleAiCallback,
} from './vendor/fragment-kit-v0.4.0/src/ai/index.js';

// Before urlState.parse(), process OAuth callbacks and scrub the callback URL.
if (!handleAiCallback()) {
  const ai = await createAi({ config, type, storage: createStorage({prefix: config.storagePrefix}) });
  if (ai) {
    const ask = createAskPanel({ai, type, getSnapshot, getFingerprint, onApply, urlState});
    workspace.append(ask.panel);
    createAiSettings({ai, container: moreBody, onChange: ask.refreshModels});
    // Add ask.panel as a tab, or mount it in a createDialog body.
    // On navigation/explicit loads: ask.cancel(). Typing may leave a stale proposal.
  }
}
```

`onApply` must follow the ordinary edit path, update drafts/revision guards, and
**suppress execution**. Acceptance is not permission to run generated code.
Execution remains an explicit consumer Run/Try action in its existing sandbox.
`getFingerprint` must describe all document fields. `urlState.commit` records the
pre-acceptance snapshot even when ordinary typing still awaits its debounce.
Undo refuses to overwrite subsequent edits.

`type.ai` supports `describe`, `output:'edits'|'full'`, `paths` (JSON pointers,
by default `/src`), `settingsKeys` (permitted top-level settings objects),
`maxBytes`, synchronous `validate`, named asynchronous `checks`, optional safe
`renderProposal({document,container})`, and `tryProposal(doc)` for an explicit
Try button. The strict application `normalize` remains the final authority.
Full output replaces the complete document and cannot rebase onto changed work.
Find/replace edits require one exact occurrence, including overlapping matches.
Refinement includes the prior proposal as data and requests consolidated edits.

Paste handoff needs no key or network. The first Copy prompt click prepares the
bounded prompt and its hash; the next copies it in that click. Open chat uses
`noopener,noreferrer`. Pasted JSON takes the same validation/review path.
No model output is interpreted as HTML, Markdown, remote media or executable code.

## Providers and decisions

Direct keys live only in a closure and disappear on reload/disconnect. Gateway
headers are requested afresh through `getAuthorization()`. HTTP redirects carrying
credentials are rejected. Errors expose status/action codes, never provider bodies.
The Anthropic driver supplies its required browser header. Gemini uses its
OpenAI-compatible endpoint. Local servers must use HTTPS or HTTP loopback;
browsers may ask for local-network permission.

OpenRouter sign-in uses prepared PKCE and a synchronous popup click. Direct-mode
callbacks check both state and popup identity. There is no redirect-only flow and
no consumer-subscription token extraction. Provider keys from other products are
never used. Live sign-in and provider-enforced key limits still need owner testing.

Decision questions follow Jev's `instructions`/`criteria` shape. Choice criteria
are named objects, score criteria are ordered arrays, and optional noul criteria name true
and false. Box answers use normalized top/bottom/left/right edges. Answers have `type` and `choice`, `score`, `noul` or `box` fields.
Native probabilities are validated. Emulation removes confidence and sets
`probabilities:null`. Only descriptions/tags/use cases are sent by `chooseSample`;
normal text search and explicit Open links remain available. No reasons are invented.

## Browser models

`ai.loadModel(cidOrLink)` explicitly fetches a bounded, CID-verified manifest.
It does not download weights. Inspect its name, total size, licence, source,
required memory, available storage and mirrors; then call
`ai.downloadModel(cid,{consent:true,signal,onProgress})`. Its model ref is
`256t:<manifest CID>`. A `?model=` link is a suggestion only; even manifest fetch
requires a user action. Invalid suggestions do not prevent opening the document.

Manifests allow only the pinned `wllama`/`gguf` engine. Each file is less than
2 GiB; contiguous shards are at most 64 MiB and their lengths come from CIDs.
Range mirrors must use a commit-pinned `/resolve/<40-hex>/` URL. Responses must
have the exact Content-Range and pass CID verification. A failed mirror, bad hash
or corrupt cache entry never enters the engine. Downloads resume by verified shard.

The engine receives verified Blobs in a Worker, uses one thread, tries WebGPU
where available and falls back to WASM. All executable JS/WASM is vendored and
pinned in `vendor/integrity.json`, independently checked before engine loading.
Compatibility files are local. The engine's own downloads/cache are disabled;
worker fetch permits only verified WASM Blob URLs. Abort terminates the worker.
Device/memory/startup failures are visible; nothing automatically retries.

Model caches use `<storagePrefix>-ai-models-…`; preserve that family in the
consumer service worker. They are not evidence that the app's offline manifest
is complete. `createWeightStore` exposes verified reads, list and delete controls.

```sh
node tools/model-manifest.mjs --input model.gguf --name 'My model' \
  --license Apache-2.0 --license-url https://example.org/LICENSE \
  --source https://example.org/commit/COMMIT --output model.json --shards ./shards
```

`--mirrors mirrors.json`, `--context`, `--memory` and `--shard-bytes` customize
metadata. HTTPS inputs must be commit-pinned; tooling streams them to a temporary
file and hashes one bounded shard at a time. Creating a manifest does not publish
it or retain its shards on HashBin.

## AI host and gateway

Host deployments use `{connection:'host',host:'https://dedicated-host.example/immutable-version/'}`.
Frame creation is lazy. A versioned MessagePort checks the exact parent origin;
there is no silent direct-mode fallback. Open AI host reveals its connection
panel, whose own click opens a same-origin top-level credential popup. Keys travel
only from that popup to its same-origin frame. The app never receives them.
Remembering a key on the host is optional and scoped to the app. Partitioned storage
falls back to this session port. Forget this app removes saved host credentials.
Browser model execution/downloads remain on the host, with a second host-side
approval for model downloads. Budgets and consent are per app origin.

```sh
node tools/stage-ai-host.mjs --config host-config.json --output dist/ai-host-v0.4.0
```

The config needs `name`, `storagePrefix`, exact `allowedOrigins`, `routes`, and
`models`. Shared github.io, preview, wildcard and hashbin.app run origins are
rejected. The output contains `_headers` with CSP/frame-ancestors and an immutable
hash manifest. The hosting operator must actually apply those response headers
and deploy at the versioned path. Staging alone provides no hosting, DNS, registry
entry or deployment receipt.

Gateway deployments use `{connection:'gateway',url:'https://gateway.example/'}`.
The base gets `v1/models`, `v1/generate` and `v1/decide` appended. SSE `text` events
carry `{text}` and the final `result` event carries the normalized response with
required usage and cost. Decisions also require a declared native/emulated source.
`AiError.code` distinguishes authorization, credit, rate-limit, model-unavailable,
size, provider and network failures. Servers own authentication, origin policy,
spending enforcement and cancellation; the kit supplies no billed server.

## Evaluation and reports

Use `parseSuite`, `validateReferences`, `runEval`, `createReport`, `loadSuite`,
`parseReport`, `loadReport` and `createCompareModels`. Suites/reports are at most
1 MiB and are data only. Each change case requires a known-good passing and a
known-bad failing reference. Named site checks execute only trusted consumer
functions, preferably inside the existing sandbox. The data-only regex check
intentionally has no grouping/repetition/backreferences; use a site check for more.

Every run preflights/reserves calls against its cap and the app ledger. It runs
sequentially (also for browser models), supports abort, and resumes prefixed local
results by suite CID/case/model/repeat/prompt/maxTokens. Cached results retain their
original incurred cost; invocation spend counts newly attempted calls only.
Imported reports are labeled self-reported: CID verification proves unchanged bytes, not measured performance. Numeric metrics and decision-source/privacy flags are strictly checked.
Reports record resolved provider refs, prompt hashes, parameters, kit version,
usage, timings, checks and failures. Private cases are excluded by default.
Report export/import is explicit; a consumer `onPublish` hook must be prepared
with the existing HashBin initialization/synchronous-click contract.

Metrics include success N/Wilson intervals, valid output, failure type, change
ratio, repeat agreement, native top-2/Brier/log loss, latency and cost per success.
Judge calls are separate: `calibrateJudge` must separate every good/bad reference;
`judgeChange` hides uncalibrated results. There is no composite score. A best model
requires separated success intervals. Blind current-request comparisons keep
proposals/preferences local and require explicit acceptance. Each valid blind proposal can be saved as a private local case with exact-document checks and checked good/bad references. Saved cases are opt-in for subsequent runs and excluded from report export.

```sh
node tools/ai-eval.mjs --adapter ./trusted-app-adapter.mjs --suite suite.json \
  --models openai:MODEL-A,openai:MODEL-B --output report.json --mock
# Manual only, with securely loaded provider env vars:
node tools/ai-eval.mjs --adapter ./trusted-app-adapter.mjs --suite suite.json \
  --models openai:MODEL-A,openai:MODEL-B --output report.json --live --budget 1
```

The trusted adapter exports `config`, `type` and optional `models`. `--log` changes
the prefixed resume/budget log (default `.ai-local/ai-eval-state.json`). CI uses only
mock responses. Manual `tools/ai-live.mjs --budget 10` uses synthetic documents,
keeps a persistent total ledger and never logs keys/provider bodies.


## Omitting the browser engine

From 0.4.1, sites without local browser models can use
`vendor-sync.mjs --without-browser-engine`. The pin retains the exact published
manifest and omits only its declared wllama files. Verify with
`vendor-sync.mjs --check --published --without-browser-engine`, and pass
`--without-browser-engine` to the kit static checker. Local browser routes must
be disabled; a deployment using only AI hosts can also omit the local engine.
The default pin still includes the engine. Pinned older releases are unchanged.

The independent `kit-check.yml` workflow on the immutable workflow revision
that adds this option accepts `without-browser-engine: true`. Older `@v2`
verifiers require full pins. Use the recorded workflow revision from the source
repository's rollout receipt; never move an existing workflow tag. No file
outside the published optional-engine list may be missing or edited.
