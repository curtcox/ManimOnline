"""Angle owns an editable path; its dot remains a separate child."""
from manim import *


class AnglePathScene(Scene):
    def construct(self):
        first = Line(ORIGIN,RIGHT*3,color=BLUE)
        second = Line(ORIGIN,UP*3,color=BLUE)
        angle = Angle(first,second,radius=2,dot=True,dot_color=GREEN,
                      color=YELLOW,stroke_width=5).save_state()
        marker = Dot(angle.get_start(),color=WHITE)
        self.add(VGroup(first,second))
        self.play(FadeIn(marker),Create(angle),run_time=2)
        self.play(MoveAlongPath(marker,angle),run_time=3)
        self.play(Transform(angle,RightAngle(first,second,length=2,color=RED,
                                            stroke_width=5)),run_time=2)
        self.play(Restore(angle),run_time=1)
        self.play(FadeOut(angle),FadeOut(marker),run_time=1)
        self.wait(1)
