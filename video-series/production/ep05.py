"""Episode 5 · Words and equations. One Scene per script segment.

    python3 video-series/production/render.py 5 [-ql] [segment ...]

Shot ids in comments ([V5.2c] ...) refer to episodes/05-words-and-equations.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403

# One colour per formula term, used wherever the term appears.
TERM_COLORS = {'2x': BLUE, '=': FOCUS, '11': GREEN, '3': TEAL, '8': PURPLE_B, 'x': BLUE_B, r'\frac{8}{2}': PURPLE_A, '4': AFTER}


def solve_steps(font_size=72):
    """The q05-03 lines of working (the snippet scales its default 48 by 1.5)."""
    return [
        MathTex("2x", "+", "3", "=", "11", font_size=font_size),
        MathTex("2x", "=", "11", "-", "3", font_size=font_size),
        MathTex("2x", "=", "8", font_size=font_size),
        MathTex("x", "=", r"\frac{8}{2}", font_size=font_size),
        MathTex("x", "=", "4", font_size=font_size),
    ]


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


def isolated(formula, tex):
    """Every glyph group MathTex isolated for `tex` (tex_to_color_map/substrings_to_isolate)."""
    return VGroup(*[formula.id_to_vgroup_dict[i] for t, i in formula.matched_strings_and_ids
                    if t == tex and i.endswith('substring')])


def tag(name, color, font_size=22):
    """A class name in a coloured outline, as a label for an example."""
    label = code_text(name, font_size, color)
    box = SurroundingRectangle(label, color=color, buff=0.12, corner_radius=0.08, stroke_width=2)
    return VGroup(box, label)


def index_tag(i, color=GREY_A, font_size=26):
    return code_text(f'[{i}]', font_size, color)


def fit(mob, width=13.0):
    """Shrink a line that would run off the frame."""
    return mob.scale_to_fit_width(width) if mob.width > width else mob


def outlined(mob, width=1.5, color=WHITE):
    return mob.copy().set_fill(opacity=0).set_stroke(color, width)


def glyph_anchors(mob, radius=0.035, color=FOCUS):
    return VGroup(*[anchors_and_handles(g, anchor_color=color, anchor_radius=radius)[0]
                    for g in mob.family_members_with_points()])


class Segment_5_1(Segment):
    """Cold open: an equation that solves itself."""
    EPISODE, SEGMENT = 5, '5.1'

    def construct(self):
        # [V5.1a] 2x + 3 = 11 writes itself
        steps = solve_steps()
        current = steps[0]
        self.play(Write(current), run_time=1.5)

        # [V5.1b] [V5.1c] each line of working, on its sentence of narration
        for step, fraction in zip(steps[1:], (0.05, 0.13, 0.19, 0.25)):
            self.hold_until(fraction)
            self.play(TransformMatchingTex(current, step))
            current = step
        ring = Circle(color=FOCUS, stroke_width=5).surround(current, buffer_factor=1.4)
        self.play(Create(ring))
        self.hold_until(0.32)

        # what doesn't disappear: replay with 2x and = coloured, leaving trails as they glide
        self.play(FadeOut(VGroup(current, ring)))
        replay = solve_steps()
        for line in replay[:3]:
            for part in line:
                if part.get_tex_string() in ('2x', '='):
                    part.set_color(TERM_COLORS[part.get_tex_string()])
        caption = Text('2x and = never vanish: they glide', font_size=32, color=SCAFFOLD).to_edge(UP, buff=0.8)
        current = replay[0]
        self.play(FadeIn(current), FadeIn(caption))
        for step in replay[1:3]:
            self.wait(0.6)
            kept = [p for p in current if p.get_tex_string() in ('2x', '=')]
            trails = VGroup(*[TracedPath(lambda p=p: p.get_bottom() + DOWN * 0.3, stroke_color=p.get_color(), stroke_width=5,
                                         dissipating_time=1.2) for p in kept])
            self.add(trails)
            self.play(TransformMatchingTex(current, step), run_time=2.2)
            current = step
            self.wait(1.2)
            self.remove(trails)
        self.hold_until(0.72)

        # letters and numbers are, to Manim, just more shapes
        self.play(FadeOut(caption))
        for step in replay[3:]:
            self.play(TransformMatchingTex(current, step), run_time=0.8)
            current = step
        self.play(current.animate.scale(2.2), run_time=1)
        self.play(current.animate.set_fill(opacity=0).set_stroke(WHITE, 2), run_time=1.5)
        dots = glyph_anchors(current, radius=0.03)
        shapes = Text('letters and numbers: just more shapes', font_size=32, color=FOCUS).to_edge(DOWN, buff=0.8)
        self.play(LaggedStart(*[FadeIn(d, scale=2) for d in dots], lag_ratio=0.2), FadeIn(shapes))
        self.finish()


class Segment_5_2(Segment):
    """Three ways to write."""
    EPISODE, SEGMENT = 5, '5.2'

    def construct(self):
        intro = Text('three ways to put words on screen', font_size=40)
        self.play(FadeIn(intro))
        self.hold_until(0.07)
        self.play(FadeOut(intro))

        # [V5.2a] the q05-01 lines, left-aligned beside their tags, clear of the QR card
        words = Text("Text uses ordinary fonts", font_size=40)
        formula = MathTex(r"e^{i\pi} + 1 = 0", font_size=72)
        sentence = Tex(r"Tex mixes words and math: $\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}$")
        sentence.scale_to_fit_width(7.4)
        tags = VGroup(tag('Text', BLUE_C), tag('MathTex', GREEN_C), tag('Tex', PURPLE_B))
        for line, label, y in zip((words, formula, sentence), tags, (2.6, 0.9, -0.9)):
            line.move_to([0, y, 0]).align_to([-4.4, 0, 0], LEFT)
            label.move_to([-5.7, y, 0])
        qr = qr_card('q05-01')
        self.play(Write(words), FadeIn(tags[0]), FadeIn(qr))
        size = code_text('font_size=40', 20, SCAFFOLD)
        size.next_to(words, DOWN, buff=0.15, aligned_edge=LEFT)
        self.play(FadeIn(size))
        self.hold_until(0.24)

        # MathTex: the whole string is mathematics, written in TeX notation
        self.play(Write(formula), FadeIn(tags[1]))
        rows = VGroup()
        for source, result in (('^', MathTex('x^2', font_size=44)), (r'\pi', MathTex(r'\pi', font_size=44)),
                               (r'\frac{1}{2}', MathTex(r'\frac{1}{2}', font_size=44))):
            row = VGroup(code_text(source, 26, FOCUS), MathTex(r'\rightarrow', font_size=36, color=SCAFFOLD), result)
            rows.add(row.arrange(RIGHT, buff=0.35))
        rows.arrange(DOWN, buff=0.35, aligned_edge=LEFT).move_to([3.9, 0.3, 0])
        heading = Text('TeX notation', font_size=24, color=SCAFFOLD).next_to(rows, UP, buff=0.3, aligned_edge=LEFT)
        for row in rows:
            self.play(FadeIn(row, shift=LEFT * 0.2), run_time=0.8)
            if row is rows[0]:
                self.add(heading)
        self.hold_until(0.52)

        # Tex: ordinary text, the mathematical parts in dollar signs
        self.play(FadeOut(VGroup(rows, heading)))
        self.play(Write(sentence), FadeIn(tags[2]), run_time=2)
        maths = VGroup(*sentence[0][21:])
        dollars = SurroundingRectangle(maths, color=PURPLE_B, buff=0.08, stroke_width=2)
        note = code_text('$ ... $', 24, PURPLE_B).next_to(dollars, UP, buff=0.12)
        self.play(Create(dollars), FadeIn(note))
        self.hold_until(0.66)

        # [V5.2c] the raw-string habit
        self.play(FadeOut(VGroup(words, size, formula, sentence, tags, dollars, note, qr)))
        source = 'MathTex(r"e^{i\\pi} + 1 = 0")'
        line = code_text(source, 44, GREY_A).shift(UP * 1.6)
        self.play(FadeIn(line))
        r = find_chars(line, source, 'r"')[0]
        ring = Circle(color=FOCUS, stroke_width=4).surround(r, buffer_factor=2.2)
        raw = Text('raw string: Python leaves backslashes alone', font_size=28, color=FOCUS)
        raw.next_to(line, UP, buff=0.5)
        self.play(Create(ring), FadeIn(raw))
        backslash = find_chars(line, source, '\\')
        self.play(backslash.animate.set_color(FOCUS), Indicate(backslash, color=FOCUS, scale_factor=1.6))
        self.wait(1)

        # without the r, \f in \frac is a special character (form feed)
        plain_source, raw_source = '"\\frac{1}{2}"', 'r"\\frac{1}{2}"'
        plain = code_text(plain_source, 36, GREY_A)
        raw_line = code_text(raw_source, 36, GREY_A)
        broken = VGroup(Text('form feed', font_size=26, color=WARNING), code_text('+ "rac{1}{2}"', 30, WARNING)).arrange(RIGHT, buff=0.3)
        fixed = VGroup(code_text('\\frac{1}{2}', 30, AFTER), MathTex(r'\frac{1}{2}', font_size=48, color=AFTER)).arrange(RIGHT, buff=0.5)
        arrow = MathTex(r'\rightarrow', color=SCAFFOLD)
        bad = VGroup(plain, arrow, broken).arrange(RIGHT, buff=0.4).shift(DOWN * 0.6)
        good = VGroup(raw_line, arrow.copy(), fixed).arrange(RIGHT, buff=0.4).shift(DOWN * 2.2)
        bad.align_to(good, LEFT)
        self.play(FadeIn(plain))
        self.play(find_chars(plain, plain_source, '\\f').animate.set_color(WARNING))
        self.play(FadeIn(bad[1:]))
        self.play(FadeIn(raw_line))
        self.play(find_chars(raw_line, raw_source, 'r"')[0].animate.set_color(FOCUS), FadeIn(good[1:]))
        self.finish()


class Segment_5_3(Segment):
    """From TeX to outlines."""
    EPISODE, SEGMENT = 5, '5.3'

    STAGE_WIDTH, STAGE_HEIGHT = 2.3, 1.45

    def stage(self, art, caption, color=SCAFFOLD):
        box = RoundedRectangle(width=self.STAGE_WIDTH, height=self.STAGE_HEIGHT, corner_radius=0.12)
        box.set_stroke(color, 2).set_fill('#15181c', 1)
        if art.width > self.STAGE_WIDTH - 0.3:
            art.scale_to_fit_width(self.STAGE_WIDTH - 0.3)
        if art.height > self.STAGE_HEIGHT - 0.3:
            art.scale_to_fit_height(self.STAGE_HEIGHT - 0.3)
        art.move_to(box)
        label = wrapped_text(caption, self.STAGE_WIDTH + 0.2, font_size=18, color=GREY_A).next_to(box, DOWN, buff=0.15)
        return VGroup(box, art, label)

    def pipeline(self, stages, y):
        row = VGroup(*stages).arrange(RIGHT, buff=0.5, aligned_edge=UP).move_to([0, y, 0])
        arrows = VGroup(*[Arrow(a[0].get_right(), b[0].get_left(), buff=0.06, stroke_width=3, color=GREY_B,
                                max_tip_length_to_length_ratio=0.35) for a, b in zip(stages, stages[1:])])
        return row, arrows

    def formula(self):
        return MathTex(r"e^{i\pi} + 1 = 0", font_size=40)

    def construct(self):
        source = 'r"e^{i\\pi} + 1 = 0"'
        # [V5.3a] standard Manim: LaTeX on your computer, then dvisvgm
        page = Rectangle(width=1.0, height=1.25).set_fill(WHITE, 1).set_stroke(width=0)
        page_formula = self.formula().set_color(BLACK).scale_to_fit_width(0.8).move_to(page).shift(UP * 0.25)
        lines = VGroup(*[Line(LEFT * 0.35, RIGHT * 0.35, color=GREY_B, stroke_width=2) for _ in range(3)]).arrange(DOWN, buff=0.12)
        lines.next_to(page_formula, DOWN, buff=0.15)
        curves = outlined(self.formula())
        standard = [
            self.stage(code_text(source, 16, FOCUS), 'MathTex string'),
            self.stage(Tex(r'\LaTeX', font_size=56), 'LaTeX (installed on your computer)'),
            self.stage(VGroup(page, page_formula, lines), 'DVI document'),
            self.stage(outlined(self.formula()), 'dvisvgm: SVG outlines'),
            self.stage(VGroup(curves, glyph_anchors(curves, radius=0.016)), 'VMobject: cubic curves', OBJECT),
        ]
        top, top_arrows = self.pipeline(standard, 1.75)
        top_title = Text('Manim Community', font_size=26, color=GREY_A).next_to(top, UP, buff=0.3).align_to(top, RIGHT)
        self.play(FadeIn(top_title), FadeIn(standard[0]))
        for arrow, stage in zip(top_arrows, standard[1:]):
            self.play(GrowArrow(arrow), FadeIn(stage, shift=RIGHT * 0.2), run_time=0.9)
            self.wait(0.5)
        self.hold_until(0.28)

        # a large download
        download = VGroup(Arrow(UP * 0.3, DOWN * 0.3, buff=0, color=WARNING, stroke_width=5), Text('large download', font_size=22, color=WARNING))
        download.arrange(RIGHT, buff=0.15).next_to(standard[1][0], UP, buff=0.15)
        self.play(FadeIn(download, shift=DOWN * 0.2))
        self.hold_until(0.36)

        # [V5.3b] ManimOnline: MathJax in the page, no TeX installation
        window = browser_icon(2.0, 1.25)
        window_formula = self.formula().scale_to_fit_width(1.4).move_to(window).shift(DOWN * 0.1)
        online_curves = outlined(self.formula())
        online = [
            self.stage(code_text(source, 16, FOCUS), 'Python worker'),
            self.stage(VGroup(window, window_formula), 'MathJax, in the page'),
            self.stage(outlined(self.formula()), 'SVG glyph paths'),
            self.stage(VGroup(online_curves, glyph_anchors(online_curves, radius=0.016)), 'VMobject', OBJECT),
        ]
        bottom, bottom_arrows = self.pipeline(online, -1.2)
        bottom_title = Text('ManimOnline', font_size=26, color=GREY_A).next_to(bottom, UP, buff=0.3).align_to(top, RIGHT)
        no_tex = Text('no TeX installation', font_size=20, color=AFTER).next_to(online[1][0], UP, buff=0.1)
        self.play(FadeIn(bottom_title), FadeIn(online[0]))
        self.play(GrowArrow(bottom_arrows[0]), FadeIn(online[1], shift=RIGHT * 0.2))
        self.play(FadeIn(no_tex))
        for arrow, stage in zip(bottom_arrows[1:], online[2:]):
            self.play(GrowArrow(arrow), FadeIn(stage, shift=RIGHT * 0.2), run_time=0.9)
        self.hold_until(0.55)

        # [V5.3c] the page measures the formulas, and the scene renders again
        loop = CurvedArrow(online[1][2].get_bottom() + DOWN * 0.1, online[0][2].get_bottom() + DOWN * 0.1,
                           angle=-TAU / 3, color=FOCUS, stroke_width=4)
        loop_label = Text('measure, then render again', font_size=22, color=FOCUS).next_to(loop, DOWN, buff=0.1)
        self.play(Create(loop), FadeIn(loop_label))
        self.play(Indicate(online[0][0], color=FOCUS))
        self.hold_until(0.74)

        # [V5.3d] what is and isn't supported
        self.play(FadeOut(VGroup(top_title, top, top_arrows, download, bottom_title, bottom, bottom_arrows, no_tex, loop, loop_label)))
        examples = VGroup(*[MathTex(t, font_size=44) for t in (
            r'\frac{a}{b}', r'\sqrt{x}', r'\sum_{n=1}^{\infty}', r'\int_0^1 x\,dx',
            r'\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}', r'\alpha\,\beta\,\gamma')])
        examples.arrange_in_grid(rows=2, buff=(0.6, 0.4))
        supported = VGroup(Text('Supported: common mathematical notation', font_size=28, color=AFTER), examples)
        supported.arrange(DOWN, buff=0.4)
        missing = VGroup(code_text('\\usepackage{...}', 26, GREY_A), code_text('custom preamble', 26, GREY_A)).arrange(RIGHT, buff=0.8)
        crosses = VGroup(*[Line(m.get_corner(DL), m.get_corner(UR), color=WARNING, stroke_width=4) for m in missing])
        unsupported = VGroup(Text('Not supported: custom LaTeX packages and preambles', font_size=28, color=WARNING),
                             VGroup(missing, crosses)).arrange(DOWN, buff=0.35)
        sign = VGroup(supported, unsupported).arrange(DOWN, buff=0.7).shift(UP * 0.3)
        self.play(FadeIn(supported[0]))
        self.play(LaggedStart(*[Write(e) for e in examples], lag_ratio=0.25), run_time=3)
        self.wait(0.5)
        self.play(FadeIn(unsupported[0]), FadeIn(missing))
        self.play(Create(crosses))
        self.hold_until(0.9)
        reference = Text('Looks wrong? Simplify it first. Full Manim with LaTeX is the reference.', font_size=24,
                         color=SCAFFOLD).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(reference))
        self.finish()


class Segment_5_4(Segment):
    """Every letter is a shape."""
    EPISODE, SEGMENT = 5, '5.4'

    def construct(self):
        # [V5.4a] q05-02: MANIM writes
        word = Text("MANIM", font_size=120).shift(UP * 1.5)
        self.play(Write(word))
        boxes = VGroup(*[SurroundingRectangle(letter, color=GREY_D, buff=0.06, stroke_width=1.5) for letter in word])
        above = VGroup(*[index_tag(i, GREY_B, 24).next_to(box, UP, buff=0.12) for i, box in enumerate(boxes)])
        below = VGroup(*[index_tag(i - 5, GREY_D, 24).next_to(box, DOWN, buff=0.12) for i, box in enumerate(boxes)])
        self.play(Create(boxes), FadeIn(above))
        self.play(FadeIn(below))
        self.hold_until(0.13)

        # [V5.4b] first and last letters
        self.play(word[0].animate.set_color(YELLOW), word[-1].animate.set_color(YELLOW),
                  above[0].animate.set_color(YELLOW), below[-1].animate.set_color(YELLOW))
        self.hold_until(0.25)

        # [V5.4c] the letters hop one after another
        self.play(FadeOut(VGroup(boxes, above[1:], below[:-1])))
        self.play(LaggedStart(*[letter.animate(rate_func=there_and_back).shift(UP * 0.5) for letter in word],
                              lag_ratio=0.15, run_time=2))
        self.hold_until(0.38)

        # [V5.4d] several strings, several parts (clear of the QR card on the right)
        self.play(FadeOut(VGroup(above[0], below[-1])))
        source = 'MathTex("a^2", "+", "b^2", "=", "c^2")'
        code = code_text(source, 26).to_edge(UP, buff=0.35)
        self.play(FadeIn(code), word.animate.set_opacity(0.35))
        formula = MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96).move_to(LEFT * 1.2 + DOWN * 1.5)
        qr = qr_card('q05-02')
        self.play(Write(formula), FadeIn(qr))
        part_boxes = VGroup(*[DashedVMobject(SurroundingRectangle(p, buff=0.1, stroke_width=2), num_dashes=24).set_color(GREY_B)
                              for p in formula])
        tags = VGroup(*[index_tag(i, GREY_A).next_to(box, UP, buff=0.15) for i, box in enumerate(part_boxes)])
        for label in tags:
            label.align_to(tags[0], DOWN)
        strings = [find_chars(code, source, f'"{t}"') for t in ("a^2", "+", "b^2", "=", "c^2")]
        for box, label, string in zip(part_boxes, tags, strings):
            self.play(Create(box), FadeIn(label), string.animate.set_color(FOCUS), run_time=0.6)
            self.play(string.animate.set_color(GREY_A), run_time=0.3)
        self.hold_until(0.72)

        # colour a, b and c
        colors = {0: BLUE, 2: GREEN, 4: RED}
        self.play(*[formula[i].animate.set_color(c) for i, c in colors.items()],
                  *[tags[i].animate.set_color(c) for i, c in colors.items()],
                  *[strings[i].animate.set_color(c) for i, c in colors.items()])
        self.hold_until(0.88)

        # point at one term
        pointer = Arrow(formula[2].get_bottom() + DOWN * 1.1, formula[2].get_bottom() + DOWN * 0.1, color=GREEN, buff=0)
        self.play(GrowArrow(pointer), Indicate(formula[2], color=GREEN))
        self.finish()


class Segment_5_5(Segment):
    """Styling words, colouring symbols."""
    EPISODE, SEGMENT = 5, '5.5'

    def construct(self):
        # [V5.5a] weight, slant, font, then t2c
        words = "Manim makes math move"
        versions = [
            ('', {}),
            (', weight=BOLD', {'weight': BOLD}),
            (', weight=BOLD, slant=ITALIC', {'weight': BOLD, 'slant': ITALIC}),
            (', font="Georgia"', {'font': 'Georgia'}),
            (', weight=BOLD, t2c={"math": YELLOW}', {'weight': BOLD, 't2c': {'math': YELLOW}}),
        ]
        times = (0.0, 0.06, 0.1, 0.14, 0.18)
        sentence = code = None
        for (args, kwargs), fraction in zip(versions, times):
            self.hold_until(fraction)
            new_sentence = Text(words, font_size=64, **kwargs).shift(UP * 1.2)
            new_code = fit(code_text(f'Text("{words}"{args})', 26)).shift(DOWN * 0.6)
            if args:
                find_chars(new_code, f'Text("{words}"{args})', args[2:]).set_color(FOCUS)
            if sentence is None:
                self.play(Write(new_sentence), FadeIn(new_code))
            else:
                self.play(FadeTransform(sentence, new_sentence), FadeTransform(code, new_code))
            sentence, code = new_sentence, new_code
        t2c = Text('t2c: text to colour', font_size=28, color=SCAFFOLD).next_to(code, DOWN, buff=0.5)
        self.play(FadeIn(t2c))
        self.hold_until(0.22)

        # [V5.5b] MarkupText: tags shape the text and never appear in it
        markup_source = 'MarkupText(\'Manim makes <span foreground="yellow">math</span> <b>move</b>\')'
        markup = MarkupText('Manim makes <span foreground="yellow">math</span> <b>move</b>', font_size=64).shift(UP * 1.2)
        markup_code = fit(code_text(markup_source, 26)).shift(DOWN * 0.6)
        for found in re.finditer(r'<[^>]+>', markup_source):
            chars(markup_code, markup_source, found.start(), found.end()).set_color(DIM)
        self.play(FadeOut(VGroup(sentence, code, t2c)))
        self.play(FadeIn(markup_code))
        self.play(Write(markup))
        tags_note = Text('the tags shape the text, and never appear in it', font_size=28, color=SCAFFOLD)
        tags_note.next_to(markup_code, DOWN, buff=0.5)
        self.play(FadeIn(tags_note))
        self.hold_until(0.44)

        # [V5.5c] tex_to_color_map: every x blue, every y green, each one its own piece
        self.play(FadeOut(VGroup(markup, markup_code, tags_note)))
        formula = MathTex("x^2 + 2xy + y^2", substrings_to_isolate=["x", "y"], font_size=110).shift(UP * 1.2)
        formula_source = 'MathTex("x^2 + 2xy + y^2", tex_to_color_map={"x": BLUE, "y": GREEN})'
        formula_code = fit(code_text(formula_source, 24)).shift(DOWN * 0.8)
        self.play(Write(formula), FadeIn(formula_code))
        xs, ys = isolated(formula, 'x'), isolated(formula, 'y')
        self.play(xs.animate.set_color(BLUE), find_chars(formula_code, formula_source, '"x": BLUE').animate.set_color(BLUE))
        self.play(ys.animate.set_color(GREEN), find_chars(formula_code, formula_source, '"y": GREEN').animate.set_color(GREEN))
        self.wait(0.5)
        inside = SurroundingRectangle(VGroup(xs[1], ys[0]), color=FOCUS, buff=0.12)
        inside_note = Text('even inside 2xy', font_size=26, color=FOCUS).next_to(inside, UP, buff=0.15)
        self.play(Create(inside), FadeIn(inside_note))
        self.wait(1)
        self.play(FadeOut(VGroup(inside, inside_note)))
        pieces = VGroup(*[SurroundingRectangle(g, color=g.get_color(), buff=0.05, stroke_width=1.5) for g in [*xs, *ys]])
        pieces_note = Text('each one is its own piece', font_size=26, color=SCAFFOLD).next_to(formula, UP, buff=0.4)
        self.play(Create(pieces), FadeIn(pieces_note))
        self.hold_until(0.74)
        self.play(LaggedStart(*[g.animate(rate_func=there_and_back).shift(UP * 0.3) for g in [*xs, *ys]], lag_ratio=0.2),
                  run_time=1.6)
        self.hold_until(0.83)

        # x is always blue, on every graph too
        self.play(FadeOut(VGroup(pieces, pieces_note, formula_code)), formula.animate.scale(0.6).to_edge(LEFT, buff=0.8).shift(UP * 0.4))
        axes = Axes(x_range=[-2, 2, 1], y_range=[0, 4, 1], x_length=4.5, y_length=3.6, tips=False,
                    axis_config={'color': GREY_B}).shift(RIGHT * 3 + DOWN * 0.3)
        x_label = MathTex('x', color=BLUE, font_size=44).next_to(axes.x_axis.get_right(), RIGHT, buff=0.15)
        y_label = MathTex('y', color=GREEN, font_size=44).next_to(axes.y_axis.get_top(), UP, buff=0.15)
        curve = axes.plot(lambda x: x ** 2, x_range=[-2, 2], color=GREY_A)
        self.play(Create(axes), FadeIn(x_label), FadeIn(y_label))
        self.play(Create(curve))
        self.play(Indicate(x_label, color=BLUE), Indicate(xs, color=BLUE))
        self.finish()


STEP_PARTS = [["2x", "+", "3", "=", "11"], ["2x", "=", "11", "-", "3"], ["2x", "=", "8"], ["x", "=", r"\frac{8}{2}"], ["x", "=", "4"]]


def colour_terms(formula):
    for part in formula:
        key = part.get_tex_string()
        if key in TERM_COLORS:
            part.set_color(TERM_COLORS[key])
    return formula


def chip(tex, font_size=22):
    """One MathTex argument as a code chip."""
    label = code_text(('r"%s"' if '\\' in tex else '"%s"') % tex, font_size, GREY_A)
    box = SurroundingRectangle(label, color=GREY_D, buff=0.1, corner_radius=0.08, stroke_width=2)
    box.set_fill('#15181c', 1)
    return VGroup(box, label)


def match_lines(rows, keys=None):
    """Lines joining chips with identical TeX in consecutive rows, grouped by key."""
    lines = {}
    for upper, lower, upper_keys, lower_keys in zip(rows, rows[1:], STEP_PARTS, STEP_PARTS[1:]):
        for i, key in enumerate(upper_keys):
            if key in lower_keys and (keys is None or key in keys):
                j = lower_keys.index(key)
                line = Line(upper[i].get_bottom(), lower[j].get_top(), color=TERM_COLORS.get(key, GREY_B), stroke_width=3)
                lines.setdefault(key, VGroup()).add(line)
    return lines


class Segment_5_6(Segment):
    """Algebra that moves."""
    EPISODE, SEGMENT = 5, '5.6'

    def construct(self):
        # [V5.6a] the q05-03 lines as code, one chip per part, beside the typeset line
        rows = VGroup()
        typeset = VGroup()
        for k, keys in enumerate(STEP_PARTS):
            row = VGroup(*[chip(key) for key in keys]).arrange(RIGHT, buff=0.3)
            row.move_to([0, 2.7 - 1.35 * k, 0]).align_to([-6.3, 0, 0], LEFT)
            rows.add(row)
            typeset.add(MathTex(*keys, font_size=48).move_to([4.2, row.get_y(), 0]))
        name = code_text('TransformMatchingTex(current, step)', 24, FOCUS).to_corner(UR, buff=0.3)
        for row, formula in zip(rows, typeset):
            self.play(FadeIn(row, shift=RIGHT * 0.2), FadeIn(formula), run_time=0.6)
        self.hold_until(0.1)
        self.play(FadeIn(name))
        self.hold_until(0.14)

        # pairs with identical TeX are joined: 2x, =, then 3 and 11
        lines = match_lines(rows)
        for key, fraction in (('2x', 0.19), ('=', 0.23), ('3', 0.27), ('11', 0.3), ('x', 0.32)):
            self.hold_until(fraction)
            matched = [row[i] for row, keys in zip(rows, STEP_PARTS) for i, k in enumerate(keys) if k == key]
            parts = [formula[i] for formula, keys in zip(typeset, STEP_PARTS) for i, k in enumerate(keys) if k == key]
            self.play(Create(lines[key]), *[m[0].animate.set_stroke(TERM_COLORS[key]) for m in matched],
                      *[p.animate.set_color(TERM_COLORS[key]) for p in parts], run_time=0.8)
        self.hold_until(0.36)

        # [V5.6b] full screen: matched parts keep their colour as they slide
        self.play(FadeOut(VGroup(rows, typeset, name, *lines.values())))
        qr = qr_card('q05-03')
        steps = [colour_terms(s) for s in solve_steps()]
        current = steps[0]
        self.play(Write(current), FadeIn(qr))
        for step in steps[1:]:
            self.wait(0.5)
            self.play(TransformMatchingTex(current, step), run_time=1.3)
            current = step
        self.hold_until(0.49)

        # [V5.6c] slow motion: + has no partner and fades out, - is new and fades in
        start, end = (colour_terms(s) for s in solve_steps()[:2])
        self.play(FadeOut(current), FadeIn(start))
        gone = VGroup(Text('no partner: fades out', font_size=24, color=WARNING),
                      Arrow(UP * 0.5, ORIGIN, buff=0, color=WARNING)).arrange(DOWN, buff=0.1)
        gone.next_to(start[1], UP, buff=0.15)
        new = VGroup(Arrow(ORIGIN, UP * 0.5, buff=0, color=AFTER), Text('new: fades in', font_size=24, color=AFTER)).arrange(DOWN, buff=0.1)
        new.next_to(end[3], DOWN, buff=0.15)
        slow = Text('slow motion', font_size=24, color=SCAFFOLD).to_corner(UL, buff=0.4)
        self.play(FadeIn(gone), FadeIn(slow))
        self.play(TransformMatchingTex(start, end), FadeIn(new, run_time=1.5), run_time=4)
        self.play(FadeOut(gone))
        self.hold_until(0.68)

        # how you split the strings decides what can match
        self.play(FadeOut(VGroup(end, new, slow, qr)))
        one_source, two_source = 'MathTex("2x + 3 = 11")', 'MathTex("2x = 11 - 3")'
        single = MathTex("2x + 3 = 11", font_size=72)
        single_end = MathTex("2x = 11 - 3", font_size=72)
        code = code_text(one_source, 28).shift(UP * 2.2)
        code_end = code_text(two_source, 28).move_to(code)
        self.play(FadeIn(code), Write(single))
        self.hold_until(0.8)
        self.play(TransformMatchingTex(single, single_end), FadeTransform(code, code_end), run_time=2)
        fades = Text('one string: nothing to match, the whole formula cross-fades', font_size=28, color=WARNING)
        fades.to_edge(DOWN, buff=1.2)
        self.play(FadeIn(fades))
        self.hold_until(0.9)
        follow = Text('parts = the pieces the viewer\'s eye should follow', font_size=30, color=FOCUS).to_edge(DOWN, buff=1.2)
        split = VGroup(*[chip(k, 26) for k in STEP_PARTS[0]]).arrange(RIGHT, buff=0.3).move_to(code_end)
        self.play(FadeOut(VGroup(code_end, single_end, fades)))
        parts = colour_terms(solve_steps()[0])
        self.play(FadeIn(split), FadeIn(parts), FadeIn(follow))
        self.play(TransformMatchingTex(parts, colour_terms(solve_steps()[1])), run_time=1.5)
        self.finish()


class Segment_5_7(Segment):
    """Lining up the working."""
    EPISODE, SEGMENT = 5, '5.7'

    def construct(self):
        # [V5.7a] arrange centres each line, so the equals signs zig-zag
        line1 = MathTex("2x + 3", "=", "11", font_size=64)
        line2 = MathTex("2x", "=", "11 - 3", font_size=64)
        line3 = MathTex("x", "=", "4", font_size=64)
        lines = VGroup(line1, line2, line3).arrange(DOWN, buff=0.4).shift(UP * 1.1)
        self.play(LaggedStart(*[Write(l) for l in lines], lag_ratio=0.4), run_time=2.5)
        top, bottom = lines.get_top()[1] + 0.3, lines.get_bottom()[1] - 0.3

        def guide(line, color):
            x = line[1].get_x()
            return DashedLine([x, top, 0], [x, bottom, 0], color=color, stroke_width=3, dash_length=0.12)

        guides = VGroup(*[guide(l, WARNING) for l in lines])
        for l in lines:
            l[1].set_color(FOCUS)
        self.play(LaggedStart(*[Create(g) for g in guides], lag_ratio=0.3))
        zigzag = Text('arrange centres each line', font_size=28, color=WARNING).next_to(lines, DOWN, buff=0.6)
        self.play(FadeIn(zigzag))
        self.hold_until(0.36)

        # the equals sign is part 1 of every line; get_x says how far across it is
        tags = VGroup(*[index_tag(1, FOCUS, 22).next_to(l[1], UP, buff=0.08) for l in lines])
        self.play(FadeOut(zigzag), FadeIn(tags))
        self.hold_until(0.5)
        gaps = VGroup(*[DoubleArrow([l[1].get_x(), l[1].get_y() - 0.45, 0], [line1[1].get_x(), l[1].get_y() - 0.45, 0],
                                    buff=0, color=GREY_A, stroke_width=3, tip_length=0.15) for l in lines[1:]])
        self.play(FadeOut(tags), *[GrowFromCenter(g) for g in gaps])

        # [V5.7c] the code: the difference between equals signs, along x only
        source = 'line.shift(RIGHT * (line1[1].get_x() - line[1].get_x()))'
        loop = code_text('for line in lines[1:]:', 24).to_edge(DOWN, buff=1.3).align_to([-5.5, 0, 0], LEFT)
        body = code_text(source, 24).next_to(loop, DOWN, aligned_edge=LEFT, buff=0.15).shift(RIGHT * 0.6)
        self.play(FadeIn(loop), FadeIn(body))
        difference = find_chars(body, source, 'line1[1].get_x() - line[1].get_x()')
        box = SurroundingRectangle(difference, color=FOCUS, buff=0.06)
        right = find_chars(body, source, 'RIGHT')
        x_only = Text('x only', font_size=22, color=TEAL).next_to(right, DOWN, buff=0.12)
        self.play(Create(box), difference.animate.set_color(FOCUS))
        self.play(right.animate.set_color(TEAL), FadeIn(x_only))
        self.hold_until(0.78)

        # [V5.7b] each line moves under the first; the red guides merge into one green line
        x0 = line1[1].get_x()
        self.play(FadeOut(gaps),
                  *[l.animate.shift(RIGHT * (x0 - l[1].get_x())) for l in lines[1:]],
                  *[g.animate.shift(RIGHT * (x0 - l[1].get_x())).set_color(AFTER) for g, l in zip(guides, lines)],
                  run_time=2)
        self.remove(*guides[1:])
        straight = Text('a straight column: what changes stands out', font_size=28, color=AFTER).next_to(lines, DOWN, buff=0.4)
        self.play(FadeIn(straight))
        self.play(*[Indicate(l[2], color=FOCUS) for l in lines], run_time=1.5)
        self.finish()


class Segment_5_8(Segment):
    """Pointing at things."""
    EPISODE, SEGMENT = 5, '5.8'

    def construct(self):
        # [V5.8a] q05-04: the title writes with its underline
        title = Title("Completing the square")
        formula = MathTex("f(x)", "=", "x^2", "+", "2x", "+", "1", font_size=72)
        self.play(Write(title))
        self.play(Write(formula))
        self.hold_until(0.1)

        # [V5.8b] a brace under formula[2:], and a label from get_text
        brace = Brace(formula[2:], DOWN)
        label = brace.get_text("a perfect square")
        qr = qr_card('q05-04')
        brace_code = code_text('brace = Brace(formula[2:], DOWN)', 22)
        label_code = code_text('label = brace.get_text("a perfect square")', 22)
        code = VGroup(brace_code, label_code).arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_corner(DL, buff=0.5)
        self.play(GrowFromCenter(brace), FadeIn(brace_code), FadeIn(qr))
        self.play(Indicate(formula[2:], color=FOCUS))
        self.hold_until(0.3)
        self.play(FadeIn(label, shift=UP), FadeIn(label_code))
        self.hold_until(0.44)

        # [V5.8c] brace and label go; f(x) and = hold still while the rest becomes (x+1)^2
        target = MathTex("f(x)", "=", "(x+1)^2", font_size=72)
        target.shift(formula[1].get_center() - target[1].get_center())
        self.play(FadeOut(brace, label))
        self.play(TransformMatchingTex(formula, target))
        self.hold_until(0.56)

        # Title: a heading at the top of the frame, with a line beneath it
        title_code = code_text('title = Title("Completing the square")', 22).move_to(code, aligned_edge=UL)
        self.play(FadeOut(code), FadeIn(title_code))
        self.play(Indicate(title[0], color=FOCUS))
        self.play(ShowPassingFlash(title[1].copy().set_stroke(FOCUS, 6), time_width=0.6), run_time=1.5)
        self.finish()


class Segment_5_9(Segment):
    """Putting it together: Pythagoras."""
    EPISODE, SEGMENT = 5, '5.9'

    def construct(self):
        # [V5.9a] the q05-05 figure: a right triangle with a square on each side
        a, b = 2.4, 1.6
        A = LEFT * 4.5 + DOWN * 0.5
        B, C = A + RIGHT * a, A + UP * b
        triangle = Polygon(A, B, C, color=WHITE, fill_opacity=0.2)
        normal = RIGHT * b + UP * a
        squares = VGroup(
            Polygon(A, B, B + DOWN * a, A + DOWN * a, color=BLUE, fill_opacity=0.5),
            Polygon(A, C, C + LEFT * b, A + LEFT * b, color=GREEN, fill_opacity=0.5),
            Polygon(B, C, C + normal, B + normal, color=RED, fill_opacity=0.5),
        )
        self.play(Create(triangle))
        self.play(LaggedStart(*[DrawBorderThenFill(s) for s in squares[:2]], lag_ratio=0.4))
        self.hold_until(0.18)

        # the hypotenuse square: a vector as long as the hypotenuse, at right angles to it
        arrow = Arrow(B, B + normal, buff=0, color=FOCUS, stroke_width=5)
        corner = RightAngle(Line(B, C), Line(B, B + normal), length=0.3, color=FOCUS)
        vector = code_text('normal = RIGHT * b + UP * a', 24, FOCUS).move_to([3.5, 2.6, 0])
        note = Text('as long as the hypotenuse, at right angles to it', font_size=24, color=SCAFFOLD)
        note.next_to(vector, DOWN, buff=0.2)
        self.play(GrowArrow(arrow), FadeIn(vector))
        self.play(Create(corner), FadeIn(note))
        self.hold_until(0.36)
        self.play(DrawBorderThenFill(squares[2]), FadeOut(VGroup(arrow, corner)))
        self.hold_until(0.46)

        # [V5.9b] a label in the middle of each square
        self.play(FadeOut(VGroup(vector, note)))
        labels = VGroup(*[MathTex(t, font_size=48).move_to(s.get_center()) for t, s in zip(["a^2", "b^2", "c^2"], squares)])
        self.play(LaggedStart(*[Write(l) for l in labels], lag_ratio=0.4))
        self.hold_until(0.6)

        # [V5.9c] copies fly to the equation; the originals stay put
        equation = MathTex("a^2", "+", "b^2", "=", "c^2", font_size=72).to_edge(RIGHT, buff=1)
        for i, color in zip([0, 2, 4], [BLUE, GREEN, RED]):
            equation[i].set_color(color)
        qr = qr_card('q05-05')
        self.play(FadeIn(qr))
        self.play(*[TransformFromCopy(labels[k], equation[i]) for k, i in enumerate([0, 2, 4])],
                  FadeIn(equation[1]), FadeIn(equation[3]), run_time=2)
        self.hold_until(0.82)

        # the colours tie each term back to its square
        for k, i in enumerate([0, 2, 4]):
            self.play(Indicate(squares[k], color=squares[k].get_color(), scale_factor=1.05), Indicate(equation[i], color=squares[k].get_color()),
                      run_time=0.9)
        self.finish()


class Segment_5_10(Segment):
    """Recap."""
    EPISODE, SEGMENT = 5, '5.10'

    def construct(self):
        # [V5.10a] one tile per idea
        three = VGroup(*[VGroup(tag(n, c, 18), m).arrange(RIGHT, buff=0.25) for n, c, m in (
            ('Text', BLUE_C, Text('words', font_size=28)),
            ('MathTex', GREEN_C, MathTex(r'e^{i\pi}+1=0', font_size=32)),
            ('Tex', PURPLE_B, Tex(r'words and $\frac{\pi^2}{6}$', font_size=32)))]).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        routes = VGroup()
        for start, middle in (('LaTeX', 'dvisvgm'), ('MathJax', 'page')):
            steps = VGroup(*[Text(w, font_size=22, color=GREY_A) for w in (start, middle, 'curves')]).arrange(RIGHT, buff=0.45)
            arrows = VGroup(*[Arrow(x.get_right(), y.get_left(), buff=0.06, stroke_width=2, max_tip_length_to_length_ratio=0.4,
                                    color=GREY_B) for x, y in zip(steps, steps[1:])])
            routes.add(VGroup(steps, arrows))
        routes.arrange(DOWN, buff=0.35)
        letters = Text('MANIM', font_size=56)
        letters[0].set_color(YELLOW)
        letters[-1].set_color(YELLOW)
        letters = VGroup(letters, index_tag(0, YELLOW, 18).next_to(letters[0], UP, buff=0.1),
                         index_tag(-1, YELLOW, 18).next_to(letters[-1], UP, buff=0.1))
        coloured = MathTex("x^2 + 2xy + y^2", tex_to_color_map={"x": BLUE, "y": GREEN}, font_size=44)
        upper = colour_terms(MathTex("2x", "+", "3", "=", "11", font_size=36))
        lower = colour_terms(MathTex("2x", "=", "11", "-", "3", font_size=36)).next_to(upper, DOWN, buff=0.6)
        joins = VGroup(*[Line(upper[i].get_bottom(), lower[j].get_top(), color=TERM_COLORS[upper[i].get_tex_string()], stroke_width=2)
                         for i, j in ((0, 0), (2, 4), (3, 1), (4, 2))])
        matched = VGroup(upper, lower, joins)
        sq = MathTex("x^2", "+", "2x", "+", "1", font_size=40)
        braced = VGroup(sq, Brace(sq, DOWN), Text('a perfect square', font_size=20).next_to(sq, DOWN, buff=0.6))
        tiles = VGroup()
        for art, words in ((three, 'Text, MathTex, Tex'), (routes, 'two routes to outlines'), (letters, 'letters you can index'),
                           (coloured, 'tex_to_color_map'), (matched, 'TransformMatchingTex'), (braced, 'Brace and get_text')):
            art.move_to(ORIGIN)
            caption = Text(words, font_size=22, color=SCAFFOLD).next_to(art, DOWN, buff=0.25)
            tiles.add(VGroup(art, caption))
        for k, tile in enumerate(tiles):
            tile.move_to([(-4.6, 0, 4.6)[k % 3], (1.7, -1.9)[k // 3], 0])
        self.play(LaggedStart(*[FadeIn(t, shift=UP * 0.2) for t in tiles], lag_ratio=0.35), run_time=5)
        self.hold_until(0.55)

        # [V5.10b] the QR wall, 10 seconds
        wall = qr_wall([f'q05-0{i}' for i in range(1, 6)])
        heading = Text('Episode 5 · scan to open each scene', font_size=26, color=SCAFFOLD).to_corner(UL, buff=0.3)
        self.play(FadeOut(tiles), FadeIn(wall), FadeIn(heading))
        self.wait(10)

        # [V5.10c] teaser: a label clinging to a dot as it flies around (episode 6)
        self.play(FadeOut(VGroup(wall, heading)))
        dot = Dot(LEFT * 4 + DOWN * 1, color=FOCUS, radius=0.12)
        label = Text('me', font_size=30).add_updater(lambda m: m.next_to(dot, UR, buff=0.1))
        path = VMobject().set_points_smoothly([LEFT * 4 + DOWN * 1, LEFT * 1.5 + UP * 1.8, RIGHT * 1 + DOWN * 0.5,
                                               RIGHT * 3.5 + UP * 1.5, RIGHT * 4 + DOWN * 1.2])
        self.play(FadeIn(dot), FadeIn(label))
        self.play(MoveAlongPath(dot, path), run_time=3, rate_func=smooth)
        nxt = Text('Next: Things that change', font_size=34).to_edge(DOWN, buff=0.6)
        self.play(Write(nxt))
        self.finish()
