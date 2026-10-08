from manim import *


class StaggeredScene(Scene):
    def construct(self):
        dots = VGroup(
            Dot(LEFT * 2, radius=0.25, color=BLUE),
            Dot(radius=0.25, color=RED),
            Dot(RIGHT * 2, radius=0.25, color=GREEN),
        )
        self.play(LaggedStart(
            *[FadeIn(dot, rate_func=linear) for dot in dots],
            lag_ratio=0.5,
            run_time=4,
        ))
        self.play(AnimationGroup(
            *[dot.animate.shift(UP) for dot in dots],
            lag_ratio=0.25,
            run_time=3,
        ))
        self.play(LaggedStart(
            *[FadeOut(dot) for dot in dots],
            lag_ratio=0.5,
            run_time=2,
        ))
        self.wait(1)
