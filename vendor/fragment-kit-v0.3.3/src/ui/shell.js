import { element, createDialog } from './dialog.js';

export function createShell({ config, container = document.body, actions = [] }) {
  const header = element('header', null, { className: 'fk-header' });
  const brand = element('a', config.name, { className: 'fk-brand', href: config.canonicalOrigin });
  const navigation = element('nav', null, { 'aria-label': 'Resources', className: 'fk-nav' });
  const more = element('button', 'More', { type: 'button', className: 'fk-more', 'aria-haspopup': 'dialog', 'aria-controls': 'fk-more-drawer' });
  const drawer = createDialog('More', { id: 'fk-more-drawer' });
  more.onclick = () => drawer.open();
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
  header.append(brand, navigation, more); container.prepend(header, notice, toolbar); container.append(status);
  return { header, toolbar, drawer, notice, status, offlineStatus, draftStatus,
    destroy() { drawer.destroy(); for (const node of [header, toolbar, notice, status]) node.remove(); } };
}
