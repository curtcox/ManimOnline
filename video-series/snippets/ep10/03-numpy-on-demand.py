import numpy as np

from manim import *


class NumPyOnDemand(Scene):
    def construct(self):
        # This file mentions NumPy, so the editor loads it before running the scene.
        xs = np.linspace(-6, 6, 49)
        sine = VGroup(*[Dot([x, np.sin(x), 0], radius=0.06, color=YELLOW) for x in xs])
        cosine = VGroup(*[Dot([x, np.cos(x), 0], radius=0.06, color=BLUE) for x in xs])
        caption = Text("49 points from np.linspace", font_size=32).to_edge(UP)
        self.play(Write(caption), LaggedStart(*[FadeIn(d) for d in sine], lag_ratio=0.05))
        self.play(Transform(sine, cosine), run_time=2)
        self.wait()
