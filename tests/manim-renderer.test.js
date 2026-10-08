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

test('creation traces a normalized outline and completed objects have no dash state', () => {
  const partial = renderer.renderMobject({ type: 'square', draw_progress: 0.25 });
  assert.equal(partial.getAttribute('pathLength'), '1');
  assert.equal(partial.getAttribute('stroke-dasharray'), '1 1');
  assert.equal(partial.getAttribute('stroke-dashoffset'), '0.75');
  assert.equal(partial.getAttribute('vector-effect'), 'none');
  const complete = renderer.renderMobject({ type: 'square' });
  assert.equal(complete.getAttribute('stroke-dasharray'), null);
});

test('arrow shaft and head both receive creation progress', () => {
  const arrow = renderer.renderMobject({ type: 'arrow', draw_progress: 0.5 });
  assert.equal(arrow.children.length, 2);
  for (const leaf of arrow.children) {
    assert.equal(leaf.getAttribute('stroke-dashoffset'), '0.5');
    assert.equal(leaf.getAttribute('pathLength'), '1');
    assert.equal(leaf.getAttribute('vector-effect'), 'none');
  }
});

test('groups preserve scalable creation dashes on their children', () => {
  const group = renderer.renderMobject({ type: 'vgroup', children: [
    { type: 'circle', draw_progress: 0.5 }, { type: 'square' }
  ] });
  assert.equal(group.children[0].getAttribute('vector-effect'), 'none');
  assert.equal(group.children[1].getAttribute('vector-effect'), 'non-scaling-stroke');
});
