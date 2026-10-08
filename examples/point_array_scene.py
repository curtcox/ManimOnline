"""Build and edit raw cubic points, append a ring, and restore the original curve."""
from manim import *


class PointArrayScene(Scene):
    def construct(self):
        seed = CubicBezier((-3,-1), (-1,2), (1,-2), (3,1)).rotate(PI/6)
        points = seed.get_points()
        path = VMobject(color=BLUE).set_points(points[:1]).append_points(points[1:])
        path.save_state()
        self.play(Create(path), run_time=2)
        edited = [(point[0], point[1]+(1.5 if i in (1,2) else 0), point[2])
                  for i, point in enumerate(path.get_points())]
        self.play(path.animate.set_points(edited), run_time=2)
        path.append_vectorized_mobject(Annulus(inner_radius=.35, outer_radius=.8,
                                               arc_center=UP*2))
        self.wait(1)
        self.play(Restore(path), run_time=2)
        self.wait(1)
