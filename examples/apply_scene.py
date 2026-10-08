"""Apply matrices, complex maps and methods, then swap objects along arcs."""
from manim import *


class ApplyScene(Scene):
    def construct(self):
        square = Square(side_length=1.2, color=BLUE).shift(LEFT*3)
        circle = Circle(radius=.6, color=GREEN).shift(RIGHT*1.5+UP*1.5)
        label = Text("swap", font_size=32).shift(RIGHT*3)
        # Cycle separate scene objects; animating children of an added group is unsupported.
        dots = [Dot(point, color=color) for point, color in
                ((LEFT*2+DOWN*2, RED), (DOWN*2, YELLOW), (RIGHT*2+DOWN*2, PURPLE))]
        self.play(Create(square), Create(circle), FadeIn(label), *(Create(dot) for dot in dots))
        self.play(ApplyMatrix([[1, .6], [0, 1]], square, about_point=square.get_center()), run_time=1.5)
        self.play(ApplyComplexFunction(lambda z: z*1j, circle), run_time=1.5)
        self.play(Swap(square, label), FadeToColor(circle, ORANGE), run_time=1.5)
        self.play(CyclicReplace(*dots), ApplyMethod(circle.shift, UP, {}), run_time=1.5)
        self.play(ApplyFunction(lambda m: m.scale(.6).set_color(PINK), label),
                  circle.animate(path_arc=-PI).shift(DOWN*3+RIGHT*1.5), run_time=1.5)
        self.play(ClockwiseTransform(square, Circle(radius=.5, color=BLUE).shift(UP*2)),
                  ApplyPointwiseFunctionToCenter(lambda p: p+UP*1.5, dots[1]), run_time=1.5)
        self.play(FadeOut(square), FadeOut(circle), FadeOut(label), *(FadeOut(dot) for dot in dots))
        self.wait(.5)
