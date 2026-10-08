from manim import *


class RestoreScene(Scene):
    def construct(self):
        shapes = VGroup(Square(), Circle()).arrange(RIGHT, buff=0.6)
        shapes.set_fill(BLUE, 0.5).set_stroke(YELLOW, width=4)
        shapes.save_state()
        title = Text("Change and restore", font_size=32).shift(UP * 2.5)
        self.add(title)
        self.play(Create(shapes), run_time=2)
        self.play(shapes.animate.shift(DOWN).scale(0.6).rotate(PI / 4)
                  .set_fill(RED, 0.8).set_stroke(GREEN, width=6), run_time=2)
        self.play(Restore(shapes), run_time=3)
        self.play(ShrinkToCenter(shapes), run_time=1)
        self.play(shapes.animate.restore(), run_time=2)
        self.wait(1)
