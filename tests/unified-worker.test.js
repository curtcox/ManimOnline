const test = require('node:test');
const assert = require('node:assert/strict');

// The worker installs a message handler on load; give it a stand-in global scope.
globalThis.self = {};
const { expandPooledScene } = require('../src/unified-worker.js');

test('pooled scenes expand into shared ordinary frames', () => {
  const curves = [[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]];
  const scene = expandPooledScene({
    fps: 15,
    pool: [curves, { type: 'bezierpath', curves: { $pool: 0 }, draw_progress: 0.5 },
           { type: 'bezierpath', curves: { $pool: 0 }, draw_progress: 1 },
           { type: 'vgroup', children: [1, 2] }],
    frames: [{ mobjects: [3], camera: {} }, { mobjects: [2, 3], camera: {} }]
  });
  assert.equal(scene.pool, undefined);
  assert.equal(scene.fps, 15);
  const group = scene.frames[0].mobjects[0];
  assert.deepEqual(group.children.map(c => c.draw_progress), [0.5, 1]);
  assert.deepEqual(group.children[0].curves, curves);
  // Repeated snapshots are the same object, which structured cloning preserves.
  assert.equal(scene.frames[1].mobjects[1], group);
  assert.equal(scene.frames[1].mobjects[0], group.children[1]);
  assert.equal(group.children[0].curves, group.children[1].curves);
});

test('plain scenes pass through and invalid pool references are rejected', () => {
  const plain = { frames: [{ mobjects: [{ type: 'circle' }] }] };
  assert.equal(expandPooledScene(plain), plain);
  for (const bad of [
    { pool: [{ type: 'vgroup', children: [0] }], frames: [] },
    { pool: [{ type: 'line', curves: { $pool: 3 } }], frames: [] },
    { pool: [{ type: 'line' }], frames: [{ mobjects: [1] }] },
    { pool: [{ type: 'line' }], frames: [{ mobjects: ['0'] }] }
  ]) assert.throws(() => expandPooledScene(bad), /Invalid pooled frame data/);
});

test('flat XY pool entries expand to planar points and grouped curves', () => {
  const scene = expandPooledScene({
    pool: [{ $xy: [0, 0, 1, 0, 1, 1, 0, 1], k: 4 }, { $xy: [2, 3, 4, 5] },
           { type: 'bezierpath', curves: { $pool: 0 }, vertices: { $pool: 1 } }],
    frames: [{ mobjects: [2], camera: {} }]
  });
  const node = scene.frames[0].mobjects[0];
  assert.deepEqual(node.curves, [[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]]);
  assert.deepEqual(node.vertices, [[2, 3, 0], [4, 5, 0]]);
  for (const bad of [{ $xy: [1, 2, 3] }, { $xy: [0, 0, 1, 1], k: 3 }, { $xy: [0, 'x'] }]) {
    assert.throws(() => expandPooledScene({ pool: [bad], frames: [] }), /Invalid pooled/);
  }
});

test('flat XYZ entries and pooled bases expand to full nodes', () => {
  const scene = expandPooledScene({
    pool: [{ $xyz: [0, 0, 1, 1, 0, 2, 1, 1, 3, 0, 1, 4], k: 4 }, { type: 'bezierpath', fill_color: '#FF0000' },
           { $base: 1, curves: { $pool: 0 }, children: [] }, { $base: 1, curves: { $pool: 0 }, children: [] }],
    frames: [{ mobjects: [2, 3], camera: {} }]
  });
  const [first, second] = scene.frames[0].mobjects;
  assert.deepEqual(first, { type: 'bezierpath', fill_color: '#FF0000', curves: [[[0, 0, 1], [1, 0, 2], [1, 1, 3], [0, 1, 4]]], children: [] });
  assert.equal(first.curves, second.curves);
  for (const bad of [{ $xyz: [1, 2, 3, 4] }, { $xyz: [0, 0, 0, 1, 1, 1], k: 4 }]) {
    assert.throws(() => expandPooledScene({ pool: [bad], frames: [] }), /Invalid pooled/);
  }
  assert.throws(() => expandPooledScene({ pool: [{ $base: 0 }], frames: [] }), /Invalid pooled/);
  assert.throws(() => expandPooledScene({ pool: [[1], { $base: 0 }], frames: [] }), /Invalid pooled/);
});

test('pooled camera background images expand to their data URI', () => {
  const uri = 'data:image/png;base64,iVBORw0KGgo=';
  const scene = expandPooledScene({
    pool: [uri, { type: 'circle' }],
    frames: [{ mobjects: [1], camera: { background_image: { $pool: 0 } } }, { mobjects: [], camera: {} }]
  });
  assert.equal(scene.frames[0].camera.background_image, uri);
  assert.equal(scene.frames[1].camera.background_image, undefined);
  assert.throws(() => expandPooledScene({ pool: [{ type: 'circle' }], frames: [{ mobjects: [], camera: { background_image: { $pool: 0 } } }] }),
    /Invalid pooled frame data/);
});
