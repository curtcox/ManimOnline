"""Construct a circle through three points and follow its rotated boundary."""
from manim import *


class CircleConstructionScene(Scene):
    def construct(self):
        points = [LEFT*2, UP*2, RIGHT*2]
        circle = Circle.from_three_points(*points, color=BLUE)
        dots = VGroup(*(Dot(point, color=YELLOW) for point in points))
        marker = Dot(circle.point_at_angle(PI/2), color=RED, radius=.12)
        marker.add_updater(lambda mob: mob.move_to(circle.point_at_angle(PI/2)))
        circle.save_state()
        self.play(Create(circle), FadeIn(dots), FadeIn(marker), run_time=2)
        self.play(circle.animate.rotate(PI/3).scale(.7), run_time=2)
        self.play(circle.animate.move_arc_center_to(RIGHT*2+DOWN), run_time=2)
        self.play(Restore(circle), run_time=1)
        self.play(FadeOut(circle), FadeOut(dots), FadeOut(marker), run_time=1)
        self.wait(1)
