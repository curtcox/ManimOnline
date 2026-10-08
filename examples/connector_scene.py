from manim import *


class ConnectorScene(Scene):
    def construct(self):
        connector = Arrow(LEFT * 3 + DOWN, RIGHT * 3 + DOWN, color=BLUE)
        connector.rotate(PI / 6).scale(0.8).save_state()
        start = Dot(connector.get_start(), color=GREEN)
        end = Dot(connector.get_end(), color=RED)
        title = Text("Move the connector endpoints", font_size=30).shift(UP * 3)
        self.add(connector, start, end, title)
        new_start, new_end = LEFT * 3 + UP, RIGHT * 2 + DOWN * 2
        self.play(connector.animate.put_start_and_end_on(new_start, new_end),
                  start.animate.move_to(new_start), end.animate.move_to(new_end),
                  run_time=4, rate_func=linear)
        self.wait(1)
        self.play(Restore(connector), FadeOut(start), FadeOut(end), run_time=2)
        self.wait(1)
