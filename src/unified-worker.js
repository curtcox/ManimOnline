/**
 * Unified Web Worker for ManimOnline
 * Handles both Graphviz rendering and Pyodide/Manim execution
 */

let pyodide = null;
let pyodideLoading = false;
let pyodideReady = false;

// Message handler
self.onmessage = async function(event) {
  const { type, id, code, options } = event.data;

  try {
    switch (type) {
      case 'render-graphviz':
        // Graphviz is handled in main thread currently
        // This is a placeholder for potential future worker-based rendering
        self.postMessage({
          id,
          type: 'error',
          error: 'Graphviz rendering should be done in main thread'
        });
        break;

      case 'init-pyodide':
        await initPyodide();
        self.postMessage({ id, type: 'pyodide-ready' });
        break;

      case 'run-python':
        if (!pyodideReady) {
          await initPyodide();
        }
        const result = await runPython(code);
        self.postMessage({ id, type: 'python-result', result });
        break;

      case 'render-manim':
        if (!pyodideReady) {
          await initPyodide();
        }
        const frames = await renderManim(code, options);
        self.postMessage({ id, type: 'manim-result', frames });
        break;

      case 'check-pyodide-status':
        self.postMessage({
          id,
          type: 'pyodide-status',
          ready: pyodideReady,
          loading: pyodideLoading
        });
        break;

      default:
        self.postMessage({ id, type: 'error', error: `Unknown message type: ${type}` });
    }
  } catch (error) {
    self.postMessage({
      id,
      type: 'error',
      error: error.message || String(error)
    });
  }
};

/**
 * Initialize Pyodide
 */
