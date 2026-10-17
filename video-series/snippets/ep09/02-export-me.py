from manim import *


class ExportMe(Scene):
    def construct(self):
        stars = VGroup(*[
            RegularPolygram(n, density=2, radius=1.1).set_stroke(color, width=6)
            for n, color in zip([5, 7, 9], [BLUE, YELLOW, RED])
        ]).arrange(RIGHT, buff=0.8)
        self.play(LaggedStart(*[Create(s) for s in stars], lag_ratio=0.3), run_time=2)
        self.play(*[Rotate(s, TAU / n) for s, n in zip(stars, [5, 7, 9])], run_time=2)
        self.play(stars.animate.set_fill(opacity=0.4))
        caption = Text("Export: MP4 video", font_size=36).to_edge(DOWN)
        self.play(Write(caption))
        self.wait()
