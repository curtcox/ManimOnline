const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createHash } = require('node:crypto');
const { ExampleCatalog, ExampleLoader } = require('../src/examples.js');
const Modl = require('../src/modl.js');

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const response = source => ({ ok: true, text: async () => source });

test('catalog points only to shipped local examples with unique IDs', () => {
  assert.equal(new Set(ExampleCatalog.map(e => e.id)).size, ExampleCatalog.length);
  for (const example of ExampleCatalog) {
    assert.match(example.path, /^examples\/[a-z_]+\.(py|dot|modl)$/);
    const source = fs.readFileSync(path.join(__dirname, '..', example.path), 'utf8');
    if (example.type === 'modl') {
      const diagram = Modl.parse(source);
      assert.deepEqual(diagram.errors, [], example.id);
      assert.ok(diagram.nodes.size > 0 && diagram.edges.length > 0, example.id);
    } else assert.match(source, example.type === 'manim' ? /class \w+\((?:Scene|MovingCameraScene|ZoomedScene|LinearTransformationScene|ThreeDScene)\)/ : /digraph/);
  }
});

test('every gallery sample has a current pre-rendered cover, animation media, and a safe editor link', () => {
  const root = path.join(__dirname, '..');
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'gallery/previews/manifest.json')));
  for (const example of ExampleCatalog) {
    const cover = fs.readFileSync(path.join(root, example.cover));
    assert.equal(cover.subarray(0, 8).toString('hex'), '89504e470d0a1a0a', example.id);
    assert.equal(manifest[example.id].source, createHash('sha256').update(fs.readFileSync(path.join(root, example.path))).digest('hex'), example.id);
    const url = new URL(example.editorURL, 'https://example.test/ManimOnline/');
    assert.equal(url.pathname, '/ManimOnline/');
    assert.equal(url.searchParams.get('example'), example.id);
    if (example.type === 'manim') {
      const video = fs.readFileSync(path.join(root, example.video));
      assert.equal(video.subarray(4, 8).toString(), 'ftyp', example.id);
      assert.ok(video.indexOf(Buffer.from('moov')) < video.indexOf(Buffer.from('mdat')), example.id);
      assert.ok(manifest[example.id].duration > 0, example.id);
    } else assert.equal(example.video, null);
  }
});

test('loading delivers exact source and clears loading state', async () => {
  const events = [];
  const loader = new ExampleLoader({
    fetchSource: async url => { assert.equal(url, 'examples/minimal_scene.py'); return response('source\n'); },
    onLoad: (source, example) => events.push([source, example.id]),
    onStatus: (...args) => events.push(args)
  });
  assert.equal(await loader.load('minimal'), true);
  assert.deepEqual(events, [['Loading example…', true], ['', false], ['source\n', 'minimal']]);
});

test('default fetch is called without binding it to the loader', async () => {
  let loaded, loader;
  const context = vm.createContext({ module: { exports: {} }, fetch: function (url) {
    assert.notEqual(this, loader);
    assert.equal(url, 'examples/minimal_scene.py');
    return Promise.resolve(response('browser source'));
  } });
  vm.runInContext(fs.readFileSync(require.resolve('../src/examples.js'), 'utf8'), context);
  loader = new context.module.exports.ExampleLoader({ onLoad: source => { loaded = source; } });
  assert.equal(await loader.load('minimal'), true);
  assert.equal(loaded, 'browser source');
});

test('new editor changes cancel a response even during body loading', async () => {
  const body = deferred();
  const loader = new ExampleLoader({
    fetchSource: async () => ({ ok: true, text: () => body.promise }),
    onLoad: () => assert.fail('must not replace newer edits')
  });
  const pending = loader.load('minimal');
  await Promise.resolve();
  loader.cancel();
  body.resolve('old source');
  assert.equal(await pending, false);
});

test('latest selection wins and stale errors do not alter current status', async () => {
  const old = deferred();
  const received = [], errors = [];
  const loader = new ExampleLoader({
    fetchSource: url => url.includes('minimal') ? old.promise : Promise.resolve(response('new source')),
    onLoad: source => received.push(source), onError: error => errors.push(error)
  });
  const pending = loader.load('minimal');
  assert.equal(await loader.load('connector'), true);
  old.reject(new Error('stale network failure'));
  assert.equal(await pending, false);
  assert.deepEqual(received, ['new source']);
  assert.deepEqual(errors, []);
});

test('failed requests preserve editor content and report recoverable errors', async () => {
  for (const fetchSource of [async () => ({ ok: false }), async () => { throw new Error('offline'); }]) {
    const errors = [], status = [];
    const loader = new ExampleLoader({ fetchSource,
      onLoad: () => assert.fail('failed source must not be loaded'),
      onError: error => errors.push(error.message), onStatus: (...args) => status.push(args)
    });
    assert.equal(await loader.load('minimal'), false);
    assert.equal(errors.length, 1);
    assert.deepEqual(status.at(-1), ['', false]);
  }
});

test('unknown selections never fetch arbitrary paths', async () => {
  const errors = [];
  const loader = new ExampleLoader({ fetchSource: () => assert.fail('unlisted fetch'),
    onLoad: () => assert.fail('unlisted source'), onError: error => errors.push(error.message) });
  assert.equal(await loader.load('https://example.com/code.py'), false);
  assert.deepEqual(errors, ['Choose an example to load.']);
});
