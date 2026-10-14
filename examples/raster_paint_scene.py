"""Screen-position raster coloring of moving outlines and flowing streams."""
from manim import *


class RasterPaintScene(Scene):
    def construct(self):
        flow = lambda p: (-p[1], p[0] / 2, 0)
        field = VectorField(flow, min_color_scheme_value=0, max_color_scheme_value=4,
                            colors=[BLUE_E, GREEN, YELLOW, RED])
        image = field.get_colored_background_image(sampling_rate=10)
        ring = Circle(radius=1.4, fill_opacity=.4, stroke_width=8).shift(LEFT*3)
        ring.color_using_background_image(image)
        streams = StreamLines(flow, x_range=[-4,4,2], y_range=[-2,2,2],
                              noise_factor=0, virtual_time=1.5, stroke_width=5,
                              min_color_scheme_value=0, max_color_scheme_value=4,
                              colors=[BLUE_E, GREEN, YELLOW, RED])
        self.play(Create(ring), streams.create(), run_time=2)
        self.add(streams)
        streams.start_animation(warm_up=False, flow_speed=1.5)
        self.play(ring.animate.shift(RIGHT*6), run_time=3)
        self.play(streams.end_animation(), run_time=1)
        self.play(FadeOut(ring), FadeOut(streams), run_time=1)
        self.wait(1)
