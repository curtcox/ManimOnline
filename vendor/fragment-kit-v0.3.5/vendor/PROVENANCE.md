# Pinned runtime dependencies

No runtime CDN imports. `integrity.json` records SHA-256 and SHA-384 SRI for
every vendored file; `tools/check.mjs` verifies them.

* lz-string 1.5.0 (MIT), https://github.com/pieroxy/lz-string/tree/1.5.0.
  Original UMD copied from GnuPlotOnline/vendor/lz-string.min.js; ESM distribution
  copied byte-for-byte from sheets/vendor/lz-string@1.5.0/index.js. The bounded
  decoder in src/core/compression.js derives from Sheets' bounded decoder.
* jsQR 1.4.0 (Apache-2.0), https://github.com/cozmo/jsQR.
  `jsqr/jsQR.js` and LICENSE-jsQR extracted from
  https://registry.npmjs.org/jsqr/-/jsqr-1.4.0.tgz. The package.json wrapper
  selects CommonJS for Node; browser UMD exports onto self.
  `jsqr/jsQR-fk.js` is a reproducibly generated derivative from the pristine file,
  produced by `node tools/vendor-jsqr.mjs`. It corrects the version-23 alignment
  centers from `[6,30,54,74,102]` to `[6,30,54,78,102]`. The upstream 1.4.0
  table cannot decode the independently encoded version-23/L fixture. The original
  npm bytes are retained, and CI checks the exact documented transformation.
* HashBin SDK v0.4.0, https://hashbin.org/sdk/v0.4.0/hashbin.js.
  Copied byte-for-byte from GnuPlotOnline/vendor/hashbin-sdk-v0.4.0.mjs and
  checked against hashbin.org/frontend/sdk/v0.4.0/integrity.json:
  `sha384-zzmaXw5svWRp0YF//G5ytyeqEowixccM/hHVDth46FnGrIlPS7fPki5vbhv+bWCr`.
  LICENSE-hashbin accompanies the SDK.
* Nayuki byte-mode QR encoder (MIT notice in src/qr/encode.js), and the
  LocalDrafts / ShareClient extraction from GnuPlotOnline. The latter retain
  vendor/LICENSE-graphvizonline for the shared template lineage.

Upgrades require deliberately updating pinned bytes, provenance, integrity,
and the kit version. Keep original distributions unchanged; documented derivatives
must have a reproducible generator and an independent conformance test.
