"""Shared building blocks for the series' production scenes (Manim Community).

Each segment of an episode script is one Scene class. Segment timing comes from the
segment's narration: by default its word count at 145 words per minute plus any
<break/> pauses, or the measured audio length when build/narration/durations.json
exists ({"01.1": 52.3, ...}, seconds per segment). Visual beats are placed at
fractions of that length with Segment.hold_until, so re-timing to the real
ElevenLabs audio is a matter of writing durations.json and rendering again.

Render from the repository root, with TeX on the PATH for MathTex, for example:
    manim -qh video-series/production/ep01.py Segment_1_1
Set SEGMENT_LABELS=1 to burn the segment id and clock into a corner for review.
"""
import json
import os
import re
from pathlib import Path

from manim import *

PRODUCTION = Path(__file__).resolve().parent
SERIES = PRODUCTION.parent
WORDS_PER_MINUTE = 145
TAIL_SECONDS = 0.8          # breathing room after the last sentence

# Colour roles from the series README.
OBJECT = BLUE
FOCUS = YELLOW
AFTER = GREEN
WARNING = RED
SCAFFOLD = GREY_B
DIM = GREY_D

QR_HEIGHT = 2.0             # 25 % of the 8-unit frame (README asks for at least 22 %)

# One sans-serif face for every Text; Pango otherwise falls back to a serif. Avenir Next
# ships with macOS; set SERIES_FONT to another installed family on other systems.
FONT = os.environ.get('SERIES_FONT', 'Avenir Next')
Text.set_default(font=FONT)
MarkupText.set_default(font=FONT)


# ---------------------------------------------------------------- timing

def _episode_file(episode):
    matches = sorted((SERIES / 'episodes').glob(f'{episode:02d}-*.md'))
    if not matches:
        raise FileNotFoundError(f'No script for episode {episode}')
    return matches[0]


def narration_text(episode, segment):
    """Narration lines (blockquotes) of one '### <segment> Title' section."""
    lines, inside = [], False
    for line in _episode_file(episode).read_text().splitlines():
        heading = re.match(r'^### (\d+\.\d+)\s', line)
        if heading:
            inside = heading.group(1) == segment
            continue
        if line.startswith('## '):
            inside = False
        if inside and line.startswith('>'):
            lines.append(line.lstrip('>').strip())
    return ' '.join(l for l in lines if l)


def narration_seconds(episode, segment):
    measured = SERIES / 'build' / 'narration' / 'durations.json'
    if measured.exists():
        durations = json.loads(measured.read_text())
        key = f'{episode:02d}.{segment.split(".")[1]}'
        if key in durations:
            return float(durations[key])
    text = narration_text(episode, segment)
    pauses = sum(float(s) for s in re.findall(r'<break time="([\d.]+)s"\s*/>', text))
    words = len(re.sub(r'<[^>]+>', ' ', text).split())
    return words / WORDS_PER_MINUTE * 60 + pauses


class Segment(Scene):
    """A scene whose length follows its segment's narration."""

    EPISODE = 0
    SEGMENT = '0.0'

    def setup(self):
        self.target = narration_seconds(self.EPISODE, self.SEGMENT) + TAIL_SECONDS
        if os.environ.get('SEGMENT_LABELS'):
            label = Text(f'{self.SEGMENT}', font_size=18, color=DIM).to_corner(UL, buff=0.15)
            clock = DecimalNumber(0, num_decimal_places=1, font_size=18, color=DIM).next_to(label, RIGHT)
            clock.add_updater(lambda m: m.set_value(self.renderer.time))
            self.add_foreground_mobjects(label, clock)

    def hold_until(self, fraction):
        """Wait until the given fraction of the narration has been spoken."""
        remaining = fraction * self.target - self.renderer.time
        if remaining > 1 / 30:
            self.wait(remaining)

    def finish(self):
        self.hold_until(1.0)


# ---------------------------------------------------------------- QR codes

_QR = json.loads((PRODUCTION / 'qr-matrices.json').read_text())


def qr_code(qr_id, height=QR_HEIGHT):
    """A scannable QR code as vector rectangles, black on white with its quiet zone."""
    rows = _QR[qr_id]['rows']
    quiet = 4
    module = height / (len(rows) + 2 * quiet)
    backing = Square(side_length=height).set_fill(WHITE, 1).set_stroke(width=0)
    top_left = backing.get_corner(UL) + (RIGHT + DOWN) * quiet * module
    modules = VGroup()
    for r, row in enumerate(rows):
        for match in re.finditer(r'1+', row):
            run = match.end() - match.start()
            # A hair of overlap hides anti-aliasing seams between neighbouring modules.
            rect = Rectangle(width=run * module * 1.01, height=module * 1.04)
            rect.set_fill(BLACK, 1).set_stroke(width=0)
            rect.move_to(top_left + RIGHT * (match.start() + run / 2) * module + DOWN * (r + 0.5) * module)
            modules.add(rect)
    return VGroup(backing, modules)


