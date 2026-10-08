"""Regenerate a circle and shape family from an animated parameter."""
from manim import *


class RedrawScene(Scene):
    def construct(self):
        size = ValueTracker(.5)
        circle = always_redraw(lambda: Circle(radius=size.get_value(), color=BLUE, fill_opacity=.2).shift(LEFT*2))
        family = always_redraw(lambda: VGroup(
            Square(side_length=size.get_value(), color=YELLOW).shift(RIGHT*2),
            Triangle(color=RED).scale(size.get_value()).shift(RIGHT*2+UP*2)
        ))
        self.add(size, circle, family)
        self.play(size.animate.set_value(1.5), run_time=3, rate_func=linear)
        circle.suspend_updating()
        self.play(size.animate.set_value(.5), run_time=2, rate_func=linear)
        circle.resume_updating()
        family.clear_updaters()
        self.play(size.animate.set_value(1), run_time=2, rate_func=linear)
        self.wait(1)
