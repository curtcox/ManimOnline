"""A filled curved triangle morphs while its defining edges keep their colors."""
from manim import *


class ArcPolygonScene(Scene):
    def construct(self):
        vertices = [(-2,-1,0),(2,-1,0),(0,2,0)]
        edges = [{'angle':PI/3,'color':YELLOW},
                 {'angle':PI/3,'color':GREEN},
                 {'angle':PI/3,'color':RED}]
        polygon = ArcPolygon(*vertices,arc_config=edges,color=BLUE,
                             fill_opacity=.35,stroke_width=0)
        target = ArcPolygon(*vertices,arc_config=[
                 {'angle':-PI/4,'color':YELLOW},
                 {'angle':0,'color':GREEN},
                 {'angle':-PI/4,'color':RED}],color=PURPLE,
                 fill_opacity=.5,stroke_width=0)
        marker = Dot(polygon.get_start(),color=WHITE)
        self.play(Create(polygon),FadeIn(marker),run_time=2)
        self.play(MoveAlongPath(marker,polygon),run_time=3)
        self.play(Transform(polygon,target),run_time=2)
        self.play(FadeOut(polygon),FadeOut(marker),run_time=1)
        self.wait(1)
