/** Python lives in this worker; the main thread enforces its hard deadline. */
let runtimePromise;
const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v0.27.0/full/';

async function initPyodide() {
  if (!runtimePromise) {
    runtimePromise = (async () => {
      self.postMessage({ type: 'pyodide-loading' });
      importScripts(PYODIDE_URL + 'pyodide.js');
      const runtime = await loadPyodide({ indexURL: PYODIDE_URL, stdout: () => {}, stderr: () => {} });
      const response = await fetch(new URL('manim-lite.py', self.location.href));
      if (!response.ok) throw new Error('Unable to load the browser animation runtime.');
      return { runtime, source: await response.text() };
    })().catch(error => { runtimePromise = null; throw error; });
  }
  return runtimePromise;
}

/**
 * Replace pooled frame indices with shared snapshot objects. Unchanged objects are
 * shared across frames (structured cloning keeps the sharing), so consumers must
 * treat frame data as read-only.
 */
function expandPooledScene(scene) {
  if (!Array.isArray(scene.pool)) return scene;
  const { pool, ...rest } = scene;
  // Children and arrays were pooled before their parents, so each index is resolved.
  pool.forEach((node, position) => {
    if (!node || typeof node !== 'object' || Array.isArray(node)) return;
    if ('$xy' in node) {
      // Planar points travel as flat XY pairs, optionally grouped k per item (curves).
      const flat = node.$xy, k = node.k ?? 0;
      if (!Array.isArray(flat) || flat.length % 2 || !flat.every(Number.isFinite) ||
          !Number.isInteger(k) || k < 0 || k > 64 || (k && (flat.length / 2) % k)) throw new Error('Invalid pooled frame data.');
      const points = [];
      for (let i = 0; i < flat.length; i += 2) points.push([flat[i], flat[i + 1], 0]);
      if (!k) pool[position] = points;
      else {
        const groups = [];
        for (let i = 0; i < points.length; i += k) groups.push(points.slice(i, i + k));
        pool[position] = groups;
      }
      return;
    }
    const resolve = index => {
      if (!Number.isInteger(index) || index < 0 || index >= position) throw new Error('Invalid pooled frame data.');
      return pool[index];
    };
    for (const [name, value] of Object.entries(node)) {
      if (value && typeof value === 'object' && !Array.isArray(value) && '$pool' in value) node[name] = resolve(value.$pool);
    }
    if (Array.isArray(node.children)) node.children = node.children.map(resolve);
  });
  for (const frame of rest.frames) {
    frame.mobjects = frame.mobjects.map(index => {
      if (!Number.isInteger(index) || index < 0 || index >= pool.length) throw new Error('Invalid pooled frame data.');
      return pool[index];
    });
  }
  return rest;
}
if (typeof module !== 'undefined') module.exports = { expandPooledScene };

// Serialize requests even during loading; Python cannot execute concurrently.
let queue = Promise.resolve();
self.onmessage = event => {
  const { id, type, code, options = {} } = event.data;
  queue = queue.then(async () => {
    try {
      if (type !== 'render-manim') throw new Error(`Unknown message type: ${type}`);
      const { runtime, source } = await initPyodide();
      // `from manim import *` exports np; load NumPy only for sources that use it.
      if (/\b(?:np|numpy)\b/.test(code)) {
        self.postMessage({ id, type: 'numpy-loading' });
        await runtime.loadPackage('numpy');
      }
      // Code listings use Pygments for syntax colors, as Community does.
      if (/\bCode\s*\(/.test(code)) await runtime.loadPackage('pygments');
      self.postMessage({ id, type: 'pyodide-ready' });
      // Rebuild the compatibility definitions and use a fresh source namespace.
      await runtime.runPythonAsync(source);
      runtime.globals.set('_source', code);
      runtime.globals.set('_scene_name', options.sceneName || null);
      // Browser-measured MathTex ink sizes let Python place formulas exactly.
      runtime.globals.set('_math_metrics', runtime.toPy(options.mathMetrics || {}));
      try {
        const result = await runtime.runPythonAsync('render_scene(_source, _scene_name, _math_metrics, compact=True)');
        if (result.length > 32 * 1024 * 1024) throw new Error('Preview is too large. Use fewer objects or shorter animations.');
        self.postMessage({ id, type: 'manim-result', sceneData: expandPooledScene(JSON.parse(result)) });
      } finally {
        runtime.globals.delete('_source');
        runtime.globals.delete('_scene_name');
        runtime.globals.delete('_math_metrics');
      }
    } catch (error) {
      self.postMessage({ id, type: 'error', error: String(error.message || error).slice(-8000) });
    }
  });
};
