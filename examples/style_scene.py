from manim import *


class StyleScene(Scene):
    def construct(self):
        shapes = VGroup(Square(), Circle(), Triangle().scale(2))
        shapes.arrange(RIGHT, buff=0.6)
        shapes.set_fill(BLUE, opacity=0.6).set_stroke(YELLOW, width=4)
        title = Text("Fill and outline", font_size=32).shift(UP * 2)
        self.play(Create(shapes), Write(title), run_time=2)
        self.play(shapes.animate.set_fill(RED, opacity=0.8)
                  .set_stroke(GREEN, width=6, opacity=0.7), run_time=2)
        self.play(shapes.animate.set_opacity(0.2), run_time=2)
        self.play(shapes.animate.set_opacity(1), run_time=2)
        self.wait(1)
