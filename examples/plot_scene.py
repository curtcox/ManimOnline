"""Smooth function plots, exact graph-input queries and a closed parametric curve."""
from manim import *
from math import cos, sin


class PlotScene(Scene):
    def construct(self):
        axes = Axes([-3,3],[-2,3],x_length=8,y_length=4,
                    axis_config=dict(font_size=22,line_to_number_buff=.4)).add_coordinates()
        coefficient = ValueTracker(1/3)
        function = lambda x: coefficient.get_value()*x*x-1
        graph = always_redraw(lambda: axes.plot(function,x_range=[-3,3,.15],color=BLUE))
        value = ValueTracker(-2)
        marker = Dot(axes.i2gp(value.get_value(),graph),color=YELLOW)
        marker.add_updater(lambda mob: mob.move_to(axes.i2gp(value.get_value(),graph)))
        loop = axes.plot_parametric_curve(lambda t: (2*cos(t),.6+.6*sin(t)),
                                          t_range=[0,TAU,.2],color=RED)
        self.play(Create(axes),Create(graph),FadeIn(marker),run_time=2)
        self.play(value.animate.set_value(2),run_time=3,rate_func=linear)
        self.play(coefficient.animate.set_value(.15),run_time=2,rate_func=linear)
        self.play(ShowPassingFlash(graph.copy().set_stroke(color=YELLOW,width=7),time_width=.3),
                  Create(loop),run_time=2)
        self.play(FadeOut(marker),FadeOut(loop),run_time=1)
        self.wait(1)
