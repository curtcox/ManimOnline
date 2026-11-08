import { createDialog, element, download } from '../ui/dialog.js';
import { encodeQr, qrSvg, qrPng, qrNotes } from './encode.js';
import { QrScanner } from './scan.js';
import { acceptScannedText } from './accept.js';

export function createQrDialog({ config, registry = [], urlState, onLoad, onSave, scanner = new QrScanner() }) {
  let controller, revision = 0, qr, href;
  const ui = createDialog('QR code', { id: 'qr-dialog', onClose: () => { controller?.abort(); revision++; video.hidden = true; } });
  const code = element('div', null, { id: 'qr-code', className: 'fk-qr' });
  const notes = element('p', '', { role: 'status', id: 'qr-notes' });
  const svg = element('button', 'Download SVG', { type: 'button' }), png = element('button', 'Download PNG', { type: 'button' });
  const save = element('button', 'Save to HashBin for a scannable link', { type: 'button' });
  const camera = element('button', 'Scan a code', { type: 'button', id: 'qr-scan' });
  const file = element('input', null, { type: 'file', accept: 'image/*', 'aria-label': 'Open QR image', id: 'qr-image' });
  const label = element('label', 'Open image'); label.append(file);
  const video = element('video', null, { 'aria-label': 'QR camera preview' }); video.hidden = true;
  const result = element('div', null, { role: 'status', className: 'fk-scanned' });
  ui.body.append(code, notes, svg, png, save, camera, label, video, result);
  function setLink(link) {
    href = link; qr = encodeQr(href); code.replaceChildren();
    if (qr) code.append(new DOMParser().parseFromString(qrSvg(qr), 'image/svg+xml').documentElement);
    notes.textContent = qrNotes(href, qr); svg.disabled = png.disabled = !qr;
    save.hidden = Boolean(qr && qr.version <= 20);
    save.disabled = !onSave;
  }
  async function accept(value) {
    const outcome = acceptScannedText(value, { config, registry, urlState });
    result.replaceChildren();
    if (outcome.kind === 'app' || outcome.kind === 'cid') { await onLoad(outcome); ui.dialog.close(); }
    else if (outcome.kind === 'sibling') result.append(element('a', `Open in ${outcome.name}`, { href: outcome.href, target: '_blank', rel: 'noopener noreferrer' }));
    else {
      const copy = element('button', 'Copy text', { type: 'button' });
      copy.onclick = () => navigator.clipboard.writeText(outcome.text).catch(error => { notes.textContent = error.message; });
      result.append(element('pre', outcome.text), copy);
    }
  }
  async function image(blob) {
    const current = ++revision;
    try {
      const value = await scanner.fromImage(blob);
      if (current !== revision || !ui.dialog.open) return;
      if (!value) throw new Error('No QR code was found in this image.');
      await accept(value);
    } catch (error) { if (current === revision) notes.textContent = error.message; }
  }
  file.onchange = () => { if (file.files[0]) void image(file.files[0]); file.value = ''; };
  ui.dialog.addEventListener('paste', event => {
    const blob = [...(event.clipboardData?.items ?? [])].find(item => item.type.startsWith('image/'))?.getAsFile();
    if (blob) { event.preventDefault(); void image(blob); }
  });
  ui.dialog.addEventListener('dragover', event => event.preventDefault());
  ui.dialog.addEventListener('drop', event => { event.preventDefault(); if (event.dataTransfer.files[0]) void image(event.dataTransfer.files[0]); });
  camera.onclick = async () => {
    controller?.abort(); controller = new AbortController(); const current = ++revision;
    video.hidden = false; notes.textContent = 'Point your camera at a QR code.';
    try { await scanner.fromCamera(video, { signal: controller.signal, onResult: value => current === revision && accept(value), onError: error => { if (current === revision) notes.textContent = error.message; } }); }
    catch (error) { if (current === revision) notes.textContent = `Camera could not start: ${error.message} Open an image instead.`; }
  };
  svg.onclick = () => download(new Blob([qrSvg(qr)], { type: 'image/svg+xml' }), config.slug + '-qr.svg');
  png.onclick = async () => { try { download(await qrPng(qr), config.slug + '-qr.png'); } catch (error) { notes.textContent = error.message; } };
  save.onclick = async () => { try { const link = await onSave(); if (link) setLink(link); } catch (error) { notes.textContent = error.message; } };
  return { ...ui, setLink, open(link) { result.replaceChildren(); setLink(link); ui.open(); } };
}
