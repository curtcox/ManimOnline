from manim import *


class LayoutScene(Scene):
    def construct(self):
        shapes = VGroup(
            Circle(radius=0.5, color=BLUE),
            Square(side_length=0.8, color=RED),
            Triangle(color=GREEN).scale(0.8),
        ).arrange(RIGHT, buff=0.6)
        marker = Dot(color=YELLOW).next_to(shapes, DOWN, buff=0.4)
        self.play(Create(shapes), FadeIn(marker), run_time=2)
        self.play(marker.animate.next_to(shapes, UP, buff=0.4), run_time=2)
        self.play(shapes.animate.arrange(DOWN, buff=0.35), run_time=2)
        self.play(marker.animate.next_to(shapes, RIGHT, buff=0.4))
        self.wait(1)
