"""Trace, follow, and deform a connected path built from corners."""
from manim import *


class CornerPathScene(Scene):
    def construct(self):
        path = VMobject(color=BLUE).set_points_as_corners([
            (-3, -1, 0), (-1, 1, 0), (1, -1, 0), (3, 1, 0)
        ]).scale(0.8).rotate(PI / 12).shift(DOWN * 0.3)
        marker = Dot(path.get_start(), color=YELLOW)
        title = Text("Connected corner path", font_size=30).shift(UP * 2.5)
        self.play(Create(path), FadeIn(marker), FadeIn(title), run_time=2)
        self.play(MoveAlongPath(marker, path), run_time=3, rate_func=linear)
        target = path.copy().set_points_as_corners([
            (-3, 0, 0), (-1, 1.5, 0), (1, 0.5, 0), (3, -1, 0)
        ]).set_color(GREEN)
        self.play(Transform(path, target), run_time=2)
        self.play(Uncreate(path), FadeOut(marker))
        self.wait(1)
