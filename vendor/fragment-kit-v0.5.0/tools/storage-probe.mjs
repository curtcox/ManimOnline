#!/usr/bin/env node
// Measures browser storage candidates for the local library. Evidence only; ships no runtime code.
import http from 'node:http';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { args } from './lib.mjs';

const options = args();
const browsers = (options.browsers ?? 'chromium,firefox,webkit').split(',');
const docBytes = Number(options['doc-bytes'] ?? 5 * 1024 * 1024), count = Number(options.count ?? 8);

async function probe({ docBytes, count }) {
  // Random printable text: Chromium compresses stored values, so repeated text understates usage.
  const out = {}, doc = (() => { const chunk = new Uint8Array(65536); let text = ''; while (text.length < docBytes) { crypto.getRandomValues(chunk); text += String.fromCharCode(...chunk.map(b => 33 + b % 90)); } return text.slice(0, docBytes); })();
  const time = async work => { const start = performance.now(); const value = await work(); return { value, ms: Math.round(performance.now() - start) }; };
  const fail = error => ({ error: `${error?.name ?? 'Error'}: ${error?.message ?? error}` });
  try { const e = await navigator.storage.estimate(); out.estimate = { quota: e.quota, usage: e.usage }; } catch (error) { out.estimate = fail(error); }
  try { out.persisted = await navigator.storage.persisted(); } catch (error) { out.persisted = fail(error); }
  out.localStorage = await (async () => {
    try {
      localStorage.clear(); let low = 0, high = 64 * 1024 * 1024, errorName = null;
      while (high - low > 65536) {
        const mid = Math.floor((low + high) / 2);
        try { localStorage.setItem('probe', 'x'.repeat(mid)); low = mid; } catch (error) { high = mid; errorName = error.name; }
      }
      localStorage.clear();
      const write = await time(() => localStorage.setItem('probe', doc.slice(0, Math.min(docBytes, low))));
      localStorage.clear();
      return { maxChars: low, quotaError: errorName, writeMs: write.ms };
    } catch (error) { return fail(error); }
  })();
  out.indexedDB = await (async () => {
    try {
      await new Promise(resolve => { const r = indexedDB.deleteDatabase('probe:library'); r.onsuccess = r.onerror = r.onblocked = resolve; });
      const db = await new Promise((resolve, reject) => {
        const request = indexedDB.open('probe:library', 1);
        request.onupgradeneeded = () => { request.result.createObjectStore('blobs'); request.result.createObjectStore('meta'); };
        request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error);
      });
      const run = (stores, mode, work) => new Promise((resolve, reject) => {
        const tx = db.transaction(stores, mode); let value;
        Promise.resolve(work(tx)).then(result => { value = result; }, reject);
        tx.oncomplete = () => resolve(value); tx.onabort = () => reject(tx.error ?? new DOMException('Transaction aborted', 'AbortError'));
      });
      const get = (tx, store, key) => new Promise((resolve, reject) => { const r = tx.objectStore(store).get(key); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); });
      const write = await time(async () => { for (let i = 0; i < count; i++) await run(['blobs'], 'readwrite', tx => { tx.objectStore('blobs').put(doc, 'd' + i); }); });
      const read = await time(() => run(['blobs'], 'readonly', async tx => { let total = 0; for (let i = 0; i < count; i++) total += (await get(tx, 'blobs', 'd' + i)).length; return total; }));
      let aborted;
      try { await run(['meta', 'blobs'], 'readwrite', tx => { tx.objectStore('meta').put('partial', 'a'); tx.objectStore('blobs').put('partial', 'b'); tx.abort(); }); aborted = 'not aborted'; }
      catch (error) { aborted = error.name; }
      const leftover = await run(['meta', 'blobs'], 'readonly', async tx => [await get(tx, 'meta', 'a'), await get(tx, 'blobs', 'b')]);
      db.close();
      return { writeMs: write.ms, readMs: read.ms, readBytes: read.value, abortError: aborted, atomic: leftover.every(value => value === undefined) };
    } catch (error) { return fail(error); }
  })();
  out.opfs = await (async () => {
    try {
      const root = await navigator.storage.getDirectory(), handle = await root.getFileHandle('probe', { create: true });
      const result = { mainThreadCreateWritable: typeof handle.createWritable === 'function', syncAccessHandle: typeof handle.createSyncAccessHandle === 'function' };
      if (result.mainThreadCreateWritable) {
        const write = await time(async () => { const stream = await handle.createWritable(); await stream.write(doc); await stream.close(); });
        const read = await time(async () => (await (await handle.getFile()).text()).length);
        Object.assign(result, { writeMs: write.ms, readMs: read.ms, readBytes: read.value });
      }
      await root.removeEntry('probe'); return result;
    } catch (error) { return fail(error); }
  })();
  out.cacheAPI = await (async () => {
    try {
      const cache = await caches.open('probe:library');
      const write = await time(() => cache.put('/probe', new Response(doc)));
      const read = await time(async () => (await (await cache.match('/probe')).text()).length);
      await caches.delete('probe:library'); return { writeMs: write.ms, readMs: read.ms, readBytes: read.value };
    } catch (error) { return fail(error); }
  })();
  out.broadcastChannel = typeof BroadcastChannel === 'function';
  out.webLocks = typeof navigator.locks?.request === 'function';
  try { out.estimateAfter = (await navigator.storage.estimate()).usage; } catch { /* reported above */ }
  return out;
}

