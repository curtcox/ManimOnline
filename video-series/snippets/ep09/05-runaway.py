from manim import *


class Runaway(Scene):
    def construct(self):
        self.add(Text("This scene never finishes."))
        while True:      # an infinite loop: the editor stops it after 90 seconds,
            pass         # or press Cancel render to stop it sooner
