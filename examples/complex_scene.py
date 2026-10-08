"""A complex value and its conjugate follow a rotating, labeled complex plane."""
from manim import *
from cmath import exp


class ComplexScene(Scene):
    def construct(self):
        plane = ComplexPlane(x_range=[-3,3],y_range=[-2,2],x_length=8,y_length=4,
                             background_line_style=dict(stroke_opacity=.4)).add_coordinates()
        plane.save_state()
        angle = ValueTracker(0)
        value = lambda: 2*exp(1j*angle.get_value())
        marker = Dot(plane.n2p(value()),color=YELLOW)
        marker.add_updater(lambda mob: mob.move_to(plane.n2p(value())))
        conjugate = Dot(plane.n2p(value().conjugate()),color=GREEN)
        conjugate.add_updater(lambda mob: mob.move_to(plane.n2p(value().conjugate())))
        vector = always_redraw(lambda: plane.get_vector([value().real,value().imag],color=YELLOW))
        self.play(Create(plane),FadeIn(marker),FadeIn(conjugate),FadeIn(vector),run_time=2)
        self.play(angle.animate.set_value(PI/2),run_time=3,rate_func=linear)
        self.play(plane.animate.rotate(PI/6).scale(.8),run_time=2)
        self.play(Restore(plane),run_time=2)
        self.play(FadeOut(vector),run_time=1)
        self.wait(1)
