"""Shared building blocks for the series' production scenes (Manim Community).

Each segment of an episode script is one Scene class. Segment timing comes from the
segment's narration: by default its word count at 145 words per minute plus any
<break/> pauses, or the measured audio length when build/narration/durations.json
exists ({"01.1": 52.3, ...}, seconds per segment). Visual beats are placed at
fractions of that length with Segment.hold_until, so re-timing to the real
ElevenLabs audio is a matter of writing durations.json and rendering again. Segment.at
places a beat where the narration says a phrase, from the character timings that
tools/narrate.py saves with each segment's audio (episode 7 on).

Render from the repository root, with TeX on the PATH for MathTex, for example:
    manim -qh video-series/production/ep01.py Segment_1_1
Set SEGMENT_LABELS=1 to burn the segment id and clock into a corner for review.
"""
import json
import os
import re
import textwrap
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
MONO = 'Menlo'
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


def phrase_seconds(episode, segment, phrase, occurrence=0):
    """When the narration reaches a phrase: from ElevenLabs' character timings (tools/narrate.py
    sidecars) when they exist, else from its word position at the estimated speaking rate.
    Matching ignores case; use the spoken text (pronunciation aliases applied)."""
    sidecar = SERIES / 'build' / 'narration' / 'audio' / f'ep{episode:02d}' / f'{segment}.json'
    alignment = json.loads(sidecar.read_text()).get('alignment') if sidecar.exists() else None
    if alignment and alignment.get('starts'):
        spoken = ''.join(alignment['characters']).lower()
        start = -1
        for _ in range(occurrence + 1):
            start = spoken.find(phrase.lower(), start + 1)
            if start < 0:
                raise ValueError(f'{segment}: narration never says {phrase!r}')
        return alignment['starts'][start]
    text = re.sub(r'<[^>]+>', ' ', narration_text(episode, segment))
    start = -1
    for _ in range(occurrence + 1):
        start = text.lower().find(phrase.lower(), start + 1)
        if start < 0:
            raise ValueError(f'{segment}: narration never says {phrase!r}')
    return len(text[:start].split()) / max(len(text.split()), 1) * narration_seconds(episode, segment)


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

    def at(self, phrase, occurrence=0, lead=0.0):
        """Wait until the narration starts saying phrase (lead seconds earlier, if given)."""
        remaining = phrase_seconds(self.EPISODE, self.SEGMENT, phrase, occurrence) - lead - self.renderer.time
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


def wrapped_text(words, max_width, font_size=20, skip=0, **kwargs):
    """Text no wider than max_width: wraps once at the comma or space nearest the middle
    (ignoring the first `skip` characters) before falling back to shrinking."""
    text = Text(words, font_size=font_size, **kwargs)
    if text.width <= max_width:
        return text
    breaks = [i for i, ch in enumerate(words) if ch in ', ' and i > skip]
    cut = min(breaks, key=lambda i: abs(i - len(words) / 2)) if breaks else len(words) // 2
    text = Text(words[:cut + 1].rstrip() + '\n' + words[cut + 1:].strip(), font_size=font_size,
                line_spacing=0.8, **kwargs)
    return text.scale_to_fit_width(max_width) if text.width > max_width else text


def qr_card(qr_id, height=QR_HEIGHT, corner=DR):
    """QR code with its caption above it, placed in a corner of the frame."""
    code = qr_code(qr_id, height)
    caption = wrapped_text(f'{qr_id} · {qr_title(qr_id)}', 4.2, font_size=20, skip=len(qr_id) + 3)
    caption.next_to(code, UP, buff=0.12)
    caption.align_to(code, RIGHT if corner[0] > 0 else LEFT)
    card = VGroup(BackgroundRectangle(caption, fill_opacity=0.85, buff=0.06), caption, code)
    return card.to_corner(corner, buff=0.3)


def qr_wall(qr_ids, height=2.0):
    """All of an episode's codes, captions underneath, for the closing wall (rows of three)."""
    cards = VGroup()
    for qr_id in qr_ids:
        code = qr_code(qr_id, height)
        caption = Text(qr_id, font_size=22).next_to(code, DOWN, buff=0.15)
        title = wrapped_text(qr_title(qr_id), height + 0.6, font_size=18, color=SCAFFOLD).next_to(caption, DOWN, buff=0.08)
        cards.add(VGroup(code, caption, title))
    if len(cards) <= 4:
        cards.arrange(RIGHT, buff=0.6, aligned_edge=UP)
    else:
        rows = [VGroup(*cards[i:i + 3]).arrange(RIGHT, buff=0.9, aligned_edge=UP) for i in range(0, len(cards), 3)]
        VGroup(*rows).arrange(DOWN, buff=0.35)
        cards.move_to(ORIGIN)
    if cards.width > 13.2:
        cards.scale_to_fit_width(13.2)
    if cards.height > 7.0:
        cards.scale_to_fit_height(7.0)
    return cards


