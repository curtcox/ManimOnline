"""Glyph-level Text: per-letter colors, markup, gradients and letter animations."""
from manim import *


class TextEffectsScene(Scene):
    def construct(self):
        title = Text("Hello, Manim!", font_size=64, t2c={"Manim": BLUE, "[0:5]": YELLOW})
        self.play(Write(title))
        self.play(title[0].animate.scale(1.5).set_color(RED), Indicate(title[-1]))
        self.play(title.animate.to_edge(UP))
        rainbow = Text("Gradient text", gradient=(RED, YELLOW, GREEN, BLUE), font_size=56)
        markup = MarkupText('Some <b>bold</b>, <i>italic</i> and <span foreground="#83C167">green</span> words',
                            font_size=36).next_to(rainbow, DOWN, buff=.6)
        self.play(FadeIn(rainbow, shift=UP), AddTextLetterByLetter(markup))
        self.play(LaggedStart(*(g.animate.shift(UP * .3) for g in rainbow), lag_ratio=.1), run_time=2)
        self.play(*(FadeOut(m) for m in (title, rainbow, markup)))
        self.wait(1)
