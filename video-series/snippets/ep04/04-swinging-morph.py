from manim import *


class SwingingMorph(Scene):
    def construct(self):
        shapes = [Square(color=BLUE), Circle(color=YELLOW), Triangle(color=RED), Star(color=GREEN)]
        for i, shape in enumerate(shapes):
            shape.move_to(LEFT * 4.5 + RIGHT * 3 * i)
        current = shapes[0].copy()
        self.play(Create(current))
        for target in shapes[1:]:
            self.play(Transform(current, target, path_arc=PI / 2), run_time=1.5)
        self.play(Transform(current, shapes[0], path_arc=-PI), run_time=2)
        self.wait()
