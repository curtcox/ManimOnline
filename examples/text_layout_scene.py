"""Lay out text, numbers and formulas using their measured ink bounds."""
from manim import *


class TextLayoutScene(Scene):
    def construct(self):
        title = Text("Measured text layout", font_size=40).to_edge(UP)
        line = Underline(title, color=BLUE)
        items = VGroup(
            Text("Text uses Liberation Sans metrics", font_size=28),
            Text("Numbers use TeX digit layout", font_size=28),
            Text("Formulas are measured by MathJax", font_size=28),
        ).arrange(DOWN, aligned_edge=LEFT, buff=MED_SMALL_BUFF).next_to(line, DOWN, buff=MED_LARGE_BUFF)
        formula = MathTex(r"e^{i\pi} + 1 = 0", font_size=60).next_to(items, DOWN, buff=MED_LARGE_BUFF)
        box = SurroundingRectangle(formula, color=YELLOW, buff=SMALL_BUFF)
        tracker = ValueTracker(0)
        number = always_redraw(lambda: DecimalNumber(tracker.get_value(), font_size=36)
                               .next_to(box, RIGHT, buff=MED_SMALL_BUFF))
        self.play(Write(title), Create(line), run_time=1)
        self.play(LaggedStart(*(FadeIn(item) for item in items), lag_ratio=.3), run_time=2)
        self.play(Write(formula), Create(box), run_time=1)
        self.add(number)
        self.play(tracker.animate.set_value(1234.5), run_time=2)
        self.play(Indicate(items[1]), run_time=1)
        self.play(items[1].animate.set_color(GOLD), run_time=1)
        self.play(*(FadeOut(m) for m in (title, line, *items, formula, box, number)), run_time=1)
        self.wait(1)
