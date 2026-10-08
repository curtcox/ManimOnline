"""Drive two objects and their connector from one animated real parameter."""
from manim import *


class TrackedValueScene(Scene):
    def construct(self):
        value = ValueTracker(-2)
        dot = Dot(color=BLUE)
        square = Square(side_length=.6, color=YELLOW)
        connector = Line(color=GREEN)
        dot.add_updater(lambda m: m.move_to(RIGHT * value.get_value() + DOWN))
        square.add_updater(lambda m: m.move_to(LEFT * value.get_value() + UP))
        connector.add_updater(lambda m: m.put_start_and_end_on(dot.get_center(), square.get_center()))
        self.add(value, dot, square, connector)
        self.play(value.animate.set_value(2), run_time=4, rate_func=linear)
        self.play(Succession(value.animate.increment_value(-1), value.animate.increment_value(-1)))
        self.wait(1)
