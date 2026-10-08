from manim import *


class CopyScene(Scene):
    def construct(self):
        source = Square(fill_color=BLUE, fill_opacity=0.5, stroke_color=PURPLE)
        source.shift(LEFT * 3)
        target = source.copy().set_color(GREEN).shift(RIGHT * 6)
        title = Text("Copy, transform, keep the original", font_size=28).shift(UP * 2.5)
        self.add(source, title)
        self.play(TransformFromCopy(source, target), run_time=4, rate_func=linear)
        self.wait(1)
        circle = Circle(color=ORANGE, fill_opacity=0.4).shift(DOWN * 1.5)
        self.play(TransformFromCopy(target, circle), run_time=2)
        self.play(Indicate(source), Indicate(target), Indicate(circle), run_time=2)
        self.play(FadeOut(target), FadeOut(circle))
        self.wait(1)
