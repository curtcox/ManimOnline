"""Keep a grouped overlay in front, release it, and remove it cleanly."""
from manim import *


class ForegroundScene(Scene):
    def construct(self):
        badge = VGroup(
            Circle(radius=0.7, color=YELLOW, fill_opacity=1),
            Text("Overlay", color=BLACK, font_size=20),
        )
        blue = Square(side_length=2.8, color=BLUE, fill_opacity=1)
        red = Square(side_length=2.2, color=RED, fill_opacity=1)
        title = Text("Foreground overlay", font_size=30).shift(UP * 2.5).set_z_index(10)
        self.add(title)
        self.add_foreground_mobject(badge)
        self.play(Create(blue), run_time=2)
        self.wait(1)
        self.remove_foreground_mobject(badge)
        self.play(Create(red))
        self.add_foreground_mobject(badge)
        self.play(Rotate(badge, PI / 6))
        self.play(FadeOut(badge))
        self.clear()
        self.wait(1)
        self.add(title)
        self.wait(1)
