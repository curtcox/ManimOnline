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
    def test_order_gallery_reorders_groups_clears_and_reintroduces_title(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/order_scene.py').read_text()))
        self.assertEqual(result['duration'], 7)
        self.assertEqual([m['type'] for m in result['frames'][0]['mobjects']], ['vgroup', 'circle', 'text'])
        self.assertEqual([m['type'] for m in result['frames'][15]['mobjects']], ['circle', 'text', 'vgroup'])
        self.assertEqual([m['type'] for m in result['frames'][45]['mobjects']], ['vgroup', 'circle', 'text'])
        self.assertEqual(result['frames'][60]['mobjects'], [])
        self.assertEqual(result['frames'][75]['mobjects'][0]['opacity'], 0)
        self.assertEqual([m['type'] for m in result['frames'][-1]['mobjects']], ['text'])
        self.assertEqual(result['frames'][-1]['mobjects'][0]['text'], 'Scene draw order')

    def test_scene_ordering_preserves_identity_geometry_and_argument_order(self):
        a, b, c, d = lite.Circle(), lite.Square(), lite.Dot(), lite.Triangle()
        scene = lite.Scene().add(a, b, c)
        before = [m.to_dict() for m in (a, b, c, d)]
        self.assertIs(scene.bring_to_front(a, b, a), scene)
        self.assertEqual(scene.mobjects, [c, a, b])
        self.assertIs(scene.bring_to_back(d, b), scene)
        self.assertEqual(scene.mobjects, [d, b, c, a])
        scene.bring_to_front().bring_to_back()
        self.assertEqual(scene.mobjects, [d, b, c, a])
        self.assertEqual([m.to_dict() for m in (a, b, c, d)], before)

    def test_reordered_roots_keep_paint_ties_during_animation(self):
        result = render('a = Circle(color=BLUE)\nb = Square(color=RED)\nself.add(a, b)\nself.wait(1)\nself.bring_to_front(a)\nself.play(Rotate(a, PI), run_time=1)\nself.bring_to_back(a)\nself.wait(1)')
        for index, colors in ((0, [lite.BLUE, lite.RED]), (15, [lite.RED, lite.BLUE]), (29, [lite.RED, lite.BLUE]), (30, [lite.BLUE, lite.RED])):
            self.assertEqual([m['color'] for m in result['frames'][index]['mobjects']], colors)

    def test_clear_keeps_previous_frames_and_objects_can_be_reintroduced(self):
        scene = lite.Scene()
        a = lite.Square().shift(lite.RIGHT).save_state()
        before = a.to_dict()
        scene.add(a).wait(1)
        self.assertIs(scene.clear(), scene)
        self.assertEqual(scene.mobjects, [])
        self.assertEqual(len(scene.frames[0]['mobjects']), 1)
        scene.wait(1)
        self.assertEqual(scene.frames[15]['mobjects'], [])
        scene.play(lite.FadeIn(a))
        self.assertEqual(a.to_dict(), before)
        self.assertEqual(scene.mobjects, [a])
        self.assertIn('_saved_state', a.__dict__)
        self.assertEqual(render('self.add(Circle())\nself.wait(1)\nself.clear()')['frames'][-1]['mobjects'], [])

    def test_ordering_rejects_family_restructuring_without_partial_changes(self):
        child = lite.Circle()
        group = lite.VGroup(child)
        other = lite.Dot()
        scene = lite.Scene().add(group, other)
        for method in (scene.bring_to_front, scene.bring_to_back):
            with self.assertRaisesRegex(NotImplementedError, 'whole scene groups'):
                method(other, child)
            self.assertEqual(scene.mobjects, [group, other])
            with self.assertRaisesRegex(TypeError, 'Mobjects'):
                method(1)
        scene = lite.Scene().add(child)
        with self.assertRaises(NotImplementedError):
            scene.bring_to_front(group)
        self.assertEqual(scene.mobjects, [child])

    def test_layer_gallery_preserves_geometry_and_restores_individual_depths(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/layer_scene.py').read_text()))
        self.assertEqual(result['duration'], 7)
        for index, depths in ((0, [-2, 2]), (45, [-3, -3]), (105, [-2, 2])):
            group = result['frames'][index]['mobjects'][0]
            self.assertEqual([c['z_index'] for c in group['children']], depths)
            self.assertEqual(group['geometry_scale'], 1.2)
            self.assertEqual(group['position'], [0, 0.2, 0])

    def test_z_index_constructor_family_and_validation(self):
        child = lite.Circle(z_index=-2)
        inner = lite.VGroup(child)
        group = lite.VGroup(inner, lite.Square())
        self.assertIs(group.set_z_index(3), group)
        self.assertEqual([group.z_index, inner.z_index, child.z_index, group.children[1].z_index], [3]*4)
        group.set_z_index(-1, family=False)
        self.assertEqual(group.z_index, -1)
        self.assertEqual(child.z_index, 3)
        for value in (float('nan'), float('inf'), 'front', None):
            with self.assertRaisesRegex(ValueError, 'finite number'):
                child.set_z_index(value)
        self.assertEqual(child.z_index, 3)

    def test_animated_z_index_crosses_other_objects_and_restores_checkpoint(self):
        result = render('a = Circle(z_index=-2).save_state()\nb = Square()\nself.add(a, b)\nself.play(a.animate.set_z_index(2), run_time=2, rate_func=linear)\nself.play(Restore(a), run_time=2, rate_func=linear)')
        for index, z in ((0, -2), (15, 0), (30, 2), (45, 0), (60, -2)):
            self.assertEqual(result['frames'][index]['mobjects'][0]['z_index'], z)
            self.assertEqual(result['frames'][index]['mobjects'][1]['z_index'], 0)

    def test_z_index_group_animation_and_copy_keep_independent_depth(self):
        result = render('g = VGroup(Circle(z_index=-3), Square(z_index=4))\nc = g.copy().set_z_index(7)\nself.add(g, c)\nself.play(g.animate.set_z_index(1), rate_func=linear)')
        self.assertEqual([c['z_index'] for c in result['frames'][0]['mobjects'][0]['children']], [-3, 4])
        self.assertEqual([c['z_index'] for c in result['frames'][7]['mobjects'][0]['children']], [-3 + 4*7/15, 4 - 3*7/15])
        self.assertEqual([c['z_index'] for c in result['frames'][-1]['mobjects'][0]['children']], [1, 1])
        self.assertEqual([c['z_index'] for c in result['frames'][-1]['mobjects'][1]['children']], [7, 7])

    def test_succession_repeated_rotations_start_from_prior_terminal_geometry(self):
        result = render('s = Square()\nself.play(Succession(Rotate(s, PI / 2, run_time=2, rate_func=linear), Rotate(s, PI / 2, run_time=2, rate_func=linear)))')
        self.assertEqual(result['duration'], 4)
        for index, angle in ((15, lite.PI / 4), (30, lite.PI / 2), (45, 3 * lite.PI / 4), (60, lite.PI)):
            self.assertAlmostEqual(result['frames'][index]['mobjects'][0]['angle'], angle)

    def test_succession_introduces_later_objects_only_when_their_stage_begins(self):
        result = render('a = Circle(color=BLUE)\nb = Square(color=RED).shift(RIGHT * 3)\nself.play(Succession(Create(a, run_time=2), FadeOut(a), FadeIn(b, run_time=2, rate_func=linear)))')
        self.assertEqual(result['duration'], 5)
        self.assertEqual(len(result['frames'][0]['mobjects']), 1)
        self.assertEqual(result['frames'][44]['mobjects'][0]['type'], 'circle')
        self.assertEqual(result['frames'][45]['mobjects'][0]['type'], 'square')
        self.assertEqual(result['frames'][45]['mobjects'][0]['opacity'], 0)
        self.assertEqual(result['frames'][60]['mobjects'][0]['opacity'], 0.5)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['opacity'], 1)

    def test_succession_replacement_can_be_followed_by_animation_of_its_target(self):
        result = render('a = Circle()\nb = Square().shift(RIGHT * 2)\nself.play(Succession(ReplacementTransform(a, b), Rotate(b, PI, run_time=2, rate_func=linear)))\nself.play(b.animate.shift(UP))')
        self.assertEqual(len(result['frames'][15]['mobjects']), 1)
        self.assertEqual(result['frames'][15]['mobjects'][0]['type'], 'square')
        self.assertAlmostEqual(result['frames'][30]['mobjects'][0]['angle'], lite.PI / 2)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['position'], [2, 1, 0])

    def test_succession_preparation_does_not_commit_live_geometry_or_checkpoints(self):
        shape = lite.Square().save_state()
        scene = lite.Scene().add(shape)
        before = shape.to_dict()
        sequence = lite.Succession(lite.Rotate(shape, lite.PI), lite.Restore(shape))
        sequence.prepare(scene)
        self.assertEqual(shape.to_dict(), before)
        self.assertEqual(sequence.states(0)[shape][0]['angle'], 0)
        self.assertAlmostEqual(sequence.states(0.5)[shape][0]['angle'], lite.PI)
        sequence.finish(scene)
        self.assertEqual(shape.to_dict(), before)
        self.assertIn('_saved_state', shape.__dict__)

    def test_succession_nested_groups_and_parallel_objects_have_independent_timelines(self):
        result = render('a = Dot()\nb = Square().shift(RIGHT * 3)\nc = Circle().shift(LEFT * 3)\nself.play(AnimationGroup(Succession(AnimationGroup(FadeIn(a), Create(b)), Succession(Rotate(b, PI, rate_func=linear), FadeOut(a))), Create(c, run_time=4)))')
        self.assertEqual(result['duration'], 4)
        self.assertEqual(result['frames'][15]['mobjects'][0]['opacity'], 1)
        self.assertAlmostEqual(result['frames'][22]['mobjects'][1]['angle'], lite.PI * 7 / 15)
        self.assertEqual(len(result['frames'][45]['mobjects']), 2)
        self.assertEqual(len(result['frames'][-1]['mobjects']), 2)

    def test_succession_duration_rescaling_and_terminal_hold(self):
        result = render('s = Square()\nc = Circle().shift(RIGHT * 3)\nself.play(Succession(Rotate(s, PI, rate_func=linear), FadeOut(s), run_time=2), Create(c, run_time=4))')
        self.assertEqual(len(result['frames'][30]['mobjects']), 1)
        self.assertEqual(len(result['frames'][59]['mobjects']), 1)
        self.assertEqual(result['duration'], 4)
        result = render('s = Square()\nself.play(Succession(Rotate(s, PI, rate_func=linear), Rotate(s, PI, rate_func=linear)), run_time=4)')
        self.assertAlmostEqual(result['frames'][45]['mobjects'][0]['angle'], 3 * lite.PI / 2)

    def test_succession_conflicts_and_invalid_options_are_explicit(self):
        for body in ('s = Square()\nself.play(Succession(Create(s), Rotate(s)), FadeOut(s))',
                     's = Square()\nself.play(Succession(AnimationGroup(Create(s), Rotate(s)), FadeOut(s)))'):
            with self.assertRaisesRegex(ValueError, 'one animation per object'):
                render(body)
        with self.assertRaises(NotImplementedError):
            lite.Succession(lite.Create(lite.Dot()), lag_ratio=0.5)
        with self.assertRaises(TypeError):
            lite.Succession()
        with self.assertRaises(ValueError):
            lite.Succession(lite.Create(lite.Dot()), run_time=float('inf'))

    def test_succession_same_animation_instance_and_final_cleanup(self):
        result = render('s = Square()\na = Rotate(s, PI / 2, rate_func=linear)\nself.play(Succession(a, a, FadeOut(s)))\nself.wait(1)')
        self.assertAlmostEqual(result['frames'][15]['mobjects'][0]['angle'], lite.PI / 2)
        self.assertEqual(result['frames'][-1]['mobjects'], [])

    def test_completed_groups_hold_terminal_state_even_with_returning_easing(self):
        for group in ('Succession', 'AnimationGroup'):
            result = render(f'a = Dot()\nb = Square().shift(RIGHT * 3)\nself.play({group}(FadeOut(a), rate_func=there_and_back), Create(b, run_time=3))')
            self.assertEqual(len(result['frames'][15]['mobjects']), 1)
            self.assertEqual(len(result['frames'][44]['mobjects']), 1)

    def test_succession_relative_animate_chains_accumulate_from_stage_starts(self):
        result = render('s = Square().save_state()\nself.play(Succession(s.animate.shift(RIGHT * 2), s.animate.shift(UP * 2).scale(2)))\nself.play(s.animate.restore())')
        self.assertEqual(result['frames'][15]['mobjects'][0]['position'], [2, 0, 0])
        self.assertEqual(result['frames'][22]['mobjects'][0]['position'][0], 2)
        self.assertEqual(result['frames'][30]['mobjects'][0]['position'], [2, 2, 0])
        self.assertEqual(result['frames'][30]['mobjects'][0]['geometry_scale'], 2)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['position'], [0, 0, 0])
        self.assertEqual(result['frames'][-1]['mobjects'][0]['geometry_scale'], 1)

    def test_delayed_animate_methods_resolve_current_layout_reference(self):
        result = render('a = Square()\nb = Square().shift(RIGHT * 3)\nself.play(Succession(b.animate.shift(UP * 2), a.animate.next_to(b, LEFT)))')
        self.assertEqual(result['frames'][-1]['mobjects'][0]['position'], [3, 2, 0])
        self.assertEqual(result['frames'][-1]['mobjects'][1]['position'], [0.75, 2, 0])

    def test_succession_gallery_example_completes_all_steps(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/succession_scene.py').read_text()))
        self.assertEqual(result['duration'], 10)
        self.assertEqual([m['type'] for m in result['frames'][15]['mobjects']], ['text', 'square'])
        self.assertEqual([m['type'] for m in result['frames'][105]['mobjects']], ['text', 'circle'])
        self.assertEqual([m['type'] for m in result['frames'][-1]['mobjects']], ['text'])

    def test_mathtex_serialization_and_constructor_validation(self):
        formula = lite.MathTex('a^2', '+ b^2', arg_separator=' ', color=lite.BLUE, font_size=36)
        self.assertEqual(formula.to_dict()['type'], 'mathtex')
        self.assertEqual(formula.text, 'a^2 + b^2')
        self.assertEqual((formula.fill_opacity, formula.stroke_width), (1, 0))
        for size in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                lite.MathTex('x', font_size=size)
        with self.assertRaises(ValueError):
            lite.MathTex('x' * 4097)
        with self.assertRaises(TypeError):
            lite.MathTex(12)
        with self.assertRaises(NotImplementedError):
            lite.MathTex('x', tex_template='custom')

    def test_mathtex_creation_fades_and_changed_formula_crossfades(self):
        result = render("a = MathTex(r'\\frac{a}{b}')\nself.play(Create(a), run_time=2)\nself.play(Transform(a, MathTex('x^2', color=RED)), run_time=2)\nself.wait(1)")
        first = result['frames'][15]['mobjects'][0]
        self.assertEqual(first['opacity'], 0.5)
        self.assertNotIn('draw_progress', first)
        middle = result['frames'][45]['mobjects']
        self.assertEqual([m['text'] for m in middle], [r'\frac{a}{b}', 'x^2'])
        self.assertEqual([m['opacity'] for m in middle], [0.5, 0.5])
        self.assertEqual(result['frames'][-1]['mobjects'][0]['text'], 'x^2')

    def test_math_example_renders_all_formula_frames(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/math_scene.py').read_text()))
        self.assertEqual(result['duration'], 7)
        self.assertEqual(result['frames'][-1]['mobjects'][1]['text'], r'\sum_{k=1}^n k = \frac{n(n+1)}{2}')

    def test_line_endpoint_queries_follow_geometry_transforms(self):
        for cls in (lite.Line, lite.Arrow):
            line = cls((1, 1), (3, 1)).scale(-2).rotate(lite.PI / 2).shift(lite.RIGHT)
            self.assertPointAlmostEqual(line.get_start(), (3, 3, 0))
            self.assertPointAlmostEqual(line.get_end(), (3, -1, 0))
            self.assertPointAlmostEqual(line.get_vector(), (0, -4, 0))
            self.assertPointAlmostEqual(line.get_unit_vector(), (0, -1, 0))
            self.assertAlmostEqual(line.get_angle(), -lite.PI / 2)
            self.assertAlmostEqual(line.get_length(), 4)
            self.assertEqual(line.get_start_and_end(), (line.get_start(), line.get_end()))

    def test_endpoint_edit_preserves_styles_checkpoint_and_transforms(self):
        line = lite.Arrow(color=lite.PURPLE, stroke_opacity=0.5).scale(2).rotate(0.7).save_state()
        original = line.to_dict()
        self.assertIs(line.put_start_and_end_on((-3, 1), (2, -2)), line)
        self.assertPointAlmostEqual(line.get_start(), (-3, 1, 0))
        self.assertPointAlmostEqual(line.get_end(), (2, -2, 0))
        self.assertEqual((line.angle, line.geometry_scale), (0.7, 2))
        self.assertEqual((line.stroke_color, line.stroke_opacity), (lite.PURPLE, 0.5))
        line.restore()
        self.assertEqual(line.to_dict(), original)

    def test_animated_endpoint_edit_matches_linear_endpoint_motion(self):
        line = lite.Line((1, 2), (4, 3)).rotate(0.8).scale(-1.5).shift(lite.LEFT)
        old_start, old_end = line.get_start_and_end()
        new_start, new_end = lite.Vector((-3, 1)), lite.Vector((2, -2))
        scene = lite.Scene()
        scene.play(line.animate.put_start_and_end_on(new_start, new_end), run_time=2, rate_func=lite.linear)
        middle = line.copy()
        middle.__dict__.update(scene.frames[15]['mobjects'][0])
        self.assertPointAlmostEqual(middle.get_start(), (old_start + new_start) * 0.5)
        self.assertPointAlmostEqual(middle.get_end(), (old_end + new_end) * 0.5)
        self.assertPointAlmostEqual(line.get_start(), new_start)
        self.assertPointAlmostEqual(line.get_end(), new_end)

    def test_degenerate_connectors_recover_and_invalid_endpoints_fail(self):
        line = lite.Line(lite.ORIGIN, lite.ORIGIN).scale(0).rotate(1)
        self.assertEqual(line.get_unit_vector(), lite.ORIGIN)
        self.assertEqual(line.get_length(), 0)
        line.put_start_and_end_on(lite.LEFT, lite.RIGHT)
        self.assertPointAlmostEqual(line.get_start(), lite.LEFT)
        self.assertPointAlmostEqual(line.get_end(), lite.RIGHT)
        line.put_start_and_end_on(lite.UP, lite.UP)
        self.assertEqual(line.get_length(), 0)
        original = line.to_dict()
        for point in ((float('nan'), 0), (float('inf'), 0)):
            with self.assertRaises(ValueError):
                line.put_start_and_end_on(point, lite.ORIGIN)
            with self.assertRaises(ValueError):
                lite.Line(lite.ORIGIN, point).get_end()
        with self.assertRaises(NotImplementedError):
            line.put_start_and_end_on(lite.OUT, lite.ORIGIN)
        self.assertEqual(line.to_dict(), original)

    def test_connector_example_renders_restored_arrow(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/connector_scene.py').read_text()))
        self.assertEqual(result['duration'], 8)
        self.assertEqual([m['type'] for m in result['frames'][-1]['mobjects']], ['arrow', 'text'])
        initial, final = result['frames'][0]['mobjects'][0], result['frames'][-1]['mobjects'][0]
        for key in ('position', 'start', 'end', 'angle', 'geometry_scale'):
            self.assertEqual(initial[key], final[key])
        self.assertEqual(initial['stroke_color'].lower(), final['stroke_color'].lower())

    def test_transform_from_copy_preserves_identity_styles_and_checkpoints(self):
        source = lite.Square(color=lite.BLUE).shift(lite.LEFT * 2).save_state()
        target = lite.Square(color=lite.RED).shift(lite.RIGHT * 2).save_state()
        original, destination = source.to_dict(), target.to_dict()
        scene = lite.Scene().add(source)
        scene.play(lite.TransformFromCopy(source, target), run_time=2, rate_func=lite.linear)
        middle = scene.frames[15]['mobjects']
        self.assertEqual(middle[0], original)
        self.assertEqual(middle[1]['position'], [0, 0, 0])
        self.assertEqual(scene.frames[0]['mobjects'], [original, original])
        self.assertEqual(source.to_dict(), original)
        self.assertEqual(target.to_dict(), destination)
        self.assertEqual(scene.mobjects, [source, target])
        source.shift(lite.UP).restore()
        target.scale(0).restore()
        self.assertEqual(source.to_dict(), original)
        self.assertEqual(target.to_dict(), destination)
        scene.play(lite.FadeOut(target))
        self.assertEqual(scene.mobjects, [source])

    def test_transform_from_copy_snapshots_at_start_and_crossfades_types(self):
        source, target = lite.Circle(), lite.Square()
        effect = lite.TransformFromCopy(source, target)
        source.shift(lite.LEFT)
        target.shift(lite.RIGHT)
        scene = lite.Scene()
        scene.play(effect, run_time=2, rate_func=lite.linear)
        middle = scene.frames[15]['mobjects']
        self.assertEqual([m['type'] for m in middle], ['circle', 'square'])
        self.assertEqual([m['opacity'] for m in middle], [0.5, 0.5])
        self.assertEqual(scene.mobjects, [target])
        self.assertEqual(effect._terminal, [target.to_dict()])

    def test_transform_from_copy_group_children_keep_identity(self):
        child = lite.Circle(color=lite.BLUE)
        source = lite.VGroup(child, lite.Square()).arrange().shift(lite.LEFT * 2)
        target = source.copy().shift(lite.RIGHT * 4)
        target_child = target.children[0]
        scene = lite.Scene().add(source, target)
        scene.play(lite.TransformFromCopy(source, target), run_time=2)
        self.assertEqual(len(scene.mobjects), 2)
        self.assertIs(source.children[0], child)
        self.assertIs(target.children[0], target_child)
        self.assertEqual(scene.frames[15]['mobjects'][1]['position'],
                         [(a + b) / 2 for a, b in zip(source.position, target.position)])

    def test_transform_from_copy_source_can_animate_while_copy_holds_terminal(self):
        source = lite.Square().shift(lite.LEFT * 2)
        target = lite.Square().shift(lite.RIGHT * 2)
        scene = lite.Scene().add(source)
        movement = source.animate.shift(lite.UP * 2)
        movement.run_time = 4
        scene.play(lite.AnimationGroup(
            lite.TransformFromCopy(source, target, run_time=1),
            movement))
        self.assertEqual(scene.frames[45]['mobjects'][1], target.to_dict())
        self.assertEqual(scene.frames[0]['mobjects'][1]['position'], [-2, 0, 0])
        self.assertEqual(source.position, [-2, 2, 0])

    def test_transform_from_copy_conflicts_and_invalid_objects(self):
        source, target = lite.Square(), lite.Circle()
        with self.assertRaises(ValueError):
            lite.TransformFromCopy(source, source)
        with self.assertRaises(TypeError):
            lite.TransformFromCopy(source, 'target')
        with self.assertRaises(ValueError):
            lite.Scene().play(lite.TransformFromCopy(source, target), lite.FadeIn(target))
        with self.assertRaises(NotImplementedError):
            lite.Scene().add(lite.VGroup(target)).play(lite.TransformFromCopy(source, target))

    def test_transform_from_copy_can_read_scene_added_group_child(self):
        source, target = lite.Circle(), lite.Circle().shift(lite.RIGHT * 2)
        group = lite.VGroup(source)
        scene = lite.Scene().add(group)
        scene.play(lite.TransformFromCopy(source, target))
        self.assertEqual(scene.mobjects, [group, target])
        self.assertIs(group.children[0], source)

    def test_copy_example_renders_and_cleans_up_only_destinations(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/copy_scene.py').read_text()))
        self.assertEqual(result['scene'], 'CopyScene')
        self.assertEqual(result['duration'], 11)
        final = result['frames'][-1]['mobjects']
        self.assertEqual([m['type'] for m in final], ['square', 'text'])
        self.assertEqual(final[0]['position'], [-3, 0, 0])
        self.assertEqual(final[0]['fill_color'], lite.BLUE)

    def test_indicate_peaks_and_returns_without_mutating_object_or_checkpoint(self):
        shape = lite.Arc(fill_color=lite.BLUE, stroke_color=lite.PURPLE, fill_opacity=0.4)
        shape.scale(2).rotate(lite.PI / 3).shift(lite.LEFT).save_state()
        original = shape.to_dict()
        scene = lite.Scene()
        scene.play(lite.Indicate(shape, scale_factor=1.5), run_time=4)
        peak = scene.frames[30]['mobjects'][0]
        self.assertEqual(peak['geometry_scale'], 3)
        self.assertEqual((peak['fill_color'], peak['stroke_color']), (lite.YELLOW.lower(), lite.YELLOW.lower()))
        self.assertEqual(peak['fill_opacity'], original['fill_opacity'])
        self.assertEqual(peak['position'], original['position'])
        self.assertEqual(peak['angle'], original['angle'])
        self.assertEqual(scene.frames[15], scene.frames[45])
        self.assertEqual(shape.to_dict(), original)
        self.assertIs(scene.mobjects[0], shape)
        shape.shift(lite.RIGHT).restore()
        self.assertEqual(shape.to_dict(), original)

    def test_indicate_samples_current_state_and_preserves_group_child_identity(self):
        child = lite.Circle(color=lite.GREEN)
        group = lite.VGroup(child, lite.Square(color=lite.RED)).arrange().rotate(lite.PI / 4)
        effect = lite.Indicate(group, color=lite.ORANGE)
        group.shift(lite.UP)
        original = group.to_dict()
        scene = lite.Scene()
        scene.play(effect, run_time=2)
        peak = scene.frames[15]['mobjects'][0]
        self.assertEqual(peak['geometry_scale'], 1.2)
        self.assertEqual(peak['children'][0]['stroke_color'], lite.ORANGE.lower())
        self.assertEqual(group.to_dict(), original)
        self.assertIs(group.children[0], child)

    def test_indicate_finished_effect_holds_original_until_longer_animation_ends(self):
        result = render('a = Square(color=BLUE)\nb = Circle(color=RED).shift(RIGHT * 3)\nself.play(AnimationGroup(Indicate(a, run_time=2), Create(b, run_time=4)))')
        state = result['frames'][45]['mobjects'][0]
        self.assertEqual(state['geometry_scale'], 1)
        self.assertEqual(state['stroke_color'], lite.BLUE)
        self.assertEqual(result['frames'][-1]['mobjects'][0], result['frames'][0]['mobjects'][0])

    def test_indicate_rate_override_and_scale_validation(self):
        result = render('self.play(Indicate(Square(), scale_factor=2, rate_func=linear), run_time=2)')
        self.assertEqual(result['frames'][15]['mobjects'][0]['geometry_scale'], 1.5)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['geometry_scale'], 1)
        self.assertEqual([lite.there_and_back(t) for t in (0, 0.25, 0.5, 0.75, 1)], [0, 0.5, 1, 0.5, 0])
        for factor in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                lite.Indicate(lite.Square(), scale_factor=factor)

    def test_indicate_example_restores_all_styles_and_geometry(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/indicate_scene.py').read_text()))
        self.assertEqual(result['duration'], 9)
        first, last = result['frames'][0]['mobjects'], result['frames'][-1]['mobjects']
        self.assertEqual(first, last)

    def test_save_and_restore_are_repeatable_isolated_and_replace_the_checkpoint(self):
        shape = lite.Arc().set_fill(lite.BLUE, 0.4).set_stroke(lite.YELLOW, 4)
        original = shape.to_dict()
        self.assertIs(shape.save_state(), shape)
        shape.shift(lite.RIGHT).scale(2).rotate(lite.PI).set_opacity(0.2)
        self.assertIs(shape.restore(), shape)
        self.assertEqual(shape.to_dict(), original)
        shape.set_fill(lite.RED).restore()
        self.assertEqual(shape.fill_color, lite.BLUE)
        shape.shift(lite.UP).save_state().shift(lite.RIGHT).restore()
        self.assertEqual(shape.position, list(lite.UP))
        self.assertNotIn('_saved_state', shape._saved_state)
        clone = shape.copy().shift(lite.LEFT)
        clone.save_state().set_color(lite.GREEN).restore()
        self.assertEqual(shape.fill_color, lite.BLUE)

    def test_saved_state_is_not_serialized_even_in_nested_groups(self):
        child = lite.Square().save_state()
        group = lite.VGroup(lite.VGroup(child)).save_state()
        before = json.dumps(group.to_dict())
        for _ in range(20):
            group.save_state()
        self.assertEqual(json.dumps(group.to_dict()), before)
        self.assertNotIn('_saved_state', before)
        group.children[0].children[0].shift(lite.RIGHT).set_color(lite.RED)
        group.restore()
        self.assertEqual(json.dumps(group.to_dict()), before)

    def test_restore_interpolates_geometry_styles_and_keeps_scene_identity(self):
        shape = lite.Square(fill_color=lite.BLUE, fill_opacity=0.5).save_state()
        shape.shift(lite.RIGHT * 2).scale(0.5).set_fill(lite.RED, 1)
        scene = lite.Scene()
        scene.play(lite.Restore(shape), run_time=2, rate_func=lite.linear)
        middle = scene.frames[15]['mobjects'][0]
        self.assertEqual(middle['position'], [1, 0, 0])
        self.assertEqual(middle['geometry_scale'], 0.75)
        self.assertEqual(middle['fill_opacity'], 0.75)
        self.assertIs(scene.mobjects[0], shape)
        self.assertEqual(shape.position, [0, 0, 0])
        self.assertEqual(shape.fill_color, lite.BLUE)
        scene.play(lite.ShrinkToCenter(shape))
        scene.play(shape.animate.restore())
        self.assertEqual(shape.geometry_scale, 1)

    def test_transform_preserves_source_checkpoint_across_shape_changes(self):
        shape = lite.Square().save_state()
        scene = lite.Scene()
        scene.play(lite.Transform(shape, lite.Circle(color=lite.RED).shift(lite.RIGHT)))
        scene.play(lite.Restore(shape), run_time=2, rate_func=lite.linear)
        self.assertEqual([s['type'] for s in scene.frames[30]['mobjects']], ['circle', 'square'])
        self.assertEqual(shape._type, 'square')
        self.assertEqual(shape.color, lite.WHITE)
        shape.shift(lite.RIGHT).restore()
        self.assertEqual(shape.position, [0, 0, 0])
        unsaved = lite.Square()
        scene = lite.Scene()
        scene.play(lite.Transform(unsaved, lite.Circle().save_state()))
        with self.assertRaises(ValueError):
            unsaved.restore()

    def test_restore_requires_checkpoint_and_supports_staggered_groups(self):
        shape = lite.Square()
        with self.assertRaises(ValueError):
            shape.restore()
        with self.assertRaises(ValueError):
            lite.Restore(shape)
        result = render('a = Circle().shift(LEFT).save_state().shift(DOWN)\nb = Square().shift(RIGHT).save_state().shift(UP)\nself.play(LaggedStart(Restore(a), Restore(b), lag_ratio=0.5), run_time=3)')
        self.assertEqual(result['frames'][-1]['mobjects'][0]['position'], [-1, 0, 0])
        self.assertEqual(result['frames'][-1]['mobjects'][1]['position'], [1, 0, 0])

    def test_restore_example_returns_group_to_initial_geometry_and_styles(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/restore_scene.py').read_text()))
        self.assertEqual(result['duration'], 11)
        group = result['frames'][-1]['mobjects'][1]
        self.assertEqual((group['geometry_scale'], group['angle']), (1, 0))
        for child in group['children']:
            self.assertEqual((child['fill_color'], child['stroke_color']), (lite.BLUE, lite.YELLOW))
        self.assertNotIn('_saved_state', json.dumps(result))

    def test_fill_and_stroke_styles_are_independent_and_color_sets_both(self):
        shape = lite.Square(color=lite.BLUE, fill_color=lite.RED, stroke_color=lite.GREEN,
                            fill_opacity=0.4, stroke_opacity=0.7)
        shape.set_fill(lite.YELLOW, 0.5)
        self.assertEqual((shape.stroke_color, shape.stroke_opacity), (lite.GREEN, 0.7))
        shape.set_stroke(lite.PURPLE, 5, opacity=0.3)
        self.assertEqual((shape.fill_color, shape.fill_opacity), (lite.YELLOW, 0.5))
        self.assertEqual(shape.stroke_width, 5)
        shape.set_color(lite.ORANGE)
        self.assertEqual((shape.fill_color, shape.stroke_color), (lite.ORANGE, lite.ORANGE))
        self.assertEqual((shape.fill_opacity, shape.stroke_opacity), (0.5, 0.3))

    def test_nested_group_styles_recurse_and_family_false_preserves_children(self):
        shape = lite.Circle(color=lite.RED)
        group = lite.VGroup(lite.VGroup(shape), lite.Square(color=lite.BLUE))
        group.set_color(lite.YELLOW, family=False)
        self.assertEqual(shape.color, lite.RED)
        group.set_fill(lite.GREEN, 0.6).set_stroke(lite.PURPLE, 4, opacity=0.2)
        self.assertEqual((shape.fill_color, shape.stroke_color), (lite.GREEN, lite.PURPLE))
        group.set_color(lite.ORANGE)
        self.assertEqual(shape.color, lite.ORANGE)
        group.set_opacity(0.5)
        for obj in (group, group.children[0], shape, group.children[1]):
            self.assertEqual((obj.fill_opacity, obj.stroke_opacity, obj.opacity), (0.5, 0.5, 1))

    def test_animated_style_channels_interpolate_and_fades_preserve_them(self):
        result = render('s = Square(fill_color=BLACK, stroke_color=WHITE, fill_opacity=1)\nself.play(s.animate.set_fill(WHITE, 0.5).set_stroke(BLACK, 6, opacity=0.2), run_time=2, rate_func=linear)\nself.play(FadeOut(s), run_time=2, rate_func=linear)')
        middle = result['frames'][15]['mobjects'][0]
        self.assertEqual((middle['fill_color'], middle['stroke_color']), ('#808080', '#808080'))
        self.assertAlmostEqual(middle['fill_opacity'], 0.75)
        self.assertAlmostEqual(middle['stroke_opacity'], 0.6)
        faded = result['frames'][45]['mobjects'][0]
        self.assertEqual((faded['fill_color'], faded['stroke_color']), (lite.WHITE, lite.BLACK))
        self.assertEqual(faded['opacity'], 0.5)
        result = render('g = VGroup(Circle(), Square())\nself.play(g.animate.set_opacity(0), run_time=2, rate_func=linear)')
        state = result['frames'][15]['mobjects'][0]
        self.assertEqual(state['opacity'], 1)
        self.assertEqual(state['children'][0]['stroke_opacity'], 0.5)
        self.assertEqual(state['children'][1]['stroke_opacity'], 0.5)

    def test_style_validation_rejects_invalid_values_before_changes(self):
        shape = lite.Square()
        for value in (-0.1, 1.1, float('nan'), float('inf')):
            for setter in (shape.set_opacity, lambda v: shape.set_fill(lite.RED, v),
                           lambda v: shape.set_stroke(lite.RED, opacity=v)):
                with self.assertRaises(ValueError):
                    setter(value)
            with self.assertRaises(ValueError):
                lite.Circle(stroke_opacity=value)
        self.assertEqual(shape.fill_color, lite.WHITE)
        self.assertEqual(shape.stroke_color, lite.WHITE)
        for width in (-1, float('inf')):
            with self.assertRaises(ValueError):
                shape.set_stroke(width=width)
        self.assertEqual(lite.Text('Hello').stroke_width, 0)

    def test_style_example_restores_opacity_and_keeps_distinct_colors(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/style_scene.py').read_text()))
        self.assertEqual(result['duration'], 9)
        shapes = result['frames'][-1]['mobjects'][0]['children']
        self.assertEqual(len(shapes), 3)
        for shape in shapes:
            self.assertEqual((shape['fill_color'], shape['stroke_color']), (lite.RED, lite.GREEN))
            self.assertEqual((shape['fill_opacity'], shape['stroke_opacity']), (1, 1))

    def test_growth_from_point_preserves_rotation_style_and_terminal_identity(self):
        shape = lite.Line((1, 0), (3, 0), color=lite.BLUE).scale(2).rotate(lite.PI / 2)
        shape.shift(lite.RIGHT * 2)
        original = shape.to_dict()
        scene = lite.Scene()
        scene.play(lite.GrowFromPoint(shape, (-2, 0)), run_time=2, rate_func=lite.linear)
        first, middle = scene.frames[0]['mobjects'][0], scene.frames[15]['mobjects'][0]
        self.assertEqual(first['geometry_scale'], 0)
        self.assertPointAlmostEqual(lite.Vector(first['position']) + original['geometry_center'], (-2, 0, 0))
        self.assertEqual(middle['geometry_scale'], 1)
        self.assertPointAlmostEqual(lite.Vector(middle['position']) + original['geometry_center'], (1, 0, 0))
        self.assertEqual(middle['angle'], original['angle'])
        self.assertEqual(middle['color'], original['color'])
        self.assertEqual(shape.to_dict(), original)
        self.assertIs(scene.mobjects[0], shape)

    def test_growth_center_is_resolved_after_prior_motion(self):
        shape = lite.Arc().scale(2).shift(lite.RIGHT)
        growth = lite.GrowFromCenter(shape)
        shape.move_to((3, 2))
        scene = lite.Scene()
        scene.play(growth, run_time=2, rate_func=lite.linear)
        for index, scale in ((0, 0), (15, 1)):
            state = scene.frames[index]['mobjects'][0]
            self.assertPointAlmostEqual(lite.Vector(state['position']) + state['geometry_center'], (3, 2, 0))
            self.assertEqual(state['geometry_scale'], scale)

    def test_growth_scales_group_as_a_whole_and_shrink_cleans_up_on_timeline(self):
        group = lite.VGroup(lite.Circle().shift(lite.LEFT * 2), lite.Square().shift(lite.RIGHT * 2))
        group.scale(0.8).rotate(lite.PI / 4).shift(lite.UP)
        original = group.to_dict()
        scene = lite.Scene()
        scene.play(lite.GrowFromCenter(group), run_time=2, rate_func=lite.linear)
        middle = scene.frames[15]['mobjects'][0]
        self.assertEqual(middle['geometry_scale'], 0.4)
        self.assertEqual(middle['children'], original['children'])
        self.assertEqual(group.to_dict(), original)
        other = lite.Dot()
        scene.play(lite.AnimationGroup(lite.ShrinkToCenter(group, run_time=1, remover=True),
                                       lite.GrowFromCenter(other, run_time=2)), rate_func=lite.linear)
        self.assertEqual(len(scene.frames[45]['mobjects']), 1)
        self.assertEqual(scene.mobjects, [other])
        self.assertEqual(group.geometry_scale, 0)
        self.assertEqual(group.get_center(), lite.UP)

    def test_shrink_default_retains_collapsed_object_and_can_be_transformed_again(self):
        shape = lite.Square().shift(lite.RIGHT)
        scene = lite.Scene()
        scene.play(lite.ShrinkToCenter(shape), run_time=2, rate_func=lite.linear)
        self.assertEqual(scene.frames[15]['mobjects'][0]['geometry_scale'], 0.5)
        self.assertEqual(scene.mobjects, [shape])
        self.assertEqual(shape.geometry_scale, 0)
        self.assertEqual(shape.get_center(), lite.RIGHT)
        scene.play(lite.Transform(shape, lite.Circle().shift(lite.LEFT)))
        self.assertEqual(shape._type, 'circle')
        self.assertEqual(shape.geometry_scale, 1)

    def test_growth_easing_and_unsupported_options(self):
        result = render('self.play(GrowFromCenter(Square()), run_time=2, rate_func=lambda t: t*t)')
        self.assertEqual(result['frames'][15]['mobjects'][0]['geometry_scale'], 0.25)
        for point in ((float('nan'), 0), (0, float('inf'))):
            with self.assertRaises(ValueError):
                lite.GrowFromPoint(lite.Square(), point)
        with self.assertRaises(NotImplementedError):
            lite.GrowFromPoint(lite.Square(), lite.OUT)
        for animation in (lite.GrowFromPoint(lite.Square().shift(lite.OUT), lite.ORIGIN),
                          lite.GrowFromCenter(lite.Square().shift(lite.OUT))):
            scene = lite.Scene()
            with self.assertRaises(NotImplementedError):
                scene.play(animation)
            self.assertEqual(scene.mobjects, [])
        with self.assertRaises(TypeError):
            lite.GrowFromCenter(lite.Square(), point_color=lite.RED)

    def test_growth_example_finishes_with_only_origin_marker(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/growth_scene.py').read_text()))
        self.assertEqual(result['duration'], 8)
        self.assertEqual(len(result['frames'][-1]['mobjects']), 1)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['color'], lite.YELLOW)

    def test_arc_defaults_clockwise_samples_and_wraparound_bounds(self):
        arc = lite.Arc()
        self.assertPointAlmostEqual(arc.point_from_proportion(0), (1, 0, 0))
        self.assertPointAlmostEqual(arc.point_from_proportion(1), (0, 1, 0))
        self.assertPointAlmostEqual(arc.get_center(), (0.5, 0.5, 0))
        clockwise = lite.Arc(start_angle=lite.PI / 2, angle=-lite.PI)
        self.assertPointAlmostEqual(clockwise.point_from_proportion(0.5), (1, 0, 0))
        self.assertPointAlmostEqual(clockwise._local_bounds(), (0, -1, 1, 1))
        wrapped = lite.Arc(start_angle=7 * lite.PI / 4, angle=lite.PI / 2)
        self.assertAlmostEqual(wrapped._local_bounds()[2], 1)
        full = lite.Arc(angle=-lite.TAU)
        self.assertPointAlmostEqual(full._local_bounds(), (-1, -1, 1, 1))
        self.assertPointAlmostEqual(full.point_from_proportion(0), full.point_from_proportion(1))

    def test_arc_transforms_keep_circle_center_distinct_from_bounds_center(self):
        arc = lite.Arc().scale(2).rotate(lite.PI / 2).shift(lite.RIGHT)
        self.assertPointAlmostEqual(arc.point_from_proportion(0), (2.5, 1.5, 0))
        self.assertPointAlmostEqual(arc.get_arc_center(), (2.5, -0.5, 0))
        arc.move_arc_center_to(lite.ORIGIN)
        self.assertPointAlmostEqual(arc.get_arc_center(), lite.ORIGIN)
        self.assertPointAlmostEqual(arc.point_from_proportion(0), (0, 2, 0))
        arc = lite.Arc(arc_center=(2, 1))
        self.assertPointAlmostEqual(arc.get_arc_center(), (2, 1, 0))

    def test_arc_creation_transform_and_path_motion(self):
        result = render('p = Arc(radius=2, angle=PI, arc_center=(1, 0))\nself.play(Create(p), run_time=2, rate_func=linear)\nself.play(MoveAlongPath(Dot(), p), run_time=2, rate_func=linear)\nself.play(p.animate.move_arc_center_to(LEFT))')
        self.assertEqual(result['frames'][15]['mobjects'][0]['draw_progress'], 0.5)
        self.assertPointAlmostEqual(result['frames'][45]['mobjects'][1]['position'], (1, 2, 0))
        self.assertPointAlmostEqual(result['frames'][-1]['mobjects'][0]['position'], (-1, 0, 0))
        result = render('self.play(Transform(Arc(angle=PI/2), Arc(angle=PI)))')
        self.assertAlmostEqual(result['frames'][-1]['mobjects'][0]['arc_angle'], lite.PI)

    def test_arc_degenerate_geometry_and_invalid_inputs(self):
        arc = lite.Arc(angle=0, radius=2, arc_center=(1, 1))
        self.assertPointAlmostEqual(arc.point_from_proportion(0.5), (3, 1, 0))
        self.assertPointAlmostEqual(lite.Arc(radius=0).point_from_proportion(0.5), lite.ORIGIN)
        for kwargs in ({'radius': -1}, {'radius': float('inf')}, {'angle': float('nan')},
                       {'start_angle': float('inf')}, {'arc_center': (float('nan'), 0)}):
            with self.assertRaises(ValueError):
                lite.Arc(**kwargs)
        for kwargs in ({'angle': lite.TAU * 2}, {'arc_center': lite.OUT}, {'num_components': 20}):
            with self.assertRaises(NotImplementedError):
                lite.Arc(**kwargs)

    def test_arc_examples_render_with_final_path_positions(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/arc_scene.py').read_text()))
        self.assertEqual(result['duration'], 7)
        self.assertEqual(len(result['frames'][-1]['mobjects']), 4)
        self.assertPointAlmostEqual(result['frames'][-1]['mobjects'][2]['position'], (-3.4, 0, 0))
        text = (ROOT / 'examples/geometry/arc.md').read_text()
        result = json.loads(lite.render_scene(text.split('```py\n')[1].split('```')[0]))
        self.assertEqual(result['frames'][0]['mobjects'][0]['type'], 'arc')

    def assertPointAlmostEqual(self, point, expected):
        for value, target in zip(point, expected):
            self.assertAlmostEqual(value, target)

    def test_circle_and_transformed_line_path_samples(self):
        circle = lite.Circle(radius=2).scale(0.5).rotate(lite.PI / 2).shift(lite.RIGHT * 3)
        self.assertPointAlmostEqual(circle.point_from_proportion(0), (3, 1, 0))
        self.assertPointAlmostEqual(circle.point_from_proportion(0.25), (2, 0, 0))
        self.assertPointAlmostEqual(circle.point_from_proportion(1), (3, 1, 0))
        line = lite.Line((1, 0), (3, 0)).scale(2).rotate(lite.PI / 2).shift(lite.UP)
        self.assertPointAlmostEqual(line.point_from_proportion(0), (2, -1, 0))
        self.assertPointAlmostEqual(line.point_from_proportion(0.5), (2, 1, 0))
        self.assertPointAlmostEqual(line.point_from_proportion(1), (2, 3, 0))

    def test_polygon_path_uses_distance_and_closes_the_outline(self):
        path = lite.Polygon((0, 0), (4, 0), (4, 1), (0, 1))
        self.assertPointAlmostEqual(path.point_from_proportion(0.4), (4, 0, 0))
        self.assertPointAlmostEqual(path.point_from_proportion(0.45), (4, 0.5, 0))
        self.assertPointAlmostEqual(path.point_from_proportion(0.95), (0, 0.5, 0))
        self.assertPointAlmostEqual(path.point_from_proportion(1), (0, 0, 0))
        self.assertPointAlmostEqual(lite.Square().point_from_proportion(0.25), (-1, 1, 0))
        self.assertPointAlmostEqual(lite.Rectangle(width=4, height=2).point_from_proportion(0.5), (-2, -1, 0))
        triangle = lite.Triangle()
        self.assertPointAlmostEqual(triangle.point_from_proportion(1 / 3), (-0.5, -3**0.5 / 6, 0))

    def test_zero_length_and_duplicate_path_vertices_are_stable(self):
        for path in (lite.Line((2, 1), (2, 1)), lite.Polygon((2, 1), (2, 1), (2, 1))):
            for alpha in (0, 0.5, 1):
                self.assertPointAlmostEqual(path.point_from_proportion(alpha), (2, 1, 0))
        path = lite.Polygon((0, 0), (0, 0), (2, 0), (2, 0))
        self.assertPointAlmostEqual(path.point_from_proportion(0.25), (1, 0, 0))

    def test_move_along_circle_keeps_radius_and_mover_orientation(self):
        result = render('p = Circle(radius=2).shift(RIGHT)\ns = Square(side_length=0.5).rotate(PI / 4)\nself.add(p)\nself.play(MoveAlongPath(s, p), run_time=4, rate_func=linear)')
        for frame in result['frames']:
            mover = frame['mobjects'][1]
            x, y, _ = mover['position']
            self.assertAlmostEqual((x - 1)**2 + y*y, 4)
            self.assertAlmostEqual(mover['angle'], lite.PI / 4)
        self.assertPointAlmostEqual(result['frames'][15]['mobjects'][1]['position'], (1, 2, 0))
        self.assertPointAlmostEqual(result['frames'][-1]['mobjects'][1]['position'], (3, 0, 0))

    def test_path_motion_centers_asymmetric_movers_and_keeps_followup_identity(self):
        result = render('m = Line((1, 0), (3, 0))\np = Line(LEFT * 2, RIGHT * 2)\nself.play(MoveAlongPath(m, p), run_time=2, rate_func=linear)\nself.play(m.animate.shift(UP))')
        middle = result['frames'][15]['mobjects'][0]
        self.assertPointAlmostEqual(middle['position'], (-2, 0, 0))
        self.assertPointAlmostEqual(result['frames'][-1]['mobjects'][0]['position'], (0, 1, 0))
        d, path = lite.Dot(), lite.Line()
        scene = lite.Scene()
        motion = lite.MoveAlongPath(d, path)
        motion.prepare(scene)
        path.shift(lite.UP * 3)
        self.assertPointAlmostEqual(motion.states(0.5)[d][0]['position'], (0, 0, 0))

    def test_path_motion_supports_lagged_groups_and_easing(self):
        result = render('p = Line(LEFT * 2, RIGHT * 2)\na, b = Dot(), Dot()\nself.play(LaggedStart(MoveAlongPath(a, p, rate_func=linear), MoveAlongPath(b, p, rate_func=linear), lag_ratio=1), run_time=4)')
        self.assertPointAlmostEqual(result['frames'][15]['mobjects'][0]['position'], (0, 0, 0))
        self.assertPointAlmostEqual(result['frames'][15]['mobjects'][1]['position'], (-2, 0, 0))
        result = render('self.play(MoveAlongPath(Dot(), Line(LEFT * 2, RIGHT * 2)), run_time=4)')
        self.assertPointAlmostEqual(result['frames'][15]['mobjects'][0]['position'], (-1.375, 0, 0))

    def test_paths_reject_invalid_proportions_geometry_and_unsupported_types(self):
        for alpha in (-0.1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                lite.Circle().point_from_proportion(alpha)
        for path in (lite.Polygon(), lite.Polygon((0, 0)), lite.Circle(radius=-1),
                     lite.Line((float('nan'), 0), (1, 0))):
            with self.assertRaises(ValueError):
                path.point_from_proportion(0.5)
        for path in (lite.Text('x'), lite.VGroup(lite.Circle()), lite.Arrow(),
                     lite.Line((0, 0, 1), (1, 0, 1)), lite.Circle().shift(lite.OUT)):
            with self.assertRaises(NotImplementedError):
                path.point_from_proportion(0.5)
        with self.assertRaises(TypeError):
            lite.MoveAlongPath(lite.Dot(), [(0, 0), (1, 0)])
        dot = lite.Dot()
        with self.assertRaises(ValueError):
            lite.MoveAlongPath(dot, dot)

    def test_path_examples_render_and_finish_at_expected_endpoint(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/path_scene.py').read_text()))
        self.assertEqual(result['duration'], 9)
        self.assertEqual(len(result['frames'][-1]['mobjects']), 5)
        mover = result['frames'][-1]['mobjects'][3]
        line = lite.Line(lite.LEFT * 3, lite.RIGHT * 3).rotate(-lite.PI / 12).shift(lite.DOWN * 2)
        self.assertPointAlmostEqual(mover['position'], line.point_from_proportion(1))
        text = (ROOT / 'examples/anim/move-along-path.md').read_text()
        result = json.loads(lite.render_scene(text.split('```py\n')[1].split('```')[0]))
        self.assertEqual(len(result['frames'][-1]['mobjects']), 2)

    def test_lagged_start_delays_reveals_and_rescales_duration(self):
        result = render('dots = VGroup(Dot(LEFT), Dot(), Dot(RIGHT))\nself.play(LaggedStart(*[FadeIn(d, rate_func=linear) for d in dots], lag_ratio=0.5), run_time=4)')
        self.assertEqual(result['duration'], 4)
        quarter = result['frames'][15]['mobjects']
        self.assertEqual([m['opacity'] for m in quarter], [0.5, 0, 0])
        middle = result['frames'][30]['mobjects']
        self.assertEqual([m['opacity'] for m in middle], [1, 0.5, 0])
        self.assertEqual([m['opacity'] for m in result['frames'][-1]['mobjects']], [1, 1, 1])
        self.assertAlmostEqual(lite.LaggedStart(lite.FadeIn(lite.Dot()), lite.FadeIn(lite.Dot())).run_time, 1.05)

    def test_parallel_group_uses_longest_end_and_removes_finished_fades(self):
        result = render('a, b = Dot(), Dot(RIGHT)\nself.add(a, b)\nself.play(AnimationGroup(a.animate.shift(UP), FadeOut(b), lag_ratio=0.1, run_time=10))')
        # Equal child times give a natural length of 1.1, stretched to ten seconds.
        self.assertEqual(result['duration'], 10)
        self.assertEqual(result['frames'][145]['mobjects'][0]['position'], [0, 1, 0])
        self.assertEqual(result['frames'][-1]['mobjects'][0]['position'], [0, 1, 0])
        result = render('a, b = Dot(), Dot(RIGHT)\nself.play(AnimationGroup(Rotate(a, run_time=10), FadeOut(b, run_time=1), lag_ratio=0.1))')
        self.assertEqual(result['duration'], 10)
        self.assertEqual(len(result['frames'][30]['mobjects']), 1)

    def test_nested_groups_and_group_easing_preserve_child_timing(self):
        result = render('a, b, c = Dot(LEFT), Dot(), Dot(RIGHT)\nself.play(AnimationGroup(LaggedStart(FadeIn(a, rate_func=linear), FadeIn(b, rate_func=linear), lag_ratio=1, run_time=4), FadeIn(c, run_time=2, rate_func=linear), lag_ratio=1))')
        self.assertEqual(result['duration'], 6)
        self.assertEqual([m['opacity'] for m in result['frames'][30]['mobjects']], [1, 0, 0])
        self.assertEqual([m['opacity'] for m in result['frames'][75]['mobjects']], [1, 1, 0.5])
        result = render('self.play(LaggedStart(FadeIn(Dot(LEFT), rate_func=linear), FadeIn(Dot(RIGHT), rate_func=linear), lag_ratio=1, run_time=4, rate_func=smooth))')
        self.assertAlmostEqual(result['frames'][15]['mobjects'][0]['opacity'], 0.3125)

    def test_group_holds_completed_creation_and_replacement_then_cleans_up(self):
        result = render('a, b, c = Circle(), Square().shift(RIGHT), Dot(UP)\nself.play(AnimationGroup(ReplacementTransform(a, b), Create(c, run_time=2)))\nself.play(b.animate.shift(UP))')
        middle = result['frames'][15]['mobjects']
        self.assertEqual(middle[0]['type'], 'square')
        self.assertEqual(middle[0]['position'], [1, 0, 0])
        final = result['frames'][-1]['mobjects']
        self.assertEqual(len(final), 2)
        self.assertNotIn('draw_progress', final[0])
        square = next(m for m in final if m['type'] == 'square')
        self.assertEqual(square['position'], [1, 1, 0])

    def test_group_rejects_conflicts_invalid_timing_and_excess_duration(self):
        for body in ('d = Dot()\nself.play(LaggedStart(FadeIn(d), FadeOut(d), lag_ratio=1))',
                     'd = Dot()\nself.play(AnimationGroup(FadeIn(d)), FadeOut(d))',
                     'd = Dot()\nself.play(FadeIn(VGroup(d)), FadeOut(d))',
                     'a, b = Dot(), Square()\nself.play(ReplacementTransform(a, b), FadeIn(b))'):
            with self.assertRaisesRegex(ValueError, 'one animation'):
                render(body)
        with self.assertRaisesRegex(NotImplementedError, 'whole scene-added group'):
            render('d = Dot()\nself.add(VGroup(d))\nself.play(FadeIn(d))')
        for kwargs in ({'lag_ratio': -1}, {'lag_ratio': float('inf')}, {'run_time': 0}):
            with self.assertRaises(ValueError):
                lite.AnimationGroup(lite.FadeIn(lite.Dot()), **kwargs)
        with self.assertRaises(TypeError):
            lite.AnimationGroup()
        with self.assertRaisesRegex(ValueError, 'timeline duration'):
            lite.AnimationGroup(lite.FadeIn(lite.Dot(), run_time=2),
                                lite.FadeIn(lite.Dot()), lag_ratio=1e308, run_time=1)
        with self.assertRaisesRegex(ValueError, '60 seconds'):
            render('self.play(LaggedStart(FadeIn(Dot()), FadeIn(Dot()), lag_ratio=1), run_time=61)')

    def test_existing_composition_examples_render(self):
        for path in ('animation-group', 'lagged-start'):
            text = (ROOT / 'examples/anim' / (path + '.md')).read_text()
            source = text.split('```py\n')[1].split('```')[0]
            result = json.loads(lite.render_scene(source))
            self.assertEqual(len(result['frames'][-1]['mobjects']), 3)

    def test_staggered_example_finishes_empty_and_group_limit_is_exact(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/staggered_scene.py').read_text()))
        self.assertEqual(result['duration'], 10)
        self.assertEqual(len(result['frames'][120]['mobjects']), 2)
        self.assertEqual(result['frames'][-1]['mobjects'], [])
        result = render('self.play(LaggedStart(FadeIn(Dot(LEFT)), FadeIn(Dot(RIGHT))), run_time=60)')
        self.assertEqual(len(result['frames']), 901)
        self.assertEqual(result['duration'], 60)

    def test_parallel_group_defaults_and_play_easing_override(self):
        result = render('self.play(AnimationGroup(FadeIn(Dot(LEFT), run_time=1, rate_func=linear), FadeIn(Dot(RIGHT), run_time=2, rate_func=linear)))')
        self.assertEqual(result['duration'], 2)
        self.assertEqual([m['opacity'] for m in result['frames'][15]['mobjects']], [1, 0.5])
        result = render('self.play(LaggedStart(FadeIn(Dot(LEFT), rate_func=linear), FadeIn(Dot(RIGHT), rate_func=linear), lag_ratio=1, run_time=4, rate_func=smooth), rate_func=linear)')
        self.assertEqual(result['frames'][15]['mobjects'][0]['opacity'], 0.5)

    def test_dot_defaults_position_and_style_overrides(self):
        dot = lite.Dot(lite.RIGHT * 2)
        self.assertEqual(dot.get_center(), (2, 0, 0))
        self.assertEqual((dot.radius, dot.fill_opacity, dot.stroke_width), (0.08, 1, 0))
        styled = lite.Dot(radius=0.2, fill_opacity=0.5, stroke_width=3)
        self.assertEqual((styled.radius, styled.fill_opacity, styled.stroke_width), (0.2, 0.5, 3))
        result = render('self.play(FadeIn(Dot(LEFT)))')
        self.assertEqual(result['frames'][-1]['mobjects'][0]['position'], [-1, 0, 0])

    def test_move_to_uses_geometry_center_and_accepts_mobjects(self):
        line = lite.Line((1, 0), (3, 0)).rotate(lite.PI / 2).move_to(lite.UP)
        self.assertEqual(line.get_center(), lite.UP)
        group = lite.VGroup(lite.Square().shift(lite.RIGHT * 4), lite.Circle().shift(lite.RIGHT * 7))
        group.move_to(line)
        self.assertEqual(group.get_center(), lite.UP)

    def test_next_to_spacing_alignment_and_transformed_shapes(self):
        circle = lite.Circle().shift(lite.LEFT)
        square = lite.Square(side_length=1).next_to(circle)
        self.assertAlmostEqual(square._bounds()[0] - circle._bounds()[2], 0.25)
        square.next_to(circle, lite.LEFT, buff=0.5, aligned_edge=lite.UP)
        self.assertAlmostEqual(circle._bounds()[0] - square._bounds()[2], 0.5)
        self.assertAlmostEqual(square._bounds()[3], circle._bounds()[3])
        square.scale(2).rotate(lite.PI / 4).next_to(circle, lite.DOWN, buff=0.4)
        self.assertAlmostEqual(circle._bounds()[1] - square._bounds()[3], 0.4)
        square.next_to(lite.ORIGIN, lite.UR, buff=0.5)
        self.assertAlmostEqual(square._bounds()[0], 0.5)
        self.assertAlmostEqual(square._bounds()[1], 0.5)

    def test_arrange_centers_row_and_preserves_first_child_when_requested(self):
        shapes = [lite.Square(), lite.Circle(radius=0.5), lite.Dot()]
        group = lite.VGroup(*shapes).arrange(buff=0.8)
        self.assertEqual(group.get_center(), lite.ORIGIN)
        for first, second in zip(shapes, shapes[1:]):
            self.assertAlmostEqual(second._bounds()[0] - first._bounds()[2], 0.8)
        shapes[0].shift(lite.UP * 3)
        start = shapes[0].get_center()
        group.arrange(lite.DOWN, buff=0.4, center=False, aligned_edge=lite.LEFT)
        self.assertEqual(shapes[0].get_center(), start)
        for first, second in zip(shapes, shapes[1:]):
            self.assertAlmostEqual(first._bounds()[1] - second._bounds()[3], 0.4)
            self.assertAlmostEqual(first._bounds()[0], second._bounds()[0])
        self.assertEqual(lite.VGroup().arrange().get_center(), lite.ORIGIN)

    def test_animated_layout_has_intermediate_states(self):
        result = render('g = VGroup(Square(), Circle()).arrange(RIGHT, buff=1)\nself.add(g)\nself.play(g.animate.arrange(DOWN, buff=0.5), run_time=2, rate_func=linear)')
        first, middle, last = [result['frames'][i]['mobjects'][0] for i in (0, 15, -1)]
        self.assertNotEqual(first['children'][1]['position'], middle['children'][1]['position'])
        self.assertNotEqual(last['children'][1]['position'], middle['children'][1]['position'])
        result = render('d = Dot(LEFT * 2)\nself.play(d.animate.next_to(ORIGIN, RIGHT, buff=0.5), run_time=2, rate_func=linear)')
        self.assertAlmostEqual(result['frames'][-1]['mobjects'][0]['position'][0], 0.58)

    def test_layout_rejects_unsupported_options_and_invalid_inputs(self):
        for direction in (lite.ORIGIN, (float('nan'), 0, 0)):
            with self.assertRaises(ValueError):
                lite.Square().next_to(lite.ORIGIN, direction)
        with self.assertRaises(NotImplementedError):
            lite.Dot().next_to(lite.ORIGIN, lite.OUT)
        with self.assertRaises(ValueError):
            lite.Dot().next_to(lite.ORIGIN, buff=float('inf'))
        with self.assertRaises(ValueError):
            lite.Dot().next_to((float('inf'), 0))
        with self.assertRaises(ValueError):
            lite.Dot().move_to((float('nan'), 0))
        with self.assertRaises(TypeError):
            lite.Dot().next_to(lite.ORIGIN, coor_mask=(1, 0, 0))
        with self.assertRaisesRegex(NotImplementedError, 'before scaling'):
            lite.VGroup(lite.Dot()).scale(2).arrange()

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
