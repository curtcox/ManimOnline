"""Morph unequal nested families, restore the checkpoint, and erase the group."""
from manim import *


class GroupMorphScene(Scene):
    def construct(self):
        title = Text("Morph nested groups", font_size=30).shift(UP * 2.5)
        shapes = VGroup(
            Circle(radius=.65, color=BLUE, fill_opacity=.2).shift(LEFT * 1.5),
            VGroup(Square(side_length=1.1, color=YELLOW).shift(RIGHT * 1.5))
        ).rotate(PI / 12).save_state()
        target = VGroup(
            Square(side_length=1.2, color=RED).shift(LEFT * 2),
            Triangle(color=GREEN).scale(2),
            VGroup(Circle(radius=.65, color=PURPLE).shift(RIGHT * 2),
                   Line((1.4,-1,0), (2.6,-1,0), color=ORANGE))
        ).rotate(-PI / 12)
        self.play(FadeIn(title), Create(shapes), run_time=2)
        self.play(Transform(shapes, target), run_time=2)
        self.wait(1)
        self.play(Restore(shapes), run_time=3)
        self.wait(1)
        self.play(Uncreate(shapes), run_time=1)
        self.wait(1)
