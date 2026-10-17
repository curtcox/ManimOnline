from manim import *


class SolveForX(Scene):
    def construct(self):
        steps = [
            MathTex("2x", "+", "3", "=", "11"),
            MathTex("2x", "=", "11", "-", "3"),
            MathTex("2x", "=", "8"),
            MathTex("x", "=", r"\frac{8}{2}"),
            MathTex("x", "=", "4"),
        ]
        for step in steps:
            step.scale(1.5)
        current = steps[0]
        self.play(Write(current))
        for step in steps[1:]:
            self.wait(0.5)
            self.play(TransformMatchingTex(current, step))
            current = step
        self.play(Circumscribe(current))
        self.wait()
