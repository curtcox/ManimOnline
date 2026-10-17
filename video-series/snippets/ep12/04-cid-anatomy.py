import base64
import hashlib

from manim import *

SHORT = "digraph{a->b}"                        # 64 bytes or fewer: stored inside the address
LONG = "from manim import *\n" + "# " + "long source " * 10   # longer: stored by fingerprint


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def cid(source):
    data = source.encode()
    prefix = b64(len(data).to_bytes(6, "big"))
    body = b64(data) if len(data) <= 64 else b64(hashlib.sha512(data).digest())
    return prefix, body, len(data)


def show(source, y, kind):
    prefix, body, size = cid(source)
    lines = [body[i:i + 44] for i in range(0, len(body), 44)]
    head = Text(prefix, font="Monospace", font_size=24, color=BLUE)
    rest = VGroup(*[Text(line, font="Monospace", font_size=24, color=YELLOW) for line in lines])
    rest.arrange(DOWN, aligned_edge=LEFT, buff=0.15)
    address = VGroup(head, rest).arrange(RIGHT, aligned_edge=UP, buff=0.1).move_to(UP * y)
    notes = VGroup(
        Text(f"length: {size} bytes", font_size=22, color=BLUE).next_to(head, UP, buff=0.3),
        Text(kind, font_size=22, color=YELLOW).next_to(rest, UP, buff=0.3),
    )
    return VGroup(address, notes)


class CIDAnatomy(Scene):
    def construct(self):
        short = show(SHORT, 1.5, "the content itself (inline)")
        long = show(LONG, -1.5, "SHA-512 fingerprint of the content")
        self.play(Write(short), run_time=2)
        self.wait()
        self.play(Write(long), run_time=3)
        self.wait()
