from manim import *


class Groups(Scene):
    def construct(self):
        dots = VGroup(*[
            Dot(radius=0.15, color=interpolate_color(BLUE, YELLOW, i / 11)) for i in range(12)
        ])
        self.play(FadeIn(dots))                               # all twelve start at the origin
        self.play(dots.animate.arrange(RIGHT, buff=0.4))
        self.play(dots.animate.arrange_in_grid(rows=3, buff=0.5))
        self.play(dots.animate.scale(1.5).rotate(PI / 6))     # the group moves as one
        self.play(dots.animate.arrange(DOWN, buff=0.2).to_edge(LEFT))
        self.wait()
