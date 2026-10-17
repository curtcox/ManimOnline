from manim import *


class SquareToCircle(Scene):
    def construct(self):
        square = Square(color=BLUE)
        circle = Circle(color=YELLOW)
        self.play(Create(square))
        self.play(Transform(square, circle))
        self.wait()
