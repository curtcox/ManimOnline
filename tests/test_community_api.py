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
