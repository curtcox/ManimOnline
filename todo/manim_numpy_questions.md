# Manim numpy Dependency Investigation

## Purpose

Determine whether numpy is required for rendering basic Manim shapes in ManimOnline, and if so, understand the bundle size implications.

## Context

- ManimOnline will use **minimal Pyodide** (~10-15MB core)
- Adding numpy increases bundle size by ~5-10MB
- We only need to support **basic shapes** for MVP (see master_plan.md Phase 4)

## Key Questions

### 1. Does Manim's core shape rendering require numpy?

**Shapes to investigate:**
- [ ] Circle
- [ ] Square
- [ ] Rectangle
- [ ] Line
- [ ] Arrow
- [ ] Triangle
- [ ] Polygon
- [ ] Text (browser-native, may not need Manim)

**Investigation tasks:**
- [ ] Review Manim source code for shape classes
- [ ] Trace imports from shape classes to numpy
- [ ] Identify which numpy functions are used (if any)
- [ ] Determine if numpy usage is in rendering path or just utilities

### 2. What does Manim use numpy for?

Potential uses to check:
- [ ] Point/coordinate calculations
- [ ] Transformation matrices
- [ ] Bezier curve calculations
- [ ] Color interpolation
- [ ] Animation interpolation

### 3. Can numpy dependencies be replaced?

If numpy is used, evaluate:
- [ ] Can we use JavaScript equivalents instead?
- [ ] Can we use Python's built-in math module?
- [ ] Would a minimal numpy subset work?
- [ ] What's the complexity of replacing numpy calls?

## Research Tasks

### Task 1: Examine Manim Shape Source Code

```bash
# Clone Manim and search for numpy imports in shape-related files
git clone https://github.com/ManimCommunity/manim.git
grep -r "import numpy" manim/mobject/geometry/
grep -r "from numpy" manim/mobject/geometry/
```

**Files to examine:**
- `manim/mobject/geometry/arc.py` (Circle)
- `manim/mobject/geometry/polygram.py` (Square, Rectangle, Triangle, Polygon)
- `manim/mobject/geometry/line.py` (Line, Arrow)
- `manim/mobject/text/text_mobject.py` (Text)

### Task 2: Trace Critical Code Paths

For each shape, trace the rendering path:
1. Constructor (`__init__`)
2. Point generation
3. SVG/path generation
4. Any transformation methods we need (shift, move_to, scale)

### Task 3: Document numpy Usage

Create a table of numpy functions used:

| numpy Function | Used By | Purpose | Replaceable? |
|----------------|---------|---------|--------------|
| (to be filled) | | | |

### Task 4: Evaluate Alternatives

If numpy is required, evaluate:

| Alternative | Pros | Cons | Feasibility |
|-------------|------|------|-------------|
| Include numpy in Pyodide | Full compatibility | +5-10MB bundle | High |
| Use JavaScript math | Smaller bundle | Rewrite required | Medium |
| Minimal numpy shim | Smaller than full numpy | Maintenance burden | Low |
| Reimplement shapes in JS | Full control | Significant work | Low |

## Expected Outcomes

### Outcome A: numpy Not Required
- Basic shapes can render without numpy
- Keep minimal Pyodide bundle (~10-15MB)
- Document which features DO require numpy for future reference

### Outcome B: numpy Required but Replaceable
- Identify specific numpy functions needed
- Evaluate effort to replace with alternatives
- Decide whether to replace or include numpy

### Outcome C: numpy Required and Essential
- Include numpy in Pyodide bundle
- Accept ~5-10MB additional bundle size
- Total bundle: ~15-25MB
- Document this decision

## Decision Criteria

| Factor | Weight | Notes |
|--------|--------|-------|
| Bundle size impact | High | Users on slow connections |
| Implementation complexity | Medium | Time to implement alternatives |
| Compatibility with Manim code | High | Users expect standard Manim to work |
| Maintenance burden | Medium | Long-term supportability |

## Timeline

This investigation should be completed before Phase 4 implementation begins.

## Results

*(To be filled after investigation)*

### Findings

### Recommendation

### Decision

---

## References

- [Manim GitHub Repository](https://github.com/ManimCommunity/manim)
- [Pyodide Package List](https://pyodide.org/en/stable/usage/packages-in-pyodide.html)
- [numpy Pyodide Package](https://pyodide.org/en/stable/usage/packages-in-pyodide.html#numpy)
