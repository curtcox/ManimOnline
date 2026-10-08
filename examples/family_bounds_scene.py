"""Family framing includes distant children while attachment preserves the host."""
from manim import *


class FamilyBoundsScene(MovingCameraScene):
    def construct(self):
        host = Rectangle(width=2,height=1,color=BLUE,fill_opacity=.15)
        host.rotate(PI/6).scale(.7).shift(LEFT*.5)
        host.add(Circle(radius=.6,color=GREEN).shift(RIGHT*4))
        anchor = Dot(host.get_start(),color=RED)
        bounds = always_redraw(lambda:Rectangle(width=host.get_width(),
                 height=host.get_height(),color=YELLOW,stroke_opacity=.5)
                 .move_to(host.get_center()))
        self.play(Create(host),FadeIn(bounds),FadeIn(anchor),run_time=2)
        self.play(self.camera.auto_zoom(host,margin=1),run_time=2)
        far = Circle(radius=.5,color=PURPLE).shift(LEFT*4)
        host.add(far)
        self.wait(1)
        self.play(self.camera.auto_zoom(host,margin=1),run_time=2)
        host.remove(far)
        self.wait(1)
        self.play(FadeOut(host),FadeOut(bounds),FadeOut(anchor),run_time=1)
        self.wait(1)
