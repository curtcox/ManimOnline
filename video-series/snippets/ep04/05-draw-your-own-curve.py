from manim import *


class DrawYourOwnCurve(Scene):
    def construct(self):
        start, handle1, handle2, end = LEFT * 4 + UP, LEFT * 2 + UP * 4, RIGHT * 2 + DOWN * 2, RIGHT * 4 + UP
        guides = VGroup(Line(start, handle1), Line(end, handle2), Dot(handle1), Dot(handle2)).set_color(GREY)
        curve = CubicBezier(start, handle1, handle2, end, color=YELLOW, stroke_width=8)
        self.play(Create(guides))
        self.play(Create(curve), run_time=3)

        # Smooth curves through many points are chains of cubic pieces.
        path = VMobject(color=BLUE, stroke_width=6)
        path.set_points_smoothly([LEFT * 5 + DOWN * 2, LEFT * 2.5 + DOWN, DOWN * 3, RIGHT * 2.5 + DOWN, RIGHT * 5 + DOWN * 2])
        self.play(Create(path), run_time=2)
        self.wait()
