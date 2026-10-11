const { test } = require('node:test');
const assert = require('node:assert/strict');
const ManimVideo = require('../src/manim-video.js');

function readBoxes(bytes, start = 0, end = bytes.length) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const boxes = [];
  for (let offset = start; offset < end;) {
    const size = view.getUint32(offset);
    const type = String.fromCharCode(...bytes.subarray(offset + 4, offset + 8));
    assert.ok(size >= 8 && offset + size <= end, `box ${type} fits`);
    boxes.push({ type, start: offset, size, body: offset + 8 });
    offset += size;
  }
  return boxes;
}
const child = (bytes, parent, type, skip = 0) =>
  readBoxes(bytes, parent.body + skip, parent.start + parent.size).find(b => b.type === type);

function readVint(bytes, offset, keepMarker) {
  let length = 1;
  while (!(bytes[offset] & (0x80 >> (length - 1)))) length++;
  let value = keepMarker ? bytes[offset] : bytes[offset] & ((0x80 >> (length - 1)) - 1);
  for (let i = 1; i < length; i++) value = value * 256 + bytes[offset + i];
  return { value, length };
}
function readElements(bytes, start = 0, end = bytes.length) {
  const elements = [];
  for (let offset = start; offset < end;) {
    const id = readVint(bytes, offset, true);
    const size = readVint(bytes, offset + id.length);
    const body = offset + id.length + size.length;
    assert.ok(body + size.value <= end, `element 0x${id.value.toString(16)} fits`);
    elements.push({ id: id.value, start: offset, body, end: body + size.value });
    offset = body + size.value;
  }
  return elements;
}
const uintAt = (bytes, element) => [...bytes.subarray(element.body, element.end)].reduce((v, b) => v * 256 + b, 0);

const chunks = (count, keyEvery) => Array.from({ length: count }, (_, i) => ({
  data: Uint8Array.from([i, i + 1, i + 2]), key: i % keyEvery === 0, timestamp: Math.round(i * 1e6 / 15)
}));

test('MP4 places a complete moov before mdat with exact sample tables and offsets', () => {
  const samples = chunks(31, 30);
  const bytes = ManimVideo.muxMP4({ width: 800, height: 450, fps: 15, description: Uint8Array.from([1, 2, 3]), chunks: samples });
  const top = readBoxes(bytes);
  assert.deepEqual(top.map(b => b.type), ['ftyp', 'moov', 'mdat']);
  const moov = top[1];
  const mvhd = child(bytes, moov, 'mvhd');
  const view = new DataView(bytes.buffer);
  assert.equal(view.getUint32(mvhd.body + 12), 1000);
  assert.equal(view.getUint32(mvhd.body + 16), Math.round(31 * 1000 / 15));
  const trak = child(bytes, moov, 'trak');
  const tkhd = child(bytes, trak, 'tkhd');
  assert.equal(view.getUint32(tkhd.body + 76) / 65536, 800);
  assert.equal(view.getUint32(tkhd.body + 80) / 65536, 450);
  const stbl = child(bytes, child(bytes, child(bytes, trak, 'mdia'), 'minf'), 'stbl');
  const stts = child(bytes, stbl, 'stts');
  assert.equal(view.getUint32(stts.body + 4), 1);
  assert.deepEqual([view.getUint32(stts.body + 8), view.getUint32(stts.body + 12)], [31, 6000]);
  const stss = child(bytes, stbl, 'stss');
  assert.deepEqual([view.getUint32(stss.body + 4), view.getUint32(stss.body + 8), view.getUint32(stss.body + 12)], [2, 1, 31]);
  const stsz = child(bytes, stbl, 'stsz');
  assert.equal(view.getUint32(stsz.body + 8), 31);
  const avc1 = child(bytes, child(bytes, stbl, 'stsd'), 'avc1', 8);
  assert.equal(view.getUint16(avc1.body + 24), 800);
  const avcC = child(bytes, avc1, 'avcC', 78);
  assert.deepEqual([...bytes.subarray(avcC.body, avcC.start + avcC.size)], [1, 2, 3]);
  const offset = view.getUint32(child(bytes, stbl, 'stco').body + 8);
  assert.equal(offset, top[2].body);
  assert.deepEqual([...bytes.subarray(offset, offset + 6)], [0, 1, 2, 1, 2, 3]);
  assert.throws(() => ManimVideo.muxMP4({ width: 2, height: 2, fps: 15, description: null, chunks: samples }), /decoder configuration/);
});

test('WebM clusters start at keyframes and cues/seek head point at real elements', () => {
  const bytes = ManimVideo.muxWebM({ codecId: 'V_VP9', width: 640, height: 360, fps: 15, chunks: chunks(45, 30) });
  const [header, segment] = readElements(bytes);
  assert.equal(header.id, 0x1A45DFA3);
  assert.equal(segment.id, 0x18538067);
  const children = readElements(bytes, segment.body, segment.end);
  assert.deepEqual(children.map(e => e.id.toString(16)), ['114d9b74', '1549a966', '1654ae6b', '1f43b675', '1f43b675', '1c53bb6b']);
  const byId = Object.fromEntries(children.map(e => [e.id, e]));
  for (const seek of readElements(bytes, children[0].body, children[0].end)) {
    const [seekId, seekPosition] = readElements(bytes, seek.body, seek.end);
    const target = uintAt(bytes, seekId);
    assert.equal(segment.body + uintAt(bytes, seekPosition), byId[target].start);
  }
  const tracks = readElements(bytes, readElements(bytes, byId[0x1654AE6B].body, byId[0x1654AE6B].end)[0].body, byId[0x1654AE6B].end);
  const codec = tracks.find(e => e.id === 0x86);
  assert.equal(String.fromCharCode(...bytes.subarray(codec.body, codec.end)), 'V_VP9');
  const clusters = children.filter(e => e.id === 0x1F43B675);
  const timecodes = clusters.map(c => uintAt(bytes, readElements(bytes, c.body, c.end)[0]));
  assert.deepEqual(timecodes, [0, 2000]);
  const second = readElements(bytes, clusters[1].body, clusters[1].end);
  assert.equal(second.length, 16);
  assert.equal(bytes[second[1].body + 3], 0x80);
  assert.equal(new DataView(bytes.buffer).getInt16(second[2].body + 1), 67);
  const cues = readElements(bytes, byId[0x1C53BB6B].body, byId[0x1C53BB6B].end);
  const positions = cues.map(cue => {
    const positionsElement = readElements(bytes, cue.body, cue.end)[1];
    return segment.body + uintAt(bytes, readElements(bytes, positionsElement.body, positionsElement.end)[1]);
  });
  assert.deepEqual(positions, clusters.map(c => c.start));
});

