"""Moving, adding and removing children must not move their group siblings."""
from manim import *


class GroupMotionScene(Scene):
    def construct(self):
        x = ValueTracker(-3)
        child = Dot(LEFT*3,color=YELLOW,radius=.2)
        child.add_updater(lambda dot:dot.move_to((x.get_value(),.5,0)))
        sibling = Circle(radius=.6,color=GREEN)
        inner = VGroup(child,sibling).rotate(PI/6).scale(.8)
        fixed = Square(side_length=1,color=BLUE).shift(RIGHT*3)
        host = Group(inner,fixed).rotate(-PI/8).scale(.9)
        anchor = Dot(host._point_to_world(inner._point_to_world(sibling.get_center())),color=RED)
        self.play(Create(host),FadeIn(anchor),run_time=2)
        self.play(x.animate.set_value(3),run_time=3)
        extra = Dot(LEFT*4,color=PURPLE,radius=.2)
        host.add(extra)
        self.wait(1)
        host.remove(extra)
        self.play(x.animate.set_value(-1),run_time=2)
        self.play(FadeOut(host),FadeOut(anchor),run_time=1)
        self.wait(1)
