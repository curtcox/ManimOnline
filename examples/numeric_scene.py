"""Display sampled tracker values and animate a number directly."""
from manim import *


class NumericScene(Scene):
    def construct(self):
        value = ValueTracker(-2)
        dot = Dot(color=BLUE)
        dot.add_updater(lambda m: m.move_to(RIGHT * value.get_value()))
        decimal = DecimalNumber(-2, include_sign=True, font_size=36, color=BLUE)
        decimal.add_updater(lambda m: m.set_value(value.get_value()).move_to(dot.get_center() + UP))
        integer = Integer(-2, font_size=36, color=YELLOW)
        integer.add_updater(lambda m: m.set_value(value.get_value()).move_to(dot.get_center() + DOWN))
        total = DecimalNumber(1000, num_decimal_places=0, unit=' points', font_size=32, color=GREEN)
        total.shift(DOWN * 2.5).save_state()
        self.add(value, dot, decimal, integer, total)
        self.play(value.animate.set_value(2), run_time=4, rate_func=linear)
        self.play(total.animate.set_value(2500), run_time=2, rate_func=linear)
        self.play(Restore(total), run_time=2, rate_func=linear)
        self.wait(1)
