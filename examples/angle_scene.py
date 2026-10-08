"""Signed angle marks follow a rotating line; corner marks stay independent."""
from manim import *


class AngleScene(Scene):
    def construct(self):
        vertex = LEFT*2
        base = Line(vertex,vertex+RIGHT*2.5,color=BLUE)
        moving = Line(vertex,vertex+RIGHT*2.5,color=BLUE).set_angle(PI/6)
        mark = always_redraw(lambda:Angle(base,moving,radius=.7,color=YELLOW,
                             dot=True,dot_color=GREEN))
        label = always_redraw(lambda:DecimalNumber(
                    Angle(base,moving).get_value(degrees=True),num_decimal_places=0,
                    font_size=30,color=YELLOW).move_to((-2,2.2,0)))
        horizontal = Line(RIGHT,RIGHT*3,color=BLUE)
        vertical = Line(RIGHT,RIGHT+UP*2,color=BLUE)
        corner = RightAngle(horizontal,vertical,length=.5,color=GREEN)
        reverse = Angle(horizontal,vertical,radius=.9,other_angle=True,color=RED)
        self.add(base,moving,horizontal,vertical)
        self.play(FadeIn(mark),FadeIn(label),Create(corner),Create(reverse),run_time=2)
        self.play(moving.animate.set_angle(PI*2/3),run_time=3)
        self.play(moving.animate.set_angle(PI/2),run_time=2)
        self.play(FadeOut(mark),FadeOut(label),FadeOut(corner),FadeOut(reverse),run_time=1)
        self.wait(1)
