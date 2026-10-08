"""Dashed coordinate projections follow a graph and a rotating frame."""
from manim import *


class GuidesScene(Scene):
    def construct(self):
        axes = NumberPlane([-2,3],[-1,3],x_length=8,y_length=4,
                           background_line_style=dict(stroke_opacity=.25)).add_coordinates()
        curve = axes.plot(lambda x:.4*x*x+.2,x_range=[-2,3,.15],color=BLUE)
        value = ValueTracker(-1.5)
        marker = always_redraw(lambda:Dot(axes.i2gp(value.get_value(),curve),color=YELLOW))
        guides = always_redraw(lambda:axes.get_lines_to_point(axes.i2gp(value.get_value(),curve),color=GREEN,
                               line_config=dict(dash_length=.15,dashed_ratio=.6)))
        self.play(Create(axes),Create(curve),FadeIn(guides),FadeIn(marker),run_time=2)
        self.play(value.animate.set_value(2),run_time=3)
        self.play(axes.animate.rotate(PI/6),curve.animate.rotate(PI/6,about_point=axes.get_center()),run_time=2)
        self.play(FadeOut(guides),FadeOut(marker),run_time=1)
        self.wait(1)
