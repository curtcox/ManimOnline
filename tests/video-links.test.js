const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { VideoLinks } = require('../src/video-links.js');
const { ExampleCatalog } = require('../src/examples.js');
const OfflineAssets = require('../offline-assets.js');

const series = path.join(__dirname, '..', 'video-series');
const meta = JSON.parse(fs.readFileSync(path.join(series, 'youtube', 'episodes.json'), 'utf8'));
const qrLinks = JSON.parse(fs.readFileSync(path.join(series, 'qr-links.json'), 'utf8'));
const watch = /^https:\/\/www\.youtube\.com\/watch\?v=([\w-]{11})&list=([\w-]+)(?:&t=(\d+)s)?$/;

test('every episode links to its published video in the playlist', () => {
  assert.equal(VideoLinks.playlist, `https://www.youtube.com/playlist?list=${meta.series.playlist_id}`);
  assert.deepEqual(VideoLinks.episodes.map(e => e.episode), [...Array(13).keys()]);
  for (const { episode, title, url } of VideoLinks.episodes) {
    const [, id, list, time] = url.match(watch);
    assert.equal(id, meta.episodes[episode].video_id);
    assert.equal(list, meta.series.playlist_id);
    assert.equal(time, undefined);
    assert.equal(title, meta.episodes[episode].title);
  }
});

test('every QR snippet links to the chapter of its own episode', () => {
  assert.deepEqual(Object.keys(VideoLinks.snippets).sort(), qrLinks.map(row => row.cid).sort());
  for (const row of qrLinks) {
    const entry = VideoLinks.snippets[row.cid];
    assert.equal(entry.qr, row.id);
    assert.equal(entry.episode, row.episode);
    assert.equal(entry.url.match(watch)[1], meta.episodes[row.episode].video_id);
    assert.ok(entry.chapter);
  }
});

test('gallery links name existing samples and the episodes that map them', () => {
  const ids = new Set(ExampleCatalog.map(example => example.id));
  const mapped = Object.entries(meta.episodes).flatMap(([n, e]) => Object.keys(e.gallery || {}).map(id => [id, +n]));
  assert.equal(Object.keys(VideoLinks.examples).length, mapped.length);
  for (const [id, episode] of mapped) {
    assert.ok(ids.has(id), id);
    assert.equal(VideoLinks.examples[id].episode, episode);
    assert.equal(VideoLinks.examples[id].url.match(watch)[1], meta.episodes[episode].video_id);
  }
});

test('the link data is cached for offline use', () => {
  assert.ok(OfflineAssets.local.includes('src/video-links.js'));
});
