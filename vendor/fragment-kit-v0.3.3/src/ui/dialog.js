let sequence = 0;
export function element(tag, text, attributes = {}, document = globalThis.document) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  for (const [name, value] of Object.entries(attributes)) {
    if (name === 'className') node.className = value;
    else node.setAttribute(name, String(value));
  }
  return node;
}
export function createDialog(title, { document = globalThis.document, id = `fk-dialog-${++sequence}`, onClose = () => {} } = {}) {
  const dialog = element('dialog', null, { id, className: 'fk-dialog', 'aria-labelledby': id + '-title' }, document);
  const heading = element('h2', title, { id: id + '-title' }, document);
  const body = element('div', null, { className: 'fk-dialog-body' }, document);
  const close = element('button', 'Close', { type: 'button', className: 'fk-close' }, document);
  const previous = { value: null };
  close.onclick = () => dialog.close();
  dialog.addEventListener('close', () => { onClose(); if (previous.value?.isConnected) previous.value.focus(); });
  dialog.append(heading, body, close); document.body.append(dialog);
  return { dialog, body, close,
    open() { previous.value = document.activeElement; if (!dialog.open) dialog.showModal(); },
    destroy() { if (dialog.open) dialog.close(); dialog.remove(); } };
}
export function download(blob, fileName, document = globalThis.document) {
  const url = URL.createObjectURL(blob), anchor = element('a', null, { href: url, download: fileName }, document);
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
