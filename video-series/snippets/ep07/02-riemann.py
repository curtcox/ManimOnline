from manim import *


class RiemannRefinement(Scene):
    def construct(self):
        axes = Axes(x_range=[0, 4, 1], y_range=[0, 5, 1], x_length=8, y_length=5).add_coordinates()
        graph = axes.plot(lambda x: x ** 2 / 4 + 0.5, color=YELLOW)
        self.add(axes, graph)
        rectangles = axes.get_riemann_rectangles(graph, x_range=[0, 4], dx=1, fill_opacity=0.6)
        self.play(Create(rectangles))
        for dx in [0.5, 0.25, 0.1, 0.05]:
            self.play(Transform(rectangles, axes.get_riemann_rectangles(graph, x_range=[0, 4], dx=dx, fill_opacity=0.6)))
        area = axes.get_area(graph, x_range=[0, 4], color=BLUE, opacity=0.6)
        self.play(FadeOut(rectangles), FadeIn(area))
        exact = MathTex(r"\int_0^4 \left(\frac{x^2}{4} + \frac{1}{2}\right) dx = \frac{22}{3}").to_corner(UL)
        self.play(Write(exact))
        self.wait()