def qr_title(qr_id):
    return _QR[qr_id]['title']


def qr_card(qr_id, height=QR_HEIGHT, corner=DR):
    """QR code with its caption above it, placed in a corner of the frame."""
    code = qr_code(qr_id, height)
    caption = Text(f'{qr_id} · {qr_title(qr_id)}', font_size=20)
    if caption.width > 4.2:
        caption.scale_to_fit_width(4.2)
    caption.next_to(code, UP, buff=0.12)
    caption.align_to(code, RIGHT if corner[0] > 0 else LEFT)
    card = VGroup(BackgroundRectangle(caption, fill_opacity=0.85, buff=0.06), caption, code)
    return card.to_corner(corner, buff=0.3)


def qr_wall(qr_ids, height=1.7):
    """All of an episode's codes in a row, captions underneath, for the closing wall."""
    cards = VGroup()
    for qr_id in qr_ids:
        code = qr_code(qr_id, height)
        caption = Text(qr_id, font_size=22).next_to(code, DOWN, buff=0.15)
        title = Text(qr_title(qr_id), font_size=16, color=SCAFFOLD).next_to(caption, DOWN, buff=0.08)
        if title.width > height + 0.6:
            title.scale_to_fit_width(height + 0.6)
        cards.add(VGroup(code, caption, title))
    cards.arrange(RIGHT, buff=0.45)
    if cards.width > 13.2:
        cards.scale_to_fit_width(13.2)
    return cards


# ---------------------------------------------------------------- code and footage

def code_panel(source, font_size=24, line_numbers=True):
    """Syntax-highlighted code on a dark rounded panel (Manim's Code mobject)."""
    return Code(code_string=source.strip('\n'), language='python', formatter_style='monokai',
                add_line_numbers=line_numbers, background='rectangle',
                background_config={'fill_color': '#1e1f1c', 'stroke_color': GREY_D, 'stroke_width': 1},
                paragraph_config={'font_size': font_size, 'font': 'Menlo'})


def code_line(code, index):
    """The text of one line (0-based) of a code_panel, for highlighting."""
    return code.code_lines[index]


def line_highlight(code, index, color=FOCUS):
    target = code_line(code, index)
    box = SurroundingRectangle(target, color=color, buff=0.03, corner_radius=0.05)
    return box.stretch_to_fit_width(code.background.width - 0.25).align_to(code.background, RIGHT).shift(LEFT * 0.1)


def footage_card(title, shots, height=6.0):
    """Placeholder for a screen recording: what to capture, never a fake interface."""
    frame = RoundedRectangle(width=height * 16 / 9, height=height, corner_radius=0.2)
    frame.set_stroke(SCAFFOLD, width=2).set_fill('#101418', 1)
    dashes = DashedVMobject(frame.copy().set_fill(opacity=0), num_dashes=80).set_stroke(SCAFFOLD, 2)
    tag = Text('SCREEN RECORDING', font_size=22, weight=BOLD, color=WARNING)
    heading = Text(title, font_size=34)
    items = VGroup(*[Text(f'• {shot}', font_size=22, color=GREY_A) for shot in shots])
    items.arrange(DOWN, aligned_edge=LEFT, buff=0.18)
    body = VGroup(tag, heading, items).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
    if body.width > frame.width - 1:
        body.scale_to_fit_width(frame.width - 1)
    body.move_to(frame)
    return VGroup(frame, dashes, body)


def browser_icon(width=2.4, height=1.6, color=SCAFFOLD):
    window = RoundedRectangle(width=width, height=height, corner_radius=0.12).set_stroke(color, 3)
    bar = Line(window.get_corner(UL) + DOWN * 0.3, window.get_corner(UR) + DOWN * 0.3).set_stroke(color, 2)
    dots = VGroup(*[Dot(radius=0.04, color=color) for _ in range(3)]).arrange(RIGHT, buff=0.08)
    dots.move_to(window.get_corner(UL) + RIGHT * 0.3 + DOWN * 0.15)
    return VGroup(window, bar, dots)


def snippet_source(path):
    """Source of a QR snippet, so on-screen code always matches what the QR opens."""
    return (SERIES / 'snippets' / path).read_text()
