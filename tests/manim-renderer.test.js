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

test('math glyphs render with transforms, styles, and no external SVG content', () => {
  const path = new Element('path');
  path.localName = 'path';
  path.setAttribute('d', 'M 0 0 L 1000 0');
  path.setAttribute('onclick', 'bad()');
  path.hasAttribute = name => path.getAttribute(name) !== null;
  global.DOMParser = class { parseFromString() { return { documentElement: { children: [path] } }; } };
  const glyphs = new Map([['x', { svg: '<svg/>', viewBox: [0, -700, 1000, 900] }]]);
  const group = renderer.renderMobject({ type: 'vgroup', children: [
    { type: 'mathtex', text: 'x', font_size: 48, fill_color: '#FF0000', position: [2, 1, 0] }
  ] }, glyphs);
  const shape = group.children[0];
  assert.match(shape.getAttribute('transform'), /translate\(100, 50\).*scale\(1, -1\) scale\(0.048\)/);
  assert.equal(shape.getAttribute('fill'), '#FF0000');
  assert.equal(shape.children[0].getAttribute('d'), 'M 0 0 L 1000 0');
  assert.equal(shape.children[0].getAttribute('onclick'), null);
  path.localName = 'script';
  assert.throws(() => renderer.renderMobject({ type: 'mathtex', text: 'x' }, glyphs), /Unsupported math SVG/);
  assert.throws(() => renderer.renderMobject({ type: 'mathtex', text: 'y' }, glyphs), /not been prepared/);
  delete global.DOMParser;
});

test('primitive fill and stroke channels render independently, including zero opacity', () => {
  for (const type of ['circle', 'arc', 'square', 'rectangle', 'triangle', 'polygon', 'text']) {
    const shape = renderer.renderMobject({ type, fill_color: '#FF0000', stroke_color: '#00FF00',
      fill_opacity: 0.4, stroke_opacity: 0, stroke_width: 3 });
    assert.equal(shape.getAttribute('fill'), '#FF0000');
    assert.equal(shape.getAttribute('stroke'), '#00FF00');
    assert.equal(shape.getAttribute('stroke-opacity'), '0');
    assert.equal(shape.getAttribute('stroke-width'), '3');
    assert.equal(shape.getAttribute('fill-opacity'), '0.4');
  }
});

test('line and arrow outlines use stroke channels and keep open heads unfilled', () => {
  const line = renderer.renderMobject({ type: 'line', color: '#FFFFFF', stroke_color: '#FF0000', stroke_opacity: 0.3 });
  assert.equal(line.getAttribute('stroke'), '#FF0000');
  const arrow = renderer.renderMobject({ type: 'arrow', fill_color: '#00FF00', stroke_color: '#FF0000', stroke_opacity: 0.3 });
  for (const leaf of arrow.children) {
    assert.equal(leaf.getAttribute('stroke'), '#FF0000');
    assert.equal(leaf.getAttribute('stroke-opacity'), '0.3');
  }
  assert.equal(arrow.children[1].getAttribute('fill'), 'none');
});

test('group container does not overwrite child styles or compound channel opacity', () => {
  const group = renderer.renderMobject({ type: 'vgroup', fill_color: '#FFFFFF', stroke_opacity: 0.5,
    children: [{type: 'circle', fill_color: '#FF0000', fill_opacity: 0.5, stroke_opacity: 0.5}] });
  assert.equal(group.getAttribute('opacity'), '1');
  assert.equal(group.getAttribute('stroke-opacity'), null);
  assert.equal(group.children[0].getAttribute('fill'), '#FF0000');
  assert.equal(group.children[0].getAttribute('stroke-opacity'), '0.5');
});

