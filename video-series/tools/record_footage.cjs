#!/usr/bin/env node
/*
Record the series' editor footage from the deployed ManimOnline site, timed to the narration.

Usage (Playwright: `npm install --no-save playwright && npx playwright install chromium`; ffmpeg):
    node video-series/tools/record_footage.cjs [V1.4 ...] [--site URL] [--keep-frames]

Each clip belongs to a segment that shows it with Segment.footage_in; render that segment first
(production/render.py) so build/footage/epNN-S.json says when its screens are on. The script then
drives a real browser (Chromium, 1536 × 864 CSS pixels at 125 % zoom = 1920 × 1080), runs the
clip's actions at the moments the narration names (from the character timings in
build/narration/audio/epNN/S.json), captures every painted frame with the DevTools screencast and
writes build/footage/<clip>.mp4 (60 fps, segment time from <clip>.json's `start`) for render.py
to lay under the scene. Re-run render.py (or `render.py N --stitch`) afterwards.

Nothing here imitates the interface: the page is the real editor. Two things are added on top of
it, because a headless browser draws neither: a mouse pointer (with a ring on clicks) and the soft
yellow outlines that the scripts ask for when a region is named.
*/
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { chromium } = require('playwright');

const SERIES = path.resolve(__dirname, '..');
const FOOTAGE = path.join(SERIES, 'build', 'footage');
const argv = process.argv.slice(2);
const option = name => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : null; };
const SITE = option('--site') || 'https://curtcox.github.io/ManimOnline/';
const KEEP = argv.includes('--keep-frames');
const VIEW = { width: 1536, height: 864 };
const ZOOM = 1.25;
const FPS = 60;

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const snippet = file => fs.readFileSync(path.join(SERIES, 'snippets', file), 'utf8');
const editorUrl = source => `${SITE}?raw=${encodeURIComponent(source)}`;

/** When segment `segment` of `episode` starts saying `words` (as common.phrase_seconds). */
function phrase(episode, segment, words, occurrence = 0) {
  const sidecar = path.join(SERIES, 'build', 'narration', 'audio', `ep${String(episode).padStart(2, '0')}`, `${segment}.json`);
  const { alignment } = JSON.parse(fs.readFileSync(sidecar, 'utf8'));
  const spoken = alignment.characters.join('').toLowerCase();
  let start = -1;
  for (let k = 0; k <= occurrence; k++) {
    start = spoken.indexOf(words.toLowerCase(), start + 1);
    if (start < 0) throw new Error(`${segment}: narration never says ${JSON.stringify(words)}`);
  }
  return alignment.starts[start];
}

// ---------------------------------------------------------------- page additions

