// Encodes text as a QR code in byte mode, using the smallest version that fits and then the strongest error
// correction that fits in that version. Returns { version, size, modules } with modules[y][x] true for dark,
// or null if the text is too long for any QR code.
//
// Condensed from the QR Code generator library by Project Nayuki
// (https://www.nayuki.io/page/qr-code-generator-library), which carries this notice:
//
//   Copyright (c) Project Nayuki. (MIT License)
//
//   Permission is hereby granted, free of charge, to any person obtaining a copy of
//   this software and associated documentation files (the "Software"), to deal in
//   the Software without restriction, including without limitation the rights to
//   use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
//   the Software, and to permit persons to whom the Software is furnished to do so,
//   subject to the following conditions:
//   - The above copyright notice and this permission notice shall be included in
//     all copies or substantial portions of the Software.
//   - The Software is provided "as is", without warranty of any kind, express or
//     implied, including but not limited to the warranties of merchantability,
//     fitness for a particular purpose and noninfringement. In no event shall the
//     authors or copyright holders be liable for any claim, damages or other
//     liability, whether in an action of contract, tort or otherwise, arising from,
//     out of or in connection with the Software or the use or other dealings in the
//     Software.
const encodeQr = (() => {
  // Indexed by error correction level (low, medium, quartile, high), then version; index 0 is unused
  const ECC_CODEWORDS_PER_BLOCK = [
    [-1,  7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28],
    [-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    [-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
  ];
  const NUM_ERROR_CORRECTION_BLOCKS = [
    [-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4,  4,  4,  4,  4,  6,  6,  6,  6,  7,  8,  8,  9,  9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25],
    [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5,  5,  8,  9,  9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49],
    [-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8,  8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68],
    [-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81],
  ];
  const FORMAT_BITS = [1, 0, 3, 2];
  const MASKS = [
    (x, y) => (x + y) % 2 === 0,
    (x, y) => y % 2 === 0,
    (x, y) => x % 3 === 0,
    (x, y) => (x + y) % 3 === 0,
    (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0,
    (x, y) => x * y % 2 + x * y % 3 === 0,
    (x, y) => (x * y % 2 + x * y % 3) % 2 === 0,
    (x, y) => ((x + y) % 2 + x * y % 3) % 2 === 0,
  ];

  const getBit = (x, i) => ((x >>> i) & 1) !== 0;

  // Data bits left after function modules, including remainder bits
  function numRawDataModules(ver) {
    let result = (16 * ver + 128) * ver + 64;
    if (ver >= 2) {
      const numAlign = Math.floor(ver / 7) + 2;
      result -= (25 * numAlign - 10) * numAlign - 55;
      if (ver >= 7) result -= 36;
    }
    return result;
  }

  function numDataCodewords(ver, ecl) {
    return Math.floor(numRawDataModules(ver) / 8)
      - ECC_CODEWORDS_PER_BLOCK[ecl][ver] * NUM_ERROR_CORRECTION_BLOCKS[ecl][ver];
  }

  // Multiplication in GF(2^8/0x11D)
  function rsMultiply(x, y) {
    let z = 0;
    for (let i = 7; i >= 0; i--) {
      z = (z << 1) ^ ((z >>> 7) * 0x11D);
      z ^= ((y >>> i) & 1) * x;
    }
    return z;
  }

  // Generator polynomial coefficients from highest to lowest power, without the leading 1
  function rsDivisor(degree) {
    const result = new Array(degree - 1).fill(0).concat([1]);
    let root = 1;
    for (let i = 0; i < degree; i++) {
      for (let j = 0; j < result.length; j++) {
        result[j] = rsMultiply(result[j], root);
        if (j + 1 < result.length) result[j] ^= result[j + 1];
      }
      root = rsMultiply(root, 0x02);
    }
    return result;
  }

  function rsRemainder(data, divisor) {
    const result = divisor.map(() => 0);
    for (const b of data) {
      const factor = b ^ result.shift();
      result.push(0);
      divisor.forEach((coef, i) => { result[i] ^= rsMultiply(coef, factor); });
    }
    return result;
  }

  function alignmentPositions(ver, size) {
    if (ver === 1) return [];
    const numAlign = Math.floor(ver / 7) + 2;
    const step = Math.floor((ver * 8 + numAlign * 3 + 5) / (numAlign * 4 - 4)) * 2;
    const result = [6];
    for (let pos = size - 7; result.length < numAlign; pos -= step) result.splice(1, 0, pos);
    return result;
  }

  function addEccAndInterleave(data, ver, ecl) {
    const numBlocks = NUM_ERROR_CORRECTION_BLOCKS[ecl][ver];
    const blockEccLen = ECC_CODEWORDS_PER_BLOCK[ecl][ver];
    const rawCodewords = Math.floor(numRawDataModules(ver) / 8);
    const numShortBlocks = numBlocks - rawCodewords % numBlocks;
    const shortBlockLen = Math.floor(rawCodewords / numBlocks);
    const divisor = rsDivisor(blockEccLen);
    const blocks = [];
    for (let i = 0, k = 0; i < numBlocks; i++) {
      const dat = data.slice(k, k + shortBlockLen - blockEccLen + (i < numShortBlocks ? 0 : 1));
      k += dat.length;
      const ecc = rsRemainder(dat, divisor);
      if (i < numShortBlocks) dat.push(0);
      blocks.push(dat.concat(ecc));
    }
    const result = [];
    for (let i = 0; i < blocks[0].length; i++) {
      blocks.forEach((block, j) => {
        // Skips the padding byte in short blocks
        if (i !== shortBlockLen - blockEccLen || j >= numShortBlocks) result.push(block[i]);
      });
    }
    return result;
  }

  function build(ver, ecl, dataCodewords) {
    const size = ver * 4 + 17;
    const modules = Array.from({ length: size }, () => new Array(size).fill(false));
    const isFunction = Array.from({ length: size }, () => new Array(size).fill(false));
    const setFunction = (x, y, dark) => { modules[y][x] = dark; isFunction[y][x] = true; };

    function drawFormatBits(mask) {
      const data = FORMAT_BITS[ecl] << 3 | mask;
      let rem = data;
      for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
      const bits = (data << 10 | rem) ^ 0x5412;
      for (let i = 0; i <= 5; i++) setFunction(8, i, getBit(bits, i));
      setFunction(8, 7, getBit(bits, 6));
      setFunction(8, 8, getBit(bits, 7));
      setFunction(7, 8, getBit(bits, 8));
      for (let i = 9; i < 15; i++) setFunction(14 - i, 8, getBit(bits, i));
      for (let i = 0; i < 8; i++) setFunction(size - 1 - i, 8, getBit(bits, i));
      for (let i = 8; i < 15; i++) setFunction(8, size - 15 + i, getBit(bits, i));
      setFunction(8, size - 8, true);
    }

    // Timing patterns, then finder patterns (which overwrite some timing modules)
    for (let i = 0; i < size; i++) {
      setFunction(6, i, i % 2 === 0);
      setFunction(i, 6, i % 2 === 0);
    }
    for (const [cx, cy] of [[3, 3], [size - 4, 3], [3, size - 4]]) {
      for (let dy = -4; dy <= 4; dy++) {
        for (let dx = -4; dx <= 4; dx++) {
          const dist = Math.max(Math.abs(dx), Math.abs(dy));
          const x = cx + dx;
          const y = cy + dy;
          if (x >= 0 && x < size && y >= 0 && y < size) setFunction(x, y, dist !== 2 && dist !== 4);
        }
      }
    }
    const align = alignmentPositions(ver, size);
    const n = align.length;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        if ((i === 0 && j === 0) || (i === 0 && j === n - 1) || (i === n - 1 && j === 0)) continue;
        for (let dy = -2; dy <= 2; dy++) {
          for (let dx = -2; dx <= 2; dx++) {
            setFunction(align[i] + dx, align[j] + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
          }
        }
      }
    }
    drawFormatBits(0);
    if (ver >= 7) {
      let rem = ver;
      for (let i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1F25);
      const bits = ver << 12 | rem;
      for (let i = 0; i < 18; i++) {
        const a = size - 11 + i % 3;
        const b = Math.floor(i / 3);
        setFunction(a, b, getBit(bits, i));
        setFunction(b, a, getBit(bits, i));
      }
    }

    // Codewords, in the zigzag order of column pairs from the right, skipping the vertical timing column
    const codewords = addEccAndInterleave(dataCodewords, ver, ecl);
    let bit = 0;
    for (let right = size - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (let vert = 0; vert < size; vert++) {
        for (let j = 0; j < 2; j++) {
          const x = right - j;
          const y = ((right + 1) & 2) === 0 ? size - 1 - vert : vert;
          if (!isFunction[y][x] && bit < codewords.length * 8) {
            modules[y][x] = getBit(codewords[bit >>> 3], 7 - (bit & 7));
            bit++;
          }
        }
      }
    }

    function applyMask(mask) {
      for (let y = 0; y < size; y++) {
        for (let x = 0; x < size; x++) {
          if (!isFunction[y][x] && MASKS[mask](x, y)) modules[y][x] = !modules[y][x];
        }
      }
    }

    function addHistory(run, history) {
      if (history[0] === 0) run += size;
      history.pop();
      history.unshift(run);
    }

    function countFinderPatterns(h) {
      const n = h[1];
      const core = n > 0 && h[2] === n && h[3] === n * 3 && h[4] === n && h[5] === n;
      return (core && h[0] >= n * 4 && h[6] >= n ? 1 : 0) + (core && h[6] >= n * 4 && h[0] >= n ? 1 : 0);
    }

    function penalty() {
      let result = 0;
      for (const at of [(a, b) => modules[a][b], (a, b) => modules[b][a]]) {
        for (let a = 0; a < size; a++) {
          let runColor = false;
          let run = 0;
          const history = [0, 0, 0, 0, 0, 0, 0];
          for (let b = 0; b < size; b++) {
            if (at(a, b) === runColor) {
              run++;
              if (run === 5) result += 3;
              else if (run > 5) result++;
            } else {
              addHistory(run, history);
              if (!runColor) result += countFinderPatterns(history) * 40;
              runColor = at(a, b);
              run = 1;
            }
          }
          if (runColor) {
            addHistory(run, history);
            run = 0;
          }
          addHistory(run + size, history);
          result += countFinderPatterns(history) * 40;
        }
      }
      for (let y = 0; y < size - 1; y++) {
        for (let x = 0; x < size - 1; x++) {
          const c = modules[y][x];
          if (c === modules[y][x + 1] && c === modules[y + 1][x] && c === modules[y + 1][x + 1]) result += 3;
        }
      }
      const dark = modules.reduce((sum, row) => sum + row.filter(Boolean).length, 0);
      const total = size * size;
      result += (Math.ceil(Math.abs(dark * 20 - total * 10) / total) - 1) * 10;
      return result;
    }

    let best = 0;
    let minPenalty = Infinity;
    for (let mask = 0; mask < 8; mask++) {
      applyMask(mask);
      drawFormatBits(mask);
      const p = penalty();
      if (p < minPenalty) {
        best = mask;
        minPenalty = p;
      }
      applyMask(mask);
    }
    applyMask(best);
    drawFormatBits(best);
    return { version: ver, size, modules };
  }

  return function encodeQr(text, options = {}) {
    const data = new TextEncoder().encode(text);
    const usedBits = (ver) => 4 + (ver < 10 ? 8 : 16) + data.length * 8;
    const requested = options.ecc === undefined ? null : ['L', 'M', 'Q', 'H'].indexOf(options.ecc);
    if (requested === -1 || (options.version !== undefined && (!Number.isInteger(options.version) || options.version < 1 || options.version > 40))) throw new Error('Invalid QR version or ECC level.');
    let ver = options.version ?? 1;
    while (usedBits(ver) > numDataCodewords(ver, requested ?? 0) * 8) {
      if (options.version !== undefined) return null;
      if (++ver > 40) return null;
    }
    let ecl = requested ?? 0;
    for (const e of requested === null ? [1, 2, 3] : []) {
      if (usedBits(ver) <= numDataCodewords(ver, e) * 8) ecl = e;
    }

    const bits = [];
    const append = (val, len) => {
      for (let i = len - 1; i >= 0; i--) bits.push((val >>> i) & 1);
    };
    append(0x4, 4);
    append(data.length, ver < 10 ? 8 : 16);
    for (const b of data) append(b, 8);
    const capacity = numDataCodewords(ver, ecl) * 8;
    append(0, Math.min(4, capacity - bits.length));
    append(0, (8 - bits.length % 8) % 8);
    for (let pad = 0xEC; bits.length < capacity; pad ^= 0xEC ^ 0x11) append(pad, 8);

    const codewords = new Array(bits.length / 8).fill(0);
    bits.forEach((b, i) => { codewords[i >>> 3] |= b << (7 - (i & 7)); });
    return build(ver, ecl, codewords);
  };
})();

function qrSvg(qr) {
  const dim = qr.size + 8;
  let path = '';
  qr.modules.forEach((row, y) => row.forEach((dark, x) => { if (dark) path += `M${x+4},${y+4}h1v1h-1z`; }));
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${dim*8}" height="${dim*8}" viewBox="0 0 ${dim} ${dim}" shape-rendering="crispEdges" role="img" aria-label="QR code of share link"><rect width="${dim}" height="${dim}" fill="white"/><path d="${path}" fill="black"/></svg>`;
}
function qrNotes(url, qr) {
  const notes = [];
  const parsed = new URL(url);
  if (parsed.protocol === 'file:' || ['localhost', '127.0.0.1', '[::1]'].includes(parsed.hostname)) notes.push('This link points to this computer. Save to HashBin on the published site to share with a phone.');
  if (!qr) notes.push('This URL is too long for a QR code. Save to HashBin for a short link.');
  else if (qr.version > 20) notes.push('This QR code is dense and may be hard to scan. Save to HashBin for a short link.');
  return notes.join(' ');
}

export { encodeQr, qrSvg, qrNotes };
export function qrPng(qr, scale = 8, document = globalThis.document) {
  if (!qr || !Number.isInteger(scale) || scale < 1 || scale > 64) throw new Error('Invalid QR image.');
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = (qr.size + 8) * scale;
  const context = canvas.getContext('2d');
  context.fillStyle = 'white'; context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = 'black';
  qr.modules.forEach((row, y) => row.forEach((dark, x) => { if (dark) context.fillRect((x + 4) * scale, (y + 4) * scale, scale, scale); }));
  return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('PNG export failed.')), 'image/png'));
}
