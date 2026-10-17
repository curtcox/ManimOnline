from manim import *


class TwoKindsOfRotation(Scene):
    def construct(self):
        left = Square(2, color=BLUE).shift(LEFT * 3)
        right = Square(2, color=YELLOW).shift(RIGHT * 3)
        self.add(Text(".animate.rotate", font_size=28).next_to(left, UP, buff=0.8))
        self.add(Text("Rotate", font_size=28).next_to(right, UP, buff=0.8))
        self.add(left, right)
        self.play(left.animate.rotate(PI / 2), Rotate(right, PI / 2), run_time=3)
        self.play(left.animate.rotate(PI), Rotate(right, PI), run_time=3)
        self.wait()
