import { element } from './dialog.js';
let nextId = 0;
export function mountMobileTabs({ panels, container, breakpoint = 768, desktop = false, window = globalThis.window, onChange = () => {} }) {
  const id = ++nextId, media = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
  const tabs = element('div', null, { className: 'fk-tabs', role: 'tablist', 'aria-label': 'Workspace panels' });
  let active = 0, split = desktop && !media.matches;
  const workspace = panels[0]?.panel.parentElement;
  const buttons = panels.map(({ label, panel }, index) => {
    panel.id ||= `fk-panel-${id}-${index}`;
    const button = element('button', label, { type: 'button', role: 'tab', id: `fk-tab-${id}-${index}`, 'aria-controls': panel.id });
    panel.setAttribute('aria-labelledby', button.id); panel.setAttribute('role', 'tabpanel');
    button.onclick = () => select(index); tabs.append(button); return button;
  });
  const splitButton = desktop ? element('button', 'Split', { type: 'button', role: 'tab', id: `fk-tab-${id}-split`, 'aria-controls': panels.map(({ panel }) => panel.id).join(' ') }) : null;
  if (splitButton) { splitButton.onclick = () => select('split'); tabs.append(splitButton); buttons.push(splitButton); }
  function update() {
    tabs.hidden = !desktop && !media.matches;
    if (desktop && workspace) {
      workspace.dataset.fkView = split ? 'split' : 'single';
      workspace.style.setProperty('--fk-panel-count', panels.length);
    }
    panels.forEach(({ panel }, index) => {
      panel.hidden = (desktop ? !split : media.matches) && index !== active;
      if (desktop) { panel.classList.add('fk-view-panel'); panel.setAttribute('aria-labelledby', split ? splitButton.id : buttons[index].id); }
      buttons[index].setAttribute('aria-selected', String(!split && index === active)); buttons[index].tabIndex = !split && index === active ? 0 : -1;
    });
    if (splitButton) { splitButton.setAttribute('aria-selected', String(split)); splitButton.tabIndex = split ? 0 : -1; }
  }
  function select(index) {
    if (index !== 'split' && (!Number.isInteger(index) || index < 0 || index >= panels.length)) return;
    if (index === 'split' && !desktop) return;
    const changed = split !== (index === 'split') || (!split && active !== index);
    split = index === 'split'; if (!split) active = index;
    update(); if (changed) onChange(split ? -1 : active);
  }
  const keyboard = event => {
    const index = buttons.indexOf(window.document.activeElement);
    const target = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : event.key === 'ArrowRight' ? (index + 1) % buttons.length : event.key === 'ArrowLeft' ? (index + buttons.length - 1) % buttons.length : null;
    if (target !== null) { event.preventDefault(); select(desktop && target === panels.length ? 'split' : target); buttons[target].focus(); }
  };
  tabs.addEventListener('keydown', keyboard);
  const viewport = () => {
    const visual = window.visualViewport;
    window.document.documentElement.style.setProperty('--fk-viewport-height', `${visual?.height ?? window.innerHeight}px`);
    onChange(split ? -1 : active);
  };
  media.addEventListener('change', update);
  window.visualViewport?.addEventListener('resize', viewport);
  window.visualViewport?.addEventListener('scroll', viewport);
  window.addEventListener('resize', viewport);
  container.prepend(tabs); update(); viewport();
  return { select, getView: () => split ? 'split' : active, destroy() {
    tabs.remove(); panels.forEach(({ panel }) => { panel.hidden = false; panel.classList.remove('fk-view-panel'); });
    if (desktop && workspace) { delete workspace.dataset.fkView; workspace.style.removeProperty('--fk-panel-count'); }
    media.removeEventListener('change', update); window.removeEventListener('resize', viewport);
    window.visualViewport?.removeEventListener('resize', viewport); window.visualViewport?.removeEventListener('scroll', viewport);
  } };
}