test('arc SVG traces the counterclockwise quarter and preserves creation styles', () => {
  const arc = renderer.renderMobject({ type: 'arc', radius: 2, start_angle: 0,
    arc_angle: Math.PI / 2, color: '#58C4DD', draw_progress: 0.5 });
  const d = arc.getAttribute('d');
  assert.match(d, /^M 100,0 A 100,100 0 0 1 /);
  const end = d.split(' ').at(-1).split(',').map(Number);
  assert.ok(Math.abs(end[0]) < 1e-10);
  assert.equal(end[1], 100);
  assert.equal(arc.getAttribute('stroke-dashoffset'), '0.5');
  assert.equal(arc.getAttribute('stroke'), '#58C4DD');
  assert.equal(arc.getAttribute('fill-opacity'), '0');
});

test('full-turn and major arcs use distinct bounded SVG segments', () => {
  const full = renderer.renderMobject({ type: 'arc', arc_angle: -2 * Math.PI });
  assert.equal(full.getAttribute('d').split(' A ').length, 3);
  assert.equal((full.getAttribute('d').match(/ 0 0 0 /g) || []).length, 2);
  const major = renderer.renderMobject({ type: 'arc', arc_angle: 1.5 * Math.PI });
  assert.equal(major.getAttribute('d').split(' A ').length, 3);
  assert.ok(!major.getAttribute('d').includes('Z'));
});

test('zero radius and zero sweep arcs do not emit invalid arc commands', () => {
  for (const props of [{ radius: 0 }, { arc_angle: 0 }]) {
    const arc = renderer.renderMobject({ type: 'arc', ...props });
    assert.ok(!arc.getAttribute('d').includes(' A '));
    assert.ok(!/NaN|Infinity/.test(arc.getAttribute('d')));
  }
});

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


test('z_index orders leaves across nested groups and keeps ancestor geometry and opacity', () => {
  const circle = { type: 'circle', color: '#0000FF', z_index: -2, position: [1, 0, 0] };
  const square = { type: 'square', color: '#FF0000', z_index: 2 };
  const group = { type: 'vgroup', position: [2, 1, 0], angle: Math.PI / 2, geometry_scale: 2,
    opacity: 0.5, children: [{ type: 'vgroup', position: [0, 3, 0], children: [square, circle] }] };
  const external = { type: 'triangle', color: '#00FF00', z_index: 0 };
  const scene = { mobjects: [group, external] };
  const before = JSON.stringify(scene);
  const layers = renderer.render(scene).children[1].children;
  assert.equal(layers.length, 3);
  assert.equal(layers[0].children[0].children[0].tag, 'circle');
  assert.equal(layers[1].tag, 'polygon');
  assert.equal(layers[2].children[0].children[0].tag, 'rect');
  for (const index of [0, 2]) {
    assert.match(layers[index].getAttribute('transform'), /translate\(100, 50\).*rotate\(90\) scale\(2\)/);
    assert.equal(layers[index].getAttribute('opacity'), '0.5');
    assert.match(layers[index].children[0].getAttribute('transform'), /translate\(0, 150\)/);
  }
  assert.equal(JSON.stringify(scene), before);
});

test('equal depth keeps scene/family order and changing depth changes paint order', () => {
  const a = { type: 'circle', color: '#0000FF' };
  const b = { type: 'square', color: '#FF0000', z_index: 0 };
  const c = { type: 'triangle', color: '#00FF00', z_index: 0 };
  const scene = { mobjects: [{ type: 'vgroup', children: [a, b] }, c] };
  const tags = () => renderer.render(scene).children[1].children.map(el => el.tag === 'g' ? el.children[0].tag : el.tag);
  assert.deepEqual(tags(), ['circle', 'rect', 'polygon']);
  a.z_index = 1;
  assert.deepEqual(tags(), ['rect', 'polygon', 'circle']);
  a.z_index = -1;
  assert.deepEqual(tags(), ['circle', 'rect', 'polygon']);
});


