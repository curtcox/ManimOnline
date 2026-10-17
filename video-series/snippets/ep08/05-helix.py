import math

from manim import *


class Helix(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes(x_range=[-2, 2, 1], y_range=[-2, 2, 1], z_range=[-2, 2, 1],
                          x_length=4, y_length=4, z_length=4)
        title = Text("A helix: (cos t, sin t, t / 4)", font_size=32).to_corner(UL)
        self.add_fixed_in_frame_mobjects(title)      # stays flat on the screen
        self.set_camera_orientation(phi=75 * DEGREES, theta=-30 * DEGREES)
        helix = axes.plot_parametric_curve(lambda t: (math.cos(t), math.sin(t), t / 4),
                                           t_range=[-TAU, TAU], color=YELLOW)
        self.add(axes)
        self.play(Write(title), Create(helix), run_time=3)
        self.move_camera(phi=10 * DEGREES, theta=-90 * DEGREES, run_time=3)   # look straight down
        self.move_camera(phi=88 * DEGREES, theta=0, run_time=3)                # look from the side
        self.wait()
