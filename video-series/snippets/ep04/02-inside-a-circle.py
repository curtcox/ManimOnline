from manim import *


class InsideACircle(Scene):
    def construct(self):
        circle = Circle(radius=3, color=BLUE)
        self.play(Create(circle))
        points = circle.get_points()
        anchors = VGroup(*[Dot(points[i], color=YELLOW) for i in range(0, len(points), 4)])
        handles = VGroup()
        for i in range(0, len(points), 4):
            handles.add(
                Line(points[i], points[i + 1], color=GREY), Line(points[i + 3], points[i + 2], color=GREY),
                Dot(points[i + 1], radius=0.05, color=GREY), Dot(points[i + 2], radius=0.05, color=GREY))
        self.play(LaggedStart(*[FadeIn(d, scale=2) for d in anchors], lag_ratio=0.2))
        self.play(Create(handles), run_time=2)
        count = Text(f"{len(points) // 4} cubic curves, {len(points)} points", font_size=32).to_edge(DOWN)
        self.play(Write(count))
        self.wait()
