"""Shared tip APIs on open arcs and closed circle outlines."""
from manim import *


class GenericTipsScene(Scene):
    def construct(self):
        arc = Arc(radius=1.6, start_angle=PI/6, angle=4*PI/3,
                  arc_center=LEFT*2, color=BLUE, tip_length=.5)
        arc.add_tip().add_tip(at_start=True, tip_shape=ArrowTriangleTip)
        circle = Circle(radius=1.3, color=GREEN, tip_length=.5).shift(RIGHT*2)
        circle.add_tip(tip_shape=StealthTip)
        arc.save_state()
        circle.save_state()
        self.play(Create(arc), Create(circle), run_time=2)
        self.play(arc.animate.rotate(PI/4).scale(.8),
                  circle.animate.rotate(-PI/3).scale(.8), run_time=2)
        self.play(arc.animate.put_start_and_end_on(LEFT*3+DOWN, LEFT+UP),
                  circle.animate.shift(UP), run_time=2)
        self.play(Restore(arc), Restore(circle), run_time=1)
        self.play(FadeOut(arc), FadeOut(circle), run_time=1)
        self.wait(1)
