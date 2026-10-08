from manim import *


class SuccessionScene(Scene):
    def construct(self):
        title = Text("Create, rotate twice, move, replace, remove", font_size=26).shift(UP * 3)
        shape = Square(color=BLUE).shift(LEFT * 2)
        target = Circle(color=ORANGE).shift(RIGHT * 2)
        self.add(title)
        self.play(Succession(
            Create(shape),
            Rotate(shape, PI / 2, run_time=2, rate_func=linear),
            Rotate(shape, PI / 2, run_time=2, rate_func=linear),
            shape.animate.shift(UP),
            ReplacementTransform(shape, target),
            Indicate(target),
            FadeOut(target),
        ))
        self.wait(1)
