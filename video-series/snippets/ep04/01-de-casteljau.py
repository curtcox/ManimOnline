from manim import *


class DeCasteljau(Scene):
    def construct(self):
        p = [LEFT * 5 + DOWN * 2, LEFT * 2 + UP * 3, RIGHT * 2 + UP * 3, RIGHT * 5 + DOWN * 2]
        t = ValueTracker(0)
        self.add(*[Line(p[i], p[i + 1], color=GREY) for i in range(3)], *[Dot(q, color=GREY) for q in p])

        def layers():
            a = t.get_value()
            first = [interpolate(p[i], p[i + 1], a) for i in range(3)]
            second = [interpolate(first[i], first[i + 1], a) for i in range(2)]
            return VGroup(
                Line(first[0], first[1], color=BLUE), Line(first[1], first[2], color=BLUE),
                *[Dot(q, radius=0.06, color=BLUE) for q in first],
                Line(second[0], second[1], color=GREEN),
                *[Dot(q, radius=0.06, color=GREEN) for q in second],
            )

        def point_on_curve():
            a = t.get_value()
            first = [interpolate(p[i], p[i + 1], a) for i in range(3)]
            second = [interpolate(first[i], first[i + 1], a) for i in range(2)]
            return interpolate(second[0], second[1], a)

        curve = TracedPath(point_on_curve, stroke_color=YELLOW, stroke_width=6)
        self.add(curve, always_redraw(layers), always_redraw(lambda: Dot(point_on_curve(), color=YELLOW)))
        self.play(t.animate.set_value(1), run_time=6, rate_func=linear)
        self.wait()
