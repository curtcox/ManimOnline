"""Small Manim Community scene for the first render/playback check.

With Manim installed: manim -ql examples/minimal_scene.py MinimalScene
"""

from manim import Circle, Create, Scene, Square, Transform


class MinimalScene(Scene):
    def construct(self):
        circle = Circle()
        square = Square()
        self.play(Create(circle))
        self.play(Transform(circle, square))
        self.wait(0.5)
