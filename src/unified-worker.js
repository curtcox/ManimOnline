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
      self.postMessage({ id, type: 'pyodide-ready' });
      // Rebuild the compatibility definitions and use a fresh source namespace.
      await runtime.runPythonAsync(source);
      runtime.globals.set('_source', code);
      runtime.globals.set('_scene_name', options.sceneName || null);
      // Browser-measured MathTex ink sizes let Python place formulas exactly.
      runtime.globals.set('_math_metrics', runtime.toPy(options.mathMetrics || {}));
      try {
        const result = await runtime.runPythonAsync('render_scene(_source, _scene_name, _math_metrics)');
        if (result.length > 12 * 1024 * 1024) throw new Error('Preview is too large. Use fewer objects or shorter animations.');
        self.postMessage({ id, type: 'manim-result', sceneData: JSON.parse(result) });
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
