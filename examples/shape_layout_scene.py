"""Arrange a shape's children while preserving its own transformed outline."""
from manim import *


class ShapeLayoutScene(Scene):
    def construct(self):
        host = Rectangle(width=6,height=4,color=BLUE,fill_opacity=.1)
        host.add(*(Dot(LEFT*1.5,color=color,radius=.15)
                   for color in (GREEN,YELLOW,RED,PURPLE)))
        host.arrange_submobjects(RIGHT,buff=.5,center=False)
        host.rotate(PI/8).scale(.8)
        host.save_state()
        anchor = Dot(host.get_start(),color=WHITE)
        self.play(Create(host),FadeIn(anchor),run_time=2)
        self.play(host.animate.arrange_in_grid(rows=2,cols=2,buff=(.6,.5)),run_time=2)
        self.play(host.animate.arrange_submobjects(DOWN,buff=.4,center=False),run_time=2)
        self.play(Restore(host),run_time=1)
        self.play(FadeOut(host),FadeOut(anchor),run_time=1)
        self.wait(1)
