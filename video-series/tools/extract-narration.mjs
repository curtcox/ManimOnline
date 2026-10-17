#!/usr/bin/env node
/**
 * Split episode scripts into ElevenLabs-ready narration files and a cue sheet.
 *
 *   node video-series/tools/extract-narration.mjs [--strip-breaks] [episode-file ...]
 *
 * In each episode, a segment starts at a "### <n.m> Title" heading. Blockquote
 * lines ("> ") are narration; everything else is direction for the animator.
 * Lines naming a QR code ("**QR q01-02** ...") become cue-sheet rows.
 *
 * Output (in video-series/build/narration/):
 *   epNN/<segment>.txt   narration for one ElevenLabs generation per segment
 *   cues.csv             segment, words, estimated seconds, QR codes shown
 *
 * --strip-breaks removes <break time="..."/> tags for voices that do not support them.
 */
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SERIES = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const WORDS_PER_MINUTE = 145;
const args = process.argv.slice(2);
const stripBreaks = args.includes('--strip-breaks');
const files = args.filter(a => !a.startsWith('--'));
const episodes = files.length ? files.map(f => resolve(f))
  : readdirSync(join(SERIES, 'episodes')).filter(f => f.endsWith('.md')).sort().map(f => join(SERIES, 'episodes', f));

const out = join(SERIES, 'build', 'narration');
const cues = [['episode', 'segment', 'title', 'words', 'seconds', 'qr_codes']];
const totals = [];

for (const file of episodes) {
  const episode = basename(file, '.md');
  const segments = [];
  let current = null;
  for (const line of readFileSync(file, 'utf8').split('\n')) {
    const heading = line.match(/^### (\d+\.\d+)\s+(.*)$/);
    if (heading) {
      current = { id: heading[1], title: heading[2].replace(/\s+·.*$/, '').trim(), paragraphs: [[]], qr: [] };
      segments.push(current);
      continue;
    }
    if (!current) continue;
    if (/^## /.test(line)) { current = null; continue; }
    const qr = [...line.matchAll(/\*\*QR (q\d\d-\d\d)\*\*/g)].map(m => m[1]);
    current.qr.push(...qr);
    if (line.startsWith('>')) {
      const text = line.replace(/^>\s?/, '');
      if (text.trim()) current.paragraphs.at(-1).push(text.trim());
      else if (current.paragraphs.at(-1).length) current.paragraphs.push([]);
    } else if (current.paragraphs.at(-1).length) {
      current.paragraphs.push([]);
    }
  }
  mkdirSync(join(out, episode), { recursive: true });
  let episodeWords = 0;
  for (const segment of segments) {
    let text = segment.paragraphs.filter(p => p.length).map(p => p.join(' ')).join('\n\n');
    if (stripBreaks) text = text.replace(/\s*<break time="[^"]*"\s*\/>\s*/g, ' ').replace(/ {2,}/g, ' ');
    const words = text.replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;
    episodeWords += words;
    const slug = segment.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    writeFileSync(join(out, episode, `${segment.id.padStart(4, '0')}-${slug}.txt`), text + '\n');
    cues.push([episode, segment.id, segment.title, words, Math.round(words / WORDS_PER_MINUTE * 60), [...new Set(segment.qr)].join(' ')]);
  }
  totals.push(`${episode}: ${segments.length} segments, ${episodeWords} words, about ${(episodeWords / WORDS_PER_MINUTE).toFixed(1)} min of narration`);
}

const csv = cues.map(row => row.map(v => /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : v).join(',')).join('\n');
writeFileSync(join(out, 'cues.csv'), csv + '\n');
console.log(totals.join('\n'));
console.log(`\nWrote narration files and cues.csv to ${out}`);
