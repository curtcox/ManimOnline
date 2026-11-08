# Development and distribution

```
npm ci
npm test
npx playwright install chromium firefox webkit
npm run demo
npm run check
npm run test:browser
npm run serve
```

Open http://127.0.0.1:8000/demo/. `npm run demo` regenerates this repository's
unreleased pinned consumer, cover images and offline manifest. It never rewrites
other consumer directories. Once v0.3.4 is published, bump the version and demo
paths before preparing another runtime release.

`vendor-sync.mjs sync --target APP --to vX.Y.Z` copies a local pinned source or
downloads an exact published release. `--check --target APP` validates every
hash and rejects missing/extra files. CI adds `--published` to compare the entire
manifest against the GitHub Release, preventing edited bytes plus edited hashes
from passing. Releases contain a tarball, manifest and SHA256SUMS; prepare them
with `npm run release:prepare`. Preparation does not tag or publish.

`offline-assets.mjs --config offline.config.json [--check]` hashes the complete
ship list and builds an app-prefixed version. Never include the output manifest
in its own inputs. CDN fallback bytes must match the remote asset's hash.

`render-gallery.mjs --config gallery.config.mjs [--check]` accepts a catalog,
baseURL, output directory, dependency files and `renderCover(page,example)` hook.
The hook returns a locator or page for capture. Check mode validates renderer,
dependencies, catalog entries and PNG hashes without launching a browser.

`check.mjs` validates runtime syntax, CSP-safe code and all vendor pins, including
the SDK's independently recorded upstream SRI. `--config app-config.json` adds
app prefix/viewport/CSP/resource checks; a `sandboxBootstrapHash` field verifies
the SDK bootstrap hash. Static checks complement the runtime layout contracts.

Reusable workflows accept consumer commands/config paths; Actions and npm
dependencies are pinned. Caller repositories retain their own engines and build
steps. Release workflows run tests and package on exact semver tags. Pages stages
only docs/demo assets and verifies a marker after deployment. Configure GitHub
Pages to deploy via Actions in repository settings before its first run.

Consumers running the contracts need `@playwright/test` as a pinned development
dependency, alongside their existing browser runner. Provide an ESM config that
exports the selectors and `build(page,doc,canonical)`, `getDocument(page)`,
`edit(page,source)`, `openMore(page)` hooks used by `testing/contract/adapter.js`.
The default adapter targets Fragment Notes. The HashBin routing fixture is demo
specific; consumer adapters supply `configureHashBin(context,clientId)` to inject
the test configuration. Set `kitURL`, `example`, `tabs`, and `cachePrefix` for the
consumer. Keep service workers blocked for network
mocks; the offline suite explicitly enables them.

Consumer contract adapters can define `getSource(page)`, `getDocument(page)`,
`edit(page,src)`, `isWrittenURL(href)`, `offlineAsset`, and `installHashBinMock(context,source)`.
Ace and other editors should read their actual document model. If the SDK also
provides the execution sandbox, the mock hook must preserve those exports while
replacing only HashBinClient. Legacy writers still pass URL identity contracts.
