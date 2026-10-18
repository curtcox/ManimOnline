// Phone touch gestures on diagram previews: one finger pans, two fingers pinch-zoom the
// diagram (not the page). Touch input is sent through CDP, so only Chromium runs it.
// node tests/browser/touch.cjs [baseUrl] [chromium ...]
const { strict: assert } = require('node:assert');
const playwright = require('playwright');
const base = process.argv[2] || 'http://localhost:8000/';
const engines = process.argv.slice(3).length ? process.argv.slice(3) : ['chromium'];
const near = (actual, expected, tolerance = .5) => assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected} (±${tolerance})`);

async function run() {
  const browser = await playwright.chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ serviceWorkers: 'block', viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    const cdp = await context.newCDPSession(page);
    const touch = (type, points) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points.map(([x, y], id) => ({ x, y, id })) });
    async function gesture(from, to, steps = 8) {
      await touch('touchStart', from);
      for (let i = 1; i <= steps; i++) {
        await touch('touchMove', from.map(([x, y], k) => [x + (to[k][0] - x) * i / steps, y + (to[k][1] - y) * i / steps]));
      }
      await touch('touchEnd', []);
    }
    // [scale, tx, ty] in screen pixels for Graphviz, SVG units for modl.
    const graphviz = () => page.evaluate(() => {
      const m = document.querySelector('#review svg .svg-pan-zoom_viewport').transform.baseVal.consolidate().matrix;
      return [m.a, m.e, m.f];
    });
    const modl = () => page.evaluate(() => {
      const t = document.querySelector('#review svg g[transform]').getAttribute('transform').match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/g).map(Number);
      return [t[2], t[0], t[1]];
    });
    for (const [example, selector, read, unitsPerPixel] of [
      ['dotdecision', '#review svg g.node', graphviz, () => 1],
      ['modlpipeline', '#review [data-node-id]', modl, () => page.evaluate(() => 800 / document.querySelector('#review svg').getBoundingClientRect().width)]
    ]) {
      await page.goto(new URL(`?example=${example}`, base).href);
      await page.waitForSelector(selector);
      const box = await page.locator('#review').boundingBox();
      // Below the drawing: the letterbox, which must pan too.
      const x = box.x + box.width / 2, y = box.y + box.height * .85;
      const units = await unitsPerPixel();
      const [scale, tx, ty] = await read();
      await gesture([[x, y]], [[x + 60, y - 40]]);
      const panned = await read();
      near(panned[0], scale, 1e-6);
      near(panned[1] - tx, 60 * units, units);
      near(panned[2] - ty, -40 * units, units);
      await gesture([[x - 40, y], [x + 40, y]], [[x - 120, y], [x + 120, y]]);
      const pinched = await read();
      near(pinched[0] / scale, 3, .05);
      assert.equal(await page.evaluate(() => visualViewport.scale), 1, 'pinch zooms the diagram, not the page');
    }
    assert.deepEqual(errors, []);
    console.log('chromium: touch pan and pinch on Graphviz and modl previews passed');
  } finally {
    await browser.close();
  }
}

(async () => {
  for (const engine of engines) {
    if (engine === 'chromium') await run();
    else console.log(`${engine}: touch gestures skipped (CDP touch input is Chromium-only)`);
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
