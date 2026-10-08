/** Compile formulas once per render; playback/export use self-contained SVG paths. */
const ManimMath = {
  loading: null,
  load() {
    if (!this.loading) {
      this.loading = new Promise((resolve, reject) => {
        window.MathJax = {
          startup: { typeset: false },
          tex: { packages: ['base', 'ams'], maxMacros: 1000, maxBuffer: 4096,
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
        glyphs.set(expression, { svg: svg.outerHTML, viewBox });
      } catch (error) {
        throw new Error('MathTex: ' + error.message);
      }
    }
    return glyphs;
  }
};

if (typeof module !== 'undefined' && module.exports) module.exports = ManimMath;
else window.ManimMath = ManimMath;
