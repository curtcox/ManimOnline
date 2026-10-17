from manim import *


class OneDotPerFrame(Scene):
    def construct(self):
        mover = Dot(LEFT * 6, color=YELLOW)
        trail = VGroup()
        trail.add_updater(lambda m: m.add(Dot(mover.get_center(), radius=0.04, color=BLUE)))  # once per frame
        counter = Integer(0, font_size=60).shift(UP * 2)
        counter.add_updater(lambda m: m.set_value(len(trail)))
        caption = Text("frames so far", font_size=28).next_to(counter, DOWN)
        self.add(trail, mover, counter, caption)
        self.play(mover.animate.move_to(RIGHT * 6), run_time=4, rate_func=linear)
        self.wait()
        # Four seconds at 15 frames per second leaves about 60 dots behind.
