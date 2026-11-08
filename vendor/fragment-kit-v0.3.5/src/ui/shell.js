import { element, createDialog } from './dialog.js';

const compactLayouts = new WeakMap();

// Consumers can keep their own action/status nodes while sharing the compact layout.
export function compactShell({ header, toolbar, status }) {
  compactLayouts.get(header)?.();
  header.classList.add('fk-compact');
  const more = header.querySelector('.fk-more');
  if (toolbar) { toolbar.classList.add('fk-toolbar'); header.insertBefore(toolbar, more); }
  let destroy = () => {};
  if (status) {
    status.classList.add('fk-status');
    const document = header.ownerDocument, media = document.defaultView.matchMedia('(max-width: 767px)');
    const menu = document.getElementById(more?.getAttribute('aria-controls'))?.querySelector('.fk-dialog-body');
    const summary = element('span', '', { className: 'fk-status-summary', role: 'status', 'aria-live': 'polite' }, document);
    header.insertBefore(summary, more);
    const update = () => {
      const message = status.querySelector('[data-fk-primary-status], #status')?.textContent?.trim() ?? '';
      summary.textContent = message; summary.title = message; summary.hidden = !media.matches || !message;
      status.classList.toggle('fk-menu-status', Boolean(menu && media.matches));
      if (menu && media.matches) menu.append(status);
      else header.insertBefore(status, more);
    };
    const observer = new document.defaultView.MutationObserver(update);
    observer.observe(status, { childList: true, characterData: true, subtree: true });
    media.addEventListener('change', update); update();
    destroy = () => { media.removeEventListener('change', update); observer.disconnect(); summary.remove(); };
  }
  compactLayouts.set(header, destroy);
  return { header, toolbar, status, destroy };
}

export function createShell({ config, container = document.body, actions = [] }) {
  const header = element('header', null, { className: 'fk-header' });
  const brand = element('a', config.name, { className: 'fk-brand', href: config.canonicalOrigin });
  const navigation = element('nav', null, { 'aria-label': 'Resources', className: 'fk-nav' });
  const more = element('button', 'More', { type: 'button', className: 'fk-more', 'aria-haspopup': 'dialog', 'aria-controls': 'fk-more-drawer' });
  const drawer = createDialog('More', { id: 'fk-more-drawer' });
  more.onclick = () => { more.focus(); drawer.open(); };
  const links = [['Docs ↗', config.docs], ['Gallery ↗', config.gallery], ['GitHub ↗', `https://github.com/${config.repo}`]];
  for (const [title, href] of links) {
    navigation.append(element('a', title, { href, target: '_blank', rel: 'noopener noreferrer' }));
    drawer.body.append(element('a', title, { href, target: '_blank', rel: 'noopener noreferrer' }));
  }
  const toolbar = element('div', null, { className: 'fk-toolbar', role: 'toolbar', 'aria-label': 'Document actions' });
  for (const { label, onClick, extra = false, id } of actions) {
    const button = element('button', label, { type: 'button', ...(id ? { id } : {}), className: extra ? 'fk-mobile-extra' : '' });
    button.onclick = onClick; toolbar.append(button);
    if (extra) {
      const proxy = element('button', label, { type: 'button' });
      proxy.onclick = () => { drawer.dialog.close(); button.click(); }; drawer.body.append(proxy);
    }
  }
  const notice = element('div', null, { className: 'fk-notice-slot', id: 'domain-migration-slot' });
  const status = element('footer', null, { className: 'fk-status', role: 'status' });
  const offlineStatus = element('span', 'Offline setup pending', { id: 'offline-status' });
  const draftStatus = element('span', '', { id: 'draft-status' }); status.append(offlineStatus, draftStatus);
  header.append(brand, navigation, more);
  compactShell({ header, toolbar, status }); container.prepend(header, notice);
  return { header, toolbar, drawer, notice, status, offlineStatus, draftStatus,
    destroy() { compactLayouts.get(header)?.(); compactLayouts.delete(header); drawer.destroy(); for (const node of [header, toolbar, notice, status]) node.remove(); } };
}
