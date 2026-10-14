from manim import *


class StyleCopyScene(Scene):
    def construct(self):
        template = Circle(radius=.7, fill_color=[BLUE, YELLOW], fill_opacity=[.3, 1],
                          stroke_color=[WHITE, GREEN], stroke_width=5)
        template.set_background_stroke([PURPLE, RED], width=14, opacity=[.2, .9])
        template.shift(3 * LEFT)
        shapes = VGroup(Square(side_length=1.2), Triangle().scale(1.4), Circle(radius=.6))
        shapes.arrange(RIGHT, buff=.8).shift(2 * RIGHT)
        self.play(FadeIn(template), FadeIn(shapes), run_time=1)
        self.play(shapes.animate.match_style(template), run_time=2)
        self.wait(2)
        self.play(FadeOut(template), FadeOut(shapes), run_time=1)
        self.wait(2)
