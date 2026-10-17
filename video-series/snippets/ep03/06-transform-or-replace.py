from manim import *


class TransformOrReplace(Scene):
    def construct(self):
        a, b = Square(color=BLUE), Circle(color=YELLOW)
        c, d = Square(color=BLUE), Circle(color=YELLOW)
        VGroup(a, b).shift(LEFT * 3)
        VGroup(c, d).shift(RIGHT * 3)
        self.add(Text("Transform(a, b)", font_size=28).shift(LEFT * 3 + UP * 2.5))
        self.add(Text("ReplacementTransform(c, d)", font_size=28).shift(RIGHT * 3 + UP * 2.5))
        self.play(Create(a), Create(c))
        self.play(Transform(a, b), ReplacementTransform(c, d))
        # On the left, the circle on screen is still named a. On the right, it is d.
        self.play(a.animate.shift(DOWN * 1.5), d.animate.shift(DOWN * 1.5))
        self.wait()
