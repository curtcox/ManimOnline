"""Trace a cubic curve, follow it, deform it, and draw a mixed path."""
from manim import *


class BezierScene(Scene):
    def construct(self):
        curve = CubicBezier((-3,-1,0), (-2,3,0), (2,-3,0), (3,1,0), color=BLUE)
        curve.scale(0.8).rotate(PI / 12).save_state()
        marker = Dot(curve.get_start(), color=YELLOW)
        title = Text("Cubic Bezier paths", font_size=30).shift(UP * 2.5)
        self.play(Create(curve), FadeIn(marker), FadeIn(title), run_time=2)
        self.play(MoveAlongPath(marker, curve), run_time=3, rate_func=linear)
        target = CubicBezier((-3,0,0), (-1,3,0), (1,3,0), (3,0,0), color=GREEN)
        self.play(Transform(curve, target), run_time=2)
        self.play(Restore(curve), FadeOut(marker))
        mixed = VMobject(color=PURPLE).set_points_as_corners([(-3,-1,0), (-1,-1,0)])
        mixed.add_cubic_bezier_curve_to((-1,2,0), (1,2,0), (1,-1,0)).add_line_to((3,-1,0))
        self.play(Uncreate(curve), Create(mixed), run_time=2)
        self.wait(1)
