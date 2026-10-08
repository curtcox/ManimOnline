"""Editable arrow-tip outlines, transforms, live anchor queries and restoration."""
from manim import *


class TipGeometryScene(Scene):
    def construct(self):
        outline = ArrowTriangleTip(length=1.5,width=1,color=BLUE).shift(LEFT*3)
        filled = ArrowTriangleFilledTip(length=1.5,width=1,color=GREEN)
        stealth = StealthTip(length=1.5,color=YELLOW).shift(RIGHT*3)
        filled.save_state()
        point = Dot(filled.tip_point,color=WHITE,radius=.1)
        base = Dot(filled.base,color=PURPLE,radius=.1)
        point.add_updater(lambda dot:dot.move_to(filled.tip_point))
        base.add_updater(lambda dot:dot.move_to(filled.base))
        self.play(Create(outline),Create(filled),Create(stealth),FadeIn(point),FadeIn(base),run_time=2)
        self.play(filled.animate.rotate(PI/2).scale(1.4),run_time=2)
        self.play(Transform(filled,StealthTip(length=1.5,color=RED).move_to(filled.get_center())),run_time=2)
        self.play(Restore(filled),run_time=1)
        self.play(FadeOut(outline),FadeOut(filled),FadeOut(stealth),FadeOut(point),FadeOut(base),run_time=1)
        self.wait(1)
