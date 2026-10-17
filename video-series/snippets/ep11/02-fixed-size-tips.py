from manim import *


class FixedSizeTips(Scene):
    def construct(self):
        arrow = Arrow(LEFT * 3, RIGHT * 3, buff=0, color=YELLOW).shift(UP * 1.5)
        shaft = Line(LEFT * 3, RIGHT * 2.7)
        head = Triangle(color=BLUE, fill_opacity=1).scale(0.3).rotate(-PI / 2).move_to(RIGHT * 2.75)
        homemade = VGroup(shaft, head).set_color(BLUE).shift(DOWN * 1.5)
        self.add(Text("Arrow", font_size=28).next_to(arrow, UP))
        self.add(Text("Line + Triangle", font_size=28).next_to(homemade, UP))
        self.add(arrow, homemade)
        self.play(arrow.animate.scale(0.4), homemade.animate.scale(0.4), run_time=2)
        self.play(arrow.animate.scale(2.5), homemade.animate.scale(2.5), run_time=2)
        self.wait()
