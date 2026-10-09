/** Compile formulas once per render; playback/export use self-contained SVG paths. */
const ManimMath = {
  loading: null,
  cache: new Map(),

  /** Tight ink box of typeset output in MathJax units, or null without a layout engine. */
  measure(svg) {
    if (typeof document === 'undefined' || !document.body || typeof svg.cloneNode !== 'function') return null;
    const host = document.createElement('div');
    host.style.cssText = 'position:absolute;left:-10000px;top:0;visibility:hidden';
    const probe = svg.cloneNode(true);
    host.appendChild(probe);
    document.body.appendChild(host);
    try {
      const box = probe.getBBox ? probe.getBBox() : null;
      const values = box && [box.x, box.y, box.width, box.height];
      return values && values.every(Number.isFinite) && box.width > 0 && box.height > 0 ? values : null;
    } finally {
      host.remove();
    }
  },

  /** Ink sizes in em for Python layout (MathJax uses 1000 units per em). */
  metrics(glyphs) {
    const result = {};
    for (const [expression, asset] of glyphs || []) {
      if (!asset.bbox) continue;
      const [x, y, width, height] = asset.bbox;
      const size = [width / 1000, height / 1000];
      if (asset.parts && asset.parts.every(part => part.bbox)) {
        // Part centers relative to the whole ink center, with y up as in Python.
        size.push(asset.parts.map(({ bbox: [px, py, pw, ph] }) => [
          (px + pw / 2 - x - width / 2) / 1000, -(py + ph / 2 - y - height / 2) / 1000, pw / 1000, ph / 1000]));
      }
      result[expression] = size;
    }
    return result;
  },

  /** One SVG per \class{manim-part-i} group, each keeping only its own glyphs. */
  splitParts(svg) {
    const tagged = node => [...node.querySelectorAll('*')].filter(n => /^manim-part-\d+$/.test(n.getAttribute('class') || ''));
    const count = tagged(svg).length;
    const parts = [];
    for (let index = 0; index < count; index++) {
      const clone = svg.cloneNode(true);
      for (const node of tagged(clone)) {
        if (node.getAttribute('class') !== `manim-part-${index}`) node.remove();
      }
      parts.push({ svg: clone.outerHTML, bbox: this.measure(clone) });
    }
    return parts;
  },
  load() {
    if (!this.loading) {
      this.loading = new Promise((resolve, reject) => {
        window.MathJax = {
          startup: { typeset: false },
          // html provides \class, which tags multi-part MathTex strings.
          loader: { load: ['[tex]/html'] },
          tex: { packages: ['base', 'ams', 'html'], maxMacros: 1000, maxBuffer: 4096,
            formatError: (_jax, error) => { throw error; } },
          svg: { fontCache: 'none' }
        };
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg.js';
        script.async = true;
        const timeout = setTimeout(() => {
          script.remove();
          reject(new Error('Math rendering could not load. Check your connection and try again.'));
        }, 20000);
        script.onload = () => window.MathJax.startup.promise.then(() => {
          clearTimeout(timeout);
          resolve(window.MathJax);
        }, error => { clearTimeout(timeout); reject(error); });
        script.onerror = () => {
          clearTimeout(timeout);
          script.remove();
          reject(new Error('Math rendering could not load. Check your connection and try again.'));
        };
        document.head.appendChild(script);
      }).catch(error => { this.loading = null; throw error; });
    }
    return this.loading;
  },

  expressions(scene) {
    const expressions = new Set();
    function visit(mobject) {
      if (mobject.type === 'mathtex') {
        if (typeof mobject.text !== 'string' || mobject.text.length > 4096) {
          throw new Error('MathTex expressions are limited to 4096 characters.');
        }
        // Keep formulas independent and disallow document/extension/link commands.
        if (/\\(?:def|gdef|edef|xdef|let|newcommand|renewcommand|require|href|url|html\w*|includegraphics)\b/.test(mobject.text)) {
          throw new Error('MathTex supports formulas, without custom macros, links, or external packages.');
        }
        expressions.add(mobject.text);
        if (expressions.size > 64) throw new Error('Preview is limited to 64 distinct math expressions.');
      }
      for (const child of mobject.children || []) visit(child);
    }
    for (const frame of scene.frames) for (const mobject of frame.mobjects) visit(mobject);
    return expressions;
  },

  async prepare(scene, isCurrent = () => true, load = () => this.load()) {
    const expressions = this.expressions(scene);
    const glyphs = new Map();
    if (!expressions.size) return glyphs;
    if (!isCurrent()) return null;
    const math = await load();
    let size = 0;
    for (const expression of expressions) {
      if (!isCurrent()) return null;
      if (this.cache.has(expression)) {
        const asset = this.cache.get(expression);
        size += asset.svg.length;
        glyphs.set(expression, asset);
        continue;
      }
      try {
        const container = await math.tex2svgPromise(expression, { display: true });
        if (!isCurrent()) return null;
        const svg = container.querySelector('svg');
        if (!svg || container.querySelector('[data-mml-node="merror"]')) {
          throw new Error('Invalid or unsupported TeX expression.');
        }
        const tags = new Set(['g', 'path', 'rect', 'line', 'polygon', 'polyline', 'circle', 'ellipse']);
        for (const node of svg.querySelectorAll('*')) {
          if (!tags.has(node.localName)) {
            throw new Error('This formula needs a glyph or SVG feature that is not supported yet.');
          }
        }
        const viewBox = svg.getAttribute('viewBox').trim().split(/\s+/).map(Number);
        if (viewBox.length !== 4 || viewBox.some(v => !Number.isFinite(v)) || viewBox[2] < 0 || viewBox[3] < 0) {
          throw new Error('Invalid math geometry.');
        }
        size += svg.outerHTML.length;
        if (size > 2 * 1024 * 1024) throw new Error('Math output is too large. Simplify the formulas.');
        const asset = { svg: svg.outerHTML, viewBox, bbox: this.measure(svg) };
        if (expression.includes('\\class{manim-part-') && typeof svg.cloneNode === 'function') {
          asset.parts = this.splitParts(svg);
          size += asset.parts.reduce((total, part) => total + part.svg.length, 0);
        }
        glyphs.set(expression, asset);
        this.cache.set(expression, asset);
        if (this.cache.size > 256) this.cache.delete(this.cache.keys().next().value);
      } catch (error) {
        throw new Error('MathTex: ' + error.message);
      }
    }
    return glyphs;
  }
};

if (typeof module !== 'undefined' && module.exports) module.exports = ManimMath;
else window.ManimMath = ManimMath;
