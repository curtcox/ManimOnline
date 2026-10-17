"""Episode 9 · From sketch to shareable. One Scene per script segment.

    python3 video-series/production/render.py 9 [-ql] [segment ...]

Shot ids in comments ([V9.4c] ...) refer to episodes/09-from-sketch-to-shareable.md.
This episode is a tour of the editor. 9.2 is a footage card; elsewhere the segments explain
each feature with diagrams (never imitations of the interface), and the editor recordings
listed in the script can be cut in over them in the edit.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403

SCENES_SNIPPET = 'ep09/01-several-scenes.py'
EXPORT_SNIPPET = 'ep09/02-export-me.py'
DOT_SNIPPET = 'ep09/03-pipeline.dot'
MODL_SNIPPET = 'ep09/04-workflow.modl'
RUNAWAY_SNIPPET = 'ep09/05-runaway.py'

# What the Share button makes for q09-01 with Middle chosen: ShareLinks.build (src/share-links.js)
# with LZString.compressToEncodedURIComponent, run on the deployed site.
SHARE_PREFIX = 'https://curtcox.github.io/ManimOnline/?scene=Middle&compressed='
SHARE_PAYLOAD = (
    'GYJw9gtgBBCGB2BLayAOYQBcoCoBQBAxgDawDOZUAkvJuABQDKhApvCwJQBceUfUAExbAohMPDJ0AroUz0yLYsG69%2BahUoB0q'
    'UgE96AdRCJMLegBUWADzkAiZmxZRxLLtVrhbHb6rV8NwJoA7rAm9BwEeCTklACyiAICxGYO7CpqQiJiEtKy8orKPH78ZAAWsKhO'
    'ALxQjACOUrAgZmLEGFUAQgAyAKoAohHF-gXaevQAws2wpvLllT5DUAGjsPplFSyaCMjTm%2BCYu-QAClRQAPRQACwcmgqYAPrA'
    'iMTE9N39ADTOqLCEJrpVAAMmgArAshssQmEIkRSBQoAB5KR0MBMVhpIr8TKicSSEAyOQBdIQkY6Vb0ABisCENAs1jsqScmFKzV'
    'ciORni%2BrXaAE0%2Bl0ugiDBwvmVEMBMFUekdwcVIaE5BEgA')
# HashBin CIDs (cidFor in tools/qr-links.mjs): q09-01 as published, and the same document with
# Square(color=RED) in Middle.
CID = 'AAAAAAJZutWN3tGb9FUTpi3ezwQ4-Mnb9wKlNLKjVqI8uB4UPcJXJfO9_xLDGayFp7Q9aJwxOXD-RDxyf_XX5tWXZ_9qIA'
CID_EDITED = 'AAAAAAJYjWu22a_s3TsKDqfgcRFZMA1O0cCmKdcQ8V_sBrHWSlWHFsb8LCZ-aWzG2U2BlXYGRINoM83Z8i-x3gJ3re9RKg'
SITE = 'https://curtcox.github.io/ManimOnline/'

# q09-03 laid out by `dot -Tplain` and `neato -Tplain` (Graphviz 16.1), in inches:
# name: label, width, height, dot centre, neato centre.
GRAPH_NODES = {
    'editor': ('Code editor', 1.1076, 0.5, (0.55382, 1.0417), (0.55382, 1.165)),
    'detector': ('Language detector', 1.6181, 0.5, (2.4306, 1.0417), (1.6253, 1.3846)),
    'worker': ('Python worker\n(Pyodide)', 1.3368, 0.56944, (5.033, 1.8611), (2.7029, 1.6006)),
    'frames': ('Frame snapshots', 1.4931, 0.5, (7.0243, 1.8611), (3.7043, 1.8542)),
    'player': ('SVG player', 1.1181, 0.5, (8.8438, 1.8611), (4.6752, 2.1391)),
    'graphviz': ('Graphviz\n(WebAssembly)', 1.4618, 0.56944, (5.033, 1.0417), (1.174, 2.4249)),
    'modl': ('modl editor', 1.1076, 0.5, (5.033, 0.25), (1.6307, 0.25)),
}
GRAPH_EDGES = [('editor', 'detector', ''), ('detector', 'worker', 'Manim'), ('detector', 'graphviz', 'DOT'),
               ('detector', 'modl', 'modl'), ('worker', 'frames', ''), ('frames', 'player', '')]
DOT_SIZE, NEATO_SIZE = (9.4028, 2.1458), (5.2343, 2.7096)


# ---------------------------------------------------------------- small pieces

def note(words, font_size=24, color=SCAFFOLD):
    return Text(words, font_size=font_size, color=color)


def backed(mob, opacity=0.85, buff=0.12):
    return VGroup(BackgroundRectangle(mob, fill_opacity=opacity, buff=buff), mob)


def check_mark(size=0.5, color=AFTER):
    return VMobject().set_points_as_corners([[-0.5, 0, 0], [-0.15, -0.4, 0], [0.55, 0.45, 0]]).scale(size).set_stroke(color, 8)


def cross_mark(size=0.35, color=WARNING):
    return VGroup(Line(UL, DR), Line(UR, DL)).scale(size).set_stroke(color, 8)


def box(width, height, color=GREY_B, fill='#15181d', radius=0.15, stroke=3):
    return RoundedRectangle(width=width, height=height, corner_radius=radius).set_stroke(color, stroke).set_fill(fill, 1)


def labelled_box(words, width=2.3, height=0.9, font_size=30, color=GREY_B):
    frame = box(width, height, color, radius=0.2)
    return VGroup(frame, Text(words, font_size=font_size).move_to(frame))


def motif(labels):
    """The series' loop: edit → render → preview, joined back to edit (and share beside it)."""
    boxes = VGroup(*[labelled_box(label) for label in labels]).arrange(RIGHT, buff=0.75)
    arrows = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.08, color=GREY_B, stroke_width=4,
                            max_tip_length_to_length_ratio=0.3) for a, b in zip(boxes, boxes[1:])])
    back = CurvedArrow(boxes[2].get_bottom() + DOWN * 0.08, boxes[0].get_bottom() + DOWN * 0.08,
                       angle=-0.9, color=GREY_B, stroke_width=4)
    return boxes, arrows, back


def chip(words, color=GREY_B, font_size=24, mono=False):
    text = Text(words, font_size=font_size, font=MONO) if mono else Text(words, font_size=font_size)
    frame = RoundedRectangle(width=text.width + 0.4, height=text.height + 0.3, corner_radius=0.12)
    frame.set_stroke(color, 2).set_fill('#15181d', 1)
    return VGroup(frame, text.move_to(frame))


def file_icon(kind, color=GREY_B, width=0.95, height=1.2):
    corner = 0.25
    page = Polygon([-width / 2, height / 2, 0], [width / 2 - corner, height / 2, 0], [width / 2, height / 2 - corner, 0],
                   [width / 2, -height / 2, 0], [-width / 2, -height / 2, 0])
    page.set_stroke(color, 3).set_fill('#15181d', 1)
    fold = VMobject().set_points_as_corners([[width / 2 - corner, height / 2, 0], [width / 2 - corner, height / 2 - corner, 0],
                                             [width / 2, height / 2 - corner, 0]]).set_stroke(color, 2)
    label = Text(kind, font_size=22, weight=BOLD, color=color)
    label.scale_to_fit_width(min(label.width, width - 0.2)).move_to(page)
    return VGroup(page, fold, label)


def mono_lines(text, width, font_size=20, color=GREY_A):
    """A long string (a link, a CID) broken into lines of at most `width` characters."""
    rows = [text[i:i + width] for i in range(0, len(text), width)]
    return VGroup(*[Text(row, font=MONO, font_size=font_size, color=color) for row in rows]).arrange(DOWN, aligned_edge=LEFT, buff=0.12)


def source_panel(source, language, font_size=20):
    """A code panel for a snippet in another language (Graphviz DOT, modl)."""
    return Code(code_string=source.strip('\n'), language=language, formatter_style='monokai',
                add_line_numbers=False, background='rectangle',
                background_config={'fill_color': '#1e1f1c', 'stroke_color': GREY_D, 'stroke_width': 1},
                paragraph_config={'font_size': font_size, 'font': MONO})


def wifi_icon(color=GREY_A):
    arcs = VGroup(*[Arc(radius=r, start_angle=PI / 4, angle=PI / 2).set_stroke(color, 6) for r in (0.25, 0.5, 0.75)])
    return VGroup(arcs, Dot(radius=0.07, color=color))


def cloud(color=GREY_B):
    parts = [Circle(radius=0.45).shift(LEFT * 0.45), Circle(radius=0.6).shift(UP * 0.2 + RIGHT * 0.15),
             Circle(radius=0.4).shift(RIGHT * 0.7), Rectangle(width=1.6, height=0.6).shift(DOWN * 0.15)]
    shape = parts[0]
    for part in parts[1:]:
        shape = Union(shape, part)
    return shape.set_stroke(color, 3).set_fill('#15181d', 1)


def pointer():
    arrow = Polygon([0, 0, 0], [0, -0.55, 0], [0.13, -0.42, 0], [0.24, -0.66, 0], [0.33, -0.62, 0],
                    [0.22, -0.39, 0], [0.4, -0.39, 0])
    return arrow.set_fill(WHITE, 1).set_stroke(BLACK, 2)


def stage_frame(width, color=GREY_B):
    """A small screen standing in for a scene's 16:9 frame."""
    return box(width, width * 9 / 16, color, fill='#000000', radius=0.08, stroke=2)


def on_stage(mob, frame):
    """Shrink a mobject laid out in scene coordinates onto a stage_frame."""
    return mob.scale(frame.width / config.frame_width, about_point=ORIGIN).shift(frame.get_center())


# ---------------------------------------------------------------- 9.1

def cut_tile():
    return box(4.0, 2.25, GREY_B, fill='#0b0d10', radius=0.12, stroke=2)


