"""Syntax-highlighted code listings with line numbers and window backgrounds."""
from manim import *


class CodeScene(Scene):
    def construct(self):
        source = '''def fibonacci(n):
    """Return the first n Fibonacci numbers."""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

print(list(fibonacci(8)))'''
        code = Code(code_string=source, language="python", background="window",
                    formatter_style="monokai")
        self.play(FadeIn(code.background), run_time=.5)
        self.play(Write(code.line_numbers), AddTextLetterByLetter(code.code_lines[0]))
        self.play(LaggedStart(*(FadeIn(line, shift=RIGHT * .2) for line in code.code_lines[1:]), lag_ratio=.2))
        box = SurroundingRectangle(code.code_lines[5], color=YELLOW, buff=.05)
        self.play(Create(box))
        self.play(box.animate.become(SurroundingRectangle(code.code_lines[3], color=YELLOW, buff=.05)))
        self.play(code.animate.scale(.7).to_edge(LEFT), FadeOut(box))
        result = Code(code_string="[0, 1, 1, 2, 3, 5, 8, 13]", language="python", add_line_numbers=False)
        result.next_to(code, RIGHT, buff=.5)
        self.play(FadeIn(result, shift=LEFT))
        self.wait(.5)
