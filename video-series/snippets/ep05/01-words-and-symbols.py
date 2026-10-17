from manim import *


class WordsAndSymbols(Scene):
    def construct(self):
        words = Text("Text uses ordinary fonts", font_size=40).shift(UP * 2.5)
        formula = MathTex(r"e^{i\pi} + 1 = 0", font_size=72)
        sentence = Tex(r"Tex mixes words and math: $\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}$")
        sentence.shift(DOWN * 2.5)
        self.play(Write(words))
        self.play(Write(formula))
        self.play(Write(sentence), run_time=2)
        self.wait()
