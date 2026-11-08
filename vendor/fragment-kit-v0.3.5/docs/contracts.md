# Runtime contracts

Fragment Kit runs as native ES modules, without a build step. Import
`vendor/fragment-kit-v0.3.5/src/index.js`; include `src/ui/kit.css` separately.
Node 22.12+ can also `require()` these modules. Execution engines, editor setup,
document validation and sandbox isolation remain application responsibilities.

## URL identity

`createUrlState({config, type})` exposes `parse`, `build`, `write`, `cancel`,
`scrub`, `link`, and `documents`. `parse(href)` returns an intent with `kind`,
`run`, `view`, `settings` and a `doc`, `cid`, `id` or callback `hash` as applicable.
Invalid explicit URLs throw: consumers display the error and keep the current
document. They must not silently open defaults or drafts.

Precedence: publish callback, CID, versioned fragment, registered legacy fragment,
`src=`/`h1=`, percent-encoded source/document, `doc` query, `compressed` query,
example, default. A consumer resolves examples and then replaces the URL with
`build(doc).href`. `write` debounces `history.replaceState` for 300 ms; call
`cancel` before navigation. Loads and edits must share a consumer revision guard.

Consumers still deploying readers across the fleet pass `legacyWriter(doc,
{url,run,view,compress,documents})` to `createUrlState`. It returns the app's
existing share URL and must include all state and presentation flags. Remove it
only after every consumer has shipped v1 read support for at least a minor release.
The URL passed to this hook has stale source/settings removed.

New links use `#v1.<lz-string URI payload>`. The payload is a version-1
`hashbin-diagram` envelope, or a JSON string containing source if `type.isDefault(doc)` guarantees
all other fields are defaults. Small `run=0` and `view` flags remain in the query.
`build` returns `{href, plain, qrCandidate, long, fallback}`. `scrub` removes old
source/example/OAuth parameters and declared settings, preserving unrelated
query parameters. Passing `{run:false, view, url}` controls presentation/base.

## DocumentType

Provide `type`, `normalize(value)`, `isDefault(value)`, `settingsKeys`, `fileName`
and `contentType`. `normalize` must preserve and validate every app-owned field
and return a document with text `src`. `format`, `version` and `type` are envelope
metadata; place language/format choices within your app-specific object.

Optional `parseLegacy(text)` handles old schemas. `legacyEnvelopeTypes` explicitly
lists legacy `format:type` pairs that overlap the shared envelope (for example
`hashbin-diagram:graphviz`). Unknown types and versions are rejected otherwise.
`legacyReaders` on `createUrlState` are functions `(URL, {documents,decompress,
settings}) => doc | null`; use them for Sheets project snapshots or Manim's
`modlpos` query. Query settings are returned separately; the adapter or consumer
decides how they affect a document. Do not copy wire-test adapters into production:
they intentionally do not contain consumer validation.

All decoded text and envelope serialization default to 5 MiB of UTF-8. The
bounded decoder stops before unbounded expansion; stream reads enforce byte
limits before collecting the response. CID loads verify the six-byte size prefix
and inline bytes (up to 64 bytes) or SHA-512 digest.

## HashBin

Construct `new HashBinStore({config,type})`. `init()` loads the vendored SDK;
an empty client ID disables saving with “HashBin saving needs a registered client
ID.” Never invent a client ID. Transactions use app-prefixed session storage;
credential persistence is disabled. Token APIs are not part of the kit contract.
An explicitly supplied `legacyStorage` is used solely by `retireLegacyTokens()`
to revoke old credentials before removing them.

Prepare a snapshot and call `init()` before the approval button is enabled.
Inside the subsequent click, call `publish(payload,snapshot)` synchronously.
Do not await anything before that call. The SDK opens its popup in that stack;
blocked popups use its redirect/file handoff. A verified CID is recorded only
when the editor fingerprint still matches the saved snapshot. Redirect callbacks
return the snapshot on cancellation as well as success. Original transaction bytes are bounded before decoding and verified against the returned CID; normalized document equality permits older envelope JSON key ordering while rejecting substituted snapshots.

`HashBinPanel` supplies these controls. Its options are `store`, `urlState`,
`getSnapshot`, `getFingerprint`, `onLoad`, `onSaved`, `container`. Call
`cancelLoad()` on edits/navigation. Explicit loads must never ask to replace a
draft. `published(hash)` handles the redirect restoration.

## QR and sharing

`encodeQr(text)` retains the upstream default behavior; optional `{version:1..40,
ecc:'L'|'M'|'Q'|'H'}` supports conformance tests. `qrSvg`, `qrPng`, `qrNotes`
export images/guidance. Dense codes (>20) and oversized links offer HashBin.