class Segment_9_1(Segment):
    """Cold open: now what?"""
    EPISODE, SEGMENT = 9, '9.1'

    def construct(self):
        # [V9.1a] the loop, with room for a fourth box
        boxes, arrows, back = motif(['edit', 'render', 'preview', 'share'])
        loop = VGroup(boxes, arrows, back).to_edge(UP, buff=0.5)
        self.play(LaggedStart(*[FadeIn(m) for m in (boxes[0], arrows[0], boxes[1], arrows[1], boxes[2])], lag_ratio=0.25),
                  run_time=1.6)
        self.play(Create(back))

        # [V9.1b] quick cuts from the series, each shrinking onto a pile
        self.at('learned to draw')
        pile = []
        spot = DOWN * 1.0

        def show(*content):
            tile = cut_tile()
            group = VGroup(tile, *content)
            group.scale(1.25).move_to(spot)
            return group

        def to_pile(group):
            k = len(pile)
            pile.append(group)
            target = [-4.7 + 0.15 * k, -2.3 + 0.12 * k, 0]
            return group.animate.scale(0.36).move_to(target).rotate((-1) ** k * 0.06)

        square = Square(1.3, color=BLUE)
        circle = Circle(radius=0.75, color=BLUE).set_fill(BLUE, 0.5)
        tile = show(square)
        circle.scale(1.25).move_to(square)
        self.play(FadeIn(tile[0]), Create(square), run_time=0.6)
        self.play(Transform(square, circle), run_time=0.8)
        self.play(to_pile(tile), run_time=0.5)

        arc = Arc(radius=1.0, start_angle=PI, angle=-PI).shift(DOWN * 0.4).set_stroke(GREY_B, 2)
        dot = Dot(arc.get_start(), color=YELLOW, radius=0.12)
        tile = show(arc, dot)
        self.play(FadeIn(tile[0]), FadeIn(arc), FadeIn(dot), run_time=0.4)
        self.play(MoveAlongPath(dot, arc), run_time=0.9)
        self.play(to_pile(tile), run_time=0.5)

        formula = MathTex(r'a^2 + b^2 = c^2', font_size=54)
        tile = show(formula)
        self.play(FadeIn(tile[0]), Write(formula), run_time=1.0)
        self.play(to_pile(tile), run_time=0.5)

        axes = Axes(x_range=[-2, 2, 1], y_range=[0, 4, 1], x_length=3.2, y_length=1.7,
                    axis_config={'stroke_width': 2, 'include_ticks': False})
        graph = axes.plot(lambda x: x * x, color=GREEN)
        tile = show(axes, graph)
        self.play(FadeIn(tile[0]), FadeIn(axes), run_time=0.3)
        self.play(Create(graph), run_time=0.8)
        self.play(to_pile(tile), run_time=0.5)

        s = 0.55
        top = Polygon([0, s, 0], [s * 1.7, s * 1.5, 0], [0, s * 2, 0], [-s * 1.7, s * 1.5, 0]).set_fill(BLUE_B, 1)
        left = Polygon([-s * 1.7, s * 1.5, 0], [0, s, 0], [0, -s * 1.2, 0], [-s * 1.7, -s * 0.7, 0]).set_fill(BLUE_D, 1)
        right = Polygon([s * 1.7, s * 1.5, 0], [0, s, 0], [0, -s * 1.2, 0], [s * 1.7, -s * 0.7, 0]).set_fill(BLUE_E, 1)
        cube = VGroup(top, left, right).set_stroke(WHITE, 1.5).move_to(ORIGIN)
        tile = show(cube)
        self.play(FadeIn(tile[0]), DrawBorderThenFill(cube), run_time=0.8)
        self.play(Rotate(cube, PI / 8), cube.animate.scale(1.15), run_time=0.7)
        self.play(to_pile(tile), run_time=0.5)

        # So: now what? The fourth box, share, joins the loop.
        self.at('now what')
        question = Text('?', font_size=96, color=FOCUS).next_to(VGroup(*pile), UP, buff=0.2)
        self.play(FadeIn(question, scale=0.5), FadeIn(boxes[3], shift=LEFT * 0.3), GrowArrow(arrows[2]))
        boxes[3][0].set_stroke(FOCUS)
        wants = [('keep your work', 'keep it'), ('real video file', 'a video file'),
                 ('show it to a friend', 'show a friend'), ('find inspiration', 'find ideas')]
        items = VGroup(*[Text(words, font_size=26, color=GREY_A) for _, words in wants])
        items.arrange(DOWN, aligned_edge=LEFT, buff=0.3).next_to(boxes[3], DOWN, buff=0.55).align_to(boxes[3], LEFT)
        for (phrase, _), item in zip(wants, items):
            self.at(phrase)
            self.play(FadeIn(item, shift=RIGHT * 0.2), run_time=0.5)

        self.at('a practical tour')
        self.play(*[Indicate(b, color=FOCUS, scale_factor=1.06) for b in boxes], run_time=1.5)
        self.finish()


# ---------------------------------------------------------------- 9.2

class Segment_9_2(Segment):
    """The gallery (screen recording)."""
    EPISODE, SEGMENT = 9, '9.2'

    def construct(self):
        # [V9.2a-d] the recording: the gallery opens in a new tab, Play preview, search and language
        # filter, Load in editor, an edit, and a reload that keeps it
        screen = footage_screen(6.0).to_edge(LEFT, buff=0.3)
        address = site_address().next_to(screen, RIGHT, buff=0.4).align_to(screen, UP)
        self.footage_in(screen, 'V9.2', FadeIn(address))
        self.finish()
        self.wait(1.0)   # the reloaded page renders the kept edit


# ---------------------------------------------------------------- 9.3

def mini_intro(frame):
    return on_stage(Text('Scene one: Intro'), frame)


def mini_outro(frame):
    return on_stage(Text('Scene three: Outro', color=YELLOW), frame)


class Segment_9_3(Segment):
    """Several scenes in one file (q09-01)."""
    EPISODE, SEGMENT = 9, '9.3'

    def construct(self):
        # [V9.3a] three classes; the chosen scene plays on the right
        parts = [snippet_lines(SCENES_SNIPPET, a, b) for a, b in ((4, 7), (10, 15), (18, 21))]
        panels = VGroup(*[code_panel(p, font_size=26, line_numbers=False) for p in parts])
        panels.arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        fit(panels, 7.4)
        if panels.height > 7.4:
            panels.scale_to_fit_height(7.4)
        panels.to_edge(LEFT, buff=0.4)
        frame = stage_frame(5.2).move_to([4.0, 1.75, 0])
        caption = note('scene to render', 22).next_to(frame, DOWN, buff=0.35).align_to(frame, LEFT)
        field = box(2.6, 0.55, GREY_B, radius=0.08, stroke=2).next_to(caption, RIGHT, buff=0.25)
        value = Text('Middle', font=MONO, font_size=24).move_to(field)
        self.play(LaggedStart(*[FadeIn(p, shift=RIGHT * 0.2) for p in panels], lag_ratio=0.2), FadeIn(frame), run_time=1.5)
        mark = SurroundingRectangle(panels[1], color=FOCUS, buff=0.06, corner_radius=0.08)
        self.play(FadeIn(caption), FadeIn(field), FadeIn(value), Create(mark))
        shape = on_stage(Square(color=BLUE), frame)
        self.play(Create(shape))
        self.play(shape.animate.rotate(PI / 4).set_fill(BLUE, opacity=0.5))

        # [V9.3b] an empty field renders the first scene
        self.at('Leave it empty')
        empty = Text('First scene', font_size=22, color=DIM, slant=ITALIC).move_to(field)
        self.play(FadeOut(value), FadeIn(empty), FadeOut(shape), mark.animate.become(
            SurroundingRectangle(panels[0], color=FOCUS, buff=0.06, corner_radius=0.08)))
        intro = mini_intro(frame)
        self.play(Write(intro))

        # [V9.3c] typing suggests the scene names from the last render
        self.at('Start typing')
        typed = Text('O', font=MONO, font_size=24).move_to(field).align_to(field, LEFT).shift(RIGHT * 0.2)
        names = VGroup(*[Text(n, font=MONO, font_size=22) for n in ('Intro', 'Middle', 'Outro')])
        names.arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        menu = VGroup(box(2.6, names.height + 0.4, GREY_B, radius=0.06, stroke=2), names)
        names.move_to(menu[0]).align_to(menu[0], LEFT).shift(RIGHT * 0.25)
        menu.next_to(field, DOWN, buff=0.08)
        self.play(FadeOut(empty), FadeIn(typed), FadeIn(menu, shift=DOWN * 0.1))
        pick = SurroundingRectangle(names[2], color=FOCUS, buff=0.06)
        self.play(Create(pick))
        chosen = Text('Outro', font=MONO, font_size=24).move_to(field)
        outro = mini_outro(frame)
        self.play(FadeOut(VGroup(menu, pick, typed)), FadeIn(chosen), FadeOut(intro),
                  mark.animate.become(SurroundingRectangle(panels[2], color=FOCUS, buff=0.06, corner_radius=0.08)))
        self.play(FadeIn(outro, shift=UP * frame.width / config.frame_width))

        # The QR code opens with Middle chosen: the choice is saved with the source.
        self.at('This code opens with Middle')
        middle = Text('Middle', font=MONO, font_size=24).move_to(field)
        shape = on_stage(Square(color=BLUE), frame)
        card = qr_card('q09-01')
        self.play(FadeOut(chosen), FadeIn(middle), FadeOut(outro), FadeIn(card, shift=UP * 0.2),
                  mark.animate.become(SurroundingRectangle(panels[1], color=FOCUS, buff=0.06, corner_radius=0.08)))
        self.play(Create(shape))
        self.play(shape.animate.rotate(PI / 4).set_fill(BLUE, opacity=0.5))
        self.wait(6.2)
        self.finish()


# ---------------------------------------------------------------- 9.4

