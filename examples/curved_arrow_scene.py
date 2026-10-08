"""Tangent-aligned curved arrows, affine endpoint fitting and restoration."""
from manim import *


class CurvedArrowScene(Scene):
    def construct(self):
        upper = CurvedArrow(LEFT*3+UP,RIGHT*3+UP,angle=-PI/2,color=BLUE,tip_length=.6)
        lower = CurvedDoubleArrow(LEFT*3+DOWN,RIGHT*3+DOWN,angle=PI/2,color=GREEN,
                                 tip_shape_start=ArrowSquareTip,
                                 tip_shape_end=ArrowCircleFilledTip,tip_length=.6)
        upper.save_state()
        lower.save_state()
        markers = VGroup(Dot(upper.get_start(),color=RED,radius=.08),
                         Dot(upper.get_end(),color=WHITE,radius=.08),
                         Dot(lower.get_start(),color=PURPLE,radius=.08),
                         Dot(lower.get_end(),color=YELLOW,radius=.08))
        markers[0].add_updater(lambda dot:dot.move_to(upper.get_start()))
        markers[1].add_updater(lambda dot:dot.move_to(upper.get_end()))
        markers[2].add_updater(lambda dot:dot.move_to(lower.get_start()))
        markers[3].add_updater(lambda dot:dot.move_to(lower.get_end()))
        self.play(Create(upper),Create(lower),FadeIn(markers),run_time=2)
        self.play(upper.animate.rotate(PI/8).scale(.8),
                  lower.animate.rotate(-PI/8).scale(.8),run_time=2)
        self.play(upper.animate.put_start_and_end_on(LEFT*2+UP,RIGHT*2+UP*2),
                  lower.animate.put_start_and_end_on(LEFT*2+DOWN,RIGHT*2+DOWN*2),run_time=2)
        self.play(Restore(upper),Restore(lower),run_time=1)
        self.play(FadeOut(upper),FadeOut(lower),FadeOut(markers),run_time=1)
        self.wait(1)
