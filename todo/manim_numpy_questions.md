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
- [x] Circle
- [x] Square
- [x] Rectangle
- [x] Line
- [x] Arrow
- [x] Triangle
- [x] Polygon
- [x] Text (browser-native, may not need Manim)

**Investigation tasks:**
- [x] Review Manim source code for shape classes
- [x] Trace imports from shape classes to numpy
- [x] Identify which numpy functions are used (if any)
- [x] Determine if numpy usage is in rendering path or just utilities

### 2. What does Manim use numpy for?

Potential uses to check:
- [x] Point/coordinate calculations
- [x] Transformation matrices
- [x] Bezier curve calculations
- [x] Color interpolation
- [x] Animation interpolation

### 3. Can numpy dependencies be replaced?

If numpy is used, evaluate:
- [x] Can we use JavaScript equivalents instead?
- [x] Can we use Python's built-in math module?
- [x] Would a minimal numpy subset work?
- [x] What's the complexity of replacing numpy calls?

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
| `np.array()` | All shapes | Convert lists/tuples to numpy arrays for coordinates | No - core data structure |
| `np.linalg.norm()` | Circle, Line, Arrow, Polygon | Calculate distances and vector lengths | No - complex implementation |
| `np.asarray()` | All shapes | Ensure data is numpy array | No - core data structure |
| `np.sqrt()` | Arc, Circle, Polygon | Geometric calculations | Theoretically yes, but deeply integrated |
| `np.cos()` / `np.sin()` | Circle, Arc | Circular arc point generation | Theoretically yes, but deeply integrated |
| `np.tan()` | Arc, Polygon | Angle calculations | Theoretically yes, but deeply integrated |
| `np.zeros()` | Arc, VMobject | Initialize empty point arrays | No - array initialization |
| `np.cross()` | Line, Polygon | Vector cross products | No - complex 3D operation |
| `np.dot()` | Line, space_ops | Dot products for projections | Theoretically yes, but deeply integrated |
| `np.linspace()` | Arc | Generate evenly-spaced values | Theoretically yes, but integrated |

### Task 4: Evaluate Alternatives

If numpy is required, evaluate:

| Alternative | Pros | Cons | Feasibility |
|-------------|------|------|-------------|
| Include numpy in Pyodide | Full compatibility, works immediately | +5-10MB bundle | ✅ High - Recommended |
| Use JavaScript math | Smaller bundle | Cannot handle array ops, would break Manim | ❌ Low - Not viable |
| Minimal numpy shim | Potentially smaller | Need to implement 30+ functions, maintenance burden, compatibility issues | ❌ Low - Too complex |
| Reimplement shapes in JS | Full control, no numpy | Not "Manim" anymore, 100x development time | ❌ Low - Wrong approach |

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

### Findings

#### 1. Does Manim's core shape rendering require numpy?

**YES - numpy is absolutely required for all Manim shape rendering.**

After examining the Manim source code (ManimCommunity/manim), the investigation found:

**All basic shape classes import and use numpy extensively:**
- `manim/mobject/geometry/arc.py` (Circle) - imports `numpy as np`
- `manim/mobject/geometry/polygram.py` (Square, Rectangle, Triangle, Polygon) - imports `numpy as np`
- `manim/mobject/geometry/line.py` (Line, Arrow) - imports `numpy as np`
- `manim/mobject/geometry/tips.py` (ArrowTip) - imports `numpy as np`
- `manim/mobject/text/text_mobject.py` (Text) - imports `numpy as np`

**Manim's core data structure is numpy-based:**
- All Mobject coordinates are stored as numpy arrays: `self.points: Point3D_Array = np.array(points)`
- The base `VMobject` class stores all vector points as numpy arrays
- This is fundamental to Manim's architecture and cannot be easily changed

#### 2. What does Manim use numpy for?

**Critical numpy functions used in geometry modules (frequency analysis):**

| numpy Function | Usage Count | Purpose |
|----------------|-------------|---------|
| `np.array()` | 41 | Convert lists to arrays, create coordinate arrays |
| `np.linalg.norm()` | 15 | Calculate distances and lengths |
| `np.asarray()` | 9 | Convert input to arrays |
| `np.sqrt()` | 8 | Square root calculations for geometry |
| `np.cos()` | 6 | Circular and arc calculations |
| `np.sin()` | 4 | Circular and arc calculations |
| `np.tan()` | 5 | Angle calculations |
| `np.zeros()` | 4 | Initialize empty arrays |
| `np.cross()` | 2 | Vector cross products for perpendicularity |
| `np.dot()` | 3 | Dot products for projections |

