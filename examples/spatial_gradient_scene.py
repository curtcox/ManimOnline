from manim import *


class SpatialGradientScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=65 * DEGREES, theta=-60 * DEGREES)
        panel = Square(side_length=2.4, fill_opacity=1, fill_color=[BLUE, YELLOW], stroke_width=0)
        panel.rotate(PI / 2, axis=RIGHT).shift(2 * LEFT)
        panel.set_sheen_direction(OUT)
        shaded = Square(side_length=2.4, fill_opacity=1, fill_color=[RED, BLUE],
                        stroke_width=0, shade_in_3d=True)
        shaded.rotate(PI / 2, axis=RIGHT).shift(2 * RIGHT)
        self.play(FadeIn(panel), FadeIn(shaded), run_time=1)
        self.move_camera(theta=-120 * DEGREES, run_time=2)
        self.play(panel.animate.shift(OUT), Rotate(shaded, angle=PI / 3, axis=OUT), run_time=2)
        self.move_camera(theta=-60 * DEGREES, run_time=1)
        self.play(FadeOut(panel), FadeOut(shaded), run_time=1)
        self.wait(1)
