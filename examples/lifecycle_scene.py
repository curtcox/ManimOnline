"""Scene setup, elapsed time, and a visible teardown animation."""
from manim import *


class LifecycleScene(Scene):
    def setup(self):
        self.shape = Square(color=BLUE)
        self.title = Text("Initialized in setup", font_size=30).shift(UP * 2.5)
        self.add(self.shape, self.title)
        self.wait(1)

    def construct(self):
        self.play(Rotate(self.shape, PI / 2), run_time=2)
        self.play(Indicate(self.shape))
        self.wait(1)

    def tear_down(self):
        summary = Text(f"Finished at {self.time:.1f}s", font_size=28).shift(DOWN * 2.5)
        self.play(FadeIn(summary))
        self.wait(1)
