const { test } = require('node:test');
const assert = require('node:assert/strict');
const Modl = require('../src/modl.js');
const Detector = require('../src/detector.js');

test('modl reserves attributes in order, chains edges and preserves quoted labels', () => {
  const parsed = Modl.parse(`white\na big square red /example.com "Node # -> A"\nb circle blue "green"\na -> b -> c small dashed purple /example.com "Link # ->"`);
  assert.deepEqual(parsed.errors, []);
  assert.equal(parsed.background, 'white');
  const a = parsed.nodes.get('a');
  assert.equal(a.size, 'big');
  assert.equal(a.shape, 'square');
  assert.equal(a.color, 'red');
  assert.equal(a.url, 'https://example.com');
  assert.equal(a.text, 'Node # -> A');
  assert.equal(parsed.nodes.get('b').text, 'green');
  assert.equal(parsed.edges.length, 2);
  assert.equal(parsed.edges[1].from, 'b');
  assert.equal(parsed.edges[1].to, 'c');
  assert.equal(parsed.edges[1].style, 'dashed');
  assert.equal(parsed.edges[1].size, 'small');
  assert.equal(parsed.edges[1].text, 'Link # ->');
});

test('quoted ids, concatenated words, repeated definitions and comments follow deployed grammar', () => {
  const parsed = Modl.parse(`"a b" none pink Hello\n"a b" # keep prior label\nx 'two '"words"\nx ""\n"a b"->x dotted teal # note`);
  assert.deepEqual(parsed.errors, []);
  assert.equal(parsed.nodes.get('a b').text, 'Hello');
  assert.equal(parsed.nodes.get('x').text, '');
  assert.equal(parsed.edges[0].from, 'a b');
  assert.equal(Modl.lexLine(`x "two "words`)[2].value, 'two words');
  assert.ok(Modl.parse('bad! circle red').errors[0].includes('Line 1'));
  assert.ok(Modl.parse('a ->').errors[0].includes('malformed'));
});

test('positions are independent finite XY copies, including prototype-like ids', () => {
  const input = JSON.parse('{"__proto__":[12,34],"constructor":[5,6],"bad":[null,3]}');
  const result = Modl.copyPositions(input);
  assert.equal(Object.getPrototypeOf(result), null);
  assert.deepEqual(result.__proto__, [12, 34]);
  result.constructor[0] = 100;
  assert.equal(input.constructor[0], 5);
  assert.equal('bad' in result, false);
});

test('modl detection resolves shared arrows but respects DOT and Python syntax', () => {
  for (const code of ['a -> b', 'a square red Hello', 'white', 'a circle blue "from manim import *"', '# comment\n"node one" -> "node two"']) assert.equal(Detector.detect(code).type, 'modl', code);
  assert.equal(Detector.detect('digraph { a -> b }').type, 'graphviz');
  assert.equal(Detector.detect('a -> b [label="modl"];').type, 'graphviz');
  assert.equal(Detector.detect('from manim import *\nText("a -> b")').type, 'manim');
});

test('deep zoom spans six orders and preserves the anchor even when clamped', () => {
  assert.equal(Modl.ZOOM_MAX / Modl.ZOOM_MIN, 1e6);
  const v = { scale: 1, tx: 72.125, ty: -93.875 };
  const center = [367.25, 191.125];
  const world = center.map((n, i) => (n - [v.tx, v.ty][i]) / v.scale);
  for (const factor of [1e-100, 1e100, 1e100, 1e-100, 1 / Modl.ZOOM_MIN]) {
    Modl.zoomViewport(v, factor, ...center);
    assert.ok(v.scale >= Modl.ZOOM_MIN && v.scale <= Modl.ZOOM_MAX);
    for (let i = 0; i < 2; i++) assert.ok(Math.abs(world[i] * v.scale + [v.tx, v.ty][i] - center[i]) < 1e-7);
  }
});

test('invalid zoom inputs leave the camera intact', () => {
  const v = { scale: 1, tx: 20, ty: 30 }, before = { ...v };
  for (const args of [[0,1,2], [-1,1,2], [NaN,1,2], [Infinity,1,2], [2,NaN,2], [2,1,Infinity], [2,1e308,1e308]]) {
    assert.equal(Modl.zoomViewport(v, ...args), false);
    assert.deepEqual(v, before);
  }
});

test('mixed zoom/pan round trips retain subpixel accuracy over 20000 operations', () => {
  const v = { scale: 1, tx: 0, ty: 0 };
  let seed = 29, maxError = 0;
  const random = () => ((seed = (1664525 * seed + 1013904223) >>> 0) / 2 ** 32);
  for (let i = 0; i < 10000; i++) {
    if (i % 1000 === 0) Modl.zoomViewport(v, [0.001,.01,.1,1,10,100,500][(i / 1000) % 7] / v.scale, 400, 225);
    v.tx += (random() - .5) * 300;
    v.ty += (random() - .5) * 300;
    const center = [random() * 800, random() * 450];
    const before = { ...v };
    const world = [(center[0] - v.tx) / v.scale, (center[1] - v.ty) / v.scale];
    Modl.zoomViewport(v, 1.2, ...center);
    Modl.zoomViewport(v, 1 / 1.2, ...center);
    maxError = Math.max(maxError, Math.abs(world[0] * v.scale + v.tx - center[0]), Math.abs(world[1] * v.scale + v.ty - center[1]));
    assert.ok(Math.abs(v.tx - before.tx) < 1e-6);
    assert.ok(Math.abs(v.ty - before.ty) < 1e-6);
  }
  assert.ok(maxError < 1e-6, `anchor drift ${maxError}px`);
});
