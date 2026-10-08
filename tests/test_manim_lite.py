import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manim_lite', ROOT / 'src/manim-lite.py')
lite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lite)


def render(body):
    source = 'from manim import *\nclass Demo(Scene):\n    def construct(self):\n'
    source += '\n'.join('        ' + line for line in body.splitlines())
    return json.loads(lite.render_scene(source))


class SceneTests(unittest.TestCase):
    def test_baseline_animation(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/minimal_scene.py').read_text()))
        self.assertEqual(result['scene'], 'MinimalScene')
        self.assertEqual(result['frames'][0]['mobjects'][0]['draw_progress'], 0)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['type'], 'square')
        self.assertGreater(len(result['frames']), 30)

    def test_create_traces_outline_and_preserves_final_style(self):
        result = render('self.play(Create(Square(fill_opacity=0.8)), run_time=2, rate_func=linear)')
        middle = result['frames'][15]['mobjects'][0]
        self.assertEqual(middle['draw_progress'], 0.5)
        self.assertEqual(middle['fill_opacity'], 0.4)
        self.assertEqual(middle['opacity'], 1)
        final = result['frames'][-1]['mobjects'][0]
        self.assertNotIn('draw_progress', final)
        self.assertEqual(final['fill_opacity'], 0.8)

    def test_create_group_and_text_fallback(self):
        result = render('self.play(Create(VGroup(Circle(), VGroup(Text("Title"), Square()))), run_time=2, rate_func=linear)')
        group = result['frames'][15]['mobjects'][0]
        self.assertEqual(group['children'][0]['draw_progress'], 0.5)
        nested = group['children'][1]['children']
        self.assertEqual(nested[0]['opacity'], 0.5)
        self.assertEqual(nested[1]['draw_progress'], 0.5)

    def test_uncreate_reverses_drawing_and_removes_the_object(self):
        result = render('c = Circle()\nself.add(c)\nself.play(Uncreate(c), run_time=2, rate_func=linear)')
        self.assertEqual(result['frames'][0]['mobjects'][0]['draw_progress'], 1)
        self.assertEqual(result['frames'][15]['mobjects'][0]['draw_progress'], 0.5)
        self.assertEqual(result['frames'][-1]['mobjects'], [])

    def test_rotate_keeps_orbital_radius_at_intermediate_frames(self):
        result = render('s = Square(side_length=0.5).shift(RIGHT * 2)\nself.play(Rotate(s, PI, about_point=ORIGIN), run_time=2, rate_func=linear)')
        for frame in result['frames']:
            x, y, _ = frame['mobjects'][0]['position']
            self.assertAlmostEqual(x*x + y*y, 4)
        middle = result['frames'][15]['mobjects'][0]
        self.assertAlmostEqual(middle['position'][0], 0)
        self.assertAlmostEqual(middle['position'][1], 2)
        self.assertAlmostEqual(middle['angle'], lite.PI / 2)
        self.assertAlmostEqual(result['frames'][-1]['mobjects'][0]['position'][0], -2)

    def test_rotation_defaults_clockwise_axis_and_followup_animation(self):
        result = render('s = Square().shift(RIGHT)\nself.play(Rotating(s, axis=IN, about_point=ORIGIN))\nself.play(s.animate.shift(RIGHT))')
        self.assertEqual(result['duration'], 6)
        quarter = result['frames'][15]['mobjects'][0]
        self.assertLess(quarter['position'][1], 0)
        final = result['frames'][-1]['mobjects'][0]
        self.assertAlmostEqual(final['position'][0], 2)
        self.assertAlmostEqual(final['angle'], -lite.TAU)
        self.assertEqual(lite.Rotate(lite.Square()).run_time, 1)
        self.assertEqual(lite.Rotate(lite.Square()).angle, lite.PI)

    def test_rotation_about_own_center_and_rejects_3d_axis(self):
        result = render('s = Square().shift(RIGHT * 2)\nself.play(Rotate(s, TAU), run_time=2)')
        self.assertEqual(result['frames'][15]['mobjects'][0]['position'], [2, 0, 0])
        with self.assertRaisesRegex(NotImplementedError, '2D rotation'):
            render('self.play(Rotate(Square(), axis=UP))')
        with self.assertRaises(ValueError):
            lite.Rotate(lite.Square(), float('inf'))

    def test_direction_math_and_animate(self):
        result = render('c = Circle().shift(LEFT * 2)\nself.add(c)\nself.play(c.animate.shift(RIGHT * 4), run_time=2, rate_func=linear)')
        frames = result['frames']
        self.assertEqual(frames[0]['mobjects'][0]['position'][0], -2)
        self.assertEqual(frames[15]['mobjects'][0]['position'][0], 0)
        self.assertEqual(frames[-1]['mobjects'][0]['position'][0], 2)
        self.assertEqual(result['duration'], 2)

    def test_fadeout_removes_object_and_wait_holds_state(self):
        result = render('c = Circle()\nself.add(c)\nself.wait(1)\nself.play(FadeOut(c))')
        self.assertEqual(result['frames'][0], result['frames'][14])
        self.assertEqual(result['frames'][-1]['mobjects'], [])
        self.assertLess(result['frames'][-2]['mobjects'][0]['opacity'], 0.1)

    def test_parallel_animations_use_individual_durations(self):
        result = render('self.play(FadeIn(Circle(), run_time=1), FadeIn(Square(), run_time=2), rate_func=linear)')
        objects = result['frames'][15]['mobjects']
        self.assertEqual(objects[0]['opacity'], 1)
        self.assertEqual(objects[1]['opacity'], 0.5)

    def test_transform_and_replacement_identity(self):
        result = render('c = Circle()\ns = Square()\nself.play(ReplacementTransform(c, s))\nself.play(s.animate.shift(RIGHT))')
        self.assertEqual(len(result['frames'][-1]['mobjects']), 1)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['position'][0], 1)
        result = render('c = Circle()\nself.play(Transform(c, Circle(radius=2)))')
        self.assertEqual(result['frames'][-1]['mobjects'][0]['radius'], 2)

    def test_no_stale_scene_after_another_render(self):
        render('self.add(Circle())')
        with self.assertRaisesRegex(ValueError, 'No Scene class'):
            lite.render_scene('from manim import *\nx = 1')

    def test_explicit_scene_and_missing_selection(self):
        source = 'from manim import *\nclass First(Scene): pass\nclass Second(Scene): pass'
        result = json.loads(lite.render_scene(source, 'Second'))
        self.assertEqual(result['scene'], 'Second')
        self.assertEqual(result['scenes'], ['First', 'Second'])
        with self.assertRaisesRegex(ValueError, 'was not found'):
            lite.render_scene(source, 'Missing')

    def test_scale_and_rotation_preserve_object_center(self):
        shape = lite.Square().shift(lite.RIGHT * 2)
        shape.scale(0.5).rotate(lite.PI / 4)
        self.assertEqual(shape.get_center(), lite.RIGHT * 2)
        self.assertEqual(shape.geometry_scale, 0.5)
        self.assertAlmostEqual(shape.angle, lite.PI / 4)

    def test_external_pivots_and_asymmetric_geometry(self):
        line = lite.Line((1, 0), (3, 0))
        self.assertEqual(line.get_center(), (2, 0, 0))
        line.scale(2, about_point=lite.ORIGIN)
        self.assertEqual(line.get_center(), (4, 0, 0))
        line.rotate(90 * lite.DEGREES, about_point=lite.ORIGIN)
        self.assertAlmostEqual(line.get_center()[0], 0)
        self.assertAlmostEqual(line.get_center()[1], 4)
        self.assertEqual(line.to_dict()['geometry_center'], [2, 0, 0])

    def test_group_scaling_uses_child_bounds_as_its_pivot(self):
        group = lite.VGroup(lite.Circle().shift(lite.RIGHT * 2), lite.Square().shift(lite.RIGHT * 4))
        self.assertEqual(group.get_center(), (3, 0, 0))
        group.scale(2)
        self.assertEqual(group._bounds(), (-1, -2, 7, 2))
        group.rotate(lite.PI / 2)
        bounds = group._bounds()
        self.assertAlmostEqual(bounds[0], 1)
        self.assertAlmostEqual(bounds[2], 5)

    def test_animated_scale_and_rotation_have_intermediate_states(self):
        result = render('s = Square()\nself.play(s.animate.scale(2).rotate(PI / 2), run_time=2, rate_func=linear)')
        midpoint = result['frames'][15]['mobjects'][0]
        self.assertEqual(midpoint['geometry_scale'], 1.5)
        self.assertAlmostEqual(midpoint['angle'], lite.PI / 4)
        final = result['frames'][-1]['mobjects'][0]
        self.assertEqual(final['geometry_scale'], 2)
        self.assertAlmostEqual(final['angle'], lite.PI / 2)

    def test_invalid_geometry_transform_is_rejected(self):
        for operation in (lambda: lite.Circle().scale(float('inf')), lambda: lite.Circle().rotate(float('nan'))):
            with self.assertRaises(ValueError):
                operation()

    def test_limits_and_invalid_durations(self):
        for body in ('self.wait(100)', 'self.play(Create(Circle()), run_time=100)', 'self.wait(float("inf"))', 'self.play(Create(Circle()), run_time=-1)'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                render(body)

    def test_exact_duration_limit_includes_final_seekable_state(self):
        result = render('self.wait(60)')
        self.assertEqual(result['duration'], 60)
        self.assertEqual(len(result['frames']), 901)
        with self.assertRaisesRegex(ValueError, '60 seconds'):
            render('self.wait(60)\nself.wait(0.1)')

    def test_errors_are_not_silently_ignored(self):
        with self.assertRaises(SyntaxError):
            lite.render_scene('class !')
        with self.assertRaises(NotImplementedError):
            render('self.add(Circle(unsupported_option=True))')
        with self.assertRaises(TypeError):
            render('self.play(Circle())')

    def test_static_scene_and_duplicate_add(self):
        result = render('c = Circle()\nself.add(c, c)')
        self.assertEqual(len(result['frames']), 1)
        self.assertEqual(len(result['frames'][0]['mobjects']), 1)


if __name__ == '__main__':
    unittest.main()
