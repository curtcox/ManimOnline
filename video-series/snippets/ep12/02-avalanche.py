import hashlib

from manim import *

FIRST = "Hello, Manim"
SECOND = "Hello, Manin"     # one letter different


def fingerprint(message, cell=0.14):
    digest = hashlib.sha512(message.encode()).digest()
    bits = [(byte >> (7 - k)) & 1 for byte in digest for k in range(8)]
    squares = VGroup(*[Square(cell, stroke_width=0, fill_opacity=1, fill_color=YELLOW if bit else BLUE_E)
                       for bit in bits])
    return squares.arrange_in_grid(rows=16, cols=32, buff=0), bits


class Avalanche(Scene):
    def construct(self):
        left, left_bits = fingerprint(FIRST)
        right, right_bits = fingerprint(SECOND)
        VGroup(left, right).arrange(RIGHT, buff=0.8)
        self.play(Write(Text(f'"{FIRST}"', font_size=32).next_to(left, UP)),
                  Write(Text(f'"{SECOND}"', font_size=32).next_to(right, UP)))
        self.play(FadeIn(left), FadeIn(right))
        changed = sum(a != b for a, b in zip(left_bits, right_bits))
        marks = VGroup(*[Square(0.14, stroke_width=1.5, color=RED).move_to(square)
                         for square, a, b in zip(right, left_bits, right_bits) if a != b])
        self.play(Create(marks), run_time=2)
        self.play(Write(Text(f"{changed} of 512 bits changed", font_size=36).to_edge(DOWN)))
        self.wait()
