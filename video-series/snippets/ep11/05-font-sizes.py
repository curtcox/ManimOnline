from manim import *


class SameSizeDifferentHeights(Scene):
    def construct(self):
        text = Text("Manim", font_size=96)
        tex = Tex("Manim", font_size=96)
        VGroup(text, tex).arrange(RIGHT, buff=1.5)
        boxes = VGroup(*[SurroundingRectangle(m, buff=0, color=YELLOW) for m in (text, tex)])
        self.add(Text('Text("Manim", font_size=96)', font_size=24).next_to(text, UP, buff=0.8))
        self.add(Tex(r'Tex("Manim", font\_size=96)', font_size=32).next_to(tex, UP, buff=0.8))
        self.play(Write(text), Write(tex))
        self.play(Create(boxes))
        heights = VGroup(*[Text(f"height {m.height:.3f}", font_size=28).next_to(m, DOWN, buff=0.6) for m in (text, tex)])
        self.play(FadeIn(heights))
        self.wait()
