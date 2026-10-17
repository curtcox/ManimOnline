from manim import *


def anchor_dots(shape, color):
    points = shape.get_points()
    return VGroup(*[Dot(points[i], radius=0.08, color=color) for i in range(0, len(points), 4)])


class MatchingPoints(Scene):
    def construct(self):
        square = Square(3, color=BLUE).shift(LEFT * 3.5)
        circle = Circle(radius=1.7, color=YELLOW).shift(RIGHT * 3.5)
        square_dots, circle_dots = anchor_dots(square, BLUE), anchor_dots(circle, YELLOW)
        self.add(square, circle)
        self.play(FadeIn(square_dots), FadeIn(circle_dots))
        self.wait()

        # Four curves cannot pair up with eight, so the square's curves are split in half.
        square.align_points(circle)
        self.play(FadeOut(square_dots))
        square_dots = anchor_dots(square, BLUE)
        self.play(FadeIn(square_dots, scale=2))
        self.wait()

        # Now every point has a partner, and each one travels in a straight line.
        target = circle.copy().move_to(square)
        self.play(Transform(square, target), Transform(square_dots, anchor_dots(target, YELLOW)), run_time=3)
        self.wait()
