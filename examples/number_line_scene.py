"""Numeric coordinates and a marker following an animated number line."""
from manim import *


class NumberLineScene(Scene):
    def construct(self):
        line = NumberLine(x_range=[-3,3,1], length=8.5, include_tip=True,
                          include_numbers=True, font_size=24, line_to_number_buff=.4,
                          numbers_with_elongated_ticks=[0], color=BLUE)
        line.save_state()
        value = ValueTracker(-2.5)
        marker = Dot(line.n2p(value.get_value()), color=YELLOW)
        marker.add_updater(lambda mob: mob.move_to(line.n2p(value.get_value())))
        label = DecimalNumber(value.get_value(), num_decimal_places=1).shift(UP*2.5)
        label.add_updater(lambda mob: mob.set_value(value.get_value()))
        self.add(label)
        self.play(Create(line), FadeIn(marker), run_time=2)
        self.play(value.animate.set_value(2.5), run_time=3, rate_func=linear)
        self.play(line.animate.rotate(PI/6).scale(.8).shift(UP),
                  value.animate.set_value(-1.5), run_time=3, rate_func=linear)
        self.play(Restore(line), value.animate.set_value(0), run_time=2)
        self.wait(1)
