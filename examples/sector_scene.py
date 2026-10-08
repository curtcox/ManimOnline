"""Create and morph connected circular and annular sector outlines."""
from manim import *


class SectorScene(Scene):
    def construct(self):
        wedge = Sector(radius=1.5, angle=PI/2, color=BLUE,
                       stroke_width=2).move_to(LEFT * 2)
        ring = AnnularSector(inner_radius=.7, outer_radius=1.5,
                             angle=-3*PI/2, color=YELLOW,
                             stroke_width=2).move_to(RIGHT * 2)
        ring.save_state()
        self.play(Create(wedge), Create(ring), run_time=2)
        dot = Dot(color=WHITE).move_to(wedge.get_start())
        self.add(dot)
        self.play(MoveAlongPath(dot, wedge), run_time=3, rate_func=linear)
        self.play(FadeOut(dot), Transform(ring, Sector(radius=1.5, angle=PI,
                  color=GREEN).move_to(RIGHT * 2)), run_time=2)
        self.play(Restore(ring), wedge.animate.rotate(PI/2), run_time=2)
        self.wait(1)