class Segment_9_4(Segment):
    """Rendering, and its limits (q09-05)."""
    EPISODE, SEGMENT = 9, '9.4'

    def construct(self):
        # [V9.4a] keystrokes, a one-second pause, then a render
        axis = Line(LEFT * 5.5, RIGHT * 2.5, color=GREY_D, stroke_width=3).shift(UP * 1.6)
        typing = note('typing', 24).next_to(axis, LEFT, buff=0.25)
        self.play(Create(axis), FadeIn(typing))
        times = [0.0, 0.35, 0.6, 0.8, 1.3, 1.5, 1.75, 2.3, 2.5, 2.7]
        keys = VGroup(*[Line(DOWN * 0.22, UP * 0.22, color=GREY_A, stroke_width=5).move_to(axis.point_from_proportion(0.03 + t / 3.1))
                        for t in times])
        last = 0.0
        for t, key in zip(times, keys):
            if t > last:
                self.wait(t - last)
            last = t
            self.add(key)
        ring = Circle(radius=0.32, color=FOCUS, stroke_width=6).move_to(axis.get_end() + RIGHT * 0.9)
        ring.rotate(PI / 2).flip(RIGHT)
        second = note('1 second', 22, FOCUS).next_to(ring, UP, buff=0.2)
        gap = Brace(Line(keys[-1].get_center(), ring.get_left()), DOWN, color=GREY_B)
        self.play(Create(ring), FadeIn(second), FadeIn(gap), run_time=1.0, rate_func=linear)
        rendered = VGroup(note('render', 26, AFTER), check_mark(0.45)).arrange(RIGHT, buff=0.2).next_to(ring, RIGHT, buff=0.35)
        self.play(FadeIn(rendered[0]), Create(rendered[1]), ring.animate.set_color(AFTER))

        # [V9.4b] Render animation starts at once (and retries after an error)
        self.at('If you don')
        button = chip('Render animation', AFTER, 26).move_to([-1.5, -0.6, 0])
        now = note('starts now, no waiting', 24, GREY_A).next_to(button, RIGHT, buff=0.4)
        self.play(FadeIn(button), FadeIn(now, shift=RIGHT * 0.2))
        self.at('retry after an error')
        retry = note('also: try again after an error', 24, GREY_A).next_to(now, DOWN, buff=0.3).align_to(now, LEFT)
        self.play(FadeIn(retry, shift=RIGHT * 0.2))

        # [V9.4c] a loop that never ends: the page stays responsive; Cancel render stops the worker
        self.at('But what if')
        self.play(FadeOut(VGroup(axis, typing, keys, ring, second, gap, rendered, button, now, retry)))
        code = code_panel(snippet_lines(RUNAWAY_SNIPPET, 7, 8), font_size=30, line_numbers=False)
        fit(code, 12.6).to_edge(UP, buff=0.4)
        self.play(FadeIn(code))
        highlight = line_highlight(code, 0)
        self.play(Create(highlight))

        page = box(4.4, 2.2).move_to([-3.6, 0.35, 0])
        worker = box(4.0, 2.2).move_to([1.4, 0.35, 0])
        page_label = note('the page: editor and preview', 22, GREY_A).next_to(page, UP, buff=0.12)
        worker_label = note('Python, running separately', 22, GREY_A).next_to(worker, UP, buff=0.12)
        spinner = Arc(radius=0.45, angle=1.5 * PI, color=FOCUS, stroke_width=7).move_to(worker)
        spinner.add_updater(lambda m, dt: m.rotate(-5 * dt))
        looping = code_text('while True: pass', 20, FOCUS).next_to(spinner, DOWN, buff=0.2)
        self.play(FadeIn(page), FadeIn(page_label), FadeIn(worker), FadeIn(worker_label), FadeIn(spinner), FadeIn(looping))

        self.at('Scan it if you like')
        card = qr_card('q09-05')
        self.play(FadeIn(card, shift=UP * 0.2))

        self.at('stays perfectly responsive')
        typed_source = 'shape = Circle()'
        typed = code_text(typed_source, 24, GREY_A).move_to(page).shift(LEFT * 0.3)
        start = self.renderer.time
        typed.add_updater(lambda m: [glyph.set_opacity(1 if self.renderer.time - start > 0.25 * i else 0)
                                     for i, glyph in enumerate(m)])
        caret = Line(DOWN * 0.2, UP * 0.2, color=WHITE, stroke_width=3)
        caret.add_updater(lambda m: m.next_to(typed[min(len(typed) - 1, int((self.renderer.time - start) / 0.25))], RIGHT, buff=0.05)
                          .set_opacity(1 if int(self.renderer.time * 2.5) % 2 == 0 else 0))
        self.add(typed, caret)
        responsive = note('still responds', 22, AFTER).next_to(page, DOWN, buff=0.2)
        self.play(FadeIn(responsive))

        self.at('Press Cancel render')
        cancel = chip('Cancel render', WARNING, 24).next_to(worker, DOWN, buff=0.25)
        self.play(FadeIn(cancel))
        spinner.clear_updaters()
        stopped = VGroup(cross_mark(0.3), note('stopped', 26, WARNING)).arrange(RIGHT, buff=0.25).move_to(worker)
        self.play(worker[0].animate.set_stroke(WARNING), FadeOut(spinner), FadeOut(looping), FadeIn(stopped))

        self.at('after ninety seconds')
        clock = clock_icon(0.35).next_to(worker, RIGHT, buff=0.35)
        ninety = note('90 s', 26, GREY_A).next_to(clock, DOWN, buff=0.12)
        self.play(FadeIn(clock), FadeIn(ninety), Rotate(clock[1], -TAU, about_point=clock[0].get_center()), run_time=1.5)

        # [V9.4d] the limits
        self.at('There are a few other limits')
        typed.clear_updaters()
        caret.clear_updaters()
        self.play(FadeOut(VGroup(code, highlight, page, page_label, worker, worker_label, typed, caret, responsive,
                                 cancel, stopped, clock, ninety, card)))
        lines = VGroup(*[Text(words, font_size=32) for words in (
            'Previews: 15 frames per second',
            'Up to 120 seconds (1,800 frames) per preview',
            'Each render must finish within 90 seconds')]).arrange(DOWN, aligned_edge=LEFT, buff=0.45)
        title = Text('Limits', font_size=40, color=FOCUS)
        body = VGroup(title, lines).arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        panel = box(body.width + 1.0, body.height + 0.9).move_to(body)
        VGroup(panel, body).move_to(UP * 0.4)
        self.play(FadeIn(panel), FadeIn(title))
        for phrase, line in zip(('Previews run at', 'A single preview', None), lines):
            if phrase:
                self.at(phrase)
            self.play(FadeIn(line, shift=RIGHT * 0.2), run_time=0.6)
        self.at('split them into several scenes')
        split = note('longer videos: several scenes', 26, GREY_A).next_to(panel, DOWN, buff=0.4)
        self.play(FadeIn(split))
        self.at('Episode ten')
        ten = note('how it works: episode 10', 26, FOCUS).next_to(split, DOWN, buff=0.3)
        self.play(FadeIn(ten, shift=UP * 0.2))
        self.finish()


# ---------------------------------------------------------------- 9.5

def export_stars():
    """q09-02's three polygrams."""
    return VGroup(*[
        RegularPolygram(n, density=2, radius=1.1).set_stroke(color, width=6)
        for n, color in zip([5, 7, 9], [BLUE, YELLOW, RED])
    ]).arrange(RIGHT, buff=0.8)


def lens(radius=1.35):
    return Circle(radius=radius).set_stroke(GREY_A, 4).set_fill('#000000', 1)


