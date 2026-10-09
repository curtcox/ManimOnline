"""ManimBanner, SampleSpace divisions and Community utility helpers."""
from manim import *


class BannerScene(Scene):
    def construct(self):
        banner = ManimBanner().scale(0.6).shift(UP * 1.5)
        self.play(banner.create())
        self.play(banner.expand())

        space = SampleSpace(width=4, height=2.4).shift(DOWN * 1.8 + LEFT * 3)
        space.divide_horizontally([0.3])
        braces = space.get_side_braces_and_labels([r"P(A)", r"P(\bar A)"])
        self.play(FadeIn(space), FadeIn(braces))

        # Utilities: regular vertices, rotate_vector and a clockwise path.
        corners, _ = regular_vertices(5, radius=1.1)
        star = Polygon(*corners, color=TEAL).shift(DOWN * 1.8 + RIGHT * 3.5)
        pointer = Dot(star.get_center() + rotate_vector(RIGHT * 1.6, PI / 5), color=YELLOW)
        self.play(Create(star), FadeIn(pointer))
        self.play(Transform(pointer, pointer.copy().shift(LEFT * 2.2), path_func=clockwise_path()))
        self.play(TransformAnimations(Rotate(star, PI), FadeIn(Circle(radius=1.1, color=RED).move_to(star))))
        self.wait()
