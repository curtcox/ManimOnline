const { test } = require('node:test');
const assert = require('node:assert/strict');
const renderer = require('../src/manim-renderer.js');

class Element {
  constructor(tag) { this.tag = tag; this.attributes = {}; this.children = []; this.style = {}; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  appendChild(child) { this.children.push(child); }
  querySelectorAll() { return this.children.flatMap(child => [child, ...child.querySelectorAll()]); }
}
global.document = { createElementNS: (_namespace, tag) => new Element(tag) };

test('SVG places a rotation and scale around the geometry center', () => {
  const line = renderer.renderMobject({ type: 'line', start: [1, 0], end: [3, 0],
    position: [2, 0], geometry_center: [2, 0], geometry_scale: 2, angle: Math.PI / 2 });
  assert.equal(line.getAttribute('x1'), '50');
  assert.equal(line.getAttribute('x2'), '150');
  assert.match(line.getAttribute('transform'), /translate\(100, 0\) translate\(100, 0\) rotate\(90\) scale\(2\) translate\(-100, 0\)/);
  assert.equal(line.getAttribute('vector-effect'), 'non-scaling-stroke');
});

test('nested transforms preserve text orientation and zero scale', () => {
  const group = renderer.renderMobject({ type: 'vgroup', geometry_scale: 0, children: [
    { type: 'text', text: 'Hello', angle: Math.PI / 2, geometry_scale: 2 }
  ] });
  assert.match(group.getAttribute('transform'), /scale\(0\)/);
  const text = group.children[0];
  assert.match(text.getAttribute('transform'), /rotate\(90\).*scale\(2\).*scale\(1, -1\)/);
  assert.equal(text.textContent, 'Hello');
});
