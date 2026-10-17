from manim import *


class BendTheGrid(LinearTransformationScene):
    def __init__(self, **kwargs):
        super().__init__(show_coordinates=True, leave_ghost_vectors=True, **kwargs)

    def construct(self):
        self.add_vector([1, 2], color=YELLOW)
        self.apply_matrix([[1, 1], [0, 1]])     # a shear: i-hat stays, j-hat leans right
        self.wait()
        self.apply_matrix([[0, -1], [1, 0]])    # then a quarter turn
        self.wait()
