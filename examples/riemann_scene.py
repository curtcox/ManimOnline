"""Refine signed area estimates, then compare the region between two functions."""
from manim import *


class RiemannScene(Scene):
    def construct(self):
        axes = NumberPlane([-2,2],[-2,2],x_length=8,y_length=4,
                           background_line_style=dict(stroke_opacity=.3)).add_coordinates()
        graph = axes.plot(lambda x:.5*x*x-.7,x_range=[-2,2,.1],color=WHITE)
        rectangles = axes.get_riemann_rectangles(graph,dx=.5,input_sample_type='center',
                                                fill_opacity=.65,color=[BLUE,GREEN])
        fine = axes.get_riemann_rectangles(graph,dx=.125,input_sample_type='center',
                                          fill_opacity=.65,color=[BLUE,GREEN])
        bound = axes.plot(lambda x:.3*x-.4,x_range=[-2,2,.1],color=YELLOW)
        between = axes.get_riemann_rectangles(graph,bounded_graph=bound,dx=.25,
                                             input_sample_type='center',fill_opacity=.65,
                                             color=[BLUE,GREEN])
        self.play(Create(axes),Create(graph),FadeIn(rectangles),run_time=2)
        self.play(Transform(rectangles,fine),run_time=2)
        self.play(Create(bound),Transform(rectangles,between),run_time=2)
        self.play(FadeOut(rectangles),FadeOut(bound),run_time=1)
        self.wait(1)
