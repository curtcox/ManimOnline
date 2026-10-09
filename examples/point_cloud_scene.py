"""Point clouds, instant additions in a Succession, sections and scene updaters."""
from manim import *


class PointCloudScene(Scene):
    def construct(self):
        disk = PointCloudDot(center=LEFT * 3, radius=1.5, color=YELLOW)
        disk.set_colors_by_radial_gradient(inner_color=YELLOW, outer_color=RED, radius=1.5)
        line = Mobject1D(density=20)
        line.add_line(LEFT * 1, RIGHT * 4, color=TEAL)
        line.add_line(RIGHT * 4, RIGHT * 4 + UP * 2, color=BLUE)
        self.play(FadeIn(disk), FadeIn(line))
        title = Text("Point clouds", font_size=36).to_edge(UP)
        self.play(Succession(Add(title), disk.animate.rotate(PI / 2), line.animate.shift(DOWN)))
        self.next_section("hidden setup", skip_animations=True)
        self.play(line.animate.scale(.6))
        self.next_section("finale")
        clock = ValueTracker(0)
        self.add_updater(lambda dt: clock.increment_value(dt))
        marker = always_redraw(lambda: Dot(disk.get_center() + 1.8 * (np.cos(clock.get_value() * 2) * RIGHT
                                                                     + np.sin(clock.get_value() * 2) * UP)))
        self.add(marker)
        self.wait(2)
