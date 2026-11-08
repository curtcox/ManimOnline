# Implementation status

This is the historical 0.3.0 release-candidate acceptance snapshot. Current release,
consumer PR, deployment and live acceptance evidence is recorded in
[todo/rollout-status.md](https://github.com/curtcox/Tools-for-pages-with-state-in-URL-fragments/blob/main/todo/rollout-status.md).
The master plan's phase definitions are acceptance criteria, not a record of actions already performed.

Local runtime, documentation, baseline corpora, demo, tooling and workflows are
implemented here. The local acceptance snapshot covers:

| Phase | Local result | Remaining acceptance work |
| --- | --- | --- |
| 0 | Ten committed corpora with source commits, serialized bytes, decoded examples and storage/cache evidence | Expand discovered documentation references into executable cases during each migration |
| 1 | Core unit tests and corpus codec round-trips | Production adapter validation remains app-owned |
| 2 | Verified loads, Publish timing, callbacks, cancellation and stale-load guards | Real registered client approval against the deployed demo |
| 3 | Versions 1–40 at all ECC levels; static image, upload and deterministic camera-frame paths | Physical camera checks |
| 4 | Original drafts and shortener tests ported; recovery and share dialogs | Consumer integration |
| 5 | Install, offline reload, update/activation, corruption detection and failed-repair preservation | Consumer extra-cache integrations |
| 6 | Desktop, 360px, Pixel 7 and iPhone 14 contracts in Chromium/Firefox/WebKit on GitHub Actions | Physical device checks |
| 7 | Published docs, demo and fingerprinted gallery; demo imports a pinned vendored copy | Consumer deployment checks |
| 8 | Reusable workflows, integrity/manifest checks and local release packaging | v0.1.0 published with CI-gated assets; 0.2.0 compatibility work remains unreleased |
| 9 | Migration guide and baseline inputs prepared | All ten consumer branches/PRs, module deletion and deployed-site checks |

The jsQR 1.4.0 original is preserved. A generated, documented derivative fixes
its version-23 alignment table; CI verifies that transformation. Canonical v1
source payloads use JSON strings to distinguish code that resembles JSON documents.
The baseline corpus tests exercise wire formats with explicit adapters; they do
not assert that a consumer has migrated or passed its actual engine tests.

Remote release/tag creation, Pages deployment, and the ten consumer migrations
require published artifacts and separate verified consumer changes. They must
not be marked complete merely because the reusable implementation exists.

## Verified remote baseline (2026-11-04)

[Kit CI at 0a275ac](https://github.com/curtcox/Tools-for-pages-with-state-in-URL-fragments/actions/runs/41900729369)
passed 269 unit tests and 85 browser contracts: Chromium and Pixel 7 (34),
Firefox (17), WebKit and iPhone 14 (34). Firefox ran on Linux; its local macOS
profile-launch problem does not invalidate that successful remote execution.

[Pages deployment](https://github.com/curtcox/Tools-for-pages-with-state-in-URL-fragments/actions/runs/41900729775)
succeeded, including the live marker check. The [demo](https://curtcox.github.io/Tools-for-pages-with-state-in-URL-fragments/demo/)
and [docs](https://curtcox.github.io/Tools-for-pages-with-state-in-URL-fragments/docs/)
are public. The [v0.1.0 release](https://github.com/curtcox/Tools-for-pages-with-state-in-URL-fragments/releases/tag/v0.1.0) is published with its tarball, manifest and SHA-256 sums.

This file is included in immutable release artifacts. Current rollout state is
tracked in `todo/rollout-status.md` in the source repository.

The 0.3.0 candidate adds bounded precache downloads, cache-family preservation,
consumer metadata that participates in manifest versions, and generated CommonJS
manifest support. Local validation passed 272 unit tests and 68 browser checks in
Chromium, WebKit, Pixel 7 and iPhone 14. Remote rollout remains recorded separately.
