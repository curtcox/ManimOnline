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
    def test_passing_flash_exact_window_and_reusable_source(self):
        source = lite.CubicBezier(lite.LEFT*3,lite.UP*2,lite.DOWN*2,lite.RIGHT*3).rotate(.4)
        source.set_stroke(color=lite.YELLOW,width=7).save_state()
        original = source.to_dict()
        scene = lite.Scene()
        flash = lite.ShowPassingFlash(source,time_width=.4,rate_func=lite.linear)
        flash.prepare(scene)
        expected = source.get_subcurve(.3,.7).to_dict()
        actual = flash.sample(.5)[0]
        for a, b in zip(actual['curves'][0],expected['curves'][0]):
            self.assertPointAlmostEqual(a,b)
        self.assertEqual(actual['stroke_color'],expected['stroke_color'])
        self.assertEqual(actual['stroke_width'],expected['stroke_width'])
        for alpha in (0,1):
            curve = flash.sample(alpha)[0]['curves'][0]
            for point in curve:
                self.assertPointAlmostEqual(point,curve[0])
        self.assertEqual(flash.states(1),{source:[]})
        flash.finish(scene)
        self.assertEqual(scene.mobjects,[])
        self.assertEqual(source.to_dict(),original)
        source.shift(lite.UP).restore()
        self.assertEqual(source.to_dict(),original)

    def test_passing_flash_groups_preserve_pivots_and_independent_styles(self):
        group = lite.VGroup(lite.Circle().shift(lite.LEFT*2),
                            lite.VGroup(lite.Square().shift(lite.RIGHT*2))).rotate(.7).scale(1.3).shift(lite.UP)
        original = group.to_dict()
        flash = lite.ShowPassingFlash(group,time_width=.2)
        flash.prepare(lite.Scene())
        middle = flash.sample(.5)[0]
        for key in ('position','angle','geometry_scale','geometry_center'):
            self.assertEqual(middle[key],original[key])
            self.assertEqual(middle['children'][1][key],original['children'][1][key])
        expected = group.children[0].get_subcurve(.4,.6).to_dict()
        for actual_curve, expected_curve in zip(middle['children'][0]['curves'],expected['curves']):
            for a,b in zip(actual_curve,expected_curve):
                self.assertPointAlmostEqual(a,b)
        self.assertEqual(group.to_dict(),original)

    def test_passing_flash_width_and_unsupported_inputs(self):
        for width in (-1,float('inf'),float('nan'),True,'wide'):
            with self.assertRaises(ValueError): lite.ShowPassingFlash(lite.Line(),time_width=width)
        source = lite.Circle()
        for width in (0,2):
            flash = lite.ShowPassingFlash(source,time_width=width)
            flash.prepare(lite.Scene())
            middle = flash.sample(.5)[0]
            if width == 0:
                self.assertTrue(all(p == middle['curves'][0][0] for p in middle['curves'][0]))
            else:
                self.assertEqual(middle,source.get_subcurve(0,1).to_dict())
        for source in (lite.Text('unsupported'),lite.Arrow(),lite.VGroup(lite.Circle(),lite.Text('unsupported'))):
            scene = lite.Scene()
            with self.assertRaises(TypeError): lite.ShowPassingFlash(source).prepare(scene)
            self.assertEqual(scene.mobjects,[])
        for source in (lite.VMobject(),lite.VGroup()):
            flash = lite.ShowPassingFlash(source)
            flash.prepare(lite.Scene())
            flash.sample(.5)

    def test_passing_flash_gallery_sequence_cleanup(self):
        result = json.loads(lite.render_scene((ROOT/'examples/passing_flash_scene.py').read_text()))
        self.assertEqual(result['duration'],9)
        self.assertEqual(len(result['frames'][30]['mobjects']),4)
        for index in (75,105):
            self.assertEqual(len(result['frames'][index]['mobjects']),3)
            self.assertEqual(result['frames'][index]['mobjects'][-1]['stroke_color'].upper(),lite.YELLOW)
        final = result['frames'][-1]['mobjects']
        self.assertEqual(len(final),2)
        self.assertEqual(final[0],result['frames'][0]['mobjects'][0])

    def test_partial_cubic_is_exact_with_transforms_and_independent_style(self):
        source = lite.CubicBezier((-2,0),(-1,3),(1,-2),(2,1)).rotate(.6).scale(1.7).shift(lite.UP)
        original = source.to_dict()
        partial = source.get_subcurve(.2,.8)
        self.assertEqual(partial.get_num_curves(), 1)
        for t in (0,.1,.25,.5,.9,1):
            expected = source._point_to_world(lite.VMobject._bezier_point(source.curves[0],.2+.6*t))
            for actual, value in zip(lite.VMobject._bezier_point(partial.curves[0],t),expected):
                self.assertAlmostEqual(actual,value)
        partial.set_color(lite.YELLOW)
        self.assertEqual(source.to_dict(),original)
        receiver = lite.VMobject(color=lite.RED,stroke_width=8)
        receiver.pointwise_become_partial(source,.2,.8)
        self.assertEqual(receiver.color,lite.RED)
        self.assertEqual(receiver.stroke_width,8)

    def test_partial_curve_count_parameter_and_exact_boundary_null_curve(self):
        path = lite.VMobject().set_points_as_corners([lite.ORIGIN,lite.RIGHT,lite.RIGHT*10])
        half = path.get_subcurve(0,.5)
        self.assertEqual(half.get_end(),lite.RIGHT)
        self.assertEqual(half.get_num_curves(),2)
        self.assertTrue(all(p == list(lite.RIGHT) for p in half.curves[-1]))
        middle = path.get_subcurve(.25,.75)
        self.assertEqual(middle.get_start(),lite.RIGHT*.5)
        self.assertEqual(middle.get_end(),lite.RIGHT*5.5)
        point = path.get_subcurve(.25,.25)
        self.assertEqual(point.get_start(),point.get_end())
        self.assertEqual(point.get_start(),lite.RIGHT*.5)

    def test_partial_disconnected_paths_keep_boundaries_and_source_checkpoint(self):
        path = lite.VMobject().start_new_path(lite.ORIGIN).add_line_to(lite.RIGHT*2)
        path.start_new_path(lite.RIGHT*10).add_line_to(lite.RIGHT*14)
        path.save_state()
        partial = path.get_subcurve(.25,.75)
        self.assertEqual(partial.subpath_lengths,[1,1])
        self.assertEqual(partial.get_start(),lite.RIGHT)
        self.assertEqual(partial.get_end(),lite.RIGHT*12)
        self.assertEqual(len(partial.get_subpaths()),2)
        path.pointwise_become_partial(path,.25,.75)
        self.assertEqual(path.get_points(),partial.get_points())
        path.restore()
        self.assertEqual(path.get_start(),lite.ORIGIN)
        self.assertEqual(path.get_end(),lite.RIGHT*14)
        ring = lite.Annulus().get_subcurve(.25,.75)
        self.assertEqual(ring.subpath_lengths,[4,5])
        self.assertEqual(ring.get_num_curves(),9)
        for actual, expected in zip(ring.get_end(),[-1,0,0]):
            self.assertAlmostEqual(actual,expected)

    def test_closed_subcurve_wrap_and_invalid_bounds_are_atomic(self):
        circle = lite.Circle().shift(lite.UP)
        self.assertTrue(circle.is_closed())
        wrapped = circle.get_subcurve(.75,.25)
        for actual, expected in zip(wrapped.get_start(),[0,0,0]):
            self.assertAlmostEqual(actual,expected)
        for actual, expected in zip(wrapped.get_end(),[0,2,0]):
            self.assertAlmostEqual(actual,expected)
        self.assertEqual(wrapped.get_num_curves(),5)
        self.assertEqual(len(lite._path_subpaths(wrapped.to_dict())),1)
        source = lite.CubicBezier(lite.ORIGIN,lite.UP,lite.UR,lite.RIGHT)
        before = source.to_dict()
        for a,b in [(True,.5), (float('nan'),1), (0,float('inf')),('0',1),(.8,.2)]:
            with self.assertRaises(ValueError): source.pointwise_become_partial(source,a,b)
            self.assertEqual(source.to_dict(),before)
        with self.assertRaises(TypeError): source.pointwise_become_partial(lite.Text('text'),0,1)
        self.assertEqual(source.to_dict(),before)
        source.pointwise_become_partial(source,-1,2)
        self.assertEqual(source.get_num_curves(),1)
        empty = lite.VMobject()
        source.pointwise_become_partial(empty,.2,.8)
        self.assertEqual(source.get_num_curves(),1)
        source.pointwise_become_partial(empty,0,1)
        self.assertFalse(source.has_points())

    def test_partial_curve_gallery_highlights_and_cleans_up(self):
        result = json.loads(lite.render_scene((ROOT/'examples/partial_curve_scene.py').read_text()))
        self.assertEqual(result['duration'],8)
        highlighted = result['frames'][60]['mobjects']
        self.assertEqual(len(highlighted),4)
        self.assertEqual(highlighted[2]['type'],'bezierpath')
        self.assertEqual(highlighted[2]['stroke_color'].upper(),lite.YELLOW)
        self.assertEqual(highlighted[3]['stroke_color'].upper(),lite.BLUE)
        self.assertEqual(len(result['frames'][-1]['mobjects']),2)

    def test_raw_points_round_trip_transforms_without_mutable_aliases(self):
        curve = lite.CubicBezier(lite.LEFT*2,lite.UL,lite.DR,lite.RIGHT*2)
        curve.rotate(lite.PI/3).scale(2).shift(lite.UP)
        before = [curve.point_from_proportion(a) for a in (0,.25,.5,.75,1)]
        points = curve.get_points()
        self.assertEqual(curve.get_num_points(), 4)
        self.assertTrue(curve.has_points())
        curve.set_points(points)
        self.assertEqual(curve.position, list(lite.ORIGIN))
        self.assertEqual(curve.geometry_scale, 1)
        self.assertEqual(curve.angle, 0)
        for alpha, expected in zip((0,.25,.5,.75,1), before):
            for actual, value in zip(curve.point_from_proportion(alpha), expected):
                self.assertAlmostEqual(actual, value)
        points[0][0] = 999
        self.assertNotEqual(curve.get_points()[0][0], 999)
        returned = curve.get_points()
        returned[1][0] = 999
        self.assertNotEqual(curve.get_points()[1][0], 999)
        self.assertEqual(len(lite.Circle().get_points()), 32)
        self.assertEqual(len(lite.Annulus().get_points()), 64)

    def test_raw_points_pending_append_and_clear_keep_styles_callbacks_checkpoint(self):
        path = lite.VMobject(color=lite.RED,stroke_width=7).set_points([lite.UP])
        callback = lambda m: None
        path.add_updater(callback).save_state()
        self.assertTrue(path.has_new_path_started())
        path.append_points([lite.UR,lite.RIGHT,lite.ORIGIN])
        self.assertFalse(path.has_new_path_started())
        self.assertEqual(path.get_num_points(), 4)
        self.assertEqual(path.get_end(), lite.ORIGIN)
        path.clear_points()
        self.assertFalse(path.has_points())
        self.assertEqual(path.get_subpaths(), [])
        for query in (path.get_start,path.get_end):
            with self.assertRaises(ValueError): query()
        path.restore()
        self.assertEqual(path.get_points(), [list(lite.UP)])
        self.assertEqual(path.stroke_width, 7)
        self.assertEqual(path.color, lite.RED)
        self.assertEqual(path.updaters, [callback])

    def test_raw_points_invalid_edits_are_atomic(self):
        path = lite.CubicBezier(lite.ORIGIN,lite.UP,lite.UR,lite.RIGHT).shift(lite.LEFT)
        before = path.to_dict()
        for points in [[lite.UP]*2, [lite.UP]*3, [lite.OUT]*4,
                       [[float('nan'),0]]*4, [[float('inf'),0]]*4]:
            with self.assertRaises((ValueError,NotImplementedError)): path.set_points(points)
            self.assertEqual(path.to_dict(), before)
            with self.assertRaises((ValueError,NotImplementedError)): path.append_points(points)
            self.assertEqual(path.to_dict(), before)
        with self.assertRaises(ValueError): path.add_subpath([lite.UP])
        with self.assertRaises(TypeError): path.append_vectorized_mobject(lite.Text('text'))
        self.assertEqual(path.to_dict(), before)

    def test_append_vector_outline_keeps_world_geometry_and_independent_provider(self):
        path = lite.CubicBezier(lite.LEFT,lite.UL,lite.UR,lite.RIGHT).rotate(.3).scale(2)
        original = path.get_points()
        ring = lite.Annulus(inner_radius=.5,outer_radius=1,arc_center=lite.UP*3)
        incoming = ring.get_points()
        path.start_new_path(lite.DOWN)
        path.append_vectorized_mobject(ring)
        self.assertEqual(path.get_points(), original + incoming)
        self.assertEqual(len(path.get_subpaths()), 3)
        ring.shift(lite.RIGHT*5)
        self.assertEqual(path.get_points(), original + incoming)
        self.assertEqual(path.color, lite.WHITE)
        path.add_subpath(lite.CubicBezier(lite.DOWN,lite.DL,lite.DR,lite.DOWN).get_points())
        self.assertEqual(len(path.get_subpaths()), 4)

    def test_point_array_gallery_edits_appends_and_restores(self):
        result = json.loads(lite.render_scene((ROOT/'examples/point_array_scene.py').read_text()))
        self.assertEqual(result['duration'], 8)
        edited = result['frames'][60]['mobjects'][0]
        self.assertEqual(len(edited['curves']), 17)
        self.assertEqual([len(p) for p in lite._path_subpaths(edited)], [1,8,8])
        final = result['frames'][-1]['mobjects'][0]
        seed = lite.CubicBezier((-3,-1),(-1,2),(1,-2),(3,1)).rotate(lite.PI/6)
        self.assertEqual(final['curves'], [seed.get_points()])
        self.assertEqual(final['color'], lite.BLUE)

    def test_disconnected_path_construction_pending_anchor_and_sampling(self):
        self.assertEqual(lite.VMobject().set_points_as_corners([lite.UP]).get_subpaths(), [])
        path = lite.VMobject().start_new_path(lite.ORIGIN)
        self.assertTrue(path.has_new_path_started())
        self.assertEqual(path.get_subpaths(), [])
        self.assertEqual(path.get_start(), lite.ORIGIN)
        self.assertEqual(path.point_from_proportion(.5), lite.ORIGIN)
        path.add_line_to(lite.RIGHT)
        self.assertFalse(path.has_new_path_started())
        path.start_new_path(lite.RIGHT*10).add_cubic_bezier_curve_to(lite.RIGHT*11,lite.RIGHT*12,lite.RIGHT*13)
        self.assertEqual([len(p) for p in path.get_subpaths()], [4,4])
        self.assertEqual(path.point_from_proportion(.25), lite.RIGHT)
        self.assertGreater(path.point_from_proportion(.251)[0], 10)
        self.assertEqual(path.get_end(), lite.RIGHT*13)
        before = path.to_dict()
        with self.assertRaises(NotImplementedError): path.start_new_path(lite.OUT)
        self.assertEqual(path.to_dict(), before)
        path.start_new_path(lite.UP)
        self.assertEqual(path.get_end(), lite.UP)
        path.start_new_path(lite.DOWN)
        self.assertEqual([len(p) for p in path.get_subpaths()], [4,4,4])
        self.assertTrue(path.has_new_path_started())
        path.set_points_as_corners([lite.ORIGIN,lite.RIGHT])
        self.assertNotIn('curves', path.__dict__)
        self.assertEqual(len(path.get_subpaths()), 1)

    def test_disconnected_path_closure_reverse_transforms_and_independence(self):
        path = lite.VMobject().set_points_as_corners([lite.ORIGIN,lite.RIGHT,lite.UP])
        path.close_path().start_new_path(lite.RIGHT*3).add_line_to(lite.RIGHT*4).close_path()
        self.assertEqual([len(p) for p in path.get_subpaths()], [12,8])
        for subpath in path.get_subpaths(): self.assertEqual(subpath[0], subpath[-1])
        saved = path.to_dict()
        path.close_path()
        self.assertEqual(path.to_dict(), saved)
        path.save_state().reverse_direction()
        self.assertEqual([len(p) for p in path.get_subpaths()], [8,12])
        path.restore()
        self.assertEqual(path.curves, saved['curves'])
        clone = path.copy().shift(lite.RIGHT)
        self.assertEqual(clone.get_subpaths()[0][0], lite.RIGHT)
        self.assertEqual(path.get_subpaths()[0][0], lite.ORIGIN)
        returned = clone.get_subpaths()
        returned[0].clear()
        self.assertEqual(len(clone.get_subpaths()[0]), 12)

    def test_disconnected_alignment_matches_each_contour_even_with_equal_total_counts(self):
        a = lite.VMobject().start_new_path(lite.ORIGIN).add_points_as_corners([lite.RIGHT,lite.UR])
        a.start_new_path(lite.LEFT*3).add_line_to(lite.LEFT*4)
        b = lite.VMobject().start_new_path(lite.UP).add_line_to(lite.UR)
        b.start_new_path(lite.DOWN*3).add_points_as_corners([lite.DR*3,lite.RIGHT*4])
        original = a.to_dict(), b.to_dict()
        first, last = lite._align_path_snapshots(*original)
        self.assertEqual(first['subpath_lengths'], [2,2])
        self.assertEqual(last['subpath_lengths'], [2,2])
        middle = lite.interpolate(first,last,.5)
        self.assertEqual([len(p) for p in lite._path_subpaths(middle)], [2,2])
        self.assertTrue(all(isinstance(n,int) for n in middle['subpath_lengths']))
        self.assertEqual((a.to_dict(),b.to_dict()), original)
        # Matching counts still need boundaries when their endpoints coincide
        # temporarily during interpolation.
        c = lite.VMobject().start_new_path(lite.ORIGIN).add_line_to(lite.RIGHT)
        c.start_new_path(lite.RIGHT*3).add_line_to(lite.RIGHT*4)
        d = lite.VMobject().start_new_path(lite.ORIGIN).add_line_to(lite.RIGHT*3)
        d.start_new_path(lite.RIGHT).add_line_to(lite.RIGHT*4)
        first, last = lite._align_path_snapshots(c.to_dict(),d.to_dict())
        middle = lite.interpolate(first,last,.5)
        self.assertEqual(middle['curves'][0][-1], middle['curves'][1][0])
        self.assertEqual([len(p) for p in lite._path_subpaths(middle)], [1,1])

    def test_annulus_morph_aligns_hole_with_collapsed_missing_contour(self):
        ring, square = lite.Annulus(), lite.Square()
        first, last = lite._align_path_snapshots(ring.to_dict(),square.to_dict())
        self.assertEqual(first['subpath_lengths'], [8,8])
        self.assertEqual(last['subpath_lengths'], [8,8])
        inner = lite._path_subpaths(first)[1]
        self.assertLess(inner[0][1][1], 0)
        null = lite._path_subpaths(last)[1]
        self.assertTrue(all(point == null[0][0] for curve in null for point in curve))
        result = render('ring = Annulus().save_state()\nself.add(ring)\nself.play(Transform(ring, Square()), run_time=2)\nself.play(Restore(ring), run_time=2)')
        self.assertEqual(len(result['frames'][15]['mobjects']), 1)
        self.assertEqual(result['frames'][15]['mobjects'][0]['subpath_lengths'], [8,8])
        self.assertEqual(result['frames'][-1]['mobjects'][0]['type'], 'annulus')

    def test_disconnected_gallery_morphs_and_restores_both_contours(self):
        result = json.loads(lite.render_scene((ROOT/'examples/subpath_scene.py').read_text()))
        self.assertEqual(result['duration'], 13)
        morph = result['frames'][105]['mobjects'][0]
        self.assertEqual(morph['subpath_lengths'], [8,8])
        collapse = result['frames'][135]['mobjects'][0]
        self.assertEqual(collapse['subpath_lengths'], [12,8])
        final = result['frames'][-1]['mobjects']
        self.assertEqual(len(final), 1)
        self.assertEqual([len(p) for p in lite._path_subpaths(final[0])], [4,4])
        self.assertEqual(final[0]['color'], lite.BLUE)

    def test_rounded_rectangle_contours_dimensions_and_radius_order(self):
        box = lite.RoundedRectangle()
        self.assertIsInstance(box, lite.Rectangle)
        self.assertIsInstance(box, lite.VMobject)
        self.assertEqual(box._bounds(), (-2,-1,2,1))
        self.assertEqual(box.get_start(), lite.Vector((2,.5,0)))
        self.assertEqual(box.get_end(), box.get_start())
        self.assertEqual(len(box.curves), 12)
        for first, second in zip(box.curves, box.curves[1:]):
            self.assertEqual(first[-1], second[0])
        varying = lite.RoundedRectangle(corner_radius=[.1,.2,.3,.4])
        for index, expected in [(0,[2,.6,0]),(3,[-1.9,1,0]),
                                (6,[-2,-.8,0]),(9,[1.7,-1,0])]:
            for actual, value in zip(varying.curves[index][0], expected):
                self.assertAlmostEqual(actual, value)
        repeated = lite.RoundedRectangle(corner_radius=[.1,.2])
        self.assertEqual(repeated.curves[0][0], [2,.8,0])
        concave = lite.RoundedRectangle(corner_radius=-.5)
        convex_mid = box.curves[0][-1]
        concave_mid = concave.curves[0][-1]
        self.assertGreater(convex_mid[0], concave_mid[0])
        self.assertGreater(convex_mid[1], concave_mid[1])
        box.rotate(lite.PI/2).scale(2).shift(lite.RIGHT)
        for actual, expected in zip(box.get_start(), [0,4,0]):
            self.assertAlmostEqual(actual, expected)

    def test_rounded_rectangle_degenerate_radii_and_invalid_inputs(self):
        for width, height, radius in [(4,2,0),(4,2,99),(4,2,-99),
                                       (0,2,.5),(4,0,.5),(0,0,.5)]:
            box = lite.RoundedRectangle(width=width, height=height, corner_radius=radius)
            self.assertEqual(box._bounds(), (-width/2,-height/2,width/2,height/2))
            self.assertEqual(box.get_start(), box.get_end())
            self.assertTrue(all(lite.math.isfinite(v) for v in box.point_from_proportion(.5)))
        for value in [True, float('nan'), float('inf'), '1', [], [False], [.2,float('inf')]]:
            with self.assertRaises(ValueError): lite.RoundedRectangle(corner_radius=value)
        for value in [-1,True,float('nan'),float('inf'),'1']:
            with self.assertRaises(ValueError): lite.RoundedRectangle(width=value)
            with self.assertRaises(ValueError): lite.RoundedRectangle(height=value)

    def test_rounded_rectangle_gallery_morph_and_restore(self):
        result = json.loads(lite.render_scene((ROOT/'examples/rounded_rectangle_scene.py').read_text()))
        self.assertEqual(result['duration'], 11)
        middle = result['frames'][105]['mobjects'][0]
        self.assertEqual(middle['type'], 'bezierpath')
        self.assertEqual(len(middle['curves']), 12)
        final = result['frames'][-1]['mobjects']
        self.assertEqual(len(final), 1)
        original = lite.RoundedRectangle(width=5,height=3,corner_radius=.6,color=lite.BLUE,fill_opacity=.25)
        self.assertEqual(final[0]['curves'], original.curves)
        self.assertEqual(final[0]['corner_radius'], .6)
        self.assertEqual(final[0]['color'], lite.BLUE)

    def test_rounded_rectangle_aligns_with_other_outlines(self):
        result = render('box = RoundedRectangle()\nself.add(box)\nself.play(Transform(box, Triangle()), run_time=2)')
        self.assertEqual(result['frames'][15]['mobjects'][0]['type'], 'bezierpath')
        self.assertEqual(len(result['frames'][15]['mobjects'][0]['curves']), 12)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['type'], 'triangle')

    def test_annulus_bounds_contour_order_and_validation(self):
        ring = lite.Annulus(inner_radius=1, outer_radius=2, arc_center=lite.UP)
        self.assertEqual(ring._bounds(), (-2,-1,2,3))
        self.assertEqual(ring.get_start(), lite.Vector((2,1,0)))
        self.assertEqual(ring.get_end(), lite.Vector((1,1,0)))
        for alpha, expected in [(1/3,[-2,1,0]), (5/6,[-1,1,0]), (1,[1,1,0])]:
            for actual, value in zip(ring.point_from_proportion(alpha), expected):
                self.assertAlmostEqual(actual, value)
        ring.rotate(lite.PI/2).scale(2).move_arc_center_to(lite.RIGHT)
        self.assertEqual(ring._bounds(), (-3,-4,5,4))
        self.assertEqual(ring.fill_opacity, 1)
        self.assertEqual(ring.stroke_width, 0)
        for inner, outer in [(0,0),(0,1),(1,1),(2,1)]:
            ring = lite.Annulus(inner_radius=inner, outer_radius=outer)
            self.assertEqual(ring._bounds()[2], max(inner,outer))
            self.assertEqual(ring.get_start()[0], outer)
            self.assertEqual(ring.point_from_proportion(1), ring.get_end())
            self.assertTrue(all(lite.math.isfinite(v) for v in ring.point_from_proportion(.5)))
        for invalid in [-1, True, float('inf'), float('nan'), '2']:
            with self.assertRaises(ValueError): lite.Annulus(inner_radius=invalid)
            with self.assertRaises(ValueError): lite.Annulus(outer_radius=invalid)
        with self.assertRaises(ValueError): lite.Annulus(mark_paths_closed=1)
        with self.assertRaises(NotImplementedError): lite.Annulus(arc_center=lite.OUT)

    def test_annulus_gallery_interpolates_radii_and_restores(self):
        result = json.loads(lite.render_scene((ROOT/'examples/annulus_scene.py').read_text()))
        self.assertEqual(result['duration'], 11)
        middle = result['frames'][105]['mobjects'][0]
        self.assertEqual(middle['type'], 'annulus')
        self.assertAlmostEqual(middle['inner_radius'], .95)
        self.assertAlmostEqual(middle['outer_radius'], 1.75)
        final = result['frames'][-1]['mobjects']
        self.assertEqual(len(final), 1)
        self.assertEqual(final[0]['inner_radius'], .7)
        self.assertEqual(final[0]['outer_radius'], 1.5)
        self.assertEqual(final[0]['color'], lite.BLUE)

    def test_sectors_have_closed_curved_outlines_and_native_style_defaults(self):
        ring = lite.AnnularSector(inner_radius=1, outer_radius=2)
        self.assertIsInstance(ring, lite.Arc)
        self.assertIsInstance(ring, lite.VMobject)
        self.assertEqual(ring.curves[0][0], [1,0,0])
        self.assertEqual(ring.curves[-1][-1], [1,0,0])
        self.assertEqual(len(ring.curves), 6)
        self.assertAlmostEqual(ring.curves[2][-1][1], 2)
        self.assertEqual(ring.fill_opacity, 1)
        self.assertEqual(ring.stroke_width, 0)
        wedge = lite.Sector(radius=2, angle=-lite.PI)
        self.assertEqual(wedge.inner_radius, 0)
        self.assertEqual(wedge.get_start(), lite.ORIGIN)
        self.assertEqual(wedge.get_end(), lite.ORIGIN)
        self.assertAlmostEqual(wedge.curves[4][-1][0], -2)
        for invalid in [-1, True, float('nan'), float('inf'), '2']:
            with self.assertRaises(ValueError): lite.Sector(radius=invalid)
            with self.assertRaises(ValueError): lite.AnnularSector(inner_radius=invalid)
        for inner, outer, angle in [(0,0,0), (1,1,lite.TAU), (2,1,-lite.PI)]:
            sector = lite.AnnularSector(inner_radius=inner, outer_radius=outer, angle=angle)
            self.assertEqual(sector.curves[0][0], sector.curves[-1][-1])
            self.assertTrue(all(lite.math.isfinite(v) for v in sector.point_from_proportion(.5)))
        with self.assertRaises(NotImplementedError): lite.Sector(angle=2*lite.TAU)
        with self.assertRaises(NotImplementedError): lite.Sector(arc_center=lite.OUT)

    def test_sector_transformed_center_and_path_queries(self):
        sector = lite.Sector(radius=2, arc_center=lite.RIGHT)
        self.assertEqual(sector.get_arc_center(), lite.RIGHT)
        sector.rotate(lite.PI/2)
        sector.move_arc_center_to(lite.UP)
        for actual, expected in zip(sector.get_arc_center(), lite.UP):
            self.assertAlmostEqual(actual, expected)
        sector.reverse_direction()
        for point in [sector.point_from_proportion(0), sector.point_from_proportion(.5),
                      sector.point_from_proportion(1)]:
            self.assertTrue(all(lite.math.isfinite(v) for v in point))
        with self.assertRaises(ValueError): sector.move_arc_center_to([float('nan'),0,0])
        for actual, expected in zip(sector.get_arc_center(), lite.UP):
            self.assertAlmostEqual(actual, expected)

    def test_sector_gallery_aligns_unequal_curves_and_restores(self):
        result = json.loads(lite.render_scene((ROOT/'examples/sector_scene.py').read_text()))
        self.assertEqual(result['duration'], 10)
        middle = result['frames'][90]['mobjects'][1]
        self.assertEqual(middle['type'], 'bezierpath')
        self.assertEqual(len(middle['curves']), 14)
        final = result['frames'][-1]['mobjects']
        self.assertEqual(len(final), 2)
        self.assertEqual(final[1]['inner_radius'], .7)
        self.assertEqual(final[1]['outer_radius'], 1.5)
        self.assertEqual(final[1]['arc_angle'], -3*lite.PI/2)
        self.assertAlmostEqual(final[0]['angle'], lite.PI/2)
        for shape in final:
            self.assertEqual(shape['curves'][0][0], shape['curves'][-1][-1])

    def test_ellipse_dimensions_path_and_rotated_bounds(self):
        ellipse = lite.Ellipse(width=4, height=2).rotate(lite.PI/2).shift(lite.RIGHT)
        for actual, expected in zip(ellipse._bounds(), [0, -2, 2, 2]):
            self.assertAlmostEqual(actual, expected)
        for alpha, expected in [(0, [1, 2, 0]), (.25, [0, 0, 0]), (.5, [1, -2, 0])]:
            for actual, value in zip(ellipse.point_from_proportion(alpha), expected):
                self.assertAlmostEqual(actual, value)
        self.assertEqual(lite.Ellipse().to_dict()['width'], 2)
        self.assertEqual(lite.Ellipse().to_dict()['height'], 1)
        self.assertEqual(lite.Ellipse(width=0, height=0)._bounds(), (0,0,0,0))
        for invalid in [-1, True, float('nan'), float('inf'), '2']:
            with self.assertRaises(ValueError): lite.Ellipse(width=invalid)
            with self.assertRaises(ValueError): lite.Ellipse(height=invalid)

    def test_ellipse_morph_alignment_and_gallery_restoration(self):
        ellipse = lite.Ellipse(width=4, height=2)
        curves = lite._path_curves(ellipse.to_dict())
        self.assertEqual(len(curves), 8)
        self.assertEqual(curves[0][0], [2, 0, 0])
        self.assertAlmostEqual(curves[2][0][1], 1)
        result = json.loads(lite.render_scene((ROOT/'examples/ellipse_scene.py').read_text()))
        self.assertEqual(result['duration'], 10)
        middle = result['frames'][90]['mobjects'][0]
        self.assertEqual(middle['type'], 'bezierpath')
        self.assertEqual(len(middle['curves']), 8)
        final = result['frames'][-1]['mobjects'][0]
        self.assertEqual(final['type'], 'ellipse')
        self.assertEqual(final['width'], 4)
        self.assertEqual(final['height'], 2)
        self.assertAlmostEqual(final['angle'], lite.PI/6)
        self.assertEqual(len(result['frames'][-1]['mobjects']), 1)

    def test_trace_tracks_sampled_geometry_and_serializes_without_callbacks(self):
        result = render("""dot = Dot(LEFT * 2)
trace = TracedPath(dot.get_center)
self.add(trace, dot)
self.play(dot.animate.shift(RIGHT * 4), run_time=2, rate_func=linear)
trace.clear_updaters()
self.wait(1)""")
        middle = result['frames'][15]['mobjects'][0]
        self.assertEqual(middle['vertices'][0], [-2, 0, 0])
        self.assertEqual(middle['vertices'][-1], [0, 0, 0])
        self.assertNotIn('traced_point_func', middle)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['vertices'][-1], [2, 0, 0])
        self.assertEqual(result['frames'][0]['mobjects'][0]['vertices'], [[-2, 0, 0]]*2)

    def test_trace_dissipation_suspension_copy_and_checkpoint(self):
        point = [0, 0, 0]
        trace = lite.TracedPath(lambda:point, dissipating_time=.2)
        trace.update(0)
        for index in range(1, 7):
            point[0] = index
            trace.update(.1)
        self.assertLessEqual(len(trace.vertices), 4)
        self.assertEqual(trace.get_end(), lite.Vector(point))
        trace.save_state()
        before = trace.to_dict()
        trace.suspend_updating().update(.5)
        self.assertEqual(trace.to_dict(), before)
        trace.resume_updating()
        clone = trace.copy()
        point[0] = 9
        clone.update(.1)
        self.assertEqual(clone.get_end()[0], 9)
        self.assertEqual(trace.get_end()[0], 6)
        trace.update(.1).restore()
        self.assertEqual(trace.to_dict(), before)
        trace.clear_updaters().update(1)
        self.assertEqual(trace.to_dict(), before)

    def test_trace_transforms_preserve_old_world_points_and_errors_are_atomic(self):
        point = [1, 0, 0]
        trace = lite.TracedPath(lambda:point)
        trace.update()
        point[0] = 2
        trace.update()
        trace.rotate(lite.PI/2).shift(lite.UP)
        old = trace.get_start()
        point[:] = [3, 2, 0]
        trace.update()
        for a, b in zip(trace.get_start(), old): self.assertAlmostEqual(a, b)
        self.assertEqual(trace.get_end(), lite.Vector(point))
        before = trace.to_dict()
        for invalid in [[float('nan'), 0, 0], [0, 0, 1]]:
            point[:] = invalid
            with self.assertRaises((ValueError, NotImplementedError)): trace.update(.1)
            self.assertEqual(trace.to_dict(), before)
        with self.assertRaises(TypeError): lite.TracedPath(3)
        for invalid in [-1, float('nan'), float('inf'), '1']:
            with self.assertRaises(ValueError): lite.TracedPath(lambda:lite.ORIGIN, dissipating_time=invalid)

    def test_trace_become_keeps_provider_clock_and_callback(self):
        point = [1, 0, 0]
        trace = lite.TracedPath(lambda:point, dissipating_time=1)
        trace.update(.1)
        callback = trace.get_updaters()[0]
        trace.become(lite.VMobject().set_points_as_corners([lite.ORIGIN, lite.UP]))
        self.assertAlmostEqual(trace.time, 1.1)
        self.assertEqual(trace.dissipating_time, 1)
        self.assertIs(trace.get_updaters()[0], callback)
        point[0] = 3
        trace.update(.1)
        self.assertEqual(trace.get_end(), lite.Vector(point))
        self.assertAlmostEqual(trace.time, 1.2)

    def test_trace_gallery_tail_disappears_and_full_trail_freezes(self):
        result = json.loads(lite.render_scene((ROOT/'examples/trace_scene.py').read_text()))
        self.assertEqual(result['duration'], 7)
        full, tail = result['frames'][45]['mobjects'][2:]
        self.assertGreater(len(full['vertices']), len(tail['vertices']))
        self.assertAlmostEqual(full['vertices'][-1][0], -3)
        self.assertAlmostEqual(full['vertices'][-1][1], -1)
        waiting = result['frames'][89]['mobjects']
        self.assertGreater(len(waiting[2]['vertices']), 50)
        for point in waiting[3]['vertices']:
            self.assertAlmostEqual(point[0], 4)
            self.assertAlmostEqual(point[1], 0)
        self.assertEqual(result['frames'][-1]['mobjects'], [])

    def test_numeric_label_formatting_and_integer_rounding(self):
        self.assertEqual(lite.DecimalNumber().text, '0.00')
        number = lite.DecimalNumber(1234.125, num_decimal_places=3, include_sign=True,
                                    show_ellipsis=True, unit=' kg')
        self.assertEqual(number.text, '+1,234.125… kg')
        number.set_value(-.0001)
        self.assertEqual(number.text, '+0.000… kg')
        self.assertEqual(lite.DecimalNumber(-0.0).text, '0.00')
        self.assertEqual(lite.DecimalNumber(1234, group_with_commas=False).text, '1234.00')
        for value, expected in [(2.5, 2), (3.5, 4), (-2.5, -2)]:
            integer = lite.Integer(value)
            self.assertEqual(integer.get_value(), expected)
            self.assertEqual(integer.text, str(expected))

    def test_numeric_validation_is_atomic_and_copies_are_independent(self):
        number = lite.DecimalNumber(1).shift(lite.RIGHT).set_color(lite.BLUE).save_state()
        before = number.to_dict()
        for invalid in [float('nan'), float('inf'), '2', complex(1, 2)]:
            with self.assertRaises(ValueError): number.set_value(invalid)
            with self.assertRaises(ValueError): number.increment_value(invalid)
            self.assertEqual(number.to_dict(), before)
        for options in [dict(num_decimal_places=-1), dict(num_decimal_places=13),
                        dict(num_decimal_places=2.5), dict(num_decimal_places=True),
                        dict(include_sign=1), dict(unit=3), dict(unit='x'*257),
                        dict(font_size=0), dict(font_size=float('nan'))]:
            with self.assertRaises(ValueError): lite.DecimalNumber(**options)
        clone = number.copy().increment_value(3)
        self.assertEqual(number.get_value(), 1)
        self.assertEqual(clone.get_value(), 4)
        number.set_value(9).restore()
        self.assertEqual(number.get_value(), 1)
        self.assertEqual(number.get_center(), lite.RIGHT)
        self.assertEqual(number.color, lite.BLUE)

    def test_numeric_animation_formats_intermediate_values_and_restoration(self):
        result = render("""number = DecimalNumber(0).save_state()
self.add(number)
self.play(number.animate.set_value(4), run_time=2, rate_func=linear)
self.play(Succession(number.animate.increment_value(1), number.animate.increment_value(1)))
self.play(Restore(number), run_time=2, rate_func=linear)""")
        self.assertEqual(result['frames'][15]['mobjects'][0]['text'], '2.00')
        self.assertEqual(result['frames'][60]['mobjects'][0]['text'], '6.00')
        self.assertEqual(result['frames'][75]['mobjects'][0]['text'], '3.00')
        self.assertEqual(result['frames'][-1]['mobjects'][0]['text'], '0.00')

    def test_numeric_labels_can_become_plain_text_or_geometry(self):
        number = lite.DecimalNumber(3)
        number.become(lite.Text('done'))
        self.assertEqual(number.to_dict()['text'], 'done')
        number.become(lite.Circle())
        self.assertEqual(number.to_dict()['type'], 'circle')
        result = render("""number = DecimalNumber(3)
self.add(number)
self.play(Transform(number, Text('done')))
self.wait(1)""")
        self.assertEqual(result['frames'][-1]['mobjects'][0]['text'], 'done')

    def test_numeric_gallery_updaters_follow_samples_and_keep_old_frames(self):
        result = json.loads(lite.render_scene((ROOT/'examples/numeric_scene.py').read_text()))
        self.assertEqual(result['duration'], 9)
        middle = result['frames'][45]['mobjects']
        self.assertEqual(middle[1]['text'], '+1.00')
        self.assertEqual(middle[1]['position'], [1, 1, 0])
        self.assertEqual(middle[2]['text'], '1')
        self.assertEqual(result['frames'][75]['mobjects'][3]['text'], '1,750 points')
        self.assertEqual(result['frames'][-1]['mobjects'][3]['text'], '1,000 points')
        self.assertEqual(result['frames'][0]['mobjects'][1]['text'], '-2.00')

    def test_become_keeps_identity_callbacks_checkpoint_and_independent_target(self):
        source = lite.Circle().save_state()
        callback = lambda m:m.set_color(lite.GREEN)
        source.add_updater(callback)
        target = lite.Square(side_length=3).shift(lite.RIGHT)
        self.assertIs(source.become(target), source)
        self.assertEqual(source.to_dict()['type'], 'square')
        self.assertEqual(source.get_center(), lite.RIGHT)
        target.shift(lite.RIGHT)
        self.assertEqual(source.get_center(), lite.RIGHT)
        self.assertEqual(source.get_updaters(), [callback])
        source.restore()
        self.assertEqual(source.to_dict()['type'], 'circle')
        self.assertEqual(source.get_updaters(), [callback])
        before=source.to_dict()
        for invalid in [3,lite.ValueTracker(),lite.MovingCameraScene().camera.frame]:
            with self.assertRaises((TypeError,ValueError)): source.become(invalid)
            self.assertEqual(source.to_dict(),before)

    def test_become_group_preserves_prefix_links_and_aligns_shared_aliases(self):
        first = lite.Circle()
        group = lite.Group(first)
        group.become(lite.Group(lite.Square(),lite.Triangle()))
        self.assertIs(group[0], first)
        self.assertEqual(first.to_dict()['type'],'square')
        self.assertEqual(len(group),2)
        shared = lite.Circle()
        group.become(lite.Group(lite.Group(shared),lite.Group(shared)))
        self.assertIs(group[0].children[0],group[1].children[0])
        group.become(lite.Group(lite.Group(lite.Square()),lite.Group(lite.Triangle())))
        self.assertIsNot(group[0].children[0],group[1].children[0])
        self.assertEqual(group[0].children[0].to_dict()['type'],'square')
        self.assertEqual(group[1].children[0].to_dict()['type'],'triangle')
        group.become(lite.Group())
        self.assertEqual(len(group),0)

    def test_redraw_rebuilds_sampled_geometry_and_copies_update_themselves(self):
        tracker=lite.ValueTracker(1)
        circle=lite.always_redraw(lambda:lite.Circle(radius=tracker.get_value()))
        original=circle.copy()
        scene=lite.Scene().add(tracker,circle)
        scene.play(tracker.animate.set_value(3),run_time=2,rate_func=lite.linear)
        self.assertEqual(scene.frames[15]['mobjects'][0]['radius'],2)
        self.assertEqual(circle.radius,3)
        tracker.set_value(4)
        original.update()
        self.assertEqual(original.radius,4)
        self.assertEqual(circle.radius,3)
        self.assertEqual(len(circle.get_updaters()),1)
        self.assertEqual(scene.frames[15]['mobjects'][0]['radius'],2)
        circle.suspend_updating().update()
        self.assertEqual(circle.radius,3)
        circle.resume_updating()
        self.assertEqual(circle.radius,4)
        circle.clear_updaters()
        tracker.set_value(2)
        circle.update()
        self.assertEqual(circle.radius,4)

    def test_redraw_errors_leave_last_valid_geometry_and_gallery_freezes(self):
        with self.assertRaises(TypeError): lite.always_redraw(3)
        with self.assertRaises(TypeError): lite.always_redraw(lambda:3)
        valid=[True]
        circle=lite.always_redraw(lambda:lite.Circle() if valid[0] else 3)
        before=circle.to_dict()
        valid[0]=False
        with self.assertRaises(TypeError): circle.update()
        self.assertEqual(circle.to_dict(),before)
        result=json.loads(lite.render_scene((ROOT/'examples/redraw_scene.py').read_text()))
        self.assertEqual(result['duration'],8)
        self.assertEqual(result['frames'][60]['mobjects'][0]['radius'],1.5)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['radius'],1)
        self.assertEqual(result['frames'][-1]['mobjects'][1]['children'][0]['side_length'],.5)

    def test_value_tracker_values_arithmetic_identity_and_validation(self):
        tracker = lite.ValueTracker(2)
        original = tracker
        self.assertEqual((tracker + 3).get_value(), 5)
        self.assertEqual(tracker.get_value(), 2)
        tracker += 3
        tracker *= 2
        tracker -= 2
        tracker /= 2
        tracker **= 2
        tracker //= 3
        tracker %= 4
        self.assertIs(tracker, original)
        self.assertEqual(tracker.get_value(), 1)
        self.assertFalse(lite.ValueTracker())
        self.assertTrue(tracker)
        for invalid in [float('inf'),float('nan'),complex(1,2),'3',lite.Circle()]:
            with self.assertRaises(ValueError): tracker.set_value(invalid)
            self.assertEqual(tracker.get_value(), 1)
        with self.assertRaises(ZeroDivisionError): tracker /= 0
        self.assertEqual(tracker.get_value(), 1)
        tracker.save_state().increment_value(3).restore()
        self.assertEqual(tracker.get_value(), 1)
        tracker.copy().increment_value(9)
        self.assertEqual(tracker.get_value(), 1)

    def test_value_tracker_animation_drives_followers_and_relative_succession(self):
        scene = lite.Scene()
        tracker = lite.ValueTracker(0)
        dot = lite.Dot().add_updater(lambda m:m.move_to(lite.RIGHT*tracker.get_value()))
        scene.add(dot)
        scene.play(tracker.animate.set_value(4),run_time=2,rate_func=lite.linear)
        self.assertEqual(scene.frames[15]['mobjects'][0]['position'], [2,0,0])
        self.assertTrue(all(len(f['mobjects'])==1 for f in scene.frames))
        self.assertEqual(tracker.get_value(), 4)
        scene.play(lite.Succession(tracker.animate.increment_value(2),tracker.animate.increment_value(2)),rate_func=lite.linear)
        self.assertEqual(scene.frames[45]['mobjects'][0]['position'], [6,0,0])
        self.assertEqual(dot.get_center(), lite.RIGHT*8)
        scene.play(lite.Restore(tracker.save_state().increment_value(2)))
        self.assertEqual(tracker.get_value(), 8)

    def test_time_based_tracker_and_grouped_tracker_stay_invisible(self):
        scene = lite.Scene()
        tracker = lite.ValueTracker().add_updater(lambda m,dt:m.increment_value(dt))
        dot = lite.Dot().add_updater(lambda m:m.move_to(lite.RIGHT*tracker.get_value()))
        scene.add(tracker,dot).wait(2)
        self.assertAlmostEqual(tracker.get_value(), 2)
        self.assertAlmostEqual(dot.get_center()[0], 2)
        self.assertEqual(len(scene.frames[15]['mobjects']), 1)
        self.assertAlmostEqual(scene.frames[15]['mobjects'][0]['position'][0], 1)
        scene.remove(tracker).wait(1)
        self.assertAlmostEqual(tracker.get_value(), 2)
        group = lite.Group(tracker, lite.Circle())
        self.assertEqual(group.to_dict()['children'][0]['type'], 'valuetracker')

    def test_value_tracker_gallery_keeps_connector_on_tracked_shapes(self):
        result = json.loads(lite.render_scene((ROOT/'examples/value_tracker_scene.py').read_text()))
        self.assertEqual(result['duration'], 7)
        midpoint = result['frames'][30]['mobjects']
        self.assertEqual(len(midpoint), 3)
        self.assertEqual(midpoint[0]['position'], [0,-1,0])
        self.assertEqual(midpoint[1]['position'], [0,1,0])
        self.assertEqual(midpoint[2]['start'], [0,-1,0])
        self.assertEqual(midpoint[2]['end'], [0,1,0])
        self.assertEqual(result['frames'][-1]['mobjects'][0]['position'], [0,-1,0])

    def test_time_updaters_advance_wait_and_unanimated_play_objects(self):
        scene = lite.Scene()
        dot = lite.Dot().add_updater(lambda m, dt:m.shift(lite.RIGHT * dt))
        scene.add(dot).wait(2)
        self.assertAlmostEqual(dot.get_center()[0], 2)
        self.assertAlmostEqual(scene.frames[15]['mobjects'][0]['position'][0], 1)
        scene.play(lite.Create(lite.Circle()), run_time=1)
        self.assertAlmostEqual(dot.get_center()[0], 3)
        self.assertAlmostEqual(scene.frames[44]['mobjects'][0]['position'][0], 3 - 1/lite.FPS)
        self.assertNotIn('updaters', dot.to_dict())

    def test_followers_query_sampled_animation_and_camera_tracks_during_play(self):
        scene = lite.MovingCameraScene()
        dot = lite.Dot()
        follower = lite.Square().add_updater(lambda m:m.move_to(dot.get_center()+lite.UP))
        scene.camera.frame.add_updater(lambda m:m.move_to(dot))
        dot.add_updater(lambda m, dt:m.shift(lite.DOWN * dt))
        scene.add(dot, follower)
        scene.play(dot.animate.shift(lite.RIGHT*4), run_time=2, rate_func=lite.linear)
        midpoint = scene.frames[15]
        self.assertEqual(midpoint['mobjects'][1]['position'], [2,1,0])
        self.assertEqual(midpoint['camera']['frame_center'], [2,0,0])
        self.assertEqual(dot.get_center(), lite.RIGHT*4)
        self.assertEqual(follower.get_center(), lite.RIGHT*4+lite.UP)
        self.assertEqual(scene.camera.frame_center, lite.RIGHT*4)
        scene.wait(1)
        self.assertAlmostEqual(dot.get_center()[1], -1)
        self.assertAlmostEqual(scene.camera.frame_center[1], -1)

    def test_updater_management_recursive_suspension_and_shared_family_dedup(self):
        events = []
        def first(m): events.append('first')
        def timed(m, dt): events.append(dt)
        child = lite.Circle().add_updater(first)
        child.add_updater(timed, index=0, call_updater=True)
        self.assertEqual(events, [0])
        self.assertTrue(child.has_time_based_updater())
        self.assertEqual(child.get_time_based_updaters(), [timed])
        group = lite.Group(child)
        self.assertEqual(group.get_family_updaters(), [timed, first])
        group.suspend_updating().update(1)
        self.assertEqual(events, [0])
        group.resume_updating()
        self.assertEqual(events, [0,0,'first'])
        events.clear()
        lite.Scene().add(group, lite.Group(child)).wait(1/lite.FPS)
        self.assertEqual(events, [0,'first',1/lite.FPS,'first'])
        child.remove_updater(first).remove_updater(first)
        self.assertEqual(child.get_updaters(), [timed])
        group.clear_updaters()
        self.assertFalse(child.has_time_based_updater())
        with self.assertRaises(TypeError): child.add_updater(3)
        with self.assertRaises(ValueError): child.update(float('nan'))

    def test_updater_failure_restores_live_sampled_geometry(self):
        scene = lite.Scene()
        circle = lite.Circle()
        def fail(m):
            if circle.get_center()[0] > 0: raise RuntimeError('updater failed')
        follower = lite.Dot().add_updater(fail)
        scene.add(circle, follower)
        before = circle.to_dict()
        with self.assertRaisesRegex(RuntimeError, 'updater failed'):
            scene.play(circle.animate.shift(lite.RIGHT), rate_func=lite.linear)
        self.assertEqual(circle.to_dict(), before)
        self.assertNotIn('_sampled_geometry_center', circle.__dict__)

    def test_transform_keeps_source_updaters_and_updater_gallery(self):
        scene = lite.Scene()
        source = lite.Circle()
        updater = lambda m,dt:m.shift(lite.UP*dt)
        source.add_updater(updater).save_state()
        scene.play(lite.Transform(source,lite.Square().shift(lite.RIGHT)))
        self.assertEqual(source.get_updaters(), [updater])
        self.assertEqual(source.get_center(), lite.RIGHT)
        source.restore()
        self.assertEqual(source.get_updaters(), [updater])
        result = json.loads(lite.render_scene((ROOT/'examples/updater_scene.py').read_text()))
        self.assertEqual(result['duration'], 6)
        midpoint = result['frames'][45]
        self.assertAlmostEqual(midpoint['mobjects'][0]['position'][0], 0)
        self.assertEqual(midpoint['mobjects'][1]['position'], [0,1,0])
        self.assertEqual(midpoint['camera']['frame_center'], [0,0,0])
        self.assertEqual(result['frames'][-1]['mobjects'][1]['position'], [2,1,0])

    def test_auto_zoom_fits_wide_and_tall_bounds_without_eager_animation(self):
        scene = lite.MovingCameraScene()
        camera = scene.camera
        shapes = [lite.Square().shift(lite.LEFT * 3), lite.Circle().shift(lite.RIGHT * 3)]
        before = camera.frame.to_dict()
        animation = camera.auto_zoom(iter(shapes), margin=2)
        self.assertEqual(camera.frame.to_dict(), before)
        scene.add(*shapes).play(animation, run_time=2, rate_func=lite.linear)
        self.assertEqual(scene.frames[15]['camera']['frame_width'], 13)
        self.assertEqual(camera.frame_width, 10)
        self.assertEqual(camera.frame_height, 5.625)
        tall = lite.Rectangle(width=1, height=6).shift(lite.UP * 2)
        self.assertIs(camera.auto_zoom(tall, margin=1, animate=False), camera.frame)
        self.assertEqual(camera.frame_height, 7)
        self.assertEqual(camera.frame_center, lite.UP * 2)

    def test_camera_visibility_filter_includes_partial_overlap_and_transformed_group(self):
        camera = lite.MovingCameraScene().camera
        camera.frame_center = lite.RIGHT * 2
        edge = lite.Square().shift(lite.RIGHT * 11)
        outside = lite.Circle().shift(lite.RIGHT * 20)
        self.assertTrue(camera.is_in_frame(edge))
        self.assertFalse(camera.is_in_frame(outside))
        camera.auto_zoom([camera.frame, edge, outside], margin=1,
                         only_mobjects_in_frame=True, animate=False)
        self.assertEqual(camera.frame_center, lite.RIGHT * 11)
        self.assertEqual(camera.frame_height, 3)
        group = lite.VGroup(lite.Square().shift(lite.LEFT * 2), lite.Circle().shift(lite.RIGHT * 2))
        group.scale(2).rotate(lite.PI / 2).shift(lite.UP)
        camera.auto_zoom(group, margin=2, animate=False)
        self.assertAlmostEqual(camera.frame_height, 14)
        self.assertEqual(camera.frame_center, lite.UP)

    def test_camera_framing_failures_preserve_view_and_checkpoints(self):
        camera = lite.MovingCameraScene().camera
        camera.frame.save_state()
        before = camera.frame.to_dict()
        for objects, options in [([], {}), ([camera.frame], {}), ([lite.Circle(), object()], {}),
                                 ([lite.Circle()], {'margin':float('nan')}),
                                 ([lite.Circle()], {'margin':-2}),
                                 ([lite.Circle().shift(lite.RIGHT*30)], {'only_mobjects_in_frame':True}),
                                 ([lite.Text('unknown metrics')], {}),
                                 ([lite.Circle().shift((0,0,1))], {})]:
            with self.assertRaises((ValueError, TypeError, NotImplementedError)):
                camera.auto_zoom(objects, animate=False, **options)
            self.assertEqual(camera.frame.to_dict(), before)
        camera.auto_zoom(lite.Circle().shift(lite.RIGHT*3), margin=1, animate=False)
        camera.frame.restore()
        self.assertEqual(camera.frame.to_dict(), before)

    def test_auto_zoom_gallery_frames_and_restores(self):
        result = json.loads(lite.render_scene((ROOT/'examples/auto_zoom_scene.py').read_text()))
        self.assertEqual(result['duration'], 9)
        self.assertEqual(result['frames'][60]['camera']['frame_width'], 8)
        self.assertEqual(result['frames'][105]['camera']['frame_center'], [-2,0,0])
        self.assertEqual(result['frames'][105]['camera']['frame_height'], 3)
        self.assertEqual(result['frames'][-1]['camera']['frame_width'], 16)

    def test_moving_camera_samples_pan_zoom_and_exact_restoration(self):
        source = "from manim import *\nclass Demo(MovingCameraScene):\n    def construct(self):\n        frame=self.camera.frame.save_state()\n        self.add(Circle())\n        self.play(frame.animate.move_to(RIGHT*2).scale(.5),run_time=2,rate_func=linear)\n        self.play(Restore(frame),run_time=2,rate_func=linear)"
        result=json.loads(lite.render_scene(source))
        camera=result['frames'][15]['camera']
        self.assertEqual(camera['frame_center'],[1,0,0])
        self.assertEqual(camera['frame_width'],12)
        self.assertEqual(camera['frame_height'],6.75)
        self.assertEqual(result['frames'][30]['camera']['frame_center'],[2,0,0])
        self.assertEqual(result['frames'][-1]['camera']['frame_center'],[0,0,0])
        self.assertEqual(result['frames'][-1]['camera']['frame_width'],16)
        self.assertTrue(all(len(frame['mobjects'])==1 for frame in result['frames']))

    def test_camera_sequential_relative_motion_and_completed_group_hold(self):
        scene=lite.MovingCameraScene()
        frame=scene.camera.frame
        scene.play(lite.Succession(frame.animate.shift(lite.RIGHT), frame.animate.shift(lite.RIGHT)),rate_func=lite.linear)
        self.assertEqual(scene.frames[15]['camera']['frame_center'],[1,0,0])
        self.assertEqual(frame.get_center(),lite.RIGHT*2)
        scene.play(frame.animate.scale(.5),lite.Create(lite.Circle(),run_time=2),rate_func=lite.linear)
        self.assertEqual(scene.frames[45]['camera']['frame_width'],8)
        self.assertEqual(len(scene.frames[45]['mobjects']),1)
        scene.clear().wait(1)
        self.assertEqual(scene.frames[-1]['camera']['frame_center'],[2,0,0])

    def test_camera_frame_validation_and_dimension_setters(self):
        scene=lite.MovingCameraScene(camera_config={'pixel_width':600,'pixel_height':600,'frame_height':8})
        frame=scene.camera.frame
        self.assertEqual(lite.MovingCameraScene(camera_config={'frame_width':8}).camera.frame_width,8)
        with self.assertRaises(ValueError):
            lite.VGroup(frame)
        frame.set_width(4)
        self.assertEqual(frame.get_height(),4)
        scene.camera.frame_height=6
        self.assertEqual(frame.get_width(),6)
        scene.play(frame.animate.set_height(3))
        self.assertEqual(scene.camera.frame_height,3)
        before=frame.to_dict()
        for operation in (lambda:frame.scale(0),lambda:frame.set_width(-1),lambda:frame.shift((0,0,1)),lambda:frame.rotate(1)):
            with self.assertRaises((ValueError,NotImplementedError)):
                operation()
            self.assertEqual(frame.to_dict(),before)
        with self.assertRaises(ValueError):
            scene.play(lite.Transform(frame,lite.Circle()))

    def test_moving_camera_gallery_reaches_focus_and_restores(self):
        result=json.loads(lite.render_scene((ROOT/'examples/moving_camera_scene.py').read_text()))
        self.assertEqual(result['duration'],9)
        camera=result['frames'][60]['camera']
        self.assertEqual(camera['frame_width'],8)
        self.assertEqual(camera['frame_center'],[2,0,0])
        self.assertEqual(result['frames'][-1]['camera']['frame_width'],16)
        self.assertEqual(result['frames'][-1]['camera']['frame_center'],[0,0,0])

    def test_configuration_is_isolated_between_successful_and_failed_sources(self):
        source = "from manim import *\nconfig.pixel_width=600\nconfig.pixel_height=600\nconfig.frame_width=8\nconfig['background_color']=WHITE\nclass Demo(Scene):\n    def construct(self): self.add(Circle())"
        result = json.loads(lite.render_scene(source))
        camera = result['frames'][0]['camera']
        self.assertEqual(camera,dict(pixel_width=600,pixel_height=600,frame_width=8,frame_height=8,background_color=lite.WHITE))
        with self.assertRaises(RuntimeError):
            lite.render_scene("from manim import *\nconfig.background_color=RED\nraise RuntimeError('failed')")
        defaults = render('self.add(Circle())')['frames'][0]['camera']
        self.assertEqual(defaults,dict(pixel_width=800,pixel_height=450,frame_width=16,frame_height=9,background_color=lite.BLACK))

    def test_camera_snapshots_preserve_background_changes_and_ignore_later_config(self):
        result = render("self.wait(1)\nself.camera.background_color=WHITE\nconfig.background_color=RED\nself.wait(1)")
        self.assertEqual(result['frames'][0]['camera']['background_color'],lite.BLACK)
        self.assertEqual(result['frames'][15]['camera']['background_color'],lite.WHITE)
        scene = lite.Scene(camera_config={'pixel_width':400,'pixel_height':600,'frame_height':12})
        self.assertEqual(scene.camera.frame_width,8)
        scene.camera.frame_width=4
        self.assertEqual(scene.camera.frame_height,6)

    def test_configuration_validation_and_square_gallery(self):
        settings = lite.PreviewConfig()
        for name,value in [('pixel_width',0),('pixel_height',4097),('pixel_width',3.5),('pixel_height',True),('frame_width',float('nan')),('frame_height',-1),('background_color','white')]:
            before=settings.to_dict()
            with self.assertRaises(ValueError):
                setattr(settings,name,value)
            self.assertEqual(settings.to_dict(),before)
        with self.assertRaises(NotImplementedError):
            settings.frame_rate=30
        result=json.loads(lite.render_scene((ROOT/'examples/camera_scene.py').read_text()))
        self.assertEqual(result['duration'],5)
        self.assertEqual(result['frames'][0]['camera']['pixel_width'],600)
        self.assertEqual(result['frames'][0]['camera']['frame_height'],8)
        self.assertEqual(result['frames'][-1]['camera']['background_color'],'#E8EEF7')

    def test_group_construction_mutation_and_cycle_rejection_are_atomic(self):
        a,b,c = lite.Circle(),lite.Square(),lite.Triangle()
        group = lite.VGroup(a,b,a)
        self.assertEqual(group.children,[a,b])
        group.add(c,a,a)
        self.assertEqual(group.children,[b,c,a])
        group.add_to_back(a,b,a)
        self.assertEqual(group.children,[a,b,c])
        group.remove(b,b)
        self.assertEqual(group.children,[a,c])
        parent = lite.Group(group)
        for operation in (lambda: group.add(b,3),lambda: group.add(b,group),
                          lambda: group.add_to_back(b,parent),lambda: group.remove(a,3)):
            with self.assertRaises((TypeError,ValueError)):
                operation()
            self.assertEqual(group.children,[a,c])
        with self.assertRaises(TypeError):
            lite.Group(a,'invalid')
        with self.assertRaises(ValueError):
            group.submobjects = [b,parent]
        self.assertEqual(group.children,[a,c])
        group.submobjects = [b,b,a]
        self.assertIs(group.submobjects,group.children)
        self.assertEqual(group.children,[b,a])

    def test_group_index_slices_share_objects_and_have_neutral_transforms(self):
        children = [lite.Circle(),lite.Square(),lite.Triangle()]
        group = lite.VGroup(*children).shift(lite.RIGHT).rotate(.3).scale(2)
        self.assertEqual(len(group),3)
        self.assertIs(group[-1],children[-1])
        self.assertEqual(list(group),children)
        self.assertEqual(group.split(),children)
        section = group[::-2]
        self.assertIsInstance(section,lite.VGroup)
        self.assertEqual(section.children,[children[2],children[0]])
        self.assertEqual(section.position,[0,0,0])
        self.assertEqual(section.geometry_scale,1)
        self.assertEqual(section.angle,0)
        section[0].set_color(lite.RED)
        self.assertEqual(group[2].color,lite.RED)
        self.assertEqual(len(group[5:]),0)
        self.assertIsInstance(lite.Group(*children)[:2],lite.Group)
        with self.assertRaises(IndexError):
            group[3]

    def test_family_queries_deduplicate_shared_members_and_copies_are_independent(self):
        a,b = lite.Circle(),lite.Square()
        inner = lite.VGroup(a,b)
        outer = lite.Group(inner,a)
        self.assertEqual(outer.get_family(),[outer,inner,a,b])
        copied = outer.copy()
        self.assertIs(copied[0][0],copied[1])
        self.assertIsNot(copied[1],a)
        copied[1].set_color(lite.GREEN)
        self.assertNotEqual(a.color,lite.GREEN)
        self.assertEqual(a.get_family(),[a])

    def test_group_mutations_preserve_previous_frames_and_gallery_cleanup(self):
        result = json.loads(lite.render_scene((ROOT/'examples/group_family_scene.py').read_text()))
        self.assertEqual(result['duration'],7)
        self.assertEqual(len(result['frames'][0]['mobjects'][1]['children']),3)
        self.assertEqual(len(result['frames'][30]['mobjects'][1]['children']),2)
        self.assertEqual(len(result['frames'][45]['mobjects'][1]['children']),3)
        self.assertEqual(len(result['frames'][-1]['mobjects']),1)

    def test_group_transform_recursively_morphs_children_and_retains_pivots(self):
        source = lite.VGroup(lite.Circle().shift(lite.LEFT),
                            lite.VGroup(lite.Square().shift(lite.RIGHT))).scale(1.4).rotate(.3)
        target = lite.VGroup(lite.Triangle().shift(lite.DOWN),
                            lite.VGroup(lite.Circle().shift(lite.UP))).shift(lite.RIGHT)
        before, after = source.to_dict(), target.to_dict()
        effect = lite.Transform(source, target)
        effect.prepare(lite.Scene())
        midpoint = effect.sample(.5)[0]
        self.assertEqual(midpoint['children'][0]['type'], 'bezierpath')
        self.assertEqual(midpoint['children'][1]['children'][0]['type'], 'bezierpath')
        self.assertEqual(midpoint['children'][0]['opacity'], 1)
        self.assertEqual(midpoint['geometry_center'], lite.interpolate(before['geometry_center'], after['geometry_center'], .5))
        self.assertEqual(source.to_dict(), before)
        self.assertEqual(target.to_dict(), after)
        effect.finish(lite.Scene())
        self.assertEqual(source.to_dict(), after)

    def test_unequal_group_transform_distributes_transparent_duplicates(self):
        source = lite.VGroup(lite.Circle(), lite.Square())
        target = lite.VGroup(lite.Square(), lite.Triangle(), lite.Circle(), lite.Line(), lite.Rectangle())
        effect = lite.Transform(source, target)
        effect.prepare(lite.Scene())
        start = effect.sample(0)[0]['children']
        self.assertEqual([c['opacity'] for c in start], [1,0,0,1,0])
        midpoint = effect.sample(.5)[0]['children']
        self.assertEqual([c['opacity'] for c in midpoint], [1,.5,.5,1,.5])
        self.assertEqual(len(source.children), 2)
        self.assertEqual(len(target.children), 5)
        reverse = lite.Transform(target, source)
        reverse.prepare(lite.Scene())
        self.assertEqual([c['opacity'] for c in reverse.sample(1)[0]['children']], [1,0,0,1,0])
        reverse.finish(lite.Scene())
        self.assertEqual(len(target.children), 2)

    def test_empty_group_transforms_and_leaf_to_nested_family(self):
        for source, target in ((lite.VGroup(), lite.VGroup(lite.Circle(),lite.Square())),
                               (lite.VGroup(lite.Circle()), lite.VGroup())):
            effect = lite.Transform(source,target)
            effect.prepare(lite.Scene())
            midpoint = effect.sample(.5)[0]['children']
            self.assertTrue(midpoint)
            self.assertTrue(all(c['opacity'] == .5 and c['geometry_scale'] == .5 for c in midpoint))
        source = lite.Circle().shift(lite.LEFT).scale(2)
        target = lite.VGroup(lite.VGroup(lite.Square(),lite.Triangle())).shift(lite.RIGHT).rotate(.5)
        effect = lite.Transform(source,target)
        effect.prepare(lite.Scene())
        frame = effect.sample(0)[0]
        self.assertEqual(frame['position'], [0,0,0])
        nested = frame['children'][0]['children']
        self.assertEqual(nested[0]['position'], [-1,0,0])
        self.assertEqual(nested[0]['geometry_scale'], 2)
        self.assertEqual(nested[1]['opacity'], 0)

    def test_group_copy_restore_sequence_and_unsupported_leaf_fades(self):
        source = lite.VGroup(lite.Circle(),lite.Text('old')).save_state()
        target = lite.VGroup(lite.Square(),lite.MathTex('x'),lite.Triangle())
        effect = lite.TransformFromCopy(source,target)
        original, destination = source.to_dict(), target.to_dict()
        effect.prepare(lite.Scene())
        self.assertEqual(len(effect.sample(.5)[0]['children']), 5)
        effect.finish(lite.Scene())
        self.assertEqual(source.to_dict(),original)
        self.assertEqual(target.to_dict(),destination)
        scene = lite.Scene().add(source)
        scene.play(lite.Succession(lite.Transform(source,target),lite.Restore(source)))
        self.assertEqual(source.to_dict(),original)
        self.assertEqual(scene.frames[15]['mobjects'][0]['children'][0]['type'], 'bezierpath')

    def test_group_morph_gallery_restores_original_family_and_clears(self):
        result = json.loads(lite.render_scene((ROOT/'examples/group_morph_scene.py').read_text()))
        self.assertEqual(result['duration'], 11)
        midpoint = result['frames'][45]['mobjects'][1]
        self.assertEqual(len(midpoint['children']),3)
        self.assertEqual([c['opacity'] for c in midpoint['children']], [1,.5,1])
        self.assertEqual(midpoint['children'][0]['type'],'bezierpath')
        restored = result['frames'][120]['mobjects'][1]
        self.assertEqual(len(restored['children']),2)
        self.assertEqual(restored['children'][0]['type'],'circle')
        self.assertEqual(len(result['frames'][-1]['mobjects']),1)

    def test_circle_conversion_is_closed_tangent_matched_and_accurate(self):
        circle = lite.Circle(radius=2)
        curves = lite._path_curves(circle.to_dict())
        self.assertEqual(len(curves), 8)
        self.assertEqual(curves[0][0], [2,0,0])
        self.assertEqual(curves[-1][-1], curves[0][0])
        for index, curve in enumerate(curves):
            self.assertEqual(curve[-1], curves[(index+1)%8][0])
            for t in (i/100 for i in range(101)):
                point = lite.VMobject._bezier_point(curve,t)
                self.assertLessEqual(abs((point[0]**2 + point[1]**2)**0.5 - 2), 1e-5)
            anchor, handle = lite.Vector(curve[0]), lite.Vector(curve[1])
            direction = handle-anchor
            self.assertAlmostEqual(anchor[0]*direction[0] + anchor[1]*direction[1], 0)
        self.assertEqual(lite._path_curves(lite.Circle(radius=0).to_dict())[0], [[0,0,0]]*4)

    def test_arc_conversion_preserves_signed_sweep_exact_endpoints_and_pivot(self):
        for sweep in (lite.PI, -lite.PI, 0, lite.TAU):
            arc = lite.Arc(radius=2,start_angle=lite.PI/3,angle=sweep,arc_center=lite.RIGHT).scale(0.7).rotate(0.2)
            snapshot = arc.to_dict()
            curves = lite._path_curves(snapshot)
            expected = lambda a: (2*lite.math.cos(a), 2*lite.math.sin(a), 0)
            for actual, point in ((curves[0][0],expected(lite.PI/3)), (curves[-1][-1],expected(lite.PI/3+sweep))):
                for a,b in zip(actual,point):
                    self.assertAlmostEqual(a,b)
            if sweep:
                anchor, handle = lite.Vector(curves[0][0]), lite.Vector(curves[0][1])
                direction = handle-anchor
                self.assertEqual((anchor[0]*direction[1]-anchor[1]*direction[0]) > 0, sweep > 0)
            aligned = lite._align_path_snapshots(snapshot, lite.Square().to_dict())[0]
            self.assertEqual(aligned['geometry_center'],snapshot['geometry_center'])
            self.assertEqual(aligned['position'],snapshot['position'])

    def test_straight_primitive_conversion_preserves_outline_vertices(self):
        cases = ((lite.Line((1,2),(4,5)), 1, (1,2,0), (4,5,0)),
                 (lite.Square(side_length=4), 4, (2,2,0), (2,2,0)),
                 (lite.Rectangle(width=6,height=2), 4, (3,1,0), (3,1,0)),
                 (lite.Triangle(), 3, (0,3**0.5/3,0), (0,3**0.5/3,0)))
        for shape, count, start, end in cases:
            with self.subTest(shape=shape._type):
                curves = lite._path_curves(shape.to_dict())
                self.assertEqual(len(curves),count)
                for a,b in zip(curves[0][0],start):
                    self.assertAlmostEqual(a,b)
                for a,b in zip(curves[-1][-1],end):
                    self.assertAlmostEqual(a,b)
                for curve in curves:
                    middle = lite.VMobject._bezier_point(curve,0.5)
                    for a,b,c in zip(middle,curve[0],curve[-1]):
                        self.assertAlmostEqual(a,(b+c)/2)

    def test_primitive_to_path_morphs_retain_one_drawable_and_native_matching_types(self):
        for source,target in (('Circle()', 'Square()'), ('Square()', 'Triangle()'),
                              ('Rectangle()', 'Polygon(ORIGIN,RIGHT,UP)'),
                              ('Line(LEFT,RIGHT)', 'CubicBezier(LEFT,UL,UR,RIGHT)'),
                              ('Arc(angle=-PI)', 'VMobject().set_points_as_corners([LEFT,UP,RIGHT])')):
            result = render(f'p = {source}\nq = {target}\nself.play(Transform(p,q), run_time=2, rate_func=linear)')
            frame = result['frames'][15]['mobjects']
            self.assertEqual(len(frame),1)
            self.assertEqual(frame[0]['type'],'bezierpath')
            self.assertEqual(frame[0]['opacity'],1)
        result = render('p = Circle(radius=1)\nself.play(Transform(p,Circle(radius=3)),run_time=2,rate_func=linear)')
        self.assertEqual(result['frames'][15]['mobjects'][0]['type'],'circle')
        self.assertEqual(result['frames'][15]['mobjects'][0]['radius'],2)
        result = render('p = Arc(angle=PI)\nself.play(Transform(p,Arc(angle=-PI)),run_time=2,rate_func=linear)')
        self.assertEqual(result['frames'][15]['mobjects'][0]['arc_angle'],0)
        result = render('p = Arrow()\nself.play(Transform(p,Circle()),run_time=2,rate_func=linear)')
        self.assertEqual([m['opacity'] for m in result['frames'][15]['mobjects']],[0.5,0.5])

    def test_primitive_morph_gallery_restores_circle_and_finishes_as_cubic(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/shape_morph_scene.py').read_text()))
        self.assertEqual(result['duration'],11)
        self.assertEqual(result['frames'][45]['mobjects'][0]['type'],'bezierpath')
        self.assertEqual(len(result['frames'][45]['mobjects'][0]['curves']),8)
        self.assertEqual(len(result['frames'][120]['mobjects'][0]['curves']),8)
        self.assertEqual(result['frames'][120]['mobjects'][0]['geometry_scale'],1.2)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['type'],'bezierpath')
        self.assertEqual(len(result['frames'][-1]['mobjects'][0]['curves']),1)

    def test_cubic_subdivision_preserves_curve_geometry_and_every_existing_join(self):
        curve = [[0,0,0], [8,4,0], [-2,3,0], [3,0,0]]
        pieces = lite._subdivide_curves([curve], 3)
        for index, piece in enumerate(pieces):
            for t in (0,0.25,0.5,1):
                for a, b in zip(lite.VMobject._bezier_point(piece,t), lite.VMobject._bezier_point(curve,(index+t)/3)):
                    self.assertAlmostEqual(a,b)
        second = [[3,0,0], [4,1,0], [5,1,0], [6,0,0]]
        pieces = lite._subdivide_curves([curve, second], 5)
        self.assertEqual(pieces[2][-1], second[0])
        self.assertEqual(pieces[3][0], second[0])
        self.assertEqual(pieces[-1][-1], second[-1])

    def test_alignment_keeps_transformed_pivots_and_live_source_target_unchanged(self):
        source = lite.CubicBezier((0,0), (8,4), (-2,3), (3,0)).scale(0.8).rotate(lite.PI/4).shift(lite.LEFT)
        target = source.copy().add_line_to((4,1)).add_line_to((5,2)).set_color(lite.GREEN)
        before = source.to_dict(), target.to_dict()
        animation = lite.Transform(source,target)
        animation.prepare(lite.Scene())
        for alpha, original in ((0,before[0]), (1,before[1])):
            frame = animation.sample(alpha)[0]
            self.assertEqual(len(frame['curves']), 3)
            for key in ('geometry_center', 'geometry_scale', 'angle', 'position'):
                self.assertEqual(frame[key], original[key])
            self.assertEqual(frame['curves'][0][0], original['curves'][0][0])
            self.assertEqual(frame['curves'][-1][-1], original['curves'][-1][-1])
        self.assertEqual((source.to_dict(),target.to_dict()),before)

    def test_corner_to_cubic_morph_and_single_point_growth_keep_endpoints(self):
        result = render('p = VMobject().set_points_as_corners([(-2,0),(2,0)])\nq = CubicBezier((-2,0),(-1,2),(1,2),(2,0))\nself.play(Transform(p,q), run_time=2, rate_func=linear)')
        frame = result['frames'][15]['mobjects'][0]
        self.assertEqual(frame['type'], 'bezierpath')
        self.assertEqual(frame['curves'][0][0], [-2,0,0])
        self.assertEqual(frame['curves'][0][-1], [2,0,0])
        self.assertEqual(frame['curves'][0][1][1], 1)
        result = render('p = VMobject().set_points_as_corners([ORIGIN])\nq = VMobject().set_points_as_corners([ORIGIN, RIGHT*2])\nself.play(Transform(p,q), run_time=2, rate_func=linear)')
        self.assertEqual(result['frames'][15]['mobjects'][0]['curves'][0][-1], [1,0,0])
        result = render('p = VMobject()\nq = CubicBezier(ORIGIN,RIGHT,UP,UR)\nself.play(Transform(p,q), run_time=2, rate_func=linear)')
        self.assertEqual([m['opacity'] for m in result['frames'][15]['mobjects']], [0.5,0.5])

    def test_alignment_handles_restore_copy_replacement_and_sequential_stage_state(self):
        result = render('p = VMobject().set_points_as_corners([ORIGIN, RIGHT*2]).save_state()\nq = VMobject().set_points_as_corners([ORIGIN, RIGHT*2, UR*2])\nself.add(p)\nself.play(TransformFromCopy(p,q), run_time=2, rate_func=linear)\nassert p.vertices == [[0,0,0],[2,0,0]]\nself.play(Succession(Transform(p,q), Restore(p)), rate_func=linear)')
        self.assertEqual(len(result['frames'][15]['mobjects']), 2)
        self.assertEqual(result['frames'][15]['mobjects'][1]['type'], 'bezierpath')
        self.assertEqual(result['frames'][-1]['mobjects'][0]['vertices'], [[0,0,0],[2,0,0]])
        result = render('p = VMobject().set_points_as_corners([ORIGIN,RIGHT])\nq = CubicBezier(ORIGIN,UP,UR,RIGHT)\nself.play(ReplacementTransform(p,q), run_time=2, rate_func=linear)\nassert self.mobjects == [q]')
        self.assertEqual(result['frames'][15]['mobjects'][0]['type'], 'bezierpath')

    def test_alignment_gallery_finishes_as_closed_polygon(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/morph_scene.py').read_text()))
        self.assertEqual(result['duration'], 10)
        self.assertEqual(result['frames'][45]['mobjects'][0]['type'], 'bezierpath')
        self.assertEqual(len(result['frames'][45]['mobjects'][0]['curves']), 3)
        self.assertEqual(len(result['frames'][75]['mobjects'][0]['curves']), 3)
        self.assertEqual(result['frames'][-1]['mobjects'][0]['type'], 'polygon')
        self.assertEqual(len(result['frames'][-1]['mobjects'][0]['vertices']), 4)

    def test_cubic_bezier_samples_endpoints_midpoint_and_transformed_geometry(self):
        curve = lite.CubicBezier((-3,0), (-1,3), (1,3), (3,0))
        self.assertIsInstance(curve, lite.VMobject)
        self.assertEqual(curve.point_from_proportion(0.5), (0,2.25,0))
        self.assertEqual(curve._local_bounds(), (-3,0,3,3))
        curve.scale(2).rotate(lite.PI/2).shift(lite.RIGHT)
        for actual, expected in ((curve.get_start(), (4,-4.5,0)), (curve.get_end(), (4,7.5,0)), (curve.point_from_proportion(0.5), (-0.5,1.5,0))):
            for a, b in zip(actual, expected):
                self.assertAlmostEqual(a, b)
        for alpha in (-0.1, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                curve.point_from_proportion(alpha)

    def test_mixed_cubic_and_corner_segments_follow_length_weighted_curve_parameters(self):
        path = lite.VMobject().set_points_as_corners([(0,0), (1,0)])
        self.assertIs(path.add_cubic_bezier_curve_to((2,0), (3,0), (4,0)), path)
        path.add_points_as_corners([(5,0), (6,0)])
        self.assertEqual(len(path.curves), 4)
        self.assertEqual(path.get_start(), (0,0,0))
        self.assertEqual(path.get_end(), (6,0,0))
        for alpha in (0.1, 0.25, 0.5, 0.75, 1):
            self.assertAlmostEqual(path.point_from_proportion(alpha)[0], 6*alpha)
        before = path.copy()
        path.reverse_direction()
        for alpha in (0,0.25,0.5,1):
            for a, b in zip(path.point_from_proportion(alpha), before.point_from_proportion(1-alpha)):
                self.assertAlmostEqual(a,b)

    def test_cubic_validation_is_atomic_and_degenerate_curves_are_stable(self):
        path = lite.VMobject()
        with self.assertRaisesRegex(ValueError, 'Start the path'):
            path.add_cubic_bezier_curve_to(lite.ORIGIN, lite.RIGHT, lite.UP)
        path.set_points_as_corners([lite.ORIGIN])
        for bad, error in (((float('inf'),0), ValueError), ((0,0,1), NotImplementedError)):
            with self.assertRaises(error):
                path.add_cubic_bezier_curve_to(lite.ORIGIN, bad, lite.RIGHT)
            self.assertEqual(path._type, 'polyline')
            self.assertEqual(path.vertices, [[0,0,0]])
        path.add_cubic_bezier_curve_to(lite.ORIGIN, lite.ORIGIN, lite.ORIGIN)
        self.assertEqual(path.point_from_proportion(0.5), lite.ORIGIN)
        saved = path.to_dict()
        with self.assertRaises(ValueError):
            path.add_points_as_corners([lite.RIGHT, (float('nan'),0)])
        self.assertEqual(path.to_dict(), saved)
        path.set_points_as_corners([])
        self.assertEqual(path._type, 'polyline')
        self.assertNotIn('curves', path.to_dict())

    def test_cubic_control_points_interpolate_and_checkpoint_restores_curve(self):
        result = render('a = CubicBezier((-3,0), (-1,0), (1,0), (3,0)).save_state()\nb = CubicBezier((-3,0), (-1,4), (1,4), (3,0))\nself.play(Transform(a,b), run_time=2, rate_func=linear)\nself.play(Restore(a))')
        middle = result['frames'][15]['mobjects'][0]
        self.assertEqual(middle['curves'][0][1], [-1,2,0])
        self.assertEqual(middle['curves'][0][2], [1,2,0])
        self.assertEqual(result['frames'][-1]['mobjects'][0]['curves'][0][1], [-1,0,0])
        result = render('a = CubicBezier(ORIGIN, RIGHT, RIGHT, RIGHT)\nself.play(a.animate.add_cubic_bezier_curve_to(UR, UR, UP), run_time=1, rate_func=linear)')
        self.assertEqual(len(result['frames'][7]['mobjects']), 1)
        self.assertEqual(len(result['frames'][7]['mobjects'][0]['curves']), 2)
        self.assertEqual(len(result['frames'][-1]['mobjects'][0]['curves']), 2)

    def test_cubic_gallery_traces_follows_deforms_restores_and_introduces_mixed_path(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/bezier_scene.py').read_text()))
        self.assertEqual(result['duration'], 11)
        first = result['frames'][0]['mobjects'][0]
        self.assertEqual(first['type'], 'bezierpath')
        self.assertEqual(first['draw_progress'], 0)
        curve = lite.CubicBezier((-3,-1), (-2,3), (2,-3), (3,1)).scale(0.8).rotate(lite.PI/12)
        for a, b in zip(result['frames'][75]['mobjects'][1]['position'], curve.get_end()):
            self.assertAlmostEqual(a,b)
        self.assertEqual(result['frames'][105]['mobjects'][0]['color'].lower(), lite.GREEN.lower())
        self.assertEqual([m['type'] for m in result['frames'][-1]['mobjects']], ['text', 'bezierpath'])
        self.assertEqual(len(result['frames'][-1]['mobjects'][1]['curves']), 3)

    def test_foreground_roots_stay_after_later_additions_and_animations(self):
        a, b, c = lite.Circle(), lite.Square(), lite.Dot()
        scene = lite.Scene().add(a)
        self.assertIs(scene.add_foreground_mobject(b), scene)
        scene.add(c, b).play(lite.Rotate(a, lite.PI))
        self.assertEqual(scene.mobjects, [a, c, b])
        self.assertEqual(scene.foreground_mobjects, [b])
        self.assertEqual([m['type'] for m in scene.frames[0]['mobjects']], ['circle', 'circle', 'square'])
        self.assertIs(scene.bring_to_front(b), scene)
        self.assertEqual(scene.foreground_mobjects, [b])

    def test_foreground_readdition_is_stable_and_keeps_identity(self):
        a, b, c = lite.Circle(), lite.Square(), lite.Dot()
        scene = lite.Scene().add(c)
        before = [m.to_dict() for m in (a, b)]
        self.assertIs(scene.add_foreground_mobjects(a, b, a), scene)
        self.assertEqual(scene.mobjects, [c, a, b])
        scene.add_foreground_mobject(a)
        self.assertEqual(scene.mobjects, [c, b, a])
        self.assertEqual(scene.foreground_mobjects, [b, a])
        self.assertEqual([m.to_dict() for m in (a, b)], before)

    def test_releasing_foreground_keeps_visible_object_and_allows_later_cover(self):
        a, b = lite.Circle(), lite.Square()
        scene = lite.Scene().add_foreground_mobject(a)
        self.assertIs(scene.remove_foreground_mobject(a), scene)
        self.assertEqual(scene.mobjects, [a])
        self.assertEqual(scene.foreground_mobjects, [])
        scene.add(b)
        self.assertEqual(scene.mobjects, [a, b])
        self.assertIs(scene.remove_foreground_mobjects(a, b), scene)
        self.assertEqual(scene.mobjects, [a, b])

    def test_removal_back_order_and_clear_release_foreground_membership(self):
        a, b = lite.Circle(), lite.Square()
        scene = lite.Scene().add(b).add_foreground_mobject(a)
        scene.bring_to_back(a)
        self.assertEqual(scene.mobjects, [a, b])
        self.assertEqual(scene.foreground_mobjects, [])
        scene.add_foreground_mobject(a).remove(a).add(a)
        self.assertEqual(scene.foreground_mobjects, [])
        scene.add_foreground_mobject(a).clear().add(b)
        self.assertEqual(scene.mobjects, [b])
        self.assertEqual(scene.foreground_mobjects, [])

    def test_foreground_fade_and_replacement_remove_membership(self):
        for animation in ('FadeOut(a)', 'ReplacementTransform(a, b)', 'Succession(Rotate(a, PI), FadeOut(a))'):
            result = render('a = Circle()\nb = Square()\nself.add_foreground_mobject(a)\nself.play(' + animation + ')\nassert self.foreground_mobjects == []\nself.add(b)')
            self.assertEqual([m['type'] for m in result['frames'][-1]['mobjects']], ['square'])

    def test_foreground_family_validation_is_atomic(self):
        child = lite.Circle()
        group, other = lite.VGroup(child), lite.Dot()
        scene = lite.Scene().add(group).add_foreground_mobject(other)
        for method in (scene.add_foreground_mobjects, scene.remove_foreground_mobjects):
            for args, error in (((other, child), NotImplementedError), ((other, 1), TypeError)):
                with self.assertRaises(error):
                    method(*args)
                self.assertEqual(scene.mobjects, [group, other])
                self.assertEqual(scene.foreground_mobjects, [other])

    def test_foreground_gallery_preserves_group_then_releases_cleans_and_clears(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/foreground_scene.py').read_text()))
        self.assertEqual(result['duration'], 8)
        self.assertEqual([m['type'] for m in result['frames'][30]['mobjects']], ['text', 'square', 'vgroup'])
        self.assertEqual([m['type'] for m in result['frames'][45]['mobjects']], ['text', 'square', 'vgroup', 'square'])
        self.assertEqual([m['type'] for m in result['frames'][60]['mobjects']], ['text', 'square', 'square', 'vgroup'])
        self.assertEqual([m['type'] for m in result['frames'][90]['mobjects']], [])
        self.assertEqual([m['text'] for m in result['frames'][-1]['mobjects']], ['Foreground overlay'])

    def test_closed_corner_paths_follow_return_to_start_and_restore_reversed_geometry(self):
        path = lite.VMobject().set_points_as_corners([lite.ORIGIN, lite.RIGHT, lite.UR, lite.ORIGIN]).save_state()
        self.assertEqual(path.get_start(), path.get_end())
        self.assertEqual(path.point_from_proportion(1), path.get_start())
        saved = path.to_dict()
        path.reverse_direction().set_color(lite.RED).restore()
        self.assertEqual(path.to_dict(), saved)
        result = render('p = VMobject().set_points_as_corners([ORIGIN, RIGHT, UR, ORIGIN])\nd = Dot()\nself.add(p)\nself.play(MoveAlongPath(d,p), run_time=1, rate_func=linear)')
        self.assertEqual(result['frames'][-1]['mobjects'][1]['position'], [0,0,0])

    def test_corner_gallery_traces_moves_and_cleans_up(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/corner_path_scene.py').read_text()))
        self.assertEqual(result['duration'], 9)
        self.assertEqual(result['frames'][0]['mobjects'][0]['type'], 'polyline')
        path = lite.VMobject().set_points_as_corners([(-3,-1,0),(-1,1,0),(1,-1,0),(3,1,0)]).scale(0.8).rotate(lite.PI/12).shift(lite.DOWN*0.3)
        for actual, expected in zip(result['frames'][75]['mobjects'][1]['position'], path.get_end()):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(result['frames'][105]['mobjects'][0]['color'], lite.GREEN)
        self.assertEqual([m['type'] for m in result['frames'][-1]['mobjects']], ['text'])

    def test_corner_path_set_append_reverse_and_geometry_queries(self):
        path = lite.VMobject(color=lite.BLUE).set_points_as_corners([(-2, 0, 0), (0, 0, 0)])
        self.assertIs(path.add_line_to((0, 2, 0)).add_points_as_corners([(2, 2, 0)]), path)
        self.assertEqual(path.get_start(), (-2, 0, 0))
        self.assertEqual(path.get_end(), (2, 2, 0))
        self.assertEqual(path.point_from_proportion(0.5), (0, 1, 0))
        original = path.copy()
        self.assertIs(path.reverse_direction(), path)
        self.assertEqual(path.get_start(), original.get_end())
        self.assertEqual(path.get_end(), original.get_start())
        self.assertEqual(path._local_bounds(), (-2, 0, 2, 2))
        self.assertEqual(path.stroke_width, 4)
        path.set_points_as_corners([(0, 0, 0), (2, 0, 0)]).scale(2).rotate(lite.PI/2).shift(lite.RIGHT)
        for actual, expected in ((path.get_start(), (2, -2, 0)), (path.get_end(), (2, 2, 0)), (path.point_from_proportion(0.5), (2, 0, 0))):
            for a, b in zip(actual, expected):
                self.assertAlmostEqual(a, b)

    def test_corner_paths_validate_atomically_and_handle_empty_or_degenerate_geometry(self):
        path = lite.VMobject()
        self.assertEqual(path.to_dict()['vertices'], [])
        for query in (path.get_start, path.get_end, lambda: path.point_from_proportion(0.5)):
            with self.assertRaises(ValueError):
                query()
        path.set_points_as_corners([(1, 2, 0)])
        self.assertEqual(path.point_from_proportion(0.8), (1, 2, 0))
        path.add_line_to((1, 2, 0))
        self.assertEqual(path.point_from_proportion(0.8), (1, 2, 0))
        before = path.to_dict()
        for method in (path.set_points_as_corners, path.add_points_as_corners):
            with self.assertRaises(ValueError):
                method([(0, 0, 0), (float('inf'), 0, 0)])
            with self.assertRaises(NotImplementedError):
                method([(0, 0, 1)])
            self.assertEqual(path.to_dict(), before)
        path.set_points_as_corners([])
        self.assertEqual(path.to_dict()['vertices'], [])

    def test_corner_paths_create_move_morph_and_remove(self):
        result = render('p = VMobject().set_points_as_corners([(0,0,0), (2,0,0), (2,2,0)])\nd = Dot()\nself.play(Create(p), run_time=2, rate_func=linear)\nself.play(MoveAlongPath(d, p), run_time=2, rate_func=linear)\nself.play(p.animate.set_points_as_corners([(0,0,0), (4,0,0), (4,4,0)]), run_time=2, rate_func=linear)\nself.play(Uncreate(p), FadeOut(d))')
        self.assertEqual(result['frames'][15]['mobjects'][0]['draw_progress'], 0.5)
        self.assertEqual(result['frames'][45]['mobjects'][1]['position'], [2, 0, 0])
        self.assertEqual(result['frames'][60]['mobjects'][1]['position'], [2, 2, 0])
        self.assertEqual(result['frames'][75]['mobjects'][0]['vertices'], [[0,0,0], [3,0,0], [3,3,0]])
        self.assertEqual(result['frames'][-1]['mobjects'], [])

    def test_unequal_corner_counts_morph_through_one_aligned_path(self):
        for shape in ('VMobject().set_points_as_corners', 'Polygon'):
            initial = '[(0,0,0), (2,0,0)]' if shape.startswith('VM') else '(0,0,0), (2,0,0), (0,2,0)'
            target = '[(0,0,0), (2,0,0), (2,2,0)]' if shape.startswith('VM') else '(0,0,0), (2,0,0), (2,2,0), (0,2,0)'
            result = render(f'p = {shape}({initial})\nq = {shape}({target})\nself.play(Transform(p,q), run_time=2, rate_func=linear)')
            middle = result['frames'][15]['mobjects']
            self.assertEqual(len(middle), 1)
            self.assertEqual(middle[0]['opacity'], 1)
            self.assertEqual(middle[0]['type'], 'bezierpath')
            self.assertEqual(len(middle[0]['curves']), 2 if shape.startswith('VM') else 4)
            final = result['frames'][-1]['mobjects'][0]
            self.assertEqual(final['type'], 'polyline' if shape.startswith('VM') else 'polygon')
            if shape.startswith('VM'):
                self.assertEqual(middle[0]['curves'][0][-1], [1.5,0,0])
                self.assertEqual(middle[0]['curves'][-1][-1], [2,1,0])
            else:
                self.assertEqual(middle[0]['curves'][0][0], middle[0]['curves'][-1][-1])

    def test_lifecycle_gallery_initializes_construct_objects_and_reports_elapsed_time(self):
        result = json.loads(lite.render_scene((ROOT / 'examples/lifecycle_scene.py').read_text()))
        self.assertEqual(result['scene'], 'LifecycleScene')
        self.assertEqual(result['duration'], 7)
        self.assertEqual(result['frames'][0]['mobjects'][1]['text'], 'Initialized in setup')
        self.assertAlmostEqual(result['frames'][45]['mobjects'][0]['angle'], lite.PI/2)
        self.assertEqual(len(result['frames'][74]['mobjects']), 2)
        self.assertEqual(result['frames'][75]['mobjects'][2]['text'], 'Finished at 5.0s')
        self.assertEqual(result['frames'][75]['mobjects'][2]['opacity'], 0)
        self.assertEqual(result['frames'][-1]['mobjects'][2]['opacity'], 1)

    def test_scene_lifecycle_runs_in_order_with_shared_initialized_objects(self):
        events = []
        class Base(lite.Scene):
            def setup(self):
                events.append(('setup', self.time))
                self.shape = lite.Circle()
                self.add(self.shape)
                self.wait(0.5)
            def tear_down(self):
                events.append(('tear_down', self.time))
                self.shape.set_color(lite.GREEN)
        class Demo(Base):
            def construct(self):
                events.append(('construct', self.time))
                self.play(lite.Rotate(self.shape, lite.PI), run_time=2)
        scene = Demo()
        result = scene.render()
        self.assertEqual(events, [('setup', 0), ('construct', 8/15), ('tear_down', 38/15)])
        self.assertEqual(scene.time, result['duration'])
        self.assertEqual(result['frames'][-1]['mobjects'][0]['color'], lite.GREEN)
        self.assertEqual(result['frames'][0]['mobjects'][0]['color'], lite.WHITE)

    def test_scene_clock_uses_sampled_max_duration_and_clear_does_not_reset_it(self):
        scene = lite.Scene()
        scene.wait(0)
        self.assertEqual(scene.time, 0)
        scene.play(lite.AnimationGroup(lite.Create(lite.Circle(), run_time=0.3), lite.Create(lite.Dot(), run_time=1.1)))
        self.assertEqual(scene.time, 17/15)
        scene.clear().wait(0.01)
        self.assertEqual(scene.time, 18/15)
        for call in (lambda: scene.wait(-1), lambda: scene.play(lite.Create(lite.Circle()), run_time=0)):
            with self.assertRaises(ValueError):
                call()
            self.assertEqual(scene.time, 18/15)
        with self.assertRaises(AttributeError):
            scene.time = 5

    def test_hooks_can_generate_frames_and_final_capture_does_not_advance_time(self):
        class Demo(lite.Scene):
            def setup(self):
                self.add(lite.Circle())
                self.wait(1)
            def construct(self):
                self.wait(2)
            def tear_down(self):
                self.clear()
                self.wait(1)
        scene = Demo()
        result = scene.render()
        self.assertEqual(scene.time, 4)
        self.assertEqual(result['duration'], 4)
        self.assertEqual(len(result['frames']), 61)
        self.assertEqual(result['frames'][-1]['mobjects'], [])
        empty = lite.Scene()
        self.assertEqual(empty.render()['duration'], 0)
        self.assertEqual(empty.time, 0)

    def test_lifecycle_errors_propagate_without_running_later_hooks(self):
        for failed in ('setup', 'construct', 'tear_down'):
            calls = []
            def hook(name):
                def execute(self):
                    calls.append(name)
                    if name == failed:
                        raise ValueError('Failure in ' + name)
                return execute
            demo = type('Demo', (lite.Scene,), {name: hook(name) for name in ('setup', 'construct', 'tear_down')})()
            with self.assertRaisesRegex(ValueError, 'Failure in ' + failed):
                demo.render()
            self.assertEqual(calls, ['setup', 'construct', 'tear_down'][:['setup', 'construct', 'tear_down'].index(failed)+1])
            self.assertEqual(demo.frames, [])

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

    def test_transform_from_copy_snapshots_at_start_and_morphs_primitives(self):
        source, target = lite.Circle(), lite.Square()
        effect = lite.TransformFromCopy(source, target)
        source.shift(lite.LEFT)
        target.shift(lite.RIGHT)
        scene = lite.Scene()
        scene.play(effect, run_time=2, rate_func=lite.linear)
        middle = scene.frames[15]['mobjects']
        self.assertEqual([m['type'] for m in middle], ['bezierpath'])
        self.assertEqual(middle[0]['opacity'], 1)
        self.assertEqual(len(middle[0]['curves']), 8)
        self.assertEqual(middle[0]['position'], [0,0,0])
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
        self.assertEqual([s['type'] for s in scene.frames[30]['mobjects']], ['bezierpath'])
        self.assertEqual(scene.frames[30]['mobjects'][0]['opacity'], 1)
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
