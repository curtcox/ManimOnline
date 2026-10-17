from manim import *


class FrameClock(Scene):
    def construct(self):
        face = Circle(radius=2, color=GREY)
        hand = Line(ORIGIN, UP * 1.8, color=YELLOW, stroke_width=8)
        hand.add_updater(lambda m, dt: m.rotate(-TAU * dt, about_point=ORIGIN))   # one turn per second
        seconds = DecimalNumber(0, num_decimal_places=2, font_size=48).to_corner(UL)
        seconds.add_updater(lambda m: m.set_value(self.time))
        frame = Integer(0, font_size=48).to_corner(UR)
        frame.add_updater(lambda m: m.set_value(round(self.time * 15)))
        self.add(face, hand, seconds, frame,
                 Text("seconds", font_size=24).next_to(seconds, DOWN),
                 Text("frame", font_size=24).next_to(frame, DOWN))
        self.wait(4)
        # Export as MP4, then scrub the video: its timestamps come from frame numbers.
