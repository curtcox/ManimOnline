"""Moving a child updates family bounds without moving the transformed host."""
from manim import *


class ChildMotionScene(Scene):
    def construct(self):
        x = ValueTracker(-3)
        child = Dot(LEFT*3,color=YELLOW,radius=.2)
        child.add_updater(lambda dot:dot.move_to((x.get_value(),.5,0)))
        sibling = Dot(ORIGIN,color=GREEN,radius=.2)
        host = Rectangle(width=3,height=1.5,color=BLUE,fill_opacity=.2)
        host.add(child,sibling).rotate(PI/6).scale(.8)
        anchor = Dot(host.get_start(),color=RED)
        self.play(Create(host),FadeIn(anchor),run_time=2)
        self.play(x.animate.set_value(3),run_time=3)
        self.play(x.animate.set_value(-1),run_time=2)
        self.play(FadeOut(host),FadeOut(anchor),run_time=1)
        self.wait(1)
