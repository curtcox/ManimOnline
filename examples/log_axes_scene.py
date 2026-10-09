"""Logarithmic axes with base-10 labels, exponential growth and ManimColor helpers."""
from manim import *


class LogAxesScene(Scene):
    def construct(self):
        axes = Axes(x_range=[0, 10, 1], y_range=[-1, 4, 1], x_length=9, y_length=5.5, tips=False,
                    axis_config={"include_numbers": True},
                    y_axis_config={"scaling": LogBase(custom_labels=True)})
        self.play(Create(axes), run_time=2)
        palette = RandomColorGenerator(seed=7)
        curves = VGroup(*(axes.plot(lambda x, b=b: b ** x, x_range=[0, min(10, 4 / np.log10(b))], color=palette.next())
                          for b in (2, 3, 10)))
        self.play(LaggedStart(*(Create(c) for c in curves), lag_ratio=.4), run_time=3)
        dot = Dot(axes.c2p(1, 2), color=ManimColor("#FFD700"))
        label = DecimalNumber(2, num_decimal_places=1, unit=r"\,\text{units}", font_size=30)
        label.add_updater(lambda m: m.set_value(axes.p2c(dot.get_center())[1]).next_to(dot, UR, buff=.1))
        self.add(dot, label)
        self.play(MoveAlongPath(dot, curves[0]), run_time=3)
        self.play(curves.animate.set_color(RED.lighter(.4)))
        self.wait(.5)
