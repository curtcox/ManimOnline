"""Regular polygons, stars and polygrams with surrounding shape matchers."""
from manim import *


class PolygramScene(Scene):
    def construct(self):
        shapes = VGroup(
            RegularPolygon(5, color=TEAL, fill_opacity=.4),
            Star(outer_radius=1.1, color=GOLD, fill_opacity=.4),
            RegularPolygram(6, radius=1.1, color=PURPLE_B),
            Triangle(color=MAROON_B).round_corners(.25),
        ).arrange(buff=.6).shift(UP * .5)
        self.play(LaggedStart(*(Create(s) for s in shapes), lag_ratio=.3), run_time=2)
        shapes.scale(.8).to_edge(UP)
        box = SurroundingRectangle(shapes[1], corner_radius=.15)
        line = Underline(shapes[0], color=TEAL)
        cross = Cross(shapes[3], stroke_width=4)
        self.play(Create(box), Create(line), run_time=1)
        self.play(box.animate.become(SurroundingRectangle(shapes[2], corner_radius=.15)), run_time=1)
        self.play(Create(cross), run_time=1)
        backdrop = BackgroundRectangle(shapes, color=GREY_E, fill_opacity=1, buff=MED_SMALL_BUFF)
        self.play(FadeIn(backdrop), run_time=1)
        self.bring_to_back(backdrop)
        self.play(Transform(shapes[1], RegularPolygram(5, radius=1.1, color=GOLD).move_to(shapes[1])), run_time=2)
        self.play(*(FadeOut(m) for m in (*shapes, box, line, cross, backdrop)), run_time=1)
        self.wait(1)
