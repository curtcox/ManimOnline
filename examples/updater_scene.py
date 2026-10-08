"""A timed spinner and a follower/camera that track an animated dot."""
from manim import *


class UpdaterScene(MovingCameraScene):
    def construct(self):
        dot = Dot(color=BLUE).shift(LEFT * 2)
        follower = Square(side_length=.5, color=YELLOW)
        follower.add_updater(lambda m: m.move_to(dot.get_center() + UP), call_updater=True)
        spinner = Square(color=RED).shift(DOWN * 2)
        spinner.add_updater(lambda m, dt: m.rotate(dt * PI / 2))
        self.camera.frame.add_updater(lambda m: m.move_to(dot), call_updater=True)
        self.add(dot, follower, spinner)
        self.wait(1)
        self.play(dot.animate.shift(RIGHT * 4), run_time=4, rate_func=linear)
        spinner.clear_updaters()
        self.camera.frame.clear_updaters()
        self.wait(1)