class Segment_9_5(Segment):
    """Exporting pictures and videos (q09-02)."""
    EPISODE, SEGMENT = 9, '9.5'

    def construct(self):
        # [V9.5a] q09-02 plays
        card = qr_card('q09-02')
        self.add(card)
        stars = export_stars()
        self.play(LaggedStart(*[Create(s) for s in stars], lag_ratio=0.3), run_time=2)
        self.play(*[Rotate(s, TAU / n) for s, n in zip(stars, [5, 7, 9])], run_time=2)
        self.play(stars.animate.set_fill(opacity=0.4))
        caption = Text('Export: MP4 video', font_size=36).to_edge(DOWN)
        self.play(Write(caption))
        self.wait(2.0)

        # [V9.5b] the four exports
        kinds = [('SVG', 'SVG frame', BLUE), ('PNG', 'PNG frame', TEAL), ('MP4', 'MP4 video', FOCUS), ('WebM', 'WebM video', ORANGE)]
        icons = VGroup()
        for kind, words, color in kinds:
            icon = file_icon(kind, color)
            icons.add(VGroup(icon, note(words, 22, GREY_A).next_to(icon, DOWN, buff=0.15)))
        icons.arrange(RIGHT, buff=1.1).to_edge(UP, buff=0.4)
        self.play(FadeOut(card), FadeOut(caption), stars.animate.scale(0.55).move_to(DOWN * 0.2),
                  LaggedStart(*[FadeIn(i, shift=DOWN * 0.2) for i in icons], lag_ratio=0.15), run_time=1.5)

        # [V9.5c] SVG: shapes, sharp at any size; PNG: pixels
        self.at('S V G frame')
        self.play(Indicate(icons[0], color=BLUE))
        left, right = lens().move_to([-3.8, -1.5, 0]), lens().move_to([3.8, -1.5, 0])
        sharp = Line(left.get_center() + DL * 0.75, left.get_center() + UR * 0.75, color=BLUE, stroke_width=26)
        self.play(stars.animate.scale(0.8).move_to(UP * 1.1), FadeIn(left), Create(sharp))
        vector = note('S V G: shapes, sharp at any size', 24, BLUE).next_to(left, DOWN, buff=0.2)
        self.play(FadeIn(vector))
        self.at('perfect for slides')
        uses = note('slides · posters · blog posts', 24, GREY_A).next_to(stars, DOWN, buff=0.35)
        self.play(FadeIn(uses))
        self.at('P N G frame')
        self.play(Indicate(icons[1], color=TEAL))
        cell = 0.18
        pixels = VGroup()
        for i in range(-7, 8):
            for j in range(-7, 8):
                if abs(i - j) <= 1 and i * i + j * j <= 45:
                    pixels.add(Square(cell).set_fill(TEAL, 1).set_stroke(width=0).move_to(right.get_center() + RIGHT * i * cell + UP * j * cell))
        raster = note('PNG: a grid of pixels', 24, TEAL).next_to(right, DOWN, buff=0.2)
        self.play(FadeIn(right), FadeIn(pixels, lag_ratio=0.02), FadeIn(raster), run_time=1.2)

        # [V9.5d] videos are encoded in the browser, from frames already computed
        self.at('MP4 and web em')
        self.play(FadeOut(VGroup(left, sharp, vector, right, pixels, raster, uses, stars)),
                  Indicate(icons[2], color=FOCUS), Indicate(icons[3], color=ORANGE))
        browser = browser_icon(9.0, 3.6, GREY_B).move_to(DOWN * 0.9)
        inside = note('your browser', 22, GREY_B).next_to(browser[1], DOWN, buff=0.1).align_to(browser, LEFT).shift(RIGHT * 0.3)
        strip = VGroup()
        for k in range(5):
            frame = box(1.0, 0.65, GREY_B, fill='#000000', radius=0.05, stroke=2)
            star = RegularPolygram(5, density=2, radius=0.25).set_stroke(BLUE, 3).rotate(k * TAU / 25).move_to(frame)
            strip.add(VGroup(frame, star))
        strip.arrange(RIGHT, buff=0.12).move_to(browser).shift(LEFT * 2.0 + DOWN * 0.2)
        video = file_icon('MP4', FOCUS).next_to(strip, RIGHT, buff=2.0)
        encode = Arrow(strip.get_right(), video.get_left(), buff=0.15, color=FOCUS, stroke_width=5)
        encoding = note('encoded here', 22, FOCUS).next_to(encode, DOWN, buff=0.15)
        self.play(FadeIn(browser), FadeIn(inside))
        self.at('from the frames it already computed')
        self.play(LaggedStart(*[FadeIn(f) for f in strip], lag_ratio=0.15), run_time=1.0)
        self.play(GrowArrow(encode), FadeIn(encoding), FadeIn(video))
        self.at('Nothing is uploaded')
        sky = cloud().scale(0.7).next_to(browser, UP, buff=0.1).shift(RIGHT * 3.4)
        nope = cross_mark(0.3).move_to(sky)
        self.play(FadeIn(sky), Create(nope))
        self.at('built-in video encoding')
        needs = note('needs a browser that can encode video', 24, GREY_A).next_to(browser, DOWN, buff=0.2)
        self.play(FadeIn(needs))

        # 15 frames per second, the preview's rate; this series is 60, made with full Manim
        self.at('Keep in mind')
        self.play(FadeOut(VGroup(browser, inside, strip, video, encode, encoding, sky, nope, needs)))
        rows = VGroup()
        clock = ValueTracker(0)
        for fps, color in ((15, FOCUS), (60, AFTER)):
            track = Line(LEFT * 4, RIGHT * 4, color=GREY_D, stroke_width=3)
            label = note(f'{fps} fps', 28, color).next_to(track, LEFT, buff=0.4)
            dot = Dot(radius=0.16, color=color)
            dot.add_updater(lambda m, fps=fps, track=track: m.move_to(
                track.point_from_proportion(min(1.0, math.floor(clock.get_value() * fps) / fps / 2))))
            rows.add(VGroup(track, label, dot))
        rows.arrange(DOWN, buff=1.0).move_to(DOWN * 0.6)
        self.play(FadeIn(rows))
        self.play(clock.animate.set_value(2), run_time=2, rate_func=linear)
        self.at('sharing an idea quickly')
        quick = note('the preview, and its videos', 24, FOCUS).next_to(rows[0], UP, buff=0.25)
        self.play(FadeIn(quick), clock.animate.set_value(0), run_time=0.5)
        self.play(clock.animate.set_value(2), run_time=2, rate_func=linear)
        self.at('sixty-frames-per-second')
        series = note('this series: full Manim', 24, AFTER).next_to(rows[1], DOWN, buff=0.3)
        self.play(FadeIn(series), clock.animate.set_value(0), run_time=0.5)
        self.play(clock.animate.set_value(2), run_time=2, rate_func=linear)
        self.finish()


# ---------------------------------------------------------------- 9.6

def share_link():
    """The real link, the address part first, then the compressed code (64 characters a line)."""
    head = Text(SHARE_PREFIX, font=MONO, font_size=18, color=GREY_A)
    body = mono_lines(SHARE_PAYLOAD, 64, 18, GREY_A)
    return VGroup(head, body).arrange(DOWN, aligned_edge=LEFT, buff=0.12)


class Segment_9_6(Segment):
    """Sharing a link."""
    EPISODE, SEGMENT = 9, '9.6'

    def construct(self):
        # [V9.6a] Share makes a link
        source = file_icon('.py', BLUE).move_to([-5.6, 2.5, 0])
        name = note('01-several-scenes.py\n495 characters', 20, GREY_A).next_to(source, DOWN, buff=0.15)
        self.play(FadeIn(source), FadeIn(name))
        self.at('It produces a link')
        link = share_link().move_to([1.4, 0.6, 0])
        share = Arrow(source.get_right(), link.get_left() + UP * 1.6, buff=0.2, color=GREY_B, stroke_width=4)
        self.play(GrowArrow(share), FadeIn(link, lag_ratio=0.05), run_time=1.5)

        # [V9.6b] the code is in the link
        self.at('contains your entire program')
        head, body = link
        code_glyphs = VGroup(*body)
        code_box = SurroundingRectangle(body, color=FOCUS, buff=0.12)
        code_tag = note('your code, compressed', 26, FOCUS).next_to(code_box, DOWN, buff=0.2)
        self.play(code_glyphs.animate.set_color(FOCUS), Create(code_box), FadeIn(code_tag))
        self.at('along with your scene choice')
        scene_part = find_chars(head, SHARE_PREFIX, 'scene=Middle')
        scene_tag = note('your scene choice', 24, AFTER).next_to(head, UP, buff=0.3).shift(RIGHT * 0.5)
        self.play(scene_part.animate.set_color(AFTER), FadeIn(scene_tag, shift=DOWN * 0.1))
        self.at('renderer settings')
        settings = note('(and the renderer settings)', 22, GREY_B).next_to(scene_tag, UP, buff=0.12)
        self.play(FadeIn(settings))

        # nothing stored; longer programs make longer links
        self.at('nothing is stored on a server')
        self.play(FadeOut(VGroup(share, source, name, settings, scene_tag)),
                  VGroup(link, code_box, code_tag).animate.scale(0.7).to_edge(UP, buff=0.4))
        server = VGroup(*[box(1.4, 0.4, GREY_B, radius=0.05, stroke=2) for _ in range(3)]).arrange(DOWN, buff=0.08)
        server.move_to([-4.6, -1.6, 0])
        server_tag = note('no server copy', 24, GREY_A).next_to(server, DOWN, buff=0.2)
        self.play(FadeIn(server), FadeIn(server_tag))
        no_server = cross_mark(0.5).move_to(server)
        self.play(Create(no_server))
        self.at('bigger programs make longer links')
        bars = VGroup()
        for words, length in (('small program', 1.6), ('bigger program', 4.4)):
            bar = Rectangle(width=length, height=0.35).set_fill(FOCUS, 0.8).set_stroke(width=0)
            bars.add(VGroup(note(words, 22, GREY_A), bar).arrange(RIGHT, buff=0.3))
        bars.arrange(DOWN, aligned_edge=LEFT, buff=0.35).move_to([1.7, -1.4, 0])
        for row in bars:
            row[1].align_to(bars[1][1], LEFT)
        length_tag = note('link length', 22, FOCUS).next_to(bars, UP, buff=0.2).align_to(bars[1][1], LEFT)
        self.play(FadeIn(length_tag), *[GrowFromEdge(row[1], LEFT) for row in bars], *[FadeIn(row[0]) for row in bars])

        # [V9.6c] Shorten link asks a public service
        self.at('Shorten link')
        self.play(FadeOut(VGroup(server, server_tag, no_server, bars, length_tag)))
        service = cloud().scale(0.9).move_to([0, -1.5, 0])
        service_tag = note('a link-shortening service', 22, GREY_A).next_to(service, DOWN, buff=0.15)
        short = Text('https://is.gd/…', font=MONO, font_size=30, color=AFTER).move_to([4.6, -1.5, 0])
        into = Arrow(link.get_bottom() + LEFT * 2.5, service.get_left() + UP * 0.1, buff=0.15, color=GREY_B, stroke_width=4)
        out = Arrow(service.get_right(), short.get_left(), buff=0.2, color=GREY_B, stroke_width=4)
        self.play(GrowArrow(into), FadeIn(service), FadeIn(service_tag))
        self.play(GrowArrow(out), FadeIn(short))
        self.at('depends on that service')
        depends = note('only while the service is up', 22, WARNING).next_to(short, DOWN, buff=0.25)
        self.play(FadeIn(depends))

        # [V9.6d] a link holds the version it was made from
        self.at('If you keep editing')
        self.play(FadeOut(VGroup(link, code_box, code_tag, service, service_tag, short, into, out, depends)))
        v1 = chip('version 1', BLUE, 26).move_to([-4.0, 1.0, 0])
        v2 = chip('version 2', BLUE, 26).move_to([2.5, 1.0, 0])
        edit = Arrow(v1.get_right(), v2.get_left(), buff=0.2, color=GREY_B, stroke_width=4)
        edit_tag = note('keep editing', 22, GREY_A).next_to(edit, UP, buff=0.1)
        link1 = chip('link 1', GREY_A, 24, mono=True).next_to(v1, DOWN, buff=1.0)
        tie1 = Line(link1.get_top(), v1.get_bottom(), color=GREY_B, stroke_width=3)
        self.play(FadeIn(v1), FadeIn(link1), Create(tie1))
        self.play(GrowArrow(edit), FadeIn(edit_tag), FadeIn(v2))
        self.at('the old link still holds')
        self.play(Indicate(VGroup(link1, tie1, v1), color=FOCUS))
        self.at('share again')
        link2 = chip('link 2', AFTER, 24, mono=True).next_to(v2, DOWN, buff=1.0)
        tie2 = Line(link2.get_top(), v2.get_bottom(), color=AFTER, stroke_width=3)
        self.play(FadeIn(link2, shift=UP * 0.2), Create(tie2))
        self.finish()


# ---------------------------------------------------------------- 9.7

