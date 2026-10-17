/** Compile formulas once per render; playback/export use self-contained SVG paths. */
/**
 * Cubic outline curves [[x, y] x 4, ...] of SVG path data under the affine map m (a DOMMatrix-like
 * {a, b, c, d, e, f}), the way Manim's SVGMobject reads paths: quadratics are raised to
 * cubics, lines get handles at thirds and a closing line is added when the end is not the
 * start. Returns null for unsupported data (arcs).
 */
function pathOutline(data, m) {
  const tokens = String(data).match(/[a-zA-Z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/g) || [];
  const map = ([x, y]) => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f];
  const curves = [];
  let i = 0, command = null, current = [0, 0], start = [0, 0], control = null, previous = null;
  const number = () => {
    const value = Number(tokens[i++]);
    if (!Number.isFinite(value)) throw new Error('bad path');
    return value;
  };
  const line = (a, b) => curves.push([a, [(2 * a[0] + b[0]) / 3, (2 * a[1] + b[1]) / 3],
    [(a[0] + 2 * b[0]) / 3, (a[1] + 2 * b[1]) / 3], b]);
  const cubic = (c1, c2, end) => curves.push([current, c1, c2, end]);
  const close = () => {
    if (Math.hypot(current[0] - start[0], current[1] - start[1]) > 1e-9) line(current, start);
    current = start;
  };
  try {
    while (i < tokens.length) {
      if (/[a-zA-Z]/.test(tokens[i])) command = tokens[i++];
      else if (command === null) return null;
      const relative = command === command.toLowerCase();
      const base = relative ? current : [0, 0];
      const point = () => { const x = number(), y = number(); return [base[0] + x, base[1] + y]; };
      let next = null;
      switch (command.toUpperCase()) {
        case 'M': current = start = point(); command = relative ? 'l' : 'L'; break;
        case 'L': next = point(); line(current, next); current = next; break;
        case 'H': next = [(relative ? current[0] : 0) + number(), current[1]]; line(current, next); current = next; break;
        case 'V': next = [current[0], (relative ? current[1] : 0) + number()]; line(current, next); current = next; break;
        case 'C': { const c1 = point(), c2 = point(); next = point(); cubic(c1, c2, next); control = c2; current = next; break; }
        case 'S': {
          const c1 = previous === 'C' ? [2 * current[0] - control[0], 2 * current[1] - control[1]] : current;
          const c2 = point(); next = point(); cubic(c1, c2, next); control = c2; current = next; break;
        }
        case 'Q': case 'T': {
          const q = command.toUpperCase() === 'Q' ? point() :
            previous === 'Q' ? [2 * current[0] - control[0], 2 * current[1] - control[1]] : current;
          next = point();
          cubic([current[0] + 2 / 3 * (q[0] - current[0]), current[1] + 2 / 3 * (q[1] - current[1])],
            [next[0] + 2 / 3 * (q[0] - next[0]), next[1] + 2 / 3 * (q[1] - next[1])], next);
          control = q; current = next; previous = 'Q'; continue;
        }
        case 'Z': close(); break;
        default: return null;
      }
      previous = command.toUpperCase() === 'C' || command.toUpperCase() === 'S' ? 'C' : null;
    }
  } catch (error) {
    return null;
  }
  if (curves.length && Math.hypot(current[0] - start[0], current[1] - start[1]) > 1e-9) close();
  return curves.map(curve => curve.map(map));
}

/** Outline curves of one drawable element under m, or null (text, clipped viewports, arcs). */
function elementOutline(node, m) {
  const number = name => Number(node.getAttribute(name)) || 0;
  switch (node.localName) {
    case 'path': return pathOutline(node.getAttribute('d') || '', m);
    case 'rect': {
      const x = number('x'), y = number('y'), w = number('width'), h = number('height');
      return pathOutline(`M${x} ${y}H${x + w}V${y + h}H${x}Z`, m);
    }
    case 'line':
      return pathOutline(`M${number('x1')} ${number('y1')}L${number('x2')} ${number('y2')}`, m);
    case 'polygon': case 'polyline': {
      const values = (node.getAttribute('points') || '').trim().split(/[\s,]+/).map(Number);
      if (values.length < 4 || values.some(v => !Number.isFinite(v))) return null;
      return pathOutline('M' + values.join(' ') + (node.localName === 'polygon' ? 'Z' : ''), m);
    }
    default: return null;
  }
}

