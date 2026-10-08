"""Compare a complete point trail with a short dissipating trail."""
from manim import *


class TraceScene(Scene):
    def construct(self):
        full_dot = Dot(LEFT * 3 + RIGHT, color=BLUE)
        tail_dot = Dot(RIGHT * 3 + RIGHT, color=YELLOW)
        full = TracedPath(full_dot.get_center, stroke_color=BLUE, stroke_width=4)
        tail = TracedPath(tail_dot.get_center, dissipating_time=1,
                          stroke_color=YELLOW, stroke_width=4)
        self.add(full_dot, tail_dot, full, tail)
        self.play(Rotate(full_dot, TAU, about_point=LEFT * 3),
                  Rotate(tail_dot, TAU, about_point=RIGHT * 3),
                  run_time=4, rate_func=linear)
        full.clear_updaters()
        self.wait(2)
        self.play(FadeOut(full_dot), FadeOut(tail_dot), FadeOut(full), FadeOut(tail))
