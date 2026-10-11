/**
 * Frame-accurate video export: every rendered frame is rasterized offscreen and encoded
 * with WebCodecs at its exact timestamp, then muxed into MP4 (H.264) or WebM (VP9/VP8).
 */
const ManimVideo = (() => {
  const MP4_CODECS = ['avc1.640034', 'avc1.4d0034', 'avc1.42e034', 'avc1.42e01f'];
  const WEBM_CODECS = [['vp09.00.41.08', 'V_VP9'], ['vp8', 'V_VP8']];
  const KEYFRAME_SECONDS = 2;

  const concat = parts => {
    const output = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0));
    let offset = 0;
    for (const part of parts) { output.set(part, offset); offset += part.length; }
    return output;
  };
  const ascii = text => Uint8Array.from(text, c => c.charCodeAt(0));
  const uint = (value, bytes) => {
    const output = new Uint8Array(bytes);
    for (let i = bytes - 1; i >= 0; i--) { output[i] = value % 256; value = Math.floor(value / 256); }
    return output;
  };

  // --- WebM (Matroska subset) -------------------------------------------------------
  const vint = value => {
    let length = 1;
    while (value >= 2 ** (7 * length) - 1) length++;
    const output = uint(value, length);
    output[0] |= 1 << (8 - length);
    return output;
  };
  const minimalUint = value => {
    let bytes = 1;
    while (value >= 2 ** (8 * bytes)) bytes++;
    return uint(value, bytes);
  };
  const id = value => uint(value, value > 0xFFFFFF ? 4 : value > 0xFFFF ? 3 : value > 0xFF ? 2 : 1);
  const element = (identifier, payload) => {
    const body = Array.isArray(payload) ? concat(payload) : payload;
    return concat([id(identifier), vint(body.length), body]);
  };
  const uintElement = (identifier, value, width) => element(identifier, width ? uint(value, width) : minimalUint(value));
  const float64 = value => {
    const output = new Uint8Array(8);
    new DataView(output.buffer).setFloat64(0, value);
    return output;
  };

  function muxWebM({ codecId, width, height, fps, chunks }) {
    const durationMs = chunks.length * 1000 / fps;
    const header = element(0x1A45DFA3, [
      uintElement(0x4286, 1), uintElement(0x42F7, 1), uintElement(0x42F2, 4), uintElement(0x42F3, 8),
      element(0x4282, ascii('webm')), uintElement(0x4287, 4), uintElement(0x4285, 2)
    ]);
    const info = element(0x1549A966, [
      uintElement(0x2AD7B1, 1000000), element(0x4489, float64(durationMs)),
      element(0x4D80, ascii('ManimOnline')), element(0x5741, ascii('ManimOnline'))
    ]);
    const tracks = element(0x1654AE6B, element(0xAE, [
      uintElement(0xD7, 1), uintElement(0x73C5, 1), uintElement(0x83, 1), uintElement(0x9C, 0),
      element(0x86, ascii(codecId)), uintElement(0x23E383, Math.round(1e9 / fps)),
      element(0xE0, [uintElement(0xB0, width), uintElement(0xBA, height)])
    ]));
    // A cluster starts at every keyframe, which keeps relative block times within int16.
    const clusters = [], cues = [];
    let blocks = [], clusterTime = 0;
    const flush = () => {
      if (blocks.length) clusters.push({ time: clusterTime, data: element(0x1F43B675, [uintElement(0xE7, clusterTime), ...blocks]) });
      blocks = [];
    };
    for (const chunk of chunks) {
      const time = Math.round(chunk.timestamp / 1000);
      if (chunk.key || !blocks.length) { flush(); clusterTime = time; }
      const relative = time - clusterTime;
      if (relative > 32767) throw new Error('Video keyframes are too far apart for WebM.');
      const head = new Uint8Array(4);
      head[0] = 0x81;
      new DataView(head.buffer).setInt16(1, relative);
      head[3] = chunk.key ? 0x80 : 0;
      blocks.push(element(0xA3, [head, chunk.data]));
    }
    flush();
    // SeekHead positions are fixed-width so its own size does not depend on them.
    const seek = (target, position) => element(0x4DBB, [element(0x53AB, id(target)), uintElement(0x53AC, position, 8)]);
    const seekSize = (element(0x114D9B74, [seek(0x1549A966, 0), seek(0x1654AE6B, 0), seek(0x1C53BB6B, 0)])).length;
    let position = seekSize + info.length + tracks.length;
    for (const cluster of clusters) {
      cues.push(element(0xBB, [uintElement(0xB3, cluster.time),
        element(0xB7, [uintElement(0xF7, 1), uintElement(0xF1, position)])]));
      position += cluster.data.length;
    }
    const seekHead = element(0x114D9B74, [seek(0x1549A966, seekSize), seek(0x1654AE6B, seekSize + info.length),
      seek(0x1C53BB6B, position)]);
    const segment = element(0x18538067, [seekHead, info, tracks, ...clusters.map(c => c.data), element(0x1C53BB6B, cues)]);
    return concat([header, segment]);
  }

  // --- MP4 (ISO BMFF, single progressive H.264 track, moov first) ----------------------
  const box = (type, ...parts) => {
    const body = concat(parts);
    return concat([uint(body.length + 8, 4), ascii(type), body]);
  };
  const fullBox = (type, version, flags, ...parts) => box(type, uint(version, 1), uint(flags, 3), ...parts);
  const MATRIX = concat([0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000].map(v => uint(v, 4)));

  function muxMP4({ width, height, fps, description, chunks }) {
    if (!description) throw new Error('The H.264 encoder did not provide a decoder configuration.');
    const timescale = 90000;
    const ticks = index => Math.round(index * timescale / fps);
    const deltas = chunks.map((_, i) => ticks(i + 1) - ticks(i));
    const duration = ticks(chunks.length);
    const movieDuration = Math.round(chunks.length * 1000 / fps);
    const stts = [];
    for (const delta of deltas) {
      if (stts.length && stts.at(-1)[1] === delta) stts.at(-1)[0]++;
      else stts.push([1, delta]);
    }
    const keys = chunks.flatMap((chunk, i) => chunk.key ? [i + 1] : []);
    const ftyp = box('ftyp', ascii('isom'), uint(512, 4), ascii('isomiso2avc1mp41'));
    const moovFor = dataOffset => box('moov',
      fullBox('mvhd', 0, 0, uint(0, 4), uint(0, 4), uint(1000, 4), uint(movieDuration, 4), uint(0x00010000, 4),
        uint(0x0100, 2), new Uint8Array(10), MATRIX, new Uint8Array(24), uint(2, 4)),
      box('trak',
        fullBox('tkhd', 0, 3, uint(0, 4), uint(0, 4), uint(1, 4), uint(0, 4), uint(movieDuration, 4),
          new Uint8Array(8), uint(0, 2), uint(0, 2), uint(0, 2), uint(0, 2), MATRIX, uint(width * 65536, 4), uint(height * 65536, 4)),
        box('mdia',
          fullBox('mdhd', 0, 0, uint(0, 4), uint(0, 4), uint(timescale, 4), uint(duration, 4), uint(0x55C4, 2), uint(0, 2)),
          fullBox('hdlr', 0, 0, uint(0, 4), ascii('vide'), new Uint8Array(12), ascii('VideoHandler\0')),
          box('minf',
            fullBox('vmhd', 0, 1, new Uint8Array(8)),
            box('dinf', fullBox('dref', 0, 0, uint(1, 4), fullBox('url ', 0, 1))),
            box('stbl',
              fullBox('stsd', 0, 0, uint(1, 4), box('avc1', new Uint8Array(6), uint(1, 2), new Uint8Array(16),
                uint(width, 2), uint(height, 2), uint(0x00480000, 4), uint(0x00480000, 4), uint(0, 4), uint(1, 2),
                new Uint8Array(32), uint(0x0018, 2), uint(0xFFFF, 2), box('avcC', description))),
              fullBox('stts', 0, 0, uint(stts.length, 4), ...stts.flatMap(([count, delta]) => [uint(count, 4), uint(delta, 4)])),
              fullBox('stss', 0, 0, uint(keys.length, 4), ...keys.map(k => uint(k, 4))),
              fullBox('stsc', 0, 0, uint(1, 4), uint(1, 4), uint(chunks.length, 4), uint(1, 4)),
              fullBox('stsz', 0, 0, uint(0, 4), uint(chunks.length, 4), ...chunks.map(c => uint(c.data.length, 4))),
              fullBox('stco', 0, 0, uint(1, 4), uint(dataOffset, 4)))))));
    const moovSize = moovFor(0).length;
    const mdatSize = chunks.reduce((sum, c) => sum + c.data.length, 8);
    if (ftyp.length + moovSize + mdatSize >= 2 ** 32) throw new Error('The video is too large for MP4 export.');
    return concat([ftyp, moovFor(ftyp.length + moovSize + 8), uint(mdatSize, 4), ascii('mdat'), ...chunks.map(c => c.data)]);
  }

  // --- Encoding -----------------------------------------------------------------------
  async function chooseConfig(format, width, height, fps, env) {
    if (typeof env.VideoEncoder !== 'function' || typeof env.VideoFrame !== 'function') {
      throw new Error('Video export needs a browser with WebCodecs video encoding.');
    }
    const bitrate = Math.min(20e6, Math.max(1e6, Math.round(width * height * fps * 0.2)));
    const base = { width, height, bitrate, framerate: fps, latencyMode: 'quality' };
    const candidates = format === 'mp4'
      ? MP4_CODECS.map(codec => [{ ...base, codec, avc: { format: 'avc' } }, null])
      : WEBM_CODECS.map(([codec, codecId]) => [{ ...base, codec }, codecId]);
    for (const [config, codecId] of candidates) {
      try {
        const support = await env.VideoEncoder.isConfigSupported(config);
        if (support && support.supported) return { config, codecId };
      } catch (_) { /* Try the next codec. */ }
    }
    throw new Error(`This browser cannot encode ${format === 'mp4' ? 'MP4 (H.264)' : 'WebM (VP9/VP8)'} video.`);
  }

  function rasterize(context, source, width, height, env) {
    return new Promise((resolve, reject) => {
      const image = new env.Image();
      const url = env.URL.createObjectURL(new env.Blob([source], { type: 'image/svg+xml' }));
      let settled = false;
      const finish = error => {
        if (settled) return;
        settled = true;
        env.clearTimeout(timer);
        image.onload = image.onerror = null;
        env.URL.revokeObjectURL(url);
        if (error) reject(error); else resolve();
      };
      const timer = env.setTimeout(() => finish(new Error('A video frame timed out while rasterizing.')), 10000);
      image.onerror = () => finish(new Error('Could not read an animation frame for video export.'));
      image.onload = () => {
        try {
          context.fillStyle = '#000000';
          context.fillRect(0, 0, width, height);
          context.drawImage(image, 0, 0, width, height);
          finish();
        } catch (error) { finish(error); }
      };
      image.src = url;
    });
  }

  /**
   * Encode `frameCount` frames. `svgFor(index)` returns a serialized SVG frame.
   * Resolves to a Blob; rejects with an AbortError-named error when `signal` aborts.
   */
  async function encode({ format, frameCount, fps, width, height, svgFor, onProgress = () => {}, signal, env = globalThis }) {
    if (!['mp4', 'webm'].includes(format)) throw new Error('Unknown video format.');
    if (!Number.isInteger(frameCount) || frameCount < 1) throw new Error('Render an animation before exporting video.');
    if (!(Number.isFinite(fps) && fps > 0 && fps <= 240)) throw new Error('Invalid animation frame rate.');
    // H.264 and 4:2:0 VP9 need even dimensions; the last odd pixel row/column is stretched.
    const evenWidth = width + (width % 2), evenHeight = height + (height % 2);
    const { config, codecId } = await chooseConfig(format, evenWidth, evenHeight, fps, env);
    const aborted = () => {
      const error = new Error('Video export cancelled.');
      error.name = 'AbortError';
      return error;
    };
    if (signal && signal.aborted) throw aborted();
    const canvas = env.document.createElement('canvas');
    canvas.width = evenWidth;
    canvas.height = evenHeight;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Video export requires a browser canvas.');
    const chunks = [];
    let description = null, failure = null;
    const encoder = new env.VideoEncoder({
      output: (chunk, metadata) => {
        const data = new Uint8Array(chunk.byteLength);
        chunk.copyTo(data);
        chunks.push({ data, key: chunk.type === 'key', timestamp: chunk.timestamp });
        const config = metadata && metadata.decoderConfig;
        if (config && config.description) {
          const source = config.description;
          description = new Uint8Array(ArrayBuffer.isView(source) ? source.buffer.slice(source.byteOffset, source.byteOffset + source.byteLength) : source.slice(0));
        }
      },
      error: error => { failure = error; }
    });
    try {
      encoder.configure(config);
      const keyInterval = Math.max(1, Math.round(fps * KEYFRAME_SECONDS));
      for (let index = 0; index < frameCount; index++) {
        if (signal && signal.aborted) throw aborted();
        if (failure) throw failure;
        await rasterize(context, svgFor(index), evenWidth, evenHeight, env);
        const frame = new env.VideoFrame(canvas, { timestamp: Math.round(index * 1e6 / fps), duration: Math.round(1e6 / fps) });
        try { encoder.encode(frame, { keyFrame: index % keyInterval === 0 }); }
        finally { frame.close(); }
        while (encoder.encodeQueueSize > 4 && !failure) await new Promise(resolve => env.setTimeout(resolve, 5));
        onProgress((index + 1) / frameCount);
      }
      await encoder.flush();
      if (failure) throw failure;
      if (signal && signal.aborted) throw aborted();
    } finally {
      if (encoder.state !== 'closed') encoder.close();
    }
    chunks.sort((a, b) => a.timestamp - b.timestamp);
    const bytes = format === 'mp4'
      ? muxMP4({ width: evenWidth, height: evenHeight, fps, description, chunks })
      : muxWebM({ codecId, width: evenWidth, height: evenHeight, fps, chunks });
    return new env.Blob([bytes], { type: format === 'mp4' ? 'video/mp4' : 'video/webm' });
  }

  return { encode, muxMP4, muxWebM };
})();
if (typeof module !== 'undefined') module.exports = ManimVideo;
else globalThis.ManimVideo = ManimVideo;
