from manim import *


class SeededStreams(Scene):
    def construct(self):
        swirl = lambda pos: (pos[0] * UR + pos[1] * LEFT) - pos
        # StreamLines jitters its starting points with NumPy's random generator.
        # manim-lite reproduces that generator bit for bit, so the lines match Manim's.
        stream = StreamLines(swirl, stroke_width=2, max_anchors_per_line=15, virtual_time=1.5,
                             x_range=[-6, 6, 1.5], y_range=[-3.5, 3.5, 1.5])
        self.play(stream.create(), run_time=2)
        self.add(stream)
        stream.start_animation(warm_up=False, flow_speed=1.5)
        self.wait(3)
        self.play(stream.end_animation())
