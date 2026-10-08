"""Render either scene by entering its class name in the browser's Scene field."""
from manim import *


class Circles(Scene):
    def construct(self):
        self.play(Create(Circle(color=BLUE)))
        self.wait(1)


class RotatingSquare(Scene):
    def construct(self):
        square = Square(color=YELLOW).scale(0.6)
        self.play(Create(square))
        self.play(square.animate.scale(2).rotate(PI / 4), run_time=2)
        self.wait(1)
