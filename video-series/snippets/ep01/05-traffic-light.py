from manim import *


class TrafficLight(Scene):
    def construct(self):
        housing = RoundedRectangle(width=2, height=5, corner_radius=0.4, color=GREY)
        lamps = VGroup(*[Circle(radius=0.6, color=DARK_GREY, fill_opacity=1) for _ in range(3)])
        lamps.arrange(DOWN, buff=0.3)
        self.add(housing, lamps)
        red, yellow, green = lamps

        self.play(green.animate.set_fill(GREEN))
        self.wait()
        # Your turn: switch green off, light yellow, wait, then light red.
        # Hint: self.play(green.animate.set_fill(DARK_GREY), yellow.animate.set_fill(YELLOW))
