const { test } = require('node:test');
const assert = require('node:assert/strict');
const math = require('../src/manim-math.js');
const frame = (...mobjects) => ({ mobjects });
const formula = text => ({ type: 'mathtex', text });
function svgResult(expression, box = '0 -700 1000 900') {
  const svg = { getAttribute: () => box, querySelectorAll: () => [], outerHTML: `<svg viewBox="${box}"><path d="${expression}"/></svg>` };
  return { querySelector: selector => selector === 'svg' ? svg : null };
}

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
