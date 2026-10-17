from manim import *


class Intro(Scene):
    def construct(self):
        self.play(Write(Text("Scene one: Intro")))
        self.wait()


class Middle(Scene):
    def construct(self):
        shape = Square(color=BLUE)
        self.play(Create(shape))
        self.play(shape.animate.rotate(PI / 4).set_fill(BLUE, opacity=0.5))
        self.wait()


class Outro(Scene):
    def construct(self):
        self.play(FadeIn(Text("Scene three: Outro", color=YELLOW), shift=UP))
        self.wait()
