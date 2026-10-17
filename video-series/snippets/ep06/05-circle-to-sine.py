import math

from manim import *


class CircleToSine(Scene):
    def construct(self):
        t = ValueTracker(0)
        circle = Circle(radius=1.5, color=BLUE).shift(LEFT * 4.5)
        self.add(circle, Line(LEFT * 2.5, RIGHT * 6.5, color=GREY))

        def on_circle():
            a = t.get_value()
            return circle.get_center() + 1.5 * (math.cos(a) * RIGHT + math.sin(a) * UP)

        def on_wave():
            a = t.get_value()
            return LEFT * 2.5 + RIGHT * a * 9 / TAU + UP * 1.5 * math.sin(a)

        self.add(
            always_redraw(lambda: Line(circle.get_center(), on_circle())),
            always_redraw(lambda: DashedLine(on_circle(), on_wave(), color=GREY)),
            TracedPath(on_wave, stroke_color=YELLOW, stroke_width=4),
            always_redraw(lambda: Dot(on_circle(), color=YELLOW)),
            always_redraw(lambda: Dot(on_wave(), color=YELLOW)),
        )
        self.play(t.animate.set_value(TAU), run_time=6, rate_func=linear)
        self.wait()
