"""Graph layouts, moving vertices with attached edges, and directed trees."""
from manim import *


class GraphScene(Scene):
    def construct(self):
        vertices = [1, 2, 3, 4, 5, 6]
        edges = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 1), (1, 4)]
        graph = Graph(vertices, edges, layout="circular", labels=True,
                      vertex_config={"fill_color": TEAL}, edge_config={"stroke_width": 3})
        self.play(Create(graph), run_time=2)
        self.play(graph[1].animate.move_to(UP * 2.5 + RIGHT * 2))
        self.play(graph.animate.change_layout("spring", layout_config={"seed": 2}))
        self.play(graph.animate.add_vertices(7, positions={7: DOWN * 3}))
        self.play(graph.animate.add_edges((7, 3), (7, 6)))
        self.play(graph.animate.remove_vertices(4))
        self.play(graph.animate.scale(.6).to_edge(LEFT))
        tree = DiGraph([1, 2, 3, 4, 5, 6, 7], [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7)],
                       layout="tree", root_vertex=1, layout_scale=2,
                       vertex_config={"color": GOLD}, edge_config={"tip_config": {"tip_length": .2}})
        tree.to_edge(RIGHT)
        self.play(Create(tree), run_time=2)
        self.play(tree[5].animate.shift(DOWN * .8 + RIGHT * .5))
        self.wait(.5)
