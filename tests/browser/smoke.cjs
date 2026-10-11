// Cross-browser smoke test: a DOT graph and a Manim scene (Pyodide) in real engines.
// Usage: node tests/browser/smoke.cjs [baseUrl] [chromium|firefox|webkit ...]
// Requires the playwright package and its browsers (npx playwright install).
const playwright = require('playwright');

const base = process.argv[2] || 'http://localhost:8000/';
const engines = process.argv.slice(3).length ? process.argv.slice(3) : ['chromium', 'firefox', 'webkit'];
const DOT = 'digraph G { a -> b -> c; a -> c }';
const MANIM = [
  'from manim import *',
  '',
  'class Smoke(Scene):',
  '    def construct(self):',
  '        square = Square(color=BLUE)',
  '        label = MathTex(r"e^{i\\pi} + 1 = 0").next_to(square, DOWN)',
  '        self.play(Create(square), Write(label))',
  '        self.play(Transform(square, Circle(color=GREEN)), run_time=0.5)',
  '',
].join('\n');
const NUMPY = [
  'from manim import *',
  '',
  'class Points(Scene):',
  '    def construct(self):',
  '        square = Square()',
  '        top = square.get_top()',
  '        top[1] += 0.5',
  '        dots = VGroup(*[Dot(p) for p in np.array([top, square.get_bottom()])])',
  '        self.play(Create(square), FadeIn(dots))',
  '',
].join('\n');

async function open(browser, source) {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => {
    // WebKit reports this benign layout notice as an error.
    if (!/ResizeObserver loop/.test(String(error))) errors.push(String(error));
  });
  await page.goto(base + '#' + encodeURIComponent(source));
  return { page, errors };
}

async function checkDot(browser) {
  const { page } = await open(browser, DOT);
  await page.waitForFunction(() => document.querySelectorAll('svg g.node').length === 3, null, { timeout: 120000 });
  const edges = await page.evaluate(() => document.querySelectorAll('svg g.edge').length);
  await page.close();
  if (edges !== 3) throw new Error('DOT graph has ' + edges + ' edges');
}

async function checkManim(browser, source) {
  const { page, errors } = await open(browser, source);
  await page.waitForFunction(() => {
    const seek = document.querySelector('[aria-label="Animation position"]');
    return (seek && Number(seek.max) > 0) || document.querySelector('#review.error');
  }, null, { timeout: 240000 });
  const state = await page.evaluate(async () => {
    const failure = document.querySelector('#review.error');
    if (failure) return { error: document.querySelector('#error').textContent.slice(0, 500) };
    const seek = document.querySelector('[aria-label="Animation position"]');
    seek.value = seek.max;
    seek.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise(resolve => setTimeout(resolve, 500));
    const preview = document.querySelector('svg[aria-label="Manim animation preview"]');
    const codecs = {};
    if (typeof VideoEncoder !== 'undefined') {
      for (const [name, codec] of [['h264', 'avc1.42001f'], ['vp9', 'vp09.00.10.08'], ['vp8', 'vp8']]) {
        try {
          codecs[name] = (await VideoEncoder.isConfigSupported({ codec, width: 640, height: 360 })).supported;
        } catch (error) {
          codecs[name] = false;
        }
      }
    }
    return { frames: Number(seek.max) + 1, paths: preview ? preview.querySelectorAll('path, circle, ellipse, polygon, polyline, rect, line').length : 0, codecs };
  });
  await page.close();
  if (state.error) throw new Error('Manim render failed: ' + state.error);
  if (errors.length) throw new Error('Page errors: ' + errors.join('; '));
  if (state.paths < 2) throw new Error('Manim preview drew ' + state.paths + ' shapes');
  return state;
}

(async () => {
  let failed = false;
  for (const name of engines) {
    let browser;
    try {
      browser = await playwright[name].launch();
      await checkDot(browser);
      const manim = await checkManim(browser, MANIM);
      const numpy = await checkManim(browser, NUMPY).catch(error => { throw new Error('NumPy scene: ' + error.message); });
      console.log(name + ': DOT ok; Manim ' + manim.frames + ' frames, ' + manim.paths +
                  ' shapes; NumPy scene ' + numpy.frames + ' frames, ' + numpy.paths +
                  ' shapes; video encoders ' + JSON.stringify(manim.codecs));
    } catch (error) {
      failed = true;
      console.log(name + ': FAILED ' + error.message);
    } finally {
      if (browser) await browser.close();
    }
  }
  process.exit(failed ? 1 : 0);
})();
