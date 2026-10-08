"""Real arrow tip children, endpoint edits, fixed-size heads and restoration."""
from manim import *


class ArrowTipsScene(Scene):
    def construct(self):
        arrow = Arrow(LEFT*3,RIGHT*3,buff=0,color=BLUE,tip_length=.6)
        arrow.add_tip(at_start=True,tip_shape=ArrowTriangleTip,tip_length=.6)
        arrow.save_state()
        point = Dot(arrow.get_end(),color=WHITE,radius=.1)
        point.add_updater(lambda dot:dot.move_to(arrow.get_end()))
        self.play(Create(arrow),FadeIn(point),run_time=2)
        self.play(arrow.animate.scale(.6).rotate(PI/4),run_time=2)
        self.play(arrow.animate.put_start_and_end_on(LEFT*2+DOWN,RIGHT*2+UP),run_time=2)
        arrow.pop_tips()
        arrow.add_tip(tip_shape=StealthTip,tip_length=.6)
        self.wait(1)
        self.play(Restore(arrow),run_time=1)
        self.play(FadeOut(arrow),FadeOut(point),run_time=1)
        self.wait(1)
