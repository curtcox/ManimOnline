/** Linear-time unified preview: unchanged edges, then the changed region. Text only. */
export function diff(before, after) {
  const a = JSON.stringify(before) === JSON.stringify(after) ? [] : String(before.src).split('\n');
  const b = String(after.src).split('\n');
  if (!a.length) return 'No changes.';
  let start = 0, end = 0;
  while (start < Math.min(a.length, b.length) && a[start] === b[start]) start++;
  while (end < Math.min(a.length, b.length) - start && a[a.length - 1 - end] === b[b.length - 1 - end]) end++;
  const out = [`@@ -${start + 1},${a.length - start - end} +${start + 1},${b.length - start - end} @@`];
  out.push(...a.slice(Math.max(0, start - 2), start).map(l => ' ' + l));
  // Avoid spread on untrusted numbers of lines.
  for (const line of a.slice(start, a.length - end)) out.push('-' + line);
  for (const line of b.slice(start, b.length - end)) out.push('+' + line);
  for (const line of b.slice(b.length - end, b.length - end + 2)) out.push(' ' + line);
  if (JSON.stringify({ ...before, src: '' }) !== JSON.stringify({ ...after, src: '' })) out.push('Settings: ' + JSON.stringify({ ...before, src: undefined }) + ' → ' + JSON.stringify({ ...after, src: undefined }));
  return out.join('\n');
}
