const { test } = require('node:test');
const assert = require('node:assert/strict');
const { ShareLinks, ShareClient } = require('../src/share-links.js');
const snapshot = ShareLinks.build({ url: 'https://example.test/ManimOnline/', code: 'from manim import *', mode: 'manim', type: 'manim', scene: 'Second' });

test('links preserve latest Unicode source, selected scene, and renderer without stale input parameters', () => {
  const code = 'from manim import *\n# π + λ\nclass Second(Scene): pass';
  const links = ShareLinks.build({ url: 'https://example.test/ManimOnline/?raw=old&compressed=older&url=external&type=dot&scene=First&engine=neato&format=png#old', code, mode: 'manim', type: 'manim', scene: ' Second ', compress: text => { assert.equal(text, code); return 'encoded+text'; } });
  const long = new URL(links.long), fallback = new URL(links.fallback);
  assert.equal(decodeURIComponent(long.hash.slice(1)), code);
  assert.equal(long.searchParams.get('scene'), 'Second');
  assert.equal(long.searchParams.get('type'), 'manim');
  for (const key of ['raw', 'compressed', 'url', 'engine', 'format']) assert.equal(long.searchParams.has(key), false, key);
  assert.equal(fallback.searchParams.get('compressed'), 'encoded+text');
  assert.equal(fallback.hash, '');
  assert.ok(Object.isFrozen(links));
});

test('Auto clears old overrides and DOT links preserve engine and format', () => {
  const links = ShareLinks.build({ url: 'https://example.test/?type=manim&scene=First', code: 'digraph{a->b}', type: 'graphviz', engine: 'neato', format: 'png' });
  const url = new URL(links.long);
  assert.equal(url.searchParams.has('type'), false);
  assert.equal(url.searchParams.has('scene'), false);
  assert.equal(url.searchParams.get('engine'), 'neato');
  assert.equal(url.searchParams.get('format'), 'png');
  assert.equal(new URL(ShareLinks.build({url: links.long, code: 'x', mode: 'graphviz', type: 'graphviz'}).long).searchParams.get('type'), 'dot');
});

test('unavailable or failed compression still produces a usable source link', () => {
  for (const compress of [undefined, () => null, () => '', () => { throw new Error('Missing compressor'); }]) {
    const links = ShareLinks.build({ url: 'https://example.test/?compressed=old', code: 'π', compress });
    assert.equal(links.fallback, links.long);
    assert.equal(decodeURIComponent(new URL(links.fallback).hash.slice(1)), 'π');
  }
});

test('shortening uses captured source and validates successful service response', async () => {
  const client = new ShareClient({ fetchLink: async (url, options) => {
    const endpoint = new URL(new URL(url).searchParams.get('url'));
    assert.equal(endpoint.searchParams.get('url'), snapshot.long);
    assert.ok(options.signal instanceof AbortSignal);
    return { ok: true, json: async () => ({ contents: ' https://is.gd/abc123\n' }) };
  }});
  assert.deepEqual(await client.shorten(snapshot), { url: 'https://is.gd/abc123', shortened: true });
  assert.equal(client.pending, null);
});

test('HTTP, connection, body, and invalid short-link responses retain a source link', async () => {
  const responses = [null, {ok:false}, {ok:true,json:async()=>{throw new Error('JSON');}},
    ...[undefined, 'Error: rate limit', 'javascript:alert(1)', 'https://evil.test/abc', 'https://is.gd/a?q=x', 'http://is.gd/abc', 'https://user@is.gd/abc'].map(contents => ({ok:true,json:async()=>({contents})}))];
  for (const response of responses) {
    const client = new ShareClient({ fetchLink: async () => { if (!response) throw new Error('Offline'); return response; } });
    assert.deepEqual(await client.shorten(snapshot), { url: snapshot.fallback, shortened: false });
  }
});

test('deadline covers stalled network and response body even when abort is ignored', async () => {
  for (const fetchLink of [() => new Promise(()=>{}), async () => ({ok:true,json:()=>new Promise(()=>{})})]) {
    let expire, signal, cleared;
    const client = new ShareClient({ fetchLink: (url, options) => {signal=options.signal;return fetchLink();},
      timers: {setTimeout: callback=>{expire=callback;return 1;},clearTimeout: id=>cleared=id} });
    const pending = client.shorten(snapshot);
    expire();
    assert.deepEqual(await pending, {url:snapshot.fallback,shortened:false});
    assert.ok(signal.aborted);
    assert.equal(cleared, 1);
  }
});

test('edits and newer requests discard stale short links', async () => {
  const completions = [];
  const client = new ShareClient({ fetchLink: () => new Promise(resolve=>completions.push(resolve)) });
  const first = client.shorten(snapshot);
  client.cancel();
  assert.equal(await first, null);
  const second = client.shorten(snapshot);
  const third = client.shorten(snapshot);
  assert.equal(await second, null);
  completions[0]({ok:true,json:async()=>({contents:'https://is.gd/old'})});
  completions[2]({ok:true,json:async()=>({contents:'https://is.gd/current'})});
  assert.deepEqual(await third, {url:'https://is.gd/current',shortened:true});
});
