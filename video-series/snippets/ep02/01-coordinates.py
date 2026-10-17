from manim import *


class Coordinates(Scene):
    def construct(self):
        self.add(NumberPlane())
        places = [
            (ORIGIN, "ORIGIN"),
            (UP * 2, "UP * 2"),
            (RIGHT * 3 + DOWN, "RIGHT * 3 + DOWN"),
            (LEFT * 5 + UP * 3, "LEFT * 5 + UP * 3"),
        ]
        for point, name in places:
            dot = Dot(point, color=YELLOW)
            label = Text(name, font_size=24).next_to(dot, UR, buff=0.1)
            label.add_background_rectangle()
            self.play(FadeIn(dot, scale=3), Write(label), run_time=0.8)
        self.wait()
