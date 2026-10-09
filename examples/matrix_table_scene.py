"""Matrices with stretched brackets, a determinant and a labeled table."""
from manim import *


class MatrixTableScene(Scene):
    def construct(self):
        m = Matrix([[2, -1], [1, 3]]).shift(LEFT * 3 + UP * 1.5)
        m.set_column_colors(BLUE, GREEN)
        det = get_det_text(m, determinant=7)
        v = IntegerMatrix([[1], [2]]).next_to(m, DOWN, buff=.5)
        self.play(Write(m), Write(v))
        self.play(FadeIn(det))
        table = Table([["0", "1"], ["1", "0"]], row_labels=[Text("A"), Text("B")],
                      col_labels=[Text("x"), Text("y")], include_outer_lines=True).scale(.6).shift(RIGHT * 3.5 + UP * .5)
        self.play(table.create(), run_time=2)
        table.add_highlighted_cell((2, 3), color=YELLOW)
        self.play(Indicate(table.get_entries((2, 3))))
        decimals = DecimalMatrix([[0.5, 1.25], [2.0, -3.5]]).scale(.8).to_corner(DR)
        self.play(FadeIn(decimals, shift=UP))
        self.play(*(FadeOut(mob) for mob in (m, det, v, decimals)), FadeOut(table))
        self.wait(1)
