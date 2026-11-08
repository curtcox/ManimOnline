import { decodeQr } from './decoder.js';

export function decodePixels({ data, width, height }) {
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 || width * height > 16_777_216 || data.length !== width * height * 4) throw new Error('Invalid or oversized QR image.');
  return decodeQr(data, width, height, { inversionAttempts: 'attemptBoth' })?.data ?? null;
}
export class QrScanner {
  constructor({ navigator = globalThis.navigator, document = globalThis.document, BarcodeDetector = globalThis.BarcodeDetector, timers = globalThis, decode = decodePixels } = {}) {
    Object.assign(this, { navigator, document, BarcodeDetector, timers, decode });
  }
  async detector() {
    try {
      if (!this.BarcodeDetector) return null;
      if (this.BarcodeDetector.getSupportedFormats && !(await this.BarcodeDetector.getSupportedFormats()).includes('qr_code')) return null;
      return new this.BarcodeDetector({ formats: ['qr_code'] });
    } catch { return null; }
  }
  async fromImage(blob) {
    if (!blob || !blob.type?.startsWith('image/') || blob.size > 20 * 1024 * 1024) throw new Error('Choose an image smaller than 20 MiB.');
    const image = await createImageBitmap(blob);
    try {
      if (image.width * image.height > 16_777_216) throw new Error('QR image dimensions are too large.');
      return await this.frame(image);
    } finally { image.close(); }
  }
  async frame(image, detector) {
    detector ??= await this.detector();
    if (detector) {
      try { const results = await detector.detect(image); if (results[0]?.rawValue) return results[0].rawValue; }
      catch { /* Unsupported source/decoder failure: use jsQR. */ }
    }
    const width = image.videoWidth ?? image.width, height = image.videoHeight ?? image.height;
    if (!width || !height) return null;
    const ratio = Math.min(1, 2048 / Math.max(width, height));
    const canvas = this.document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(width * ratio)); canvas.height = Math.max(1, Math.round(height * ratio));
    const context = canvas.getContext('2d', { willReadFrequently: true });
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    return this.decode(context.getImageData(0, 0, canvas.width, canvas.height));
  }
  async fromCamera(video, { onResult, onError = () => {}, signal } = {}) {
    if (!this.navigator?.mediaDevices?.getUserMedia) throw new Error('Camera scanning is unavailable. Open an image instead.');
    let stopped = false, timer, stream;
    const stop = () => {
      stopped = true; this.timers.clearTimeout(timer);
      stream?.getTracks().forEach(track => track.stop());
      video.srcObject = null;
      signal?.removeEventListener('abort', stop);
    };
    if (signal?.aborted) return stop;
    signal?.addEventListener('abort', stop, { once: true });
    try {
      stream = await this.navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
      if (stopped) { stop(); return stop; }
      video.srcObject = stream; video.muted = true; video.playsInline = true;
      await video.play();
      const detector = await this.detector();
      const scan = async () => {
        if (stopped) return;
        try {
          const result = await this.frame(video, detector);
          if (stopped) return;
          if (result) {
            stop();
            try { await onResult(result); } catch (error) { onError(error); }
            return;
          }
        } catch (error) { if (!stopped) onError(error); }
        if (!stopped) timer = this.timers.setTimeout(scan, 125);
      };
      void scan(); return stop;
    } catch (error) { stop(); throw error; }
  }
}
export const scan = new QrScanner();
