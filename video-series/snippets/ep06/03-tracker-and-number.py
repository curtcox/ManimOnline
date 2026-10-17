from manim import *


class TrackerAndNumber(Scene):
    def construct(self):
        x = ValueTracker(0)
        line = NumberLine(x_range=[0, 10, 1], length=10, include_numbers=True).shift(DOWN)
        pointer = Triangle(color=YELLOW, fill_opacity=1).scale(0.2).rotate(PI)
        pointer.add_updater(lambda m: m.next_to(line.n2p(x.get_value()), UP, buff=0.1))
        readout = DecimalNumber(0, num_decimal_places=2, font_size=48)
        readout.add_updater(lambda m: m.set_value(x.get_value()).next_to(pointer, UP))
        self.add(line, pointer, readout)
        self.play(x.animate.set_value(7.5), run_time=3)
        self.play(x.animate.set_value(2), run_time=2)
        self.play(x.animate.increment_value(5), run_time=2)
        self.wait()
