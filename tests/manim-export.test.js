const { test } = require('node:test');
const assert = require('node:assert/strict');
const ManimExport = require('../src/manim-export.js');

function fixture({ contextMissing = false, blobMissing = false, drawError = false } = {}) {
  const calls = [];
  let image, timeout;
  const blob = { type: 'image/png' };
  const context = {
    fillRect: (...args) => calls.push(['background', context.fillStyle, ...args]),
    drawImage: (...args) => { if (drawError) throw new Error('Canvas failed'); calls.push(['draw', ...args]); }
  };
  const canvas = {
    getContext: () => contextMissing ? null : context,
    toBlob: (callback, type) => { calls.push(['encode', type]); callback(blobMissing ? null : blob); }
  };
  const env = {
    Image: class { constructor() { image = this; } },
    Blob,
    URL: { createObjectURL: source => { calls.push(['source', source]); return 'blob:snapshot'; }, revokeObjectURL: url => calls.push(['revoke', url]) },
    document: { createElement: () => canvas },
    setTimeout: callback => { timeout = callback; return 1; },
    clearTimeout: id => calls.push(['clear', id])
  };
  return { env, calls, canvas, blob, get image() { return image; }, expire: () => timeout() };
}

test('PNG rasterizes the snapshot at preview resolution with an opaque black background', async () => {
  const f = fixture();
  const result = ManimExport.png('<svg>π</svg>', 800, 450, f.env);
  assert.equal(f.image.src, 'blob:snapshot');
  f.image.onload();
  assert.equal(await result, f.blob);
  assert.equal(f.canvas.width, 800);
  assert.equal(f.canvas.height, 450);
  assert.deepEqual(f.calls[1], ['background', '#000000', 0, 0, 800, 450]);
  assert.equal(await f.calls[0][1].text(), '<svg>π</svg>');
  assert.deepEqual(f.calls.at(-1), ['revoke', 'blob:snapshot']);
  assert.equal(f.image.onload, null);
});

test('Image failure and timeout release the snapshot URL', async () => {
  for (const action of ['error', 'timeout']) {
    const f = fixture();
    const result = ManimExport.png('<svg/>', 800, 450, f.env);
    if (action === 'error') f.image.onerror(); else f.expire();
    await assert.rejects(result, action === 'error' ? /Could not read/ : /timed out/);
    assert.deepEqual(f.calls.at(-1), ['revoke', 'blob:snapshot']);
  }
});

test('Canvas and encoding failures reject without leaking snapshot URLs', async () => {
  for (const options of [{ contextMissing: true }, { blobMissing: true }, { drawError: true }]) {
    const f = fixture(options);
    const result = ManimExport.png('<svg/>', 800, 450, f.env);
    f.image.onload();
    await assert.rejects(result);
    assert.deepEqual(f.calls.at(-1), ['revoke', 'blob:snapshot']);
  }
});
