from manim import *


class FirstPlot(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3, 1], y_range=[-2, 9, 1], x_length=7, y_length=6, tips=False).add_coordinates()
        parabola = axes.plot(lambda x: x ** 2, color=YELLOW)
        line = axes.plot(lambda x: 2 * x + 1, x_range=[-1.5, 3], color=BLUE)
        self.play(Create(axes))
        self.play(Create(parabola), Write(axes.get_graph_label(parabola, "x^2", x_val=-2.5)))
        self.play(Create(line), Write(axes.get_graph_label(line, "2x+1", x_val=2.5, direction=RIGHT)))
        crossings = [1 - 2 ** 0.5, 1 + 2 ** 0.5]          # where x^2 = 2x + 1
        dots = VGroup(*[Dot(axes.c2p(x, x ** 2), color=RED) for x in crossings])
        self.play(LaggedStart(*[FadeIn(d, scale=3) for d in dots], lag_ratio=0.5))
        self.wait()
