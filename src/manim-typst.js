/**
 * Compile Typst documents requested by Python (typst_pending) to SVG with typst.ts, the
 * Typst compiler built for WebAssembly. Community compiles the same documents with the
 * typst package and imports the SVG; Python imports these the same way.
 */
const ManimTypst = {
  VERSION: '0.7.0',
  loading: null,
  cache: new Map(),

  load() {
    if (!this.loading) {
      this.loading = new Promise((resolve, reject) => {
        if (typeof document === 'undefined') {
          reject(new Error('Typst compilation needs a browser.'));
          return;
        }
        const base = 'https://cdn.jsdelivr.net/npm/@myriaddreamin';
        const script = document.createElement('script');
        script.type = 'module';
        script.src = `${base}/typst.ts@${this.VERSION}/dist/esm/contrib/all-in-one-lite.bundle.js`;
        const timeout = setTimeout(() => {
          script.remove();
          reject(new Error('Typst could not load. Check your connection and try again.'));
        }, 60000);
        script.onload = () => {
          const typst = window.$typst;
          if (!typst) {
            clearTimeout(timeout);
            reject(new Error('Typst could not load.'));
            return;
          }
          typst.setCompilerInitOptions({
            getModule: () => `${base}/typst-ts-web-compiler@${this.VERSION}/pkg/typst_ts_web_compiler_bg.wasm`
          });
          typst.setRendererInitOptions({
            getModule: () => `${base}/typst-ts-renderer@${this.VERSION}/pkg/typst_ts_renderer_bg.wasm`
          });
          clearTimeout(timeout);
          resolve(typst);
        };
        script.onerror = () => {
          clearTimeout(timeout);
          script.remove();
          reject(new Error('Typst could not load. Check your connection and try again.'));
        };
        document.head.appendChild(script);
      }).catch(error => { this.loading = null; throw error; });
    }
    return this.loading;
  },

  /** Keep the geometry: drop the viewer's stylesheet, script and text-selection overlays. */
  clean(svg) {
    return svg.replace(/<style[\s\S]*?<\/style>/g, '').replace(/<script[\s\S]*?<\/script>/g, '')
      .replace(/<foreignObject[\s\S]*?<\/foreignObject>/g, '');
  },

  async compile(sources, isCurrent = () => true, load = () => this.load()) {
    const result = {};
    if (!sources || !sources.length) return result;
    if (sources.length > 64) throw new Error('Preview is limited to 64 distinct Typst documents.');
    if (!isCurrent()) return null;
    const typst = await load();
    for (const source of sources) {
      if (!isCurrent()) return null;
      if (typeof source !== 'string' || source.length > 100000) throw new Error('Typst sources are limited to 100000 characters.');
      if (!this.cache.has(source)) {
        let svg;
        try {
          svg = this.clean(await typst.svg({ mainContent: source }));
        } catch (error) {
          throw new Error('Typst: ' + String(error.message || error));
        }
        if (svg.length > 2 * 1024 * 1024) throw new Error('Typst output is too large. Simplify the document.');
        this.cache.set(source, svg);
        if (this.cache.size > 256) this.cache.delete(this.cache.keys().next().value);
      }
      result[source] = this.cache.get(source);
    }
    return result;
  }
};

if (typeof module !== 'undefined' && module.exports) module.exports = ManimTypst;
else window.ManimTypst = ManimTypst;
