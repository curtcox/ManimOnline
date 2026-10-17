from manim import *


class CopyTrap(Scene):
    def construct(self):
        a = Square(color=BLUE).shift(LEFT * 3)
        b = a            # a second name for the same square
        c = a.copy()     # a genuinely new square
        self.add(a, c)
        self.play(c.animate.shift(RIGHT * 6).set_color(GREEN))
        self.play(b.animate.set_color(RED))   # a turns red: a and b are one object
        self.wait()
