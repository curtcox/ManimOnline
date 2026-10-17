from manim import *


class ThreeShapes(Scene):
    def construct(self):
        shape = Square(color=BLUE, fill_opacity=0.5)
        self.play(Create(shape))
        self.play(Transform(shape, Circle(color=YELLOW, fill_opacity=0.5)))
        self.play(Transform(shape, Triangle(color=RED, fill_opacity=0.5)))
        # Try it: add another line here that turns the shape into Star(color=GREEN).
        self.wait()
