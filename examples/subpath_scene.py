"""Keep separate contours while following, morphing, collapsing and restoring."""
from manim import *


class SubpathScene(Scene):
    def construct(self):
        path = VMobject(color=BLUE, fill_opacity=.35)
        path.start_new_path(UR*2).add_points_as_corners([UL*2, DL*2, DR*2]).close_path()
        path.start_new_path(UR).add_points_as_corners([DR, DL, UL]).close_path()
        path.save_state()
        self.play(Create(path), run_time=2)
        dot = Dot(color=YELLOW).move_to(path.get_start())
        self.add(dot)
        self.play(MoveAlongPath(dot, path), run_time=4, rate_func=linear)
        ring = Annulus(inner_radius=1, outer_radius=2, color=GREEN, stroke_width=4)
        self.play(FadeOut(dot), Transform(path, ring), run_time=2)
        self.play(Transform(path, RoundedRectangle(color=PURPLE, fill_opacity=.35)), run_time=2)
        self.play(Restore(path), run_time=2)
        self.wait(1)
