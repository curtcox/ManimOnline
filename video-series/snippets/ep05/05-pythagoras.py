from manim import *


class Pythagoras(Scene):
    def construct(self):
        a, b = 3, 2
        A = LEFT * 4.5 + DOWN * 0.5
        B, C = A + RIGHT * a, A + UP * b
        triangle = Polygon(A, B, C, color=WHITE, fill_opacity=0.2)
        normal = RIGHT * b + UP * a   # as long as the hypotenuse, at a right angle to it
        squares = VGroup(
            Polygon(A, B, B + DOWN * a, A + DOWN * a, color=BLUE, fill_opacity=0.5),
            Polygon(A, C, C + LEFT * b, A + LEFT * b, color=GREEN, fill_opacity=0.5),
            Polygon(B, C, C + normal, B + normal, color=RED, fill_opacity=0.5),
        )
        labels = VGroup(*[MathTex(t, font_size=48).move_to(s.get_center()) for t, s in zip(["a^2", "b^2", "c^2"], squares)])
        self.play(Create(triangle))
        self.play(LaggedStart(*[DrawBorderThenFill(s) for s in squares], lag_ratio=0.4))
        self.play(LaggedStart(*[Write(l) for l in labels], lag_ratio=0.4))
        equation = MathTex("a^2", "+", "b^2", "=", "c^2", font_size=72).to_edge(RIGHT, buff=1)
        for i, color in zip([0, 2, 4], [BLUE, GREEN, RED]):
            equation[i].set_color(color)
        self.play(*[TransformFromCopy(labels[k], equation[i]) for k, i in enumerate([0, 2, 4])],
                  FadeIn(equation[1]), FadeIn(equation[3]), run_time=2)
        self.wait()
