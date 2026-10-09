"""Inline SVG drawings and pixel-array images (no files are needed in the browser)."""
from manim import *

LOGO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 100">
  <circle cx="35" cy="50" r="30" fill="#58C4DD"/>
  <rect x="55" y="20" width="60" height="60" rx="8" fill="#FC6255"/>
  <path d="M 20 90 Q 60 60 100 90" fill="none" stroke="#FFFF00" stroke-width="4"/>
  <polygon points="60,5 70,25 50,25" fill="#83C167"/>
</svg>"""


class SvgImageScene(Scene):
    def construct(self):
        logo = SVGMobject(LOGO, height=2.5).to_edge(LEFT, buff=1)
        self.play(LaggedStart(*(DrawBorderThenFill(part) for part in logo), lag_ratio=.3), run_time=2)
        # A 48 x 48 RGB gradient built from plain lists.
        pixels = [[[int(255 * x / 47), int(255 * y / 47), 160] for x in range(48)] for y in range(48)]
        # Height = rows / scale_to_resolution * frame height: 48 rows -> 2 units.
        image = ImageMobject(pixels, scale_to_resolution=192).to_edge(RIGHT, buff=1)
        checker = ImageMobject([[255 * ((x + y) % 2) for x in range(8)] for y in range(8)], scale_to_resolution=64)
        checker.set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"]).next_to(image, DOWN)
        self.play(FadeIn(image, shift=LEFT), FadeIn(checker))
        self.play(image.animate.rotate(PI / 6).scale(.8), logo.animate.scale(.8))
        self.play(Transform(logo[1], Circle(radius=.6, color=RED, fill_opacity=1).move_to(logo[1])))
        self.wait(.5)
