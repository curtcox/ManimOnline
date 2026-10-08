"""Endpoint arcs bend in opposite directions and follow moving endpoints."""
from manim import *


class EndpointArcScene(Scene):
    def construct(self):
        height = ValueTracker(0)
        bend = ValueTracker(PI/2)
        start = LEFT*2
        def end():
            return RIGHT*2+UP*height.get_value()
        positive = always_redraw(lambda:ArcBetweenPoints(start,end(),angle=bend.get_value(),color=YELLOW))
        negative = always_redraw(lambda:ArcBetweenPoints(start,end(),radius=-3,color=GREEN))
        markers = always_redraw(lambda:VGroup(Dot(start,color=RED),Dot(end(),color=RED)))
        chord = always_redraw(lambda:Line(start,end(),color=BLUE,stroke_opacity=.4))
        self.add(chord,markers)
        self.play(Create(positive),Create(negative),run_time=2)
        self.play(height.animate.set_value(1.5),run_time=3)
        self.play(bend.animate.set_value(0),run_time=2)
        self.play(FadeOut(positive),FadeOut(negative),run_time=1)
        self.wait(1)
