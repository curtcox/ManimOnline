"""Community entrance, emphasis, swap and exit animations with rate functions."""
from manim import *


class AnimationTourScene(Scene):
    def construct(self):
        title = Text("Animation tour", font_size=36).to_edge(UP)
        shapes = VGroup(Square(color=BLUE), Circle(color=RED), Triangle(color=GREEN)).arrange(buff=1)
        arrow = Arrow(LEFT * 3, RIGHT * 3, color=GOLD).next_to(shapes, DOWN)
        self.play(Write(title))
        self.play(Create(shapes), run_time=2)
        self.play(GrowArrow(arrow), rate_func=rate_functions.ease_out_bounce)
        self.play(Circumscribe(shapes[0]), Flash(shapes[1], color=YELLOW), Wiggle(shapes[2]))
        self.play(Swap(shapes[0], shapes[2]))
        shapes[1].generate_target()
        shapes[1].target.scale(.5).set_color(PURPLE).next_to(arrow, DOWN)
        self.play(MoveToTarget(shapes[1]), rate_func=there_and_back_with_pause, run_time=2)
        self.play(FadeOut(title, shift=UP), FadeOut(arrow, shift=DOWN),
                  FadeOut(VGroup(shapes[0], shapes[2]), lag_ratio=.5, scale=.5))
        self.play(Unwrite(shapes[1]))
        self.wait(1)
