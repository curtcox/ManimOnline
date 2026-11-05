import fs from 'node:fs/promises';
/* Renders docs/*.md to formatted docs/*.html pages; --check fails if any page is stale. */
const root = new URL('../', import.meta.url);
const escape = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
function href(url) {
  if (!/^(?:[a-z]+:|#|\/)/i.test(url)) url = url.replace(/^([^#?]*)\.md(?=$|[#?])/, '$1.html');
  return escape(url);
}
function inline(text) {
  const codes = [];
  text = text.replace(/`([^`]+)`/g, (_, code) => '\0' + (codes.push('<code>' + escape(code) + '</code>') - 1) + '\0');
  return escape(text)
    .replace(/&lt;br&gt;/g, '<br>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, url) => '<a href="' + href(url.replace(/&amp;/g, '&')) + '">' + label + '</a>')
    .replace(/\0(\d+)\0/g, (_, index) => codes[index]);
}
const cells = line => line.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim());
function render(markdown) {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n'), html = [];
  let title = '';
  for (let i = 0; i < lines.length;) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    let match;
    if ((match = line.match(/^```(\w*)/))) {
      const code = [];
      for (i++; i < lines.length && !lines[i].startsWith('```'); i++) code.push(lines[i]);
      i++;
      html.push('<pre><code' + (match[1] ? ' class="language-' + match[1] + '"' : '') + '>' + escape(code.join('\n')) + '</code></pre>');
    } else if ((match = line.match(/^(#{1,6})\s+(.*)$/))) {
      if (!title) title = match[2].replace(/[`*]/g, '');
      html.push('<h' + match[1].length + '>' + inline(match[2]) + '</h' + match[1].length + '>'); i++;
    } else if (line.startsWith('|') && /^\s*\|?\s*:?-+/.test(lines[i + 1] || '')) {
      const head = cells(line).map(cell => '<th>' + inline(cell) + '</th>').join(''), rows = [];
      for (i += 2; i < lines.length && lines[i].startsWith('|'); i++) rows.push('<tr>' + cells(lines[i]).map(cell => '<td>' + inline(cell) + '</td>').join('') + '</tr>');
      html.push('<div class="table"><table><thead><tr>' + head + '</tr></thead><tbody>' + rows.join('') + '</tbody></table></div>');
    } else if (/^(?:[-*]|\d+\.)\s/.test(line)) {
      const ordered = /^\d/.test(line), items = [];
      for (; i < lines.length && /^(?:[-*]|\d+\.)\s/.test(lines[i]); i++) items.push('<li>' + inline(lines[i].replace(/^(?:[-*]|\d+\.)\s+/, '')) + '</li>');
      html.push((ordered ? '<ol>' : '<ul>') + items.join('') + (ordered ? '</ol>' : '</ul>'));
    } else {
      const text = [];
      for (; i < lines.length && lines[i].trim() && !/^(?:#{1,6}\s|```|\||[-*]\s|\d+\.\s)/.test(lines[i]); i++) text.push(lines[i].trim());
      html.push('<p>' + inline(text.join(' ')) + '</p>');
    }
  }
  return { title, body: html.join('\n') };
}
const stale = [];
for (const name of (await fs.readdir(new URL('docs/', root))).filter(name => name.endsWith('.md')).sort()) {
  const { title, body } = render(await fs.readFile(new URL('docs/' + name, root), 'utf8'));
  const page = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#236c60"><title>' + escape(title) + ' · ManimOnline</title><link rel="stylesheet" href="../src/docs.css?v=1"></head><body><header><a class="brand" href="../">ManimOnline</a><a href="../gallery.html">Sample gallery ↗</a></header><main>\n<!-- Generated from docs/' + name + ' by npm run docs. -->\n' + body + '\n</main></body></html>\n';
  const target = new URL('docs/' + name.replace(/\.md$/, '.html'), root);
  if (process.argv.includes('--check')) {
    if (await fs.readFile(target, 'utf8').catch(() => '') !== page) stale.push(name);
  } else await fs.writeFile(target, page);
}
if (stale.length) throw new Error('Docs pages are stale for ' + stale.join(', ') + '. Run npm run docs.');
console.log('Docs pages are current.');
