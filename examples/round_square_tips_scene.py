"""Circular and square tips with transformed shafts and endpoint markers."""
from manim import *


class RoundSquareTipsScene(Scene):
    def construct(self):
        circle = Arrow(LEFT*3+UP,RIGHT*3+UP,buff=0,color=BLUE,
                       tip_shape=ArrowCircleFilledTip,tip_length=.7)
        circle.add_tip(at_start=True,tip_shape=ArrowCircleTip,tip_length=.7)
        square = Arrow(LEFT*3+DOWN,RIGHT*3+DOWN,buff=0,color=GREEN,
                       tip_shape=ArrowSquareFilledTip,tip_length=.7)
        square.add_tip(at_start=True,tip_shape=ArrowSquareTip,tip_length=.7)
        circle.save_state()
        square.save_state()
        top = Dot(circle.get_end(),color=WHITE,radius=.08)
        bottom = Dot(square.get_end(),color=YELLOW,radius=.08)
        top.add_updater(lambda dot:dot.move_to(circle.get_end()))
        bottom.add_updater(lambda dot:dot.move_to(square.get_end()))
        self.play(Create(circle),Create(square),FadeIn(top),FadeIn(bottom),run_time=2)
        self.play(circle.animate.rotate(PI/6).scale(.8),
                  square.animate.rotate(-PI/6).scale(.8),run_time=2)
        self.play(circle.animate.put_start_and_end_on(LEFT*2+UP,RIGHT*2+UP*2),
                  square.animate.put_start_and_end_on(LEFT*2+DOWN,RIGHT*2+DOWN*2),run_time=2)
        self.play(Restore(circle),Restore(square),run_time=1)
        self.play(FadeOut(circle),FadeOut(square),FadeOut(top),FadeOut(bottom),run_time=1)
        self.wait(1)