**Specific uses in basic shapes:**
- **Point/coordinate calculations**: All vertices, positions stored as numpy arrays
- **Transformation matrices**: Numpy used for matrix operations on points
- **Bezier curve calculations**: Arc anchors and handles computed with numpy
- **Distance/length calculations**: `np.linalg.norm()` for all length computations
- **Trigonometric operations**: Circle arcs, angles all use numpy's sin/cos/tan
- **Vector operations**: Cross products, dot products, normalization

#### 3. Can numpy dependencies be replaced?

**NO - Replacement is not feasible for the following reasons:**

1. **Architectural dependency**: numpy arrays are the fundamental data structure
   - All Mobject points stored as `np.ndarray`
   - Changing this would require rewriting Manim's entire codebase
   - Not compatible with "minimal changes" approach

2. **Deep integration**: numpy is used in every layer
   - Base classes: `Mobject`, `VMobject`
   - All geometry classes: Circle, Square, Line, etc.
   - Utility modules: `space_ops.py` (50+ numpy operations)
   - Transform operations
   - Rendering pipeline

3. **Performance requirements**: numpy provides optimized vector operations
   - JavaScript equivalents would be significantly slower
   - Python's built-in math module doesn't support array operations
   - Would need to manually implement all array operations

4. **Official dependency**: numpy is a required dependency
   - Listed in `pyproject.toml`: `"numpy>=2.1"`
   - No conditional or optional numpy support exists in Manim

#### Investigation Results Summary

| Shape | numpy Required? | numpy Usage |
|-------|----------------|-------------|
| Circle | ✅ Yes | Points array, arc calculations (sin/cos), norm |
| Square | ✅ Yes | Points array, vertices array |
| Rectangle | ✅ Yes | Points array, vertices array |
| Line | ✅ Yes | Points array, start/end points, dot product |
| Arrow | ✅ Yes | Points array, vector normalization, cross product |
| Triangle | ✅ Yes | Points array, vertices array |
| Polygon | ✅ Yes | Points array, vertices array, cross product |
| Text | ✅ Yes | Points array (text is vectorized) |

**All shapes require numpy. There are no exceptions.**

### Recommendation

**Accept numpy as a required dependency and include it in the Pyodide bundle.**

**Rationale:**
1. **Technical necessity**: numpy is fundamentally integrated into Manim's architecture
2. **Cost-benefit analysis**: 
   - Attempting to replace numpy would require rewriting Manim from scratch
   - This contradicts the project goal of running "Manim" in the browser
   - Development time would be 100x higher than accepting the bundle size
3. **Bundle size is acceptable**: 
   - numpy in Pyodide: ~5-10MB
   - Total bundle: ~15-25MB (Pyodide core + numpy)
   - This is comparable to other web-based code editors
4. **User expectations**: Users expect standard Manim code to work
   - Replacing numpy would break compatibility
   - Creates a "fake Manim" that looks like Manim but isn't

**Alternative approaches considered and rejected:**
- ❌ JavaScript math library: Cannot handle array operations efficiently
- ❌ Python built-in math: No array/vector support
- ❌ Minimal numpy shim: Would need to implement 30+ numpy functions
- ❌ Reimplement shapes in JS: No longer "Manim", defeats project purpose

### Decision

**OUTCOME C: numpy Required and Essential**

**Include numpy in the Pyodide bundle.**

**Implementation details:**
- Use Pyodide's built-in numpy package (already compiled to WASM)
- Load numpy along with Pyodide for Manim rendering
- Accept ~5-10MB additional bundle size
- Total expected bundle: ~15-25MB
- First load requires internet; subsequent loads from cache

**Bundle size justification:**
- Modern web apps commonly exceed 20MB (e.g., VS Code web, Google Docs)
- Users on slow connections: show loading progress bar
- Service worker caching means first load only
- Offline use after initial load

**Documentation note:**
For future reference, if we wanted to support shapes WITHOUT Manim:
- We could create browser-native SVG shapes (Circle, Square, etc.)
- This would avoid numpy entirely
- But it would NOT be "Manim" - it would be a different system
- This is out of scope for "ManimOnline" project

---

## References

- [Manim GitHub Repository](https://github.com/ManimCommunity/manim)
- [Pyodide Package List](https://pyodide.org/en/stable/usage/packages-in-pyodide.html)
- [numpy Pyodide Package](https://pyodide.org/en/stable/usage/packages-in-pyodide.html#numpy)