// Two tabs increment one counter with read-modify-write transactions and notify each other.
async function tab({ name, rounds }) {
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open('probe:tabs', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('meta');
    request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error);
  });
  const channel = new BroadcastChannel('probe:library'); let heard = 0;
  channel.onmessage = event => { if (event.data !== name) heard++; };
  for (let i = 0; i < rounds; i++) {
    await new Promise((resolve, reject) => {
      const tx = db.transaction('meta', 'readwrite'), store = tx.objectStore('meta'), request = store.get('counter');
      request.onsuccess = () => store.put((request.result ?? 0) + 1, 'counter');
      tx.oncomplete = resolve; tx.onerror = () => reject(tx.error);
    });
    channel.postMessage(name);
    await new Promise(resolve => setTimeout(resolve, 1));
  }
  await new Promise(resolve => setTimeout(resolve, 200));
  const counter = await new Promise(resolve => { const r = db.transaction('meta').objectStore('meta').get('counter'); r.onsuccess = () => resolve(r.result); });
  channel.close(); db.close(); return { heard, counter };
}

async function quota(docBytes) {
  const doc = (() => { const chunk = new Uint8Array(65536); let text = ''; while (text.length < docBytes) { crypto.getRandomValues(chunk); text += String.fromCharCode(...chunk.map(b => 33 + b % 90)); } return text.slice(0, docBytes); })();
  const db = await new Promise((resolve, reject) => { const r = indexedDB.open('probe:quota', 1); r.onupgradeneeded = () => r.result.createObjectStore('blobs'); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); });
  for (let i = 0; i < 10; i++) {
    const outcome = await new Promise(resolve => { const tx = db.transaction('blobs', 'readwrite'); tx.objectStore('blobs').put(doc, i); tx.oncomplete = () => resolve(null); tx.onabort = () => resolve(`${tx.error?.name}: ${tx.error?.message}`); });
    if (outcome) { db.close(); return { failedAtWrite: i, error: outcome }; }
  }
  db.close(); return { failedAtWrite: null };
}

async function mark(value) {
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open('probe:persist', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('meta');
    request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error);
  });
  const result = await new Promise((resolve, reject) => {
    const tx = db.transaction('meta', value ? 'readwrite' : 'readonly'), store = tx.objectStore('meta');
    if (value) store.put(value, 'marker');
    const request = store.get('marker'); request.onsuccess = () => resolve(request.result); tx.onerror = () => reject(tx.error);
  });
  if (value) localStorage.setItem('probe:marker', value);
  db.close(); return { indexedDB: result ?? null, localStorage: localStorage.getItem('probe:marker') };
}

const server = http.createServer((_, response) => { response.writeHead(200, { 'Content-Type': 'text/html' }); response.end('<!doctype html><title>storage probe</title>'); });
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}/`;
const playwright = await import('@playwright/test');
const report = { date: new Date().toISOString(), platform: `${os.platform()} ${os.release()}`, docBytes, count, browsers: {} };
for (const name of browsers) {
  const type = playwright[name], result = report.browsers[name] = {};
  try {
    const browser = await type.launch();
    result.version = browser.version();
    const context = await browser.newContext(), page = await context.newPage();
    await page.goto(origin);
    result.ephemeral = await page.evaluate(probe, { docBytes, count });
    const pages = [page, await context.newPage()]; await pages[1].goto(origin);
    result.twoTabs = await Promise.all(pages.map((p, i) => p.evaluate(tab, { name: 'tab' + i, rounds: 50 })));
    await context.close(); await browser.close();
    const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'fk-probe-'));
    try {
      let persistent = await type.launchPersistentContext(dir);
      let p = persistent.pages()[0] ?? await persistent.newPage(); await p.goto(origin);
      const written = await p.evaluate(mark, 'kept');
      await persistent.close();
      persistent = await type.launchPersistentContext(dir); p = persistent.pages()[0] ?? await persistent.newPage(); await p.goto(origin);
      result.restart = { written, afterRestart: await p.evaluate(mark, null), persisted: await p.evaluate(() => navigator.storage.persisted()) };
      result.persistentProbe = await p.evaluate(probe, { docBytes, count });
      await persistent.close();
    } finally { await fs.rm(dir, { recursive: true, force: true }); }
    if (name === 'chromium') {
      // Force a small quota on a fresh profile to observe how a full origin reports write failures.
      const fresh = await fs.mkdtemp(path.join(os.tmpdir(), 'fk-probe-'));
      try {
        const persistent = await type.launchPersistentContext(fresh), p = persistent.pages()[0] ?? await persistent.newPage(); await p.goto(origin);
        await (await persistent.newCDPSession(p)).send('Storage.overrideQuotaForOrigin', { origin: origin.slice(0, -1), quotaSize: 12 * 1024 * 1024 });
        result.quotaFailure = await p.evaluate(quota, docBytes);
        await persistent.close();
      } finally { await fs.rm(fresh, { recursive: true, force: true }); }
    }
  } catch (error) { result.error = error.message.split('\n')[0]; }
}
server.close();
console.log(JSON.stringify(report, null, 2));
