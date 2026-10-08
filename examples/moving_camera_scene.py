"""Pan and zoom into a shape, follow a new focus, then restore the full view."""
from manim import *


class MovingViewScene(MovingCameraScene):
    def construct(self):
        frame = self.camera.frame.save_state()
        circle = Circle(color=BLUE, fill_opacity=.2).shift(LEFT * 2)
        square = Square(color=RED, fill_opacity=.2).shift(RIGHT * 2)
        title = Text("Pan, zoom, and restore", font_size=30).shift(UP * 2.7)
        self.play(Create(circle), Create(square), FadeIn(title), run_time=2)
        self.play(frame.animate.move_to(square).scale(.5), run_time=2)
        self.wait(1)
        self.play(frame.animate.move_to(circle), run_time=1)
        self.play(Restore(frame), run_time=2)
        self.wait(1)
