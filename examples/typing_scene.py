"""Typing with a cursor, animated boundaries, re-timed motion and implicit curves."""
from manim import *


class TypingScene(Scene):
    def construct(self):
        text = Text("Hello, Manim!", font="Monospace", font_size=40).to_edge(UP)
        cursor = Rectangle(height=.6, width=.25, fill_opacity=1, stroke_width=0, color=GREY_A).move_to(text[0])
        self.play(TypeWithCursor(text, cursor))
        self.play(Blink(cursor, blinks=2, time_on=.2, time_off=.2))
        heart = ImplicitFunction(lambda x, y: (x * x + y * y - 1) ** 3 - x * x * y ** 3,
                                 x_range=[-1.5, 1.5], y_range=[-1.3, 1.6], color=RED).scale(1.3).shift(LEFT * 3)
        boundary = AnimatedBoundary(Square(2.6).move_to(heart), cycle_rate=1)
        self.play(Create(heart))
        self.add(boundary)
        dot = Dot(RIGHT * 1.5 + DOWN, color=YELLOW)
        self.add(dot)
        self.play(ChangeSpeed(dot.animate.shift(RIGHT * 4), {0.4: .2, 0.8: 3}, rate_func=linear), run_time=2)
        room = LabeledPolygram([(1, 1.5, 0), (5, 1.5, 0), (5, 0, 0), (3, 0, 0), (3, -.8, 0), (1, -.8, 0)],
                               label="Room", color=TEAL)
        self.play(FadeIn(room))
        self.play(ShowPassingFlashWithThinningStrokeWidth(heart.copy().set_color(YELLOW), n_segments=8, time_width=.4))
        self.play(UntypeWithCursor(text, cursor))
        self.wait(.5)
