from manim import *


def wheel(color):
    spokes = [Line(ORIGIN, RIGHT * 1.2).rotate(k * TAU / 3, about_point=ORIGIN) for k in range(3)]
    return VGroup(Circle(radius=1.2, color=color), *spokes)


class TimeBasedUpdaters(Scene):
    def construct(self):
        slow, fast = wheel(BLUE).shift(LEFT * 3), wheel(YELLOW).shift(RIGHT * 3)
        slow.add_updater(lambda m, dt: m.rotate(-dt * PI / 2))   # a quarter turn per second
        fast.add_updater(lambda m, dt: m.rotate(-dt * PI))       # half a turn per second
        self.add(slow, fast)
        self.wait(4)
        fast.clear_updaters()
        self.wait(2)
