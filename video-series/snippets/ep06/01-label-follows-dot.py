from manim import *


class LabelFollowsDot(Scene):
    def construct(self):
        dot = Dot(LEFT * 4, color=YELLOW)
        label = Text("I follow", font_size=28)
        label.add_updater(lambda m: m.next_to(dot, UP))   # runs once per frame
        self.add(dot, label)
        self.play(dot.animate.shift(RIGHT * 8), run_time=2)
        self.play(dot.animate.move_to(UP * 2), run_time=1.5)
        self.play(Rotate(dot, TAU, about_point=ORIGIN), run_time=3)
        label.clear_updaters()
        self.play(dot.animate.move_to(DOWN * 3))           # now the label stays behind
        self.wait()