// MathJax codepoints of ellipses that TeX typesets as three separate dots.
const DOT_GLYPHS = new Set(['2026', '22EF', '22EE', '22F1']);

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
        // Outlines travel as flat x, y pairs in em, relative to the ink center with y up.
        const cx = x + width / 2, cy = y + height / 2;
        const round = v => Math.round(v * 1000) / 1000;
        let budget = 40000;
        size.push(asset.glyphs.map(glyph => {
          const entry = [...relative(glyph.bbox), glyph.part, glyph.sub ?? -1];
          const points = glyph.outline ? glyph.outline.flat() : null;
          if (points && points.length * 2 <= budget) {
            budget -= points.length * 2;
            entry.push(points.flatMap(([px, py]) => [round((px - cx) / 1000), round(-(py - cy) / 1000)]));
          }
          return entry;
        }));
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
          else if (kid.localName === 'path' && DOT_GLYPHS.has(kid.getAttribute('data-c'))) {
            // TeX sets \dots, \cdots, \vdots and \ddots as three dot glyphs; MathJax draws one
            // path of three contours. Split it into one leaf per contour.
            for (const contour of (kid.getAttribute('d') || '').match(/[Mm][^Mm]*/g) || []) {
              const piece = kid.cloneNode(false);
              piece.setAttribute('d', contour);
              kid.parentNode.insertBefore(piece, kid);
              leaves.push(piece);
            }
            kid.remove();
          }
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
        const corners = (b, t) => {
          const xs = [], ys = [];
          for (const [px, py] of [[b.x, b.y], [b.x + b.width, b.y], [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]]) {
            xs.push(t.a * px + t.c * py + t.e);
            ys.push(t.b * px + t.d * py + t.f);
          }
          return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
        };
        let [x0, y0, x1, y1] = corners(box, m);
        if (viewport) {
          // The visible ink of a clipped stretchy piece: its content within the viewport.
          let ink = null;
          for (const node of leaf.querySelectorAll('path, rect, line, polygon, polyline')) {
            const ctm = node.getScreenCTM && node.getScreenCTM();
            if (!ctm) continue;
            const [a, b, c, d] = corners(node.getBBox(), inverse.multiply(ctm));
            ink = ink ? [Math.min(ink[0], a), Math.min(ink[1], b), Math.max(ink[2], c), Math.max(ink[3], d)] : [a, b, c, d];
          }
          if (ink && ink[0] < x1 && ink[2] > x0 && ink[1] < y1 && ink[3] > y0) {
            [x0, y0, x1, y1] = [Math.max(x0, ink[0]), Math.max(y0, ink[1]), Math.min(x1, ink[2]), Math.min(y1, ink[3])];
          }
        }
        const bbox = [x0, y0, x1 - x0, y1 - y0];
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
        // Community's glyphs are outline paths: send them (formula units) for Python's points.
        // A clipped stretchy piece (rules, extenders) is outlined by its visible box.
        const outline = viewport ? pathOutline(`M${x0} ${y0}H${x1}V${y1}H${x0}Z`, { a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 })
          : elementOutline(leaf, m);
        result.push({ svg: `<svg xmlns="http://www.w3.org/2000/svg">${clone.outerHTML}</svg>`, bbox,
          part: tag('part'), sub: tag('sub'), ...(outline && outline.length ? { outline } : {}),
          ...(viewport ? { viewport: true } : {}) });
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
        if (leaves && leaves.some(leaf => leaf.viewport)) {
          // getBBox counts a clipped stretchy piece's whole geometry; its viewport is the ink.
          const x0 = Math.min(...leaves.map(l => l.bbox[0])), y0 = Math.min(...leaves.map(l => l.bbox[1]));
          const x1 = Math.max(...leaves.map(l => l.bbox[0] + l.bbox[2])), y1 = Math.max(...leaves.map(l => l.bbox[1] + l.bbox[3]));
          asset.bbox = [x0, y0, x1 - x0, y1 - y0];
        }
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

ManimMath.pathOutline = pathOutline;

if (typeof module !== 'undefined' && module.exports) module.exports = ManimMath;
else window.ManimMath = ManimMath;
