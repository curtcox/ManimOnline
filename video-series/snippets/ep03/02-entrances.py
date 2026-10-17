from manim import *


class EntrancesAndEmphasis(Scene):
    def construct(self):
        title = Text("Hello, Manim").shift(UP * 2)
        circle = Circle(color=BLUE).shift(DOWN * 1.5)
        star = Star(color=YELLOW, fill_opacity=1).scale(0.6).shift(RIGHT * 4 + DOWN * 1.5)
        square = Square(color=GREEN).scale(0.6).shift(LEFT * 4 + DOWN * 1.5)
        self.play(Write(title))
        self.play(Create(circle))
        self.play(GrowFromCenter(star))
        self.play(FadeIn(square, shift=UP))
        self.play(Indicate(title))
        self.play(Circumscribe(circle))
        self.play(Rotate(star, PI))
        self.play(FadeOut(title, circle, star, square, shift=DOWN))
