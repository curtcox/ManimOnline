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

    def test_unknown_keywords_raise_type_error(self):
        for build, message in ((lambda: lite.ParametricFunction(lambda t: (t, t, 0), t_min=-3),
                                "Mobject.__init__() got an unexpected keyword argument 't_min'"),
                               (lambda: lite.Square().set_style(glow=1),
                                "VMobject.set_style() got an unexpected keyword argument 'glow'")):
            with self.assertRaises(TypeError) as caught:
                build()
            self.assertEqual(str(caught.exception), message)

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

    def test_single_color_text_and_arrow_only_growth(self):
        # Community-measured errors: text, TeX and SVG store one ManimColor; GrowArrow's
        # starting copy calls scale(0, scale_tips=True), which only Arrow accepts.
        self.assertEqual(scene_values(
            'result = []\n'
            'for build in (lambda: MathTex("x", color=[RED, BLUE, GREEN]), lambda: Text("x", color=[RED, BLUE]),\n'
            '              lambda: Tex("x", color=["#FF0000", "#00FF00", "#0000FF"]),\n'
            '              lambda: GrowArrow(Line()).begin(),\n'
            '              lambda: GrowArrow(ImageMobject([[[0, 0, 0]]])).begin()):\n'
            '    try:\n'
            '        build()\n'
            '        result.append("ok")\n'
            '    except Exception as error:\n'
            '        result.append(f"{type(error).__name__}: {error}")\n'
            'result += [MathTex("x", color=(1, 0, 0)).color]\n'
            '# A constructor color list paints VMobjects solid; stroke/fill lists and set_color are gradients.\n'
            'result += [[m.color, m.get_stroke_color(), m.get_fill_color()] for m in (Square(color=[RED, BLUE]),\n'
            '           VGroup(Dot(), color=[RED, BLUE]), Line(color=[GREEN, BLUE]))]\n'
            'result += [Square(stroke_color=[RED, BLUE]).stroke_color, Square().set_color([RED, BLUE]).fill_color]\n'
            'result += [Square().set_sheen_direction(None).get_sheen_direction()]\n'),
            ['ValueError: setting an array element with a sequence.',
             'ValueError: ManimColor only accepts lists/tuples/arrays of length 3 or 4, not 2',
             "ValueError: could not convert string to float: '#FF0000'",
             "TypeError: VMobject.scale() got an unexpected keyword argument 'scale_tips'",
             "TypeError: Mobject.scale() got an unexpected keyword argument 'scale_tips'",
             '#010000', ['#FC6255'] * 3, ['#FC6255'] * 3, ['#83C167'] * 3, '#FC6255', '#FC6255', None])

    def test_smoothed_double_arrow_scale_keeps_arrow_tip_semantics(self):
        # Community 0.22: Arrow.scale keeps tip sizes even after make_smooth curves the shaft.
        self.assertEqual(scene_values(
            'o = DoubleArrow(LEFT * 2, RIGHT).make_smooth()\n'
            'o.add(Square().scale(0.3))\n'
            'o.scale(1.2)\n'
            'result = [[round(float(v), 4) for v in (m.get_left()[0], m.get_right()[0], m.height)]\n'
            '          for m in o.submobjects]\n'),
            [[-0.2639, 0.4444, 0.7083], [0.65, 1.0, 0.4667], [-2.0, -1.65, 0.4667]])

    def test_vgroup_own_points_and_community_failures(self):
        # Community 0.22: a VGroup is a VMobject, so its own points are kept and moved;
        # Arrow.scale re-adds a lone start tip as old_tips[1]; restore() is become(), which
        # plain Mobjects cannot run.
        self.assertEqual(scene_values(
            'g = VGroup(Square(), Dot(RIGHT * 3)).set_points_as_corners([LEFT, RIGHT, UP])\n'
            'g.shift(UP)\n'
            'result = [len(g.points), g.width, g.get_center(), g.points[0], len(g.submobjects)]\n'
            'g.add_line_to(DOWN)\n'
            'result += [len(g.points), len(VGroup().set_points_as_corners([LEFT, RIGHT]).clear_points().points)]\n'
            'a = DoubleArrow(LEFT * 2, RIGHT)\n'
            'a.remove(a.submobjects[0])\n'
            'for call in (lambda: a.scale(2), lambda: Group(Square()).save_state().restore(),\n'
            '             lambda: ValueTracker(1).save_state().restore()):\n'
            '    try:\n'
            '        call()\n'
            '        result.append("ok")\n'
            '    except Exception as error:\n'
            '        result.append(f"{type(error).__name__}: {error}")\n'),
            [8, 4.08, [1.04, 1.0, 0.0], [-1.0, 1.0, 0.0], 2, 12, 0,
             'IndexError: range object index out of range',
             'NotImplementedError: Please override in a child class.',
             'NotImplementedError: Please override in a child class.'])

    def test_wait_placeholder_reversed_arrow_fade_and_collapsed_arc(self):
        # Community 0.22: wait() adds an empty Mobject root (ReplacementTransform keeps the
        # replaced root's slot); FadeIn's re-tipped copy of a reversed arrow regrows its shaft;
        # a shape shrunk to a point still follows path_arc.
        self.assertEqual(scene_values(
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        o = Elbow(); self.add(o); self.wait(0.2)\n'
            '        self.play(ReplacementTransform(o, Star()))\n'
            '        self.roots = [type(m).__name__ for m in self.mobjects]\n'
            '        a = Arrow(LEFT, RIGHT).reverse_points(); self.add(a)\n'
            '        self.lefts, self.ys = [], []\n'
            '        self.add_updater(lambda dt: self.lefts.append(a.get_left()[0]))\n'
            '        self.play(FadeIn(a), run_time=0.4)\n'
            '        self.remove_updater(self.updaters[-1])\n'
            '        p = Square(); self.play(ShrinkToCenter(p)); self.add(p)\n'
            '        self.add_updater(lambda dt: self.ys.append(p.get_y()))\n'
            '        self.play(p.animate(path_arc=1).shift(RIGHT), run_time=0.4)\n'
            's = S(); s.render(); result = [s.roots, s.lefts, s.ys]\n'),
            [['Star', 'Mobject'], [0.4, 0.3677, 0.2226, -0.175, -0.5726, -0.7177],
             [0.0, -0.0137, -0.0659, -0.1277, -0.0659, -0.0137]])

    def test_rotate_keeps_tip_and_fade_keeps_turned_tip_still(self):
        # Community 0.22: Rotate keeps member identities (tip points stay in world
        # coordinates); FadeOut's re-tipped copy of a half-turned vector does not spin.
        self.assertEqual(scene_values(
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        o = Vector(UP + RIGHT); self.add(o); tip = o.tip\n'
            '        self.play(Rotate(o, PI, about_point=ORIGIN), run_time=0.4)\n'
            '        self.same, self.tip = o.tip is tip, list(o.tip.points[0])\n'
            '        o.move_to(RIGHT * 2 + UP); self.lefts = []\n'
            '        self.add_updater(lambda dt: self.lefts.append(o.get_left()[0]))\n'
            '        self.play(FadeOut(o), run_time=0.4)\n'
            's = S(); s.render(); result = [s.same, s.tip, sorted(set(s.lefts))]\n'),
            [True, [-1.0, -1.0, 0.0], [1.5]])

    def test_zero_scaled_tipped_arrow_keeps_collapsed_shaft(self):
        # Community 0.22: re-adding tips to a zero-length shaft never cuts it at their bases.
        self.assertEqual(scene_values(
            'a, d = Arrow(LEFT * 3, RIGHT * 2).scale(0), DoubleArrow(LEFT * 3, RIGHT * 2).scale(0)\n'
            'result = [[list(m.points[0]), list(m.points[-1]), m.get_left()[0], m.get_right()[0]] for m in (a, d)]\n'),
            [[[-0.5, 0.0, 0.0], [-0.5, 0.0, 0.0], -0.5, -0.15]] * 2)

    def test_closed_line_regenerates_between_new_ends(self):
        # Community 0.22: Line.put_start_and_end_on (also via pop_tips and Arrow.scale)
        # regenerates a straight path when the own ends coincide exactly.
        self.assertEqual(scene_values(
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        l = Line(LEFT, RIGHT); l.become(Square()); l.put_start_and_end_on(LEFT, UP)\n'
            '        v = Vector(UP + RIGHT); self.play(Transform(v, Square().shift(LEFT)), run_time=0.2)\n'
            '        a, b = v.copy(), v.copy(); a.scale(0.5); b.put_start_and_end_on(LEFT, RIGHT)\n'
            '        self.out = [[len(m.points), list(m.points[0]), list(m.points[-1])] for m in (l, a, b)]\n'
            's = S(); s.render(); result = s.out\n'),
            [[4, [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], [4, [-0.25, 0.75, 0.0], [-0.75, 0.25, 0.0]],
             [4, [-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]])

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

    def test_rotated_circles_bound_their_cubic_points(self):
        self.assertEqual(scene_values(
            'result = [Circle().rotate(a).width for a in (0.3, 0.7, PI / 8)] + '
            '[Circle().rotate(0.3).get_critical_point(UR)[0]]\n'),
            [2.0674, 2.038, 2.0507, 0.9553])

    def test_arc_transforms_between_similar_shapes_match_community(self):
        self.assertEqual(scene_values(
            'a = Square(); b = Square(0.5).shift(UR).rotate(0.4)\n'
            't = Transform(a, b, path_arc=-PI); t.begin(); t.interpolate(0.5)\n'
            'c = Circle(); d = Circle(radius=0.3).shift(LEFT * 2)\n'
            'u = Transform(c, d, path_arc=PI / 2); u.begin(); u.interpolate(0.25)\n'
            'result = [a.get_center(), a.width, a.get_start(), c.get_center(), c.get_start()]\n'),
            [[0.0, 1.0, 0.0], 1.8053, [0.9026, 1.2303, 0.0], [-0.116, 0.1038, 0.0], [0.8435, 0.1402, 0.0]])

    def test_arrow_scaling_keeps_tips_and_resets_width_from_the_shaft(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1], m.get_stroke_width()]\n'
            'r = [b(Arrow(LEFT, RIGHT * 2).scale(k)) for k in (0, 0.3, 0.001)]\n'
            'a = Arrow(LEFT, RIGHT * 2).scale(0.3)\n'
            'r.append([a.tip.width, a.get_tip().get_center()[0]])\n'
            'r.append(b(Arrow(DL, UR * 2).scale(0.5, about_edge=UL)))\n'
            'r.append(b(Arrow(LEFT, RIGHT).put_start_and_end_on(UP, UP + RIGHT * 0.5)))\n'
            'result = r\n'),
            [[0.5, -0.175, 0.85, 0.175, 0.0], [0.125, -0.175, 0.875, 0.175, 2.0],
             [0.1512, -0.175, 0.5012, 0.175, 1.7375], [0.35, 0.7],
             [-0.8232, 0.5, 0.5, 1.8232, 6.0], [0.0, 0.825, 0.5, 1.175, 0.75]])

    def test_arrow_growth_and_arc_paths_move_tips_pointwise_in_world_space(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'r = []\n'
            'for anim, alpha in ((GrowFromCenter, 0.3), (SpinInFromNothing, 0.4), (ShrinkToCenter, 0.7)):\n'
            '    m = Arrow(LEFT, RIGHT * 2)\n'
            '    a = anim(m); a.begin(); a.interpolate(alpha)\n'
            '    r.append(b(m))\n'
            'm = Arrow(LEFT, RIGHT); t = Arrow(UP * 2, UP * 2 + RIGHT * 3).rotate(0.5)\n'
            'a = Transform(m, t, path_arc=-2); a.begin(); a.interpolate(0.4)\n'
            'r.append(b(m.tip))\n'
            'result = r\n'),
            [[0.2024, -0.1351, 0.7577, 0.1351], [0.2091, -0.3462, 0.8382, 0.2612],
             [0.3575, -0.1351, 0.9127, 0.1351], [0.3144, 0.8063, 0.6344, 1.1113]])

    def test_members_of_a_family_collapse_into_a_childless_target_center(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'r = []\n'
            'for alpha in (0.2, 0.5, 0.9):\n'
            '    m = Arrow(LEFT, RIGHT * 2)\n'
            '    a = Transform(m, Star().shift(RIGHT)); a.begin(); a.interpolate(alpha)\n'
            '    r.append(b(m.submobjects[0]))\n'
            'result = r\n'),
            [[1.3835, -0.1638, 1.719, 0.1717], [1.2, -0.0398, 1.375, 0.1352], [1.0046, 0.0924, 1.0086, 0.0964]])

    def test_turning_posed_families_move_members_in_straight_lines(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'r = []\n'
            'for m in (DashedLine(LEFT, RIGHT * 2), NumberLine(x_range=[0, 4, 1], length=4)):\n'
            '    a = Transform(m, m.copy().shift(RIGHT).rotate(0.5)); a.begin(); a.interpolate(0.4)\n'
            '    r.append(b(m))\n'
            'result = r\n'),
            [[-0.6854, -0.1912, 2.217, 0.1912], [-1.6819, -0.3516, 2.2135, 0.3516]])

    def test_curved_arrows_draw_partially_along_their_trimmed_shaft(self):
        self.assertEqual(scene_values(
            'r = []\n'
            'for t in (0.1, 0.4, 0.6):\n'
            '    m = CurvedArrow(LEFT, RIGHT)\n'
            '    m.pointwise_become_partial(m.copy(), 0, t)\n'
            '    p = m.get_points()\n'
            '    r.append([min(q[1] for q in p), p[-1], len(p)])\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        m = CurvedArrow(LEFT, RIGHT)\n'
            '        self.bottoms = []\n'
            '        self.add_updater(lambda dt: self.bottoms.append(m.get_bottom()[1]))\n'
            '        self.play(Create(m))\n'
            's = S(); s.render()\n'
            'r.append([s.bottoms[k] for k in (3, 4, 8, 11)])\n'
            'result = r\n'),
            [[-0.1472, [-0.87, -0.1472, 0.0], 4.0], [-0.4441, [-0.3667, -0.4441, 0.0], 16.0],
             [-0.4999, [0.021, -0.4988, 0.0], 20.0], [-0.3409, -0.4989, -0.497, -0.497]])

    def test_spiral_in_moves_arrow_tips_in_world_space(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'm = Arrow(LEFT, RIGHT * 2)\n'
            'a = SpiralIn(m, rate_func=linear); a.begin(); a.interpolate(0.1)\n'
            'n = Arrow(LEFT, RIGHT * 2)\n'
            'n.rotate(0.6, about_point=[0.5, 0, 0])\n'
            'c = n.get_center_of_mass()\n'
            'n.rotate(-0.6, about_point=c)\n'
            'result = [b(m), b(m.tip), m.get_start(), c, n.get_start()]\n'),
            [[-0.8873, 0.4225, 7.8176, 5.322], [7.4676, 4.972, 7.8176, 5.322],
             [-0.8873, 0.4225, 0.0], [1.0932, 0.4058, 0.0], [-0.8755, 0.4058, 0.0]])

    def test_animations_of_one_object_begin_in_order_and_the_running_one_wins(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        m = Square()\n'
            '        self.r = []\n'
            '        self.add_updater(lambda dt: self.r.append(b(m)))\n'
            '        self.add(m)\n'
            '        self.play(m.animate.shift(RIGHT), Rotate(m, PI / 4), run_time=0.5)\n'
            '        self.play(AnimationGroup(Rotate(m, PI / 3, run_time=2), m.animate.shift(UP)), run_time=1)\n'
            '        self.play(LaggedStart(FadeOut(m), FadeIn(m), lag_ratio=0.3), run_time=0.7)\n'
            '        self.play(AnimationGroup(Create(m), Indicate(m), lag_ratio=0.5))\n'
            's = S(); s.render()\n'
            'result = [s.r[k] for k in (7, 13, 17, 22)] + [b(s.mobjects[0])]\n'),
            [[-1.4142, -1.4142, 1.4142, 1.4142], [-1.4142, -0.5685, 1.4142, 2.26],
             [-1.0164, -1.0164, 1.0164, 1.0164], [-1.22, -1.22, 1.22, 1.22], [0.0, 2.4142, 0.0, 2.4142]])

    def test_transform_matching_shapes_keeps_parts_in_the_scene(self):
        self.assertEqual(scene_values(
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        self.r = []\n'
            '        m = VGroup(DashedLine(LEFT, RIGHT * 2), Square().scale(0.5).shift(UP * 2))\n'
            '        self.add(m)\n'
            '        def record(dt):\n'
            '            roots = [r for r in self.mobjects if r.family_members_with_points()]\n'
            '            self.r.append([min(r.get_left()[0] for r in roots), min(r.get_bottom()[1] for r in roots),\n'
            '                           max(r.get_right()[0] for r in roots), max(r.get_top()[1] for r in roots)])\n'
            '        self.add_updater(record)\n'
            '        self.play(TransformMatchingShapes(m, VGroup(Square(), Circle()).arrange(DOWN)))\n'
            's = S(); s.render()\n'
            'result = [s.r[k] for k in (0, 4, 8, 12)] + [len(s.mobjects)]\n'),
            [[-1.0, -2.125, 2.0, 2.5], [-1.0414, -2.125, 1.9586, 2.4689], [-1.2918, -2.125, 1.7082, 2.2811],
             [-1.4794, -2.125, 1.5206, 2.1405], 1])

    def test_passing_flash_cuts_arrow_shafts_and_tips(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'a = Arrow(LEFT, RIGHT * 2)\n'
            'f = ShowPassingFlash(a, time_width=0.5, rate_func=linear); f.begin(); f.interpolate(0.5)\n'
            'c = Arrow(LEFT, RIGHT * 2)\n'
            'for m in c.family_members_with_points():\n'
            '    m.pointwise_become_partial(m.copy(), 0, 0)\n'
            'r = [b(a), b(a.tip), c.get_end(), c.get_length()]\n'
            'c.scale(1.2)\n'
            'result = r + [b(c)]\n'),
            [[-0.2125, -0.175, 1.4875, 0.175], [1.4, -0.175, 1.4875, 0.175], [1.75, 0.0, 0.0], 2.5,
             [-1.0, 0.0, 2.0, 0.0]])

    def test_curved_arrows_morph_their_drawn_shaft_into_other_shapes(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        m = CurvedArrow(LEFT, RIGHT)\n'
            '        self.r = []\n'
            '        self.add(m)\n'
            '        self.add_updater(lambda dt: self.r.append(b(m)))\n'
            '        self.play(Transform(m, Star().shift(RIGHT)))\n'
            's = S(); s.render()\n'
            'xs = [p[0] for f in s.frames for root in f["mobjects"] for c in [root] + root["children"]\n'
            '      for curve in c.get("shaft_curves") or c.get("curves") or [] for p in curve]\n'
            'result = [s.r[k] for k in (0, 4, 8, 12)] + [min(xs) > -1.01]\n'),
            [[-1.0, -0.4979, 1.0, 0.0], [-0.8344, -0.5237, 1.0, 0.0828], [-0.3186, -0.6795, 1.2689, 0.5837],
             [0.0125, -0.7962, 1.8834, 0.9587], True])

    def test_number_lines_morph_their_shaft_as_their_own_points(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        m = NumberLine(x_range=[0, 4, 1], length=4)\n'
            '        self.r = []\n'
            '        self.add(m)\n'
            '        self.add_updater(lambda dt: self.r.append(b(m)))\n'
            '        self.play(Transform(m, Star().shift(RIGHT)))\n'
            's = S(); s.render()\n'
            'result = [s.r[k] for k in (5, 7, 10)]\n'),
            [[-1.5373, -0.1248, 1.8458, 0.1542], [-0.7511, -0.3368, 1.5837, 0.4163],
             [-0.1437, -0.6842, 1.8352, 0.8458]])

    def test_number_line_unwrite_and_scaled_circle_morphs_follow_community(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        m = NumberLine(x_range=[0, 4, 1], length=4)\n'
            '        self.r = []\n'
            '        self.add(m)\n'
            '        self.add_updater(lambda dt: self.r.append(b(m)[3]))\n'
            '        self.play(Unwrite(m, rate_func=linear))\n'
            's = S(); s.render()\n'
            'c = Circle().rotate(1).scale(0.5)\n'
            'a = Transform(c, Circle(2).shift(UP), rate_func=linear); a.begin(); a.interpolate(0.25)\n'
            'result = [s.r[len(s.r) * k // 10] for k in (7, 8)] + [b(c)]\n'),
            [0.1, 0.06, [-0.72, -0.47, 0.72, 0.97]])

    def test_config_frame_dimensions_are_independent_and_cameras_keep_the_width(self):
        self.assertEqual(scene_values(
            'out = []\n'
            'with tempconfig({"frame_height": 10}) as config:\n'
            '    s = Scene()\n'
            '    out.append([config.frame_width, config.frame_height, config.top[1], Axes().x_range[0],\n'
            '                s.camera.frame_width, s.camera.frame_height])\n'
            'with tempconfig({"frame_x_radius": 100, "frame_y_radius": 200}) as config:\n'
            '    s = Scene()\n'
            '    out.append([config.frame_width, config.frame_height, s.camera.frame_width, s.camera.frame_height])\n'
            'with tempconfig({"frame_size": (1080, 1080)}) as config:\n'
            '    s = Scene()\n'
            '    out.append([config.pixel_width, config.frame_height, s.camera.frame_width, s.camera.frame_height])\n'
            'result = out\n'),
            [[14.2222, 10.0, 5.0, -7.0, 14.2222, 8.0], [200.0, 400.0, 200.0, 112.5],
             [1080.0, 8.0, 14.2222, 14.2222]])

    def test_animation_copies_and_targets_keep_updating(self):
        # Expected values from Manim 0.22 at frame_rate = 15.
        result = scene_values(
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        a = Square(); a.add_updater(lambda x, dt: x.shift(RIGHT*dt))\n'
            '        self.play(FadeIn(a, shift=UP))\n'
            '        b = Circle(); b.add_updater(lambda x, dt: x.rotate(dt))\n'
            '        self.play(Create(b))\n'
            '        c = Square(); d = Circle().shift(UP); d.add_updater(lambda x, dt: x.shift(LEFT*dt))\n'
            '        self.add(c); self.play(ReplacementTransform(c, d))\n'
            '        t = ValueTracker(0); t.add_updater(lambda x, dt: x.increment_value(dt)); self.add(t)\n'
            '        before = self.renderer.time\n'
            '        self.wait_until(lambda: t.get_value() > 0.5)\n'
            '        self.r = [a.get_center(), b.width, d.get_center(), round(self.renderer.time - before, 4)]\n'
            's = S(); s.render()\n'
            'result = s.r\n')
        self.assertEqual(result, [[3.3333, 0.0, 0.0], 2.0213, [-1.4667, 1.0, 0.0], 0.6])

    def test_rotate_grow_indicate_wiggle_and_paths_follow_updaters(self):
        # Expected values from Manim 0.22 at frame_rate = 15.
        result = scene_values(
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        r = []\n'
            '        def mk():\n'
            '            a = Square(); a.add_updater(lambda x, dt: x.shift(RIGHT*dt)); return a\n'
            '        a = mk(); self.add(a); self.play(Rotate(a, PI/2)); r.append(a.get_center()); self.remove(a)\n'
            '        a = mk(); self.play(SpinInFromNothing(a)); r.append(a.get_center()); self.remove(a)\n'
            '        a = mk(); self.add(a); self.play(Indicate(a)); r.append(a.get_center()); self.remove(a)\n'
            '        a = mk(); self.add(a); self.play(Wiggle(a)); r.append(a.get_center()); self.remove(a)\n'
            '        a = mk(); self.add(a); self.play(FadeOut(a, shift=UP)); r.append(a.get_center())\n'
            '        a = mk(); self.add(a); self.play(MoveAlongPath(a, Circle()), rate_func=linear); r.append(a.get_center())\n'
            '        a = Square(); a.add_updater(lambda x, dt: x.rotate(dt)); self.add(a)\n'
            '        self.play(MoveAlongPath(a, Line(LEFT, RIGHT))); r.append(round(a.width, 4)); self.remove(a)\n'
            '        self.r = r\n'
            's = S(); s.render()\n'
            'result = s.r\n')
        self.assertEqual(result, [[0.9333, 0.0, 0.0]] * 3 + [[1.9333, 0.0, 0.0], [0.9333, 0.0, 0.0],
                                                             [1.0, -0.0, 0.0], 2.7975])

    def test_number_line_layout_keeps_the_shaft_and_arrow_ends_follow_tips(self):
        result = scene_values(
            'n = NumberLine(x_range=[0, 4, 1], length=4).space_out_submobjects(1.5)\n'
            'm = NumberLine(x_range=[0, 4, 1], length=4, include_tip=True).arrange(DOWN)\n'
            'a = Arrow(LEFT, RIGHT*2).space_out_submobjects(1.5)\n'
            'result = [round(n.width, 4), round(n.height, 4), [round(v, 4) for v in m.get_center()],\n'
            '          round(m.height, 4), a.get_end()]\n')
        self.assertEqual(result[:4], [6.0, 0.2, [0.0, 0.0, 0.0], 0.8])
        self.assertEqual([abs(v) for v in result[4]], [2.3167, 0.0, 0.0])

    def test_frame_updaters_run_only_once_the_frame_is_in_the_scene(self):
        result = scene_values(
            'class S(MovingCameraScene):\n'
            '    def construct(self):\n'
            '        m = Square().shift(LEFT)\n'
            '        self.add(m)\n'
            '        self.camera.frame.add_updater(lambda f: f.move_to(m))\n'
            '        self.play(m.animate.shift(RIGHT * 3), run_time=0.5)\n'
            '        self.before = self.camera.frame.get_center()\n'
            '        self.add(self.camera.frame)\n'
            '        self.play(m.animate.shift(UP), run_time=0.5)\n'
            '        self.after = self.camera.frame.get_center()\n'
            's = S(); s.render()\n'
            'result = [s.before, s.after]\n')
        self.assertEqual(result, [[0.0, 0.0, 0.0], [2.0, 1.0, 0.0]])

    def test_depth_layout_stretch_and_polyhedron_become(self):
        result = scene_values(
            'c = Cube(side_length=1).next_to(Dot3D([0, 0, 2]), OUT)\n'
            's = Square().next_to(Cube(side_length=1).shift(UP), IN, buff=0.5, aligned_edge=LEFT)\n'
            'g = VGroup(Square(0.5), Circle(0.3), Triangle().scale(0.3)).arrange(OUT, buff=0.4)\n'
            'h = VGroup(Cube(side_length=0.5), Cube(side_length=0.6)).arrange(IN + RIGHT)\n'
            'd = Dot3D([1, 1, 1]).stretch(1.5, 0)\n'
            'e = Cube(side_length=1).shift(RIGHT + OUT).stretch(2, 2)\n'
            'class S(ThreeDScene):\n'
            '    def construct(self):\n'
            '        t = Tetrahedron()\n'
            '        self.add(t)\n'
            '        self.play(t.animate.become(Cube(side_length=0.5).shift(LEFT)), run_time=0.5)\n'
            '        self.final = t.get_center()\n'
            'scene = S(); scene.render()\n'
            'result = [c.get_center(), s.get_center(), [m.get_center() for m in g], [m.get_center() for m in h],\n'
            '          d.get_center(), d.width, e.get_center(), e.depth, scene.final]\n')
        self.assertEqual(result, [
            [0.0, 0.0, 2.83], [0.5, 1.0, -1.0], [[0.0, 0.0, -0.4], [0.0, 0.0, 0.0], [0.0, 0.0, 0.4]],
            [[-0.425, 0.0, 0.425], [0.375, 0.0, -0.375]], [1.0, 1.0, 1.0], 0.24, [1.0, 0.0, 1.0], 2.0, [-1.0, 0.0, 0.0]])

    def test_out_of_plane_fades_growth_and_indicate(self):
        result = scene_values(
            'class S(ThreeDScene):\n'
            '    def construct(self):\n'
            '        cube, ring, dot = Cube(side_length=1), Circle().shift(OUT), Dot3D([1, 1, 1])\n'
            '        self.r = []\n'
            '        self.add_updater(lambda dt: self.r.append([cube.get_z(), ring.width, dot.get_center()]))\n'
            '        self.play(FadeIn(cube, shift=OUT), GrowFromCenter(ring), GrowFromCenter(dot), run_time=1)\n'
            '        self.play(Indicate(ring), FadeOut(cube, target_position=[0, 0, 2]), run_time=1)\n'
            's = S(); s.render()\n'
            'result = [s.r[7], s.r[22], s.r[-1][2]]\n')
        self.assertEqual(result[0][0], -0.5837)
        self.assertEqual(result[0][2], [1.0, 1.0, 1.0])
        self.assertGreater(result[0][1], 0.5)
        self.assertLess(result[0][1], 2)
        self.assertGreater(result[1][1], 2.3)
        self.assertGreater(result[1][0], 0.5)

    def test_dashed_line_tips_refit_the_dashes(self):
        result = scene_values(
            'def bounds(m):\n'
            '    return [m.get_left()[0], m.get_right()[0], m.get_top()[1], m.get_bottom()[1]]\n'
            'm = DashedLine(LEFT*2, RIGHT*2, dash_length=0.2).add_tip()\n'
            'a = [len(m.submobjects), bounds(m), m.get_end(), m.submobjects[-2].get_end()]\n'
            'm3 = DashedLine(LEFT*2, RIGHT*2, dash_length=0.2).add_tip().add_tip(at_start=True, tip_length=0.5)\n'
            'b = [m3.submobjects[0].get_start(), m3.submobjects[-3].get_end()]\n'
            'm4 = DashedLine(LEFT, UR*2, dash_length=0.3).rotate(0.4).shift(DOWN).add_tip(tip_shape=StealthTip)\n'
            'm5 = DashedLine(LEFT*2, RIGHT*2, dash_length=0.2).add_tip()\n'
            'm5.put_start_and_end_on(DOWN, UP*2)\n'
            'm6 = DashedLine(LEFT*2, RIGHT*2, dash_length=0.2).add_tip()\n'
            'tips = m6.pop_tips()\n'
            'result = [a, b, bounds(m4), m4.get_end(), bounds(m5), m5.submobjects[-1].get_center(),\n'
            '          len(m6.submobjects), len(tips), m6.get_end()]\n')
        self.assertEqual(result, [
            [11.0, [-2.0, 2.0, 0.175, -0.175], [2.0, 0.0, 0.0], [1.65, 0.0, 0.0]],
            [[-1.5, 0.0, 0.0], [1.6938, 0.0, 0.0]],
            [-0.4922, 1.4922, 1.5052, -1.5052], [1.4922, 1.5052, 0.0],
            [-0.1313, 0.1312, 2.0, -1.0], [0.0, 1.8687, 0.0], 10.0, 1.0, [2.0, 0.0, 0.0]])

    def test_background_rectangles_fade_in_instead_of_tracing(self):
        frames = json.loads(lite.render_scene(
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        self.play(Create(BackgroundRectangle(Circle(), fill_opacity=0.5)))\n'))['frames']
        shape = frames[len(frames) // 2]['mobjects'][0]
        self.assertNotIn('draw_progress', shape)
        self.assertGreater(shape['fill_opacity'], 0)
        self.assertLess(shape['fill_opacity'], 0.5)
        self.assertEqual(scene_values(
            'r = BackgroundRectangle(Square(), fill_opacity=0.6)\n'
            'r.pointwise_become_partial(r.copy(), 0, 0.5)\n'
            'result = [r.get_fill_opacity(), r.width]\n'), [0.3, 2.0])

    def test_reshaped_curved_arrows_move_their_drawn_shaft_pointwise(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        m = CurvedArrow(LEFT, RIGHT)\n'
            '        self.r = []\n'
            '        self.add(m)\n'
            '        self.add_updater(lambda dt: self.r.append(b(m)))\n'
            '        self.play(m.animate.reverse_points())\n'
            's = S(); s.render()\n'
            'result = [s.r[k] for k in (4, 7, 12)]\n'),
            [[-0.8549, -0.4914, 1.0, 0.0], [-0.2704, -0.4867, 1.0, 0.0], [-0.9276, -0.4942, 1.0, 0.0]])

    def test_succession_stages_updater_time_and_image_depths(self):
        self.assertEqual(scene_values(
            'line = Line()\n'
            's = Succession(FadeIn(line, run_time=1), FadeOut(line, run_time=4))\n'
            'before = hasattr(s, "active_animation")\n'
            's._setup_scene(None); s.begin()\n'
            'stages = []\n'
            'for alpha in (0.1, 0.2, 1.0):\n'
            '    s.interpolate(alpha); stages.append(s.active_index)\n'
            'a = FadeIn(Circle(), run_time=0)\n'
            'turn_animation_into_updater(a)\n'
            'a.mobject.update(0.1)\n'
            'image = ImageMobject([[[1000, 2000, 65535, 7]]], pixel_array_dtype="uint16", invert=True)\n'
            'result = [before, stages, s.active_animation is None, a.total_time >= 0, len(a.mobject.updaters),\n'
            '          [list(map(int, p)) for p in image.get_pixel_array()[0]]]\n'),
            [False, [0, 1, 2], True, True, 0, [[64535, 63535, 0, 7]]])

    def test_animation_updaters_draw_partial_outlines(self):
        self.assertEqual(scene_values(
            'def b(m):\n'
            '    return [m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]]\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        m = Square()\n'
            '        n = VGroup(Circle(), Square().shift(RIGHT * 3))\n'
            '        self.r = []\n'
            '        turn_animation_into_updater(Create(m, run_time=0.9))\n'
            '        turn_animation_into_updater(Write(n, run_time=0.9))\n'
            '        self.add(m, n)\n'
            '        self.add_updater(lambda dt: self.r.append(b(m) + b(n)))\n'
            '        self.wait(0.5)\n'
            '        self.wait(0.6)\n'
            's = S(); s.render()\n'
            'result = [s.r[k] for k in (2, 4, 7)]\n'),
            [[0.9413, 1.0, 1.0, 1.0, 0.438, 0.0, 4.0, 1.0],
             [0.5796, 1.0, 1.0, 1.0, -1.0, -0.2088, 4.0, 1.0],
             [-1.0, 0.0981, 1.0, 1.0, -1.0, -1.0, 4.0, 1.0]])

    def test_rotate_fixes_its_pivot_when_constructed(self):
        self.assertEqual(scene_values(
            's = Square()\n'
            'a = Rotate(s, PI / 2, about_edge=UR); a.begin(); a.interpolate(1)\n'
            't = Square()\n'
            'b = Rotating(t, angle=PI / 2, about_edge=UR); b.begin(); b.interpolate(1)\n'
            'u = Square()\n'
            'c = Rotate(u, PI)\n'
            'u.shift(RIGHT)\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        self.play(c)\n'
            'S().render()\n'
            'result = [s.get_center(), t.get_center(), u.get_center()]\n'),
            [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])

    def test_lagged_start_map_animates_shapes_once_with_their_children(self):
        self.assertEqual(scene_values(
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        a = Arrow(LEFT, RIGHT)\n'
            '        self.add(a)\n'
            '        g = LaggedStartMap(FadeOut, a)\n'
            '        self.play(g)\n'
            '        self.count = [len(g.animations), len(self.mobjects)]\n'
            's = S(); s.render()\n'
            'result = s.count\n'),
            [1.0, 0.0])

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

    def test_next_to_submobject_alignment_and_coordinate_mask(self):
        self.assertEqual(scene_values(
            'g = VGroup(Square(0.5), Circle(0.3).shift(UP * 2))\n'
            'result = [VGroup(Square(0.5), Circle(0.3)).next_to(VGroup(Dot(), Dot(RIGHT * 3)), DOWN,'
            ' index_of_submobject_to_align=1).get_center(),\n'
            '          g.next_to(Square(2), RIGHT, submobject_to_align=g[1]).get_center(),\n'
            '          Square(1).shift(UP * 2).next_to(Square(2), RIGHT, coor_mask=[1, 0, 0]).get_center()]\n'),
            [[3.0, -0.63, 0.0], [1.55, -0.975, 0.0], [1.75, 2.0, 0.0]])

    def test_animation_names_wait_duration_and_manual_update_functions(self):
        self.assertEqual(scene_values(
            's = Square()\n'
            'a = UpdateFromAlphaFunc(s, lambda m, a: m.move_to(RIGHT * a * 4))\n'
            'a.begin()\n'
            'a.interpolate(0.25)\n'
            'result = [str(FadeIn(Square())), repr(Transform(Square(), Circle())),'
            ' str(AnimationGroup(FadeIn(Square()))), str(FadeIn(Square(), name="x")), str(Wait()),'
            ' Wait(2).duration, s.get_x(), Axes().x_length, Axes(y_length=5).y_length]\n'),
            ['FadeIn(Square)', 'Transform(Square)', 'AnimationGroup(Group)', 'x', 'Wait(Mobject)',
             2.0, 0.2804, 12.0, 5.0])

    def test_plain_scene_camera_frame_center(self):
        frames = json.loads(lite.render_scene(
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        self.add(Square())\n'
            '        self.wait(0.1)\n'
            '        self.camera.frame_center = RIGHT * 2\n'
            '        self.wait(0.1)\n'))['frames']
        self.assertNotIn('frame_center', frames[0]['camera'])
        self.assertEqual(frames[-1]['camera']['frame_center'], [2, 0, 0])
        self.assertEqual(scene_values('result = Scene().camera.frame_center\n'), [0.0, 0.0, 0.0])

    def test_buff_equal_to_half_the_length_collapses_lines_and_arrows(self):
        self.assertEqual(scene_values(
            'a = Arrow(ORIGIN, RIGHT * 0.5)\n'
            'result = [a.get_start(), a.get_end(), a.tip.length, a.get_stroke_width(),'
            ' Line(ORIGIN, RIGHT * 0.5, buff=0.25).get_length(), DoubleArrow(ORIGIN, RIGHT * 0.5).width]\n'),
            [[0.25, 0.0, 0.0], [0.25, 0.0, 0.0], 0.0, 0.0, 0.0, 0.0])

    def test_parametric_function_scaling_maps_sample_inputs(self):
        self.assertEqual(scene_values(
            'g = ParametricFunction(lambda t: (math.log10(t), t / 50, 0), t_range=[0, 2, 0.5], scaling=LogBase())\n'
            'result = [g.get_start(), g.get_end(), len(g.get_points())]\n'.replace('math.log10', '__import__("math").log10')),
            [[0.0, 0.02, 0.0], [2.0, 2.0, 0.0], 16.0])

    def test_text_attributes_follow_community(self):
        self.assertEqual(scene_values(
            't = Text("Hi\\nyo", font_size=30)\n'
            'm = MarkupText("<b>ab</b>\\nc")\n'
            'result = [t.text, t.original_text, t.line_spacing, Text("Hi", line_spacing=2).line_spacing,'
            ' Text("Hi").font, Text("Hi", font="Arial").font, Text("Hi").slant, Text("Hi").weight,'
            ' Text("abc", t2c={"b": RED}).t2c, Text("a").t2w, m.text, m.original_text]\n'),
            ['Hiyo', 'Hi\nyo', 39.0, 144.0, '', 'Arial', 'NORMAL', 'NORMAL', {'b': '#FC6255'}, {},
             '<b>ab</b>c', '<b>ab</b>\nc'])

    def test_space_utilities_and_3d_vmobject_corners(self):
        self.assertEqual(scene_values(
            'result = [get_3d_vmob_start_corner(Square()), get_3d_vmob_end_corner(Square()),'
            ' get_3d_vmob_end_corner_index(Square()),'
            ' get_3d_vmob_start_corner_unit_normal(Square().rotate(0.4, RIGHT)),'
            ' get_3d_vmob_end_corner_unit_normal(Polygon(ORIGIN, RIGHT, UP + OUT)),'
            ' get_3d_vmob_unit_normal(Line(), 0),'
            ' shoelace([[0, 0], [1, 0], [1, 1], [0, 1]]), shoelace_direction(Square().get_start_anchors()),'
            ' bezier([0, 1, 3])(0.4), bezier([[0, 0], [1, 2], [3, 1]])(0.3), center_of_mass([1, 2, 6])]\n'),
            [[1.0, 1.0, 0.0], [-1.0, -0.3333, 0.0], 6.0, [0.0, -0.3894, 0.9211],
             [0.0, -0.7071, 0.7071], [0.0, 1.0, 0.0], -1.0, 'CCW', 0.96, [0.69, 0.93], 3.0])

    def test_family_anchor_modes_tip_polygons_and_container_paths(self):
        self.assertEqual(scene_values(
            'a = Arrow(); a.make_smooth()\n'
            's = Square().rotate(0.3); s.add(Triangle().scale(0.5).shift(RIGHT * 2)); s.make_smooth()\n'
            't = ArrowSquareTip(); t.round_corners(0.05)\n'
            'g = VGroup(Square())\n'
            'p = PGroup(PointCloudDot(), PointCloudDot().shift(RIGHT)); n = len(p.get_all_points())\n'
            'p.ingest_submobjects()\n'
            'result = [a.height, a.tip.get_points()[1], s.width, s.height, s[1].get_points()[1],'
            ' ArrowSquareTip().get_vertices(), len(ArrowTriangleTip().get_vertex_groups()),'
            ' isinstance(ArrowTriangleTip(), Triangle), isinstance(ArrowSquareTip(), Square),'
            ' t.width, t.get_num_points(), g.has_new_path_started(), g.get_direction(),'
            ' g.reverse_direction() is g, g.clear_points() is g, ArcPolygon().width,'
            ' ValueTracker(2).set_color().get_value(), len(Square().get_points_defining_boundary()),'
            ' len(VGroup(Square(), Circle()).get_points_defining_boundary()),'
            ' PMobject().get_array_attrs(), len(p.submobjects), len(p.get_points()), n]\n'),
            [0.4667, [0.75, 0.1167, 0.0], 4.1581, 3.1615, [1.7113, 0.625, 0.0],
             [[0.175, 0.175, 0.0], [-0.175, 0.175, 0.0], [-0.175, -0.175, 0.0], [0.175, -0.175, 0.0]],
             1.0, True, True, 0.35, 32.0, False, 'CCW', True, True, 0.0, 2.0, 8.0, 24.0,
             ['points', 'rgbas'], 0.0, 2606.0, 2606.0])
        with self.assertRaises(TypeError):
            scene_values('result = Square().set_color()\n')

    def test_arc_bounds_use_cubic_points_and_corner_points_are_world(self):
        self.assertEqual(scene_values(
            'a = Arc(radius=2, start_angle=0.2, angle=2)\n'
            'b = Arc(radius=1.5, start_angle=-1, angle=-3).rotate(0.4).scale(1.3).shift(RIGHT)\n'
            's = Square().rotate(0.3).shift(LEFT); s.set_points_as_corners([LEFT, UP, RIGHT])\n'
            'c = Circle().scale(2).shift(UP); c.set_points_smoothly([LEFT, UP, RIGHT])\n'
            'result = [a.get_center(), a.width, a.height, a.get_top(), b.get_center(), b.height,'
            ' b.get_corner(UL), Arc(angle=2).height, s.get_center(), s.height, s.get_points()[0],'
            ' c.get_center(), c.width, c.height]\n'),
            [[0.3916, 1.1914, 0.0], 3.1371, 1.6082, [0.3916, 1.9854, 0.0], [0.7784, -0.2901, 0.0],
             2.8273, [-0.9979, 1.1048, 0.0], 1.0034, [0.0, 0.5, 0.0], 1.0, [-1.0, 0.0, 0.0],
             [0.0, 0.5, 0.0], 2.0, 1.0])

    def test_posed_path_appends_ellipse_proportions_and_empty_member_depth(self):
        self.assertEqual(scene_values(
            'e = Elbow(width=0.5, angle=0.3); e.add_line_to(UP)\n'
            'q = RoundedRectangle(corner_radius=0.3, width=3, height=2).rotate(0.2)\n'
            'q.add_quadratic_bezier_curve_to(RIGHT * 2, UP)\n'
            'o = Ellipse(width=3, height=1).rotate(0.5).shift(DOWN)\n'
            'p = NumberPlane(); p.shift(OUT * 0.5)\n'
            'result = [e.get_center(), e.width, e.height, e.get_points()[-1], q.width, q.get_points()[-1],'
            ' Ellipse(width=3, height=1).point_from_proportion(0.3), o.point_from_proportion(0.08),'
            ' p.get_z()]\n'),
            [[0.165, 0.5739, 0.0], 0.6254, 0.8522, [0.0, 1.0, 0.0], 3.4191, [0.0, 1.0, 0.0],
             [-0.3636, 0.4851, 0.0], [0.8477, -0.1679, 0.0], 0.5])

    def test_compiled_animation_data_moving_members_and_empty_brace(self):
        self.assertEqual(scene_values(
            's = Scene(); a = Circle().set_z_index(1); b = Circle().set_z_index(1)\n'
            'l = Line().set_z_index(-1); s.add(a, b)\n'
            's.compile_animation_data(Succession(b.animate.set_fill(opacity=1), ShowPassingFlash(l)))\n'
            's.begin_animations()\n'
            's2 = Scene(); child = Square(); parent = Circle().add(child); other = Square()\n'
            's2.add(other, parent); s2.compile_animation_data(child.animate.shift(RIGHT))\n'
            's2.begin_animations()\n'
            's3 = Scene(); s3.add(Square())\n'
            'from manim.utils.family import extract_mobject_family_members\n'
            'result = [a in s.moving_mobjects, len(s.moving_mobjects), len(s.static_mobjects),'
            ' parent in s2.moving_mobjects, other in s2.static_mobjects, len(s2.moving_mobjects),'
            ' len(s2.static_mobjects), s3.compile_animation_data(Wait()) is None, s2.duration,'
            ' Brace(Mobject()).width, Brace(Mobject()).get_center(),'
            ' len(VMobject().set_points([UP] * 3).get_points()),'
            ' len(extract_mobject_family_members([parent, other], only_those_with_points=True))]\n'),
            [True, 3, 0, True, True, 2, 1, True, 1.0, 0.0, [0.0, -0.3365, 0.0], 3, 3])
        self.assertEqual(scene_values(
            'from manim.mobject.opengl.opengl_compatibility import ConvertToOpenGL\n'
            'from manim.utils.color.XKCD import GREEN as XGREEN\n'
            'class Blob(VMobject, metaclass=ConvertToOpenGL):\n'
            '    pass\n'
            'result = [Blob in ConvertToOpenGL._converted_classes, isinstance(Blob(), VMobject),'
            ' XGREEN.to_hex()]\n'), [True, True, '#15B01A'])
        with self.assertRaises(ImportError):
            scene_values('from manim.utils.qhull import NoSuchHull\nresult = 0\n')
        if HAS_NUMPY:
            self.assertEqual(scene_values(
                'from manim.utils.qhull import QuickHull\n'
                'h = QuickHull(); h.build(np.array([[0, 0], [2, 0], [0, 2], [2, 2], [1, 1]], dtype=float))\n'
                'result = len(set(h.facets) - h.removed)\n'), 4)

    def test_earclip_triangulation_and_any_length_normalize(self):
        values = scene_values(
            'v = [[-2,-2,0],[2,-2,0],[2,2,0],[-2,2,0],[-1.5,-1.5,0],[-1.5,-0.5,0],[-0.5,-0.5,0],[-0.5,-1.5,0]]\n'
            't = earclip_triangulation(v, [4, 8])\n'
            'def area(i, j, k):\n'
            '    (a, b, c) = (v[i], v[j], v[k])\n'
            '    return abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])) / 2\n'
            'u = [[0,0,0],[2,0,0],[2,1,0],[1,0.5,0],[0,1,0]]\n'
            'w = earclip_triangulation(u, [5])\n'
            'result = [len(t), sum(area(*t[k:k+3]) for k in range(0, len(t), 3)), len(w),'
            ' list(normalize([3, 4])), list(normalize([0, 0, 0, 0])), normalize([0, 0], fall_back=(1, 2)),'
            ' normalize((0.1, 0.1, 0))]\n')
        self.assertEqual(values, [24, 15.0, 9, [0.6, 0.8], [0.0, 0.0, 0.0, 0.0], [1, 2],
                                  [0.7071, 0.7071, 0.0]])

    def test_deprecation_decorators_warn_and_redirect(self):
        with self.assertLogs('manim', level='WARNING') as logs:
            values = scene_values(
                'from manim.utils.deprecation import deprecated, deprecated_params\n'
                '@deprecated(since="0.7.0", replacement="new_area")\n'
                'def area(r):\n'
                '    return 3 * r * r\n'
                '@deprecated_params(redirections=[("radius", "r")])\n'
                'def size(r=1):\n'
                '    return r\n'
                'result = [area(2), size(radius=5)]\n')
        self.assertEqual(values, [12, 5])
        self.assertEqual([record.getMessage() for record in logs.records], [
            'The function area has been deprecated since 0.7.0 and may be removed in a later version. '
            'Use new_area instead.',
            'The parameter radius of function size has been deprecated and may be removed in a later version.'])

    def test_fade_transform_restores_source_and_appends_target(self):
        # Values from Manim Community 0.22.
        self.assertEqual(plain(scene_values(
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        global result\n'
            '        a = Square().set_fill(RED, 0.5); b = Circle(radius=0.5).shift(UP); x = Dot()\n'
            '        a.save_state(); a.shift(DOWN); t = FadeTransform(a, b); a.shift(LEFT)\n'
            '        self.add(a, x); self.play(t)\n'
            '        roots = [type(m).__name__ for m in self.mobjects]\n'
            '        p = VGroup(Square(), Circle().shift(RIGHT * 2)); self.add(p)\n'
            '        self.play(FadeTransform(p[0], Triangle(), replace_mobject_with_target_in_scene=True))\n'
            '        c = VGroup(Square(), Square()); d = VGroup(*[Circle() for _ in range(5)])\n'
            '        e = Square(); f = VGroup(Circle(), Circle())\n'
            '        self.add(c, e); self.play(FadeTransformPieces(c, d), FadeTransformPieces(e, f))\n'
            '        g = Square(); self.add(g)\n'
            '        self.play(Transform(g, Circle(), replace_mobject_with_target_in_scene=True))\n'
            '        result = [a.get_center(), a.width, a.get_fill_opacity(), roots,\n'
            '                  [type(m).__name__ for m in self.mobjects], len(p),\n'
            '                  [s.get_stroke_opacity() for s in c], c.width,\n'
            '                  [type(m).__name__ for m in e.submobjects], e.width, g in self.mobjects]\n'
            'S().render()\n')),
            [[0.0, -1.0, 0.0], 2.0, 0.5, ['Dot', 'Circle'],
             ['Dot', 'Circle', 'Circle', 'Triangle', 'VGroup', 'VGroup', 'Circle'], 2,
             [1.0, 0.0, 0.0, 1.0, 0.0], 2.0, ['VectorizedPoint', 'VectorizedPoint'], 2.0, False])

    def test_path_options_on_finish_and_group_keywords(self):
        # Values from Manim Community 0.22 (whose AnimationGroup adds a Group root: 3 there).
        src = open(Path(__file__).with_name('fixtures') / 'path_options.py').read()
        self.assertEqual(plain(scene_values(src)), [
            [[0.5, 3.0, 0.0], [0.7071, 3.5, 0.0]], [[0.5, 0.5, 0.0], [1.0, 1.0, 0.0]],
            [[-0.75, 0.0, 0.0], 0.0], [[-0.375, -0.1628, 0.0], 0.75], [2, True], [1.0, 0.0, 0.0]])

    def test_template_names_color_components_tip_and_section_helpers(self):
        # Values from Manim Community 0.22.
        src = open(Path(__file__).with_name('fixtures') / 'api_members.py').read()
        self.assertEqual(plain(scene_values(src)), [
            True, 'Comic Sans MS', '', [0.25, 0.5, 0.8], 0.5, 1.0, [3.175, 0.0, 0.0], True, True,
            [1.0, -1.0, 0.0], 2.4, 0.16, ['a', 'b'], 'intro'])

    def test_text_chars_label_types_and_number_line_label_modes(self):
        values = scene_values(
            'text = Text("ab", disable_ligatures=True)\n'
            'chars = len(Text("fl ligature")._gen_chars())\n'
            'text.submobjects = text.submobjects[:1]\n'
            'try:\n'
            '    text._gen_chars(); error = None\n'
            'except ValueError as e:\n'
            '    error = "glyph" in str(e)\n'
            'typst = Typst("hello")\n'
            'line = NumberLine(x_range=[-1, 1])\n'
            'line.add_labels({0: "origin", 1: 2.5}, label_constructor=MathTex)\n'
            'other = NumberLine(x_range=[-1, 1]).add_labels({0: "x"}, label_constructor=MathTypst)\n'
            'result = [chars, error, Label(typst).rendered_label is typst,\n'
            '          [type(m).__name__ for m in line.labels], type(other.labels[0]).__name__]\n')
        self.assertEqual(values, [10, True, True, ['Tex', 'MathTex'], 'Typst'])

    def test_circle_components_and_corner_radius_lists(self):
        # Manim 0.22: num_components anchors set bounds, centers and sampled proportions;
        # round_corners zips repeated radius lists strictly with each vertex group.
        values = scene_values(
            'c = Circle(num_components=12)\n'
            'd = Circle(num_components=12).rotate(0.3).shift(UP).scale(2)\n'
            'out = []\n'
            'for r in ([0.1, 0.2, 0.3], [0.1, 0.2]):\n'
            '    try:\n'
            '        out.append(Square().round_corners(r).width)\n'
            '    except ValueError:\n'
            '        out.append("error")\n'
            'result = [c.width, c.height, list(c.get_center()), list(d.get_center()), d.width,\n'
            '          list(Circle().point_from_proportion(0.3)), list(Arc(angle=PI, num_components=5).point_from_proportion(0.3)),\n'
            '          len(c.points), out]\n')
        self.assertEqual(values, plain([
            2.0135, 2.0342, [0.0203, 0, 0], [-0.0173, 0.9961, 0], 4.0349,
            [-0.3095, 0.9509, 0], [0.587, 0.8096, 0], 44, ['error', 2]]))

    def test_plain_group_boundary_includes_handles(self):
        # Manim 0.22: Mobject/Group critical points (and so centers, pivots and next_to)
        # use all points, handles included; VGroup uses anchors.
        values = scene_values(
            'def r(v): return [round(float(x), 4) for x in v[:2]]\n'
            'g = Group(Square(), Circle().shift(UP * 2).rotate(0.4))\n'
            'v = VGroup(Square(), Circle().shift(UP * 2).rotate(0.4))\n'
            'm = Mobject().add(Circle().rotate(0.4))\n'
            'g2 = Group(Square(), Circle().shift(UP * 2).rotate(0.4)).scale(2)\n'
            'g3 = Group(Circle().rotate(0.4)); g3.rotate(0.5)\n'
            'd = Dot().next_to(Group(Circle().rotate(0.4)), RIGHT, buff=0)\n'
            'result = [r(g.get_center()), r(g.get_top()), r(g.get_right()), r(v.get_center()), r(v.get_right()),\n'
            '          r(m.get_right()), r(g2.get_center()), r(g2.get_right()), r(g3.get_right()), r(d.get_center()),\n'
            '          round(g.width, 4), round(v.width, 4)]\n')
        self.assertEqual(values, plain([
            [0, 1.0132], [0, 3.0264], [1.0264, 1.0132], [0, 0.9633], [1.0, 0.9633], [1.0264, 0],
            [0, 1.0132], [2.0527, 1.0132], [1.0238, 0], [1.1064, 0], 2.0527, 2.0527]))

    def test_removed_tips_family_and_become_errors(self):
        # Manim 0.22: removing a tip leaves the shaft cut at the tip base (pop_tips restores
        # the ends); get_family has no NumberLine shaft member; become needs interpolate_color.
        values = scene_values(
            'def r(m): return [round(float(x), 3) for x in (*m.get_corner(DL)[:2], *m.get_corner(UR)[:2])]\n'
            'a = DoubleArrow(LEFT, RIGHT * 1.12); a.remove(a.submobjects[0])\n'
            'c = Arrow(LEFT, RIGHT * 2).rotate(0.7).shift(UP); c.remove(c.submobjects[0]); c.rotate(0.3)\n'
            'd = CurvedArrow(LEFT, RIGHT * 2); d.remove(d.submobjects[0])\n'
            'f = Arrow(LEFT, RIGHT); f.remove(f.tip); f.add_tip()\n'
            'errors = []\n'
            'for g in (lambda: Group(Square()).become(Group(Circle())), lambda: Square().become(Group(Circle())),\n'
            '          lambda: ValueTracker(1).become(ValueTracker(3)), lambda: VGroup(Square()).become(VGroup(Circle()))):\n'
            '    try:\n'
            '        g(); errors.append("ok")\n'
            '    except Exception as e:\n'
            '        errors.append(type(e).__name__)\n'
            'line = NumberLine(x_range=[-2, 2, 1], include_tip=True)\n'
            'result = [r(a), r(c), r(d), r(f), [type(m).__name__ for m in line.get_family()], len(Axes().get_family()), errors]\n')
        self.assertEqual(values, plain([
            [-0.75, -0.175, 0.52, 0.175], [-0.215, -0.017, 0.947, 1.792], [-1.0, -0.694, 1.753, 0.0],
            [-0.75, -0.144, 0.4, 0.144],
            ['NumberLine', 'ArrowTriangleFilledTip', 'VGroup', 'Line', 'Line', 'Line', 'Line'], 27,
            ['NotImplementedError', 'AttributeError', 'NotImplementedError', 'ok']]))

    def test_shift_vectors_spacing_and_grid_origin(self):
        # Manim 0.22: shift sums its vectors; space_out shrinks members about their world
        # centers; grid cells grow up and right from the origin before the family recenters.
        values = scene_values(
            'def r(m): return [round(float(x), 3) for x in (*m.get_corner(DL)[:2], *m.get_corner(UR)[:2])]\n'
            'a = Axes(x_range=[-2, 2], y_range=[-1, 1], x_length=1.96, y_length=2).rotate(0.85)\n'
            'a.space_out_submobjects(1.48)\n'
            'c = Square().add(Circle(radius=0.3).shift(RIGHT * 2)); c.arrange_in_grid(buff=0.21)\n'
            'd = Square().add(Circle(radius=0.3).shift(RIGHT * 2), Dot(UP * 2)).rotate(0.5); d.arrange_in_grid(buff=0.21)\n'
            'try:\n'
            '    VGroup().arrange_in_grid(); empty = "ok"\n'
            'except ZeroDivisionError:\n'
            '    empty = "error"\n'
            'result = [list(Square().shift(UP, RIGHT * 2).get_center()), r(a), r(c[1]), [r(m) for m in d.submobjects], empty]\n')
        self.assertEqual(values, plain([
            [2, 1, 0], [-0.756, -0.802, 0.817, 0.736], [0.65, 0.0, 1.25, 0.6],
            [[0.365, 0.26, 0.941, 0.836], [1.18, 0.471, 1.333, 0.624]], 'error']))

    def test_arrow_children_of_scaled_parents_keep_world_tips(self):
        # Attaching to (or removing from) a scaled, rotated parent must not resize the tips.
        values = scene_values(
            'def r(m): return [round(float(x), 3) for x in (*m.get_corner(DL)[:2], *m.get_corner(UR)[:2])]\n'
            'a = Arc(radius=0.69, angle=3.55).scale(2).rotate(0.3); arr = DoubleArrow(LEFT, RIGHT).shift(UR)\n'
            'a.add(arr); inside = r(arr); a.remove(arr)\n'
            'result = [inside, r(arr), r(a)]\n')
        self.assertEqual(values, plain([[0.25, 0.825, 1.75, 1.175], [0.25, 0.825, 1.75, 1.175],
                                        [-1.239, -1.081, 1.437, 1.194]]))

    def test_arrow_shaft_is_cut_once(self):
        # Community cuts the shaft when tips attach: moving or removing a tip, arranging or
        # spacing out the tips leaves it, while Arrow.scale re-cuts at (stretched) tip bases.
        values = scene_values(
            'R = lambda x: [round(float(v), 4) for v in x[:2]]\n'
            'a = Arrow(LEFT*2, RIGHT*2); a.tip.shift(UP)\n'
            'r1 = [R(a.points[0]), R(a.points[-1]), R(a.get_end()), R(a.get_center())]\n'
            'a.scale(2); r1 += [R(a.points[-1]), R(a.tip.get_center())]\n'
            'b = DoubleArrow(LEFT, RIGHT * 2.74); b.rotate(0.93, about_edge=UL)\n'
            'b.stretch_to_fit_height(1.11); b.arrange(RIGHT, buff=0.31); b.space_out_submobjects(1.53)\n'
            'r2 = [R(b.points[0]), R(b.points[-1]), R(b.tip.base), R(b.start_tip.get_center())]\n'
            'v = Vector([1, 1.34]); v.rotate(1.56); v.space_out_submobjects(1.02)\n'
            'c = Arrow(LEFT, RIGHT); c.remove(c.tip)\n'
            'result = [r1, r2, [R(v.points[-1]), R(v.get_center())], [R(c.points[-1]), R(c.get_end())]]\n')
        self.assertEqual(values, plain([
            [[-1.75, 0.0], [1.4, 0.0], [1.75, 1.0], [0.0, 0.5875], [3.1635, 1.4038], [3.3077, 1.4038]],
            [[0.6535, 0.4316], [0.7247, 0.3938], [0.682, 0.4215], [0.7769, 0.3518]],
            [[0.1004, 0.975], [0.5019, 0.6683]], [[0.4, 0.0], [0.4, 0.0]]]))

    def test_number_line_tip_edits_keep_the_cut_shaft(self):
        # A NumberLine's own points end at the tip base; after its tip is removed or moved,
        # n2p follows get_end (the shaft end or the moved tip point), as in Community.
        values = scene_values(
            'R = lambda x: [round(float(v), 4) for v in x[:2]]\n'
            'n = NumberLine(x_range=[-2, 2, 1], length=1.05, include_tip=True)\n'
            'n.remove(n.submobjects[0]); r1 = [R(n.points[-1]), R(n.n2p(2)), R(n.get_right())]\n'
            'm = NumberLine(x_range=[-2, 2, 1], length=1.05, include_tip=True)\n'
            'm.submobjects[0].shift(UL * .93)\n'
            'r2 = [R(m.n2p(2)), R(m.get_end()), R(m.get_center()), R(m.get_right())]\n'
            'k = NumberLine(x_range=[-2, 2, 1], length=1.83, include_tip=True)\n'
            'k.space_out_submobjects(1.33)\n'
            'result = [r1, r2, [R(k.get_corner(UR)), R(k.get_center()), R(k.n2p(0))]]\n')
        self.assertEqual(values, plain([
            [[0.175, 0.0], [0.175, 0.0], [0.2625, 0.0]],
            [[-0.405, 0.93], [-0.405, 0.93], [-0.2462, 0.5025], [0.2625, 0.5025]],
            [[1.1592, 0.175], [-0.0289, 0.0], [-0.0289, 0.0]]]))

    def test_become_aligns_family_structure(self):
        # align_data pads the shorter child list (faded repeats or center points) and pushes
        # a member with points under a pointless one, so receivers keep the larger structure.
        values = scene_values(
            'R = lambda m: [round(float(v), 3) for v in (*m.get_corner(DL)[:2], *m.get_corner(UR)[:2])]'
            ' + [len(m.submobjects), len(m.get_family())]\n'
            'out = []\n'
            'a = VGroup(Square(1.32), Circle(1.32).shift(RIGHT*2)); a.become(SurroundingRectangle(Square(1.15)))\n'
            'out.append(R(a))\n'
            'b = DoubleArrow(LEFT, RIGHT*2.73); b.become(CurvedArrow(LEFT, RIGHT*2.1).set_height(.67)); out.append(R(b))\n'
            'd = Cross(scale_factor=.5); d.become(Dot([-.07, -1.43, 0]).stretch(1.83, 1)); out.append(R(d))\n'
            'f = VGroup(Square(), VGroup(Circle(), Dot()).shift(RIGHT))\n'
            'f.become(VGroup(Triangle(), Square().shift(UP)).rotate(.4)); out.append(R(f) + [R(x) for x in f.submobjects])\n'
            'g = Square().rotate(.5).shift(UR); g.become(VGroup(Circle(), Dot(), Dot(LEFT*2), Square(.3).shift(DOWN)))\n'
            'out.append(R(g) + [R(x) for x in g.submobjects])\n'
            'h = VGroup(Circle(), Dot(), Dot(LEFT*2)); h.become(VGroup(Square().rotate(.3), Dot(UP)))\n'
            'out.append(R(h) + [R(x) for x in h.submobjects] + [x.get_fill_opacity() for x in h.submobjects])\n'
            'm = VGroup(Dot(), Dot(RIGHT), Dot(UP)); m.become(Square()); m.submobjects[2].shift(UP * 0.98)\n'
            'out.append(R(m) + [R(x) for x in m.submobjects])\n'
            'p = VGroup(Dot(), VGroup(Dot(), Dot()))\n'
            'p.become(VGroup(Circle(), Square().scale(.5).add(Dot(RIGHT*3)).rotate(.7)))\n'
            'out.append(R(p) + [R(x) for x in p.submobjects] + [R(x) for x in p[1].submobjects])\n'
            'result = out\n')
        self.assertEqual(values, plain([
            [-0.675, -0.675, 0.675, 0.675, 2, 3], [-0.88, -0.687, 1.98, -0.028, 2, 3],
            [-0.15, -1.576, 0.01, -1.284, 2, 3],
            [-1.408, -0.739, 1.284, 2.291, 2, 5, [-0.311, -0.739, 1.284, 0.98, 0, 1],
             [-1.408, -0.33, 1.213, 2.291, 2, 3]],
            [-2.08, -1.15, 1.0, 1.0, 4, 5, [-1.0, -1.0, 1.0, 1.0, 0, 1], [-0.08, -0.08, 0.08, 0.08, 0, 1],
             [-2.08, -0.08, -1.92, 0.08, 0, 1], [-0.15, -1.15, 0.15, -0.85, 0, 1]],
            [-1.251, -1.251, 1.251, 1.251, 3, 4, [-1.251, -1.251, 1.251, 1.251, 0, 1],
             [-1.251, -1.251, 1.251, 1.251, 0, 1], [-0.08, 0.92, 0.08, 1.08, 0, 1], 0.0, 0.0, 1.0],
            [-1.0, -1.0, 1.0, 1.98, 3, 4, [-1.0, -1.0, 1.0, 1.0, 0, 1], [-1.0, -1.0, 1.0, 1.0, 0, 1],
             [-1.0, -0.02, 1.0, 1.98, 0, 1]],
            [-1.0, -1.536, 2.678, 1.181, 2, 5, [-1.0, -1.0, 1.0, 1.0, 0, 1], [-0.401, -1.536, 2.678, 1.181, 2, 3],
             [2.518, 1.022, 2.678, 1.181, 0, 1], [-0.401, -1.536, 1.008, -0.127, 0, 1]]]))

    def test_become_keeps_scene_attributes(self):
        # Community's become copies points and colors; attributes scene code added remain,
        # so a transformed label keeps its bookkeeping (LinearTransformationScene relies on it).
        values = scene_values(
            'a = Circle(); a.speed = 3; a.tag = "x"\n'
            'b = Square(); b.tag = "y"; b.extra = 1\n'
            'a.become(b)\n'
            'c = Dot(); c.info = {"k": 1}\n'
            'scene = Scene(); scene.play(Transform(c, Square()), run_time=0.2)\n'
            's = Square(); s.color = RED\n'
            'result = [a.speed, a.tag, hasattr(a, "extra"), c.info, s.get_stroke_color(), a.width]\n')
        self.assertEqual(values, plain([3, 'x', False, {'k': 1}, '#FC6255', 2.0]))
        source = open(Path(__file__).parents[1] / 'examples' / 'linear_transformation_scene.py').read()
        self.assertNotIn('error', json.loads(lite.render_scene(source, 'LinearTransformationExample')))

    def test_point_equality_rejects_non_finite_differences(self):
        # np.allclose semantics (Manim 0.22): infinities match only themselves; NaN never matches.
        values = scene_values(
            'v = VMobject(); inf, nan = float("inf"), float("nan")\n'
            'pts = [[0, 0, 0], [.3, 0, 0], [.6, 0, 0], [1, 0, 0], [inf, 0, 0], [1.3, 0, 0], [1.6, 0, 0], [2, 0, 0]]\n'
            'result = [v.consider_points_equals([1, 0, 0], [inf, 0, 0]), v.consider_points_equals([inf, 0], [inf, 0]),\n'
            '          v.consider_points_equals([nan, 0], [nan, 0]), len(v.get_subpaths_from_points(pts)),\n'
            '          len(v.get_subpath_split_indices_from_points(pts))]\n')
        self.assertEqual(values, [False, True, False, 2, 2])

    def test_rate_function_submodule_holds_easing_functions(self):
        # Manim 0.22 keeps ease_* (and sqrt) in manim.utils.rate_functions, not the top level.
        values = scene_values(
            'import manim.utils.rate_functions as rf\n'
            'from manim.utils.rate_functions import ease_in_out_back\n'
            'result = [rf.ease_in_quad(0.5), ease_in_out_back(0.25), rf.sqrt(0.25), rf.smooth(0.5),\n'
            '          rate_functions.ease_out_bounce(0.7)]\n')
        self.assertEqual(values, [0.25, -0.0997, 0.5, 0.5, 0.9306])

    def test_submodule_only_names_import(self):
        # Manim 0.22 defines these in submodules without exporting them from manim.
        values = scene_values(
            'from manim.mobject.graph import GenericGraph\n'
            'from manim.mobject.types.image_mobject import AbstractImageMobject\n'
            'from manim.animation.transform_matching_parts import TransformMatchingAbstractBase\n'
            'from manim.data_structures import MethodWithArgs\n'
            'from manim.utils.config_ops import DictAsObject\n'
            'from manim.mobject.vector_field import StreamLine\n'
            'import manim\n'
            'call = MethodWithArgs(Square.shift, (UP,), {})\n'
            'result = [issubclass(DiGraph, GenericGraph), issubclass(ImageMobject, AbstractImageMobject),\n'
            '          issubclass(TransformMatchingShapes, TransformMatchingAbstractBase), call.args == (UP,),\n'
            '          DictAsObject({"a": 1}).a, issubclass(StreamLine, VMobject), hasattr(manim, "MethodWithArgs")]\n')
        self.assertEqual(values, [True, True, True, True, 1, True, False])

    def test_community_keyword_parameter_names(self):
        # Manim 0.22 parameter names, usable as keywords.
        values = scene_values(
            'a = Arrow(LEFT, RIGHT)\n'
            'd = Dot().move_to(point_or_mobject=a.tip)\n'
            's = Square().match_style(vmobject=Circle(fill_opacity=0.5))\n'
            'v = VDict(mapping_or_iterable=[("x", Dot())]); v.add(mapping_or_iterable={"y": Square()})\n'
            'keys = list(v.submob_dict); v.remove(key="x")\n'
            'g = FunctionGraph(lambda x: x * x)\n'
            'with tempconfig(temp={"background_color": RED}):\n'
            '    rate = str(config.background_color)\n'
            'result = [list(d.get_center()) == list(a.tip.get_center()), s.get_fill_opacity(), keys,\n'
            '          list(v.submob_dict), list(g.get_point_from_function(x=2)), rate,\n'
            '          ImageMobject(np.zeros((2, 2, 3), dtype=np.uint8)).set_color(RED, alpha=0.5) is not None\n'
            '          if "np" in globals() else True]\n')
        self.assertEqual(values, [True, 0.5, ['x', 'y'], ['y'], [2, 4, 0], '#FC6255', True])

    def test_number_line_scene_structure(self):
        # Manim 0.22: the line owns the shaft points (cut at the tip base); submobjects
        # are the tip and ticks, and indexing/iteration include the line itself.
        values = scene_values(
            'nl = NumberLine(x_range=[-3, 3, 1], length=6, include_tip=True)\n'
            'ax = Axes(x_range=[-2, 2], y_range=[-1, 1], x_length=4, y_length=2)\n'
            'result = [[type(m).__name__ for m in nl.submobjects], [type(m).__name__ for m in nl],\n'
            '          len(nl.points), type(nl[0]).__name__, len(nl), nl.has_points(),\n'
            '          [type(m).__name__ for m in ax.submobjects],\n'
            '          [list(p) for p in nl.get_points()[:2]], nl.get_num_points()]\n')
        self.assertEqual(plain(values), plain([
            ['ArrowTriangleFilledTip', 'VGroup'], ['NumberLine', 'ArrowTriangleFilledTip', 'VGroup'],
            4, 'NumberLine', 3, True, ['NumberLine', 'NumberLine'],
            [[-3, 0, 0], [-1.1167, 0, 0]], 4]))

    def test_image_files_and_png_pixel_arrays(self):
        # Expected pixels come from Pillow, Community's image reader.
        import tempfile
        cases = json.loads((Path(__file__).with_name('fixtures') / 'png_cases.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            values = scene_values(
                'import base64, os\n'
                f'cases = {[[mode, data] for mode, data, _ in cases]!r}\n'
                f'folder = {folder!r}\n'
                'pixels = [[[list(p) for p in row] for row in\n'
                '           ImageMobject("data:image/png;base64," + data).get_pixel_array()]\n'
                '          for _, data in cases]\n'
                'with open(os.path.join(folder, "tiny.png"), "wb") as handle:\n'
                '    handle.write(base64.b64decode(cases[2][1]))\n'
                'image = ImageMobject(os.path.join(folder, "tiny"), scale_to_resolution=7)\n'
                'inverted = ImageMobject(os.path.join(folder, "tiny.png"), invert=True)\n'
                'result = [pixels, image.href.startswith("data:image/png;base64,"), image.height,\n'
                '          [list(p) for p in inverted.get_pixel_array()[0][:2]], "_pixels" in inverted.to_dict()]\n')
        self.assertEqual(plain(values[0]), [expected for _, _, expected in cases])
        first = cases[2][2][0][:2]
        self.assertEqual(plain(values[1:]), plain([True, 5 / 7 * 8, [[255 - r, 255 - g, 255 - b, a]
                                                                    for r, g, b, a in first], False]))

    def test_subdivision_matrices_skia_path_stand_in_and_files(self):
        import tempfile
        values = scene_values(
            'from manim.utils.bezier import _get_subdivision_matrix, SUBDIVISION_MATRICES\n'
            'from manim.mobject.geometry.boolean_ops import _BooleanOps\n'
            'm = _get_subdivision_matrix(4, 2)\n'
            'quartic = [[0, 0, 0], [1, 2, 0], [2, 0, 0], [3, 2, 0], [4, 0, 0]]\n'
            'ops = _BooleanOps(); path = ops._convert_vmobject_to_skia_path(Square())\n'
            'back = _BooleanOps()._convert_skia_path_to_vmobject(path)\n'
            'result = [[list(row) for row in m], 2 in SUBDIVISION_MATRICES[3],\n'
            '          [list(p) for p in subdivide_bezier(quartic[:3], 2)],\n'
            '          [list(p) for p in subdivide_bezier(quartic, 2)][4:6],\n'
            '          [s[0] for s in path.segments], len(back.points),\n'
            '          [list(p) for p in back.points[:-4]] == [list(p) for p in Square().points],\n'
            '          [list(p) for p in ops._convert_2d_to_3d_array([(1.0, 2.0)], z_dim=1.0)]]\n')
        self.assertEqual(plain(values), [
            [[1.0, 0.0, 0.0, 0.0], [0.5, 0.5, 0.0, 0.0], [0.25, 0.5, 0.25, 0.0], [0.125, 0.375, 0.375, 0.125],
             [0.125, 0.375, 0.375, 0.125], [0.0, 0.25, 0.5, 0.25], [0.0, 0.0, 0.5, 0.5], [0.0, 0.0, 0.0, 1.0]],
            True, [[0.0, 0.0, 0.0], [0.5, 1.0, 0.0], [1.0, 1.0, 0.0], [1.0, 1.0, 0.0], [1.5, 1.0, 0.0],
                   [2.0, 0.0, 0.0]],
            [[2.0, 1.0, 0.0], [2.0, 1.0, 0.0]],
            ['moveTo', 'curveTo', 'curveTo', 'curveTo', 'curveTo', 'closePath'], 20.0, True, [[1.0, 2.0, 1.0]]])
        with tempfile.TemporaryDirectory() as folder:
            svg, code = Path(folder) / 'shape.svg', Path(folder) / 'listing.py'
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d=""/>'
                           '<path d="M 0 0 L 1 1"/></svg>', encoding='utf-8')
            code.write_text('def f(x):\n    return x + 1\n', encoding='utf-8')
            self.assertEqual(len(lite.SVGMobject(svg).children), 1)
            self.assertEqual(len(lite.SVGMobject(str(svg)[:-4]).children), 1)
            self.assertEqual(len(lite.Code(code_file=code).code_lines), 2)
        with self.assertRaises(NotImplementedError):
            lite.Code(code_file='missing_listing.py')

    def test_tip_shafts_become_alignment_and_surface_handles(self):
        values = scene_values(
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        m = DoubleArrow(LEFT, RIGHT)\n'
            '        self.add(m)\n'
            '        self.lefts = []\n'
            '        self.add_updater(lambda dt: self.lefts.append(m.get_left()[0]))\n'
            '        self.play(m.animate.arrange(DOWN), run_time=0.4)\n'
            'scene = S(); scene.render()\n'
            'line = Line(LEFT*2, RIGHT*2).add_tip(tip_shape=ArrowCircleFilledTip)\n'
            'line.add_tip(at_start=True, tip_shape=ArrowSquareTip)\n'
            'circle = Circle().shift(OUT)\n'
            'circle.become(Sphere(radius=0.5, resolution=(6, 6)).shift(LEFT))\n'
            'face = Sphere(radius=0.5, resolution=(6, 6)).get_family()[9]\n'
            'empty = VMobject(); empty.shift(RIGHT); empty.to_edge(LEFT)\n'
            'cam = MovingCameraScene().camera.frame\n'
            'result = [scene.lefts[1:5], line.submobjects[0].width, circle.get_top()[1],\n'
            '          [len(m.points) for m in circle.get_family()[:2]], list(face.points[1]),\n'
            '          list(empty.get_center()), type(cam).__name__, isinstance(cam, ScreenRectangle),\n'
            '          [type(m).__name__ for m in Axes().family_members_with_points()[:2]]]\n')
        self.assertEqual(values, [[-0.7226, -0.5996, -0.4875, -0.548], 0.3067, 0.4985, [0.0, 32.0],
                                  [0.0856, 0.4506, -0.25], [0.0, 0.0, 0.0], 'ScreenRectangle', True,
                                  ['NumberLine', 'ArrowTriangleFilledTip']])

    def test_number_line_own_point_queries(self):
        values = scene_values(
            'n = NumberLine(x_range=[-3, 3, 1], length=6, include_tip=True).rotate(0.3).shift(UP)\n'
            'result = [n.point_from_proportion(0.25), n.get_arc_length(), n.get_anchors(), n.get_last_handle(),\n'
            '          len(n.get_all_points()), n.get_center_of_mass(), n.proportion_from_point(n.n2p(0))]\n')
        self.assertEqual(values, [[-1.5166, 0.5309, 0.0], 5.65, [[-2.866, 0.1134, 0.0], [2.5316, 1.7831, 0.0]],
                                  [0.7324, 1.2266, 0.0], 40.0, [0.4896, 1.1515, 0.0], 0.531])

    def test_arc_center_estimate_and_tipped_point_edits(self):
        values = scene_values(
            'e = Ellipse(width=3, height=1).rotate(0.5).shift(DOWN)\n'
            'c = CurvedArrow(LEFT * 2, RIGHT * 2, angle=1.2)\n'
            'd = CurvedArrow(LEFT * 2, RIGHT * 2, angle=1.2).add_line_to(UP)\n'
            'f = CurvedArrow(LEFT * 2, RIGHT * 2, angle=1.2).set_points_as_corners([LEFT, UP, RIGHT])\n'
            'result = [e.get_arc_center(), c.get_arc_center(), d.get_center(), d.height, f.get_center(), f.width]\n')
        self.assertEqual(values, [[0.8274, -0.548, 0.0], [0.0, 2.6135, 0.0], [0.0, 0.1636, 0.0], 1.6816,
                                  [0.5, 0.329, 0.0], 3.0])

    def test_surrounding_rectangle_measures_like_a_group(self):
        values = scene_values(
            'r = SurroundingRectangle(CubicBezier(LEFT, UP, UR, RIGHT))\n'
            'e = SurroundingRectangle(Ellipse(width=2, height=1).rotate(0.5))\n'
            'result = [r.get_center(), r.width, r.height, e.width, e.height]\n')
        self.assertEqual(values, [[0.0, 0.5, 0.0], 2.2, 1.2, 2.0823, 1.5138])

    def test_decimal_number_glyph_submobjects(self):
        values = scene_values(
            'd = DecimalNumber(3.14159, num_decimal_places=2)\n'
            'n = DecimalNumber(-1.5, include_sign=True)\n'
            'i = Integer(42)\n'
            'xs = [m.get_center()[0] for m in d]\n'
            'd[0].set_color(RED)\n'
            'd.set_value(12.5)\n'
            'result = [len(n), len(i.submobjects), xs, type(i[0]).__name__, len(d), d[0].get_color() == WHITE]\n')
        # Community 0.22 places these glyph centers at -0.291, -0.113, 0.043, 0.284.
        self.assertEqual(values, [5.0, 2.0, [-0.2918, -0.1135, 0.0435, 0.2848], 'MathTex', 5.0, True])


    def test_partial_parent_exposure_keeps_member_frames(self):
        source = (
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        x = ValueTracker(-3)\n'
            '        child = Dot(LEFT*3, radius=.2)\n'
            '        child.add_updater(lambda dot: dot.move_to((x.get_value(), .5, 0)))\n'
            '        host = Rectangle(width=3, height=1.5).add(child, Dot(radius=.2)).rotate(PI/6).scale(.8)\n'
            '        self.centers = []\n'
            '        self.add_updater(lambda dt: self.centers.append(list(child.get_center())))\n'
            '        self.play(Create(host), run_time=2)\n'
            '        TRACE.extend(self.centers[8:11])\n')
        trace = []
        lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
        namespace = {'TRACE': trace}
        exec(compile(source, '<test>', 'exec'), namespace)
        namespace['S']().render()
        # Community 0.22: the undrawn dot sits at its first point while the rectangle completes.
        self.assertEqual(plain(trace), [[-2.8614, 0.58, 0.0]] * 3)


    def test_padded_receivers_repeat_their_own_members(self):
        source = (
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        shapes = VGroup(Circle().shift(LEFT), VGroup(Square().shift(RIGHT)))\n'
            '        target = VGroup(Square(), Triangle(), VGroup(Circle(), Line()))\n'
            '        self.play(Transform(shapes, target))\n'
            '        a = VGroup(Dot(), Square())\n'
            '        a.become(VGroup(Dot(), Dot(), Dot(), Circle()))\n'
            '        FOUND.extend([[type(m).__name__ for m in shapes], [type(m).__name__ for m in shapes[2]],\n'
            '                    [type(m).__name__ for m in a]])\n')
        found = []
        lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
        namespace = {'FOUND': found}
        exec(compile(source, '<test>', 'exec'), namespace)
        namespace['S']().render()
        # Community 0.22's align_data puts each member's faded copies right after it.
        self.assertEqual(found, [['Circle', 'Circle', 'VGroup'], ['Square', 'Square'],
                                 ['Dot', 'Dot', 'Square', 'Square']])


    def test_rotated_point_clouds_bound_their_points(self):
        values = scene_values(
            'disk = PointCloudDot(center=LEFT * 3, radius=1.5).scale(.7).rotate(.6)\n'
            'result = [disk.get_critical_point(DL), disk.get_critical_point(UR)]\n')
        # Community 0.22 bounds the turned points, not the turned bounding box.
        self.assertEqual([v[:2] for v in values], [[-3.9795, -0.9801], [-2.0199, 0.9795]])


    def test_transforms_into_arrows_keep_aligned_shaft_points(self):
        source = (
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        o = Circle(radius=0.7)\n'
            '        self.add(o)\n'
            '        self.play(Transform(o, Arrow(LEFT, RIGHT * 2)))\n'
            '        FOUND.append(len(o.get_points()))\n'
            '        self.play(o.animate.become(Triangle()))\n'
            '        FOUND.append(len(o.get_points()))\n')
        found = []
        lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
        namespace = {'FOUND': found}
        exec(compile(source, '<test>', 'exec'), namespace)
        namespace['S']().render()
        # Community 0.22: the circle's eight curves subdivide the shaft, then the triangle.
        self.assertEqual(found, [32, 32])


    def test_animation_copies_see_the_previous_frame(self):
        source = (
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        d = Dot()\n'
            '        d.add_updater(lambda m: m.next_to(d, UP))\n'
            '        self.add(d)\n'
            '        self.play(Create(d))\n'
            '        FOUND.append(d.get_top()[1])\n')
        found = []
        lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
        namespace = {'FOUND': found}
        exec(compile(source, '<test>', 'exec'), namespace)
        namespace['S']().render()
        # Community 0.22: Create's updated starting copy follows the dot as the previous frame
        # left it (collapsed to its first point at alpha 0), so it climbs every frame.
        self.assertEqual(plain(found), [6.6289])


    def test_wave_and_flash_start_copies_follow_updaters(self):
        source = (
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        d = Dot().add_updater(lambda m, dt: m.shift(RIGHT * dt))\n'
            '        self.add(d)\n'
            '        self.play(ApplyWave(d))\n'
            '        FOUND.append(d.get_x())\n')
        found = []
        lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
        namespace = {'FOUND': found}
        exec(compile(source, '<test>', 'exec'), namespace)
        namespace['S']().render()
        # Community 0.22: the wave runs on the updated starting copy, so the dot keeps drifting.
        self.assertEqual(plain(found), [1.9333])


    def test_change_speed_finishes_through_community_piecewise(self):
        source = (
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        d, e = Dot(LEFT * 3), Dot(LEFT * 3)\n'
            '        self.play(ChangeSpeed(d.animate.shift(RIGHT * 6), {0.3: .2, 0.7: 3}, rate_func=linear))\n'
            '        self.play(ChangeSpeed(e.animate.shift(RIGHT * 6), {0.3: .2, 0.7: 3}))\n'
            '        FOUND.extend([d.get_x(), e.get_x()])\n')
        found = []
        lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
        namespace = {'FOUND': found}
        exec(compile(source, '<test>', 'exec'), namespace)
        namespace['S']().render()
        # Community 0.22: smooth(1) returns the integer 1, so np.piecewise truncates the
        # remapped 0.999... to 0 and the dot ends where it started; linear(1.0) does not.
        self.assertEqual(plain(found), [3.0, -3.0])


    def test_shrink_rotating_subsets_and_focus_follow_updaters(self):
        source = (
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        a, b, c, d = Square(), Square(), Square(), Square()\n'
            '        for m in (a, b, c, d):\n'
            '            m.add_updater(lambda m, dt: m.shift(RIGHT * dt))\n'
            '        self.add(a, b, c, d)\n'
            '        self.play(ShrinkToCenter(a), Rotating(b, run_time=1), ShowIncreasingSubsets(c), FocusOn(d))\n'
            '        FOUND.extend([a.get_x(), b.get_x(), c.get_x(), d.get_x()])\n')
        found = []
        lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
        namespace = {'FOUND': found}
        exec(compile(source, '<test>', 'exec'), namespace)
        namespace['S']().render()
        # Community 0.22: the shrinking copy, the rotating copy and the subset-showing mobject
        # keep moving with their updaters; FocusOn (2 s) does not animate d itself.
        self.assertEqual(plain(found), [1.9333, 1.9333, 1.9333, 1.9333])


    def test_unsuspended_animations_update_in_scene_order(self):
        source = (
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        p = Dot().add_updater(lambda m, dt: m.shift(UP * dt))\n'
            '        self.add(p)\n'
            '        o = Square().add_updater(lambda m: m.next_to(p, RIGHT))\n'
            '        self.add(o)\n'
            '        tops = []\n'
            '        self.add_updater(lambda dt: tops.append(o.get_top()[1]))\n'
            '        self.play(MoveAlongPath(o, Circle()))\n'
            '        FOUND.extend(tops[1:4])\n')
        found = []
        lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
        namespace = {'FOUND': found}
        exec(compile(source, '<test>', 'exec'), namespace)
        namespace['S']().render()
        # Community 0.22: MoveAlongPath leaves updating on, and the square's updater runs after
        # the dot moved in the same frame.
        self.assertEqual(plain(found), [1.0667, 1.1333, 1.2])


    def test_fade_transform_target_copy_is_a_scene_member(self):
        source = (
            'from manim import *\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        o, d = Circle(), Dot()\n'
            '        self.add(o, d)\n'
            '        seen = []\n'
            '        self.add_updater(lambda dt: seen.append([type(m).__name__ for m in self.get_mobject_family_members()]))\n'
            '        self.play(FadeTransform(o, Square()))\n'
            '        FOUND.extend([seen[5], [type(m).__name__ for m in self.mobjects]])\n')
        found = []
        lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
        namespace = {'FOUND': found}
        exec(compile(source, '<test>', 'exec'), namespace)
        namespace['S']().render()
        # Community 0.22 adds Group(source, target copy) as a root while the animation runs,
        # so the source moves after the dot and the morphing copy is in the scene (Community
        # also lists the Group itself; the preview keeps its members as roots).
        self.assertEqual(found, [['Dot', 'Circle', 'Square'], ['Dot', 'Square']])


    def test_reversed_create_ends_collapsed(self):
        values = scene_values(
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        self.play(Create(Square(), reverse_rate_function=True))\n'
            '        self.result = self.mobjects[0].height\n'
            's = S(); s.render()\n'
            'result = [s.result]\n')
        # Community 0.22's final interpolate is at alpha 0: the square stays a point.
        self.assertEqual(values, [0.0])


    def test_wiggle_readds_arrow_tips_every_frame(self):
        source = (
            'from manim import *\n'
            'import math\n'
            'class S(Scene):\n'
            '    def construct(self):\n'
            '        a = Arrow(LEFT, RIGHT).rotate(1)\n'
            '        self.add(a)\n'
            '        lengths = []\n'
            '        def shaft(dt):\n'
            '            points = a.get_points()\n'
            '            lengths.append(math.dist(points[-1], points[0]))\n'
            '        self.add_updater(shaft)\n'
            '        self.play(Wiggle(a))\n'
            '        FOUND.extend(lengths[10:14])\n')
        found = []
        lite.render_scene('from manim import *\nclass Empty(Scene):\n    pass\n')
        namespace = {'FOUND': found}
        exec(compile(source, '<test>', 'exec'), namespace)
        namespace['S']().render()
        # Community 0.22: Wiggle scales the arrow member with Arrow.scale, which pops and re-adds
        # the already wiggled tip each frame, so the shaft keeps lengthening.
        self.assertEqual(plain(found), [1.1708, 1.198, 1.2498, 1.3058])


if __name__ == '__main__':
    unittest.main()
