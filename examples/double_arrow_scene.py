"""Two-ended arrows with separate shapes, endpoint updates and checkpoints."""
from manim import *


class DoubleArrowScene(Scene):
    def construct(self):
        default = DoubleArrow(LEFT*3+UP,RIGHT*3+UP,buff=0,color=BLUE,tip_length=.6)
        mixed = DoubleArrow(LEFT*3+DOWN,RIGHT*3+DOWN,buff=0,color=GREEN,
                            tip_shape_start=ArrowSquareTip,
                            tip_shape_end=ArrowCircleFilledTip,tip_length=.6)
        default.save_state()
        mixed.save_state()
        markers = VGroup(Dot(default.get_start(),color=RED,radius=.08),
                         Dot(default.get_end(),color=WHITE,radius=.08),
                         Dot(mixed.get_start(),color=PURPLE,radius=.08),
                         Dot(mixed.get_end(),color=YELLOW,radius=.08))
        markers[0].add_updater(lambda dot:dot.move_to(default.get_start()))
        markers[1].add_updater(lambda dot:dot.move_to(default.get_end()))
        markers[2].add_updater(lambda dot:dot.move_to(mixed.get_start()))
        markers[3].add_updater(lambda dot:dot.move_to(mixed.get_end()))
        self.play(Create(default),Create(mixed),FadeIn(markers),run_time=2)
        self.play(default.animate.rotate(PI/6).scale(.7),
                  mixed.animate.rotate(-PI/6).scale(.7),run_time=2)
        self.play(default.animate.put_start_and_end_on(LEFT*2+UP,RIGHT*2+UP*2),
                  mixed.animate.put_start_and_end_on(LEFT*2+DOWN,RIGHT*2+DOWN*2),run_time=2)
        self.play(Restore(default),Restore(mixed),run_time=1)
        self.play(FadeOut(default),FadeOut(mixed),FadeOut(markers),run_time=1)
        self.wait(1)
