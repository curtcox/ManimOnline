"""Ordinary shapes retain their own path while hosting child geometry."""
from manim import *


class ShapeFamilyScene(Scene):
    def construct(self):
        host = Rectangle(width=4,height=2,color=BLUE,fill_opacity=.15)
        left = Dot(LEFT,color=YELLOW,radius=.2)
        right = Dot(RIGHT,color=GREEN,radius=.2)
        host.add(left,right).save_state()
        nested = Circle(radius=.45,color=RED).add(Dot(color=WHITE))
        self.play(Create(host),run_time=2)
        self.play(host.animate.rotate(PI/4).shift(LEFT),run_time=2)
        host.add_to_back(nested)
        self.wait(1)
        host.remove(left)
        self.wait(1)
        self.play(Restore(host),run_time=2)
        self.play(FadeOut(host),run_time=1)
        self.wait(1)
