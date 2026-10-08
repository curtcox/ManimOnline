from manim import *


class GrowthScene(Scene):
    def construct(self):
        origin = LEFT * 4 + DOWN
        marker = Dot(origin, color=YELLOW)
        square = Square(color=BLUE, fill_opacity=0.4).rotate(PI / 6).shift(LEFT * 2)
        group = VGroup(Circle(radius=0.6, color=GREEN),
                       Triangle(color=RED)).arrange(RIGHT, buff=0.4).shift(RIGHT * 2)
        self.add(marker)
        self.play(GrowFromPoint(square, origin), GrowFromCenter(group),
                  run_time=3, rate_func=linear)
        self.wait(1)
        self.play(LaggedStart(ShrinkToCenter(square, remover=True),
                             ShrinkToCenter(group, remover=True),
                             lag_ratio=0.5), run_time=3)
        self.wait(1)
