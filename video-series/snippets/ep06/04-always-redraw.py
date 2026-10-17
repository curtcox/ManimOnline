import math

from manim import *


class AlwaysRedraw(Scene):
    def construct(self):
        radius = 2.5
        angle = ValueTracker(0.3)

        def tip():
            a = angle.get_value()
            return radius * (math.cos(a) * RIGHT + math.sin(a) * UP)

        def foot():
            return radius * math.cos(angle.get_value()) * RIGHT

        self.add(Circle(radius=radius, color=GREY), Line(LEFT * 3, RIGHT * 3, color=GREY))
        triangle = always_redraw(lambda: Polygon(ORIGIN, foot(), tip(), color=YELLOW, fill_opacity=0.3))
        cos_label = always_redraw(lambda: MathTex(r"\cos\theta", color=BLUE).next_to(Line(ORIGIN, foot()), DOWN))
        sin_label = always_redraw(lambda: MathTex(r"\sin\theta", color=GREEN).next_to(Line(foot(), tip()), RIGHT))
        self.add(triangle, cos_label, sin_label)
        self.play(angle.animate.set_value(1.3), run_time=3)
        self.play(angle.animate.set_value(0.6), run_time=2)
        self.wait()
