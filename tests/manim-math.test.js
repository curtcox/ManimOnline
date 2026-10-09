const { test, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const math = require('../src/manim-math.js');
const frame = (...mobjects) => ({ mobjects });
const formula = text => ({ type: 'mathtex', text });
function svgResult(expression, box = '0 -700 1000 900') {
  const svg = { getAttribute: () => box, querySelectorAll: () => [], outerHTML: `<svg viewBox="${box}"><path d="${expression}"/></svg>` };
  return { querySelector: selector => selector === 'svg' ? svg : null };
}

beforeEach(() => math.cache.clear());

test('math preprocessing deduplicates formulas across frames and nested groups', async () => {
  const compiled = [];
  const scene = { frames: [frame(formula('x'), { type: 'vgroup', children: [formula('y')] }), frame(formula('x'))] };
  const glyphs = await math.prepare(scene, () => true, async () => ({ tex2svgPromise: async text => {
    compiled.push(text); return svgResult(text);
  } }));
  assert.deepEqual(compiled, ['x', 'y']);
  assert.deepEqual(glyphs.get('x').viewBox, [0, -700, 1000, 900]);
});

test('plain scenes do not load math dependencies', async () => {
  const glyphs = await math.prepare({ frames: [frame({ type: 'text', text: 'hello' })] }, () => true,
    () => assert.fail('no math library needed'));
  assert.equal(glyphs.size, 0);
});

test('editing discards pending math output', async () => {
  let current = true;
  const scene = { frames: [frame(formula('x'), formula('y'))] };
  const result = await math.prepare(scene, () => current, async () => ({ tex2svgPromise: async text => {
    current = false; return svgResult(text);
  } }));
  assert.equal(result, null);
});

test('math limits reject oversized expressions and external or custom commands', () => {
  for (const text of ['x'.repeat(4097), String.raw`\require{html}`, String.raw`\href{https://example.com}{x}`, String.raw`\def\x{y}`]) {
    assert.throws(() => math.expressions({ frames: [frame(formula(text))] }));
  }
  assert.throws(() => math.expressions({ frames: [frame(...Array.from({ length: 65 }, (_, i) => formula(`x_${i}`)))] }), /64/);
});

test('TeX and invalid SVG geometry failures are explicit', async () => {
  const scene = { frames: [frame(formula('x'))] };
  await assert.rejects(math.prepare(scene, () => true, async () => ({ tex2svgPromise: () => { throw new Error('Unknown macro'); } })), /MathTex: Unknown macro/);
  await assert.rejects(math.prepare(scene, () => true, async () => ({ tex2svgPromise: async () => svgResult('x', '0 0 NaN 1') })), /Invalid math geometry/);
});

test('stale requests skip dependency loading and oversized glyph output fails', async () => {
  const scene = { frames: [frame(formula('x'))] };
  assert.equal(await math.prepare(scene, () => false, () => assert.fail('stale load')), null);
  await assert.rejects(math.prepare(scene, () => true, async () => ({ tex2svgPromise: async () =>
    svgResult('x'.repeat(2 * 1024 * 1024)) })), /Math output is too large/);
});

test('unsupported glyph geometry is rejected before player construction', async () => {
  const scene = { frames: [frame(formula('x'))] };
  await assert.rejects(math.prepare(scene, () => true, async () => ({ tex2svgPromise: async () => ({
    querySelector: selector => selector === 'svg' ? { querySelectorAll: () => [{ localName: 'text' }] } : null
  }) })), /glyph or SVG feature/);
});

test('compiled formulas are cached across renders and expose em metrics', async () => {
  let compiles = 0;
  const load = async () => ({ tex2svgPromise: async text => { compiles++; return svgResult(text); } });
  const scene = { frames: [frame(formula('z'))] };
  const first = await math.prepare(scene, () => true, load);
  const second = await math.prepare(scene, () => true, load);
  assert.equal(compiles, 1);
  assert.equal(second.get('z'), first.get('z'));
  // Without a layout engine there is no ink box, so Python keeps its estimate.
  assert.equal(first.get('z').bbox, null);
  assert.deepEqual(math.metrics(new Map([['w', { bbox: [10, -600, 450, 700] }], ['v', { bbox: null }]])), { w: [0.45, 0.7] });
});

test('multi-part formulas report part centers relative to the ink center', () => {
  const glyphs = new Map([['\\class{manim-part-0}{a} \\class{manim-part-1}{b}', { bbox: [0, -800, 2000, 1000],
    parts: [{ bbox: [0, -800, 900, 1000] }, { bbox: [1100, -700, 900, 600] }] }]]);
  const [entry] = Object.values(math.metrics(glyphs));
  assert.deepEqual(entry.slice(0, 2), [2, 1]);
  assert.deepEqual(entry[2].map(part => part.map(v => Math.round(v * 1000) / 1000 + 0)), [[-0.55, 0, 0.9, 1], [0.55, 0.1, 0.9, 0.6]]);
});

test('glyph boxes are reported in TeX order with their part, relative to the ink center', () => {
  const glyphs = new Map([['x^2', { bbox: [0, -800, 1000, 1000],
    glyphs: [{ bbox: [0, -500, 500, 500], part: -1 }, { bbox: [600, -800, 400, 400], part: -1 }] }]]);
  const [entry] = Object.values(math.metrics(glyphs));
  assert.equal(entry[2], null);
  assert.deepEqual(entry[3].map(glyph => glyph.map(v => Math.round(v * 1000) / 1000 + 0)),
    [[-0.25, -0.05, 0.5, 0.5, -1], [0.3, 0.3, 0.4, 0.4, -1]]);
});
