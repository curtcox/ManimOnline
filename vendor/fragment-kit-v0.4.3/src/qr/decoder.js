// UMD exports onto self in browsers; Node uses its CommonJS namespace.
import * as decoder from '../../vendor/jsqr/jsQR-fk.js';
export const decodeQr = (...args) => (decoder.default ?? globalThis.jsQR)(...args);
