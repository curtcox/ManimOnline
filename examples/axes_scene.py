"""Coordinate-driven geometry follows an animated Cartesian frame."""
from manim import *


class AxesScene(Scene):
    def construct(self):
        axes = Axes(x_range=[-3,3,1], y_range=[-2,3,1], x_length=8, y_length=4,
                    axis_config=dict(font_size=22, line_to_number_buff=.4)).add_coordinates()
        axes.save_state()
        value = ValueTracker(-2)
        curve = always_redraw(lambda: VMobject(color=BLUE).set_points_as_corners(
            [axes.c2p(x,x*x/3-1) for x in (-3,-2.5,-2,-1.5,-1,-.5,0,.5,1,1.5,2,2.5,3)]))
        marker = Dot(axes.c2p(value.get_value(),value.get_value()**2/3-1),color=YELLOW)
        marker.add_updater(lambda mob: mob.move_to(
            axes.c2p(value.get_value(),value.get_value()**2/3-1)))
        readout = DecimalNumber(value.get_value(),num_decimal_places=1).shift(UP*3)
        readout.add_updater(lambda mob: mob.set_value(value.get_value()))
        self.add(readout)
        self.play(Create(axes), Create(curve), FadeIn(marker), run_time=2)
        self.play(value.animate.set_value(2), run_time=3, rate_func=linear)
        self.play(axes.animate.rotate(PI/12).scale(.9).shift(UP*.2),
                  value.animate.set_value(-1), run_time=3, rate_func=linear)
        self.play(Restore(axes), value.animate.set_value(0), run_time=2)
        self.wait(1)