async function initPyodide() {
  if (pyodideReady) return;
  if (pyodideLoading) {
    // Wait for loading to complete
    while (pyodideLoading) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    return;
  }

  pyodideLoading = true;
  self.postMessage({ type: 'pyodide-loading', progress: 0 });

  try {
    // Import Pyodide
    importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.0/full/pyodide.js');

    self.postMessage({ type: 'pyodide-loading', progress: 10 });

    // Load Pyodide
    pyodide = await loadPyodide({
      indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.27.0/full/',
      stdout: (text) => {
        self.postMessage({ type: 'python-stdout', text });
      },
      stderr: (text) => {
        self.postMessage({ type: 'python-stderr', text });
      }
    });

    self.postMessage({ type: 'pyodide-loading', progress: 80 });

    // Install manim-lite (our custom implementation will be injected)
    await pyodide.runPythonAsync(`
import sys
import json

# Create a minimal manim-lite module
class ManimLite:
    """Minimal Manim implementation for browser rendering"""

    # Colors
    BLUE = "#58C4DD"
    RED = "#FC6255"
    GREEN = "#83C167"
    YELLOW = "#FFFF00"
    PURPLE = "#9A72AC"
    ORANGE = "#FF8C00"
    WHITE = "#FFFFFF"
    BLACK = "#000000"
    GRAY = "#888888"
    GREY = "#888888"
    PINK = "#FF69B4"

    # Directions
    UP = (0, 1, 0)
    DOWN = (0, -1, 0)
    LEFT = (-1, 0, 0)
    RIGHT = (1, 0, 0)
    ORIGIN = (0, 0, 0)

    class Mobject:
        """Base class for all mathematical objects"""
        def __init__(self):
            self.position = [0, 0, 0]
            self.color = ManimLite.WHITE
            self.fill_opacity = 1.0
            self.stroke_width = 2
            self.children = []
            self._type = "mobject"

        def shift(self, direction):
            if isinstance(direction, tuple):
                direction = list(direction)
            self.position = [
                self.position[0] + direction[0],
                self.position[1] + direction[1],
                self.position[2] + (direction[2] if len(direction) > 2 else 0)
            ]
            return self

        def move_to(self, point):
            if isinstance(point, tuple):
                point = list(point)
            self.position = point[:3] if len(point) >= 3 else point + [0] * (3 - len(point))
            return self

        def set_color(self, color):
            self.color = color
            return self

        def set_fill(self, color=None, opacity=None):
            if color is not None:
                self.color = color
            if opacity is not None:
                self.fill_opacity = opacity
            return self

        def to_dict(self):
            return {
                "type": self._type,
                "position": self.position,
                "color": self.color,
                "fill_opacity": self.fill_opacity,
                "stroke_width": self.stroke_width,
                "children": [c.to_dict() for c in self.children]
            }

    class Circle(Mobject):
        def __init__(self, radius=1, color=None, **kwargs):
            super().__init__()
            self._type = "circle"
            self.radius = radius
            if color:
                self.color = color

        def to_dict(self):
            d = super().to_dict()
            d["radius"] = self.radius
            return d

    class Square(Mobject):
        def __init__(self, side_length=2, color=None, **kwargs):
            super().__init__()
            self._type = "square"
            self.side_length = side_length
            if color:
                self.color = color

        def to_dict(self):
            d = super().to_dict()
            d["side_length"] = self.side_length
            return d

    class Rectangle(Mobject):
        def __init__(self, width=4, height=2, color=None, **kwargs):
            super().__init__()
            self._type = "rectangle"
            self.width = width
            self.height = height
            if color:
                self.color = color

        def to_dict(self):
            d = super().to_dict()
            d["width"] = self.width
            d["height"] = self.height
            return d

    class Line(Mobject):
        def __init__(self, start=None, end=None, color=None, **kwargs):
            super().__init__()
            self._type = "line"
            self.start = list(start) if start else [-1, 0, 0]
            self.end = list(end) if end else [1, 0, 0]
            if color:
                self.color = color

        def to_dict(self):
            d = super().to_dict()
            d["start"] = self.start
            d["end"] = self.end
            return d

    class Arrow(Line):
        def __init__(self, start=None, end=None, color=None, **kwargs):
            super().__init__(start, end, color, **kwargs)
            self._type = "arrow"

    class Triangle(Mobject):
        def __init__(self, color=None, **kwargs):
            super().__init__()
            self._type = "triangle"
            if color:
                self.color = color

    class Polygon(Mobject):
        def __init__(self, *vertices, color=None, **kwargs):
            super().__init__()
            self._type = "polygon"
            self.vertices = [list(v) if isinstance(v, tuple) else v for v in vertices]
            if color:
                self.color = color

        def to_dict(self):
            d = super().to_dict()
            d["vertices"] = self.vertices
            return d

    class Text(Mobject):
        def __init__(self, text, color=None, font_size=48, **kwargs):
            super().__init__()
            self._type = "text"
            self.text = text
            self.font_size = font_size
            if color:
                self.color = color

        def to_dict(self):
            d = super().to_dict()
            d["text"] = self.text
            d["font_size"] = self.font_size
            return d

    class VGroup(Mobject):
        def __init__(self, *mobjects, **kwargs):
            super().__init__()
            self._type = "vgroup"
            self.children = list(mobjects)

        def add(self, *mobjects):
            self.children.extend(mobjects)
            return self

    class Scene:
        """Base class for Manim scenes"""
        def __init__(self):
            self.mobjects = []
            self._frames = []
            self._current_frame = 0

        def add(self, *mobjects):
            self.mobjects.extend(mobjects)

        def remove(self, *mobjects):
            for m in mobjects:
                if m in self.mobjects:
                    self.mobjects.remove(m)

        def play(self, *animations, **kwargs):
            # For MVP, animations are not yet implemented
            # Just capture the current state
            pass

        def wait(self, duration=1):
            # For MVP, wait just captures current state
            pass

        def construct(self):
            # To be overridden by user
            pass

        def render(self):
            self.construct()
            return {
                "mobjects": [m.to_dict() for m in self.mobjects]
            }

# Create module
sys.modules['manim'] = ManimLite
sys.modules['manim_lite'] = ManimLite

# Create convenient imports
Circle = ManimLite.Circle
Square = ManimLite.Square
Rectangle = ManimLite.Rectangle
Line = ManimLite.Line
Arrow = ManimLite.Arrow
Triangle = ManimLite.Triangle
Polygon = ManimLite.Polygon
Text = ManimLite.Text
VGroup = ManimLite.VGroup
Scene = ManimLite.Scene
Mobject = ManimLite.Mobject

# Colors
BLUE = ManimLite.BLUE
RED = ManimLite.RED
GREEN = ManimLite.GREEN
YELLOW = ManimLite.YELLOW
PURPLE = ManimLite.PURPLE
ORANGE = ManimLite.ORANGE
WHITE = ManimLite.WHITE
BLACK = ManimLite.BLACK
GRAY = ManimLite.GRAY
GREY = ManimLite.GREY
PINK = ManimLite.PINK

# Directions
UP = ManimLite.UP
DOWN = ManimLite.DOWN
LEFT = ManimLite.LEFT
RIGHT = ManimLite.RIGHT
ORIGIN = ManimLite.ORIGIN

print("Manim-lite initialized successfully")
`);

    self.postMessage({ type: 'pyodide-loading', progress: 100 });
    pyodideReady = true;
  } catch (error) {
    pyodideLoading = false;
    throw error;
  } finally {
    pyodideLoading = false;
  }
}

/**
 * Run Python code and return the result
 */
async function runPython(code) {
  if (!pyodide) {
    throw new Error('Pyodide not initialized');
  }

  // Run the code
  const result = await pyodide.runPythonAsync(code);
  return result;
}

/**
 * Render Manim code and return frames
 */
async function renderManim(code, options = {}) {
  if (!pyodide) {
    throw new Error('Pyodide not initialized');
  }

  const timeout = options.timeout || 90000; // 90 second default timeout

  // Wrap in timeout
  const timeoutPromise = new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Render timed out after 90 seconds. Try simplifying your scene.')), timeout);
  });

  const renderPromise = (async () => {
    // Execute the user's code
    await pyodide.runPythonAsync(code);

    // Find and render the Scene class
    const result = await pyodide.runPythonAsync(`
import json

# Find all Scene subclasses defined in the code
scene_classes = [cls for cls in dir() if isinstance(eval(cls), type) and issubclass(eval(cls), Scene) and cls != 'Scene']

if not scene_classes:
    raise ValueError("No Scene class found in the code. Define a class that inherits from Scene.")

# Use the first (or only) Scene class
scene_class = eval(scene_classes[0])
scene_instance = scene_class()
result = scene_instance.render()
json.dumps(result)
`);

    return JSON.parse(result);
  })();

  return Promise.race([renderPromise, timeoutPromise]);
}

// Signal that worker is ready
self.postMessage({ type: 'worker-ready' });
