const test = require('node:test');
const assert = require('node:assert/strict');
const typst = require('../src/manim-typst.js');

test('typst.ts output keeps geometry but drops the viewer stylesheet and selection overlays', () => {
  const svg = '<svg><style>.a{}</style><g><use href="#g1"/><foreignObject><div>x</div></foreignObject></g>' +
    '<script type="text/javascript">if (a &amp;&amp; b < c) {}</script></svg>';
  assert.equal(typst.clean(svg), '<svg><g><use href="#g1"/></g></svg>');
});

test('requested documents compile once and are cached', async () => {
  let compiles = 0;
  const load = async () => ({ svg: async ({ mainContent }) => { compiles++; return `<svg>${mainContent.length}</svg>`; } });
  const first = await typst.compile(['a', 'bb'], () => true, load);
  assert.deepEqual(first, { a: '<svg>1</svg>', bb: '<svg>2</svg>' });
  await typst.compile(['a'], () => true, load);
  assert.equal(compiles, 2);
  assert.equal(await typst.compile(['c'], () => false, load), null);
  assert.deepEqual(await typst.compile([], () => true, load), {});
});

test('compile errors and oversized requests are explicit', async () => {
  const load = async () => ({ svg: async () => { throw new Error('unknown variable'); } });
  await assert.rejects(typst.compile(['#oops'], () => true, load), /Typst: unknown variable/);
  await assert.rejects(typst.compile(Array.from({ length: 65 }, (_, i) => String(i)), () => true, load), /64 distinct/);
  await assert.rejects(typst.compile(['x'.repeat(100001)], () => true, load), /100000 characters/);
});
