"""ThreeDAxes, plotted surfaces, solids and camera motion in a ThreeDScene."""
import math

from manim import *


class ThreeDSurfaceScene(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes(x_range=(-3, 3, 1), y_range=(-3, 3, 1), z_range=(-2, 2, 1),
                          x_length=6, y_length=6, z_length=4)
        labels = axes.get_axis_labels()
        self.set_camera_orientation(phi=70 * DEGREES, theta=-50 * DEGREES)
        self.add(axes, labels)

        surface = axes.plot_surface(
            lambda u, v: 0.6 * math.sin(u) * math.cos(v),
            u_range=(-3, 3), v_range=(-3, 3), resolution=(16, 16),
            colorscale=[BLUE, GREEN, YELLOW, RED], fill_opacity=0.85)
        self.play(Create(surface), run_time=2)

        helix = axes.plot_parametric_curve(
            lambda t: (1.5 * math.cos(t), 1.5 * math.sin(t), t / 4), t_range=(-6, 6), color=ORANGE)
        title = Text("ThreeDAxes", font_size=36).to_corner(UL)
        self.add_fixed_in_frame_mobjects(title)
        self.play(Create(helix), FadeIn(title))

        self.move_camera(phi=55 * DEGREES, theta=20 * DEGREES, run_time=2)
        self.begin_ambient_camera_rotation(rate=0.4)
        self.wait(2)
        self.stop_ambient_camera_rotation()


class SolidsScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=65 * DEGREES, theta=-40 * DEGREES)
        sphere = Sphere(radius=0.9, resolution=(16, 8)).shift(LEFT * 2.6)
        cube = Cube(side_length=1.4, fill_color=TEAL)
        torus = Torus(major_radius=0.8, minor_radius=0.25, resolution=(16, 8)).shift(RIGHT * 2.6)
        arrow = Arrow3D(start=DOWN * 2 + LEFT * 2, end=DOWN * 2 + RIGHT * 2, color=YELLOW, resolution=8)
        self.play(FadeIn(sphere), FadeIn(cube), FadeIn(torus))
        self.play(Create(arrow))
        self.play(Rotate(cube, PI / 2, axis=UP), Rotate(torus, PI / 2, axis=RIGHT), run_time=2)
        self.move_camera(theta=40 * DEGREES, run_time=2)
        self.wait()


class PolyhedraScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=70 * DEGREES, theta=-60 * DEGREES)
        tetra = Tetrahedron(edge_length=2.2).shift(LEFT * 2)
        hull = ConvexHull3D(*[[math.cos(a), math.sin(a), (-1) ** k * 0.6]
                              for k, a in enumerate([i * TAU / 7 for i in range(7)])],
                            faces_config={"fill_color": TEAL, "fill_opacity": 0.7}).shift(RIGHT * 2)
        self.play(Create(tetra), Create(hull))
        # Moving a vertex dot drags its faces along (Polyhedron's face updater).
        self.play(tetra.graph[0].animate.shift(OUT + RIGHT * 0.5))
        self.play(Rotate(hull, PI / 2, axis=RIGHT))
        self.wait(0.5)
