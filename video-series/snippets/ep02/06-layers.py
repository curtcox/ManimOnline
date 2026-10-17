from manim import *


class Layers(Scene):
    def construct(self):
        back = Circle(radius=1.5, color=BLUE, fill_opacity=1).shift(LEFT)
        middle = Square(2.5, color=GREEN, fill_opacity=1)
        front = Triangle(color=RED, fill_opacity=1).scale(1.5).shift(RIGHT)
        self.add(back, middle, front)     # later additions are drawn on top
        self.wait()
        self.play(back.animate.set_z_index(1))     # a higher z_index is drawn later
        self.play(front.animate.set_z_index(2))
        self.wait()
