const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup(frames = 31) {
  const callbacks = new Map();
  let nextId = 0;
  const makeElement = () => ({
    children: [], attributes: {},
    append(...children) { this.children.push(...children); },
    appendChild(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    setAttribute(name, value) { this.attributes[name] = value; },
    remove() { this.removed = true; }
  });
  const context = {
    window: {}, document: { createElement: makeElement },
    performance: { now: () => 1000 },
    requestAnimationFrame: callback => { const id = ++nextId; callbacks.set(id, callback); return id; },
    cancelAnimationFrame: id => callbacks.delete(id),
    ManimRenderer: { render: frame => { assert.ok(frame, 'frame exists'); return makeElement(); } }
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(require.resolve('../src/manim-player.js'), 'utf8'), context);
  const displayed = [];
  const player = new context.window.ManimPlayer(makeElement(), {
    frames: Array.from({ length: frames }, () => ({ mobjects: [] })), fps: 15
  }, svg => displayed.push(svg));
  return { player, displayed, tick(now) {
    const [id, callback] = callbacks.entries().next().value;
    callbacks.delete(id);
    callback(now);
  }, callbacks };
}

test('an early animation callback cannot read a negative frame', () => {
  const { player, tick } = setup();
  tick(999);
  assert.equal(player.index, 0);
  assert.ok(player.playing);
  player.destroy();
});

test('playback follows elapsed time and stops on the final frame', () => {
  const { player, tick, callbacks } = setup();
  tick(2000);
  assert.equal(player.index, 15);
  tick(4000);
  assert.equal(player.index, 30);
  assert.equal(player.playing, false);
  assert.equal(player.playButton.textContent, 'Play');
  assert.equal(callbacks.size, 0);
});

test('seek pauses, redraws and replay restarts', () => {
  const { player, tick, displayed } = setup();
  player.seek.value = '20';
  player.seek.oninput();
  assert.equal(player.index, 20);
  assert.equal(player.playing, false);
  assert.equal(displayed.length, 2);
  player.draw(30);
  player.play();
  assert.equal(player.index, 0);
  tick(1500);
  assert.equal(player.index, 7);
  player.destroy();
  assert.equal(player.root.removed, true);
});

test('a static scene stays on its only frame', () => {
  const { player, callbacks } = setup(1);
  assert.equal(player.playing, false);
  assert.equal(callbacks.size, 0);
});
