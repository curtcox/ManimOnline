from manim import *


class FixTheTypo(Scene):
    def construct(self):
        square = Square(color=BLUE)
        circle = Circel(color=YELLOW)  # This line has a typo. Read the error, then fix it.
        self.play(Create(square))
        self.play(Transform(square, circle))
        self.wait()
