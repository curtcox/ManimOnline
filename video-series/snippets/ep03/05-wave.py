from manim import *


class Wave(Scene):
    def construct(self):
        bars = VGroup(*[
            Rectangle(width=0.4, height=1, fill_opacity=1, stroke_width=0,
                      color=interpolate_color(BLUE, PURPLE, i / 15))
            for i in range(16)
        ]).arrange(RIGHT, buff=0.1)
        self.play(FadeIn(bars))
        self.play(LaggedStart(
            *[bar.animate(rate_func=there_and_back).stretch(3, 1) for bar in bars],
            lag_ratio=0.15, run_time=3))
        self.play(LaggedStart(*[FadeOut(bar, shift=DOWN) for bar in bars], lag_ratio=0.05))
