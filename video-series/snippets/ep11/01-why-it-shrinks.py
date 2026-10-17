from manim import *


class WhyItShrinks(Scene):
    def construct(self):
        left = Square(2.5, color=BLUE).shift(LEFT * 3.2)
        right = Square(2.5, color=YELLOW).shift(RIGHT * 3.2)
        self.add(Text(".animate.rotate(PI)", font_size=28).to_edge(UP).shift(LEFT * 3.2))
        self.add(Text("Rotate(PI)", font_size=28).to_edge(UP).shift(RIGHT * 3.2))
        traces = [TracedPath(lambda s=s, k=k: s.get_vertices()[k], stroke_color=c, stroke_width=3)
                  for s, c in ((left, BLUE), (right, YELLOW)) for k in range(4)]
        self.add(left, right, *traces)
        # Each corner of the left square travels in a straight line to its final position.
        self.play(left.animate.rotate(PI), Rotate(right, PI), run_time=4)
        self.wait()
