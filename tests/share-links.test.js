const { test } = require('node:test');
const assert = require('node:assert/strict');
const { ShareLinks, ShareClient } = require('../src/share-links.js');
const snapshot = ShareLinks.build({ url: 'https://example.test/ManimOnline/', code: 'from manim import *', mode: 'manim', type: 'manim', scene: 'Second' });

test('links preserve latest Unicode source, selected scene, and renderer without stale input parameters', () => {
  const code = 'from manim import *\n# π + λ\nclass Second(Scene): pass';
  const links = ShareLinks.build({ url: 'https://example.test/ManimOnline/?example=minimal&raw=old&compressed=older&url=external&type=dot&scene=First&engine=neato&format=png#old', code, mode: 'manim', type: 'manim', scene: ' Second ', compress: text => { assert.equal(text, code); return 'encoded+text'; } });
  const long = new URL(links.long), fallback = new URL(links.fallback);
  assert.equal(decodeURIComponent(long.hash.slice(1)), code);
  assert.equal(long.searchParams.get('scene'), 'Second');
  assert.equal(long.searchParams.get('type'), 'manim');
  for (const key of ['example', 'raw', 'compressed', 'url', 'engine', 'format']) assert.equal(long.searchParams.has(key), false, key);
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

test('modl shares retain its override and copied node positions', () => {
  const positions = { a: [100,200], b: [300,400] };
  const links = ShareLinks.build({url:'https://example.test/?type=dot&scene=Old&modlpos=old', code:'a -> b', mode:'modl',type:'modl',positions});
  const url = new URL(links.long);
  assert.equal(url.searchParams.get('type'),'modl');
  assert.equal(url.searchParams.has('scene'),false);
  assert.deepEqual(JSON.parse(url.searchParams.get('modlpos')),positions);
  positions.a[0] = 900;
  assert.equal(JSON.parse(url.searchParams.get('modlpos')).a[0],100);
  const dot = new URL(ShareLinks.build({url:links.long,code:'digraph{a->b}',type:'graphviz'}).long);
  assert.equal(dot.searchParams.has('modlpos'),false);
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
    const result = await client.shorten(snapshot);
    assert.equal(result.url, snapshot.fallback);
    assert.equal(result.shortened, false);
    assert.match(result.error.message, /source link above is still ready to copy/);
    assert.match(result.error.message, /Retry|retry|Check|Reconnect|Wait/);
  }
});

test('deadline covers stalled network and response body even when abort is ignored', async () => {
  for (const fetchLink of [() => new Promise(()=>{}), async () => ({ok:true,json:()=>new Promise(()=>{})})]) {
    let expire, signal, cleared;
    const client = new ShareClient({ fetchLink: (url, options) => {signal=options.signal;return fetchLink();},
      timers: {setTimeout: callback=>{expire=callback;return 1;},clearTimeout: id=>cleared=id} });
    const pending = client.shorten(snapshot);
    expire();
    const result = await pending;
    assert.equal(result.url, snapshot.fallback);
    assert.equal(result.shortened, false);
    assert.equal(result.error.code, 'timeout');
    assert.match(result.error.message, /10 seconds.*Retry later/);
    assert.ok(signal.aborted);
    assert.equal(cleared, 1);
  }
});

test('proxy HTTP errors identify the service/status and a concrete recovery step', async () => {
  for (const [status, guidance] of [[522,/Retry later/], [429,/at least one minute/], [414,/too large.*Save to HashBin/], [403,/refused.*Save to HashBin/]]) {
    const client = new ShareClient({fetchLink:async()=>({ok:false,status})});
    const result = await client.shorten(snapshot);
    assert.equal(result.error.code, 'http');
    assert.match(result.error.message,new RegExp(`AllOrigins .*HTTP ${status}`));
    assert.match(result.error.message,guidance);
    assert.equal(result.url,snapshot.fallback);
  }
});

test('is.gd rejection details and upstream failures survive the proxy response', async () => {
  for (const [contents, status, guidance] of [
    ['Error: rate limit exceeded',502,/Wait at least one minute/],
    ['Error: URL too long.',400,/without sending a long URL/],
    ['Error: Invalid original URL',400,/check it/],
    ['Error: Could not generate a short link',400,/check it/],
    ['Error: Maintenance in progress',503,/Retry later/],
    ['Error, database insert failed',200,/problem with the shortening service.*Retry later/]
  ]) {
    const client = new ShareClient({fetchLink:async()=>({ok:true,json:async()=>({contents,status:{http_code:status}})})});
    const result = await client.shorten(snapshot);
    assert.equal(result.error.code,'provider');
    assert.ok(result.error.message.includes(contents.replace(/^Error[:,] /,'')));
    assert.match(result.error.message,guidance);
    assert.ok(!result.error.message.includes('..'));
  }
  for (const contents of ['Service unavailable', undefined, 'a'.repeat(300)]) {
    const client = new ShareClient({fetchLink:async()=>({ok:true,json:async()=>({contents,status:{http_code:503}})})});
    assert.match((await client.shorten(snapshot)).error.message,/is.gd .*HTTP 503/);
  }
});

test('offline and opaque browser failures provide guidance without inventing an HTTP status', async () => {
  let calls=0;
  const offline = new ShareClient({isOnline:()=>false,fetchLink:async()=>{calls++;}});
  const result = await offline.shorten(snapshot);
  assert.equal(calls,0);
  assert.equal(result.error.code,'offline');
  assert.match(result.error.message,/offline.*Reconnect/);
  const blocked = new ShareClient({isOnline:()=>true,fetchLink:async()=>{throw new TypeError('Failed to fetch');}});
  const failure = await blocked.shorten(snapshot);
  assert.equal(failure.error.code,'network');
  assert.match(failure.error.message,/did not provide a response.*content blockers/);
  assert.ok(!failure.error.message.includes('HTTP'));
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
