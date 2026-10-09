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
