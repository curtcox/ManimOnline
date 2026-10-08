"""Select, reorder, and edit children while keeping a scene-added group intact."""
from manim import *


class GroupFamilyScene(Scene):
    def construct(self):
        title = Text("Build and edit a group", font_size=30).shift(UP * 2.5)
        row = VGroup(Circle(radius=.6, color=BLUE),
                     Square(side_length=1.2, color=RED),
                     Triangle(color=GREEN).scale(2)).arrange(RIGHT, buff=.7)
        self.add(title, row)
        self.wait(1)
        row[::2].set_color(YELLOW)
        self.wait(1)
        middle = row[1]
        row.remove(middle)
        self.wait(1)
        row.add_to_back(middle)
        self.play(row.animate.rotate(PI / 2), run_time=2)
        self.play(FadeOut(row), run_time=1)
        self.wait(1)