def storage(color=GREY_B):
    body = Rectangle(width=1.8, height=1.4).set_stroke(color, 3).set_fill('#15181d', 1)
    top = Ellipse(width=1.8, height=0.5).set_stroke(color, 3).set_fill('#22262d', 1).move_to(body.get_top())
    bottom = Arc(radius=1, start_angle=PI, angle=PI).stretch_to_fit_width(1.8).stretch_to_fit_height(0.25)
    bottom.set_stroke(color, 3).move_to(body.get_bottom() + DOWN * 0.125)
    return VGroup(body, bottom, top)


class Segment_9_7(Segment):
    """Saving to HashBin."""
    EPISODE, SEGMENT = 9, '9.7'

    def construct(self):
        # [V9.7a] source and scene choice go to HashBin; a CID comes back
        source = file_icon('.py', BLUE).move_to([-5.4, 1.9, 0])
        scene = chip('scene: Middle', AFTER, 22, mono=True).next_to(source, DOWN, buff=0.35)
        bin_ = storage().move_to([-2.6, 1.6, 0])
        bin_tag = note('HashBin', 26, GREY_A).next_to(bin_, UP, buff=0.15)
        self.play(FadeIn(source), FadeIn(scene))
        self.at('Save to hash bin')
        send = Arrow(VGroup(source, scene).get_right(), bin_.get_left(), buff=0.25, color=GREY_B, stroke_width=4)
        self.play(GrowArrow(send), FadeIn(bin_), FadeIn(bin_tag))
        self.at('a content identifier')
        cid = mono_lines(CID, 47, 18, FOCUS).next_to(bin_, RIGHT, buff=0.7)
        back = Arrow(bin_.get_right(), cid.get_left(), buff=0.15, color=FOCUS, stroke_width=4)
        cid_tag = note('C I D: content identifier', 24, FOCUS).next_to(cid, UP, buff=0.2)
        self.play(GrowArrow(back), FadeIn(cid), FadeIn(cid_tag))
        self.at('the end of the page')
        address = VGroup(Text(SITE + '#', font=MONO, font_size=20, color=GREY_A), mono_lines(CID, 47, 20, FOCUS))
        address.arrange(DOWN, aligned_edge=LEFT, buff=0.12).move_to(DOWN * 1.2)
        address_tag = note('the page address', 24, GREY_A).next_to(address, DOWN, buff=0.25)
        self.play(TransformFromCopy(cid, address[1]), FadeIn(address[0]), FadeIn(address_tag), run_time=1.5)

        # paid storage: connect once, see the price and retention, then save
        self.at('paid storage service')
        self.play(FadeOut(VGroup(source, scene, send, back, cid, cid_tag, address, address_tag)),
                  VGroup(bin_, bin_tag).animate.move_to([-5.2, 1.0, 0]))
        steps = VGroup(*[chip(words, color, 24) for words, color in (
            ('1  connect an account (the first time)', GREY_A),
            ('2  see the price and how long it is kept', FOCUS),
            ('3  save', AFTER))]).arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to([1.2, 1.0, 0])
        for phrase, step in zip(('connect an account', 'shows you the price', None), steps):
            if phrase:
                self.at(phrase)
            self.play(FadeIn(step, shift=RIGHT * 0.2), run_time=0.6)

        # [V9.7c] loading is free, for anyone: a CID, a saved link, or just open the link
        self.at('Loading saved work is free')
        self.play(FadeOut(steps), FadeOut(VGroup(bin_, bin_tag)))
        key = Text(CID[:18] + '…', font=MONO, font_size=26, color=FOCUS).move_to([-4.0, 0.6, 0])
        free = note('free, for anyone', 26, AFTER).next_to(key, UP, buff=0.35)
        browsers = VGroup(*[browser_icon(3.2, 2.1) for _ in range(2)]).arrange(DOWN, buff=0.5).move_to([3.0, 0.3, 0])
        squares = VGroup(*[Square(0.6, color=BLUE).set_fill(BLUE, 0.5).rotate(PI / 4).move_to(b).shift(DOWN * 0.15) for b in browsers])
        loads = VGroup(*[Arrow(key.get_right(), b.get_left(), buff=0.2, color=GREY_B, stroke_width=4) for b in browsers])
        self.play(FadeIn(key), FadeIn(free), FadeIn(browsers))
        self.at('paste a C I D')
        paste = note('paste a C I D or a saved link', 22, GREY_A).next_to(loads[0], UP, buff=0.05).shift(LEFT * 0.6)
        self.play(GrowArrow(loads[0]), FadeIn(paste), FadeIn(squares[0]))
        self.at('simply open the link')
        opened = note('or open the link', 22, GREY_A).next_to(loads[1], DOWN, buff=0.05).shift(LEFT * 0.6)
        self.play(GrowArrow(loads[1]), FadeIn(opened), FadeIn(squares[1]))

        # [V9.7d] every QR code in the series is a HashBin link
        self.at('every QR code in this series')
        self.play(FadeOut(VGroup(key, free, browsers, squares, loads, paste, opened)))
        code = qr_code('q09-01', 3.4).move_to([-4.0, 0.6, 0])
        url = VGroup(Text(SITE + '#', font=MONO, font_size=20, color=GREY_A), mono_lines(CID, 47, 20, FOCUS))
        url.arrange(DOWN, aligned_edge=LEFT, buff=0.12).next_to(code, RIGHT, buff=0.7).shift(UP * 0.5)
        caption = note('q09-01 opens', 24, GREY_A).next_to(url, UP, buff=0.3).align_to(url, LEFT)
        self.play(FadeIn(code, scale=0.6))
        self.at('Each one is a hash bin link')
        self.play(FadeIn(caption), FadeIn(url, shift=LEFT * 0.2))

        # the CID is computed from the code: change one word and it changes completely
        self.at('computed from the code itself')
        self.play(FadeOut(VGroup(code, caption, url)))
        before = code_text('shape = Square(color=BLUE)', 24, GREY_A).move_to([-3.6, 2.0, 0])
        before_cid = mono_lines(CID, 32, 18, FOCUS).move_to([3.6, 2.0, 0])
        hashing = Arrow(before.get_right(), before_cid.get_left(), buff=0.25, color=GREY_B, stroke_width=4)
        hash_tag = note('computed', 20, GREY_B).next_to(hashing, UP, buff=0.05)
        self.play(FadeIn(before), GrowArrow(hashing), FadeIn(hash_tag), FadeIn(before_cid))
        self.at('that exact code')
        after = code_text('shape = Square(color=RED)', 24, GREY_A).move_to([-3.6, -0.6, 0])
        find_chars(after, 'shape = Square(color=RED)', 'RED').set_color(WARNING)
        after_cid = mono_lines(CID_EDITED, 32, 18, WARNING).move_to([3.6, -0.6, 0])
        hashing2 = Arrow(after.get_right(), after_cid.get_left(), buff=0.25, color=GREY_B, stroke_width=4)
        changed = note('one word changed: a completely different C I D', 24, WARNING).next_to(after_cid, DOWN, buff=0.4)
        changed.set_x(0)
        self.play(TransformFromCopy(before, after))
        self.play(GrowArrow(hashing2), FadeIn(after_cid), FadeIn(changed))

        self.at('Episode twelve')
        twelve = note('how it works, and why a QR code cannot be changed: episode 12', 24, FOCUS).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(twelve, shift=UP * 0.2))
        self.finish()


# ---------------------------------------------------------------- 9.8

class Segment_9_8(Segment):
    """Working offline."""
    EPISODE, SEGMENT = 9, '9.8'

    def construct(self):
        # [V9.8a] the first visit fills a store on the device
        browser = browser_icon(5.0, 3.2).move_to([-3.2, 1.0, 0])
        device = box(4.6, 2.6, GREY_B).move_to([3.2, 0.4, 0])
        device_tag = note('saved on your device', 24, GREY_A).next_to(device, UP, buff=0.15)
        self.play(FadeIn(browser), FadeIn(device), FadeIn(device_tag))
        items = VGroup()
        for phrase, words in (('the editor', 'the editor'), ('the gallery', 'the gallery'), ('the Python runtime', 'the Python runtime')):
            items.add(chip(words, GREY_A, 24))
        items.arrange(DOWN, buff=0.2).move_to(device)
        for phrase, item in zip(('the editor', 'the gallery', 'the Python runtime'), items):
            self.at(phrase)
            self.play(TransformFromCopy(browser, item), run_time=0.6)
        self.at('Ready offline')
        ready = VGroup(check_mark(0.4), note('Ready offline', 28, AFTER)).arrange(RIGHT, buff=0.25).next_to(browser, DOWN, buff=0.35)
        self.play(Create(ready[0]), FadeIn(ready[1]))

        # [V9.8b] no connection: the page opens and renders anyway
        self.at('no internet connection')
        signal = wifi_icon().move_to([0, 2.9, 0])
        self.play(FadeIn(signal))
        self.play(Create(cross_mark(0.35).move_to(signal)))
        square = Square(1.0, color=BLUE).move_to(browser).shift(DOWN * 0.2)
        circle = Circle(radius=0.6, color=BLUE).set_fill(BLUE, 0.5).move_to(square)
        self.play(Create(square))
        self.play(Transform(square, circle))

        # [V9.8c] what still needs a connection
        self.at('Only the things that genuinely need')
        waiting = VGroup(chip('save to HashBin', GREY_B, 22), chip('shorten a link', GREY_B, 22)).arrange(RIGHT, buff=0.3)
        waiting.next_to(device, DOWN, buff=0.45)
        clock = clock_icon(0.3).next_to(waiting, LEFT, buff=0.3)
        self.play(FadeIn(waiting), FadeIn(clock))
        self.at('back online')
        caption = note('First visit needs a connection. Sharing and saving need one too.', 26, FOCUS)
        caption.to_edge(DOWN, buff=0.4)
        self.play(FadeIn(caption))
        self.finish()


# ---------------------------------------------------------------- 9.9