function overlays() {
  const install = () => {
    if (document.getElementById('__rec_cursor')) return;
    const cursor = document.createElement('div');
    cursor.id = '__rec_cursor';
    cursor.innerHTML = '<svg width="30" height="30" viewBox="0 0 26 26"><path d="M3 2 L3 21 L8 16.5 L11.5 24 L15 22.5 ' +
      'L11.5 15 L18 15 Z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    const ring = document.createElement('div');
    ring.id = '__rec_ring';
    Object.assign(cursor.style, { position: 'fixed', left: '0', top: '0', zIndex: 2147483647, pointerEvents: 'none',
      transform: `translate(${(window.__recX ?? -60) - 4}px, ${(window.__recY ?? -60) - 3}px)` });
    Object.assign(ring.style, { position: 'fixed', left: '0', top: '0', width: '36px', height: '36px', borderRadius: '50%',
      border: '3px solid rgba(244, 211, 69, 0.95)', opacity: '0', zIndex: 2147483646, pointerEvents: 'none',
      transition: 'opacity 0.45s ease-out, transform 0.45s ease-out', boxSizing: 'border-box' });
    document.documentElement.append(ring, cursor);
  };
  addEventListener('mousemove', event => {
    window.__recX = event.clientX;
    window.__recY = event.clientY;
    const cursor = document.getElementById('__rec_cursor');
    if (cursor) cursor.style.transform = `translate(${event.clientX - 4}px, ${event.clientY - 3}px)`;
  }, true);
  window.__recRing = (x, y) => {
    const ring = document.getElementById('__rec_ring');
    if (!ring) return;
    ring.style.transition = 'none';
    ring.style.opacity = '1';
    ring.style.transform = `translate(${x - 18}px, ${y - 18}px) scale(0.6)`;
    ring.getBoundingClientRect();
    ring.style.transition = 'opacity 0.45s ease-out, transform 0.45s ease-out';
    ring.style.opacity = '0';
    ring.style.transform = `translate(${x - 18}px, ${y - 18}px) scale(1.3)`;
  };
  addEventListener('mousedown', event => window.__recRing(event.clientX, event.clientY), true);
  window.__recOutline = (selectors, on = true, pad = 6) => {
    const id = '__rec_outline_' + selectors.replace(/[^a-z0-9]/gi, '_');
    const old = document.getElementById(id);
    if (!on) {
      if (old) { old.style.opacity = '0'; setTimeout(() => old.remove(), 500); }
      return;
    }
    const rects = selectors.split(',').map(s => document.querySelector(s.trim())).filter(Boolean)
      .map(e => e.getBoundingClientRect());
    if (!rects.length) throw new Error(`no element for ${selectors}`);
    const left = Math.max(3, Math.min(...rects.map(r => r.left)) - pad);
    const top = Math.max(3, Math.min(...rects.map(r => r.top)) - pad);
    const right = Math.min(innerWidth - 3, Math.max(...rects.map(r => r.right)) + pad);
    const bottom = Math.min(innerHeight - 3, Math.max(...rects.map(r => r.bottom)) + pad);
    const box = old || document.createElement('div');
    box.id = id;
    Object.assign(box.style, { position: 'fixed', left: `${left}px`, top: `${top}px`, width: `${right - left}px`,
      height: `${bottom - top}px`, border: '4px solid #F4D345', borderRadius: '10px', boxSizing: 'border-box',
      boxShadow: '0 0 0 3px rgba(244, 211, 69, 0.25), 0 0 26px rgba(244, 211, 69, 0.55)', opacity: '0',
      transition: 'opacity 0.4s', pointerEvents: 'none', zIndex: 2147483645 });
    document.documentElement.append(box);
    requestAnimationFrame(() => requestAnimationFrame(() => { box.style.opacity = '1'; }));
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', install);
  else install();
}

// ---------------------------------------------------------------- capture

/** One recording: screencast frames of whichever page is on show, in segment time. */
class Take {
  constructor(clip) {
    this.clip = clip;
    this.dir = fs.mkdtempSync(path.join(os.tmpdir(), `footage-${clip}-`));
    this.frames = [];
    this.mouse = { x: -60, y: -60 };
  }

  /** Segment time `segmentTime` is now. */
  begin(segmentTime) {
    this.zero = Date.now() / 1000 - segmentTime;
  }

  now() {
    return Date.now() / 1000 - this.zero;
  }

  async until(time) {
    const wait = (time - this.now()) * 1000;
    if (wait > 0) await sleep(wait);
  }

  async show(page) {
    if (this.cdp) await this.cdp.send('Page.stopScreencast').catch(() => {});
    const cdp = await page.context().newCDPSession(page);
    this.cdp = cdp;
    this.page = page;
    cdp.on('Page.screencastFrame', frame => {
      cdp.send('Page.screencastFrameAck', { sessionId: frame.sessionId }).catch(() => {});
      if (cdp !== this.cdp || this.zero === undefined) return;
      const file = path.join(this.dir, `f${String(this.frames.length).padStart(6, '0')}.jpg`);
      fs.writeFileSync(file, Buffer.from(frame.data, 'base64'));
      this.frames.push({ file, time: frame.metadata.timestamp - this.zero });
    });
    await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
    // A pointer that keeps its place when the page changes.
    await page.mouse.move(this.mouse.x, this.mouse.y);
  }

  /** Move the pointer to (x, y) CSS pixels over `seconds`, easing in and out. */
  async glide(x, y, seconds = 0.8) {
    const from = { ...this.mouse };
    const steps = Math.max(1, Math.round(seconds * 60));
    const start = Date.now();
    for (let i = 1; i <= steps; i++) {
      const t = i / steps;
      const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      this.mouse = { x: from.x + (x - from.x) * e, y: from.y + (y - from.y) * e };
      await this.page.mouse.move(this.mouse.x, this.mouse.y);
      const due = start + t * seconds * 1000 - Date.now();
      if (due > 0) await sleep(due);
    }
  }

  async click(x, y, seconds = 0.6) {
    if (x !== undefined) await this.glide(x, y, seconds);
    await this.page.mouse.click(this.mouse.x, this.mouse.y);
  }

  async outline(selectors, on = true) {
    await this.page.evaluate(([s, o]) => window.__recOutline(s, o), [selectors, on]);
  }

  /** Write <clip>.mp4 covering [start, end] of segment time, and <clip>.json. */
  async finish(start, end, extra = {}) {
    if (this.cdp) await this.cdp.send('Page.stopScreencast').catch(() => {});
    this.cdp = null;
    const frames = this.frames.filter(f => f.time <= end);
    const first = frames.findLastIndex(f => f.time <= start);
    const kept = frames.slice(Math.max(first, 0));
    if (!kept.length) throw new Error(`${this.clip}: no frames captured`);
    kept[0] = { ...kept[0], time: start };
    const lines = ['ffconcat version 1.0'];
    kept.forEach((f, i) => {
      const next = i + 1 < kept.length ? kept[i + 1].time : end;
      lines.push(`file '${f.file}'`, `duration ${Math.max(next - f.time, 0.0001).toFixed(6)}`);
    });
    lines.push(`file '${kept[kept.length - 1].file}'`);
    const list = path.join(this.dir, 'frames.txt');
    fs.writeFileSync(list, lines.join('\n') + '\n');
    fs.mkdirSync(FOOTAGE, { recursive: true });
    const output = path.join(FOOTAGE, `${this.clip}.mp4`);
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list,
      '-vf', `fps=${FPS},scale=1920:1080:flags=lanczos,format=yuv420p`, '-t', `${end - start}`,
      '-c:v', 'libx264', '-crf', '14', '-preset', 'slow', output]);
    const meta = { clip: this.clip, start, end, frames: kept.length, site: SITE, recorded: new Date().toISOString(), ...extra };
    fs.writeFileSync(path.join(FOOTAGE, `${this.clip}.json`), JSON.stringify(meta, null, 1) + '\n');
    if (!KEEP) fs.rmSync(this.dir, { recursive: true, force: true });
    console.log(`${output}: ${(end - start).toFixed(1)} s from ${kept.length} captured frames`);
  }
}

