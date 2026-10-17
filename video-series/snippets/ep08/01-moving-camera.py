from manim import *


class ZoomToDetail(MovingCameraScene):
    def construct(self):
        frame = self.camera.frame
        dots = VGroup(*[Dot(radius=0.12, color=interpolate_color(BLUE, YELLOW, i / 24)) for i in range(25)])
        dots.arrange_in_grid(rows=5, buff=0.8)
        secret = Text("hello from the middle", font_size=8).move_to(dots[12]).shift(DOWN * 0.2)
        self.add(dots, secret)
        frame.save_state()
        self.play(frame.animate.scale(0.15).move_to(dots[12]), run_time=3)
        self.wait()
        self.play(frame.animate.move_to(dots[13]))
        self.play(Restore(frame), run_time=2)
        self.wait()