def graph_node(label, width, height, scale):
    frame = RoundedRectangle(width=width * scale, height=height * scale, corner_radius=0.08 * scale)
    frame.set_stroke('#58c4dd', 2).set_fill('#1f3b57', 1)
    text = Text(label, font_size=20, color=WHITE, line_spacing=0.8)
    text.scale_to_fit_height(min(text.height, height * scale * (0.5 if '\n' not in label else 0.72)))
    if text.width > width * scale - 0.15:
        text.scale_to_fit_width(width * scale - 0.15)
    return VGroup(frame, text.move_to(frame))


def box_exit(node, toward):
    """Where the line from a node's centre toward a point leaves its rectangle."""
    centre = node.get_center()
    d = toward - centre
    hw, hh = node[0].width / 2, node[0].height / 2
    t = min(hw / abs(d[0]) if abs(d[0]) > 1e-9 else math.inf, hh / abs(d[1]) if abs(d[1]) > 1e-9 else math.inf)
    return centre + d * min(t, 1.0)


def graph_edge(a, b, label):
    start, end = box_exit(a, b.get_center()), box_exit(b, a.get_center())
    group = VGroup()
    if np.dot(end - start, b.get_center() - a.get_center()) > 0.05 and np.linalg.norm(end - start) > 0.12:
        group.add(Arrow(start, end, buff=0, color='#bbbbbb', stroke_width=3, tip_length=0.15,
                        max_tip_length_to_length_ratio=0.5))
    return group


def graph_layout(nodes, which, scale, centre):
    size = DOT_SIZE if which == 'dot' else NEATO_SIZE
    for name, (label, w, h, dot_xy, neato_xy) in GRAPH_NODES.items():
        x, y = dot_xy if which == 'dot' else neato_xy
        yield nodes[name], centre + scale * np.array([x - size[0] / 2, y - size[1] / 2, 0])


def modl_shape(kind, color, words):
    if kind == 'circle':
        shape = Circle(radius=0.45)
    elif kind == 'square':
        shape = Square(0.9)
    elif kind == 'diamond':
        shape = Square(0.8).rotate(PI / 4)
    else:
        shape = RegularPolygon(6, radius=0.5)
    shape.set_stroke(color, 4).set_fill(color, 0.25)
    label = Text(words, font_size=22).next_to(shape, DOWN, buff=0.12)
    return VGroup(shape, label)


def modl_edge(a, b, color, style, words, bend=0.0):
    ca, cb = a[0].get_center(), b[0].get_center()
    u = normalize(cb - ca)
    start = ca + rotate_vector(u, -bend / 2) * 0.55
    end = cb - rotate_vector(u, bend / 2) * 0.55
    path = ArcBetweenPoints(start, end, angle=bend) if bend else Line(start, end)
    path.set_stroke(color, 4)
    if style == 'dashed':
        path = DashedVMobject(path, num_dashes=10).set_stroke(color, 4)
    elif style == 'dotted':
        path = DashedVMobject(path, num_dashes=18, dashed_ratio=0.3).set_stroke(color, 5)
    direction = normalize(end - (ArcBetweenPoints(start, end, angle=bend) if bend else Line(start, end)).point_from_proportion(0.95))
    tip = Triangle().set_fill(color, 1).set_stroke(width=0).scale(0.12)
    tip.rotate(angle_of_vector(direction) - PI / 2).move_to(end - direction * 0.08)
    middle = (ArcBetweenPoints(start, end, angle=bend) if bend else Line(start, end)).point_from_proportion(0.5)
    bulge = middle - (start + end) / 2
    side = normalize(bulge) if np.linalg.norm(bulge) > 0.01 else rotate_vector(u, PI / 2)
    label = Text(words, font_size=20, color=color)
    label.move_to(middle + side * (0.2 + 0.5 * abs(side[0]) * label.width))
    return VGroup(path, tip, label)


class Segment_9_9(Segment):
    """Two more languages (q09-03, q09-04)."""
    EPISODE, SEGMENT = 9, '9.9'

    def construct(self):
        langs = VGroup(chip('Manim', BLUE, 28), chip('Graphviz', '#58c4dd', 28), chip('modl', PURPLE, 28)).arrange(RIGHT, buff=0.6)
        self.play(FadeIn(langs[0]))
        self.at('two diagram languages')
        self.play(LaggedStart(FadeIn(langs[1], shift=UP * 0.2), FadeIn(langs[2], shift=UP * 0.2), lag_ratio=0.4))

        # [V9.9a] q09-03 laid out by dot
        self.at('describes graphs')
        scale = 1.2
        centre = np.array([0, 1.9, 0])
        nodes = {name: graph_node(label, w, h, scale) for name, (label, w, h, _, _) in GRAPH_NODES.items()}
        for node, point in graph_layout(nodes, 'dot', scale, centre):
            node.move_to(point)
        edges = VGroup(*[always_redraw(lambda a=nodes[a], b=nodes[b], t=t: graph_edge(a, b, t)) for a, b, t in GRAPH_EDGES])
        tags = {}
        for a, b, t in GRAPH_EDGES:
            if t:
                tag = Text(t, font_size=16, color=GREY_A)
                tag.add_updater(lambda m, a=nodes[a], b=nodes[b]: m.move_to((a.get_center() + b.get_center()) / 2 + UP * 0.18))
                tags[t] = tag
        code = source_panel(snippet_lines(DOT_SNIPPET, 6, 17), 'dot', font_size=16)
        code.scale_to_fit_height(min(code.height, 3.4))
        fit(code, 7.4).to_corner(DL, buff=0.35)
        card = qr_card('q09-03')
        self.play(FadeOut(langs), FadeIn(code), FadeIn(card, shift=UP * 0.2))
        self.play(LaggedStart(*[FadeIn(n) for n in nodes.values()], lag_ratio=0.1), run_time=1.2)
        self.add(edges, *tags.values())
        self.play(FadeIn(edges), *[FadeIn(t) for t in tags.values()])
        self.at('works out the layout')
        self.play(Indicate(VGroup(*nodes.values()), color=FOCUS, scale_factor=1.03))

        # [V9.9b] the Engine menu: dot → neato
        self.at('The Engine menu')
        engine = VGroup(note('engine:', 24, GREY_A), Text('dot', font=MONO, font_size=26, color=FOCUS)).arrange(RIGHT, buff=0.2)
        engine.to_edge(UP, buff=0.25).to_edge(RIGHT, buff=0.5)
        self.play(FadeIn(engine))
        neato = Text('neato', font=MONO, font_size=26, color=FOCUS).move_to(engine[1], aligned_edge=LEFT)
        self.play(FadeTransform(engine[1], neato),
                  *[node.animate.move_to(point) for node, point in graph_layout(nodes, 'neato', scale, centre)], run_time=2)
        self.wait(1.0)

        # [V9.9c] q09-04 in modl: one line per node or arrow; drag a node and its arrows follow
        self.at('moddle is a lighter language')
        for tag in tags.values():
            tag.clear_updaters()
        for edge in edges:
            edge.clear_updaters()
        self.play(FadeOut(VGroup(*nodes.values(), edges, *tags.values(), code, card, engine[0], neato)))
        modl_code = source_panel(snippet_source(MODL_SNIPPET), 'text', font_size=16)
        modl_code.scale_to_fit_height(min(modl_code.height, 4.6))
        fit(modl_code, 6.4).to_edge(LEFT, buff=0.35).shift(UP * 0.9)
        spots = {'idea': (0.9, 2.9), 'code': (3.9, 2.9), 'preview': (3.9, 0.5), 'share': (0.9, 0.5), 'qr': (0.9, -1.9)}
        shapes = {'idea': ('circle', YELLOW, 'Idea'), 'code': ('square', BLUE, 'Write a scene'),
                  'preview': ('circle', GREEN, 'Preview'), 'share': ('diamond', PURPLE, 'Share link'),
                  'qr': ('hex', ORANGE, 'QR code')}
        nodes = {}
        for name, (kind, color, words) in shapes.items():
            nodes[name] = modl_shape(kind, color, words)
            nodes[name][0].move_to([*spots[name], 0])
            side = RIGHT if name in ('code', 'preview') else DOWN
            nodes[name][1].next_to(nodes[name][0], side, buff=0.15)
        specs = [('idea', 'code', TEAL, 'solid', 'Type', 0), ('code', 'preview', TEAL, 'solid', 'Render', 0.5),
                 ('preview', 'code', ORANGE, 'dashed', 'Tweak', 0.5), ('preview', 'share', PURPLE, 'solid', 'Save', 0),
                 ('share', 'qr', PURPLE, 'dotted', 'Scan', 0)]
        arrows = VGroup(*[always_redraw(lambda a=nodes[a], b=nodes[b], c=c, s=s, w=w, k=k: modl_edge(a, b, c, s, w, k))
                          for a, b, c, s, w, k in specs])
        card = qr_card('q09-04')
        self.play(FadeIn(modl_code), FadeIn(card, shift=UP * 0.2))
        self.play(LaggedStart(*[FadeIn(n) for n in nodes.values()], lag_ratio=0.15), run_time=1.2)
        self.add(arrows)
        self.play(FadeIn(arrows))

        self.at('drag nodes into place')
        hand = pointer().move_to(nodes['qr'][0].get_center() + DR * 0.1, aligned_edge=UL)
        self.play(FadeIn(hand))
        drag = VGroup(nodes['qr'], hand)
        self.play(drag.animate.shift(RIGHT * 2.0 + UP * 0.4), run_time=1.5)
        self.play(drag.animate.shift(LEFT * 0.4 + DOWN * 0.2), run_time=0.8)
        self.at('positions are saved')
        saved = note('positions are saved with your work', 24, FOCUS).next_to(modl_code, DOWN, buff=0.3).align_to(modl_code, LEFT)
        self.play(FadeIn(saved), FadeOut(hand))

        # the editor recognises the language; the Renderer menu overrides it
        self.at('You never have to tell')
        for arrow in arrows:
            arrow.clear_updaters()
        self.play(FadeOut(VGroup(*nodes.values(), arrows, modl_code, card, saved)))
        samples = VGroup(chip('class Hello(Scene): …', BLUE, 22, mono=True), chip('digraph G { a -> b }', '#58c4dd', 22, mono=True),
                         chip('a -> b solid', PURPLE, 22, mono=True)).arrange(DOWN, aligned_edge=LEFT, buff=0.45).move_to([-4.2, 0.4, 0])
        detector = labelled_box('reads the code', 2.9, 1.0, 26).move_to([0.3, 0.4, 0])
        outputs = VGroup(chip('Manim', BLUE, 24), chip('Graphviz', '#58c4dd', 24), chip('modl', PURPLE, 24)).arrange(DOWN, buff=0.45).move_to([4.5, 0.4, 0])
        ins = VGroup(*[Arrow(s.get_right(), detector.get_left(), buff=0.15, color=GREY_B, stroke_width=3) for s in samples])
        outs = VGroup(*[Arrow(detector.get_right(), o.get_left(), buff=0.15, color=GREY_B, stroke_width=3) for o in outputs])
        self.play(FadeIn(samples, lag_ratio=0.2), FadeIn(detector), run_time=1.2)
        self.at('picks the right renderer')
        self.play(LaggedStart(*[GrowArrow(a) for a in ins], lag_ratio=0.1), run_time=0.8)
        self.play(LaggedStart(*[AnimationGroup(GrowArrow(a), FadeIn(o)) for a, o in zip(outs, outputs)], lag_ratio=0.2), run_time=1.2)
        self.at('If it guesses wrong')
        menu = note('Renderer: Auto, or choose one yourself', 26, FOCUS).to_edge(DOWN, buff=0.7)
        self.play(FadeIn(menu, shift=UP * 0.2))
        self.finish()


