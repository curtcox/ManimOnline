"""A sampled vector-field color map, real arrows and an advected marker."""
from manim import *


class FieldImageScene(Scene):
    def construct(self):
        flow = lambda p: (-p[1], p[0] / 2, 0)
        field = VectorField(flow, min_color_scheme_value=0, max_color_scheme_value=4,
                            colors=[BLUE_E, GREEN, YELLOW, RED])
        background = ImageMobject(field.get_colored_background_image(sampling_rate=10))
        background.height = config.frame_height
        background.set_opacity(.7)
        arrows = ArrowVectorField(flow, color=WHITE, x_range=[-5,5,1.5], y_range=[-3,3,1.5])
        marker = Dot(LEFT*3+DOWN, color=WHITE, radius=.14)
        self.play(FadeIn(background), Create(arrows), FadeIn(marker), run_time=2)
        marker.add_updater(field.get_nudge_updater(speed=.5))
        self.wait(4)
        marker.clear_updaters()
        self.play(FadeOut(arrows), FadeOut(marker), FadeOut(background), run_time=1)
        self.wait(1)
