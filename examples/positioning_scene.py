"""Place shapes against frame edges, align them and color them by gradient."""
from manim import *


class PositioningScene(Scene):
    def construct(self):
        row = VGroup(*(Square(side_length=.8, fill_opacity=.6) for _ in range(5))).arrange(buff=SMALL_BUFF)
        row.set_color_by_gradient(BLUE_E, TEAL, GOLD_A)
        row.to_edge(UP, buff=MED_LARGE_BUFF)
        marker = Triangle(color=MAROON).scale(.8).to_corner(DL)
        arrow = Arrow(LEFT, RIGHT, buff=0, color=GREY_B).to_edge(RIGHT)
        self.play(Create(row), Create(marker), Create(arrow), run_time=2)
        self.play(marker.animate.align_to(row, LEFT).set_y(0), run_time=1)
        self.play(arrow.animate.match_width(row).next_to(marker, RIGHT).flip(), run_time=2)
        self.play(row.animate.to_corner(DR, buff=SMALL_BUFF).fade(.5), run_time=2)
        self.play(Rotate(marker, PI, about_edge=DR), run_time=1)
        self.play(marker.animate.center(), row.animate.set_x(0), run_time=1)
        self.play(FadeOut(row), FadeOut(marker), FadeOut(arrow), run_time=1)
        self.wait(1)