// ---------------------------------------------------------------- editor helpers

async function newContext(browser) {
  const context = await browser.newContext({ viewport: VIEW, deviceScaleFactor: ZOOM });
  await context.addInitScript(overlays);
  return context;
}

/** Wait until the editor has Python and is not rendering. */
async function rendered(page, timeout = 90000) {
  await page.waitForFunction(() => {
    const ready = document.getElementById('pyodide-status')?.textContent.includes('ready');
    const busy = /render/i.test(document.getElementById('status')?.textContent || '');
    return ready && !busy && document.querySelector('.manim-controls');
  }, null, { timeout, polling: 100 }).catch(async error => {
    const shown = await page.evaluate(() => document.getElementById('error')?.innerText).catch(() => '');
    throw shown ? new Error(`the editor shows an error:\n${shown}`) : error;
  });
}

/** Wait for a render that starts after an edit, then for it to finish. */
async function rerendered(page, timeout = 90000) {
  await page.waitForFunction(() => /render/i.test(document.getElementById('status')?.textContent || ''), null,
    { timeout: 10000, polling: 50 }).catch(() => {});
  await rendered(page, timeout);
}

/** Centre of `text` (its `occurrence`-th appearance) in the code editor, in CSS pixels. */
async function codePoint(page, text, occurrence = 0, offset = 0.5) {
  return page.evaluate(([text, occurrence, offset]) => {
    const editor = ace.edit('editor');
    const lines = editor.session.getDocument().getAllLines();
    let seen = 0;
    for (let row = 0; row < lines.length; row++) {
      let col = lines[row].indexOf(text);
      while (col >= 0) {
        if (seen++ === occurrence) {
          const at = editor.renderer.textToScreenCoordinates(row, col + text.length * offset);
          return { x: at.pageX, y: at.pageY + editor.renderer.lineHeight / 2 };
        }
        col = lines[row].indexOf(text, col + 1);
      }
    }
    throw new Error(`no ${text} in the editor`);
  }, [text, occurrence, offset]);
}

async function centre(page, selector) {
  const box = await page.locator(selector).first().boundingBox();
  if (!box) throw new Error(`${selector} is not on screen`);
  return { x: box.x + box.width / 2, y: box.y + box.height / 2, box };
}

async function control(page, label) {
  return centre(page, `.manim-controls button:text-is("${label}")`);
}

/** A point on the preview's seek bar, `fraction` of the way along. */
async function seekPoint(page, fraction) {
  const { box } = await centre(page, '.manim-controls input[type=range]');
  const inset = 8;
  return { x: box.x + inset + (box.width - 2 * inset) * fraction, y: box.y + box.height / 2 };
}

