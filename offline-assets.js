/** Exact offline dependencies. Bump VERSION whenever any listed local file changes. */
const OfflineAssets = {
  VERSION: 'manimonline-offline-v79',
  local: [
    'examples/stretch_scene.py',
    'examples/surround_scene.py',
    'examples/circle_construction_scene.py',
    'examples/generic_tips_scene.py',
    'examples/tip_style_scene.py',
    'examples/curved_arrow_scene.py',
    'examples/double_arrow_scene.py',
    'examples/round_square_tips_scene.py',
    'examples/arrow_tips_scene.py',
    'examples/tip_geometry_scene.py',
    'examples/shape_layout_scene.py',
    'examples/grid_layout_scene.py',
    'examples/transformed_layout_scene.py',
    'examples/group_motion_scene.py',
    'examples/child_motion_scene.py',
    'examples/family_bounds_scene.py',
    'examples/shape_family_scene.py',
    'examples/angle_path_scene.py',
    'examples/arc_polygon_scene.py',
    'examples/endpoint_arc_scene.py',
    'examples/angle_scene.py',
    'examples/tangent_paths_scene.py',
    'examples/dashed_paths_scene.py',
    'examples/guides_scene.py',
    'examples/area_scene.py',
    'examples/secant_scene.py',
    'examples/riemann_scene.py',
    'examples/calculus_scene.py',
    'examples/complex_scene.py',
    'examples/plane_scene.py',
    'examples/plot_scene.py',
    'examples/axes_scene.py',
    'examples/number_line_scene.py',
    'examples/passing_flash_scene.py',
    'examples/partial_curve_scene.py',
    'examples/point_array_scene.py',
    'examples/subpath_scene.py',
    'examples/rounded_rectangle_scene.py',
    'index.html', 'ace/ace.js', 'ace/theme-twilight.js', 'ace/mode-python.js', 'ace/mode-dot.js',
    'viz-global.js', 'svg-pan-zoom.min.js', 'src/detector.js', 'src/render-scheduler.js', 'src/unified-worker.js',
    'src/manim-lite.py', 'src/manim-client.js', 'src/manim-renderer.js', 'src/manim-player.js',
    'src/manim-math.js', 'src/manim-export.js', 'src/examples.js', 'src/offline.js', 'src/share-links.js',
    'examples/minimal_scene.py', 'examples/math_scene.py', 'examples/multiple_scenes.py',
    'examples/creation_and_rotation.py', 'examples/layout_scene.py', 'examples/staggered_scene.py',
    'examples/succession_scene.py', 'examples/auto_zoom_scene.py', 'examples/updater_scene.py', 'examples/value_tracker_scene.py', 'examples/redraw_scene.py', 'examples/numeric_scene.py', 'examples/trace_scene.py', 'examples/ellipse_scene.py', 'examples/sector_scene.py', 'examples/annulus_scene.py',
    'examples/moving_camera_scene.py', 'examples/camera_scene.py', 'examples/group_family_scene.py', 'examples/group_morph_scene.py', 'examples/shape_morph_scene.py', 'examples/morph_scene.py', 'examples/bezier_scene.py', 'examples/corner_path_scene.py', 'examples/path_scene.py', 'examples/arc_scene.py', 'examples/growth_scene.py',
    'examples/foreground_scene.py', 'examples/lifecycle_scene.py', 'examples/order_scene.py', 'examples/layer_scene.py', 'examples/style_scene.py', 'examples/restore_scene.py', 'examples/indicate_scene.py',
    'examples/copy_scene.py', 'examples/connector_scene.py', 'examples/basic_graph.dot'
  ],
  remote: [
    'https://cdnjs.cloudflare.com/ajax/libs/lz-string/1.5.0/lz-string.min.js',
    'https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg.js',
    ...['pyodide.js', 'pyodide.asm.js', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json']
      .map(file => 'https://cdn.jsdelivr.net/pyodide/v0.27.0/full/' + file)
  ],
  urls(scope) { return [...this.local.map(path => new URL(path, scope).href), ...this.remote]; },
  key(request, scope) {
    if (request.method !== 'GET') return null;
    const url = new URL(request.url);
    const base = new URL(scope);
    if (url.origin === base.origin && (url.pathname === base.pathname || url.pathname === base.pathname + 'index.html')) {
      if (request.mode === 'navigate') return new URL('index.html', scope).href;
    }
    // Local script version queries do not create additional cache entries.
    if (url.origin === base.origin) url.search = '';
    url.hash = '';
    return this.urls(scope).includes(url.href) ? url.href : null;
  }
};
if (typeof module !== 'undefined') module.exports = OfflineAssets;
else globalThis.OfflineAssets = OfflineAssets;
