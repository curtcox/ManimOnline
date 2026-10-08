from manim import *


class IndicateScene(Scene):
    def construct(self):
        square = Square(fill_color=BLUE, fill_opacity=0.5, stroke_color=PURPLE)
        square.rotate(PI / 6).shift(LEFT * 2.5)
        group = VGroup(Circle(radius=0.6, color=GREEN),
                       Triangle(color=RED)).arrange(RIGHT, buff=0.4).shift(RIGHT * 2)
        title = Text("Highlight and return", font_size=32).shift(UP * 2.5)
        self.add(square, group, title)
        self.play(Indicate(square, scale_factor=1.5),
                  Indicate(group, scale_factor=1.4, color=ORANGE), run_time=4)
        self.wait(1)
        self.play(LaggedStart(Indicate(square), Indicate(group),
                             lag_ratio=0.5), run_time=3)
        self.wait(1)
