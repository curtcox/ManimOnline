# Consumer migration

The ten-app order and full checklist remain in `todo/master_plan.md` §7. Start
with GnuPlotOnline, then R, PythonOnline, livelier, AudioOnline, pages,
ManimOnline, apptron, sheets and modl. Each migration needs its own branch/PR,
its actual engine suites and post-deployment checks.

1. Run `node tools/vendor-sync.mjs sync --target ../GnuPlotOnline --to v0.3.3`.
   For a published version, use a released CLI or `--source` pinned checkout.
   The destination is immutable: changed existing bytes are an error.
2. Define app config and a validated DocumentType. Preserve current storage keys.
   Pass a `legacyWriter` to keep writing the existing URL format until the fleet has v1 readers. Retain registered client IDs and the existing SDK sandbox CSP hash.
3. Replace modules with ES imports. `installGlobals({config,type})` in
   `src/globals.js` supplies old names while scripts migrate. Modules execute
   after classic deferred scripts: explicitly sequence the migration entry point.
4. Move app-specific schema code and extra offline caches into app adapters;
   retain sandbox/engine/editor code and optional t256 hooks in the consumer.
5. Add the worker loader and generate its allowlisted offline manifest, including
   the kit's `src` and `vendor` directories. Keep dist/_site staging allowlists.
6. Use the shell or reproduce its resource links, phone targets and dialog rules.
7. Supply a browser contract adapter and run all corpus links, engine-specific
   suites and chromium/firefox/webkit contracts. Never count an unrun engine.
8. Switch workflows only after a published kit tag exists; inspect deployed
   recovery/canonical URLs before deleting the last legacy code.

Baseline caveats discovered during harvesting: Audio uses `hashbin-audio`;
Sheets uses `sheets-document` versions 1–3 and portable `#project=` snapshots;
Manim's envelope `type` names its language; modl's legacy envelope may omit type.
These require adapter readers. The common envelope must not discard those fields.
The corpora contain actual example text and old serializer bytes, source commit
hashes, old decoded documents, and discovered references. Their wire adapters
exercise codecs; they do not substitute for production consumer validators.

Run `npm run corpus:harvest` only when deliberately refreshing baselines from
the adjacent checkouts. Review changed snapshots before committing.
