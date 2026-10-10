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
      // Centers relative to the whole ink center, with y up as in Python.
      const relative = ([px, py, pw, ph]) => [
        (px + pw / 2 - x - width / 2) / 1000, -(py + ph / 2 - y - height / 2) / 1000, pw / 1000, ph / 1000];
      const parts = asset.parts && asset.parts.every(part => part.bbox) ? asset.parts.map(part => relative(part.bbox)) : null;
      if (parts) size.push(parts);
      if (Array.isArray(asset.glyphs) && asset.glyphs.length <= 2000) {
        // Glyph submobjects, in TeX's order, tagged with their part (-1 for single strings)
        // and the isolated substring holding them (-1 for none).
        if (!parts) size.push(null);
        size.push(asset.glyphs.map(glyph => [...relative(glyph.bbox), glyph.part, glyph.sub ?? -1]));
      }
      result[expression] = size;
    }
    return result;
  },

  /**
   * Drawable leaves in TeX's (dvisvgm) order, each a self-contained SVG with its composed
   * transform. MathJax draws fraction rules, radicals, limits and accents in a different
   * order than TeX, so those nodes are visited in TeX's order.
   */
  glyphLeaves(svg) {
    if (typeof document === 'undefined' || !document.body || typeof svg.cloneNode !== 'function') return null;
    const host = document.createElement('div');
    host.style.cssText = 'position:absolute;left:-10000px;top:0;visibility:hidden';
    const probe = svg.cloneNode(true);
    host.appendChild(probe);
    document.body.appendChild(host);
    try {
      const drawable = new Set(['path', 'rect', 'line', 'polygon', 'polyline', 'circle', 'ellipse', 'text']);
      const leaves = [];
      const visit = node => {
        let kids = [...node.children];
        const role = node.getAttribute && node.getAttribute('data-mml-node');
        if (role === 'mfrac' && kids.length === 3) kids = [kids[0], kids[2], kids[1]];
        else if (role === 'msqrt' && kids.length === 3) kids = [kids[1], kids[2], kids[0]];
        else if (role === 'mroot' && kids.length === 4) kids = [kids[1], kids[2], kids[3], kids[0]];
        else if (role === 'munderover' && kids.length === 3) kids = [kids[2], kids[0], kids[1]];
        else if (role === 'mover' && kids.length === 2) kids = [kids[1], kids[0]];
        for (const kid of kids) {
          // A nested svg is a clipped piece of a stretchy delimiter: keep it whole.
          if (kid.localName === 'svg') leaves.push(kid);
          else if (!drawable.has(kid.localName)) visit(kid);
          else if (kid.localName !== 'path' || (kid.getAttribute('d') || '').trim()) leaves.push(kid);
        }
      };
      visit(probe);
      const root = probe.getScreenCTM && probe.getScreenCTM();
      if (!root || leaves.length > 2000) return null;
      const inverse = root.inverse();
      const result = [];
      for (const leaf of leaves) {
        const viewport = leaf.localName === 'svg';
        // A nested viewport is placed by its parent's transform and clipped to x/y/width/height.
        const ctm = viewport ? leaf.parentNode.getScreenCTM() : leaf.getScreenCTM();
        if (!ctm) return null;
        const m = inverse.multiply(ctm);
        const box = viewport ? ['x', 'y', 'width', 'height'].reduce((result, key) =>
          Object.assign(result, { [key]: Number(leaf.getAttribute(key)) || 0 }), {}) : leaf.getBBox();
        const xs = [], ys = [];
        for (const [px, py] of [[box.x, box.y], [box.x + box.width, box.y], [box.x, box.y + box.height],
          [box.x + box.width, box.y + box.height]]) {
          xs.push(m.a * px + m.c * py + m.e);
          ys.push(m.b * px + m.d * py + m.f);
        }
        const bbox = [Math.min(...xs), Math.min(...ys), Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)];
        if (!bbox.every(Number.isFinite)) return null;
        const tag = kind => {
          const tagged = leaf.closest(`[class*="manim-${kind}-"]`);
          return tagged ? this.classIndex(tagged, kind) : -1;
        };
        let clone = leaf.cloneNode(true);
        if (viewport) {
          const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
          group.appendChild(clone);
          clone = group;
        }
        clone.setAttribute('transform', `matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e} ${m.f})`);
        result.push({ svg: `<svg xmlns="http://www.w3.org/2000/svg">${clone.outerHTML}</svg>`, bbox,
          part: tag('part'), sub: tag('sub') });
      }
      return result;
    } finally {
      host.remove();
    }
  },

  /**
   * The index in a manim-part-i / manim-sub-k class, or -1. MathJax merges nested
   * \class tags on one node (class="manim-sub-0 manim-part-1").
   */
  classIndex(node, kind) {
    const match = new RegExp(`(?:^|\\s)manim-${kind}-(\\d+)(?:\\s|$)`).exec(node.getAttribute('class') || '');
    return match ? Number(match[1]) : -1;
  },

  /** One SVG per \class{manim-part-i} group, each keeping only its own glyphs. */
  splitParts(svg) {
    const tagged = node => [...node.querySelectorAll('*')].filter(n => this.classIndex(n, 'part') >= 0);
    // A part may be tagged in several runs (around ^ and _); count distinct indices.
    const count = Math.max(0, ...tagged(svg).map(n => this.classIndex(n, 'part') + 1));
    const parts = [];
    for (let index = 0; index < count; index++) {
      const clone = svg.cloneNode(true);
      for (const node of tagged(clone)) {
        if (this.classIndex(node, 'part') !== index) node.remove();
      }
      parts.push({ svg: clone.outerHTML, bbox: this.measure(clone) });
    }
    return parts;
  },
  /**
   * MathJax widens every ruled fraction by 0.1em on each side of its numerator,
   * denominator and rule; TeX does not. Lay fractions out as TeX does, so formula
   * sizes match Manim's LaTeX output.
   */
  patchFractions(mathjax) {
    const mfrac = mathjax?.startup?.output?.factory?.getNodeClass?.('mfrac');
    if (!mfrac || mfrac.prototype.texFractions) return;
    mfrac.prototype.texFractions = true;
    mfrac.prototype.getFractionBBox = function (bbox, display, t) {
      const nbox = this.childNodes[0].getOuterBBox(), dbox = this.childNodes[1].getOuterBBox();
      const a = this.font.params.axis_height;
      const { T, u, v } = this.getTUV(display, t);
      bbox.combine(nbox, 0, a + T + Math.max(nbox.d * nbox.rscale, u));
      bbox.combine(dbox, 0, a - T - Math.max(dbox.h * dbox.rscale, v));
      bbox.w += 2 * this.pad;
    };
    mfrac.prototype.makeFraction = function (display, t) {
      const svg = this.element;
      const { numalign, denomalign } = this.node.attributes.getList('numalign', 'denomalign');
      const [num, den] = this.childNodes;
      const nbox = num.getOuterBBox(), dbox = den.getOuterBBox();
      const a = this.font.params.axis_height;
      const pad = this.node.getProperty('withDelims') ? 0 : this.font.params.nulldelimiterspace;
      const w = Math.max((nbox.L + nbox.w + nbox.R) * nbox.rscale, (dbox.L + dbox.w + dbox.R) * dbox.rscale);
      const { T, u, v } = this.getTUV(display, t);
      num.toSVG(svg);
      num.place(this.getAlignX(w, nbox, numalign) + pad, a + T + Math.max(nbox.d * nbox.rscale, u));
      den.toSVG(svg);
      den.place(this.getAlignX(w, dbox, denomalign) + pad, a - T - Math.max(dbox.h * dbox.rscale, v));
      this.adaptor.append(svg, this.svg('rect', { width: this.fixed(w), height: this.fixed(t), x: this.fixed(pad), y: this.fixed(a - t / 2) }));
    };
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
          this.patchFractions(window.MathJax);
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

  /**
   * Manim typesets MathTex inside align*: rows (\\\\) and alignment points (&) outside other
   * environments need that environment in MathJax too.
   */
  texSource(expression) {
    let outer = expression, previous;
    do {
      previous = outer;
      outer = outer.replace(/\\begin\{([^{}]*)\}(?:(?!\\begin\{)[\s\S])*?\\end\{\1\}/g, '');
    } while (outer !== previous);
    return /(^|[^\\])&|\\\\/.test(outer) ? `\\begin{align*}${expression}\\end{align*}` : expression;
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
        const container = await math.tex2svgPromise(this.texSource(expression), { display: true });
        if (!isCurrent()) return null;
        const svg = container.querySelector('svg');
        if (!svg || container.querySelector('[data-mml-node="merror"]')) {
          throw new Error('Invalid or unsupported TeX expression.');
        }
        // Nested svg viewports clip the extension pieces of stretchy delimiters; text
        // elements draw characters MathJax has no glyph for (e.g. CJK) with a browser font.
        const tags = new Set(['g', 'svg', 'path', 'rect', 'line', 'polygon', 'polyline', 'circle', 'ellipse', 'text']);
        for (const node of svg.querySelectorAll('*')) {
          if (!tags.has(node.localName) || (node.localName === 'text' && node.children.length)) {
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
        const leaves = this.glyphLeaves(svg);
        if (leaves) {
          asset.glyphs = leaves;
          size += leaves.reduce((total, glyph) => total + glyph.svg.length, 0);
        }
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
