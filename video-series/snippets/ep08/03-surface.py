import math

from manim import *


class WavySurface(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[-2, 2, 1],
                          x_length=6, y_length=6, z_length=4)
        self.set_camera_orientation(phi=70 * DEGREES, theta=-50 * DEGREES)
        self.play(Create(axes))
        surface = axes.plot_surface(lambda u, v: math.sin(u) * math.cos(v),
                                    u_range=[-3, 3], v_range=[-3, 3], resolution=(20, 20),
                                    colorscale=[BLUE, GREEN, YELLOW], fill_opacity=0.85)
        self.play(Create(surface), run_time=2)
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(5)
        self.stop_ambient_camera_rotation()