`QrScanner.fromCamera(video,{onResult,onError,signal})` asks for camera permission
only when called, throttles to roughly 8 fps, and stops tracks on success/abort.
`fromImage(blob)` decodes upload/paste/drop input. Native BarcodeDetector is used
when supported; jsQR is the offline fallback. Decoded same-app origin **and path**
loads in place; sibling links require an explicit “Open in …” action; other data
is displayed as text with copy. Arbitrary scanned URLs never auto-navigate.

`ShareClient` is the original is.gd-via-AllOrigins client, including its messages,
deadline, cancellation and original-link fallback. `createShareDialog` snapshots
on open and includes copy, shorten, run-on-open and HashBin actions.

## Drafts, storage and rendering

`createStorage({prefix,storage?,kind?})` adds `prefix:` to every key. Reads fail
to null; writes surface quota/permission failures. Pass this facade and a relative
key to `LocalDrafts`, or use the old raw-storage/prefixed-key contract. Do not
double-prefix existing keys during migration. `opened()` marks an explicit URL
load. `save(value,true)` records an edit and keeps prior drafts; `attempt` reports
storage failures. Draft recovery is always an explicit user action.

`RenderScheduler` accepts the template `{detect,render,detectionDelay,renderDelay}`
or asynchronous `{render,onResult,onStatus,delay}` contract. Every edit cancels
timers, increments a revision and aborts prior work. Consumer engines still need
their own worker termination/deadline rules.

## Offline and UI

Generate `offline-assets.js` from an app allowlist with
`node …/tools/offline-assets.mjs --config offline.config.json`. The config needs
`prefix`, `files`, optional pinned `remote` URLs and `cdnFallbacks`. The worker is:

```js
importScripts('offline-assets.js', 'vendor/fragment-kit-v0.3.5/src/offline/sw-core.js');
```

The manifest must load first. Atomic staging downloads and verifies every file
before committing. Every cached response is verified on read. Status counts only
the manifest; app package/voice caches remain separate. Optional
`self.FragmentKitOfflineConfig = {extraCaches,preserveCache,downloadConcurrency,cdnFallbacks,onMessage}` can preserve
extra named caches and handle app messages. `preserveCache(name)` can retain app-owned cache families. Downloads use at most six concurrent requests by default; `downloadConcurrency` accepts 1–16. Manifest config `metadata` carries consumer fields and cannot override reserved kit fields. Metadata participates in the content version, and generated manifests also support Node CommonJS readers. Every cache name must be prefixed.
`OfflineClient` exposes `init`, `status`, `repair`, `update`, `activateUpdate`.
The app decides when a waiting worker activates and when to reload.

`createShell` renders a compact header containing resources, document actions and
status, plus a More dialog. On phones, status moves into More to keep the
workspace available; concise primary run/error feedback remains visible in the
header. Mark a consumer message with `data-fk-primary-status`; legacy `#status`
is also recognized. Resource links stay in More and also appear on wide screens. `compactShell({header,toolbar,status})` moves existing
consumer bars into that layout without replacing their controls or listeners.
The empty domain-notice slot is retained for compatibility; notices are owned by
hashbin.org and must not be injected as overlays on working editors.

`mountMobileTabs` uses real tab/tabpanel semantics and arrow/Home/End keys. Its
existing behavior switches below 768 px and tracks visualViewport height.
Opt into `desktop:true` to show the same controls at every width, including a
Split tab. `select(index)` shows one panel; `select('split')` shows all panels;
`getView()` returns that index or `'split'`. `onChange` receives the panel index,
or `-1` for split, including viewport changes. Initial view is split on desktop
and the first panel on phones; explicit selections survive resizing. Consumers
must reconcile app-owned URL/view state and resize their editors/renderers.
Shared panels expose `data-fk-view="single|split"` on their parent for layout.
Include viewport-fit=cover in the app's HTML.

Dialogs keep their title and Close button above a separately scrolling body.
More uses a compact grid; phone dialogs use the available viewport with safe
areas. Use paired `--fk-text`/`--fk-panel` theme variables for readable controls;
respect reduced motion and 44 px targets.

## Versions

Pin exact runtime versions; upgrades are explicit. Major changes cover URL,
envelope, storage or API breaks. Roll out readers across the fleet before
switching writers. Release tags never move. Reusable major workflow aliases need
an explicit repository release policy; exact immutable version tags work as well.

## Consumer contract fixtures

A testing adapter may provide source(text), returning a valid program containing that text. All source identity, draft, Publish, QR and sharing fixtures use this factory for both writes and expected reads. It defaults to the original text. Structured formats can keep their production validator strict, for example source: text => '# apptron snapshot v1\n-- main.sh --\necho '+JSON.stringify(text)+'\n'. The hook supplies test data only; runtime adapters still validate it normally.
