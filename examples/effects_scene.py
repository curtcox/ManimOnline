"""Hulls, cutouts, tangent arcs, arc braces and attention effects."""
from manim import *


class EffectsScene(Scene):
    def construct(self):
        title = Text("Shapes and effects", font_size=36).to_edge(UP)
        self.play(AddTextWordByWord(title))
        points = [LEFT * 2 + DOWN, RIGHT * 2 + DOWN * 1.5, RIGHT * 2.5 + UP, UP * 1.5, LEFT * 2.5 + UP * .5, ORIGIN]
        dots = VGroup(*(Dot(p) for p in points))
        hull = ConvexHull(*points, color=TEAL, fill_opacity=.3)
        shapes = VDict({"hull": VGroup(dots, hull).scale(.6).shift(LEFT * 4)})
        shapes["cutout"] = Cutout(Square(2.5), Circle(.6).shift(LEFT * .5), Square(.6).shift(RIGHT * .6 + UP * .4),
                                  fill_opacity=.8, color=BLUE, stroke_width=2)
        l1, l2 = Line(LEFT * 1.5, RIGHT * 1.5), Line(DOWN * 1.2 + LEFT * .8, UP * 1.2 + RIGHT * .8)
        arc = TangentialArc(l1, l2, radius=.5, color=YELLOW)
        shapes["corner"] = VGroup(l1, l2, arc).shift(RIGHT * 4)
        self.play(LaggedStartMap(FadeIn, VGroup(*shapes.get_all_submobjects()), shift=UP * .3), run_time=2)
        self.play(Broadcast(Circle(radius=1.5, color=YELLOW), focal_point=shapes["corner"].get_center(), n_mobs=3))
        self.play(Blink(shapes["cutout"], blinks=2, time_on=.25, time_off=.25))
        ring = Arc(radius=1.5, start_angle=PI / 4, angle=PI / 2).move_to(DOWN * 2.6 + LEFT * 3)
        brace = ArcBrace(ring, color=GOLD)
        self.play(Create(ring), FadeIn(brace))
        stars = VGroup(*(Star(outer_radius=.3, color=c, fill_opacity=.8) for c in (RED, GREEN, BLUE, PURPLE)))
        stars.arrange(RIGHT, buff=.4).to_edge(DOWN).shift(RIGHT * 2.5)
        self.play(SpiralIn(stars), run_time=2)
        self.wait(.5)
