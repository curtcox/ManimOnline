"""A surrounding circle follows a rectangle's transformed bounds."""
from manim import *


class SurroundScene(Scene):
    def construct(self):
        target = Rectangle(width=3, height=1.5, color=BLUE).shift(LEFT)
        ring = Circle(color=YELLOW).surround(target, buffer_factor=1.1)
        ring.add_updater(lambda mob: mob.surround(target, buffer_factor=1.1))
        target.save_state()
        self.play(Create(target), Create(ring), run_time=2)
        self.play(target.animate.rotate(PI/4).scale(1.2), run_time=2)
        self.play(target.animate.scale_to_fit_width(2).shift(RIGHT*3), run_time=2)
        self.play(Restore(target), run_time=1)
        ring.clear_updaters()
        self.play(FadeOut(target), FadeOut(ring), run_time=1)
        self.wait(1)