# ---------------------------------------------------------------- 9.10

BUILD_STEPS = [
    ['dot = Dot(radius=0.3, color=BLUE)', 'self.add(dot)'],
    ['label = Text("x").next_to(dot, UP)', 'self.add(label)'],
    ['self.play(VGroup(dot, label).animate.shift(RIGHT * 2))'],
    ['self.play(self.camera.frame.animate.scale(0.5).move_to(dot))'],
]

HELPER_SOURCE = '''COLOR_X = BLUE

def labelled_dot(name, color=COLOR_X):
    dot = Dot(radius=0.3, color=color)
    label = Text(name).next_to(dot, UP)
    return VGroup(dot, label)

class First(Scene):
    def construct(self):
        a = labelled_dot("a").shift(LEFT * 2)
        self.add(a, labelled_dot("b").shift(RIGHT * 2))

class Second(Scene):
    def construct(self):
        self.play(FadeIn(labelled_dot("x")))'''


def mini_labelled_dot(name, color, frame, shift=ORIGIN):
    dot = Dot(radius=0.3, color=color)
    label = Text(name).next_to(dot, UP)
    return on_stage(VGroup(dot, label).shift(shift), frame)


class Segment_9_10(Segment):
    """A workflow that scales."""
    EPISODE, SEGMENT = 9, '9.10'

    def construct(self):
        habits = VGroup(*[note(w, 24, DIM) for w in ('small steps', 'names for repeats', 'short scenes', 'checkpoints')])
        habits.arrange(RIGHT, buff=0.9).to_edge(UP, buff=0.35)
        self.play(FadeIn(habits, lag_ratio=0.2), run_time=1.5)

        def focus(k):
            return [h.animate.set_color(FOCUS if i == k else DIM) for i, h in enumerate(habits)]

        # [V9.10a] four versions, one addition each, each rendered and checked
        self.at('Build in small steps')
        self.play(*focus(0))
        frame = stage_frame(4.8).move_to([3.9, 0.3, 0])
        self.play(FadeIn(frame))
        lines = []
        shown = VGroup()
        ticks = VGroup()
        dot = label = None
        content = VGroup()
        for k, step in enumerate(BUILD_STEPS):
            lines += step
            panel = code_panel('\n'.join(lines), font_size=20, line_numbers=False)
            fit(panel, 6.6).to_edge(LEFT, buff=0.4).align_to(frame, UP)
            new = VGroup(*[code_line(panel, i) for i in range(len(lines) - len(step), len(lines))])
            if k == 0:
                self.play(FadeIn(panel), run_time=0.6)
            else:
                self.play(FadeTransform(shown, panel), run_time=0.6)
            self.play(Indicate(new, color=FOCUS, scale_factor=1.02), run_time=0.6)
            shown = panel
            if k == 0:
                dot = on_stage(Dot(radius=0.3, color=BLUE), frame)
                content.add(dot)
                self.play(FadeIn(dot))
            elif k == 1:
                label = on_stage(Text('x').next_to(Dot(radius=0.3), UP), frame)
                content.add(label)
                self.play(FadeIn(label))
            elif k == 2:
                self.play(content.animate.shift(RIGHT * 2 * frame.width / config.frame_width))
            else:
                self.play(content.animate.scale(2, about_point=dot.get_center()).shift(frame.get_center() - dot.get_center()))
            tick = VGroup(check_mark(0.35), note('renders', 20, AFTER)).arrange(RIGHT, buff=0.15)
            tick.next_to(frame, DOWN, buff=0.3 + 0.45 * k).align_to(frame, LEFT)
            ticks.add(tick)
            self.play(Create(tick[0]), FadeIn(tick[1]), run_time=0.5)

        # [V9.10b] a helper and a constant, shared by two scenes; one edit recolours both
        self.at('Give names to things')
        self.play(*focus(1), FadeOut(VGroup(shown, frame, content, ticks)))
        source = HELPER_SOURCE
        panel = code_panel(source, font_size=24, line_numbers=False)
        fit(panel, 8.4)
        if panel.height > 6.4:
            panel.scale_to_fit_height(6.4)
        panel.to_edge(LEFT, buff=0.3).shift(DOWN * 0.35)
        rows = source.split('\n')
        first = stage_frame(4.0).move_to([4.75, 1.3, 0])
        second = stage_frame(4.0).move_to([4.75, -1.75, 0])
        names = VGroup(note('First', 20, GREY_A).next_to(first, UP, buff=0.08).align_to(first, LEFT),
                       note('Second', 20, GREY_A).next_to(second, UP, buff=0.08).align_to(second, LEFT))
        dots_first = VGroup(mini_labelled_dot('a', BLUE, first, LEFT * 2), mini_labelled_dot('b', BLUE, first, RIGHT * 2))
        dots_second = mini_labelled_dot('x', BLUE, second)
        self.play(FadeIn(panel), FadeIn(first), FadeIn(second), FadeIn(names), FadeIn(dots_first), FadeIn(dots_second))

        def occurrences(needle):
            found = VGroup()
            for i, row in enumerate(rows):
                start = row.find(needle)
                while start >= 0:
                    found.add(chars(code_line(panel, i), row, start, start + len(needle)))
                    start = row.find(needle, start + 1)
            return found

        self.at('write a little function')
        helper = occurrences('labelled_dot')
        self.play(helper.animate.set_color(FOCUS))
        self.at('define a constant')
        constant = occurrences('COLOR_X')
        self.play(helper.animate.set_color(GREY_A), constant.animate.set_color(AFTER))
        self.at('a one-line edit')
        green = code_panel(source.replace('COLOR_X = BLUE', 'COLOR_X = GREEN', 1), font_size=24, line_numbers=False)
        green.scale_to_fit_width(panel.width).move_to(panel, aligned_edge=UL)
        new_line = code_line(green, 0)
        find_chars(new_line, rows[0].replace('BLUE', 'GREEN'), 'COLOR_X').set_color(AFTER)
        self.play(Transform(code_line(panel, 0), new_line),
                  *[d[0].animate.set_color(GREEN) for d in (*dots_first, dots_second)], run_time=1.2)

        # [V9.10c] one long scene against three short ones
        self.at('Prefer several short scenes')
        self.play(*focus(2), FadeOut(VGroup(panel, first, second, names, dots_first, dots_second)))
        unit = 0.05  # units per second
        limit_x = -5.0 + 120 * unit
        long_bar = Rectangle(width=150 * unit, height=0.5).set_fill(BLUE, 0.7).set_stroke(width=0)
        long_bar.move_to([-5.0 + 75 * unit, 1.5, 0])
        long_tag = note('one long scene', 24, GREY_A).next_to(long_bar, UP, buff=0.15).align_to(long_bar, LEFT)
        shorts = VGroup(*[Rectangle(width=50 * unit, height=0.45).set_fill(AFTER, 0.7).set_stroke(width=0) for _ in range(3)])
        shorts.arrange(DOWN, buff=0.2).move_to([-5.0 + 25 * unit, -0.55, 0])
        short_tags = VGroup(*[Text(f'Part{i}', font=MONO, font_size=20).move_to(s) for i, s in enumerate(shorts, 1)])
        shorts_tag = note('three short scenes', 24, GREY_A).next_to(shorts, UP, buff=0.15).align_to(shorts, LEFT)
        limit = DashedLine([limit_x, 2.4, 0], [limit_x, -1.7, 0], color=WARNING, stroke_width=4)
        limit_tag = note('preview limit: 120 s', 22, WARNING).next_to(limit, DOWN, buff=0.15)
        self.play(GrowFromEdge(long_bar, LEFT), FadeIn(long_tag))
        self.play(Create(limit), FadeIn(limit_tag))
        too_long = cross_mark(0.25).next_to(long_bar, RIGHT, buff=0.3)
        self.play(FadeIn(too_long))
        self.play(LaggedStart(*[GrowFromEdge(s, LEFT) for s in shorts], lag_ratio=0.3), FadeIn(short_tags), FadeIn(shorts_tag))
        self.at('render faster')
        each = VGroup(*[check_mark(0.25).next_to(s, RIGHT, buff=0.3) for s in shorts])
        self.play(LaggedStart(*[Create(c) for c in each], lag_ratio=0.2))
        self.at('perfect each part')
        self.play(Indicate(VGroup(shorts[1], short_tags[1]), color=FOCUS))

        # [V9.10d] checkpoints: links made whenever something works
        self.at('And keep checkpoints')
        self.play(*focus(3), FadeOut(VGroup(long_bar, long_tag, shorts, short_tags, shorts_tag, limit, limit_tag, too_long, each)))
        line = Arrow(LEFT * 6, RIGHT * 6, buff=0, color=GREY_D, stroke_width=4).shift(DOWN * 0.3)
        when = note('time', 20, DIM).next_to(line, DOWN, buff=0.1).align_to(line, RIGHT)
        self.play(GrowArrow(line), FadeIn(when))
        marks = VGroup()
        for x, words in ((-3.8, 'dot and label work'), (0.0, '+ the animation'), (3.8, '+ the camera move')):
            pin = chip('link', AFTER, 22, mono=True).move_to([x, 0.7, 0])
            stem = Line(pin.get_bottom(), [x, -0.3, 0], color=AFTER, stroke_width=3)
            tag = note(words, 22, GREY_A).next_to([x, -0.3, 0], DOWN, buff=0.5)
            marks.add(VGroup(pin, stem, tag))
        self.at('a snapshot of your work')
        self.play(LaggedStart(*[FadeIn(m, shift=DOWN * 0.2) for m in marks], lag_ratio=0.4), run_time=1.8)
        self.at('always go back')
        back = CurvedArrow(marks[2][0].get_top() + UP * 0.1, marks[0][0].get_top() + UP * 0.1, angle=0.8, color=FOCUS)
        self.play(Create(back))
        self.finish()


