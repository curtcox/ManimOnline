const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const Detector = require('../src/detector.js');
const { ExampleCatalog } = require('../src/examples.js');

test('all shipped gallery examples select their intended renderer', () => {
  for (const example of ExampleCatalog) {
    assert.equal(Detector.detect(fs.readFileSync(example.path, 'utf8')).type,
      example.id === 'dot' ? 'graphviz' : 'manim', example.path);
  }
});

test('DOT graph headers and quoted names ignore misleading labels and comments', () => {
  for (const source of [
    'digraph{ a -> b }', 'strict GRAPH "quoted name" { a -- b }',
    '// from manim import *\ndigraph { a [label="class Demo(Scene): self.play(Create(Circle()))"] }',
    '/* class Demo(Scene):\ndef construct(self): */ digraph { a -> b }',
    'digraph { a [label="escaped \\" import manim"] }'
  ]) assert.equal(Detector.detect(source).type, 'graphviz', source);
});

test('Manim ignores DOT snippets in strings, raw strings, docstrings, and comments', () => {
  for (const literal of ['"digraph { a -> b [shape=box] }"', "'graph { a -- b }'", 'r"digraph { a -> b }"', '"""digraph {\na -> b\n}"""']) {
    const source = `from manim import *\nclass Demo(Scene):\n    def construct(self):\n        Text(${literal})\n        # digraph { a -> b }`;
    assert.equal(Detector.detect(source).type, 'manim', literal);
  }
});

test('empty and descriptive-only inputs remain unknown, including incomplete literals', () => {
  for (const source of ['', ' ', '# from manim import *', '/* digraph { a -> b } */', '"from manim import *', '"""digraph { a -> b }']) {
    assert.equal(Detector.detect(source).type, 'unknown', source);
  }
  assert.equal(Detector.detect('class Demo(manim.Scene):\n def construct(self):\n  self.wait()').type, 'manim');
});

test('URL overrides accept established aliases and ignore invalid values', () => {
  for (const type of ['dot', 'graphviz']) assert.equal(Detector.getTypeFromURL(`?type=${type}`), 'graphviz');
  for (const type of ['manim', 'python']) assert.equal(Detector.getTypeFromURL(`?scene=Demo&type=${type}`), 'manim');
  for (const type of ['auto', 'unknown', 'MANIM', '']) assert.equal(Detector.getTypeFromURL(`?type=${type}`), null);
});
