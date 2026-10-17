from manim import *


class Positioning(Scene):
    def construct(self):
        box = Square(1.5, color=BLUE)
        dot = Dot(color=YELLOW)
        self.add(box)
        self.play(FadeIn(dot))
        self.play(dot.animate.shift(RIGHT * 3))                # relative: move by an offset
        self.play(dot.animate.move_to(UP * 2 + LEFT * 4))      # absolute: go to a point
        self.play(dot.animate.next_to(box, DOWN, buff=0.3))    # beside another object
        self.play(dot.animate.to_corner(UR))                   # against the edge of the frame
        self.play(box.animate.align_to(dot, UP))               # line up one edge
        self.wait()