# ---------------------------------------------------------------- 9.11

def terminal(width=8.4, height=3.0):
    window = box(width, height, GREY_B, fill='#0d0f12', radius=0.15, stroke=2)
    dots = VGroup(*[Dot(radius=0.06, color=GREY_B) for _ in range(3)]).arrange(RIGHT, buff=0.1)
    dots.move_to(window.get_corner(UL) + RIGHT * 0.4 + DOWN * 0.25)
    title = note('Terminal', 20, GREY_B).move_to(window.get_top() + DOWN * 0.25)
    return VGroup(window, dots, title)


class Segment_9_11(Segment):
    """Graduating to full Manim."""
    EPISODE, SEGMENT = 9, '9.11'

    def construct(self):
        reasons = VGroup(*[chip(w, GREY_A, 26) for w in ('60 fps, high resolution', 'very long scenes', 'every Manim feature')])
        reasons.arrange(RIGHT, buff=0.4).move_to(UP * 2.6)
        for phrase, item in zip(('sixty-frame', 'very long scenes', 'for features'), reasons):
            self.at(phrase)
            self.play(FadeIn(item, shift=DOWN * 0.2), run_time=0.6)

        # [V9.11a] install, then run a scene from a terminal
        self.at('documentation walks you through')
        self.play(reasons.animate.scale(0.75).to_edge(UP, buff=0.25))
        shell = terminal().move_to([-2.0, 0.6, 0])
        self.play(FadeIn(shell))
        install = Text('$ pip install manim', font=MONO, font_size=26).move_to(shell[0]).align_to(shell[0], LEFT).shift(RIGHT * 0.4 + UP * 0.5)
        self.play(AddTextLetterByLetter(install), run_time=1.2)
        self.at('Then you run your scene')
        pieces = ['manim', '-pql', 'scene.py', 'SquareToCircle']
        words = VGroup(Text('$', font=MONO, font_size=26), *[Text(p, font=MONO, font_size=26) for p in pieces])
        words.arrange(RIGHT, buff=0.22, aligned_edge=DOWN).next_to(install, DOWN, buff=0.45).align_to(install, LEFT)
        self.play(LaggedStart(*[AddTextLetterByLetter(w) for w in words], lag_ratio=1), run_time=1.5)
        self.at('a quality flag')
        braces = VGroup()
        for piece, words_ in zip(words[1:], ('manim', 'quality', 'your file', 'the scene')):
            brace = Brace(piece, DOWN, buff=0.1, color=GREY_B)
            braces.add(VGroup(brace, note(words_, 20, GREY_A).next_to(brace, DOWN, buff=0.08)))
        self.play(LaggedStart(*[FadeIn(b) for b in braces], lag_ratio=0.35), run_time=2.0)

        # [V9.11b] the flags, and the video window
        window = browser_icon(3.6, 2.4, GREY_B).move_to([4.6, -1.3, 0])
        square = Square(1.0, color=BLUE).move_to(window).shift(DOWN * 0.15)
        circle = Circle(radius=0.55, color=BLUE).set_fill(BLUE, 0.5).move_to(square)
        self.play(FadeIn(window, scale=0.8), Create(square))
        self.play(Transform(square, circle))
        flags = VGroup(note('-p: play when done', 22, FOCUS), note('-ql: quality low (fast)', 22, FOCUS)).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        flags.next_to(shell, DOWN, buff=0.35).align_to(shell, LEFT)
        self.play(FadeOut(braces), FadeIn(flags))
        self.at('almost unchanged')
        high = Text('-pqh', font=MONO, font_size=26, color=FOCUS).move_to(words[2], aligned_edge=LEFT)
        high_note = note('-qh: quality high (1080p, 60 fps)', 22, FOCUS).move_to(flags[1], aligned_edge=LEFT)
        self.play(Transform(words[2], high), Transform(flags[1], high_note))

        # [V9.11c] the direction of compatibility
        self.at('be clear about the direction')
        self.play(FadeOut(VGroup(shell, install, words, flags, window, square, reasons)))
        outer = Circle(radius=2.9, color=BLUE).set_fill(BLUE, 0.12).move_to([-2.2, -0.3, 0])
        inner = Circle(radius=1.3, color=AFTER).set_fill(AFTER, 0.2).move_to(outer).shift(DOWN * 0.9 + LEFT * 0.3)
        outer_tag = Text('Manim Community', font_size=30, color=BLUE).move_to(outer.get_top() + DOWN * 0.7)
        inner_tag = Text('ManimOnline\nsubset', font_size=26, color=AFTER, line_spacing=0.8).move_to(inner)
        self.play(DrawBorderThenFill(outer), FadeIn(outer_tag))
        self.play(DrawBorderThenFill(inner), FadeIn(inner_tag))
        self.at('Most of what you write')
        out_arrow = Arrow(inner.get_right(), [1.6, -1.5, 0], buff=0.1, color=AFTER, stroke_width=5)
        out_text = note('code that works in ManimOnline\nis written for Manim', 24, AFTER).next_to(out_arrow, RIGHT, buff=0.15)
        self.play(GrowArrow(out_arrow), FadeIn(out_text))
        self.at('Not everything written')
        ring_point = outer.point_at_angle(PI / 5)
        in_arrow = Arrow([1.7, 2.6, 0], ring_point, buff=0.1, color=WARNING, stroke_width=5)
        in_text = note('not everything in Manim\nruns in ManimOnline', 24, WARNING).next_to(in_arrow.get_start(), RIGHT, buff=0.1)
        self.play(GrowArrow(in_arrow), FadeIn(in_text))
        self.at('it says so')
        says = note('and when it can’t, it says so', 26, GREY_A).to_edge(DOWN, buff=0.4).shift(RIGHT * 2.5)
        self.play(FadeIn(says))
        self.finish()


# ---------------------------------------------------------------- 9.12

class Segment_9_12(Segment):
    """Recap: the end of the main track."""
    EPISODE, SEGMENT = 9, '9.12'

    def construct(self):
        # [V9.12a] the loop, box by box
        boxes, arrows, back = motif(['edit', 'render', 'preview', 'share'])
        loop = VGroup(boxes, arrows, back).move_to(UP * 1.2)
        self.play(FadeIn(loop))
        details = ['gallery · scenes', 'cancel · limits', 'SVG · PNG · video', 'links · HashBin']
        notes = VGroup(*[note(d, 22, GREY_A).next_to(b, UP, buff=0.25) for d, b in zip(details, boxes)])
        for phrase, b, n in zip(('Gallery for inspiration', 'Rendering that you', 'Exports as pictures', 'links that carry'),
                                boxes, notes):
            self.at(phrase)
            self.play(b[0].animate.set_stroke(FOCUS), FadeIn(n, shift=DOWN * 0.1), run_time=0.6)
        self.at('Offline whenever')
        extras = VGroup(chip('offline', AFTER, 24), chip('Graphviz', '#58c4dd', 24), chip('modl', PURPLE, 24)).arrange(RIGHT, buff=0.4)
        extras.next_to(loop, DOWN, buff=0.7)
        self.play(FadeIn(extras[0]))
        self.at('with diagrams on the side')
        self.play(FadeIn(extras[1:], lag_ratio=0.3))

        # [V9.12b] the QR wall, 10 seconds
        self.at("That's the end of the main track", lead=0.5)
        wall = qr_wall([f'q09-0{i}' for i in range(1, 6)])
        heading = Text('Episode 9 · scan to open each scene', font_size=26, color=SCAFFOLD).to_corner(UL, buff=0.3)
        self.play(FadeOut(VGroup(loop, notes, extras)), FadeIn(wall), FadeIn(heading))
        self.wait(10)

        # [V9.12c] a fork in the road: keep making things, or open the hood (episode 10)
        self.play(FadeOut(VGroup(wall, heading)))
        stem = Line([0, -3.4, 0], [0, -1.0, 0], color=GREY_B, stroke_width=8)
        left = Line([0, -1.0, 0], [-3.6, 1.3, 0], color=GREY_B, stroke_width=8)
        right = Line([0, -1.0, 0], [3.6, 1.3, 0], color=GREY_B, stroke_width=8)
        keep = note('keep making things', 28, AFTER).next_to(left.get_end(), UP, buff=0.3)
        how = note('how does it work?', 28, FOCUS)
        door = box(1.2, 1.9, FOCUS, fill='#22262d', radius=0.05).move_to(right.get_end() + UP * 0.95)
        knob = Dot(door.get_center() + RIGHT * 0.4 + DOWN * 0.2, radius=0.06, color=FOCUS)
        ten = Text('10', font_size=40, color=FOCUS).move_to(door).shift(UP * 0.45)
        how.next_to(door, LEFT, buff=0.4)
        self.play(Create(stem), run_time=0.8)
        self.play(Create(left), Create(right), run_time=1.0)
        self.play(FadeIn(keep), FadeIn(how), FadeIn(VGroup(door, knob, ten), shift=UP * 0.2))
        self.wait(1.5)
        self.finish()
