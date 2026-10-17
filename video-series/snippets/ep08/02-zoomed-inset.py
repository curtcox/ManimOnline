from manim import *


class ZoomedInset(ZoomedScene):
    def __init__(self, **kwargs):
        super().__init__(zoom_factor=0.25, zoomed_display_height=3, zoomed_display_width=4,
                         image_frame_stroke_width=4, **kwargs)

    def construct(self):
        ticks = VGroup(*[Line(UP * 0.1, DOWN * 0.1).shift(RIGHT * (i * 0.1 - 5)) for i in range(101)])
        ruler = VGroup(Line(LEFT * 5, RIGHT * 5), ticks).shift(DOWN * 1.5)
        dot = Dot(ruler.get_left(), color=YELLOW)
        self.add(ruler, dot)
        frame = self.zoomed_camera.frame
        frame.move_to(dot).set_color(YELLOW)
        self.zoomed_display.to_corner(UR)
        self.zoomed_display.display_frame.set_color(YELLOW)
        frame.add_updater(lambda m: m.move_to(dot))
        self.activate_zooming(animate=True)
        self.play(dot.animate.move_to(ruler.get_right()), run_time=5, rate_func=linear)
        self.wait()
