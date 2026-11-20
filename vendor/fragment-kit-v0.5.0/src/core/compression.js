import LZString from '../../vendor/lz-string-1.5.0.mjs';
import { bounded, MAX_BYTES } from './bytes.js';
export const compress = value => LZString.compressToEncodedURIComponent(value);
export function decompress(input, limit = MAX_BYTES) {
  if (typeof input !== 'string' || input.length > Math.ceil(limit * 4) + 64) throw new Error('Shared source is too large.');
  const result = decodeSource(input, limit);
  if (result === null || compress(result) !== input.replaceAll(' ', '+')) throw new Error('The shared source could not be decompressed.');
  return bounded(result, limit);
}
export const decompressSource = decompress;
// Bounded variant of lz-string 1.5.0's URI decoder (Pieroxy, MIT).
// See ../../vendor/LICENSE-lz-string. Stop before allocating oversized output.
const alphabet =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-$";
function decodeSource(input, limit) {
  if (!input) return null;
  input = input.replaceAll(" ", "+");
  if (/[^A-Za-z0-9+\-$]/.test(input)) return null;
  let position = 32,
    index = 1,
    value = alphabet.indexOf(input[0]);
  const bits = (count) => {
    let result = 0;
    for (let p = 0; p < count; p++) {
      if (value & position) result += 2 ** p;
      position >>= 1;
      if (!position) {
        position = 32;
        value = alphabet.indexOf(input[index++]);
        if (value < 0) value = 0;
      }
    }
    return result;
  };
  const dictionary = [0, 1, 2];
  let next = bits(2),
    c;
  if (next === 0) c = String.fromCharCode(bits(8));
  else if (next === 1) c = String.fromCharCode(bits(16));
  else return next === 2 ? "" : null;
  dictionary[3] = c;
  let w = c,
    dictSize = 4,
    enlarge = 4,
    numBits = 3,
    length = 1;
  if (length > limit) throw new Error("Shared source exceeds the byte limit.");
  const output = [c];
  while (true) {
    if (index > input.length) return null;
    next = bits(numBits);
    if (next === 0 || next === 1) {
      dictionary[dictSize++] = String.fromCharCode(bits(next === 0 ? 8 : 16));
      next = dictSize - 1;
      enlarge--;
    } else if (next === 2) return output.join("");
    if (!enlarge) {
      enlarge = 2 ** numBits;
      numBits++;
    }
    let entry = dictionary[next];
    if (!entry) {
      if (next !== dictSize) return null;
      entry = w + w[0];
    }
    length += entry.length;
    if (length > limit) throw new Error("Shared source exceeds 5 MiB.");
    output.push(entry);
    dictionary[dictSize++] = w + entry[0];
    enlarge--;
    w = entry;
    if (!enlarge) {
      enlarge = 2 ** numBits;
      numBits++;
    }
  }
}
