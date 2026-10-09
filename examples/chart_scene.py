"""Bar charts with animated values, and polar coordinates with a rotating vector."""
from manim import *


class ChartScene(Scene):
    def construct(self):
        chart = BarChart([3, 5, 2, 4], bar_names=["A", "B", "C", "D"], y_range=[0, 6, 2],
                         y_length=4, x_length=5).to_edge(LEFT)
        labels = chart.get_bar_labels(font_size=24)
        self.play(Create(chart), run_time=2)
        self.play(FadeIn(labels), run_time=.5)
        self.play(FadeOut(labels), chart.animate.change_bar_values([5, 2, 4, 1]), run_time=1.5)
        plane = PolarPlane(size=4, azimuth_units="PI radians").add_coordinates().to_edge(RIGHT)
        angle = ValueTracker(PI / 6)
        vector = always_redraw(lambda: Arrow(plane.get_origin(), plane.pr2pt(1.5, angle.get_value()),
                                             buff=0, color=YELLOW))
        self.play(Create(plane), run_time=2)
        self.add(vector)
        self.play(angle.animate.set_value(PI * 4 / 3), run_time=2)
        self.wait(.5)
