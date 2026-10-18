const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup(frames = 31) {
  const callbacks = new Map();
  let nextId = 0;
  const makeClassList = () => {
    const names = new Set();
    return { contains: name => names.has(name), toggle(name, on = !names.has(name)) { if (on) names.add(name); else names.delete(name); return on; } };
  };
  const listeners = new Map();
  const makeElement = () => ({
    children: [], attributes: {}, classList: makeClassList(), style: { setProperty() {} }, isConnected: true,
    append(...children) { this.children.push(...children); },
    appendChild(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    setAttribute(name, value) { this.attributes[name] = value; },
    remove() { this.removed = true; }
  });
  const context = {
    window: {},
    document: {
      createElement: makeElement, documentElement: makeElement(), fullscreenElement: null, fullscreenEnabled: false,
      addEventListener(type, listener) { listeners.set(type, [...(listeners.get(type) || []), listener]); },
      removeEventListener(type, listener) { listeners.set(type, (listeners.get(type) || []).filter(other => other !== listener)); }
    },
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
  return { player, displayed, listeners, document: context.document, tick(now) {
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

test('full screen falls back to filling the window and Escape or destroy undo it', () => {
  const { player, listeners, document } = setup();
  assert.equal(player.fullButton.attributes['aria-label'], 'Full screen');
  player.toggleFullscreen();
  assert.ok(player.root.classList.contains('manim-player-full'));
  assert.ok(document.documentElement.classList.contains('manim-player-filling'));
  assert.equal(player.fullButton.attributes['aria-label'], 'Exit full screen');
  assert.equal(player.fullButton.attributes['aria-pressed'], 'true');
  player.setWindowFill(true);
  assert.equal(listeners.get('keydown').length, 1, 'repeated requests add one Escape listener');
  listeners.get('keydown')[0]({ key: 'Escape' });
  assert.ok(!player.root.classList.contains('manim-player-full'));
  assert.equal(listeners.get('keydown').length, 0);
  player.toggleFullscreen();
  player.destroy();
  assert.ok(!document.documentElement.classList.contains('manim-player-filling'));
  assert.equal(listeners.get('keydown').length, 0);
  assert.equal(listeners.get('fullscreenchange').length, 0);
});
