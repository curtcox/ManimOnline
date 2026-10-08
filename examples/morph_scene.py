"""Morph unequal path counts, restore a curve, and close an outline."""
from manim import *


class MorphScene(Scene):
    def construct(self):
        path = CubicBezier((-3,0,0), (-1,3,0), (1,-3,0), (3,0,0), color=BLUE)
        path.scale(0.8).rotate(PI / 12).save_state()
        corners = VMobject(color=GREEN).set_points_as_corners([(-3,-1,0), (-1,1,0), (1,-1,0), (3,1,0)])
        title = Text("Morph aligned paths", font_size=30).shift(UP * 2.5)
        self.play(Create(path), FadeIn(title), run_time=2)
        self.play(Transform(path, corners), run_time=2, rate_func=linear)
        self.play(Restore(path), run_time=2, rate_func=linear)
        polygon = Polygon((-3,-1,0), (-1,1,0), (1,1,0), (3,-1,0), color=PURPLE, fill_opacity=0.2)
        self.play(Transform(path, polygon), run_time=3, rate_func=linear)
        self.wait(1)
