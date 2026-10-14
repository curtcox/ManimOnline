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
const THREE_D = [
  'from manim import *',
  '',
  'class Depth(ThreeDScene):',
  '    def construct(self):',
  '        self.set_camera_orientation(phi=60 * DEGREES, theta=-45 * DEGREES)',
  '        surface = Surface(lambda u, v: (u, v, u * v / 4), u_range=[-2, 2], v_range=[-2, 2], resolution=8)',
  '        cloud = PMobject().add_points([(x / 4, 0, x / 4) for x in range(-8, 9)], color=YELLOW)',
  '        cube = Cube(side_length=1).shift(3 * LEFT)',
  '        gradient = Square(fill_opacity=1, fill_color=[RED,BLUE]).rotate(PI/2, axis=RIGHT).shift(3*RIGHT)',
  '        gradient.set_sheen_direction(OUT)',
  '        self.add(gradient)',
  '        self.play(Create(surface), FadeIn(cloud), FadeIn(cube), run_time=0.5)',
  '        self.play(Rotate(cube, angle=PI / 3, axis=UP), run_time=0.5)',
  '',
].join('\n');

const FIELD_IMAGE = [
  'from manim import *',
  'config.pixel_width = 64',
  'config.pixel_height = 36',
  'class FieldImage(Scene):',
  '    def construct(self):',
  '        field = VectorField(lambda p: p)',
  '        gradient = field.get_vectorized_rgba_gradient_function(0, 1, [RED, BLUE])',
  '        colors = gradient([0, .5, 1], opacity=.5)',
  '        assert colors.shape == (3, 4) and colors[:, 3].tolist() == [.5, .5, .5]',
  '        streams = StreamLines(lambda p: RIGHT + p[0] * UP, x_range=[0,0,1], y_range=[0,0,1], z_range=[0,1,1], noise_factor=0, dt=.1, virtual_time=1)',
  '        assert len(streams[0].get_stroke_colors()) > 8',
  '        self.add(streams)',
  '        image = ImageMobject(field.get_colored_background_image(sampling_rate=4))',
  '        image.height = config.frame_height',
  '        self.play(FadeIn(image), FadeIn(Dot()), run_time=0.2)',
  '        self.wait(0.2)',
].join('\n');

const RASTER_PAINT = [
  'from manim import *',
  'from PIL import Image',
  'config.pixel_width = 80',
  'config.pixel_height = 40',
  'class RasterPaint(Scene):',
  '    def construct(self):',
  '        image = Image.new("RGB", (2,2), (255,0,0))',
  '        image.putpixel((1,0), (0,0,255))',
  '        image.putpixel((0,1), (0,255,0))',
  '        image.putpixel((1,1), (255,255,0))',
  '        box = Rectangle(width=config.frame_width,height=config.frame_height,fill_opacity=1,stroke_width=0)',
  '        template = Square(fill_opacity=1,stroke_width=0).color_using_background_image(image)',
  '        box.match_style(template)',
  '        self.play(FadeIn(box),run_time=0.2)',
  '        self.wait(0.2)',
].join('\n');

const GRADIENT_FADE = [
  'from manim import *',
  'config.pixel_width = 80',
  'config.pixel_height = 40',
  'config.frame_width = 8',
  'config.frame_height = 4',
  'class GradientFade(Scene):',
  '    def construct(self):',
  '        box = Rectangle(width=8,height=4,fill_color=WHITE,fill_opacity=[.25,.75],stroke_width=0)',
  '        box.set_sheen_direction(RIGHT)',
  '        self.add(box)',
  '        self.play(FadeOut(box),run_time=2,rate_func=linear)',
].join('\n');

const SHEEN_FADE = GRADIENT_FADE.replace(
  'fill_color=WHITE,fill_opacity=[.25,.75]',
  'fill_color=BLACK,fill_opacity=2,sheen_factor=1');

const NESTED_GRADIENT = [
  'from manim import *',
  'config.pixel_width = 80',
  'config.pixel_height = 80',
  'config.frame_width = 5',
  'config.frame_height = 5',
  'class NestedGradient(Scene):',
  '    def construct(self):',
  '        panel = Rectangle(width=4,height=2,fill_color=[PURE_RED,PURE_BLUE],fill_opacity=1,stroke_width=0)',
  '        parent = Square(side_length=1,stroke_width=0).add(panel).rotate(PI/4)',
  '        self.add(parent)',
  '        self.wait(.2)',
].join('\n');

