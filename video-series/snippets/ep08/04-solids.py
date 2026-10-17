from manim import *


class Solids(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=65 * DEGREES, theta=-40 * DEGREES)
        sphere = Sphere(radius=0.9, resolution=(16, 8)).shift(LEFT * 2.8)
        cube = Cube(side_length=1.4, fill_color=TEAL)
        torus = Torus(major_radius=0.8, minor_radius=0.25, resolution=(16, 8)).shift(RIGHT * 2.8)
        self.play(FadeIn(sphere), FadeIn(cube), FadeIn(torus))
        self.play(Rotate(cube, PI / 2, axis=UP), Rotate(torus, PI / 2, axis=RIGHT), run_time=2)
        self.move_camera(phi=40 * DEGREES, theta=30 * DEGREES, run_time=3)
        self.wait()
