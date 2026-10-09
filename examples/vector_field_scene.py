"""Arrow fields, particles nudged along a field, and flowing stream lines."""
from manim import *


class VectorFieldScene(Scene):
    def construct(self):
        func = lambda pos: np.sin(pos[0] / 2) * UR + np.cos(pos[1] / 2) * LEFT
        field = ArrowVectorField(func, x_range=[-7, 7, 1], y_range=[-4, 4, 1])
        self.play(Create(field), run_time=1.5)
        dots = VGroup(*(Dot(point, color=WHITE) for point in (LEFT * 3, ORIGIN, RIGHT * 3 + UP)))
        self.add(dots)
        for dot in dots:
            dot.add_updater(field.get_nudge_updater(speed=1.5))
        self.wait(2)
        for dot in dots:
            dot.clear_updaters()
        self.play(FadeOut(field), FadeOut(dots), run_time=.5)
        swirl = lambda pos: (pos[0] * UR + pos[1] * LEFT) - pos
        # Sparse starts and short traces keep the preview's frame data small.
        stream = StreamLines(swirl, stroke_width=2, max_anchors_per_line=15, virtual_time=1.5,
                             x_range=[-6, 6, 1.5], y_range=[-3.5, 3.5, 1.5])
        self.play(stream.create(), run_time=2)
        self.add(stream)  # The flow updater runs on the field, so it must be in the scene.
        stream.start_animation(warm_up=False, flow_speed=1.5)
        self.wait(1.5)
        self.play(stream.end_animation())
        self.wait(.5)
