"""A labeled secant triangle follows a changing interval and graph input."""
from manim import *


class SecantScene(Scene):
    def construct(self):
        axes = NumberPlane([-2,3],[-2,3],x_length=8,y_length=4,
                           background_line_style=dict(stroke_opacity=.3)).add_coordinates()
        graph = axes.plot(lambda x:.5*x*x-.7,x_range=[-2,3,.15],color=BLUE)
        start = ValueTracker(0)
        interval = ValueTracker(1.5)
        secant = always_redraw(lambda: axes.get_secant_slope_group(start.get_value(),graph,
                              dx=interval.get_value(),dx_label='dx',dy_label='df',
                              dy_line_color=RED,secant_line_length=6))
        self.play(Create(axes),Create(graph),FadeIn(secant),run_time=2)
        self.play(interval.animate.set_value(.25),run_time=3)
        self.play(start.animate.set_value(1),run_time=2)
        self.play(FadeOut(secant),run_time=1)
        self.wait(1)
