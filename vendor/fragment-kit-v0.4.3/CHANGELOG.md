# Changelog

## 0.4.3 — 2026-11-08

- Keep the AI-host iframe visible above consumer dialogs even when the shared
  empty-element style is applied. Test the full credential flow with real kit CSS.

## 0.4.2 — 2026-11-08

- Open the AI-host frame in its own accessible connection dialog, above settings
  and consumer drawers. Host sign-in controls remain usable while settings is open.
- Cover the complete settings-to-host-popup credential flow in browser contracts.

## 0.4.1 — 2026-11-08

* Optional engine-free vendor pins retain the published manifest and verify every required file; static checks reject local browser routes without an engine.
* Validate numeric report metrics and privacy/source flags, reject probability metrics from emulated decisions, and label imported reports as self-reported.

## 0.4.0 — 2026-11-08

* Opt-in AI entry point with paste handoff, memory-only direct credentials, hosted provider drivers, typed decisions, conservative spending caps and gateway clients.
* Reviewed, validated changes with stale-edit rebasing, cancellation, undo and one history entry per acceptance.
* Local evaluation suites with checked references, resumable results, Wilson intervals, blind comparison, private saved cases and data-only report export.
* CID-verified model manifests and resumable shards, a pinned wllama engine with worker/network isolation, and static AI-host staging with exact-origin consent.
* Fragment Notes Ask, settings, sample search and comparison surfaces, including 360px layouts. No consumer upgrade, host deployment or release is asserted by this entry.

## 0.3.5

* Compact shared chrome and an adapter for existing application action/status bars.
* Explicit light/dark control colors, denser More menus and an always-visible dialog close control.
* Keep concise primary run/error feedback visible on phones while details live in More.
* Optional desktop workspace tabs with single-panel and split views.

## 0.3.4 — 2026-11-04

* Let consumer contract adapters provide valid source fixtures for structured
  formats such as Apptron txtar, while retaining identity, drafts, Publish,
  QR, sharing and history assertions against the actual document validator.
* Existing adapters use the unchanged plain-text fixtures by default.

## 0.3.3 — 2026-11-04

* Verify Publish redirects against the bounded original transaction bytes and
  compare normalized documents, preserving pre-kit envelope ordering and CIDs.
* Reject snapshots that differ from their saved content; preserve approved and
  cancelled return snapshots through the actual immutable SDK.

## 0.3.2 — 2026-11-04

* Match offline repair's polling deadline to the bounded 60-second acceptance
  window for large, verified consumer precaches on CI runners.

## 0.3.1 — 2026-11-04

* Contract tests scope QR actions to their dialog and allow large consumer
  precaches enough time for verified install and repair.

## 0.3.0 — 2026-11-04

* Offline: bounded download concurrency, consumer cache-preservation hooks,
  app-owned manifest metadata and CommonJS-compatible generated manifests.
* R migration keeps optional package caches separate from app readiness.

## 0.2.0 — 2026-11-04

* Consumer migration: adapter hooks for Ace/editor assertions, legacy link writers,
  URL expectations and offline corruption targets in the shared browser contracts.
* URL writers can retain the consumer's existing format while v1 readers roll out.
* Demo regeneration follows the package version instead of overwriting v0.1.0.

## 0.1.0 — 2026-11-04

* Baseline: pinned source commits, legacy document bytes, decoded documents,
  URL cases, discovered documentation links and storage/cache evidence for ten apps.
* Core: native ES modules, bounded codecs, envelope adapters, verified CIDs,
  canonical fragment links, legacy readers, prefixed storage and revision scheduling.
* HashBin: pinned SDK with upstream SRI, bounded streaming loads, synchronous
  Publish, snapshot callbacks, cancellation messages and stale-load guards.
* QR: Nayuki generation, SVG/PNG downloads, jsQR 1.4.0 fallback, camera/image/
  paste/drop scanning and app/path-aware acceptance policy.
* Drafts/sharing: extracted LocalDrafts and ShareClient with original error messages,
  snapshot share dialog and explicit draft recovery.
* Offline: hash-verified precache, staging before repair, app-scoped cleanup,
  update/status controls and generated manifests.
* Shell/gallery: theme tokens, keyboard-accessible mobile tabs, safe areas,
  Docs/Gallery/GitHub links, gallery filters and fingerprinted covers.
* Tooling: immutable vendor sync, integrity checks, package/release artifacts,
  reusable Actions, Playwright contracts, documentation and a pinned reference app.

Publishing, release tags, deployments and consumer migration status are recorded
separately in docs/implementation-status.md. This entry does not assert remote completion.
