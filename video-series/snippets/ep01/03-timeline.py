from manim import *


class Timeline(Scene):
    def construct(self):
        dot = Dot(LEFT * 4, color=YELLOW)
        self.add(dot)                                        # 0 seconds: add is instant
        self.play(dot.animate.shift(RIGHT * 4))              # 1 second (the default)
        self.wait(1)                                         # 1 second of stillness
        self.play(dot.animate.shift(RIGHT * 4), run_time=3)  # 3 slower seconds
        self.wait(0.5)
        # Total: 5.5 seconds. Change the numbers and watch the timeline change.
