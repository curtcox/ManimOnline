"""Draw an orbit, move a square around it, then erase the square's outline."""
from manim import *


class Orbit(Scene):
    def construct(self):
        orbit = Circle(radius=2, color=BLUE)
        square = Square(side_length=0.6, color=YELLOW).shift(RIGHT * 2)
        self.play(Create(orbit), Create(square), run_time=2)
        self.play(Rotate(square, TAU, about_point=ORIGIN), run_time=4, rate_func=linear)
        self.play(Uncreate(square), run_time=1)
        self.wait(1)
