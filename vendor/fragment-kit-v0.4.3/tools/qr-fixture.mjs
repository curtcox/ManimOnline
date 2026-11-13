/** Deterministic fixture generator; normal tests read the committed pixels. */
import fs from 'node:fs/promises';
import { deflateSync } from 'node:zlib';
import { encodeQr } from '../src/qr/encode.js';
const text = 'https://256t.us/AAAAAAAFaGVsbG8', qr = encodeQr(text), scale = 3;
const width = (qr.size + 8) * scale, rgba = Buffer.alloc(width * width * 4, 255);
qr.modules.forEach((row, y) => row.forEach((dark, x) => {
  if (dark) for (let dy = 0; dy < scale; dy++) for (let dx = 0; dx < scale; dx++) {
    const offset = (((y + 4) * scale + dy) * width + (x + 4) * scale + dx) * 4;
    rgba[offset] = rgba[offset + 1] = rgba[offset + 2] = 0;
  }
}));
const directory = new URL('../testing/fixtures/', import.meta.url);
await fs.writeFile(new URL('qr-known.json', directory), JSON.stringify({ text, width, height: width, rgba64: rgba.toString('base64') }) + '\n');
function crc32(data) {
  let crc = 0xffffffff;
  for (const byte of data) { crc ^= byte; for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0); }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const name = Buffer.from(type), length = Buffer.alloc(4), crc = Buffer.alloc(4);
  length.writeUInt32BE(data.length); crc.writeUInt32BE(crc32(Buffer.concat([name, data])));
  return Buffer.concat([length, name, data, crc]);
}
const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(width, 0); ihdr.writeUInt32BE(width, 4); ihdr[8] = 8; ihdr[9] = 6;
const rows = [];
for (let y = 0; y < width; y++) rows.push(Buffer.from([0]), rgba.subarray(y * width * 4, (y + 1) * width * 4));
await fs.writeFile(new URL('qr-known.png', directory), Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]), chunk('IHDR', ihdr), chunk('IDAT', deflateSync(Buffer.concat(rows))), chunk('IEND', Buffer.alloc(0))]));
