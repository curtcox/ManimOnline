"""Expand a gradient area, then fill the region between two functions."""
from manim import *


class AreaScene(Scene):
    def construct(self):
        axes = Axes([-2,3],[-1,3],x_length=8,y_length=4).add_coordinates()
        curve = axes.plot(lambda x:.5*x*x-.4,x_range=[-2,3,.12],color=BLUE)
        lower = axes.plot(lambda x:-.3*x-.4,x_range=[-1.5,2,.12],color=YELLOW)
        end = ValueTracker(-.5)
        area = always_redraw(lambda:axes.get_area(curve,[-1.5,end.get_value()],
                              color=[BLUE,GREEN],opacity=.5,stroke_width=0).set_z_index(-1))
        self.play(Create(axes),Create(curve),FadeIn(area),run_time=2)
        self.play(end.animate.set_value(2),run_time=3)
        area.clear_updaters()
        between = axes.get_area(curve,[-1.5,2],bounded_graph=lower,
                                color=[RED,YELLOW],opacity=.5,stroke_width=0).set_z_index(-1)
        self.play(Create(lower),Transform(area,between),run_time=2)
        self.play(FadeOut(area),FadeOut(lower),run_time=1)
        self.wait(1)
