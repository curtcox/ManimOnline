from manim import *


class ArcScene(Scene):
    def construct(self):
        upper = Arc(radius=1.4, start_angle=0, angle=PI, arc_center=LEFT * 2, color=BLUE)
        clockwise = Arc(radius=1.4, start_angle=PI, angle=-PI, arc_center=RIGHT * 2, color=GREEN)
        clockwise.scale(0.8).rotate(PI / 6)
        yellow = Dot(radius=0.13, color=YELLOW)
        red = Dot(radius=0.13, color=RED)
        self.play(Create(upper), Create(clockwise), run_time=2)
        self.play(
            MoveAlongPath(yellow, upper),
            MoveAlongPath(red, clockwise),
            run_time=4,
            rate_func=linear,
        )
        self.wait(1)