function fakeEnv({ supported = () => true } = {}) {
  const calls = [];
  const env = {
    Blob,
    URL: { createObjectURL: () => 'blob:frame', revokeObjectURL: url => calls.push(['revoke', url]) },
    Image: class { set src(url) { this._src = url; queueMicrotask(() => this.onload && this.onload()); } },
    setTimeout: (callback, ms) => setTimeout(callback, Math.min(ms, 1)),
    clearTimeout,
    document: { createElement: () => ({ getContext: () => ({ fillRect() {}, drawImage: () => calls.push(['draw']) }) }) },
    VideoFrame: class { constructor(source, init) { this.init = init; } close() { calls.push(['close', this.init.timestamp]); } },
    VideoEncoder: class {
      static async isConfigSupported(config) { calls.push(['probe', config.codec]); return { supported: supported(config) }; }
      constructor({ output }) { this.output = output; this.state = 'unconfigured'; this.encodeQueueSize = 0; }
      configure(config) { this.config = config; this.state = 'configured'; calls.push(['configure', config.codec, config.width, config.height]); }
      encode(frame, options) {
        calls.push(['encode', frame.init.timestamp, options.keyFrame]);
        const data = Uint8Array.from([frame.init.timestamp % 251]);
        this.output({ byteLength: 1, type: options.keyFrame ? 'key' : 'delta', timestamp: frame.init.timestamp, copyTo: target => target.set(data) },
          options.keyFrame ? { decoderConfig: { description: Uint8Array.from([9, 9]) } } : undefined);
      }
      async flush() { calls.push(['flush']); }
      close() { this.state = 'closed'; calls.push(['closeEncoder']); }
    }
  };
  return { env, calls };
}

test('encode rasterizes each frame at its timestamp with periodic keyframes', async () => {
  const { env, calls } = fakeEnv();
  const progress = [];
  const blob = await ManimVideo.encode({ format: 'mp4', frameCount: 31, fps: 15, width: 801, height: 451,
    svgFor: index => `<svg>${index}</svg>`, onProgress: p => progress.push(p), env });
  assert.equal(blob.type, 'video/mp4');
  assert.deepEqual(calls.find(c => c[0] === 'configure'), ['configure', 'avc1.640034', 802, 452]);
  const encodes = calls.filter(c => c[0] === 'encode');
  assert.equal(encodes.length, 31);
  assert.deepEqual(encodes.filter(c => c[2]).map(c => c[1]), [0, 2000000]);
  assert.equal(encodes[1][1], 66667);
  assert.equal(calls.filter(c => c[0] === 'close').length, 31);
  assert.equal(calls.filter(c => c[0] === 'revoke').length, 31);
  assert.equal(progress.at(-1), 1);
  assert.equal(calls.at(-1)[0], 'closeEncoder');
  const bytes = new Uint8Array(await blob.arrayBuffer());
  assert.equal(String.fromCharCode(...bytes.subarray(4, 8)), 'ftyp');
});

test('encode falls back to VP8 for WebM, reports unsupported formats and honors cancellation', async () => {
  let { env, calls } = fakeEnv({ supported: config => config.codec === 'vp8' });
  const blob = await ManimVideo.encode({ format: 'webm', frameCount: 3, fps: 30, width: 4, height: 4, svgFor: () => '<svg/>', env });
  assert.equal(blob.type, 'video/webm');
  assert.deepEqual(calls.filter(c => c[0] === 'probe').map(c => c[1]), ['vp09.00.41.08', 'vp8']);
  ({ env } = fakeEnv({ supported: () => false }));
  await assert.rejects(ManimVideo.encode({ format: 'mp4', frameCount: 3, fps: 30, width: 4, height: 4, svgFor: () => '<svg/>', env }), /cannot encode MP4/);
  await assert.rejects(ManimVideo.encode({ format: 'mp4', frameCount: 3, fps: 30, width: 4, height: 4, svgFor: () => '<svg/>', env: { Blob } }), /WebCodecs/);
  ({ env, calls } = fakeEnv());
  const controller = new AbortController();
  const result = ManimVideo.encode({ format: 'webm', frameCount: 100, fps: 30, width: 4, height: 4, signal: controller.signal,
    svgFor: index => { if (index === 5) controller.abort(); return '<svg/>'; }, env });
  await assert.rejects(result, error => error.name === 'AbortError');
  assert.ok(calls.filter(c => c[0] === 'encode').length < 10);
  assert.equal(calls.at(-1)[0], 'closeEncoder');
});