async function sourceIs(page, expected) {
  const actual = await page.evaluate(() => ace.edit('editor').getValue());
  if (actual.trim() !== expected.trim()) throw new Error(`editor holds unexpected code:\n${actual}`);
}

// ---------------------------------------------------------------- clips

const SQUARE_TO_CIRCLE = snippet('ep01/01-square-to-circle.py');

const CLIPS = {
  /** 0.2: the Showcase scene plays; RED becomes GREEN on the Star line and the preview shows it. */
  async 'V0.2'(browser, slots) {
    const at = words => phrase(0, '0.2', words);
    const source = snippet('ep00/01-showcase.py');
    const context = await newContext(browser);
    const page = await context.newPage();
    await page.goto(editorUrl(source));
    await rendered(page);
    const take = new Take('V0.2');
    take.mouse = { x: 1150, y: 600 };
    await take.show(page);
    const start = slots[0].start;
    take.begin(start - 0.3);
    await take.click(...Object.values(await control(page, 'Replay')).slice(0, 2), 0.25);
    const red = await codePoint(page, 'Star(color=RED', 0, 0.85);
    await take.until(at('No install') - 1.1);
    await take.glide(red.x, red.y, 0.9);
    await take.until(at('No install'));
    await page.mouse.dblclick(take.mouse.x, take.mouse.y);
    await page.keyboard.type('GREEN', { delay: 90 });
    await sourceIs(page, source.replace('Star(color=RED', 'Star(color=GREEN'));
    await take.glide(1150, 700, 0.6);
    await rerendered(page);
    // The star is complete when the last 5.5 s of the scene begin (the formula, axes and wave
    // follow): seek there, so the green star is on screen.
    const total = await page.evaluate(() => Number(/\/\s*([\d.]+)\s*s/.exec(document.querySelector('.manim-controls').textContent)[1]));
    await take.until(at('it plays') - 0.4);
    const pause = await control(page, 'Pause').catch(() => null);
    if (pause) await take.click(pause.x, pause.y, 0.3);
    const star = await seekPoint(page, (total - 5.5) / total);
    await take.click(star.x, star.y, 0.35);
    await take.glide(star.x + 140, star.y - 260, 0.5);
    await take.until(slots[0].duration + 0.05);
    await take.finish(start - 0.3, slots[0].duration);
    await context.close();
  },

  /** 1.4: page load, the regions, Python loading, playback controls, Renderer and gallery link. */
  async 'V1.4'(browser, slots) {
    const at = (words, k = 0) => phrase(1, '1.4', words, k);
    const context = await newContext(browser);
    // Hold Python's download until the narration talks about it, so "Loading Python…" is on screen then.
    let release;
    const held = new Promise(resolve => { release = resolve; });
    await context.route(/pyodide\.asm\.wasm/, async route => { await held; await route.continue(); });
    const page = await context.newPage();
    const take = new Take('V1.4');
    take.mouse = { x: 1100, y: 500 };
    await take.show(page);
    take.begin(0);
    await take.until(0.25);
    await page.goto(editorUrl(SQUARE_TO_CIRCLE));
    await take.until(at('code editor') - 0.2);
    await take.outline('#editor');
    await take.until(at('On the right') - 0.1);
    await take.outline('#editor', false);
    await take.outline('#review');
    await take.until(at('Along the top'));
    await take.outline('#review', false);
    await take.outline('#options');
    await take.until(at('The first time'));
    await take.outline('#options', false);
    await take.until(at('downloads'));
    await take.outline('#pyodide-status');
    await take.until(at('takes a little while'));
    release();
    await rendered(page);
    await take.outline('#pyodide-status', false);
    await take.until(at('behaves like a video player') - 0.3);
    await take.outline('.manim-controls');
    await take.glide(...Object.values(await control(page, 'Replay')).slice(0, 2), 0.9);
    await take.until(at('play,') );
    await take.outline('.manim-controls', false);
    await take.click();
    await take.until(at('pause') + 0.3);
    await take.click(...Object.values(await control(page, 'Pause')).slice(0, 2), 0.35);
    await take.until(at('drag the seek bar'));
    const range = await page.evaluate(() => {
      const input = document.querySelector('.manim-controls input[type=range]');
      return Number(input.value) / Number(input.max || 100);
    });
    const thumb = await seekPoint(page, range);
    await take.glide(thumb.x, thumb.y, 0.5);
    await page.mouse.down();
    for (const [fraction, seconds] of [[0.95, 1.0], [0.05, 1.3], [0.7, 1.0], [0.35, 0.8], [0.55, 0.6]]) {
      const p = await seekPoint(page, fraction);
      await take.glide(p.x, p.y, seconds);
    }
    await page.mouse.up();
    for (const [words, fraction] of [['already computed', 0.85], ['before it started', 0.15], ['jumping', 0.6], ['instant', 0.3]]) {
      await take.until(at(words));
      const p = await seekPoint(page, fraction);
      await take.click(p.x, p.y, 0.35);
    }
    await take.until(at('guesses'));
    await take.outline('#type-indicator');
    await take.until(at('The Renderer selector'));
    await take.outline('#type-indicator', false);
    await take.outline('#renderer-mode');
    const renderer = await centre(page, '#renderer-mode');
    await take.glide(renderer.x, renderer.y + 4, 0.8);
    await take.until(at('Sample gallery'));
    await take.outline('#renderer-mode', false);
    await take.outline('#sample-gallery');
    const gallery = await centre(page, '#sample-gallery');
    await take.glide(gallery.x, gallery.y + 4, 0.8);
    await take.until(at('come back to both'));
    await take.outline('#sample-gallery', false);
    await take.until(slots[0].duration + 0.05);
    await take.finish(0, slots[0].duration);
    await context.close();
  },

  /** 1.7: fill_opacity=0.5 on the square, then a third transform into a red triangle. */
  async 'V1.7'(browser, slots) {
    const at = words => phrase(1, '1.7', words);
    const context = await newContext(browser);
    const page = await context.newPage();
    await page.goto(editorUrl(SQUARE_TO_CIRCLE));
    await rendered(page);
    const take = new Take('V1.7');
    take.mouse = { x: 1150, y: 640 };
    await take.show(page);
    take.begin(0);
    const fill = await codePoint(page, 'color=BLUE', 0, 1);
    await take.until(at('Try giving'));
    await take.click(fill.x + 1, fill.y, 0.9);
    await take.until(at('equals'));
    await page.keyboard.type(', fill_opacity=0.5', { delay: 75 });
    await take.glide(1150, 640, 0.7);
    await rerendered(page);
    await take.until(at('Now add another') - 1.0);
    const transform = await codePoint(page, 'self.play(Transform(square, circle))', 0, 1);
    await take.click(transform.x + 2, transform.y, 0.9);
    await page.keyboard.press('End');
    await page.keyboard.press('Enter');
    await page.keyboard.type('self.play(Transform(square, Triangle(color=RED, fill_opacity=0.5)))', { delay: 35 });
    await sourceIs(page, SQUARE_TO_CIRCLE.replace('Square(color=BLUE)', 'Square(color=BLUE, fill_opacity=0.5)')
      .replace('        self.play(Transform(square, circle))\n',
        '        self.play(Transform(square, circle))\n        self.play(Transform(square, Triangle(color=RED, fill_opacity=0.5)))\n'));
    await take.glide(1150, 640, 0.7);
    await rerendered(page);
    const slot = slots[0];
    await take.until(slot.end + slot.fade_out + 0.05);
    await take.finish(0, slot.end + slot.fade_out);
    await context.close();
  },

  /** 9.2: the gallery in a new tab, Play preview, search and filter, Load in editor, edit, reload. */
  async 'V9.2'(browser, slots) {
    const at = words => phrase(9, '9.2', words);
    const context = await newContext(browser);
    let page = await context.newPage();
    await page.goto(editorUrl(SQUARE_TO_CIRCLE));
    await rendered(page);
    const take = new Take('V9.2');
    take.mouse = { x: 1150, y: 640 };
    await take.show(page);
    take.begin(0);
    await take.until(at('The Sample gallery') + 0.1);
    const link = await centre(page, '#sample-gallery');
    await take.glide(link.x, link.y + 3, 0.8);
    const [gallery] = await Promise.all([context.waitForEvent('page'), page.mouse.click(take.mouse.x, take.mouse.y)]);
    await gallery.setViewportSize(VIEW);
    take.mouse = { x: 900, y: 300 };
    await take.show(gallery);
    page = gallery;
    await page.waitForSelector('.load');
    await take.until(at('Each card'));
    const cover = await centre(page, 'img');
    await take.glide(cover.x, cover.y, 0.9);
    await take.until(at('animated samples') - 0.4);
    const play = page.locator('button.play').first();
    for (let k = 0; k < 16; k++) {           // a smooth scroll down to the first animated card
      await page.mouse.wheel(0, 55);
      await sleep(40);
      const box = await play.boundingBox();
      if (box && box.y < 520) break;
    }
    await take.until(at('Play preview') - 0.3);
    const playAt = await centre(page, 'button.play');
    await take.click(playAt.x, playAt.y, 0.6);
    await take.until(at('You can search') - 0.5);
    for (let k = 0; k < 20 && await page.evaluate(() => scrollY) > 0; k++) {
      await page.mouse.wheel(0, -90);
      await sleep(25);
    }
    const search = await centre(page, '#sample-search');
    await take.click(search.x - 300, search.y, 0.6);
    await page.keyboard.type('arrow', { delay: 70 });
    await take.until(at('filter by language') - 0.1);
    const language = await centre(page, '#sample-type');
    await take.glide(language.x, language.y, 0.6);
    await page.evaluate(([x, y]) => window.__recRing(x, y), [take.mouse.x, take.mouse.y]);
    await page.selectOption('#sample-type', { label: 'Manim animations' });
    await take.until(at('choose Load in editor'));
    const load = await centre(page, 'a.load >> visible=true');
    await take.glide(load.x, load.y, 0.6);
    await Promise.all([page.waitForURL(/example=/), page.mouse.click(take.mouse.x, take.mouse.y)]);
    await page.mouse.move(take.mouse.x, take.mouse.y);
    await rendered(page);
    await take.until(at('ready for you') - 0.6);
    const blue = await codePoint(page, 'BLUE');
    await take.glide(blue.x, blue.y, 0.7);
    await page.mouse.dblclick(take.mouse.x, take.mouse.y);
    await page.keyboard.type('ORANGE', { delay: 80 });
    await take.glide(1150, 640, 0.7);
    await rerendered(page);
    await take.until(at('remembers') - 0.2);
    await page.reload();
    await page.mouse.move(take.mouse.x, take.mouse.y);
    await rendered(page);
    const kept = await page.evaluate(() => ace.edit('editor').getValue().includes('color=ORANGE'));
    if (!kept) throw new Error('V9.2: the reload lost the edit');
    await take.until(slots[0].duration + 0.05);
    await take.finish(0, slots[0].duration);
    await context.close();
  },

  /** 11.1: the left panel's code, played in ManimOnline in step with Manim Community. */
  async 'V11.1'(browser, slots, notes) {
    const context = await newContext(browser);
    const page = await context.newPage();
    await page.goto(editorUrl(notes.code));
    await rendered(page);
    await page.click('#toggle-btn');            // hide the code: the preview fills the page
    await sleep(800);
    const svg = await page.locator('.manim-stage svg').first().boundingBox();
    const crop = [svg.x, svg.y, svg.width, svg.height].map(v => Math.round(v * ZOOM));
    const take = new Take('V11.1');
    await take.show(page);
    await page.evaluate(() => { document.getElementById('__rec_cursor').style.display = 'none'; });   // nothing to point at
    const start = slots[0].start;
    take.begin(start - 0.2);
    await take.until(notes.start);
    await page.evaluate(() => [...document.querySelectorAll('.manim-controls button')]
      .find(b => b.textContent.trim() === 'Replay').click());
    await take.until(notes.duration + 0.05);
    await take.finish(start - 0.2, notes.duration, { crops: { preview: crop } });
    await context.close();
  },
};

const SEGMENTS = { 'V0.2': 'ep00-0.2', 'V1.4': 'ep01-1.4', 'V1.7': 'ep01-1.7', 'V9.2': 'ep09-9.2', 'V11.1': 'ep11-11.1' };

(async () => {
  const chosen = argv.filter((a, i) => !a.startsWith('--') && !(i && argv[i - 1] === '--site'));
  const browser = await chromium.launch();
  try {
    for (const clip of chosen.length ? chosen : Object.keys(CLIPS)) {
      if (!CLIPS[clip]) throw new Error(`unknown clip ${clip}; known: ${Object.keys(CLIPS).join(', ')}`);
      const file = path.join(FOOTAGE, `${SEGMENTS[clip]}.json`);
      if (!fs.existsSync(file)) throw new Error(`${file} is missing: render the segment with production/render.py first`);
      const notes = JSON.parse(fs.readFileSync(file, 'utf8'));
      const slots = notes.slots.filter(s => s.clip === clip).map(s => ({ ...s, duration: notes.duration }));
      console.log(`recording ${clip} (${notes.duration.toFixed(1)} s segment) ...`);
      await CLIPS[clip](browser, slots, notes);
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