test('corner paths render connected open segments with tracing and standard geometry styles', () => {
  const path = renderer.renderMobject({ type: 'polyline', vertices: [[-2, 0, 0], [0, 1, 0], [2, 0, 0]],
    fill_color: '#0000FF', stroke_color: '#FF0000', fill_opacity: 0.2, stroke_width: 4,
    draw_progress: 0.5, geometry_scale: 2, angle: Math.PI / 2, position: [1, 0, 0] });
  assert.equal(path.tag, 'path');
  assert.equal(path.getAttribute('d'), 'M -100,0 L 0,50 L 100,0');
  assert.equal(path.getAttribute('fill'), '#0000FF');
  assert.equal(path.getAttribute('stroke'), '#FF0000');
  assert.equal(path.getAttribute('pathLength'), '1');
  assert.equal(path.getAttribute('stroke-dashoffset'), '0.5');
  assert.match(path.getAttribute('transform'), /translate\(50, 0\).*rotate\(90\) scale\(2\)/);
  assert.equal(renderer.renderMobject({ type: 'polyline', vertices: [] }).getAttribute('d'), '');
});


test('cubic paths render SVG curves with standard tracing, styles, and transforms', () => {
  const path = renderer.renderMobject({ type: 'bezierpath', curves: [
    [[-3, 0, 0], [-1, 3, 0], [1, 3, 0], [3, 0, 0]],
    [[3, 0, 0], [4, 0, 0], [5, 0, 0], [6, 0, 0]]
  ], color: '#58C4DD', stroke_opacity: 0.4, fill_opacity: 0.2, draw_progress: 0.5,
    geometry_center: [1.5, 1.5, 0], geometry_scale: 0.8, angle: Math.PI / 12 });
  assert.equal(path.getAttribute('d'), 'M -150,0 C -50,150 50,150 150,0 C 200,0 250,0 300,0');
  assert.equal(path.getAttribute('stroke'), '#58C4DD');
  assert.equal(path.getAttribute('stroke-width'), '4');
  assert.equal(path.getAttribute('stroke-opacity'), '0.4');
  assert.equal(path.getAttribute('pathLength'), '1');
  assert.equal(path.getAttribute('stroke-dashoffset'), '0.5');
  assert.match(path.getAttribute('transform'), /rotate\(14.999.*scale\(0.8\)/);
  assert.equal(renderer.renderMobject({ type: 'bezierpath', curves: [] }).getAttribute('d'), '');
});

test('aligned closed paths retain SVG stroke joins at their closing anchor', () => {
  const path = renderer.renderMobject({ type: 'bezierpath', curves: [
    [[0,0,0],[1,0,0],[1,1,0],[0,1,0]],
    [[0,1,0],[-1,1,0],[-1,0,0],[0,0,0]]
  ], fill_opacity: 0.3 });
  assert.equal(path.getAttribute('d'), 'M 0,0 C 50,0 50,50 0,50 C -50,50 -50,0 0,0 Z');
  assert.equal(path.getAttribute('fill-opacity'), '0.3');
});


test('camera dimensions, frame extent and explicit background survive SVG rendering', () => {
  const svg = renderer.render({camera:{pixel_width:600,pixel_height:600,frame_width:8,frame_height:8,background_color:'#FFFFFF'},mobjects:[{type:'circle',radius:1}]});
  assert.equal(svg.getAttribute('viewBox'),'0 0 600 600');
  assert.equal(svg.getAttribute('width'),'600');
  assert.equal(svg.children[0].getAttribute('fill'),'#FFFFFF');
  assert.equal(svg.children[0].getAttribute('data-manim-background'),'true');
  assert.equal(svg.children[1].getAttribute('transform'),'translate(300, 300) scale(1.5, -1.5)');
  assert.equal(svg.children[1].children[0].getAttribute('r'),'50');
  const defaultSVG = renderer.render({mobjects:[]});
  assert.equal(defaultSVG.children[1].getAttribute('transform'),'translate(400, 225) scale(1, -1)');
  for(const camera of [{pixel_width:Infinity},{pixel_height:4097},{frame_height:0},{background_color:'url(bad)'}])
    assert.throws(()=>renderer.render({camera}),/Invalid preview camera/);
});
