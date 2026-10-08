"""Change depth across group boundaries while retaining group geometry."""
from manim import *


class LayerScene(Scene):
    def construct(self):
        back = Square(color=BLUE, fill_opacity=1, z_index=-2).shift(LEFT * 0.65)
        front = Square(color=RED, fill_opacity=1, z_index=2).shift(RIGHT * 0.65)
        pair = VGroup(back, front).scale(1.2).shift(UP * 0.2).save_state()
        middle = Circle(radius=0.8, color=YELLOW, fill_opacity=1).shift(DOWN * 0.4)
        title = Text("Layers across groups", font_size=30, z_index=10).shift(UP * 2.5)
        self.add(pair, middle, title)
        self.wait(1)
        self.play(pair.animate.set_z_index(-3), run_time=2, rate_func=linear)
        self.wait(1)
        self.play(Restore(pair), run_time=2, rate_func=linear)
        self.wait(1)
