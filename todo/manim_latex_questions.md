# Manim LaTeX Rendering Investigation

## Purpose

Determine the best approach for rendering mathematical expressions (MathTex) in ManimOnline without a native LaTeX installation.

## Context

- Manim uses LaTeX for `MathTex` and `Tex` objects
- Browser environments don't have LaTeX installed
- Need browser-based alternative for math rendering
- Must integrate with Manim's SVG/Canvas output pipeline

## Options Under Consideration

### Option A: MathJax 3

**Overview:** Full-featured LaTeX renderer for the web.

| Aspect | Details |
|--------|---------|
| Bundle Size | ~1MB (full), ~500KB (minimal) |
| LaTeX Coverage | Excellent - nearly complete |
| Rendering Speed | Slower (async, DOM-based) |
| Output Format | SVG, HTML+CSS, or MathML |
| License | Apache 2.0 |

**Pros:**
- Most complete LaTeX support
- Widely used and well-maintained
- Excellent documentation
- Supports custom macros

**Cons:**
- Larger bundle size
- Async rendering adds complexity
- May need DOM access (problematic in web worker)

### Option B: KaTeX

**Overview:** Fast, lightweight LaTeX renderer.

| Aspect | Details |
|--------|---------|
| Bundle Size | ~300KB |
| LaTeX Coverage | Good - common expressions |
| Rendering Speed | Fast (sync, no DOM required) |
| Output Format | HTML+CSS or SVG |
| License | MIT |

**Pros:**
- Smaller bundle size
- Synchronous rendering
- Can run without DOM (server-side rendering)
- Very fast

**Cons:**
- Limited LaTeX macro support
- Some advanced expressions not supported
- Less comprehensive than MathJax

### Option C: Defer to v1.0

**Overview:** Support only `Text` in MVP, add `MathTex` later.

| Aspect | Details |
|--------|---------|
| Bundle Size | 0 (no additional) |
| LaTeX Coverage | None |
| Implementation | Simple error message for MathTex |

**Pros:**
- Simplest MVP implementation
- No additional bundle size
- Can evaluate user demand first

**Cons:**
- MathTex is a key Manim feature
- May disappoint users expecting math support
- Delays a core feature

## Research Tasks

### Task 1: Evaluate KaTeX Coverage

Test these common Manim MathTex expressions:

| Expression | KaTeX Support | Notes |
|------------|---------------|-------|
| `\frac{a}{b}` | | Fractions |
| `\int_0^1 x dx` | | Integrals |
| `\sum_{i=1}^n` | | Summations |
| `\sqrt{x}` | | Square roots |
| `\matrix` | | Matrices |
| `\begin{align}` | | Alignment |
| Custom macros | | User-defined |

### Task 2: Test Web Worker Compatibility

| Library | Works in Worker? | Notes |
|---------|------------------|-------|
| MathJax 3 | | May need DOM shim |
| KaTeX | | Should work with SVG output |

### Task 3: Benchmark Performance

Test rendering 10 math expressions:

| Library | Time (cold) | Time (warm) | Memory |
|---------|-------------|-------------|--------|
| MathJax 3 | | | |
| KaTeX | | | |

### Task 4: Integration Complexity

Evaluate how each integrates with Manim's pipeline:

| Library | Integration Steps | Complexity |
|---------|-------------------|------------|
| MathJax 3 | | |
| KaTeX | | |

### Task 5: Visual Quality Comparison

Render same expressions with both libraries, compare:
- Font quality
- Spacing accuracy
- Alignment precision
- Match to native LaTeX output

## Decision Criteria

| Factor | Weight | Notes |
|--------|--------|-------|
| Bundle size | Medium | KaTeX wins here |
| LaTeX coverage | High | MathJax wins here |
| Rendering speed | Medium | KaTeX wins here |
| Web worker compatibility | High | Critical for architecture |
| Visual quality | High | Must look professional |
| Implementation complexity | Medium | Time to integrate |

## Proof of Concept Tasks

### POC 1: KaTeX in Web Worker

```javascript
// Test KaTeX rendering in web worker
importScripts('https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js');

self.onmessage = function(e) {
  const latex = e.data;
  try {
    const html = katex.renderToString(latex, { throwOnError: false });
    self.postMessage({ success: true, html });
  } catch (error) {
    self.postMessage({ success: false, error: error.message });
  }
};
```

### POC 2: MathJax in Web Worker

```javascript
// Test MathJax rendering in web worker
// May require additional setup for DOM-less environment
```

### POC 3: Integration with Manim SVG Output

- Render math expression to SVG
- Convert to Manim-compatible path/shape
- Position within scene

## Expected Outcomes

### If KaTeX is Sufficient
- Use KaTeX for smaller bundle
- Document unsupported LaTeX features
- Provide fallback error messages

### If MathJax Required
- Accept larger bundle size
- Investigate async rendering integration
- May need DOM shim in worker

### If Both Problematic
- Defer MathTex to v1.0
- Focus MVP on Text only
- Revisit after core features stable

## Timeline

This investigation should be completed before Phase 4 implementation begins.

## Results

*(To be filled after investigation)*

### Findings

### Recommendation

### Decision

---

## References

- [KaTeX Documentation](https://katex.org/)
- [KaTeX Supported Functions](https://katex.org/docs/supported.html)
- [MathJax Documentation](https://docs.mathjax.org/)
- [MathJax v3 Migration](https://docs.mathjax.org/en/latest/upgrading/v2.html)
- [Manim MathTex Source](https://github.com/ManimCommunity/manim/blob/main/manim/mobject/text/tex_mobject.py)