# ---------------------------------------------------------------- outlines

def anchors_and_handles(mob, anchor_color=FOCUS, handle_color=GREY_B, anchor_radius=0.08):
    """Every cubic of a VMobject: anchor dots, handle dots and the lines joining them."""
    points = mob.get_points()
    anchors, handles = VGroup(), VGroup()
    for i in range(0, len(points), 4):
        for j in (i, i + 3):
            if not any(np.allclose(points[j], d.get_center()) for d in anchors):
                anchors.add(Dot(points[j], radius=anchor_radius, color=anchor_color))
        handles.add(Line(points[i], points[i + 1], color=handle_color, stroke_width=2),
                    Line(points[i + 3], points[i + 2], color=handle_color, stroke_width=2),
                    Dot(points[i + 1], radius=0.045, color=handle_color), Dot(points[i + 2], radius=0.045, color=handle_color))
    return anchors, handles


# ---------------------------------------------------------------- code and footage

def code_text(source, font_size=26, color=GREY_A):
    """A single line of code in the code font, without a panel."""
    return Text(source, font=MONO, font_size=font_size, color=color)


def chars(text, source, start, end=None):
    """Glyphs of a Text for source[start:end]: Text has no glyphs for whitespace."""
    end = len(source) if end is None else end
    index = len(re.sub(r'\s', '', source[:start]))
    count = len(re.sub(r'\s', '', source[start:end]))
    return VGroup(*text[index:index + count])


def find_chars(text, source, needle, occurrence=0):
    start = -1
    for _ in range(occurrence + 1):
        start = source.index(needle, start + 1)
    return chars(text, source, start, start + len(needle))


def fit(mob, width=13.0):
    """Shrink a line that would run off the frame."""
    return mob.scale_to_fit_width(width) if mob.width > width else mob


def code_panel(source, font_size=24, line_numbers=True):
    """Syntax-highlighted code on a dark rounded panel (Manim's Code mobject)."""
    return Code(code_string=source.strip('\n'), language='python', formatter_style='monokai',
                add_line_numbers=line_numbers, background='rectangle',
                background_config={'fill_color': '#1e1f1c', 'stroke_color': GREY_D, 'stroke_width': 1},
                paragraph_config={'font_size': font_size, 'font': MONO})


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
    tag = Text('SCREEN RECORDING', font_size=26, weight=BOLD, color=WARNING)
    heading = Text(title, font_size=44)
    items = VGroup(*[Text(f'• {shot}', font_size=28, color=GREY_A) for shot in shots])
    items.arrange(DOWN, aligned_edge=LEFT, buff=0.28)
    body = VGroup(tag, heading, items).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
    body.scale_to_fit_width(frame.width - 1.2)
    if body.height > frame.height - 1:
        body.scale_to_fit_height(frame.height - 1)
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


def snippet_lines(path, first, last):
    """Lines first..last (1-based, inclusive) of a snippet, dedented, for an excerpt panel."""
    lines = snippet_source(path).splitlines()[first - 1:last]
    return textwrap.dedent('\n'.join(lines))


def stage(width=5.6):
    floor = Line(LEFT * width / 2, RIGHT * width / 2, color=SCAFFOLD, stroke_width=4).shift(DOWN * 1.6)
    left = Rectangle(width=0.5, height=3.6).set_fill(DARK_BROWN, 1).set_stroke(width=0)
    right = left.copy()
    left.next_to(floor.get_start(), UP, buff=0).shift(RIGHT * 0.25)
    right.next_to(floor.get_end(), UP, buff=0).shift(LEFT * 0.25)
    return VGroup(floor, left, right)


def clock_icon(radius=0.45):
    face = Circle(radius=radius, color=GREY_A, stroke_width=3)
    hand = Line(ORIGIN, UP * radius * 0.8, color=FOCUS, stroke_width=4)
    return VGroup(face, hand)


# ---------------------------------------------------------------- names

def sticky_note(letter):
    paper = Square(0.6).set_fill('#f3d564', 1).set_stroke(width=0).rotate(0.08)
    return VGroup(paper, Text(letter, font=MONO, font_size=32, color=BLACK).move_to(paper))


def attach(note, target, corner):
    """Keep a note beside a corner of its object, tied on with a string."""
    note.add_updater(lambda m: m.move_to(target.get_corner(corner) + corner * 0.75))
    string = always_redraw(lambda: Line(note.get_center(), target.get_corner(corner), color=GREY_B, stroke_width=2))
    return string
