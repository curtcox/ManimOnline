"""Community API surface: class tree, Mobject/VMobject utilities and default styles.

Expected values were measured with Manim Community 0.22."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manim_lite_api', ROOT / 'src/manim-lite.py')
lite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lite)

try:
    import numpy  # noqa: F401  (the browser loads NumPy only for sources that use it)
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def scene_values(body):
    """Run body as scene code (so mobject calls see world coordinates); return `result`."""
    lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
    namespace = {}
    exec(compile('from manim import *\n' + body, '<test>', 'exec'), namespace)
    return plain(namespace['result'])


def plain(value):
    if hasattr(value, 'tolist'):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), 4) + 0.0
    return value


class CommunityTreeTests(unittest.TestCase):
    def test_isinstance_follows_community_classes(self):
        result = scene_values(
            'result = [isinstance(VGroup(), VMobject), isinstance(Text("a"), VMobject),\n'
            '          isinstance(MathTex("x"), VMobject), isinstance(Axes(), VMobject),\n'
            '          isinstance(Group(), VMobject), issubclass(VGroup, VMobject),\n'
            '          isinstance(AnimationGroup(FadeIn(Square())), Animation),\n'
            '          isinstance(FadeIn(Square()), Transform), isinstance(Write(Text("a")), Transform),\n'
            '          isinstance(Square(), Circle), type(Vector([1, 0])).__name__]\n')
        self.assertEqual(result, [True, True, True, True, False, True, True, True, False, False, 'Vector'])

    def test_library_checks_use_real_inheritance(self):
        with self.assertRaises(TypeError):
            lite.VMobject().align_points(lite.VGroup())
        self.assertTrue(lite._is_a(lite.Circle(), lite.VMobject))
        self.assertFalse(lite._is_a(lite.VGroup(), lite.VMobject))

    def test_animation_overrides_registry(self):
        result = scene_values(
            'class Marker(Square):\n'
            '    @override_animation(FadeIn)\n'
            '    def _fade(self, **kwargs):\n'
            '        return Create(self, **kwargs)\n'
            'class Plain(Square):\n'
            '    pass\n'
            'Plain.add_animation_override(Write, lambda mob, **kw: FadeIn(mob, **kw))\n'
            'result = [type(FadeIn(Marker())).__name__, type(Write(Plain())).__name__,\n'
            '          Marker.animation_override_for(FadeIn) is not None, Square.animation_override_for(FadeIn)]\n')
        self.assertEqual(result, ['Create', 'FadeIn', True, None])


class MobjectUtilityTests(unittest.TestCase):
    def test_curve_queries(self):
        result = scene_values(
            'c = Circle()\n'
            'result = [c.get_last_point(), [list(x[0]) for x in c.get_anchors_and_handles()],\n'
            '          c.get_nth_curve_points(1), c.get_nth_curve_length(2), c.get_nth_curve_function(0)(0.3)]\n')
        self.assertEqual(result, [
            [1.0, 0.0, 0.0], [[1.0, 0.0, 0.0], [1.0, 0.2652, 0.0], [0.8946, 0.5196, 0.0], [0.7071, 0.7071, 0.0]],
            [[0.7071, 0.7071, 0.0], [0.5196, 0.8946, 0.0], [0.2652, 1.0, 0.0], [0.0, 1.0, 0.0]],
            0.7852, [0.9722, 0.2343, 0.0]])

    def test_path_builders(self):
        result = scene_values(
            'v = VMobject(); v.set_points_as_corners([LEFT, UP, RIGHT]); v.add_smooth_curve_to(DOWN)\n'
            'v.add_quadratic_bezier_curve_to(2*DOWN, 2*LEFT)\n'
            'w = VMobject(); w.start_new_path(ORIGIN); w.add_smooth_curve_to(UP, RIGHT)\n'
            'w.add_cubic_bezier_curve(RIGHT, 2*RIGHT, 2*RIGHT+UP, 3*RIGHT)\n'
            'result = [v.points[8:], w.points]\n')
        self.assertEqual(result[0], [[1.0, 0.0, 0.0], [1.3333, -0.3333, 0.0], [0.3333, -1.3333, 0.0],
                                     [0.0, -1.0, 0.0], [0.0, -1.0, 0.0], [0.0, -1.6667, 0.0],
                                     [-0.6667, -1.3333, 0.0], [-2.0, 0.0, 0.0]])
        self.assertEqual(len(result[1]), 8)
        self.assertEqual(result[1][4:], [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [2.0, 1.0, 0.0], [3.0, 0.0, 0.0]])

    def test_point_edits(self):
        result = scene_values(
            's = Square(); s.scale_handle_to_anchor_distances(2)\n'
            't = Square(); t.put_start_and_end_on(ORIGIN, 2*UP)\n'
            'c = Circle(); c.reverse_points()\n'
            'r = Square(); r.repeat(2)\n'
            'result = [s.points[:4], t.get_start(), t.get_center(), c.points[:2], len(r.points)]\n')
        self.assertEqual(result[0], [[1.0, 1.0, 0.0], [-0.3333, 1.0, 0.0], [0.3333, 1.0, 0.0], [-1.0, 1.0, 0.0]])
        self.assertEqual(result[1], [0.0, 0.0, 0.0])
        self.assertEqual(result[3], [[1.0, 0.0, 0.0], [1.0, -0.2652, 0.0]])
        self.assertEqual(result[4], 32)

    def test_family_queries_and_alignment(self):
        result = scene_values(
            'g = VGroup(Circle(), Square().shift(2*RIGHT))\n'
            'a = Circle(); b = Square(); a.align_data(b)\n'
            'p = VGroup(Circle(), Circle()); q = VGroup(Square()); p.align_submobjects(q)\n'
            'd = Dot(); h = VGroup(Square(), Circle()); h.insert(1, d)\n'
            'result = [len(g.get_all_points()), g.reduce_across_dimension(max, 0),\n'
            '          g.get_extremum_along_dim(dim=1, key=1), len(g.nonempty_submobjects()),\n'
            '          len(a.points), len(b.points), len(q), q[1].get_fill_opacity(),\n'
            '          [type(m).__name__ for m in h]]\n')
        self.assertEqual(result, [48, 3.0, 1.0, 2, 32, 32, 2, 0.0, ['Square', 'Dot', 'Circle']])

    def test_proportions_and_fitting(self):
        result = scene_values(
            's = Square(); s.surround(Circle(radius=2))\n'
            'g = VGroup(Dot(), Dot(RIGHT)); g.space_out_submobjects(2)\n'
            'result = [Line(LEFT, RIGHT).proportion_from_point(ORIGIN), Circle().proportion_from_point(UP),\n'
            '          s.width, [m.get_center() for m in g]]\n')
        self.assertEqual(result, [0.5, 0.25, 4.25, [[-0.5, 0.0, 0.0], [1.5, 0.0, 0.0]]])

    def test_styles(self):
        result = scene_values(
            'c = Circle(fill_opacity=0.5, color=RED)\n'
            's = Square(); s.set_style(**c.get_style())\n'
            'result = [c.get_fill_rgbas(), c.get_stroke_opacities(), c.get_fill_colors()[0],\n'
            '          s.get_stroke_color(), s.get_fill_opacity(), c.get_style(simple=True)["stroke_width"]]\n')
        self.assertEqual(result, [[[0.9882, 0.3843, 0.3333, 0.5]], [1.0], '#FC6255', '#FC6255', 0.5, 4])

    def test_default_stroke_widths(self):
        result = scene_values(
            'result = [m.stroke_width for m in (Circle(), Line(), Arc(), VGroup(), Axes(), NumberLine(),\n'
            '          Axes().x_axis, Axes(stroke_width=6).x_axis, DoubleArrow(), DoubleArrow(ORIGIN, RIGHT, buff=0))]\n')
        self.assertEqual(result, [4, 4, 4, 4, 4, 2.0, 2.0, 2.0, 4.0, 2.5])

    def test_line_and_arc_helpers(self):
        result = scene_values(
            'a = Arc(start_angle=1, angle=2).shift(RIGHT)\n'
            'l = Line(LEFT, RIGHT); l.set_path_arc(1)\n'
            'm = Line(LEFT, RIGHT, path_arc=1); m.set_path_arc(0)\n'
            'n = Line(LEFT, RIGHT, buff=0.2); n.set_points_by_ends(UP, DOWN, buff=0.5, path_arc=2)\n'
            'result = [a.stop_angle(), l.get_points()[1], l.path_arc, m.get_start(), len(m.get_points()),\n'
            '          n.get_start(), n.get_end()]\n')
        self.assertEqual(result, [3.0, [-0.9237, -0.0417, 0.0], 1.0, [-1.0, 0.0, 0.0], 4,
                                  [0.0, 0.5, 0.0], [0.0, -0.5, 0.0]])

    def test_formula_and_number_line_helpers(self):
        result = scene_values(
            'm = MathTex("a", "c", "b"); p = m[2]\n'
            'n = NumberLine(x_range=[-2, 2, 1])\n'
            't = NumberLine(include_tip=True)\n'
            'result = [m.index_of_part(p), [x.get_tex_string() for x in m.sort_alphabetically()],\n'
            '          len(n.get_labels()), [x.get_value() for x in n.get_number_mobjects(1, 2)],\n'
            '          n.has_tip(), t.has_tip(), len(t.get_tips())]\n')
        self.assertEqual(result, [2, ['a', 'b', 'c'], 5, [1.0, 2.0], False, True, 1])
        with self.assertRaises(ValueError):
            scene_values('result = MathTex("a", "b").index_of_part(Square())\n')

    def test_point_results_support_array_methods(self):
        result = scene_values(
            'd = Dot(UP)\n'
            'p = d.get_center().copy()\n'
            'result = [p.tolist(), d.get_top().tolist(), list(d.get_center().shape), list(UR * [2, 0.5, 0]),\n'
            '          list([3, 1, 1] * LEFT), list(UR / [2, 4, 1])]\n')
        self.assertEqual(result, [[0.0, 1.0, 0.0], [0.0, 1.08, 0.0], [3.0], [2.0, 0.5, 0.0], [-3.0, 0.0, 0.0],
                                  [0.5, 0.25, 0.0]])

    @unittest.skipUnless(HAS_NUMPY, 'scene code gets NumPy point arrays only when NumPy is loaded')
    def test_point_results_are_mutable_arrays_with_numpy(self):
        result = scene_values(
            'd = Dot()\n'
            'p = d.get_center()\n'
            'p[1] = 2\n'
            'ax = Axes([-2, 2], [-2, 2], x_length=4, y_length=8, tips=False)\n'
            'pts = [ax.c2p(1, 3), ax.c2p(2, 4)]\n'
            'result = [type(p).__name__, p, d.get_center(), ax.p2c(pts), ax.c2p(np.array([[1, 3], [2, 4]])),\n'
            '          NumberLine().n2p(np.array([1, 2]))]\n')
        self.assertEqual(result, ['ndarray', [0.0, 2.0, 0.0], [0.0, 0.0, 0.0], [[1.0, 3.0], [2.0, 4.0]],
                                  [[1.0, 6.0, 0.0], [2.0, 8.0, 0.0]], [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]])


class AnimationApiTests(unittest.TestCase):
    def test_transform_paths(self):
        result = scene_values(
            't = Transform(Square(), Circle(), path_arc=PI/2)\n'
            'u = Transform(Square(), Circle()); u.path_func = clockwise_path()\n'
            'v = Transform(Square(), Circle(), path_func=counterclockwise_path())\n'
            'result = [t.create_target() is t.target_mobject, t.path_func([ORIGIN], [RIGHT], 0.5),\n'
            '          u.path_arc, u.path_func([ORIGIN], [RIGHT], 0.5), v.path_arc]\n')
        self.assertEqual(result, [True, [[0.5, -0.2071, 0.0]], 0.0, [[0.5, 0.5, 0.0]], 0.0])

    def test_path_func_drives_sampling(self):
        clockwise = scene_values(
            't = Transform(Dot(LEFT), Dot(RIGHT)); t.path_func = clockwise_path()\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        self.play(t)\n'
            's = S(); s.render(); result = [f for f in s.frames]\n')
        middle = clockwise[len(clockwise) // 2]
        self.assertGreater(middle['mobjects'][0]['position'][1], 0.5)

    def test_animate_builder_and_timing_validation(self):
        def error(body):
            return scene_values('try:\n' + ''.join('    ' + line + '\n' for line in body.splitlines()) +
                                '    result = None\nexcept Exception as e:\n    result = [type(e).__name__, str(e)]\n')
        self.assertEqual(scene_values('s = Square(); a = s.animate.shift(RIGHT)\n'
                                      'result = [isinstance(a.build(), Animation), s.target is not None]\n'),
                         [True, True])
        self.assertEqual(error('Square().animate(run_time=2)(run_time=3)'),
                         ['ValueError', 'Animation arguments must be passed before accessing methods '
                          'and can only be passed once'])
        self.assertEqual(error('Scene().wait(0)'),
                         ['ValueError', 'Scene.wait() has a duration of 0 <= 0 seconds which Manim cannot '
                          'render. The duration must be a positive number.'])
        self.assertEqual(error('Scene().play(AnimationGroup())'),
                         ['ValueError', 'Scene.play() has a total run_time of 0 <= 0 seconds which Manim '
                          'cannot render. The total run_time must be a positive number.'])
        self.assertEqual(scene_values('g = AnimationGroup()\nresult = [g.run_time, len(g.animations)]\n'),
                         [0.0, 0.0])
        self.assertEqual(error('FadeIn(Square(), run_time=-1)')[1][:39],
                         'The run_time of FadeIn cannot be negati')
        self.assertEqual(error("AddTextLetterByLetter(Text(''))"),
                         ['ValueError', "The text mobject Text('') does not seem to contain any characters."])
        self.assertEqual(error(
            'class Spin(Square):\n'
            '    @override_animation(FadeIn)\n'
            '    def _a(self, **kw):\n'
            '        return Rotate(self, PI)\n'
            'class Spin2(Spin):\n'
            '    @override_animation(FadeIn)\n'
            '    def _b(self, **kw):\n'
            '        return Rotate(self, PI)'),
            ['MultiAnimationOverrideException',
             'The animation FadeIn for Spin2 is overridden by more than one method: Spin._a and Spin2._b.'])

    def test_animation_group_accessors(self):
        result = scene_values(
            'g = AnimationGroup(FadeIn(Square()), FadeIn(Circle(), run_time=2), lag_ratio=0.5)\n'
            'result = [g.get_run_time(), [(s, e) for _, s, e in g.anims_with_timings], g.max_end_time,\n'
            '          g.init_run_time(5), g.is_remover(), len(g.get_all_mobjects()),\n'
            '          g.set_run_time(3).get_run_time(), g.set_name("x").name, g.get_rate_func()(0.5)]\n')
        self.assertEqual(result, [2.5, [[0.0, 1.0], [0.5, 2.5]], 2.5, 5.0, False, 0, 3.0, 'x', 0.5])

    def test_write_and_wiggle_helpers(self):
        result = scene_values(
            'w = Write(Square(color=RED), stroke_width=3)\n'
            'o = w.get_outline()\n'
            'wg = Wiggle(Square().shift(RIGHT), scale_about_point=UP)\n'
            'result = [w.stroke_width, o.get_fill_opacity(), o.get_stroke_width(), o.get_stroke_color(),\n'
            '          w.get_stroke_color(Circle()), wg.get_scale_about_point(), wg.get_rotate_about_point()]\n')
        self.assertEqual(result, [3.0, 0.0, 3.0, '#FC6255', '#FC6255', [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]])

    def test_animation_construction_helpers(self):
        result = scene_values(
            'f = Flash(ORIGIN, num_lines=4)\n'
            'h = Homotopy(lambda x, y, z, t: (x + t, y, z), Square())\n'
            'c = ChangeSpeed(Wait(1), speedinfo={0.5: 2})\n'
            'a = ApplyMatrix([[1, 2], [3, 4]], Square())\n'
            't = FadeTransform(Square(), Circle(radius=2)); g = Square(); t.ghost_to(g, Circle(radius=2))\n'
            'result = [len(f.create_lines()), len(f.create_line_anims()), h.function_at_time_t(0.5)([1, 2, 0]),\n'
            '          c.get_scaled_total_time(), a.initialize_matrix([[1, 2], [3, 4]]), g.width,\n'
            '          g.get_fill_opacity(), g.get_stroke_opacity(), Arrow().get_normal_vector()[2]]\n')
        self.assertEqual(result, [4, 4, [1.5, 2.0, 0.0], 0.5833, [[1.0, 2.0, 0.0], [3.0, 4.0, 0.0], [0.0, 0.0, 1.0]],
                                  4.0, 0.0, 0.0, -1.0])
        with self.assertRaises(ValueError):
            scene_values('s = Square()\nresult = ApplyMethod(s.shift, UP).check_validity_of_input(s)\n')

    def test_scene_animation_helpers(self):
        result = scene_values(
            's = Scene(); a, b = Square(), Circle()\n'
            'anims = s.compile_animations(FadeIn(a), b.animate.shift(UP), run_time=3)\n'
            't = Scene(); t.add_mobjects_from_animations([FadeIn(a), b.animate.shift(UP), Rotate(a)])\n'
            'u = Scene(); u.add(a, b); moving, static = u.get_moving_and_static_mobjects([FadeIn(b)])\n'
            'result = [[x.run_time for x in anims], [type(m).__name__ for m in t.mobjects],\n'
            '          Scene.validate_run_time(2, Scene.wait), [type(m).__name__ for m in moving],\n'
            '          [type(m).__name__ for m in static], b.animate.shift(UP).build().run_time]\n')
        self.assertEqual(result, [[3.0, 3.0], ['Circle', 'Square'], 2.0, ['Circle'], ['Square'], 1.0])
        with self.assertRaisesRegex(ValueError, 'cannot render'):
            scene_values('result = Scene.validate_run_time(0, Scene.wait)\n')
        with self.assertRaisesRegex(TypeError, 'Use Mobject.animate'):
            scene_values('result = Scene().compile_animations(Square().shift)\n')

    def test_group_remover_removes_every_member(self):
        frames = json.loads(lite.render_scene(
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        self.play(AnimationGroup(AnimationGroup(Create(Square()), Create(Circle())),\n'
            '                                 Succession(FadeIn(Dot()), FadeIn(Star())), remover=True))\n'
            '        self.wait(0.1)\n'))['frames']
        self.assertGreater(len(frames[0]['mobjects']), 0)
        self.assertEqual(frames[-1]['mobjects'], [])

    def test_become_matching_options(self):
        result = scene_values(
            's = Rectangle(width=2, height=1).shift(UP); d = Dot()\n'
            'a = s.copy().become(d, match_width=True)\n'
            'b = s.copy().become(d, match_height=True, match_center=True)\n'
            'c = s.copy().become(d, stretch=True)\n'
            'result = [a.width, a.get_center(), b.height, b.get_center(), c.width, c.height]\n')
        self.assertEqual(result, [2.0, [0.0, 0.0, 0.0], 1.0, [0.0, 1.0, 0.0], 2.0, 1.0])

    def test_transform_path_variants(self):
        result = scene_values(
            't = Transform(VGroup(Dot(LEFT)), VGroup(Dot(RIGHT)), path_arc=PI, path_arc_centers=ORIGIN)\n'
            'f = FadeTransform(Square().shift(LEFT), VGroup().shift(RIGHT))\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        self.play(t)\n'
            '        self.play(ApplyComplexFunction(lambda z: z + 2j, Square()))\n'
            '        self.add(Square().shift(LEFT)); self.play(f)\n'
            's = S(); s.render(); result = [type(t.path_func).__name__, s.frames]\n')
        self.assertEqual(result[0], '_CirclesPath')
        frames = result[1]
        # The counterclockwise orbit passes below the center; the complex shift moves straight up (no arc).
        self.assertTrue(any(f['mobjects'][0]['children'][0]['position'][1] < -0.9 for f in frames[:16]))
        shifted = [f['mobjects'][-1] for f in frames[16:30]]
        self.assertTrue(all(abs(m['position'][0] + m['geometry_center'][0]) < 1e-9 for m in shifted))
        self.assertGreater(shifted[-1]['geometry_center'][1], 1.9)

    def test_plot_colorscale(self):
        result = scene_values(
            'ax = Axes(x_range=[-3, 3], y_range=[-3, 3])\n'
            'c = ax.plot(lambda x: x, x_range=(-3, 3, 1), colorscale=[(RED, -1), (BLUE, 2)])\n'
            'result = [[str(x) for x in c.get_stroke_colors()], c.get_sheen_direction()]\n')
        self.assertEqual(result, [['#FC6255', '#FC6255', '#FC6255', '#C58282', '#8EA3AF', '#58C4DD', '#58C4DD'],
                                  [1.0, 0.0, 0.0]])

    @unittest.skipUnless(HAS_NUMPY, 'vectorized plotting passes NumPy arrays to the function')
    def test_vectorized_plot(self):
        result = scene_values(
            'ax = Axes(x_range=[-1, 4], y_range=[0, 3], x_axis_config={"scaling": LogBase()})\n'
            'g = ax.plot(lambda x: np.where(x < 10, 2, 1), x_range=[-1, 4], use_vectorized=True)\n'
            'ax2 = Axes()\n'
            'f = ax2.plot(lambda x: 2 * x, x_range=[0, 2])\n'
            'a = ax2.plot_antiderivative_graph(f, use_vectorized=True)\n'
            'b = ax2.plot_antiderivative_graph(f)\n'
            'result = [len(g.points), g.points[0], g.points[-1], np.allclose(a.points, b.points)]\n')
        self.assertEqual(result, [200.0, [-6.0, 1.0, 0.0], [6.0, -1.0, 0.0], True])

    def test_play_accepts_lists_and_generators(self):
        frames = json.loads(lite.render_scene(
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        dots = [Dot(RIGHT * i) for i in range(3)]\n'
            '        self.play([FadeIn(d) for d in dots[:2]], (Create(d) for d in dots[2:]))\n'))['frames']
        self.assertEqual(len(frames[-1]['mobjects']), 3)

    def test_special_three_d_scene_helpers(self):
        frames = json.loads(lite.render_scene(
            'from manim import *\n'
            'class S(SpecialThreeDScene):\n'
            '    def construct(self):\n'
            '        self.set_camera_to_default_position()\n'
            '        self.add(self.get_axes(), self.get_sphere(resolution=(6, 12)))\n'
            '        self.wait(0.2)\n'))['frames']
        camera = frames[-1]['camera']['three_d']
        self.assertAlmostEqual(camera['phi'], 70 * lite.DEGREES)
        self.assertAlmostEqual(camera['theta'], -110 * lite.DEGREES)

    def test_coordinate_system_queries(self):
        self.assertEqual(scene_values(
            'ax = Axes()\n'
            'g = ax.plot_line_graph([1, 3, 5], [-1, 2, -2], add_vertex_dots=False)["line_graph"]\n'
            'log = Axes(x_range=[0, 3], y_range=[0, 1], tips=False, x_axis_config={"scaling": LogBase()})\n'
            'lg = log.plot_line_graph([1, 10, 100, 1000], [0.5] * 4, add_vertex_dots=False)["line_graph"]\n'
            'label = log.get_graph_label(lg, Dot(), x_val=100, dot=True)\n'
            'result = [ax.input_to_graph_point(PI, g), [round(v, 3) for v in label.dot.get_center()]]\n'),
            [[2.6928, 1.2876, 0.0], [2.0, 0.0, 0.0]])
        self.assertEqual(scene_values(
            'cs = CoordinateSystem()\n'
            'result = [cs.x_range, cs.y_range, cs.dimension, Axes().dimension, ThreeDAxes().dimension]\n'),
            [[-7.0, 7.0, 1.0], [-4.0, 4.0, 1.0], 2.0, 2.0, 3.0])
        with self.assertRaises(NotImplementedError):
            scene_values('result = CoordinateSystem().get_axes()\n')
        self.assertEqual(scene_values(
            'line = NumberLine([0, 7], length=12)\n'
            'result = [line.unit_size, NumberLine([0, 4], unit_size=2).unit_size,'
            ' line.p2n([line.n2p(1), line.n2p(2.5)])]\n'),
            [1.7143, 2.0, [1.0, 2.5]])
        self.assertEqual(scene_values(
            'ax = ThreeDAxes(x_range=(3, 9, 1), y_range=(6, 12, 1), z_range=(2, 5, 1),'
            ' x_axis_config={"scaling": LogBase()}, y_axis_config={"scaling": LogBase()},'
            ' z_axis_config={"scaling": LogBase()})\n'
            'result = [ax.c2p(1000, 1e6, 100), ax.z_axis.n2p(1000)]\n'),
            [[-5.25, -5.25, 0.0], [-5.25, -5.25, 2.1667]])
        self.assertEqual(scene_values(
            'plane = NumberPlane(x_range=[2, 4])\n'
            'result = [plane.c2p([[1, 0], [3, 4]]), plane.c2p([1, 3], [0, 4]), plane.c2p(1)]\n'),
            [[[-2.0, 0.0, 0.0], [0.0, 4.0, 0.0]], [[-2.0, 0.0], [0.0, 4.0], [0.0, 0.0]],
             [-2.0, 0.0, 0.0]])

    def test_submobject_validation_and_strings(self):
        self.assertEqual(scene_values(
            'result = []\n'
            'for build in (lambda: VGroup().add(Mobject()), lambda: VGroup([VMobject(), 3])):\n'
            '    try:\n'
            '        build()\n'
            '    except TypeError as error:\n'
            '        result.append(str(error))\n'), [
            'Only values of type VMobject can be added as submobjects of VGroup, but the value '
            'Mobject (at index 0 of parameter 0) is of type Mobject. You can try adding this '
            'value into a Group instead.',
            'Only values of type VMobject can be added as submobjects of VGroup, but the value '
            '3 (at index 1 of parameter 0) is of type int.'])
        with self.assertRaisesRegex(TypeError, 'of type VMobject can be added as submobjects of VMobject'):
            scene_values('result = VMobject().add(3)\n')
        self.assertEqual(scene_values(
            'result = [str(VGroup()), str(VGroup(Circle())), repr(VGroup(Circle(), Text("a"))),'
            ' str(VGroup(Square(), Square()))]\n'),
            ['VGroup of 0 submobjects', 'VGroup of 1 submobject', "VGroup(Circle, Text('a'))",
             'VGroup of 2 submobjects'])
        self.assertEqual(scene_values(
            'm1, m2, m3, m4 = Mobject(), Mobject(), Mobject(), Mobject()\n'
            'obj = Mobject().add(m1)\n'
            'obj.insert(0, m2); obj.insert(-1, m3); obj.insert(10, m4); obj.insert(4, m1)\n'
            'names = {m1: "m1", m2: "m2", m3: "m3", m4: "m4"}\n'
            'result = [names[m] for m in obj.submobjects]\n'), ['m2', 'm3', 'm4', 'm1'])

    def test_plain_mobject_points_and_compat_accessors(self):
        self.assertEqual(scene_values(
            'm = Mobject()\n'
            'm.points = [[-1, -2, -3], [1, 3, 5]]\n'
            'g = Group(m, Square().shift(RIGHT * 4))\n'
            'result = [m.width, m.height, m.depth, m.get_center(), g.width, m.shift(UP).get_center()]\n'),
            [2.0, 5.0, 8.0, [0.0, 0.5, 1.0], 6.0, [0.0, 1.5, 1.0]])
        self.assertEqual(scene_values(
            'm = Mobject(); m.test = 3\n'
            'result = [m.get_test(), m.set_test(5).test, hasattr(m, "get_anything")]\n'), [3.0, 5.0, True])
        self.assertEqual(scene_values(
            'v = VMobject()\n'
            'result = [v.consider_points_equals_2d([float("inf"), 0], [float("inf"), 0]),'
            ' v.consider_points_equals_2d([float("nan"), 0], [float("nan"), 0]),'
            ' v.consider_points_equals_2d([float("inf"), 0], [0, 0])]\n'), [True, False, False])
        self.assertEqual(scene_values(
            'a = VMobject(); a.set_stroke(width=50, background=True); a.scale(0.5, scale_stroke=True)\n'
            'p = Polygon(UP * 3 ** 0.5, LEFT, RIGHT).shift(LEFT).scale(0.8)\n'
            'result = [a.get_stroke_width(background=True),'
            ' [p.proportion_from_point(v) for v in p.get_vertices()]]\n'), [25.0, [0.0, 0.3333, 0.6667]])

    def test_color_values_operators_and_helpers(self):
        self.assertEqual(scene_values(
            'result = [repr(WHITE / 2), list(WHITE / 2), repr(~RED), int(RED), RED[0], repr(RED & BLUE),\n'
            '          repr(0.5 * RED + 0.5 * BLUE), RED == RED.opacity(.5), RED == ManimColor("#fc6255"),\n'
            '          hash(RED) == hash("#FC6255FF"), repr(rgb_to_color((1, 0, 0))), rgb_to_hex((1., 0, 0)),\n'
            '          list(color_to_int_rgba("#FF8040", alpha=0.5)), repr(HSV((0.25, 1, 1))), HSV((0.25, 1, 1))[0],\n'
            '          color_gradient([RED, BLUE, GREEN], 4), list(color_to_rgb("#F00")), repr(average_color(RED, BLUE))]\n'),
            ["ManimColor('#7F7F7F')", [0.5, 0.5, 0.5, 0.5], "ManimColor('#029DAA')", 16540245.0, 0.9882,
             "ManimColor('#584055')", "ManimColor('#AA9399')", False, True, True, "ManimColor('#010000')",
             '#010000', [255.0, 128.0, 64.0, 127.0], "HSV('#7FFF00')", 0.25,
             ['#FC6255', '#8EA3AF', '#66C3B5', '#83C167'], [1.0, 0.0, 0.0], "ManimColor('#AA9399')"])
        for source, message in (('ManimColor("TOMATO")', 'Color TOMATO not found'),
                                ('ManimColor("#12345")', 'contain 6 or 8 hexadecimal numbers'),
                                ('color_gradient([], 5)', 'Expected 1 or more reference colors')):
            with self.assertRaisesRegex(ValueError, message):
                scene_values('result = %s\n' % source)

    def test_graph_matrix_number_and_scene_options(self):
        self.assertEqual(scene_values(
            'g = Graph([1, 2, 3], [(1, 2), (2, 3)], layout="circular")\n'
            'm = Matrix([[1, 2], [3, 4]], left_bracket="(", right_bracket=")")\n'
            'n = DecimalNumber(3.14159, num_decimal_places=3); n.num_decimal_places = 1; n.set_value(2.71828)\n'
            'with tempconfig({"seed": 5}):\n'
            '    Scene(); a = [random_color() for _ in range(3)]\n'
            '    Scene(); b = [random_color() for _ in range(3)]\n'
            's = Scene(); s.add_subcaption("a", duration=1); s.wait()\n'
            's.play(Wait(), run_time=2, subcaption="b", subcaption_duration=1.5, subcaption_offset=.5)\n'
            'result = [str(g), str(DiGraph([1, 2], [(1, 2)])), list(g._graph.nodes()), m.left_bracket,\n'
            '          m.right_bracket, n.num_decimal_places, n.text, a == b, a,\n'
            '          [(c.content, c.start.total_seconds(), c.end.total_seconds())\n'
            '           for c in s.renderer.file_writer.subcaptions]]\n'),
            ['Undirected graph on 3 vertices and 2 edges', 'Directed graph on 2 vertices and 1 edges',
             [1.0, 2.0, 3.0], '(', ')', 1.0, '2.7', True, ['#FF862F', '#236B8E', '#699C52'],
             [['a', 0.0, 1.0], ['b', 1.5, 3.0]]])

    def test_units_table_labels_and_fixed_mobjects(self):
        self.assertEqual(scene_values(
            'from manim.utils.unit import Pixels, Percent, Degrees, Munits\n'
            't = Table([["A", "B"], ["C", "D"]], row_labels=iter(()), col_labels=[Text("x"), Text("y")])\n'
            's = ThreeDScene(); sq = Square()\n'
            's.add_fixed_in_frame_mobjects(sq); s.add_fixed_orientation_mobjects(Circle())\n'
            'a = [Percent(X_AXIS) * 50, Percent(Y_AXIS) * 25, 960 * Pixels, 90 * Degrees, 3 * Munits]\n'
            'with tempconfig({"pixel_width": 1000}) as c:\n'
            '    a.append(10 * Pixels == 10 * c.frame_width / 1000)\n'
            'result = a + [960 * Pixels, len(t.get_row_labels()), len(t.get_col_labels()),\n'
            '              sq in s.renderer.camera.fixed_in_frame_mobjects,\n'
            '              type(s.renderer.camera.fixed_orientation_mobjects).__name__]\n'),
            [7.1111, 2.0, 7.1111, 1.5708, 3.0, True, 7.1111, 0.0, 2.0, True, 'dict'])

    def test_tex_templates_typing_aliases_and_empty_groups(self):
        self.assertEqual(scene_values(
            'from manim.typing import Point3D, ManimFloat\n'
            'from manim.utils.tex import _texcode_for_environment\n'
            'from manim.utils.bezier import get_quadratic_approximation_of_cubic\n'
            'import typing\n'
            'def f(p: typing.Optional[Point3D] = None) -> Point3D: return p\n'
            't = TexTemplate(); t.add_to_preamble(r"\\usepackage{x}", prepend=True); t.add_to_document("D")\n'
            'q = get_quadratic_approximation_of_cubic([0, 0, 0], [1, 0, 0], [2, 1, 0], [2, 2, 0])\n'
            'g = VGroup().shift(3 * RIGHT)\n'
            'result = [t.get_texcode_for_expression_in_env("E", "{tabular}[t]{cc}").split("\\n"),\n'
            '          _texcode_for_environment("align*"), ManimFloat(2), [list(p) for p in q],\n'
            '          list(g.get_center()), config.tex_template.placeholder_text]\n'),
            [['\\documentclass[preview]{standalone}', '\\usepackage{x}', '\\usepackage[english]{babel}',
              '\\usepackage{amsmath}', '\\usepackage{amssymb}', '\\begin{document}', 'D',
              '\\begin{tabular}[t]{cc}', 'E', '\\end{tabular}', '\\end{document}'],
             ['\\begin{align*}', '\\end{align*}'], 2.0,
             [[0.0, 0.0, 0.0], [0.75, 0.0, 0.0], [1.375, 0.625, 0.0], [1.375, 0.625, 0.0],
              [2.0, 1.25, 0.0], [2.0, 2.0, 0.0]], [0.0, 0.0, 0.0], 'YourTextHere'])

    def test_color_properties_group_smoothing_and_transformed_squares(self):
        self.assertEqual(scene_values(
            's = Square(); a = [s.color, s.fill_color, s.stroke_color]\n'
            's.color = RED; b = [s.get_fill_color(), s.get_stroke_color(), s.get_fill_opacity()]\n'
            's.fill_color = BLUE; c = [s.get_fill_color(), s.get_stroke_color()]\n'
            's.stroke_color = GREEN; d = [s.get_fill_color(), s.get_stroke_color(), s.color]\n'
            'g = VGroup(Square(), Circle()); g.color = YELLOW\n'
            'e = [m.get_stroke_color() for m in g] + [g.color]\n'
            'source = Circle(color=RED, fill_opacity=.4).set_fill(BLUE)\n'
            'v = VGroup(Square(), Line(LEFT, RIGHT)); v.make_smooth()\n'
            'm1 = Square(); scene = Scene(); scene.play(Transform(m1, Rectangle().rotate(0.2)))\n'
            'result = [a, b, c, d, e, Square().match_color(source).get_color(), len(v[0].points),\n'
            '          m1.width, m1.height, m1.side_length]\n'),
            [['#FFFFFF'] * 3, ['#FC6255', '#FC6255', 0.0], ['#58C4DD', '#FC6255'],
             ['#58C4DD', '#83C167', '#83C167'], ['#F7D96F'] * 3, '#58C4DD', 16.0, 4.3176, 2.7548, 4.0])

    def test_angles_need_xy_lines_and_passive_config_names_exist(self):
        for body in ('Angle(Line([0, 0, 1], [1, 0, 1]), Line([0, 0, 1], [0, 1, 1]))',
                     'line_intersection([ORIGIN, OUT], [ORIGIN, UP])'):
            with self.assertRaisesRegex(ValueError, 'xy-plane'):
                scene_values('result = %s\n' % body)
        self.assertEqual(scene_values(
            'result = [config["text_dir"], config.tex_dir, config.transparent, config.zero_pad,\n'
            '          config.upto_animation_number > 1e9, Angle(Line(LEFT, RIGHT), Line(DOWN, UP)).get_value()]\n'),
            ['{media_dir}/texts', '{media_dir}/Tex', False, 4.0, True, 1.5708])

    def test_align_points_pairs_subpaths(self):
        self.assertEqual(scene_values(
            'o = VMobject(); o.start_new_path(ORIGIN); o.add_line_to(UP); o.add_line_to(UR); o.add_line_to(RIGHT)\n'
            'o.start_new_path(2 * RIGHT); o.add_line_to(2 * RIGHT + UP)\n'
            'p = VMobject(); p.start_new_path(ORIGIN); p.add_line_to(UP)\n'
            'p.start_new_path(RIGHT); p.add_line_to(UR); p.add_line_to(RIGHT + 2 * UP)\n'
            'o.align_points(p)\n'
            'result = [[len(s) // 4 for s in o.get_subpaths()], [len(s) // 4 for s in p.get_subpaths()],\n'
            '          o.get_subpaths()[1][3], p.get_subpaths()[0][3]]\n'),
            [[3.0, 2.0], [3.0, 2.0], [2.0, 0.5, 0.0], [0.0, 0.3333, 0.0]])

    def test_number_line_tips_squeeze_the_family_like_community(self):
        self.assertEqual(scene_values(
            'b = NumberLine(x_range=[-3, 3, 1]); b.add_tip()\n'
            'after = [t.get_center()[0] for t in b.ticks]\n'
            'b.add_tip(at_start=True)\n'
            'both = [b.has_tip(), b.has_start_tip(), b.tip.base, b.start_tip.base, b.n2p(2)]\n'
            'c = NumberLine(x_range=[0, 4, 1]).rotate(PI / 4).shift(UP).scale(0.5)\n'
            'c.add_tip(tip_length=0.5, tip_width=0.3)\n'
            'tips = b.pop_tips()\n'
            'result = [after, both, c.tip.get_tip_point(), c.tip.base, c.get_center(), c.width,\n'
            '          len(tips), b.has_tip(), tips[0].get_tip_point()]\n'),
            [[-3.0, -2.0583, -1.1167, -0.175, 0.7667, 1.7083, 2.65],
             [True, True, [2.6704, 0.0, 0.0], [-2.65, 0.0, 0.0], [2.0, 0.0, 0.0]],
             [0.7071, 1.7071, 0.0], [0.3536, 1.3536, 0.0], [-0.0133, 0.9867, 0.0], 1.4407,
             2.0, False, [3.0, 0.0, 0.0]])

    def test_scene_restructuring_helpers_and_font_list(self):
        self.assertEqual(scene_values(
            'a, b, c = Square(), Circle(), Dot(); g = VGroup(a, b)\n'
            'scene = Scene(); scene.add(g, c)\n'
            'scene.restructure_mobjects([a])\n'
            'listed = scene.get_restructured_mobject_list([g, c], [c])\n'
            'result = [[type(m).__name__ for m in scene.mobjects], listed == [g], "monospace" in Text.font_list()]\n'),
            [['Circle', 'Dot'], True, True])

    def test_manimpango_enums_drive_text_weights(self):
        self.assertEqual(scene_values(
            'import manimpango\n'
            'weights = sorted(manimpango.Weight, key=lambda w: w.value)\n'
            'g = VGroup(*(Text(w.name, weight=w.name) for w in weights))\n'
            'result = [weights[0].name, weights[-1].value, len(g), g[7].weight, manimpango.Style.ITALIC.value]\n'),
            ['THIN', 1000.0, 11.0, 'BOLD', 2.0])

    def test_bulleted_list_and_title_tex_queries(self):
        self.assertEqual(scene_values(
            'b = BulletedList("Item 1", "Item 2", "Item 3", height=2, width=2)\n'
            'b.set_color_by_tex("Item 1", RED)\n'
            'b.set_opacity_by_tex("Item 3", 0.2, remaining_opacity=0.9)\n'
            't = Title("Hello World").set_color_by_tex("Hello World", BLUE)\n'
            'result = [b.index_of_part(b.get_part_by_tex("Item 2")), b[0].get_color(), b[1].get_color(),\n'
            '          b[2].get_fill_opacity(), b[0].get_fill_opacity(), b.tex_strings, t[0][0].get_color(),\n'
            '          t.font_size, t.get_tex_string()]\n'),
            [1.0, '#FC6255', '#FFFFFF', 0.2, 0.9, ['Item 1', 'Item 2', 'Item 3'], '#58C4DD', 48.0, 'Hello World'])

    def test_manual_animation_protocol_and_custom_targets(self):
        self.assertEqual(scene_values(
            'class ToRight(Transform):\n'
            '    def create_target(self):\n'
            '        return self.mobject.copy().shift(2 * RIGHT).scale(0.5)\n'
            's = Square()\n'
            'a = ToRight(s)\n'
            'a.begin(); a.interpolate(0.5); mid = [s.get_center(), s.width]\n'
            'a.interpolate(1); a.finish()\n'
            'i = Square(); ind = Indicate(i); ind.begin(); ind.interpolate(0.5)\n'
            'q, c = Square(), Circle()\n'
            'g = AnimationGroup(FadeIn(q), c.animate.shift(RIGHT), lag_ratio=0.5)\n'
            'g.begin(); g.interpolate(0.5); half = c.get_center()\n'
            'g.finish()\n'
            'u, v = Square(), Circle()\n'
            'w = Succession(u.animate.shift(RIGHT), v.animate.shift(UP))\n'
            'w.begin(); w.interpolate(0.75); stage = [u.get_center(), v.get_center()]\n'
            'w.finish()\n'
            'result = [mid, s.get_center(), s.width, i.get_color(), i.width, half, c.get_center(),\n'
            '          stage, v.get_center(), FunctionGraph(lambda x: x).get_color()]\n'),
            [[[1.0, 0.0, 0.0], 1.5], [2.0, 0.0, 0.0], 1.0, '#FFFF00', 2.4, [0.0701, 0.0, 0.0],
             [1.0, 0.0, 0.0], [[1.0, 0.0, 0.0], [0.0, 0.5, 0.0]], [0.0, 1.0, 0.0], '#FFFF00'])

    def test_manual_groups_accept_mobject_free_waits(self):
        self.assertEqual(scene_values(
            's = Square()\n'
            'g = AnimationGroup(Wait(), FadeIn(s), lag_ratio=1)\n'
            'g.begin(); g.interpolate(0.75); half = s.get_stroke_opacity()\n'
            'g.finish()\n'
            'result = [g.anims_with_timings.tolist()[1][1:], half, s.get_stroke_opacity()]\n'),
            [[1.0, 2.0], 0.5, 1.0])

    def test_containers_report_empty_subpaths_and_arrows_sample_shafts(self):
        self.assertEqual(scene_values(
            'g = VGroup(Square())\n'
            'g.set_points(g.points)\n'
            'result = [len(g.get_subpaths()), len(Text("a").get_subpaths()), len(Square().get_subpaths()),\n'
            '          Arrow(LEFT, UP * 2).point_from_proportion(0.25), DoubleArrow().point_from_proportion(0.5)]\n'),
            [0.0, 0.0, 1.0, [-0.7332, 0.5335, 0.0], [0.0, 0.0, 0.0]])

    def test_curved_arrows_sample_their_trimmed_shaft(self):
        self.assertEqual(scene_values(
            'a = CurvedArrow(LEFT, RIGHT)\n'
            'result = [a.point_from_proportion(0.5), a.point_from_proportion(1),\n'
            '          CurvedDoubleArrow(LEFT * 2, UP, angle=-1).point_from_proportion(0.3),\n'
            '          Arc().add_tip().point_from_proportion(0.5)]\n'),
            [[-0.175, -0.4867, 0.0], [0.7525, -0.2475, 0.0], [-1.4589, 0.6824, 0.0], [0.8821, 0.6346, 0.0]])

    def test_text_glyphs_are_leaves(self):
        self.assertEqual(scene_values(
            'def depth(m):\n'
            '    return 1 + max([depth(c) for c in m.submobjects], default=0)\n'
            't = Text("ab")\n'
            'result = [depth(t), len(t[0].submobjects), len(list(t[0])), depth(Table([["a", "b"]]))]\n'),
            [2.0, 0.0, 1.0, 5.0])

    def test_animation_role_flags_match_community(self):
        self.assertEqual(scene_values(
            'result = [[a.introducer, a.remover] for a in (\n'
            '    Uncreate(Square()), ShrinkToCenter(Square()), ShowPassingFlash(Square()),\n'
            '    ShowPassingFlashWithThinningStrokeWidth(Square()), Create(Square()), FadeOut(Square()))]\n'),
            [[False, True], [False, False], [True, True], [False, False], [True, False], [False, True]])

    def test_standalone_tips_match_community_construction(self):
        self.assertEqual(scene_values(
            'result = []\n'
            'for cls in (ArrowTriangleTip, StealthTip, ArrowCircleTip, ArrowSquareTip):\n'
            '    t = cls()\n'
            '    result.append([t.get_color(), t.tip_point, t.base, t.get_center(), t.start_angle])\n'),
            [['#58C4DD', [-0.425, 0.0, 0.0], [-0.075, 0.0, 0.0], [-0.25, 0.0, 0.0], 3.1416],
             ['#FFFFFF', [0.4875, 0.0, 0.0], [0.3781, 0.0, 0.0], [0.4, 0.0, 0.0], 3.1416],
             ['#FC6255', [0.175, 0.0, 0.0], [-0.175, 0.0, 0.0], [0.0, 0.0, 0.0], 0.0],
             ['#FFFFFF', [0.175, 0.175, 0.0], [-0.175, -0.175, 0.0], [0.0, 0.0, 0.0], 3.1416]])

    def test_dashed_arrows_keep_one_set_of_tips(self):
        self.assertEqual(scene_values(
            'd = DashedVMobject(Arrow(ORIGIN, 2 * UR, color=RED))\n'
            'two = DashedVMobject(Arrow(ORIGIN, 2 * UR).add_tip(at_start=True), num_dashes=5)\n'
            'result = [len(d.submobjects), d.submobjects[0].get_start(), d.submobjects[-2].get_end(),'
            ' type(d.submobjects[-1]).__name__, d.get_center(), d.width, len(two.submobjects), two.width]\n'),
            [16.0, [0.1768, 0.1768, 0.0], [1.8232, 1.8232, 0.0], 'ArrowTriangleFilledTip',
             [1.0, 1.0, 0.0], 1.6464, 7.0, 1.6464])

    def test_opengl_and_pixel_camera_names_fail_clearly(self):
        for name in ('DotCloud', 'TrueDot', 'OpenGLPMobject', 'MappingCamera', 'SplitScreenCamera'):
            with self.assertRaisesRegex(NotImplementedError, name):
                scene_values('result = %s()\n' % name)

    def test_pixel_images_are_reported_as_unsupported(self):
        with self.assertRaises(NotImplementedError):
            scene_values('result = Square().get_image()\n')


if __name__ == '__main__':
    unittest.main()
