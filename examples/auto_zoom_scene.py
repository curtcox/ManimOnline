"""Fit several shapes, focus on one, and restore the saved camera view."""
from manim import *


class AutoZoomScene(MovingCameraScene):
    def construct(self):
        frame = self.camera.frame.save_state()
        circle = Circle(color=BLUE, fill_opacity=.2).shift(LEFT * 2)
        square = Square(color=RED, fill_opacity=.2).shift(RIGHT * 2)
        self.play(Create(circle), Create(square), run_time=2)
        self.play(self.camera.auto_zoom([circle, square], margin=2), run_time=2)
        self.wait(1)
        self.play(self.camera.auto_zoom(circle, margin=1), run_time=2)
        self.play(Restore(frame), run_time=2)
