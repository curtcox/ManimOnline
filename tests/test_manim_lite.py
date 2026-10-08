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
        self.assertEqual(result['frames'][0]['mobjects'][0]['opacity'], 0)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['type'], 'square')
        self.assertGreater(len(result['frames']), 30)

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
        self.assertEqual(json.loads(lite.render_scene(source, 'Second'))['scene'], 'Second')
        with self.assertRaisesRegex(ValueError, 'was not found'):
            lite.render_scene(source, 'Missing')

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
