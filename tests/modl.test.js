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
