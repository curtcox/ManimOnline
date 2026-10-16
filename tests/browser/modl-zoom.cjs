// Real SVG, pointer input, exports and optional timing diagnostics (no CDN dependencies).
// node tests/browser/modl-zoom.cjs [baseUrl] [chromium|firefox|webkit ...] [--benchmark]
const { strict: assert } = require('node:assert');
const playwright = require('playwright');
const fs = require('node:fs');
const base = process.argv[2] || 'http://localhost:8000/';
const engines = process.argv.slice(3).filter(arg => !arg.startsWith('--'));
if (!engines.length) engines.push('chromium', 'firefox', 'webkit');
const benchmark = process.argv.includes('--benchmark');
const near = (actual, expected, tolerance = .1) => assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected} (±${tolerance})`);

async function run(engine) {
  const browser = await playwright[engine].launch({headless:true});
  try {
    const context = await browser.newContext({viewport:{width:1000,height:650},serviceWorkers:'block'});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.route('**/__modl_zoom_fixture__', route => route.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0} svg{width:800px;height:450px}</style>'}));
    await page.goto(new URL('__modl_zoom_fixture__', base).href);
    await page.addScriptTag({url:new URL('src/modl.js',base).href});
    const setup = async (positions = {a:[400,225],b:[650,350]}) => page.evaluate(positions => {
      window.preview?.destroy();
      window.changes = [];
      window.preview = Modl.create('white\na square blue Target\nb circle green Other\na -> b dashed purple Link', {
        positions, onChange: p => changes.push(p)
      });
      document.body.append(preview.svg);
    }, positions);
    const frame = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const camera = () => page.evaluate(() => preview.viewport());
    const point = (id = 'a') => page.evaluate(id => {
      const p = preview.positions()[id], m = preview.svg.querySelector('g[transform]').getScreenCTM();
      return {x:m.a*p[0]+m.e,y:m.d*p[1]+m.f};
    }, id);
    await setup();
    // Background left-pan remains available, and canceled gestures release capture.
    await page.mouse.move(30,30); await page.mouse.down();
    await page.mouse.move(50,45); await page.mouse.up();
    near((await camera()).tx,20); near((await camera()).ty,15);
    await page.evaluate(() => preview.resetView());
    const cancelPoint=await point();
    await page.mouse.move(cancelPoint.x,cancelPoint.y); await page.mouse.down();
    await page.evaluate(() => preview.svg.dispatchEvent(new PointerEvent('pointercancel',{pointerId:1})));
    await page.mouse.up();
    await page.evaluate(() => preview.zoom(2));
    near((await camera()).scale,2);
    assert.deepEqual(await page.evaluate(() => preview.positions().a),[400,225]);
    await setup();
    // Preserve a noncentral cursor point through every decade and both clamps.
    const maxAnchorError = await page.evaluate(() => {
      let error = 0;
      const center = [317.125,183.75];
      for (const scale of [.001,.01,.1,1,10,100,1000]) {
        preview.zoom(scale/preview.viewport().scale,...center);
        const simple=scale<.1||scale>8;
        if(preview.svg.hasAttribute('data-modl-simple')!==simple) throw Error('detail threshold');
        const filter=getComputedStyle(preview.svg.querySelector('[data-node-id="a"] rect')).filter;
        if((filter==='none')!==simple) throw Error('shadow detail policy');
        const m = preview.svg.querySelector('g[transform]').getScreenCTM();
        error = Math.max(error,Math.abs(m.a*center[0]+m.e-center[0]),Math.abs(m.d*center[1]+m.f-center[1]));
      }
      preview.zoom(1e100,...center);
      if (preview.viewport().scale !== 1000) throw Error('upper clamp');
      preview.zoom(1e-100,...center);
      if (preview.viewport().scale !== .001) throw Error('lower clamp');
      return error;
    });
    near(maxAnchorError,0,.1);
    assert.deepEqual(await page.evaluate(() => preview.positions()),{a:[400,225],b:[650,350]});

    // High-zoom dragging must move by a fraction of a world unit, with real hit testing.
    // At .001x normal nodes are subpixel; native mouse targeting is unreliable
    // in WebKit. Minimum-scale camera/pan/export behavior is checked separately.
    for (const scale of [1,100,1000]) {
      await setup();
      await page.evaluate(scale => preview.zoom(scale),scale);
      const p = await point();
      assert.equal(await page.evaluate(p => document.elementFromPoint(p.x,p.y)?.closest('[data-node-id]')?.dataset.nodeId,p),'a');
      await page.mouse.move(p.x,p.y);
      await page.mouse.down();
      // Wheel/buttons during a captured gesture must not invalidate its anchors.
      await page.evaluate(() => preview.zoom(1.2));
      near((await camera()).scale,scale,1e-9);
      await page.mouse.move(p.x+23,p.y+17,{steps:4});
      await page.mouse.up();
      await frame();
      const result = await point();
      near(result.x,p.x+23);
      near(result.y,p.y+17);
      const pos = await page.evaluate(() => preview.positions().a);
      near(pos[0],400+23/scale,1e-8);
      near(pos[1],225+17/scale,1e-8);
      assert.ok(await page.evaluate(() => changes.length >= 1));
      assert.deepEqual(await page.evaluate(() => changes.at(-1).a),pos);
      assert.equal(await page.evaluate(() => preview.svg.hasPointerCapture(1)),false);
    }

    // Panning at both limits is a screen-space operation. Zoom preserves positions.
    for (const scale of [.001,1,1000]) {
      await setup();
      await page.evaluate(scale => preview.zoom(scale),scale);
      const before = await camera();
      await page.mouse.move(400,225); await page.mouse.down({button:'middle'});
      await page.mouse.move(437,254); await page.mouse.up({button:'middle'});
      const after = await camera();
      near(after.tx-before.tx,37,1e-8); near(after.ty-before.ty,29,1e-8);
      assert.deepEqual(await page.evaluate(() => preview.positions()),{a:[400,225],b:[650,350]});
    }
    await setup();
    // CSS sizing / viewBox mapping and wheel modes, including a horizontal-only wheel.
    await page.evaluate(() => { preview.svg.style.width='640px'; preview.svg.style.height='360px'; });
    for (const deltaMode of [0,1,2]) {
      await page.evaluate(() => preview.resetView());
      await page.evaluate(deltaMode => preview.svg.dispatchEvent(new WheelEvent('wheel',{clientX:240,clientY:160,deltaY:-1,deltaMode,cancelable:true})),deltaMode);
      const v = await camera();
      near(v.tx+300*v.scale,300,1e-7); near(v.ty+200*v.scale,200,1e-7);
      assert.ok(v.scale>1);
    }
    const beforeWheel = await camera();
    await page.evaluate(() => preview.svg.dispatchEvent(new WheelEvent('wheel',{deltaX:20,deltaY:0,cancelable:true})));
    assert.deepEqual(await camera(),beforeWheel);
    // Real wheel event as well as mode-specific dispatched events.
    await page.mouse.move(240,160); await page.mouse.wheel(0,-120); await frame();
    assert.ok((await camera()).scale>beforeWheel.scale);

    // Browser rasterization proves exported SVG paints at both extremes, not just finite matrices.
    for (const scale of [.001,1,1000]) {
      await setup();
      await page.evaluate(scale => preview.zoom(scale),scale);
      const exported = await page.evaluate(async () => {
        const source = new XMLSerializer().serializeToString(preview.svg);
        const image = new Image();
        image.src = 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(source);
        await image.decode();
        const canvas = document.createElement('canvas'); canvas.width=800; canvas.height=450;
        const ctx = canvas.getContext('2d'); ctx.drawImage(image,0,0);
        const rgba = Array.from(ctx.getImageData(400,225,1,1).data);
        return {source,rgba};
      });
      assert.ok(!/NaN|Infinity/.test(exported.source));
      assert.ok(exported.source.includes('marker-end="url(#arrow-purple)"'));
      assert.ok(exported.source.includes('data-node-id="b"'));
      assert.equal(exported.rgba[3],255);
      if (scale>=1) assert.ok(exported.rgba.slice(0,3).some(n=>n<245), `missing exported node at ${scale}x: ${exported.rgba}`);
    }
    // Image loads rebuild geometry asynchronously; they must retain the camera,
    // node identity and image URL, including after fractional high-zoom dragging.
    await context.route('https://modl.test/image.svg',route=>route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="64"><rect width="128" height="64" fill="blue"/></svg>'}));
    await page.evaluate(() => {
      preview.destroy();
      window.preview=Modl.create('picture small square teal https://modl.test/image.svg "Image # ->"',{positions:{picture:[400,225]}});
      document.body.append(preview.svg); preview.zoom(1000);
    });
    await page.waitForFunction(() => document.querySelector('[data-node-id="picture"] image')?.getAttribute('height')==='27.5');
    near((await camera()).scale,1000);
    const imagePoint=await point('picture');
    await page.mouse.move(imagePoint.x,imagePoint.y); await page.mouse.down();
    await page.mouse.move(imagePoint.x+21,imagePoint.y+13); await page.mouse.up(); await frame();
    near((await page.evaluate(() => preview.positions().picture))[0],400.021,1e-8);
    assert.equal(await page.locator('[data-node-id="picture"] image').getAttribute('href'),'https://modl.test/image.svg');

    // Probe native SVG coordinate precision at progressively distant origins.
    const precision = [];
    for (const origin of [400,1e6,1e9,1e12]) {
      await setup({a:[origin,225],b:[origin+250,350]});
      precision.push(await page.evaluate(origin => {
        // Isolate the renderer's precision from synthetic PointerEvent coordinate limits.
        const svg=preview.svg;
        svg.querySelector('g[transform]').setAttribute('transform',`translate(${400-origin*1000} ${225-225*1000}) scale(1000)`);
        const rect=svg.querySelector('[data-node-id="a"] rect').getBoundingClientRect();
        const box=svg.querySelector('[data-node-id="a"] rect').getBBox();
        return {origin,centerError:Math.abs((rect.left+rect.right)/2-400),localCenter:box.x+box.width/2};
      },origin));
    }
    console.log(engine+': zoom/drag/pan/wheel/export passed; native anchor error '+maxAnchorError+'px; distant-origin probe '+JSON.stringify(precision));

    // Optional: run the same port's native UI after applying patches/modl-deep-zoom.patch.
    if (process.env.MODL_STANDALONE_HTML) {
      const html = fs.readFileSync(process.env.MODL_STANDALONE_HTML,'utf8');
      await page.route('https://hashbin.org/**',route=>route.abort());
      await page.route('**/__modl_standalone__',route=>route.fulfill({contentType:'text/html',body:html}));
      await page.goto(new URL('__modl_standalone__',base).href);
      await page.locator('#src').fill('white\na square blue Target\nb circle green Other\na -> b dashed purple Link');
      await page.locator('[data-node-id="a"] rect').waitFor();
      const standalonePoint = () => page.evaluate(() => {
        const node=document.querySelector('[data-node-id="a"] rect');
        const box=node.getBBox(),m=node.getScreenCTM();
        return {x:(box.x+box.width/2)*m.a+m.e,y:(box.y+box.height/2)*m.d+m.f,worldX:Number(node.getAttribute('x'))+Number(node.getAttribute('width'))/2};
      });
      const original = await standalonePoint();
      for (let i=0;i<5;i++) await page.evaluate(p => document.querySelector('#svg').dispatchEvent(new WheelEvent('wheel',{clientX:p.x,clientY:p.y,deltaY:-10000,cancelable:true})),original);
      assert.equal(await page.locator('#zoomScale').textContent(),'1000×');
      near((await standalonePoint()).x,original.x,.1);
      await page.mouse.move(original.x,original.y); await page.mouse.down();
      await page.mouse.move(original.x+23,original.y+17); await page.mouse.up();
      await frame();
      near((await standalonePoint()).worldX,original.worldX+.023,1e-7);
      await page.locator('#btnResetView').click();
      assert.equal(await page.locator('#zoomScale').textContent(),'1×');
      await page.locator('#btnZoomIn').click();
      assert.equal(await page.locator('#zoomScale').textContent(),'1.2×');
      await page.locator('#btnResetView').click();
      for (let i=0;i<5;i++) await page.evaluate(() => document.querySelector('#svg').dispatchEvent(new WheelEvent('wheel',{deltaY:10000,cancelable:true})));
      assert.equal(await page.locator('#zoomScale').textContent(),'0.001×');
      await page.reload(); await page.locator('[data-node-id="a"]').waitFor();
      near((await standalonePoint()).worldX,original.worldX+.023,1e-7);
      console.log(engine+': standalone modl patch controls, wheel, fractional dragging and saved positions passed');
    }

    if (benchmark) {
      // Restore the isolated fixture if the optional standalone check navigated away.
      if (process.env.MODL_STANDALONE_HTML) {
        await page.goto(new URL('__modl_zoom_fixture__',base).href);
        await page.addScriptTag({url:new URL('src/modl.js',base).href});
      }
      for (const count of [100,1000,5000]) {
        const timing = await page.evaluate(async count => {
          window.preview?.destroy();
          const pos={}, lines=['white'];
          for(let i=0;i<count;i++) { pos['n'+i]=[(i%100)*120,Math.floor(i/100)*90]; lines.push(`n${i} square blue Node ${i}`); if(i) lines.push(`n${i-1} -> n${i} dashed purple Edge`); }
          let serialize=false, exportMs=0;
          const start=performance.now();
          window.preview=Modl.create(lines.join('\n'),{positions:pos,onFrame:svg=>{if(serialize){const t=performance.now();new XMLSerializer().serializeToString(svg);exportMs+=performance.now()-t;}}});
          document.body.append(preview.svg);
          const buildMs=performance.now()-start, samples={};
          for(const legacy of [false,true]) {
            serialize=legacy;
            for(const scale of [.001,1,1000]) {
              preview.resetView(); preview.zoom(scale);
              const durations=[],cpu=[];
              for(let i=0;i<24;i++) {
                await new Promise(requestAnimationFrame); const t=performance.now();
                preview.zoom(i%2?1/1.01:1.01,370,210);
                cpu.push(performance.now()-t);
                await new Promise(requestAnimationFrame); durations.push(performance.now()-t);
              }
              durations.sort((a,b)=>a-b); cpu.sort((a,b)=>a-b);
              samples[(legacy?'serialize':'prototype')+'@'+scale]={frameP50:durations[12],frameP95:durations[22],cpuP95:cpu[22]};
            }
          }
          serialize=false; preview.resetView(); preview.zoom(1000,0,0);
          const svg=preview.svg, capture=svg.setPointerCapture;
          svg.setPointerCapture=()=>{};
          svg.querySelector('[data-node-id="n0"]').dispatchEvent(new PointerEvent('pointerdown',{button:0,pointerId:29,clientX:0,clientY:0,bubbles:true}));
          const dragFrames=[];
          for(let i=1;i<=12;i++) {
            await new Promise(requestAnimationFrame); const t=performance.now();
            svg.dispatchEvent(new PointerEvent('pointermove',{pointerId:29,clientX:i*4,clientY:i*3}));
            await new Promise(requestAnimationFrame);
            dragFrames.push(performance.now()-t);
          }
          svg.dispatchEvent(new PointerEvent('pointerup',{pointerId:29})); svg.setPointerCapture=capture;
          dragFrames.sort((a,b)=>a-b);
          return {count,buildMs,elements:preview.svg.querySelectorAll('*').length,exportMs,dragFrameP50:dragFrames[6],dragFrameP95:dragFrames[11],samples};
        },count);
        console.log(engine+' benchmark '+JSON.stringify(timing));
      }
    }
    assert.deepEqual(errors,[]);
    await context.close();
  } finally { await browser.close(); }
}
(async () => { for (const engine of engines) await run(engine); })().catch(e=>{console.error(e);process.exitCode=1;});
