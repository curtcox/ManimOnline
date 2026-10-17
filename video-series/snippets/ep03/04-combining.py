from manim import *


class Combining(Scene):
    def construct(self):
        balls = [Circle(radius=0.5, color=c, fill_opacity=0.8) for c in (RED, GREEN, BLUE)]
        VGroup(*balls).arrange(RIGHT, buff=1)
        label = Text("AnimationGroup", font_size=32).to_edge(UP)
        self.add(label)
        self.play(AnimationGroup(*[GrowFromCenter(b) for b in balls]))
        self.play(Transform(label, Text("LaggedStart", font_size=32).to_edge(UP)))
        self.play(LaggedStart(*[b.animate.shift(UP) for b in balls], lag_ratio=0.5))
        self.play(Transform(label, Text("Succession", font_size=32).to_edge(UP)))
        self.play(Succession(*[b.animate.shift(DOWN * 2) for b in balls]))
        self.wait()
