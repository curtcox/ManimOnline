"""Use a square canvas and preserve changing backgrounds in exported frames."""
from manim import *

config.pixel_width = 600
config.pixel_height = 600
config.frame_height = 8
config.background_color = WHITE


class CameraScene(Scene):
    def construct(self):
        title = Text("A square canvas", color=BLACK, font_size=30).shift(UP * 2.7)
        shapes = VGroup(Circle(color=BLUE, fill_opacity=.25),
                        Square(color=RED, fill_opacity=.15)).arrange(RIGHT, buff=.6).scale(.7)
        self.play(FadeIn(title), Create(shapes), run_time=2)
        self.camera.background_color = "#E8EEF7"
        self.play(shapes.animate.rotate(PI / 2), run_time=2)
        self.wait(1)
