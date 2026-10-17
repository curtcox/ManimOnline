import math

from manim import *


class MovingBound(Scene):
    def construct(self):
        axes = Axes(x_range=[0, 6.5, 1], y_range=[-1.5, 1.5, 0.5], x_length=10, y_length=4).shift(DOWN * 0.5)
        graph = axes.plot(math.sin, x_range=[0, 6.5], color=YELLOW)
        b = ValueTracker(0.01)
        area = always_redraw(lambda: axes.get_area(graph, x_range=[0, b.get_value()], color=[BLUE, GREEN], opacity=0.5))
        edge = always_redraw(lambda: axes.get_vertical_line(axes.i2gp(b.get_value(), graph), color=WHITE))
        caption = MathTex(r"\int_0^{b} \sin x \, dx =").to_corner(UL)
        value = DecimalNumber(0, num_decimal_places=2).next_to(caption, RIGHT)
        value.add_updater(lambda m: m.set_value(1 - math.cos(b.get_value())))
        self.add(axes, graph, area, edge, caption, value)
        self.play(b.animate.set_value(TAU), run_time=6, rate_func=linear)
        self.wait()
