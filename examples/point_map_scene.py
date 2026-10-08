"""Shear and warp a grid with matrix, point and complex function maps."""
from manim import *


class PointMapScene(Scene):
    def construct(self):
        grid = VGroup(*(Line((x,-1,0),(x,1,0),color=GRAY,stroke_width=1)
                        for x in (-3,-2,-1,0,1,2,3)),
                      *(Line((-3,y,0),(3,y,0),color=GRAY,stroke_width=1)
                        for y in (-1,0,1)))
        circle = Circle(radius=.7,color=BLUE).shift(LEFT*1.5)
        square = Square(side_length=.9,color=GREEN).shift(RIGHT*1.5)
        arrow = DoubleArrow(LEFT*3+UP*1.4,RIGHT*3+UP*1.4,buff=0,color=YELLOW)
        family = VGroup(grid,circle,square,arrow)
        self.play(Create(family),run_time=2)
        family.save_state()
        self.play(family.animate.apply_matrix([[1,.5],[0,1]]),run_time=2)
        self.play(family.animate.apply_function(lambda p:(p[0],p[1]+.15*p[0]**2,0)),run_time=2)
        self.play(family.animate.apply_complex_function(lambda z:z*(.8+.2j)),run_time=2)
        self.play(Restore(family),run_time=1)
        self.play(FadeOut(family),run_time=1)
        self.wait(1)
