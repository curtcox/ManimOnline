from manim import *


class RateFunctionRace(Scene):
    def construct(self):
        racers = [
            ("linear", linear),
            ("smooth", smooth),
            ("rush_into", rush_into),
            ("rush_from", rush_from),
            ("there_and_back", there_and_back),
        ]
        animations = []
        for row, (name, rate) in enumerate(racers):
            y = 2 - row
            self.add(Text(name, font_size=24).move_to(LEFT * 5 + UP * y))
            self.add(Line(LEFT * 3 + UP * y, RIGHT * 4 + UP * y, stroke_opacity=0.3))
            dot = Dot(LEFT * 3 + UP * y, color=YELLOW)
            self.add(dot)
            animations.append(dot.animate(rate_func=rate).shift(RIGHT * 7))
        self.play(*animations, run_time=3)
        self.wait()
