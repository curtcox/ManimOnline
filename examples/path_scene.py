from manim import *


class PathScene(Scene):
    def construct(self):
        circle = Circle(radius=1.2, color=BLUE).scale(0.8).shift(LEFT * 2)
        polygon = Polygon((0, 0), (2, 0), (2, 1), (0, 1), color=GREEN)
        polygon.rotate(PI / 6).shift(RIGHT * 2)
        line = Line(LEFT * 3, RIGHT * 3, color=GRAY).rotate(-PI / 12).shift(DOWN * 2)
        dot = Dot(radius=0.15, color=YELLOW)
        square = Square(side_length=0.3, color=RED, fill_opacity=1).rotate(PI / 4)
        self.play(Create(circle), Create(polygon), Create(line))
        self.play(LaggedStart(
            MoveAlongPath(dot, circle, run_time=4, rate_func=linear),
            MoveAlongPath(square, polygon, run_time=4, rate_func=linear),
            lag_ratio=0.25,
        ))
        self.play(MoveAlongPath(dot, line), square.animate.shift(UP), run_time=2, rate_func=linear)
        self.wait(1)
