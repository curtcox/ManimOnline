"""Finite path tangents track motion and grow without changing the source."""
from manim import *


class TangentPathsScene(Scene):
    def construct(self):
        ellipse = Ellipse(width=3,height=2,color=BLUE).shift(LEFT*2.3)
        curve = CubicBezier((.3,-1.5),(1,3),(2,-3),(4,1.5),color=BLUE)
        alpha = ValueTracker(.1)
        extent = ValueTracker(1.8)
        left = always_redraw(lambda:VGroup(
               TangentLine(ellipse,alpha.get_value(),length=extent.get_value(),color=YELLOW,stroke_width=4),
               Dot(ellipse.point_from_proportion(alpha.get_value()),color=YELLOW)))
        right = always_redraw(lambda:VGroup(
                TangentLine(curve,alpha.get_value(),length=extent.get_value(),color=GREEN,stroke_width=4),
                Dot(curve.point_from_proportion(alpha.get_value()),color=GREEN)))
        labels = VGroup(Text('Ellipse tangent',font_size=24).move_to((-2.3,2.5,0)),
                        Text('Cubic tangent',font_size=24).move_to((2,2.5,0)))
        self.add(labels)
        self.play(Create(ellipse),Create(curve),FadeIn(left),FadeIn(right),run_time=2)
        self.play(alpha.animate.set_value(.8),run_time=3)
        self.play(extent.animate.set_value(3),run_time=2)
        self.play(FadeOut(left),FadeOut(right),run_time=1)
        self.wait(1)
