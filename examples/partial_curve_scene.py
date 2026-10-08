"""Extract exact cubic portions and wrap a highlight across a closed outline."""
from manim import *


class PartialCurveScene(Scene):
    def construct(self):
        curve = CubicBezier((-3,-1), (-2,3), (2,-3), (3,1)).rotate(PI/8)
        curve.set_stroke(color=GRAY, width=3)
        highlight = curve.get_subcurve(.2,.8).set_stroke(color=YELLOW, width=7)
        ring = Circle(radius=1.2, color=GRAY).shift(UP*2)
        wrapped = ring.get_subcurve(.85,.15).set_stroke(color=BLUE, width=7)
        self.play(Create(curve), Create(ring), run_time=2)
        self.play(Create(highlight), Create(wrapped), run_time=2)
        self.play(highlight.animate.pointwise_become_partial(curve,.6,1), run_time=2)
        self.play(FadeOut(highlight), FadeOut(wrapped), run_time=1)
        self.wait(1)
