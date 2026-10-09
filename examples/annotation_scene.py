"""Titles, braces with labels, Tex text, bullet lists, vectors and variables."""
from manim import *


class AnnotationScene(Scene):
    def construct(self):
        title = Title(r"Annotating a rectangle")
        rect = Rectangle(width=4, height=2, color=BLUE).shift(LEFT * 2.5 + DOWN * .5)
        width = BraceLabel(rect, r"w = 4", brace_direction=DOWN)
        height = Brace(rect, direction=LEFT)
        height_label = height.get_tex(r"h = 2")
        notes = BulletedList(r"Area is $w \cdot h$", r"Perimeter is $2(w + h)$", font_size=32)
        notes.next_to(rect, RIGHT, buff=1)
        area = Variable(0, "A", num_decimal_places=1).next_to(notes, DOWN, buff=.6, aligned_edge=LEFT)
        diagonal = Vector(rect.get_corner(UR) - rect.get_corner(DL), color=YELLOW).shift(rect.get_corner(DL))
        self.play(Write(title))
        self.play(Create(rect))
        self.play(width.creation_anim(), GrowFromCenter(height), FadeIn(height_label))
        self.play(FadeIn(notes, shift=RIGHT * .5), FadeIn(area))
        self.play(GrowArrow(diagonal), area.tracker.animate.set_value(8), run_time=2)
        self.play(notes.animate.fade_all_but(0), Indicate(height_label))
        self.play(*(FadeOut(m) for m in (title, rect, width, height, height_label, notes, area, diagonal)))
        self.wait(1)
