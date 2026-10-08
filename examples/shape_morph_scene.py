"""Morph primitive outlines, restore a circle, and finish as a cubic curve."""
from manim import *


class ShapeMorphScene(Scene):
    def construct(self):
        shape = Circle(color=BLUE, fill_opacity=0.15).scale(1.2).save_state()
        title = Text("Morph built-in shapes", font_size=30).shift(UP * 2.5)
        self.play(Create(shape), FadeIn(title), run_time=2)
        self.play(Transform(shape, Square(color=RED, fill_opacity=0.2)), run_time=2)
        self.play(Transform(shape, Triangle(color=GREEN, fill_opacity=0.3).scale(3)), run_time=2)
        self.play(Restore(shape), run_time=2)
        curve = CubicBezier((-3,-1,0), (-1,3,0), (1,-3,0), (3,1,0), color=PURPLE)
        self.play(Transform(shape, curve), run_time=2)
        self.wait(1)
