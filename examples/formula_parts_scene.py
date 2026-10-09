"""Color, indicate and rearrange the parts of multi-string formulas."""
from manim import *


class FormulaPartsScene(Scene):
    def construct(self):
        first = MathTex("a^2", "+", "b^2", "=", "c^2", font_size=72)
        first.set_color_by_tex("a", BLUE).set_color_by_tex("b", GREEN)
        self.play(Write(first))
        self.play(Indicate(first[4]), Circumscribe(first[0]))
        second = MathTex("c^2", "-", "b^2", "=", "a^2", font_size=72)
        second.set_color_by_tex_to_color_map({"a": BLUE, "b": GREEN})
        self.play(TransformMatchingTex(first, second), run_time=2)
        label = Tex(r"Solve for $a^2$", font_size=40).next_to(second, UP, buff=.6)
        self.play(FadeIn(label, shift=DOWN * .3))
        isolated = MathTex(r"e^{i\pi} + 1 = 0", substrings_to_isolate=["e", r"\pi"],
                           tex_to_color_map={r"\pi": YELLOW}).next_to(second, DOWN, buff=.8)
        self.play(Write(isolated))
        self.play(FadeOut(label), FadeOut(second), FadeOut(isolated))
        self.wait(1)
