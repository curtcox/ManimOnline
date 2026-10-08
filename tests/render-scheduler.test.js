const { test } = require('node:test');
const assert = require('node:assert/strict');
const Scheduler = require('../src/render-scheduler.js');

function setup() {
  let now = 0, id = 0;
  const timers = new Map(), calls = [];
  const scheduler = new Scheduler({
    detect: () => calls.push(['detect', now]), render: () => calls.push(['render', now]),
    timers: { setTimeout: (callback, delay) => { timers.set(++id, { callback, at: now + delay }); return id; }, clearTimeout: id => timers.delete(id) }
  });
  const advance = time => {
    while (true) {
      const next = [...timers].filter(([, timer]) => timer.at <= time).sort((a, b) => a[1].at - b[1].at)[0];
      if (!next) break;
      timers.delete(next[0]); now = next[1].at; next[1].callback();
    }
    now = time;
  };
  return { scheduler, timers, calls, advance };
}

test('typing refreshes detection after 300ms and renders only after one second of quiet', () => {
  const f = setup();
  f.scheduler.schedule(); f.advance(200); f.scheduler.schedule();
  f.advance(499); assert.deepEqual(f.calls, []);
  f.advance(500); assert.deepEqual(f.calls, [['detect', 500]]);
  f.advance(1100); f.scheduler.schedule(); f.advance(2100);
  assert.deepEqual(f.calls, [['detect', 500], ['detect', 1400], ['render', 2100]]);
});

test('explicit renders cancel all queued work, even callbacks already removed from the timer queue', () => {
  const f = setup();
  f.scheduler.schedule();
  const queued = [...f.timers.values()].map(timer => timer.callback);
  f.scheduler.cancel(); queued.forEach(callback => callback()); f.advance(1000);
  assert.deepEqual(f.calls, []);
});

test('scene edits replace pending source renders without an extra detection pass', () => {
  const f = setup();
  f.scheduler.schedule(); f.advance(100); f.scheduler.schedule({ detect: false });
  f.advance(1100);
  assert.deepEqual(f.calls, [['render', 1100]]);
});
