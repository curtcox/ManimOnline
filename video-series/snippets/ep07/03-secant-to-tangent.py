from manim import *


def f(x):
    return x ** 2 / 4 + 1


class SecantToTangent(Scene):
    def construct(self):
        axes = Axes(x_range=[-1, 5, 1], y_range=[0, 7, 1], x_length=8, y_length=5.5).to_edge(LEFT)
        graph = axes.plot(f, x_range=[-1, 4.8], color=YELLOW)
        dx = ValueTracker(2.5)
        secant = always_redraw(lambda: axes.get_secant_slope_group(
            x=1.5, graph=graph, dx=dx.get_value(), dx_label="dx", dy_label="dy",
            secant_line_color=GREEN, secant_line_length=6))
        slope = DecimalNumber(0, num_decimal_places=3).to_corner(UR)
        slope.add_updater(lambda m: m.set_value((f(1.5 + dx.get_value()) - f(1.5)) / dx.get_value()))
        caption = MathTex(r"\frac{dy}{dx} =").next_to(slope, LEFT)
        self.add(axes, graph, secant, caption, slope)
        self.play(dx.animate.set_value(0.01), run_time=5)
        self.wait()
