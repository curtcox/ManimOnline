# ManimOnline Master Plan

## Project Vision

Create a web-based editor similar to [GraphvizOnline](https://dreampuf.github.io/GraphvizOnline) that supports both Graphviz DOT language diagrams and Manim Python animations, with automatic detection and appropriate rendering.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Phase 1: Import GraphvizOnline](#phase-1-import-graphvizonline)
3. [Phase 2: GitHub Pages Deployment](#phase-2-github-pages-deployment)
4. [Phase 3: Pyodide Integration](#phase-3-pyodide-integration)
5. [Phase 4: Manim Web Worker](#phase-4-manim-web-worker)
6. [Phase 5: Content Type Detection](#phase-5-content-type-detection)
7. [Phase 6: Unified Rendering Pipeline](#phase-6-unified-rendering-pipeline)
8. [Test Plan](#test-plan)
9. [Open Questions](#open-questions)
10. [Technical Risks](#technical-risks)
11. [Dependencies Map](#dependencies-map)

---

## Architecture Overview

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Worker Architecture | **Single worker** | Simpler communication, unified message handling |
| Animation Output | **Frame-by-frame** | More control, seekable, no video encoding needed |
| Detection Timing | **Debounced (1 second)** | Better performance, acceptable UI delay |
| Rendering Trigger | **Automatic** | Better UX for quick iteration |
| Offline Support | **Service workers (required)** | Core requirement for offline editing |
| Backend | **Pure static site** | Simpler deployment, no server costs |
| Hard Timeout | **90 seconds** | Balance between complex scenes and runaway prevention |
| First Load Offline | **Show error message** | Clear communication, requires internet for first load |

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser Main Thread                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  ACE Editor  │  │   Detector   │  │    Output Display      │ │
│  │  (Code Input)│  │  (Debounced) │  │  (SVG/Canvas/Frames)   │ │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬───────────┘ │
│         │                 │                       │             │
│         └────────────────┬┴───────────────────────┘             │
│                          │                                       │
│  ┌───────────────────────┴───────────────────────────────────┐  │
│  │                    Service Worker                          │  │
│  │              (Caching for offline support)                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                       │
├──────────────────────────┼───────────────────────────────────────┤
│                   Single Unified Worker                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  ┌───────────────┐  ┌─────────────────────────────────────┐ ││
│  │  │   viz.js      │  │   Pyodide (Python WASM)             │ ││
│  │  │  (Graphviz)   │  │  ┌───────────────────────────────┐  │ ││
│  │  └───────────────┘  │  │  Manim-lite (Basic Shapes)    │  │ ││
│  │                     │  └───────────────────────────────┘  │ ││
│  │                     └─────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Import GraphvizOnline

### Goal
Fork and integrate the GraphvizOnline codebase as the foundation for ManimOnline.

### Tasks

1.1. **Clone/Download GraphvizOnline source**
   - Source: https://github.com/dreampuf/GraphvizOnline
   - License: BSD-3-Clause (compatible)

1.2. **Inventory existing files**
   - `index.html` - Main application interface
   - `viz-global.js` - Compiled Graphviz library (Emscripten)
   - `svg-pan-zoom.min.js` - SVG interaction library
   - `ace/` directory - ACE editor components
   - `.github/workflows/` - Existing CI/CD (if any)

1.3. **Copy files to ManimOnline repository**
   - Preserve directory structure
   - Update any hardcoded references to "GraphvizOnline"
   - Rename/rebrand as appropriate

1.4. **Verify Graphviz functionality works locally**
   - Test basic DOT rendering
   - Test URL parameter loading (`?url=`, `?presentation`)
   - Test pan-zoom functionality

### Deliverables
- [ ] All GraphvizOnline source files copied to repository
- [ ] Local development server runs successfully
- [ ] Graphviz rendering works identically to original

---

## Phase 2: GitHub Pages Deployment

### Goal
Set up automated deployment to GitHub Pages via GitHub Actions.

### Tasks

2.1. **Create GitHub Actions workflow file**
   - `.github/workflows/deploy.yml`
   - Trigger on push to `main` branch
   - Build static site (if build step needed)
   - Deploy to `gh-pages` branch

2.2. **Configure repository settings**
   - Enable GitHub Pages
   - Set source to `gh-pages` branch or Actions

2.3. **Add build script (if needed)**
   - Package.json with build commands
   - Minification/bundling (optional)

2.4. **Test deployment pipeline**
   - Verify site is accessible at `https://<username>.github.io/ManimOnline`
   - Verify all static assets load correctly

### Deliverables
- [ ] GitHub Actions workflow file created
- [ ] Deployment succeeds on push to main
- [ ] Site accessible via GitHub Pages URL
- [ ] All functionality works on deployed site

---

## Phase 3: Pyodide Integration

### Goal
Integrate Pyodide to enable Python execution in the browser.

### Tasks

3.1. **Add Pyodide to the project**
   - CDN: `https://cdn.jsdelivr.net/pyodide/v0.27.0/full/pyodide.js`
   - Or self-host Pyodide files

3.2. **Create Pyodide web worker**
   - `workers/pyodide-worker.js`
   - Initialize Pyodide in worker context
   - Handle message passing for code execution

3.3. **Implement Python execution pipeline**
   - Send Python code to worker
   - Execute code in Pyodide
   - Return results/errors to main thread

3.4. **Add loading indicator**
   - Pyodide initial load is ~10-15 MB
   - Show progress during initialization
   - Cache Pyodide in browser storage if possible

3.5. **Test basic Python execution**
   - Simple print statements
   - Import standard library modules
   - Error handling and display

### Deliverables
- [ ] Pyodide loads successfully in web worker
- [ ] Python code executes and returns results
- [ ] Loading progress is displayed
- [ ] Errors are captured and displayed to user

---

## Phase 4: Manim Web Worker

### Goal
Create a browser-compatible Manim rendering solution.

### Critical Challenge
Manim has heavy dependencies that are difficult to run in browser:
- **Cairo** - 2D graphics library (rendering backend)
- **Pango** - Text layout/rendering (via ManimPango)
- **FFmpeg** - Video encoding
- **LaTeX** - Mathematical typesetting (optional)

### Decided Approach: Hybrid (Manim-lite with SVG/Canvas backend)

Use Manim's scene graph concepts but replace rendering backend with browser-native SVG/Canvas.

**Rationale:**
- Moderate compatibility with reasonable bundle size
- Leverages browser's native rendering capabilities
- Avoids dependency on unavailable WASM ports (Cairo/Pango)

### MVP Feature Scope (Basic Shapes Only)

| Feature | Included in MVP | Notes |
|---------|-----------------|-------|
| Circle | Yes | Core shape |
| Square | Yes | Core shape |
| Rectangle | Yes | Core shape |
| Line | Yes | Core shape |
| Arrow | Yes | Core shape |
| Triangle | Yes | Core shape |
| Polygon | Yes | Core shape |
| Text | Yes | Browser-native text rendering |
| MathTex | TBD | Requires LaTeX investigation |
| Axes/Graphs | No | Future version |
| 3D Scenes | No | Future version |
| VGroup | Yes | Basic grouping |
| Positioning (shift, move_to) | Yes | Essential |
| Coloring (color, fill_opacity) | Yes | Essential |
| Create animation | Future v1.0 | Not MVP |
| FadeIn/FadeOut | Future v1.0 | Not MVP |
| Transform | Future v1.0 | Not MVP |

### Output Format: Frame-by-Frame

Animations will be rendered as individual frames sent to the main thread:
- Each frame is an SVG or Canvas snapshot
- Main thread handles frame sequencing and playback
- Enables seeking, pausing, and frame-by-frame stepping
- No video encoding required in browser

### Error Handling: Explicit Unsupported Feature Errors

When users try unsupported Manim features:
- Display clear error message listing the unsupported feature
- Provide link to supported features documentation
- Example: "Error: `ThreeDScene` is not supported in ManimOnline. Supported scene types: Scene"

### Tasks

4.1. **Research existing Manim WASM efforts**
   - Check for `manim-wasm` projects
   - Evaluate Pyodide-compatible Manim forks
   - Assess Cairo/Pango WASM status

4.2. **Investigate LaTeX rendering options** (TBD)
   - Option A: MathJax integration
   - Option B: KaTeX integration
   - Option C: Support only Text, defer MathTex
   - Evaluate: rendering quality, bundle size, performance

4.3. **Implement Manim worker (integrated into single worker)**
   - Add Manim rendering to unified worker
   - Load Pyodide with minimal bundle
   - Parse Manim Python code
   - Generate SVG/Canvas output

4.4. **Implement frame-by-frame pipeline**
   - Scene construction from Python AST
   - Frame generation at target FPS
   - Transfer frames to main thread via postMessage
   - Implement frame player in main thread

4.5. **Implement unsupported feature detection**
   - Parse code for unsupported imports/classes
   - Generate helpful error messages
   - Link to documentation

4.6. **Implement hard timeout for long renders**
   - Terminate worker if render exceeds timeout
   - Display timeout error with suggestion to simplify
   - Allow user to retry

### Deliverables
- [ ] Implementation approach documented
- [ ] Manim worker processes valid Manim code
- [ ] Visual output renders in browser
- [ ] Basic Manim shapes work (Circle, Square, Line, Text)
- [ ] Unsupported features show clear errors
- [ ] Hard timeout prevents runaway renders

---

## Phase 5: Content Type Detection

### Goal
Automatically detect whether user input is Graphviz DOT or Manim Python.

### Detection Strategies

#### Strategy 1: Syntax Analysis

**DOT Language Indicators:**
- Keywords: `digraph`, `graph`, `subgraph`, `node`, `edge`
- Operators: `->`, `--`
- Attribute syntax: `[label="...", shape=...]`
- Comment style: `//` or `/* */`

**Manim Python Indicators:**
- `from manim import *`
- `import manim`
- Class definitions inheriting from `Scene`
- Method `construct(self)`
- Manim objects: `Circle`, `Square`, `MathTex`, `Text`, `Axes`
- Animation methods: `play`, `wait`, `FadeIn`, `Transform`

#### Strategy 2: File Extension Hints
- `.dot`, `.gv` → Graphviz
- `.py` → Manim (Python)

#### Strategy 3: User Override
- UI toggle to force interpretation
- URL parameter: `?type=dot` or `?type=manim`

#### Strategy 4: Confidence Scoring

```javascript
function detectContentType(code) {
  let dotScore = 0;
  let manimScore = 0;

  // DOT indicators
  if (/\b(di)?graph\s+\w*\s*\{/.test(code)) dotScore += 10;
  if (/->|--/.test(code)) dotScore += 5;
  if (/\[\s*\w+\s*=/.test(code)) dotScore += 3;

  // Manim indicators
  if (/from\s+manim\s+import/.test(code)) manimScore += 10;
  if (/class\s+\w+\s*\(\s*Scene\s*\)/.test(code)) manimScore += 10;
  if (/def\s+construct\s*\(\s*self\s*\)/.test(code)) manimScore += 8;
  if (/\.(play|wait|add)\s*\(/.test(code)) manimScore += 5;

  if (dotScore > manimScore) return 'graphviz';
  if (manimScore > dotScore) return 'manim';
  return 'unknown';
}
```

### Tasks

5.1. **Implement detection module**
   - `src/detector.js`
   - Multiple detection strategies
   - Confidence scoring system

5.2. **Implement automatic type indicator**
   - Show detected type in UI (no tabs/dropdowns)
   - Small indicator showing "Graphviz" or "Manim"
   - Manual override via URL parameter only (`?type=dot` or `?type=manim`)

5.3. **Handle edge cases**
   - Empty input → Show default sample (Manim)
   - Invalid syntax for both → Attempt render, show error
   - Ambiguous input → Use confidence scoring, show indicator
   - Mixed content → Use highest confidence match

5.4. **Integrate with editor (debounced)**
   - Debounce detection to avoid excessive computation
   - Detection runs after user stops typing
   - Update UI indicator when detection completes
   - Trigger auto-render after detection

### Deliverables
- [ ] Detection module correctly identifies DOT vs Manim
- [ ] UI shows detected type (automatic indicator)
- [ ] Debouncing works correctly
- [ ] Edge cases handled gracefully

---

## Phase 6: Unified Rendering Pipeline

### Goal
Create a seamless experience that routes code to the appropriate renderer.

### Default Content: Sample Manim Scene

When the page loads with no URL parameters, display a sample Manim scene:

```python
from manim import *

class HelloWorld(Scene):
    def construct(self):
        circle = Circle(color=BLUE)
        square = Square(color=RED).shift(RIGHT * 2)
        self.add(circle, square)
```

This showcases Manim capabilities and encourages exploration of the primary new feature.

### Rendering: Automatic with Debounce

- Rendering triggers automatically after debounce period
- No manual "Render" button required for normal use
- Stop/cancel button available for long-running renders
- Hard timeout terminates runaway renders

### Tasks

6.1. **Create unified worker (single worker architecture)**
   - `src/unified-worker.js`
   - Contains both viz.js and Pyodide
   - Routes code based on detection result
   - Lazy-loads Pyodide only when Manim detected

6.2. **Implement service worker for offline support** (Core Requirement)
   - `sw.js` - Service worker file
   - Cache all static assets on first load
   - Cache Pyodide files after first use
   - Enable full offline functionality after initial load
   - Handle cache invalidation on updates

6.3. **Implement output display**
   - Common output area for both renderers
   - SVG display with pan-zoom (for Graphviz and static Manim)
   - Frame player for Manim animations (play/pause/seek)
   - Error display panel with helpful messages

6.4. **Implement automatic rendering**
   - Debounced trigger after typing stops
   - Cancel previous render if new input received
   - Show rendering indicator during processing
   - Display result when complete

6.5. **Implement URL sharing**
   - Encode code in URL (gzip + base64)
   - Support loading from GitHub Gist
   - Support `?url=` parameter for remote files
   - Add `?type=` parameter for explicit type override

6.6. **Add export options**
   - Download SVG
   - Download PNG
   - Download GIF (for Manim animations)
   - Copy embed code

6.7. **Implement examples gallery**
   - Pre-built Graphviz examples
   - Pre-built Manim examples
   - Easy loading into editor
   - Clear indication of which type each example is

### Deliverables
- [ ] Both renderers accessible through unified worker
- [ ] Service worker enables offline use
- [ ] Auto-detection routes to correct renderer
- [ ] Automatic rendering with debounce works
- [ ] URL sharing works for both types
- [ ] Export options available
- [ ] Examples gallery implemented
- [ ] Default Manim sample loads on empty page

---

## Test Plan

### Unit Tests

#### Detection Module Tests

| Test ID | Description | Input | Expected Output |
|---------|-------------|-------|-----------------|
| DET-001 | Empty input | `""` | `unknown` |
| DET-002 | Simple DOT graph | `digraph { a -> b }` | `graphviz` |
| DET-003 | DOT with attributes | `graph { a [label="A"] }` | `graphviz` |
| DET-004 | Simple Manim scene | `from manim import *\nclass Test(Scene):...` | `manim` |
| DET-005 | Manim without import | `class Test(Scene):\n  def construct(self):...` | `manim` |
| DET-006 | Python non-Manim | `print("hello")` | `unknown` |
| DET-007 | DOT-like in Python string | `x = "digraph { a -> b }"` | `manim` (Python context) |
| DET-008 | Comments only (DOT style) | `// This is a comment` | `unknown` |
| DET-009 | Comments only (Python style) | `# This is a comment` | `unknown` |
| DET-010 | Whitespace only | `   \n\t  ` | `unknown` |
| DET-011 | Mixed indicators | `# digraph comment\nclass Scene:...` | Based on confidence |
| DET-012 | URL parameter override | Code + `?type=dot` | `graphviz` (forced) |
| DET-013 | Invalid DOT syntax | `digraph { syntax error` | `graphviz` (detected, render fails) |
| DET-014 | Invalid Manim syntax | `from manim import *\nclass Bad:` | `manim` (detected, render fails) |

#### Graphviz Renderer Tests

| Test ID | Description | Input | Expected Output |
|---------|-------------|-------|-----------------|
| GV-001 | Empty graph | `graph {}` | Empty SVG |
| GV-002 | Single node | `graph { a }` | SVG with one node |
| GV-003 | Directed edge | `digraph { a -> b }` | SVG with arrow |
| GV-004 | Undirected edge | `graph { a -- b }` | SVG with line |
| GV-005 | Node attributes | `graph { a [shape=box] }` | SVG with box shape |
| GV-006 | Edge labels | `digraph { a -> b [label="test"] }` | SVG with label |
| GV-007 | Subgraph | `digraph { subgraph cluster_0 { a; b } }` | SVG with cluster |
| GV-008 | Large graph (100 nodes) | Generated DOT | SVG renders within 5s |
| GV-009 | Unicode labels | `graph { a [label="日本語"] }` | SVG with Unicode text |
| GV-010 | HTML labels | `graph { a [label=<B>bold</B>] }` | SVG with formatted text |
| GV-011 | Syntax error | `digraph { -> }` | Error message displayed |
| GV-012 | Different layouts | `graph { layout=neato; a -- b }` | Different SVG layout |

#### Manim Renderer Tests

| Test ID | Description | Input | Expected Output |
|---------|-------------|-------|-----------------|
| MN-001 | Empty scene | Scene with empty construct | Blank output |
| MN-002 | Single Circle | `Circle()` added to scene | Circle renders |
| MN-003 | Single Square | `Square()` added to scene | Square renders |
| MN-004 | Text object | `Text("Hello")` | Text renders |
| MN-005 | MathTex (if supported) | `MathTex(r"\int_0^1 x dx")` | Math renders |
| MN-006 | Basic animation | `self.play(Create(Circle()))` | Animation plays |
| MN-007 | Transform animation | `self.play(Transform(a, b))` | Transform works |
| MN-008 | Multiple objects | Circle, Square, Triangle | All render |
| MN-009 | Positioning | `Circle().shift(RIGHT)` | Positioned correctly |
| MN-010 | Coloring | `Circle(color=RED)` | Correct color |
| MN-011 | Syntax error in Python | `def construct(self)` (missing colon) | Error displayed |
| MN-012 | Runtime error | `1/0` in construct | Error displayed |
| MN-013 | Import error | `from nonexistent import x` | Error displayed |
| MN-014 | Unsupported feature | Feature requiring FFmpeg | Graceful error |
| MN-015 | Long animation (10s) | Animation with many waits | Renders or timeout |

#### Integration Tests

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| INT-001 | Auto-detect and render DOT | Paste DOT code | Correct detection, SVG output |
| INT-002 | Auto-detect and render Manim | Paste Manim code | Correct detection, animation output |
| INT-003 | Switch between types | Type DOT, clear, type Manim | Both render correctly |
| INT-004 | Manual type override | Set type, paste conflicting code | Forced type used |
| INT-005 | URL loading DOT | Load `?url=<gist-with-dot>` | DOT renders |
| INT-006 | URL loading Manim | Load `?url=<gist-with-py>` | Manim renders |
| INT-007 | Share and reload | Generate share URL, open | Same output |
| INT-008 | Presentation mode DOT | `?presentation` + DOT | Editor hidden |
| INT-009 | Presentation mode Manim | `?presentation` + Manim | Editor hidden |
| INT-010 | Export SVG | Render DOT, export | Valid SVG file |
| INT-011 | Export PNG | Render, export PNG | Valid PNG file |
| INT-012 | Pan and zoom | Render, use pan-zoom | Works smoothly |
| INT-013 | Resize window | Render, resize | Output adjusts |
| INT-014 | Mobile viewport | Load on mobile | Usable UI |

#### Performance Tests

| Test ID | Description | Metric | Target |
|---------|-------------|--------|--------|
| PERF-001 | Initial page load | Time to interactive | < 3s (without Pyodide) |
| PERF-002 | Pyodide initialization | Time to ready | < 15s |
| PERF-003 | Simple DOT render | Render time | < 500ms |
| PERF-004 | Complex DOT (100 nodes) | Render time | < 3s |
| PERF-005 | Simple Manim render | Render time | < 5s |
| PERF-006 | Manim animation (5s) | Render time | < 30s |
| PERF-007 | Memory usage idle | Heap size | < 100MB |
| PERF-008 | Memory usage Pyodide | Heap size | < 500MB |
| PERF-009 | Re-render same content | Render time | < previous render |
| PERF-010 | Typing responsiveness | Input lag | < 50ms |

#### Browser Compatibility Tests

| Test ID | Browser | Version | Expected |
|---------|---------|---------|----------|
| COMPAT-001 | Chrome | Latest | Full support |
| COMPAT-002 | Firefox | Latest | Full support |
| COMPAT-003 | Safari | Latest | Full support (verify WASM) |
| COMPAT-004 | Edge | Latest | Full support |
| COMPAT-005 | Chrome Mobile | Latest | Basic support |
| COMPAT-006 | Safari Mobile | Latest | Basic support |
| COMPAT-007 | Chrome | 2 versions back | Graceful degradation |

#### Security Tests

| Test ID | Description | Input | Expected |
|---------|-------------|-------|----------|
| SEC-001 | XSS in DOT labels | `[label="<script>alert(1)</script>"]` | Script not executed |
| SEC-002 | XSS in Manim text | `Text("<script>alert(1)</script>")` | Script not executed |
| SEC-003 | File system access | Manim code trying `open()` | Blocked/sandboxed |
| SEC-004 | Network access | Manim code trying `requests.get()` | Blocked/sandboxed |
| SEC-005 | Infinite loop | `while True: pass` | Timeout/kill |
| SEC-006 | Memory exhaustion | `[0] * 10**9` | Blocked/error |
| SEC-007 | URL injection | `?url=javascript:alert(1)` | Blocked |

#### Service Worker / Offline Tests

| Test ID | Description | Steps | Expected |
|---------|-------------|-------|----------|
| SW-001 | Service worker registers | Load page first time | SW registered in browser |
| SW-002 | Static assets cached | Load page, check cache | HTML, JS, CSS cached |
| SW-003 | Graphviz works offline | Load, go offline, render DOT | SVG renders |
| SW-004 | Pyodide cached after use | Render Manim, check cache | Pyodide files cached |
| SW-005 | Manim works offline | Load, render Manim, go offline, re-render | Still works |
| SW-006 | Cache invalidation | Deploy update, reload | New version loads |
| SW-007 | First load offline | Clear cache, go offline, load | Appropriate error/fallback |
| SW-008 | Partial cache offline | Only HTML cached, go offline | Graceful degradation |

#### Timeout Tests

| Test ID | Description | Input | Expected |
|---------|-------------|-------|----------|
| TO-001 | Render completes before timeout | Simple scene | Success |
| TO-002 | Render exceeds timeout | `while True: pass` | Timeout error displayed |
| TO-003 | Complex scene near timeout | Many objects | Completes or clear timeout |
| TO-004 | Timeout shows helpful message | Long render | "Render timed out. Try simplifying your scene." |
| TO-005 | Cancel stops render | Click cancel during render | Render stops, no output |

#### Debounce Tests

| Test ID | Description | Steps | Expected |
|---------|-------------|-------|----------|
| DB-001 | Single character no render | Type one char, wait | No render triggered immediately |
| DB-002 | Pause triggers render | Type, pause for debounce period | Render triggers |
| DB-003 | Continuous typing delays | Type continuously | No render until pause |
| DB-004 | Rapid edits single render | Make 10 quick edits | Only one render after pause |
| DB-005 | Detection updates on pause | Type DOT, pause, check indicator | Shows "Graphviz" |

---

## Resolved Decisions

The following questions have been resolved:

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Single or separate workers? | **Single worker** | Simpler communication, unified message handling |
| 2 | Frame-by-frame or video blob? | **Frame-by-frame** | More control, seekable, no video encoding needed |
| 3 | Detection timing? | **Debounced (1 second)** | Better performance, acceptable UI delay |
| 4 | Manim feature scope for MVP? | **Basic shapes only** | Circle, Square, Line, Text, etc. (see Phase 4) |
| 5 | LaTeX rendering? | **Separate investigation** | See [manim_latex_questions.md](./manim_latex_questions.md) |
| 6 | Unsupported feature handling? | **Show error listing feature** | Clear feedback helps users understand limitations |
| 7 | Default content? | **Sample Manim scene** | Showcases primary new feature |
| 8 | Type indicator UI? | **Automatic indicator only** | No tabs/dropdowns, just show detected type |
| 9 | Rendering trigger? | **Automatic** | Better UX for quick iteration |
| 10 | Pyodide bundle size? | **Minimal (~10-15MB)** | numpy - see [manim_numpy_questions.md](./manim_numpy_questions.md) |
| 11 | Offline support? | **Yes - core requirement** | Service workers required |
| 12 | Long render handling? | **Hard timeout (90 seconds)** | Balance between complex scenes and runaway prevention |
| 13 | Backend needed? | **No - pure static site** | Simpler deployment |
| 14 | Custom packages? | **Not now, maybe later** | Keep initial scope minimal |
| 15 | First load offline behavior? | **Show error message** | "Please connect to internet for first load" |
| 16 | Presentation mode for Manim? | **Not now, maybe later** | Keep initial scope minimal |

---

## Open Questions

**All architectural questions have been resolved.** Two items require separate investigation:

### Separate Investigation Files

| Topic | File | Status |
|-------|------|--------|
| numpy dependency for basic shapes | [manim_numpy_questions.md](./manim_numpy_questions.md) | To be investigated |
| LaTeX rendering approach | [manim_latex_questions.md](./manim_latex_questions.md) | To be investigated |

These investigations should be completed before Phase 4 implementation begins.

---

## Technical Risks

### High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cairo/Pango not available in WASM | Cannot run full Manim | Implement Manim-lite with SVG backend |
| Pyodide bundle too large (>100MB) | Poor user experience | Lazy load, use minimal bundle |
| Manim render too slow (>60s) | Unusable for complex scenes | Set timeouts, show progress |
| Browser memory exhaustion | Crash | Implement memory limits in worker |

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Detection accuracy insufficient | Wrong renderer used | Provide manual override |
| Safari WASM issues | Reduced browser support | Test early, document limitations |
| GitHub Pages bandwidth limits | Site throttled | Monitor usage, consider CDN |
| Web worker message overhead | Slow rendering | Batch messages, use transferables |

### Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| ACE editor maintenance | Editor issues | Fork or use alternative (Monaco) |
| viz.js updates | Missing Graphviz features | Pin version, update periodically |
| URL encoding limits | Long code can't be shared | Use Gist for large code |

---

## Dependencies Map

### External Dependencies

| Dependency | Version | Purpose | Size | License |
|------------|---------|---------|------|---------|
| viz.js | Latest | Graphviz rendering | ~2.5MB | MIT |
| ace-editor | Latest | Code editing | ~500KB | BSD-2 |
| svg-pan-zoom | Latest | SVG interaction | ~50KB | MIT |
| Pyodide | 0.27.x | Python runtime | ~10MB (core) | MPL-2.0 |

### Manim Dependencies (to evaluate)

| Dependency | Required For | WASM Status | Decision |
|------------|--------------|-------------|----------|
| numpy | Array operations | Available in Pyodide | **TBD** - investigate if basic shapes need it |
| scipy | Some animations | Available in Pyodide | Not for MVP |
| Pillow | Image handling | Available in Pyodide | Not for MVP |
| cairo | Rendering | Not available | Replace with SVG/Canvas |
| pango | Text rendering | Not available | Replace with browser text |
| ffmpeg | Video encoding | Experimental WASM | Not needed (frame-by-frame) |
| LaTeX | Math typesetting | Not available | **TBD** - KaTeX vs MathJax vs defer |

### LaTeX Rendering Options (To Be Investigated)

| Option | Bundle Size | LaTeX Coverage | Performance | Notes |
|--------|-------------|----------------|-------------|-------|
| MathJax 3 | ~1MB | Excellent | Slower | Full LaTeX, async rendering |
| KaTeX | ~300KB | Good | Fast | Limited macros, sync rendering |
| Defer | 0 | N/A | N/A | MVP has Text only, no MathTex |

---

## Success Criteria

### Minimum Viable Product (MVP)

- [ ] GraphvizOnline functionality fully preserved
- [ ] Basic Manim shapes render (Circle, Square, Line, Text)
- [ ] Auto-detection works for clear cases
- [ ] Manual type override available
- [ ] Deployed to GitHub Pages
- [ ] URL sharing works

### Version 1.0

- [ ] All MVP features
- [ ] Basic Manim animations play (Create, FadeIn, FadeOut)
- [ ] MathTex renders (via KaTeX)
- [ ] Examples gallery available
- [ ] Export to SVG/PNG
- [ ] Mobile-friendly UI

### Future Versions

- [ ] More Manim animation types
- [ ] 3D scene support
- [ ] Collaborative editing
- [ ] Save to account
- [ ] Custom package imports

---

## Timeline-Free Milestones

1. **Milestone: GraphvizOnline Parity** - All original functionality works
2. **Milestone: Deployment Ready** - CI/CD pipeline working
3. **Milestone: Python in Browser** - Pyodide executes Python successfully
4. **Milestone: First Manim Render** - Any Manim code produces output
5. **Milestone: Detection Working** - Auto-switching between renderers
6. **Milestone: MVP Complete** - Basic dual-renderer site functional
7. **Milestone: v1.0 Release** - Polished, documented, ready for users

---

## Next Steps

1. Resolve open questions through research and prototyping
2. Create proof-of-concept for Manim-in-browser
3. Define exact Manim feature subset for MVP
4. Begin Phase 1 implementation

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-01-18 | Initial draft |
| 0.2 | 2026-01-18 | Resolved 14 architectural decisions; added service worker, timeout, and debounce tests; refined open questions to 6 followup items |
| 0.3 | 2026-01-18 | Resolved all remaining questions: timeout=90s, debounce=1s, offline first-load=error, presentation mode=deferred; created separate investigation files for numpy and LaTeX |
