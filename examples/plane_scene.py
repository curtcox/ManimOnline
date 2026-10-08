"""Cartesian grids, plotted functions and moving vectors on a transformed plane."""
from manim import *


class PlaneScene(Scene):
    def construct(self):
        plane = NumberPlane([-3,3],[-2,2],x_length=8,y_length=4,faded_line_ratio=2,
                            background_line_style=dict(stroke_width=2,stroke_opacity=.5)).add_coordinates()
        plane.save_state()
        value = ValueTracker(-2)
        function = lambda x: .3*x*x-1
        graph = always_redraw(lambda: plane.plot(function,x_range=[-3,3,.15],color=RED))
        marker = Dot(plane.i2gp(value.get_value(),graph),color=YELLOW)
        marker.add_updater(lambda mob: mob.move_to(plane.i2gp(value.get_value(),graph)))
        vector = always_redraw(lambda: plane.get_vector([value.get_value(),function(value.get_value())],
                                                       color=YELLOW))
        self.play(Create(plane),Create(graph),FadeIn(marker),FadeIn(vector),run_time=2)
        self.play(value.animate.set_value(2),run_time=3,rate_func=linear)
        self.play(plane.animate.rotate(PI/6).scale(.8).shift(UP*.3),run_time=2)
        self.play(Restore(plane),run_time=2)
        self.play(FadeOut(marker),FadeOut(vector),run_time=1)
        self.wait(1)
