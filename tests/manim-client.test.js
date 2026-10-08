const { test } = require('node:test');
const assert = require('node:assert/strict');
const ManimClient = require('../src/manim-client.js');

function setup(timeout = 1000) {
  const workers = [];
  const client = new ManimClient({ timeout, workerFactory: () => {
    const worker = {
      terminate() { this.terminated = true; },
      postMessage(message) { this.message = message; },
      reply(data) { this.onmessage({ data }); }
    };
    workers.push(worker);
    return worker;
  }});
  return { client, workers };
}

test('results are correlated and successful workers are reused', async () => {
  const { client, workers } = setup();
  const pending = client.render('source');
  const worker = workers[0];
  worker.reply({ id: 999, type: 'manim-result', sceneData: { stale: true } });
  assert.ok(client.pending);
  worker.reply({ id: worker.message.id, type: 'manim-result', sceneData: { frames: [] } });
  assert.deepEqual(await pending, { frames: [] });
  const second = client.render('second');
  worker.reply({ id: worker.message.id, type: 'error', error: 'SyntaxError' });
  await assert.rejects(second, /SyntaxError/);
  assert.equal(workers.length, 1);
  client.cancel();
});

test('timeout terminates computation and next render gets a fresh worker', async () => {
  const { client, workers } = setup(10);
  await assert.rejects(client.render('while True: pass'), /timed out/);
  assert.equal(workers[0].terminated, true);
  const retry = client.render('good');
  workers[1].reply({ id: workers[1].message.id, type: 'manim-result', sceneData: {} });
  await retry;
  client.cancel();
});

test('editing cancels work and rejects its promise', async () => {
  const { client, workers } = setup();
  const old = client.render('old');
  const rejected = assert.rejects(old, { name: 'AbortError' });
  const next = client.render('new');
  await rejected;
  assert.ok(workers[0].terminated);
  workers[0].reply({ id: 1, type: 'manim-result', sceneData: { stale: true } });
  workers[1].reply({ id: 2, type: 'manim-result', sceneData: { current: true } });
  assert.deepEqual(await next, { current: true });
  client.cancel();
});

test('worker load failure rejects without waiting for the deadline', async () => {
  const { client, workers } = setup();
  const pending = client.render('source');
  workers[0].onerror({ message: 'network failure', preventDefault() {} });
  await assert.rejects(pending, /network failure/);
  assert.ok(workers[0].terminated);
  assert.equal(client.pending, null);
});

test('events from a terminated worker cannot interrupt its replacement', async () => {
  const { client, workers } = setup();
  const old = client.render('old');
  const rejected = assert.rejects(old, { name: 'AbortError' });
  const next = client.render('new');
  await rejected;
  workers[0].onerror({ message: 'late failure', preventDefault() {} });
  assert.ok(!workers[1].terminated);
  workers[1].reply({ id: 2, type: 'manim-result', sceneData: {} });
  await next;
  client.cancel();
});
