"""A function, its numerical derivative and a tangent tracking a changing input."""
from manim import *
from math import sin


class CalculusScene(Scene):
    def construct(self):
        axes = NumberPlane([-3,3],[-2,2],x_length=8,y_length=4,
                           background_line_style=dict(stroke_opacity=.3)).add_coordinates()
        graph = axes.plot(sin,x_range=[-3,3,.15],color=BLUE)
        derivative = axes.plot_derivative_graph(graph,x_range=[-3,3,.15],color=GREEN)
        recovered = axes.plot_antiderivative_graph(derivative,samples=30,x_range=[-3,3,.15],
                                                  color=RED,stroke_width=1)
        value = ValueTracker(-2)
        point = Dot(axes.i2gp(-2,graph),color=YELLOW)
        point.add_updater(lambda mob: mob.move_to(axes.i2gp(value.get_value(),graph)))
        def tangent():
            x = value.get_value()
            y = axes.i2gc(x,graph)[1]
            slope = axes.slope_of_tangent(x,graph)
            return Line(axes.c2p(x-.6,y-.6*slope),axes.c2p(x+.6,y+.6*slope),color=YELLOW)
        line = always_redraw(tangent)
        readout = DecimalNumber(axes.slope_of_tangent(-2,graph),num_decimal_places=2,color=GREEN).shift(UP*2.5)
        readout.add_updater(lambda mob: mob.set_value(axes.slope_of_tangent(value.get_value(),graph)))
        self.play(Create(axes),Create(graph),Create(derivative),Create(recovered),run_time=2)
        self.play(FadeIn(point),FadeIn(line),FadeIn(readout),run_time=1)
        self.play(value.animate.set_value(2),run_time=4,rate_func=linear)
        self.play(FadeOut(point),FadeOut(line),FadeOut(readout),run_time=1)
        self.wait(1)
