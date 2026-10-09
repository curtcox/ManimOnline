"""LinearTransformationScene: basis vectors, labels and a unit square follow matrices."""
from manim import *


class LinearTransformationExample(LinearTransformationScene):
    def __init__(self, **kwargs):
        LinearTransformationScene.__init__(
            self, show_coordinates=True, leave_ghost_vectors=True, **kwargs
        )

    def construct(self):
        self.add_title("A shear, then a rotation")
        self.add_unit_square()
        vector = self.add_vector([1, 2], color=PURE_YELLOW)
        self.add_transformable_label(vector, "v", animate=False)
        self.apply_matrix([[1, 1], [0, 1]])
        self.wait(0.5)
        self.apply_matrix([[0, -1], [1, 0]])
        self.wait(0.5)
        self.apply_inverse([[0, -1], [1, 0]], run_time=2)
        self.wait()


class NonlinearWarp(LinearTransformationScene):
    def construct(self):
        self.apply_nonlinear_transformation(
            lambda p: [p[0] + np.sin(p[1]), p[1] + np.sin(p[0]), 0]
        )
        self.wait()
