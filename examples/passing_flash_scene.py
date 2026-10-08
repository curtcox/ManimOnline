"""Traveling outline highlights, simultaneous groups, and reusable flash objects."""
from manim import *


class PassingFlashScene(Scene):
    def construct(self):
        curve = CubicBezier((-3,-1), (-2,2), (2,-2), (3,1)).shift(DOWN)
        outlines = VGroup(Circle(radius=.9).shift(LEFT*1.5),
                          RoundedRectangle(width=2, height=1.6, corner_radius=.3).shift(RIGHT*1.5))
        outlines.rotate(PI/12).shift(UP*1.5)
        curve.set_stroke(color=GRAY, width=3)
        outlines.set_stroke(color=GRAY, width=3)
        flash = curve.copy().set_stroke(color=YELLOW, width=8)
        group_flash = outlines.copy().set_stroke(color=BLUE, width=7)
        self.add(curve, outlines)
        self.play(ShowPassingFlash(flash, time_width=.3, rate_func=linear),
                  ShowPassingFlash(group_flash, time_width=.4, rate_func=linear), run_time=4)
        self.play(Succession(ShowPassingFlash(flash, time_width=.6, run_time=2),
                             ShowPassingFlash(flash, time_width=.2, run_time=2)))
        self.wait(1)
