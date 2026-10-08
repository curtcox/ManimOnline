"""Reorder equal-depth roots, clear the display, and reuse an object."""
from manim import *


class OrderScene(Scene):
    def construct(self):
        square = Square(color=BLUE, fill_opacity=1).shift(LEFT * 0.5)
        triangle = Triangle(color=GREEN, fill_opacity=1).scale(2).shift(RIGHT * 0.5)
        group = VGroup(square, triangle)
        circle = Circle(color=RED, fill_opacity=1, radius=0.8).shift(DOWN * 0.3)
        title = Text("Scene draw order", font_size=30).shift(UP * 2.5)
        self.add(group, circle, title)
        self.wait(1)
        self.bring_to_front(group)
        self.play(Rotate(group, PI / 6), run_time=2)
        self.bring_to_back(group)
        self.wait(1)
        self.clear()
        self.wait(1)
        self.play(FadeIn(title))
        self.wait(1)
