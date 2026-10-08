"""Tip style dictionaries, independent widths and detached tip factories."""
from manim import *


class TipStyleScene(Scene):
    def construct(self):
        straight = Arrow(LEFT*3+UP,RIGHT*3+UP,buff=0,color=BLUE,tip_length=.6,
                         tip_style={"fill_color":RED,"stroke_color":YELLOW,
                                    "fill_opacity":.4,"stroke_width":3,"width":.8})
        curved = CurvedDoubleArrow(LEFT*3+DOWN,RIGHT*3+DOWN,angle=PI/2,color=GREEN,
                                  tip_length=.6,
                                  tip_style={"fill_color":YELLOW,"stroke_color":PURPLE,
                                             "fill_opacity":.5,"stroke_width":3,"width":.7})
        straight.save_state()
        curved.save_state()
        self.play(Create(straight),Create(curved),run_time=2)
        self.play(straight.animate.rotate(PI/10).scale(.8),
                  curved.animate.rotate(-PI/10).scale(.8),run_time=2)
        straight.tip_style.pop("width")
        head = straight.create_tip(tip_length=.6,tip_width=1.1)
        # The factory positions a detached tip before it is attached.
        head.set_fill(GREEN,opacity=.8).set_stroke(WHITE,width=2)
        straight.pop_tips()
        straight.add_tip(tip=head)
        self.wait(2)
        self.play(Restore(straight),Restore(curved),run_time=1)
        self.play(FadeOut(straight),FadeOut(curved),run_time=1)
        self.wait(1)
