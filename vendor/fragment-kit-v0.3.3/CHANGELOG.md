# Changelog

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
