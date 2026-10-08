/** Supported, local examples and a loader that ignores superseded requests. */
const ExampleCatalog = Object.freeze([
  { id: 'minimal', label: 'First animation', path: 'examples/minimal_scene.py' },
  { id: 'math', label: 'Math formulas', path: 'examples/math_scene.py' },
  { id: 'scenes', label: 'Multiple scenes', path: 'examples/multiple_scenes.py' },
  { id: 'creation', label: 'Creation and rotation', path: 'examples/creation_and_rotation.py' },
  { id: 'layout', label: 'Position and arrange', path: 'examples/layout_scene.py' },
  { id: 'stagger', label: 'Staggered animations', path: 'examples/staggered_scene.py' },
  { id: 'succession', label: 'Animate in sequence', path: 'examples/succession_scene.py' },
  { id: 'annulus', label: 'Rings with separate contours', path: 'examples/annulus_scene.py' },
  { id: 'subpaths', label: 'Morph separate contours', path: 'examples/subpath_scene.py' },
  { id: 'points', label: 'Edit cubic point arrays', path: 'examples/point_array_scene.py' },
  { id: 'partial', label: 'Extract and wrap curve highlights', path: 'examples/partial_curve_scene.py' },
  { id: 'flash', label: 'Traveling outline highlights', path: 'examples/passing_flash_scene.py' },
  { id: 'numberline', label: 'Follow numeric coordinates', path: 'examples/number_line_scene.py' },
  { id: 'axes', label: 'Animate Cartesian coordinates', path: 'examples/axes_scene.py' },
  { id: 'curvedarrows', label: 'Animate tangent-aligned curved arrows', path: 'examples/curved_arrow_scene.py' },
  { id: 'doublearrow', label: 'Animate two-ended arrows', path: 'examples/double_arrow_scene.py' },
  { id: 'roundsquaretips', label: 'Render circular and square arrow tips', path: 'examples/round_square_tips_scene.py' },
  { id: 'arrowtips', label: 'Manage arrow tips and shafts', path: 'examples/arrow_tips_scene.py' },
  { id: 'tipgeometry', label: 'Edit arrow tip outlines', path: 'examples/tip_geometry_scene.py' },
  { id: 'shapelayout', label: 'Arrange children on a shape', path: 'examples/shape_layout_scene.py' },
  { id: 'gridlayout', label: 'Reflow a transformed grid', path: 'examples/grid_layout_scene.py' },
  { id: 'transformedlayout', label: 'Arrange rotated and scaled groups', path: 'examples/transformed_layout_scene.py' },
  { id: 'groupmotion', label: 'Move children inside nested groups', path: 'examples/group_motion_scene.py' },
  { id: 'childmotion', label: 'Move children inside transformed shapes', path: 'examples/child_motion_scene.py' },
  { id: 'familybounds', label: 'Frame shapes and distant children', path: 'examples/family_bounds_scene.py' },
  { id: 'shapefamilies', label: 'Attach and restore children on shapes', path: 'examples/shape_family_scene.py' },
  { id: 'anglepaths', label: 'Follow and restore an editable angle path', path: 'examples/angle_path_scene.py' },
  { id: 'arcpolygons', label: 'Morph polygons with curved edges', path: 'examples/arc_polygon_scene.py' },
  { id: 'endpointarcs', label: 'Bend arcs between moving endpoints', path: 'examples/endpoint_arc_scene.py' },
  { id: 'angles', label: 'Mark angles between moving lines', path: 'examples/angle_scene.py' },
  { id: 'tangents', label: 'Follow tangents along curved paths', path: 'examples/tangent_paths_scene.py' },
  { id: 'dashedpaths', label: 'Dash curved paths and shift their phase', path: 'examples/dashed_paths_scene.py' },
  { id: 'guides', label: 'Follow dashed coordinate guides', path: 'examples/guides_scene.py' },
  { id: 'area', label: 'Fill changing graph regions', path: 'examples/area_scene.py' },
  { id: 'secant', label: 'Follow a labeled secant', path: 'examples/secant_scene.py' },
  { id: 'riemann', label: 'Refine signed area estimates', path: 'examples/riemann_scene.py' },
  { id: 'calculus', label: 'Follow a tangent and derivative', path: 'examples/calculus_scene.py' },
  { id: 'complex', label: 'Animate complex coordinates', path: 'examples/complex_scene.py' },
  { id: 'plane', label: 'Move a Cartesian grid', path: 'examples/plane_scene.py' },
  { id: 'plot', label: 'Plot smooth functions', path: 'examples/plot_scene.py' },
  { id: 'rounded', label: 'Rounded and concave corners', path: 'examples/rounded_rectangle_scene.py' },
  { id: 'sectors', label: 'Circular and ring sectors', path: 'examples/sector_scene.py' },
  { id: 'ellipse', label: 'Follow an ellipse', path: 'examples/ellipse_scene.py' },
  { id: 'trace', label: 'Trace moving points', path: 'examples/trace_scene.py' },
  { id: 'numbers', label: 'Show changing numbers', path: 'examples/numeric_scene.py' },
  { id: 'redraw', label: 'Rebuild shapes each frame', path: 'examples/redraw_scene.py' },
  { id: 'tracker', label: 'Animate a shared value', path: 'examples/value_tracker_scene.py' },
  { id: 'updaters', label: 'Follow objects each frame', path: 'examples/updater_scene.py' },
  { id: 'autozoom', label: 'Fit shapes in the view', path: 'examples/auto_zoom_scene.py' },
  { id: 'movingcamera', label: 'Pan and zoom the view', path: 'examples/moving_camera_scene.py' },
  { id: 'camera', label: 'Configure the canvas', path: 'examples/camera_scene.py' },
  { id: 'family', label: 'Build and edit a group', path: 'examples/group_family_scene.py' },
  { id: 'groupmorph', label: 'Morph nested groups', path: 'examples/group_morph_scene.py' },
  { id: 'shapemorph', label: 'Morph built-in shapes', path: 'examples/shape_morph_scene.py' },
  { id: 'morph', label: 'Morph aligned paths', path: 'examples/morph_scene.py' },
  { id: 'bezier', label: 'Cubic Bezier paths', path: 'examples/bezier_scene.py' },
  { id: 'corners', label: 'Connected corner paths', path: 'examples/corner_path_scene.py' },
  { id: 'path', label: 'Follow a path', path: 'examples/path_scene.py' },
  { id: 'arc', label: 'Circular arcs', path: 'examples/arc_scene.py' },
  { id: 'growth', label: 'Grow and shrink', path: 'examples/growth_scene.py' },
  { id: 'lifecycle', label: 'Scene setup and time', path: 'examples/lifecycle_scene.py' },
  { id: 'foreground', label: 'Keep an overlay in front', path: 'examples/foreground_scene.py' },
  { id: 'order', label: 'Reorder and clear a scene', path: 'examples/order_scene.py' },
  { id: 'layers', label: 'Layer overlapping shapes', path: 'examples/layer_scene.py' },
  { id: 'style', label: 'Fill and outline styles', path: 'examples/style_scene.py' },
  { id: 'restore', label: 'Save and restore', path: 'examples/restore_scene.py' },
  { id: 'indicate', label: 'Highlight objects', path: 'examples/indicate_scene.py' },
  { id: 'copy', label: 'Transform a copy', path: 'examples/copy_scene.py' },
  { id: 'connector', label: 'Move connector endpoints', path: 'examples/connector_scene.py' },
  { id: 'dot', label: 'Graphviz diagram', path: 'examples/basic_graph.dot' }
].map(example => Object.freeze(example)));

class ExampleLoader {
  constructor({ fetchSource = url => fetch(url), onLoad, onStatus = () => {}, onError = () => {} }) {
    this.fetchSource = fetchSource;
    this.onLoad = onLoad;
    this.onStatus = onStatus;
    this.onError = onError;
    this.revision = 0;
  }

  cancel() {
    this.revision++;
    this.onStatus('', false);
  }

  async load(id) {
    const revision = ++this.revision;
    const example = ExampleCatalog.find(item => item.id === id);
    try {
      if (!example) throw new Error('Choose an example to load.');
      this.onStatus('Loading example…', true);
      const response = await this.fetchSource(example.path);
      if (revision !== this.revision) return false;
      if (!response.ok) throw new Error('Could not load the example. Try again.');
      const source = await response.text();
      if (revision !== this.revision) return false;
      this.onStatus('', false);
      this.onLoad(source, example);
      return true;
    } catch (error) {
      if (revision === this.revision) {
        this.onStatus('', false);
        this.onError(error);
      }
      return false;
    }
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ExampleCatalog, ExampleLoader };
} else {
  window.ExampleCatalog = ExampleCatalog;
  window.ExampleLoader = ExampleLoader;
}
