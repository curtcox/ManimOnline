"""Stretch nested vector families, including curved shafts and real tips."""
from manim import *


class StretchScene(Scene):
    def construct(self):
        circle = Circle(color=BLUE).shift(LEFT*2)
        box = Rectangle(width=1.4, height=.7, color=GREEN).shift(DOWN*.6)
        arrow = CurvedDoubleArrow(LEFT, RIGHT, angle=PI/2, color=YELLOW).shift(UP*.7)
        family = VGroup(circle, VGroup(box, arrow).shift(RIGHT*2)).rotate(PI/12)
        self.play(Create(family), run_time=2)
        family.save_state()
        self.play(family.animate.stretch(1.4, 0), run_time=2)
        self.play(family.animate.stretch_to_fit_height(2), run_time=2)
        self.play(Restore(family), run_time=1)
        self.play(FadeOut(family), run_time=1)
        self.wait(1)
