"""Union, intersection, difference and exclusion of overlapping outlines."""
from manim import *


class BooleanScene(Scene):
    def construct(self):
        circle = Circle(radius=1, color=BLUE, fill_opacity=.4).shift(LEFT * .6)
        square = Square(1.8, color=RED, fill_opacity=.4).shift(RIGHT * .6).rotate(PI / 8)
        pair = VGroup(circle, square).shift(UP * 1.6)
        self.play(Create(circle), Create(square))
        operations = VGroup(
            Union(circle, square, color=TEAL, fill_opacity=.6),
            Intersection(circle, square, color=YELLOW, fill_opacity=.6),
            Difference(circle, square, color=PURPLE, fill_opacity=.6),
            Exclusion(circle, square, color=GREEN, fill_opacity=.6),
        ).scale(.6)
        names = VGroup(*(Text(n, font_size=22) for n in ("Union", "Intersection", "Difference", "Exclusion")))
        # Arrange each result above its name so labels never collide.
        columns = VGroup(*(VGroup(op, name).arrange(DOWN) for op, name in zip(operations, names)))
        columns.arrange(RIGHT, buff=.5, aligned_edge=DOWN).shift(DOWN * 1.6)
        self.play(LaggedStart(*(TransformFromCopy(pair, op) for op in operations), lag_ratio=.3), run_time=3)
        self.play(FadeIn(names))
        holed = Difference(Square(2.4), Circle(.6), color=GOLD, fill_opacity=.8).move_to(pair)
        self.play(FadeOut(circle), FadeOut(square), FadeIn(holed))
        self.play(Transform(holed, Union(Circle(1), Square(1.4).shift(RIGHT), color=GOLD, fill_opacity=.8).move_to(holed)))
        self.wait(.5)
