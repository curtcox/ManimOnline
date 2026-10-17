import platform
import sys

from manim import *


class WhereAmI(Scene):
    def construct(self):
        facts = VGroup(
            Text(f"Python {platform.python_version()}", font_size=48),
            Text(f"sys.platform = {sys.platform}", font_size=40, color=YELLOW),
            Text(f"machine = {platform.machine()}", font_size=40, color=BLUE),
        ).arrange(DOWN, buff=0.5)
        self.play(LaggedStart(*[Write(f) for f in facts], lag_ratio=0.5))
        self.wait()
        # In ManimOnline you should see emscripten and wasm32: Python compiled to WebAssembly.
