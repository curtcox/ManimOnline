import { element } from './dialog.js';
let nextId = 0;
export function mountMobileTabs({ panels, container, breakpoint = 768, window = globalThis.window, onChange = () => {} }) {
  const id = ++nextId, media = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
  const tabs = element('div', null, { className: 'fk-tabs', role: 'tablist', 'aria-label': 'Workspace panels' });
  let active = 0;
  const buttons = panels.map(({ label, panel }, index) => {
    panel.id ||= `fk-panel-${id}-${index}`;
    const button = element('button', label, { type: 'button', role: 'tab', id: `fk-tab-${id}-${index}`, 'aria-controls': panel.id });
    panel.setAttribute('aria-labelledby', button.id); panel.setAttribute('role', 'tabpanel');
    button.onclick = () => select(index); tabs.append(button); return button;
  });
  function update() {
    tabs.hidden = !media.matches;
    panels.forEach(({ panel }, index) => {
      panel.hidden = media.matches && index !== active;
      buttons[index].setAttribute('aria-selected', String(index === active)); buttons[index].tabIndex = index === active ? 0 : -1;
    });
  }
  function select(index) { active = index; update(); onChange(index); }
  const keyboard = event => {
    const index = buttons.indexOf(window.document.activeElement);
    const target = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : event.key === 'ArrowRight' ? (index + 1) % buttons.length : event.key === 'ArrowLeft' ? (index + buttons.length - 1) % buttons.length : null;
    if (target !== null) { event.preventDefault(); select(target); buttons[target].focus(); }
  };
  tabs.addEventListener('keydown', keyboard);
  const viewport = () => {
    const visual = window.visualViewport;
    window.document.documentElement.style.setProperty('--fk-viewport-height', `${visual?.height ?? window.innerHeight}px`);
    onChange(active);
  };
  media.addEventListener('change', update);
  window.visualViewport?.addEventListener('resize', viewport);
  window.visualViewport?.addEventListener('scroll', viewport);
  window.addEventListener('resize', viewport);
  container.prepend(tabs); update(); viewport();
  return { select, destroy() {
    tabs.remove(); panels.forEach(({ panel }) => { panel.hidden = false; });
    media.removeEventListener('change', update); window.removeEventListener('resize', viewport);
    window.visualViewport?.removeEventListener('resize', viewport); window.visualViewport?.removeEventListener('scroll', viewport);
  } };
}
