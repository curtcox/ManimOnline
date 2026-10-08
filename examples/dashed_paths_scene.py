"""Wrap ring dashes and compare equal-length versus parameter spacing."""
from manim import *


class DashedPathsScene(Scene):
    def construct(self):
        loop = Circle(radius=1.4,color=GREEN).shift(LEFT*2.2)
        curve = CubicBezier((.3,-1.6),(2.5,3),(1,-3.5),(4,1.6),color=BLUE)
        references = VGroup(loop.copy().set_stroke(opacity=.2),
                            curve.copy().shift(UP*.65).set_stroke(opacity=.2),
                            curve.copy().shift(DOWN*.65).set_stroke(opacity=.2))
        labels = VGroup(Text('Wrapped phase',font_size=24).move_to((-2.2,2.5,0)),
                        Text('Even lengths',font_size=24).move_to((2.2,2.8,0)),
                        Text('Curve parameter',font_size=24).move_to((2.2,-2.8,0)))
        phase = ValueTracker(0)
        ring = always_redraw(lambda:DashedVMobject(loop,num_dashes=12,
                              dashed_ratio=.55,dash_offset=phase.get_value()))
        even = DashedVMobject(curve.copy().set_color(YELLOW),num_dashes=8).shift(UP*.65)
        legacy = DashedVMobject(curve,num_dashes=8,equal_lengths=False).shift(DOWN*.65)
        self.add(references,labels)
        self.play(Create(ring),Create(even),Create(legacy),run_time=2)
        self.play(phase.animate.set_value(1.25),run_time=3)
        denser = DashedVMobject(curve.copy().set_color(RED),num_dashes=16,dashed_ratio=.8).shift(UP*.65)
        self.play(Transform(even,denser),run_time=2)
        self.play(FadeOut(ring),FadeOut(even),FadeOut(legacy),run_time=1)
        self.wait(1)