const STYLE_MORPH = [
  'from manim import *',
  'config.pixel_width = 80',
  'config.pixel_height = 40',
  'config.frame_width = 8',
  'config.frame_height = 4',
  'class StyleMorph(Scene):',
  '    def construct(self):',
  '        box = Rectangle(width=8,height=4,fill_color=WHITE,fill_opacity=1,stroke_width=0)',
  '        template = Square(fill_color=[PURE_RED,PURE_BLUE],fill_opacity=1,stroke_width=0,sheen_direction=RIGHT)',
  '        self.add(box)',
  '        self.play(box.animate.match_style(template),run_time=2,rate_func=linear)',
].join('\n');

const MANUAL_STYLE_MORPH = STYLE_MORPH.replace(
  '        self.play(box.animate.match_style(template),run_time=2,rate_func=linear)',
  [
    '        start = box.copy().set_sheen_direction(RIGHT)',
    '        value = ValueTracker(0)',
    '        box.add_updater(lambda mob: mob.interpolate_color(start,template,value.get_value()))',
    '        self.play(value.animate.set_value(1),run_time=2,rate_func=linear)',
  ].join('\n'));

const GLYPH_STYLE_MORPH = [
  'from manim import *',
  'config.pixel_width = 80',
  'config.pixel_height = 40',
  'config.frame_width = 8',
  'config.frame_height = 4',
  'class GlyphStyleMorph(Scene):',
  '    def construct(self):',
  '        formula = MathTex(r"\\rule{8em}{4em}",font_size=96)',
  '        text = Text("AB").shift(1.3*UP)',
  '        self.add(formula,text)',
  '        self.play(formula.animate.set_fill([PURE_RED,PURE_BLUE],1),text.animate.set_fill([PURE_RED,PURE_BLUE],1),run_time=2,rate_func=linear)',
].join('\n');

