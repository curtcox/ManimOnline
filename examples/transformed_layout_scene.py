"""Arrange transformed shapes in screen directions without changing orientation."""
from manim import *


class TransformedLayoutScene(Scene):
    def construct(self):
        shapes = VGroup(
            Rectangle(width=1.5,height=.8,color=BLUE),
            Circle(radius=.45,color=GREEN),
            Square(side_length=.7,color=YELLOW),
        ).arrange(RIGHT,buff=.5).rotate(PI/6).scale(.8)
        shapes.save_state()
        self.play(Create(shapes),run_time=2)
        self.play(shapes.animate.arrange(DOWN,buff=.5,aligned_edge=LEFT),run_time=2)
        self.play(shapes.animate.arrange(RIGHT,buff=.7),run_time=2)
        self.play(Restore(shapes),run_time=1)
        self.play(FadeOut(shapes),run_time=1)
        self.wait(1)
