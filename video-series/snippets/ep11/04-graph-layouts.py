from manim import *


class GraphLayouts(Scene):
    def construct(self):
        vertices = list(range(1, 9))
        edges = [(1, 2), (2, 3), (3, 4), (4, 1), (1, 5), (2, 6), (3, 7), (4, 8), (5, 6), (7, 8)]
        graph = Graph(vertices, edges, layout="spring", layout_config={"seed": 3}, labels=True)
        self.play(Create(graph), run_time=2)
        self.play(graph.animate.change_layout("circular"), run_time=2)
        self.play(graph.animate.change_layout("spring", layout_config={"seed": 7}), run_time=2)
        self.wait()