const GLYPH_GRADIENT = [
  'from manim import *',
  'config.pixel_width = 80',
  'config.pixel_height = 80',
  'config.frame_width = 8',
  'config.frame_height = 8',
  'class GlyphGradient(Scene):',
  '    def construct(self):',
  '        formula = MathTex(r"\\rule{8em}{8em}",font_size=96)',
  '        formula.set_fill([PURE_RED,PURE_BLUE],1).set_sheen_direction(UP)',
  '        self.add(formula)',
  '        self.wait(.2)',
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

async function checkManim(browser, source, verifyRaster = false) {
  const name = source.match(/^class\s+(\w+)/m)?.[1] || 'Manim';
  try {
    return await renderManim(browser, source, verifyRaster);
  } catch (error) {
    throw new Error(name + ': ' + error.message);
  }
}

async function renderManim(browser, source, verifyRaster = false) {
  const { page, errors } = await open(browser, source);
  await page.waitForFunction(() => {
    const seek = document.querySelector('[aria-label="Animation position"]');
    return (seek && Number(seek.max) > 0) || document.querySelector('#review.error');
  }, null, { timeout: 240000 });
  const state = await page.evaluate(async verifyRaster => {
    const failure = document.querySelector('#review.error');
    if (failure) return { error: document.querySelector('#error').textContent.slice(0, 500) };
    const seek = document.querySelector('[aria-label="Animation position"]');
    seek.value = ['fade','morph'].includes(verifyRaster) ? Math.floor(Number(seek.max)/2) : seek.max;
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
    let rasterPixels;
    if (verifyRaster) {
      const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(preview)],{type:'image/svg+xml'}));
      try {
        const image=new Image();
        await new Promise((resolve,reject)=>{
          const timer=setTimeout(()=>reject(new Error('Raster SVG export timed out')),10000);
          image.onload=()=>{clearTimeout(timer);resolve();};
          image.onerror=()=>{clearTimeout(timer);reject(new Error('Raster SVG export failed'));};
          image.src=url;
        });
        const canvas=document.createElement('canvas');
        canvas.width=Number(preview.getAttribute('width'));canvas.height=Number(preview.getAttribute('height'));
        const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);
        rasterPixels=(verifyRaster === 'nested' ? [[40,24],[40,56]] : ['fade','morph'].includes(verifyRaster) ? [[40,20]] : [[10,5],[70,5],[10,35],[70,35]]).flatMap(([x,y])=>[...ctx.getImageData(x,y,1,1).data]);
      } finally { URL.revokeObjectURL(url); }
    }
    return { rasterPixels, images: preview ? preview.querySelectorAll('image').length : 0, frames: Number(seek.max) + 1, paths: preview ? preview.querySelectorAll('path, circle, ellipse, polygon, polyline, rect, line').length : 0, codecs };
  }, verifyRaster);
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
      const fieldImage = await checkManim(browser, FIELD_IMAGE).catch(error => { throw new Error('Field image scene: ' + error.message); });
      if (fieldImage.images !== 1) throw new Error('Field image scene drew ' + fieldImage.images + ' images');
      const raster = await checkManim(browser, RASTER_PAINT, true);
      if (JSON.stringify(raster.rasterPixels)!==JSON.stringify([255,0,0,255,0,0,255,255,0,255,0,255,255,255,0,255])) throw new Error('Raster pixels: '+JSON.stringify(raster.rasterPixels));
      const fade = await checkManim(browser, GRADIENT_FADE, 'fade');
      if (fade.rasterPixels.slice(0,3).some(v=>v<63 || v>66) || fade.rasterPixels[3]!==255) throw new Error('Gradient fade pixels: '+JSON.stringify(fade.rasterPixels));
      const sheen = await checkManim(browser, SHEEN_FADE, 'fade');
      if (sheen.rasterPixels.slice(0,3).some(v=>v<63 || v>66) || sheen.rasterPixels[3]!==255) throw new Error('Sheen fade pixels: '+JSON.stringify(sheen.rasterPixels));
      const nested = await checkManim(browser, NESTED_GRADIENT, 'nested');
      const [r0,g0,b0,a0,r1,g1,b1,a1] = nested.rasterPixels;
      if (!(b0>r0+40 && r1>b1+40 && g0===0 && g1===0 && a0===255 && a1===255)) throw new Error('Nested gradient pixels: '+JSON.stringify(nested.rasterPixels));
      const morph = await checkManim(browser, STYLE_MORPH, 'morph');
      const [mr,mg,mb,ma] = morph.rasterPixels;
      if (!(mr>=188 && mr<=196 && mg>=126 && mg<=130 && mb>=188 && mb<=196 && ma===255)) throw new Error('Style morph pixels: '+JSON.stringify(morph.rasterPixels));
      const manual = await checkManim(browser, MANUAL_STYLE_MORPH, 'morph');
      const [cr,cg,cb,ca] = manual.rasterPixels;
      if (!(cr>=188 && cr<=196 && cg>=125 && cg<=129 && cb>=188 && cb<=196 && ca===255)) throw new Error('Manual style interpolation pixels: '+JSON.stringify(manual.rasterPixels));
      const glyph = await checkManim(browser, GLYPH_STYLE_MORPH, 'morph');
      const [gr,gg,gb,ga] = glyph.rasterPixels;
      if (!(gr>=188 && gr<=196 && gg>=126 && gg<=130 && gb>=188 && gb<=196 && ga===255)) throw new Error('Glyph style morph pixels: '+JSON.stringify(glyph.rasterPixels));
      const direction = await checkManim(browser, GLYPH_GRADIENT, 'nested');
      const [dr0,dg0,db0,da0,dr1,dg1,db1,da1] = direction.rasterPixels;
      if (!(db0>dr0+40 && dr1>db1+40 && dg0===0 && dg1===0 && da0===255 && da1===255)) throw new Error('Glyph gradient direction pixels: '+JSON.stringify(direction.rasterPixels));
      const depth = await checkManim(browser, THREE_D).catch(error => { throw new Error('3D scene: ' + error.message); });
      console.log(name + ': DOT ok; Manim ' + manim.frames + ' frames, ' + manim.paths +
                  ' shapes; NumPy scene ' + numpy.frames + ' frames, ' + numpy.paths +
                  ' shapes; 3D scene ' + depth.frames + ' frames, ' + depth.paths +
                  ' shapes; field image ' + fieldImage.frames + ' frames, ' + fieldImage.images + ' image; raster paint/export and halfway gradient-fade and sheen-fade and nested gradient and style-morph and manual interpolation and glyph-style and glyph-direction pixels ok; video encoders ' + JSON.stringify(manim.codecs));
    } catch (error) {
      failed = true;
      console.log(name + ': FAILED ' + error.message);
    } finally {
      if (browser) await browser.close();
    }
  }
  process.exit(failed ? 1 : 0);
})();
