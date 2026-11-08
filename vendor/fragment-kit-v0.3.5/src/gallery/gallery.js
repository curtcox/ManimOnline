import { element } from '../ui/dialog.js';
import { safeURL } from '../core/config.js';

export function mountGallery({ container, catalog, urlState, base = globalThis.location?.href }) {
  const search = element('input', null, { type: 'search', 'aria-label': 'Search examples', placeholder: 'Search examples' });
  const tags = element('select', null, { 'aria-label': 'Filter by tag' });
  const all = element('option', 'All tags', { value: '' }); tags.append(all);
  for (const tag of [...new Set(catalog.flatMap(example => example.tags ?? []))].sort()) tags.append(element('option', tag, { value: tag }));
  const grid = element('div', null, { className: 'fk-gallery-grid' }), count = element('p', '', { role: 'status' });
  const filters = element('div', null, { className: 'fk-gallery-filters' }); filters.append(search, tags);
  function render() {
    const query = search.value.trim().toLowerCase();
    const matches = catalog.filter(example => (!tags.value || example.tags?.includes(tags.value)) && `${example.title} ${example.description} ${example.tags?.join(' ')}`.toLowerCase().includes(query));
    grid.replaceChildren(...matches.map(example => {
      const card = element('article', null, { className: 'fk-gallery-card' });
      if (example.cover) card.append(element('img', null, { src: safeURL(example.cover, base).href, alt: '', loading: 'lazy', width: 640, height: 360 }));
      card.append(element('h2', example.title), element('p', example.description ?? ''), element('small', example.tags?.join(' · ') ?? ''), element('a', 'Open', { href: urlState.build(example.document).href, 'aria-label': `Open ${example.title}` }));
      return card;
    }));
    count.textContent = `${matches.length} example${matches.length === 1 ? '' : 's'}`;
  }
  search.oninput = tags.onchange = render; container.append(filters, count, grid); render();
  return { render, destroy() { filters.remove(); count.remove(); grid.remove(); } };
}
