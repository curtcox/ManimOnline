const { test } = require('node:test');
const assert = require('node:assert/strict');
const renderer = require('../src/manim-renderer.js');
// World-space ThreeDScene frames written by tests/fixtures/generate_three_d_frames.py.
const frames = require('./fixtures/three_d_frames.json');

const project = name => renderer.projectThreeD(frames[name].mobjects, frames[name].camera.three_d);
const close = (actual, expected, digits = 9) => {
  assert.equal(actual.length, expected.length);
  actual.forEach((value, i) => assert.ok(Math.abs(value - expected[i]) < 10 ** -digits,
    `${actual} != ${expected}`));
};

test('square anchors project like Community ThreeDCamera.project_points', () => {
  const [leaf] = project('square_projection');
  assert.equal(leaf.type, 'bezierpath');
  // Manim 0.22: camera.project_points(square anchors) at phi=75, theta=-45.
  const expected = [[1.414213562373095, 0, 0], [0, 0.3426237654117778, -1.3660254037844388],
    [-1.414213562373095, 0, 0], [0, -0.3928581118281109, 1.3660254037844388]];
  leaf.curves.slice(0, 4).forEach((curve, i) => close(curve[0], expected[i]));
});

test('shaded leaves sort by rotated depth and take start-corner shading', () => {
  const leaves = project('depth_shading');
  // Manim 0.22: at phi=0 the OUT square's depth key is larger, so it paints last.
  assert.equal(leaves[1].fill_color, '#70DCF5');
  assert.deepEqual(leaves.map(leaf => leaf.z_index), [0, 1]);
  // phi=180 views from below: the OUT square now paints first.
  assert.equal(project('depth_flipped')[0].fill_color, '#70DCF5');
});

test('cube faces paint in Community order with Community shading', () => {
  const leaves = project('cube');
  // Manim 0.22: get_mobjects_to_display order is LEFT, UP, IN, OUT, DOWN, RIGHT
  // and camera.get_fill_rgbas(face)[0] gives these shaded hexes.
  assert.deepEqual(leaves.map(leaf => leaf.fill_color),
    ['#54C0D9', '#76E2FB', '#8BF7FF', '#49B5CE', '#4AB6CF', '#69D5EE']);
  assert.deepEqual(leaves.map(leaf => leaf.z_index), [0, 1, 2, 3, 4, 5]);
});

test('fixed-in-frame text stays put and fixed-orientation dots only translate', () => {
  const [text, dot] = project('fixed_members');
  assert.equal(text.type, 'text');
  assert.deepEqual(text.position, [0, 0, 0]);
  // Manim 0.22: project_points(RIGHT) = RIGHT, so the dot keeps its anchor.
  close(dot.curves[0][0].slice(0, 2), [1.08, 0], 4);
});

test('projection returns new identity-pose leaves without editing frame data', () => {
  const before = JSON.stringify(frames.rotated_square);
  const [leaf] = project('rotated_square');
  assert.equal(JSON.stringify(frames.rotated_square), before);
  assert.deepEqual([leaf.position, leaf.angle, leaf.geometry_scale], [[0, 0, 0], 0, 1]);
  assert.notDeepEqual(leaf.curves, frames.rotated_square.mobjects[0].curves);
});

test('full renders project ThreeDScene frames and reject invalid cameras', () => {
  class Element {
    constructor(tag) { this.tag = tag; this.attributes = {}; this.children = []; this.style = {}; }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    getAttribute(name) { return this.attributes[name] ?? null; }
    appendChild(child) { this.children.push(child); }
    querySelectorAll() { return this.children.flatMap(child => [child, ...child.querySelectorAll()]); }
  }
  global.document = { createElementNS: (_namespace, tag) => new Element(tag) };
  const svg = renderer.render(frames.cube);
  assert.equal(svg.querySelectorAll().filter(element => element.tag === 'path').length, 6);
  const broken = { ...frames.cube, camera: { ...frames.cube.camera, three_d: { ...frames.cube.camera.three_d, phi: NaN } } };
  assert.throws(() => renderer.render(broken), /Invalid 3D camera/);
});
