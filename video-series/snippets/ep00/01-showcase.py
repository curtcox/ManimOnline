from manim import *
import math



class Showcase(Scene):
    def construct(self):
        title = Text("Manim, in your browser", font_size=56)
        self.play(Write(title))
        self.play(title.animate.scale(0.6).to_edge(UP))

        shape = Square(color=BLUE, fill_opacity=0.4)
        self.play(Create(shape))
        self.play(Transform(shape, Circle(color=YELLOW, fill_opacity=0.4)))
        self.play(Transform(shape, Star(color=RED, fill_opacity=0.4)))

        formula = MathTex(r"e^{i\pi} + 1 = 0", font_size=72)
        self.play(ReplacementTransform(shape, formula))
        self.wait(0.5)

        axes = Axes(x_range=[-4, 4, 1], y_range=[-1.5, 1.5, 1], x_length=10, y_length=3).shift(DOWN * 0.5)
        wave = axes.plot(lambda x: math.sin(2 * x) * math.exp(-0.1 * x * x), color=YELLOW)
        self.play(FadeOut(formula, shift=UP), Create(axes))
        self.play(Create(wave), run_time=2)
        self.wait()
