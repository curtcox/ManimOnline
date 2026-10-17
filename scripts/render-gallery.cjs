// Build intentional, shipped gallery media with the same Pyodide/SVG runtime as the editor.
// Usage: node scripts/render-gallery.cjs [baseURL] [example IDs ...]
// Serve the checkout first. Requires Playwright Chromium with H.264 WebCodecs support.
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { chromium } = require('playwright');
const { ExampleCatalog } = require('../src/examples.js');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'gallery/previews');
const base = process.argv[2] || 'http://localhost:8000/';
const selected = process.argv.slice(3);
const runtimeFiles = ['src/manim-lite.py', 'src/text-outlines.json', 'src/unified-worker.js', 'src/manim-renderer.js',
  'src/manim-math.js', 'src/manim-typst.js', 'src/manim-video.js', 'src/modl.js', 'viz-global.js'];
const digest = files => createHash('sha256').update(Buffer.concat(files.map(file => fs.readFileSync(path.join(root, file))))).digest('hex');
const runtime = digest(runtimeFiles);
fs.mkdirSync(output, { recursive: true });
const manifestPath = path.join(output, 'manifest.json');
const manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath)) : {};
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ serviceWorkers: 'block' });
    const page = await context.newPage();
    // Start on the gallery origin without executing editor source or loading gallery media.
    await page.route('**/gallery.html', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><html><head></head><body></body></html>' }));
    await page.goto(new URL('gallery.html', base).href);
    for (const file of ['src/manim-client.js', 'src/manim-renderer.js', 'src/manim-math.js',
      'src/manim-typst.js', 'src/manim-export.js', 'src/manim-video.js', 'src/modl.js', 'viz-global.js']) {
      await page.addScriptTag({ url: new URL(file, base).href });
    }
    await page.evaluate(() => { window.galleryClient = new ManimClient(); });
    for (const example of ExampleCatalog) {
      if (selected.length && !selected.includes(example.id)) continue;
      const sourceHash = digest([example.path]);
      if (!selected.length && manifest[example.id]?.source === sourceHash && manifest[example.id]?.runtime === runtime &&
        fs.existsSync(path.join(root, example.cover)) && (!example.video || fs.existsSync(path.join(root, example.video)))) continue;
      process.stdout.write(`Rendering ${example.id}…\n`);
      const result = await page.evaluate(async example => {
        const source = await (await fetch(example.path)).text();
        let frames, glyphs, fps;
        if (example.type === 'manim') {
          let scene = await galleryClient.render(source);
          let typstSvgs = {};
          if (scene.typst_pending?.length) {
            typstSvgs = await ManimTypst.compile(scene.typst_pending);
            scene = await galleryClient.render(source, { typstSvgs });
          }
          glyphs = await ManimMath.prepare(scene);
          const mathMetrics = ManimMath.metrics(glyphs);
          if (scene.math_estimated?.some(expression => mathMetrics[expression])) {
            scene = await galleryClient.render(source, { mathMetrics, typstSvgs });
            glyphs = await ManimMath.prepare(scene);
          }
          frames = scene.frames;
          fps = scene.fps;
        }
        const serialize = svg => new XMLSerializer().serializeToString(svg);
        let staticSVG;
        if (example.type === 'modl') staticSVG = Modl.create(source).svg;
        if (example.type === 'graphviz') staticSVG = (await Viz.instance()).renderSVGElement(source);
        // Keep custom camera aspect ratios, within a small gallery-sized resolution.
        const camera = frames?.[0].camera;
        const originalWidth = camera?.pixel_width || Number(staticSVG?.getAttribute('width')?.replace('pt', '')) || 800;
        const originalHeight = camera?.pixel_height || Number(staticSVG?.getAttribute('height')?.replace('pt', '')) || 450;
        const ratio = Math.min(480 / originalWidth, 270 / originalHeight);
        const width = Math.max(2, Math.round(originalWidth * ratio / 2) * 2);
        const height = Math.max(2, Math.round(originalHeight * ratio / 2) * 2);
        const svgFor = index => staticSVG ? serialize(staticSVG) : serialize(ManimRenderer.render(frames[index], glyphs));
        // Pick a populated frame near the middle, avoiding samples whose final frame is empty.
        let coverIndex = 0, largest = -1;
        if (frames) {
          for (let index = Math.floor(frames.length * .25); index < frames.length * .75; index += Math.max(1, Math.floor(fps))) {
            const size = svgFor(index).length;
            if (size > largest) { largest = size; coverIndex = index; }
          }
        }
        const toBase64 = blob => new Promise(resolve => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result.split(',')[1]);
          reader.readAsDataURL(blob);
        });
        const cover = await toBase64(await ManimExport.png(svgFor(coverIndex), width, height));
        let video = null;
        const previewFPS = 10;
        if (frames) video = await toBase64(await ManimVideo.encode({ format: 'mp4', width, height,
          fps: previewFPS, frameCount: Math.max(1, Math.ceil(frames.length / fps * previewFPS)),
          svgFor: index => svgFor(Math.min(frames.length - 1, Math.floor(index * fps / previewFPS))) }));
        return { cover, video, width, height, duration: frames ? frames.length / fps : 0, coverTime: coverIndex / (fps || 1) };
      }, example);
      fs.writeFileSync(path.join(root, example.cover), Buffer.from(result.cover, 'base64'));
      if (example.video) fs.writeFileSync(path.join(root, example.video), Buffer.from(result.video, 'base64'));
      manifest[example.id] = { source: sourceHash, runtime, width: result.width, height: result.height,
        duration: result.duration, coverTime: result.coverTime };
      fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
      process.stdout.write(`Saved ${example.id} (${result.duration.toFixed(1)}s)\n`);
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
