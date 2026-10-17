from manim import *

MESSAGE = "the cat sat on the mat; the cat sat"   # try your own repetitive sentence
CELL = 0.36


def lz77(text, min_match=3):
    """Greedy LZ77: each token is a literal character or (distance back, length)."""
    tokens, i = [], 0
    while i < len(text):
        best_length, best_distance = 0, 0
        for start in range(i):
            length = 0
            while i + length < len(text) and text[start + length] == text[i + length]:
                length += 1
            if length > best_length:
                best_length, best_distance = length, i - start
        if best_length >= min_match:
            tokens.append((i, best_distance, best_length))
            i += best_length
        else:
            tokens.append((i, 0, 1))
            i += 1
    return tokens


def row(text, y):
    cells = VGroup(*[Text("·" if ch == " " else ch, font="Monospace", font_size=26) for ch in text])
    for k, cell in enumerate(cells):
        cell.move_to(RIGHT * (k - (len(text) - 1) / 2) * CELL + UP * y)
    return cells


class LZCompression(Scene):
    def construct(self):
        source = row(MESSAGE, 2)
        self.play(Write(source), run_time=2)
        x = -(len(MESSAGE) - 1) / 2 * CELL
        output = VGroup()
        literals = 0
        references = 0
        for start, distance, length in lz77(MESSAGE):
            if distance == 0:
                cell = source[start].copy().move_to(RIGHT * x + DOWN)
                self.play(TransformFromCopy(source[start], cell), run_time=0.2)
                output.add(cell)
                x += CELL
                literals += 1
                continue
            earlier = SurroundingRectangle(source[start - distance:start - distance + length], color=GREEN, buff=0.05)
            repeat = SurroundingRectangle(source[start:start + length], color=YELLOW, buff=0.05)
            token = Text(f"({distance},{length})", font="Monospace", font_size=26, color=YELLOW)
            token.move_to(RIGHT * (x + token.width / 2) + DOWN)
            self.play(Create(earlier), Create(repeat))
            self.play(TransformFromCopy(repeat, token))
            self.play(FadeOut(earlier, repeat), run_time=0.4)
            output.add(token)
            x += token.width + 0.1
            references += 1
        summary = Text(f"{len(MESSAGE)} characters became {literals} letters and {references} references",
                       font_size=28).to_edge(DOWN)
        self.play(Write(summary))
        self.wait()
