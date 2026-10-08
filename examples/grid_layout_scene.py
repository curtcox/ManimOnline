"""Reflow a transformed grid while preserving shape orientation."""
from manim import *


class GridLayoutScene(Scene):
    def construct(self):
        shapes = VGroup(
            Rectangle(width=1.4,height=.8,color=BLUE),
            Circle(radius=.45,color=GREEN),
            Square(side_length=.7,color=YELLOW),
            Circle(radius=.35,color=RED),
            Rectangle(width=1,height=.6,color=PURPLE),
            Square(side_length=.9,color=WHITE),
        ).arrange_in_grid(rows=2,cols=3,buff=(.5,.4)).rotate(PI/10).scale(.8)
        shapes.save_state()
        self.play(Create(shapes),run_time=2)
        self.play(shapes.animate.arrange_in_grid(rows=3,cols=2,buff=(.6,.3),col_alignments='lr'),run_time=2)
        self.play(shapes.animate.arrange_in_grid(rows=2,cols=3,buff=(.4,.6),flow_order='ur'),run_time=2)
        self.play(Restore(shapes),run_time=1)
        self.play(FadeOut(shapes),run_time=1)
        self.wait(1)
