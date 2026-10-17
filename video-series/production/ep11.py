"""Episode 11 · Rebuilding an engine to match. One Scene per script segment.

    python3 video-series/production/render.py 11 [-ql] [segment ...]

Shot ids in comments ([V11.6a] ...) refer to episodes/11-rebuilding-an-engine-to-match.md.
Everything drawn here comes from Manim Community; manim-lite's side of each comparison is
either a screen recording (footage card) or a number measured by running manim-lite.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403
from ep09 import backed, box, check_mark, chip, cross_mark, labelled_box, note, on_stage, stage_frame  # noqa: E402

SHRINK_SNIPPET = 'ep11/01-why-it-shrinks.py'
TIPS_SNIPPET = 'ep11/02-fixed-size-tips.py'
STREAM_SNIPPET = 'ep11/03-stream-lines.py'
GRAPH_SNIPPET = 'ep11/04-graph-layouts.py'
FONT_SNIPPET = 'ep11/05-font-sizes.py'

LITE_LINES = 28_067        # wc -l src/manim-lite.py
REFERENCE_CASES = 30       # tests/fixtures/community_reference.json
PYTHON_TESTS, JS_TESTS = 750, 147
# Run in both engines (Manim Community 0.21 and manim-lite), identical to six decimal places.
FUZZ_CHAIN = 'Square().scale(0.3).rotate(1.2).next_to(Circle(), UL)'
FUZZ_RESULT = 'centre (-1.638319, 1.638319), width 0.776638'
ROW_WIDTH = 6.732051       # VGroup(Square(), Circle(), Triangle()).arrange(RIGHT, buff=0.5).width
# q11-03's stream line start points as manim-lite computes them (its own PCG64); Manim's are identical.
LITE_STARTS = [
    [-5.897279, -3.67266], [-6.362604, -1.765047], [-5.920023, -0.327878], [-5.673696, 1.23689], [-5.731947, 2.150189],
    [-6.243258, 4.272384], [-4.650216, -3.557985], [-4.781788, -1.872032], [-4.413461, -0.587242], [-4.139373, 1.139156],
    [-4.358665, 2.416691], [-4.333884, 4.019016], [-3.010623, -3.207884], [-3.106654, -1.946353], [-2.929275, -0.621567],
    [-2.707294, 0.795368], [-3.311988, 2.749483], [-3.195473, 4.282363], [-1.622912, -3.76229], [-1.277757, -2.202018],
    [-1.571586, -0.726115], [-1.439751, 0.849022], [-1.725363, 2.831585], [-1.795879, 4.096831], [-0.044717, -3.159057],
    [-0.056079, -1.90984], [0.336708, -0.529966], [-0.001933, 1.021984], [-0.064008, 2.675863], [0.324045, 3.711199],
    [1.820568, -3.149055], [1.77273, -1.639104], [1.236573, -0.145528], [1.74178, 0.984991], [1.72641, 2.817648],
    [1.529201, 3.957065], [2.655383, -3.325995], [2.646274, -1.835585], [3.193463, -0.490431], [2.674562, 1.255988],
    [2.883232, 2.447724], [3.046674, 3.819148], [4.791089, -3.705598], [4.341248, -1.935408], [4.732283, -0.454643],
    [4.434672, 1.238591], [4.844308, 2.402053], [4.570443, 4.261218], [5.929883, -3.192531], [6.24203, -2.063462],
    [5.632466, -0.601215], [6.114461, 0.830387], [6.332851, 2.220113], [5.669598, 3.910578]]
UNSUPPORTED = 'NotImplementedError: Moving camera frames support pan and zoom, not rotation'


def halfway(rate=smooth):
    return lambda t: rate(t) / 2


def swirl(pos):
    return (pos[0] * UR + pos[1] * LEFT) - pos


def note_card(words, color='#f3d564'):
    text = Text(words, font_size=24, color=BLACK, line_spacing=0.8)
    paper = Square(max(text.width, text.height) + 0.5).set_fill(color, 1).set_stroke(width=0)
    return VGroup(paper, text.move_to(paper)).rotate(0.05)


# ---------------------------------------------------------------- 11.1

class Segment_11_1(Segment):
    """Cold open: a bug-for-bug match."""
    EPISODE, SEGMENT = 11, '11.1'

    def construct(self):
        # [V11.1a] Manim Community on the left; on the right, a recording of ManimOnline playing the
        # same code (same_code below, with waits that keep both in step)
        frame = stage_frame(6.4).move_to([-3.4, 0.5, 0])
        left_tag = note('Manim Community', 26, BLUE).next_to(frame, UP, buff=0.2)
        screen = footage_screen(3.6).move_to([3.4, 0.5, 0])
        right_tag = note('ManimOnline', 26, AFTER).next_to(screen, UP, buff=0.2)
        self.play(FadeIn(frame), FadeIn(left_tag))
        self.at('On the right')
        self.footage_in(screen, 'V11.1', FadeIn(right_tag))

        starts = []
        # scale_tips: on_stage's plain scale would keep the tip at full size, unlike the picture on the right
        arrow = Arrow(LEFT * 3, RIGHT * 3, buff=0, color=YELLOW).shift(UP * 1.6)
        arrow.scale(frame.width / config.frame_width, scale_tips=True, about_point=ORIGIN).shift(frame.get_center())
        words = on_stage(VGroup(Text('Manim', font='Helvetica', font_size=72), Tex('Manim', font_size=72))
                         .arrange(RIGHT, buff=1.2).shift(DOWN * 1.6), frame)
        starts.append(self.renderer.time)
        self.play(GrowArrow(arrow), FadeIn(words))
        # [V11.1b] ManimOnline's picture laid over Manim Community's at 50 %: one picture, frame for frame
        overlay = Rectangle(width=frame.width, height=frame.height).move_to(frame).set_stroke(opacity=0)
        both = note('ManimOnline laid over it at 50 %', 22, AFTER).next_to(frame, DOWN, buff=0.25)
        self.footage_in(overlay, 'V11.1', arrow.animate.scale(0.4), FadeIn(both), run_time=1.5, crop='preview', opacity=0.5)
        self.play(arrow.animate.scale(2.5), run_time=1.5)

        # the square that collapses, frozen at the midpoint: on purpose
        self.at('Including this')
        starts.append(self.renderer.time)
        self.play(FadeOut(arrow), FadeOut(words))
        square = on_stage(Square(3, color=BLUE).set_fill(BLUE, 0.4), frame)
        self.play(FadeIn(square))
        self.at('collapses to a point')
        starts.append(self.renderer.time)
        self.play(square.animate.rotate(PI), rate_func=halfway(), run_time=1.5)
        purpose = note('on purpose', 30, FOCUS).next_to(frame, DOWN, buff=0.3)
        self.at('arguably a surprising behaviour')
        self.footage_out('V11.1', FadeOut(both), FadeIn(purpose, scale=0.8))
        self.at('deliberately')
        starts.append(self.renderer.time)
        final = on_stage(Square(3, color=BLUE).set_fill(BLUE, 0.4), frame)
        self.play(Transform(square, final), rate_func=lambda t: smooth(0.5 + t / 2) * 2 - 1, run_time=1.5)

        self.at('how do you know')
        question = Text("how do you know it's right?", font_size=40, color=FOCUS).to_edge(DOWN, buff=0.5)
        self.play(FadeOut(purpose), Write(question))
        self.finish()
        self.footage_notes = {'start': starts[0], 'code': same_code(starts, self.renderer.time)}


def same_code(starts, end):
    """The left panel's animations as one ManimOnline scene, with waits that keep it in step."""
    grow, fade, turn, finish = (round(t - starts[0], 3) for t in starts)

    def wait(seconds):   # Manim rejects a zero wait, and the gaps are often empty
        return f'        self.wait({seconds:.3f})\n' if seconds >= 1 / 60 else ''

    return ('''from manim import *


class SameCode(Scene):
    def construct(self):
        arrow = Arrow(LEFT * 3, RIGHT * 3, buff=0, color=YELLOW).shift(UP * 1.6)
        words = VGroup(Text("Manim", font="Helvetica", font_size=72), Tex("Manim", font_size=72))
        words.arrange(RIGHT, buff=1.2).shift(DOWN * 1.6)
        self.play(GrowArrow(arrow), FadeIn(words))
        self.play(arrow.animate.scale(0.4), run_time=1.5)
        self.play(arrow.animate.scale(2.5), run_time=1.5)
''' + wait(fade - 4) + '''        self.play(FadeOut(arrow), FadeOut(words))
        square = Square(3, color=BLUE).set_fill(BLUE, 0.4)
        self.play(FadeIn(square))
''' + wait(turn - fade - 2) + '''        # Half a turn with .animate, stopped halfway: the square has collapsed to its centre
        self.play(square.animate.rotate(PI), rate_func=lambda t: smooth(t) / 2, run_time=1.5)
''' + wait(finish - turn - 1.5) + '''        # ... and the second half of the same straight-line path
        self.play(Transform(square, Square(3, color=BLUE).set_fill(BLUE, 0.4)),
                  rate_func=lambda t: smooth(0.5 + t / 2) * 2 - 1, run_time=1.5)
''' + wait(end - starts[0] - finish - 1.5))


# ---------------------------------------------------------------- 11.2

class Segment_11_2(Segment):
    """Why not run the real thing?"""
    EPISODE, SEGMENT = 11, '11.2'

    def construct(self):
        # [V11.2a] Manim and the software beneath it
        manim = labelled_box('Manim Community', 3.6, 0.9, 30, BLUE).move_to(UP * 2.6)
        deps = [('Cairo', '(drawing)', 'Cairo'), ('Pango', '(text)', 'Pango'), ('FFmpeg', '(video)', 'FFmpeg'),
                ('OpenGL', '', None), ('LaTeX', '(installed\nseparately)', 'lay tek for formulas'),
                ('NumPy, SciPy,\nPillow, …', '', None)]
        roots = VGroup()
        for name, what, _ in deps:
            frame = box(2.0, 1.2, GREY_B, radius=0.1)
            text = VGroup(Text(name, font_size=24), note(what, 18, GREY_A)) if what else VGroup(Text(name, font_size=22))
            text.arrange(DOWN, buff=0.08).move_to(frame)
            roots.add(VGroup(frame, text))
        roots.arrange(RIGHT, buff=0.2).move_to(UP * 0.2)
        lines = VGroup(*[Line(manim.get_bottom(), r.get_top(), color=GREY_B, stroke_width=2) for r in roots])
        self.play(FadeIn(manim))
        for (_, _, phrase), root, line in zip(deps, roots, lines):
            if phrase:
                self.at(phrase)
            self.play(Create(line), FadeIn(root, shift=DOWN * 0.15), run_time=0.5)

        # [V11.2b] in a browser, the compiled libraries are not available
        self.at('Several of those are large compiled libraries')
        browser = browser_icon(13.2, 2.4).move_to(DOWN * 2.4)
        self.play(FadeIn(browser, shift=UP * 0.3))
        compiled = [roots[i] for i in range(5)]
        self.play(*[r[0].animate.set_stroke(WARNING) for r in compiled])
        missing = note('compiled libraries: not available in the page', 24, WARNING).move_to(browser).shift(DOWN * 0.15)
        self.play(FadeIn(missing))

        # [V11.2c] the same names on a different engine
        self.at('Keep the parts people actually type')
        self.play(FadeOut(VGroup(roots, lines, browser, missing)))
        names = VGroup(*[code_text(w, 26, GREY_A) for w in ('Square', 'Circle.animate', 'self.play', 'Transform', 'run_time=2')])
        names.arrange(RIGHT, buff=0.5).next_to(manim, DOWN, buff=0.6)
        self.play(LaggedStart(*[FadeIn(n) for n in names], lag_ratio=0.15))
        self.at('reimplement everything underneath')
        lite = labelled_box('manim-lite: the same names, a different engine', 9.6, 1.0, 28, AFTER).next_to(names, DOWN, buff=0.6)
        self.play(FadeIn(lite, shift=UP * 0.2))
        self.at('Instead of pixels')
        output = note('frame snapshots → SVG in the page', 26, GREY_A).next_to(lite, DOWN, buff=0.4)
        self.play(FadeIn(output))
        self.at('a single Python file')
        size = note(f'one Python file: {LITE_LINES:,} lines', 28, FOCUS).next_to(output, DOWN, buff=0.35)
        self.play(FadeIn(size, shift=UP * 0.15))
        self.at('the same code should produce the same animation')
        goal = note('same code, same animation', 30, AFTER).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(goal))
        self.finish()


# ---------------------------------------------------------------- 11.3

class Segment_11_3(Segment):
    """What does "the same" mean?"""
    EPISODE, SEGMENT = 11, '11.3'

    def construct(self):
        # [V11.3a] observable output, as layers
        layers = VGroup()
        for k, (words, color) in enumerate((('geometry: points, bounds', BLUE), ('style: colours, opacity, widths', TEAL),
                                            ('timing: durations, rate functions', FOCUS), ('structure: which objects, in what order', AFTER))):
            sheet = Polygon([-2.6, -0.5, 0], [2.0, -0.5, 0], [2.6, 0.5, 0], [-2.0, 0.5, 0]).set_fill(color, 0.18).set_stroke(color, 2)
            label = note(words, 24, color).next_to(sheet, RIGHT, buff=0.3)
            layers.add(VGroup(sheet, label).shift(UP * (1.2 - 0.85 * k)))
        layers.move_to(LEFT * 1.0)
        title = Text('What does "the same" mean?', font_size=44)
        self.play(FadeIn(title))
        self.at('everything you can observe')
        self.play(FadeOut(title))
        for phrase, layer in zip(('sizes and positions', 'the colours', 'how long each animation', 'which objects exist'), layers):
            self.at(phrase)
            self.play(FadeIn(layer, shift=DOWN * 0.2), run_time=0.6)

        # [V11.3b] one measurement, both engines
        self.at('That definition has an important consequence')
        self.play(FadeOut(layers))
        row = VGroup(Square(), Circle(), Triangle()).arrange(RIGHT, buff=0.5).scale(0.6)
        pair = VGroup(row, row.copy()).arrange(RIGHT, buff=1.4).move_to(UP * 1.2)
        tags = VGroup(note('Manim Community', 24, BLUE).next_to(pair[0], UP, buff=0.3), note('manim-lite', 24, AFTER).next_to(pair[1], UP, buff=0.3))
        self.play(FadeIn(pair), FadeIn(tags))
        readouts = VGroup(*[code_text(f'width {ROW_WIDTH}', 26, FOCUS).next_to(r, DOWN, buff=0.35) for r in pair])
        braces = VGroup(*[Brace(r, DOWN, buff=0.1, color=GREY_B) for r in pair])
        for r, b in zip(readouts, braces):
            r.next_to(b, DOWN, buff=0.1)
        self.play(FadeIn(braces), FadeIn(readouts))
        source = code_text('VGroup(Square(), Circle(), Triangle()).arrange(RIGHT, buff=0.5)', 22, GREY_B).next_to(readouts, DOWN, buff=0.4)
        source.set_x(0)
        self.play(FadeIn(source))

        # [V11.3c] measure, don't read
        self.at("You can't confirm it by reading code")
        sticky = note_card('Read the code?\nNot enough.\nMeasure.').move_to([4.8, -2.4, 0])
        self.play(FadeIn(sticky, shift=DOWN * 0.2))
        self.at('run both, and compare')
        self.play(Indicate(readouts, color=AFTER))
        self.finish()


# ---------------------------------------------------------------- 11.4

def result_row(words, verdict, color, width=11.0):
    frame = Rectangle(width=width, height=0.6).set_fill(color, 0.18).set_stroke(color, 2)
    text = note(words, 20, WHITE).move_to(frame).align_to(frame, LEFT).shift(RIGHT * 0.25)
    mark = note(verdict, 22, color).move_to(frame).align_to(frame, RIGHT).shift(LEFT * 0.25)
    return VGroup(frame, text, mark)


class Segment_11_4(Segment):
    """Measuring against the reference."""
    EPISODE, SEGMENT = 11, '11.4'

    def construct(self):
        # [V11.4a] scenes through both engines, compared
        pile = VGroup(*[box(1.6, 1.0, GREY_B, radius=0.06, stroke=2).shift(UP * 0.08 * k + RIGHT * 0.08 * k) for k in range(4)])
        pile.move_to([-5.4, 1.6, 0])
        pile_tag = note('test scenes', 22, GREY_A).next_to(pile, DOWN, buff=0.15)
        engines = VGroup(labelled_box('Manim 0.22', 2.6, 0.8, 24, BLUE), labelled_box('manim-lite', 2.6, 0.8, 24, AFTER))
        engines.arrange(DOWN, buff=0.5).move_to([-1.6, 1.6, 0])
        feeds = VGroup(*[Arrow(pile.get_right(), e.get_left(), buff=0.15, color=GREY_B, stroke_width=3) for e in engines])
        table = VGroup(result_row('arrange in a row: width', 'match', AFTER, 5.4), result_row('arc path: bounds', 'match', AFTER, 5.4),
                       result_row('Text: bounds', 'differs', ORANGE, 5.4)).arrange(DOWN, buff=0.12).move_to([4.1, 1.6, 0])
        joins = VGroup(*[Arrow(e.get_right(), table.get_left(), buff=0.15, color=GREY_B, stroke_width=3) for e in engines])
        self.play(FadeIn(pile), FadeIn(pile_tag))
        self.play(LaggedStart(*[GrowArrow(f) for f in feeds], lag_ratio=0.2), FadeIn(engines))
        self.play(LaggedStart(*[GrowArrow(j) for j in joins], lag_ratio=0.2), FadeIn(table, lag_ratio=0.2), run_time=1.2)

        # [V11.4b] reference snippets, measured once with Manim 0.22
        self.at('a set of reference snippets')
        refs = chip(f'{REFERENCE_CASES} reference snippets: bounds recorded from Manim 0.22', BLUE, 24).move_to(DOWN * 1.0)
        self.play(FadeIn(refs, shift=UP * 0.2))
        self.at('checked against those measurements automatically')
        auto = note('checked on every change', 22, GREY_A).next_to(refs, DOWN, buff=0.2)
        self.play(FadeIn(auto))
        self.at('even a tiny fraction of a unit')
        fail = note('moved by 0.0001 → the check fails', 22, WARNING).next_to(auto, DOWN, buff=0.15)
        self.play(FadeIn(fail))

        # [V11.4c] every documentation example, through both engines
        self.at("Mannim's documentation is full of example scenes")
        self.play(FadeOut(VGroup(refs, auto, fail)))
        docs = VGroup(*[box(1.8, 0.22, GREY_B, radius=0.03, stroke=1).shift(UP * 0.18 * k) for k in range(14)])
        docs.move_to([-5.6, -1.7, 0])
        docs_tag = note("every example in Manim's documentation", 22, GREY_A).next_to(docs, RIGHT, buff=0.3).shift(UP * 0.6)
        self.play(LaggedStart(*[FadeIn(d, shift=DOWN * 0.1) for d in docs], lag_ratio=0.05), FadeIn(docs_tag), run_time=1.2)
        self.at('the final positions, sizes and durations')
        compared = result_row('one example: final bounds and total duration', 'both match', AFTER, 10.0).next_to(docs_tag, DOWN, buff=0.35).align_to(docs_tag, LEFT)
        self.play(FadeIn(compared, shift=UP * 0.15))

        # [V11.4d] an explained difference
        self.at('Not every difference is a bug')
        amber = result_row('Text bounds differ: different fonts on this computer', 'explained', ORANGE, 10.0)
        amber.next_to(compared, DOWN, buff=0.2).align_to(compared, LEFT)
        self.play(FadeIn(amber, shift=UP * 0.15), Indicate(table[2], color=ORANGE))
        self.at('sorting differences')
        sorts = VGroup(chip('manim-lite is wrong', WARNING, 22), chip("this comparison isn't fair", ORANGE, 22)).arrange(RIGHT, buff=0.4)
        sorts.to_edge(DOWN, buff=0.25).shift(RIGHT * 1.4)
        self.play(FadeIn(sorts, lag_ratio=0.3))
        self.finish()


# ---------------------------------------------------------------- 11.5

class Segment_11_5(Segment):
    """Random scenes, and Manim's own tests."""
    EPISODE, SEGMENT = 11, '11.5'

    def construct(self):
        # [V11.5a] a fuzzer: random code, run in both engines
        machine = box(3.2, 2.2, FOCUS, radius=0.2).move_to([-4.8, 2.3, 0])
        reels = VGroup(*[box(0.7, 1.0, GREY_B, fill='#000000', radius=0.05, stroke=2) for _ in range(3)]).arrange(RIGHT, buff=0.15)
        reels.move_to(machine)
        tag = note('fuzzer', 26, FOCUS).next_to(machine, UP, buff=0.15)
        symbols = VGroup(*[Text(s, font=MONO, font_size=28) .move_to(r) for s, r in zip(('□', '↻', '⇱'), reels)])
        self.play(FadeIn(machine), FadeIn(reels), FadeIn(tag))
        self.at('generate random chains of methods')
        self.play(LaggedStart(*[FadeIn(s, shift=DOWN * 0.3) for s in symbols], lag_ratio=0.3))
        chain = code_text(FUZZ_CHAIN, 22, GREY_A).move_to([0, 0.6, 0])
        self.play(Write(chain), run_time=1.5)
        both = VGroup(note('Manim:', 22, BLUE), code_text(FUZZ_RESULT, 20, GREY_A), note('manim-lite:', 22, AFTER), code_text(FUZZ_RESULT, 20, GREY_A))
        both.arrange_in_grid(rows=2, cols=2, buff=(0.3, 0.2), col_alignments='rl').next_to(chain, DOWN, buff=0.3)
        self.play(FadeIn(both, lag_ratio=0.2))
        agree = check_mark(0.35).next_to(both, RIGHT, buff=0.3)
        self.play(Create(agree))

        # thousands of ticks, a rare amber one becomes a permanent test
        ticks = VGroup(*[check_mark(0.09) for _ in range(160)]).arrange_in_grid(rows=8, cols=20, buff=0.18).move_to(DOWN * 2.4)
        self.play(LaggedStart(*[FadeIn(t) for t in ticks], lag_ratio=0.01), run_time=2)
        self.at('Whenever a difference turns up')
        odd = Dot(ticks[87].get_center(), radius=0.12, color=ORANGE)
        self.play(FadeOut(ticks[87]), FadeIn(odd, scale=2))
        test = chip('a permanent test', AFTER, 22).move_to([4.6, -3.5, 0])
        self.at('turned into a permanent test')
        self.play(odd.animate.move_to(test.get_left() + LEFT * 0.3), FadeIn(test))

        # [V11.5c] Manim's own unit tests, pointed at manim-lite
        self.at('Mannim Community has its own suite of unit tests')
        self.play(FadeOut(VGroup(machine, reels, tag, symbols, chain, both, agree, ticks, odd, test)))
        folder = labelled_box("Manim's own unit tests", 4.2, 1.0, 26, BLUE).move_to(UP * 2.4)
        self.play(FadeIn(folder))
        self.at('known categories')
        bins = VGroup(*[chip(w, ORANGE, 22) for w in ('needs LaTeX files', 'OpenGL', 'writes video files', 'private helper functions')])
        bins.arrange(RIGHT, buff=0.3).move_to(UP * 0.6)
        most = note('most pass; the rest fall into known categories', 24, GREY_A).next_to(folder, DOWN, buff=0.25)
        self.play(FadeIn(most), LaggedStart(*[FadeIn(b, shift=DOWN * 0.15) for b in bins], lag_ratio=0.2))

        # [V11.5d] ManimOnline's own tests
        self.at("Mannim Online's own tests")
        summary = VGroup(Text(f'{PYTHON_TESTS} Python tests · {JS_TESTS} JavaScript tests', font_size=32),
                         note('browser checks in Chromium, Firefox and WebKit', 28, GREY_A)).arrange(DOWN, buff=0.25)
        panel = box(summary.width + 0.9, summary.height + 0.7).move_to(summary)
        VGroup(panel, summary).move_to(DOWN * 1.8)
        self.play(FadeIn(panel), FadeIn(summary[0]))
        self.at('three different browser engines')
        self.play(FadeIn(summary[1]))
        self.finish()


# ---------------------------------------------------------------- 11.6

class Segment_11_6(Segment):
    """Case study: the straight path (q11-01)."""
    EPISODE, SEGMENT = 11, '11.6'

    def construct(self):
        intro = Text('Case studies', font_size=44)
        self.play(FadeIn(intro))

        # [V11.6a] q11-01 at 80 %, its corners traced
        self.at('The collapsing square')
        self.play(FadeOut(intro))
        k, lift = 0.8, UP * 0.5
        place = lambda m: m.scale(k, about_point=ORIGIN).shift(lift)  # noqa: E731
        left = place(Square(2.5, color=BLUE).shift(LEFT * 3.2))
        right = place(Square(2.5, color=YELLOW).shift(RIGHT * 3.2))
        titles = VGroup(place(Text('.animate.rotate(PI)', font_size=28).to_edge(UP).shift(LEFT * 3.2)),
                        place(Text('Rotate(PI)', font_size=28).to_edge(UP).shift(RIGHT * 3.2)))
        traces = [TracedPath(lambda s=s, i=i: s.get_vertices()[i], stroke_color=c, stroke_width=3)
                  for s, c in ((left, BLUE), (right, YELLOW)) for i in range(4)]
        card = qr_card('q11-01')
        self.play(FadeIn(left), FadeIn(right), FadeIn(titles), FadeIn(card, shift=UP * 0.2))
        self.add(*traces)

        # [V11.6b] the left square's width over time
        axes = Axes(x_range=[0, 4, 1], y_range=[0, 2.5, 1], x_length=4.0, y_length=1.3, tips=False,
                    axis_config={'stroke_width': 2, 'color': GREY_B}).move_to([-3.0, -2.9, 0])
        axes_tag = note('width of the left square', 20, BLUE).next_to(axes, UP, buff=0.1)
        start = self.renderer.time
        samples = []

        def record(m):
            samples.append((self.renderer.time - start, left.width / k))
            if len(samples) > 1:
                m.set_points_as_corners([axes.c2p(t, w) for t, w in samples])
        curve = VMobject(stroke_color=BLUE, stroke_width=4).set_points_as_corners([axes.c2p(0, 2.5), axes.c2p(0, 2.5)])
        curve.add_updater(record)
        self.add(axes, axes_tag, curve)
        self.at('each corner travels in a straight line')
        start = self.renderer.time
        samples.clear()
        self.play(left.animate.rotate(PI), Rotate(right, PI), run_time=4)
        curve.clear_updaters()
        zero = note('0 at the midpoint', 20, FOCUS).next_to(axes.c2p(2, 0), UP, buff=0.15)
        self.play(FadeIn(zero))

        # [V11.6c] pose blended as one complex number
        self.at('stores shapes differently')
        self.play(FadeOut(VGroup(left, right, titles, *traces, axes, axes_tag, curve, zero, card)))
        pose = VGroup(note('position', 26, GREY_A), note('scale and rotation', 26, FOCUS), note('outline', 26, GREY_A)).arrange(RIGHT, buff=0.8)
        pose.move_to(UP * 2.4)
        self.play(FadeIn(pose, lag_ratio=0.2))
        self.at('a naive blend')
        naive = VGroup(note('angle from 0 to π:', 26, WARNING), note('a rigid spin', 26, WARNING)).arrange(RIGHT, buff=0.3).move_to(UP * 1.2)
        self.play(FadeIn(naive))
        self.at('a single complex number')
        blend = MathTex(r'z = s\,e^{i\theta}', r'\qquad z(t) = (1-t)\cdot 1 + t\cdot(-1) = 1 - 2t', font_size=40)
        blend.move_to(DOWN * 0.1)
        self.play(Write(blend))
        midpoint = MathTex(r'z\!\left(\tfrac12\right) = 0', font_size=40, color=FOCUS).next_to(blend, DOWN, buff=0.4)
        self.play(FadeIn(midpoint))
        self.at('faithfully reproducing the collapse')
        same = note("the same straight paths as Manim's point by point blend", 26, AFTER).next_to(midpoint, DOWN, buff=0.4)
        self.play(FadeIn(same))
        self.finish()


# ---------------------------------------------------------------- 11.7

class Segment_11_7(Segment):
    """Case study: arrow tips keep their size (q11-02)."""
    EPISODE, SEGMENT = 11, '11.7'

    def construct(self):
        # [V11.7a] q11-02
        arrow = Arrow(LEFT * 3, RIGHT * 3, buff=0, color=YELLOW).shift(UP * 1.5)
        shaft = Line(LEFT * 3, RIGHT * 2.7)
        head = Triangle(color=BLUE, fill_opacity=1).scale(0.3).rotate(-PI / 2).move_to(RIGHT * 2.75)
        homemade = VGroup(shaft, head).set_color(BLUE).shift(DOWN * 1.5)
        labels = VGroup(Text('Arrow', font_size=28).next_to(arrow, UP), Text('Line + Triangle', font_size=28).next_to(homemade, UP))
        card = qr_card('q11-02', corner=UR)
        self.add(arrow, homemade, labels)
        self.play(FadeIn(card, shift=UP * 0.2), run_time=0.5)
        self.play(arrow.animate.scale(0.4), homemade.animate.scale(0.4), run_time=2)
        self.play(arrow.animate.scale(2.5), homemade.animate.scale(2.5), run_time=2)
        self.at('Compare the home-made arrow')
        self.play(arrow.animate.scale(0.4), homemade.animate.scale(0.4), run_time=2)
        self.wait(1.5)

        # [V11.7b] remove the tip, scale the shaft, put the tip back
        self.at('it takes its tip off')
        self.play(FadeOut(VGroup(arrow, homemade, labels, card)))
        steps = VGroup()
        for words in ('take the tip off', 'scale the shaft', 'attach the tip again'):
            steps.add(note(words, 24, GREY_A))
        steps.arrange(RIGHT, buff=1.4).move_to(UP * 2.8)
        pictures = VGroup()
        full = Arrow(LEFT * 1.5, RIGHT * 1.5, buff=0, color=YELLOW)
        tip = full.tip.copy()
        bare = Line(LEFT * 1.5, full.tip.get_left()[0] * RIGHT, color=YELLOW, stroke_width=6)
        one = VGroup(bare, tip.shift(RIGHT * 0.4)).move_to(steps[0]).shift(DOWN * 1.0)
        two = VGroup(Line(LEFT * 0.6, RIGHT * 0.6, color=YELLOW, stroke_width=6), full.tip.copy().shift(RIGHT * 0.4)).move_to(steps[1]).shift(DOWN * 1.0)
        two[1].next_to(two[0], RIGHT, buff=0.4)
        three = Arrow(LEFT * 0.75, RIGHT * 0.75, buff=0, color=YELLOW).move_to(steps[2]).shift(DOWN * 1.0)
        pictures.add(one, two, three)
        joins = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.25, color=GREY_B, stroke_width=3) for a, b in zip(steps, steps[1:])])
        self.play(FadeIn(steps[0]), FadeIn(one))
        self.at('scales the shaft')
        self.play(GrowArrow(joins[0]), FadeIn(steps[1]), FadeIn(two))
        self.at('attaches the tip again')
        self.play(GrowArrow(joins[1]), FadeIn(steps[2]), FadeIn(three))

        # [V11.7c] the tip is capped relative to the arrow's length
        self.at('up to a limit')
        short = VGroup(*[Arrow(ORIGIN, RIGHT * length, buff=0, color=YELLOW) for length in (4.0, 1.6, 0.8, 0.4)])
        short.arrange(RIGHT, buff=0.7, aligned_edge=DOWN).move_to(DOWN * 1.4)
        lengths = VGroup(*[note(f'length {a.get_length():.1f}', 20, GREY_A).next_to(a, DOWN, buff=0.25) for a in short])
        self.play(LaggedStart(*[GrowArrow(a) for a in short], lag_ratio=0.2), FadeIn(lengths))
        capped = note("tips are capped at a quarter of the arrow's length", 24, FOCUS).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(capped))
        self.at('mirrors')
        literal = note('manim-lite: the same three steps, literally', 26, AFTER).next_to(pictures, DOWN, buff=0.2)
        self.play(FadeIn(literal))
        self.finish()


# ---------------------------------------------------------------- 11.8

class Segment_11_8(Segment):
    """Case study: same font size, different heights (q11-05)."""
    EPISODE, SEGMENT = 11, '11.8'

    def construct(self):
        # [V11.8a] q11-05
        text = Text('Manim', font_size=96, font='Helvetica')   # a Liberation Sans match, as in manim-lite's reference
        tex = Tex('Manim', font_size=96)
        VGroup(text, tex).arrange(RIGHT, buff=1.5).shift(UP * 0.4)
        boxes = VGroup(*[SurroundingRectangle(m, buff=0, color=YELLOW) for m in (text, tex)])
        captions = VGroup(Text('Text("Manim", font_size=96)', font_size=24, font='Helvetica').next_to(text, UP, buff=0.8),
                          Tex(r'Tex("Manim", font\_size=96)', font_size=32).next_to(tex, UP, buff=0.8))
        card = qr_card('q11-05')
        self.add(captions, card)
        self.play(Write(text), Write(tex))
        self.play(Create(boxes))
        heights = VGroup(*[Text(f'height {m.height:.3f}', font_size=28).next_to(m, DOWN, buff=0.6) for m in (text, tex)])
        self.play(FadeIn(heights))
        self.wait(2)

        # [V11.8b] two rules for the em square, drawn to scale
        self.at('each converts font size into screen units')
        self.play(FadeOut(VGroup(text, tex, boxes, captions, heights, card)))
        ems = VGroup()
        for words, size, color in (('Text: em = font_size / 72', 96 / 72, BLUE), ('Tex: em = font_size / 96', 96 / 96, AFTER)):
            square = Square(size).set_stroke(color, 4).set_fill(color, 0.15)
            label = MathTex(r'\text{' + words.split(':')[0] + r'}:\ ' + (r'\frac{96}{72} = 1.333' if size > 1 else r'\frac{96}{96} = 1'),
                            font_size=36, color=color).next_to(square, DOWN, buff=0.3)
            ems.add(VGroup(square, label))
        ems.arrange(RIGHT, buff=2.0, aligned_edge=DOWN).move_to(DOWN * 0.2)
        rules = VGroup(note('Text: em = font size ÷ 72', 28, BLUE), note('Tex: em = font size ÷ 96', 28, AFTER)).arrange(RIGHT, buff=1.6)
        rules.to_edge(UP, buff=0.6)
        self.at('For Text')
        self.play(FadeIn(rules[0]), DrawBorderThenFill(ems[0][0]), FadeIn(ems[0][1]))
        self.at('For tek')
        self.play(FadeIn(rules[1]), DrawBorderThenFill(ems[1][0]), FadeIn(ems[1][1]))
        unit = note('in scene units, at font size 96', 22, GREY_A).next_to(ems, DOWN, buff=0.3)
        self.play(FadeIn(unit))

        # [V11.8c] measured, not assumed
        self.at("Those numbers weren't guessed")
        measured = note('measured from Manim 0.22, not assumed', 30, FOCUS).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(measured))
        self.finish()


# ---------------------------------------------------------------- 11.9

def graph_scene():
    vertices = list(range(1, 9))
    edges = [(1, 2), (2, 3), (3, 4), (4, 1), (1, 5), (2, 6), (3, 7), (4, 8), (5, 6), (7, 8)]
    return Graph(vertices, edges, layout='spring', layout_config={'seed': 3}, labels=True)


class Segment_11_9(Segment):
    """Case study: randomness, exactly (q11-03, q11-04)."""
    EPISODE, SEGMENT = 11, '11.9'

    def construct(self):
        # [V11.9a] q11-03: stream lines from jittered starting points
        stream = StreamLines(swirl, stroke_width=2, max_anchors_per_line=15, virtual_time=1.5,
                             x_range=[-6, 6, 1.5], y_range=[-3.5, 3.5, 1.5])
        card = qr_card('q11-03')
        self.play(stream.create(), FadeIn(card, shift=UP * 0.2), run_time=2)
        self.add(stream)
        stream.start_animation(warm_up=False, flow_speed=1.5)
        self.at('a little random jitter')
        crosses = VGroup(*[cross_mark(0.06, YELLOW).set_stroke(width=3).move_to(line.get_start()) for line in stream.stream_lines])
        self.play(FadeIn(crosses))
        self.wait(3.5)

        # [V11.9b] manim-lite's starting points land on Manim's
        self.at('computer randomness is reproducible')
        self.play(stream.end_animation())
        rings = VGroup(*[Circle(radius=0.12, color=AFTER, stroke_width=3).move_to([x, y, 0]) for x, y in LITE_STARTS])
        legend = VGroup(VGroup(cross_mark(0.08, YELLOW).set_stroke(width=3), note('Manim, seed 0', 24, YELLOW)).arrange(RIGHT, buff=0.2),
                        VGroup(Circle(radius=0.12, color=AFTER, stroke_width=3), note('manim-lite, seed 0', 24, AFTER)).arrange(RIGHT, buff=0.2))
        legend.arrange(RIGHT, buff=0.8).to_edge(UP, buff=0.25)
        legend = backed(legend)
        self.play(FadeOut(card), FadeIn(legend))
        self.play(LaggedStart(*[Create(r) for r in rings], lag_ratio=0.02), run_time=2)
        every = backed(note('all 54 starting points identical', 26, AFTER).to_edge(DOWN, buff=0.4))
        self.play(FadeIn(every))

        # [V11.9c] q11-04: seeded spring layouts
        self.at('the networkx library')
        self.play(FadeOut(VGroup(crosses, rings, legend, every)))
        graph = graph_scene()
        card = qr_card('q11-04')
        self.play(Create(graph), FadeIn(card, shift=UP * 0.2), run_time=2)
        self.play(graph.animate.change_layout('circular'), run_time=2)
        self.play(graph.animate.change_layout('spring', layout_config={'seed': 7}), run_time=2)

        # [V11.9d] seed → generator → numbers → positions
        self.at('exact reimplementations')
        self.play(FadeOut(graph), FadeOut(card))
        rows = VGroup()
        for name, used, numbers in (('PCG64', 'stream lines (NumPy)', '0.6370, 0.2698, 0.0410, …'),
                                    ('Mersenne Twister', 'graph layouts (networkx)', '0.5508, 0.7081, 0.2909, …')):
            seed = chip('seed', GREY_A, 24)
            generator = labelled_box(name, 3.2, 0.8, 26, FOCUS)
            out = code_text(numbers, 24, GREY_A)
            row = VGroup(seed, generator, out).arrange(RIGHT, buff=0.9)
            links = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.15, color=GREY_B, stroke_width=3) for a, b in zip(row, row[1:])])
            use = note(used, 22, GREY_B).next_to(generator, DOWN, buff=0.15)
            rows.add(VGroup(row, links, use))
        rows.arrange(DOWN, buff=0.9).move_to(UP * 0.2)
        rows[0][0][0][1].become(Text('seed 0', font_size=24).move_to(rows[0][0][0][1]))
        rows[1][0][0][1].become(Text('seed 3', font_size=24).move_to(rows[1][0][0][1]))
        self.at('P C G sixty four')
        self.play(FadeIn(rows[0]))
        self.at('Mersenne Twister')
        self.play(FadeIn(rows[1]))
        self.at('Same seed, same numbers')
        same = note('same seed, same numbers, same picture', 30, AFTER).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(same))
        self.finish()


# ---------------------------------------------------------------- 11.10

class Segment_11_10(Segment):
    """Case study: the order of addition."""
    EPISODE, SEGMENT = 11, '11.10'

    def construct(self):
        # [V11.10a] one sum, two orders
        sums = VGroup(code_text(f'(0.1 + 0.2) + 0.3  →  {(0.1 + 0.2) + 0.3!r}', 34, GREY_A),
                      code_text(f'0.1 + (0.2 + 0.3)  →  {0.1 + (0.2 + 0.3)!r}', 34, GREY_A)).arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        sums.move_to(UP * 1.6)
        self.play(FadeIn(sums[0]))
        self.play(FadeIn(sums[1]))
        self.at('in the sixteenth decimal place')
        last = chars(sums[0], f'(0.1 + 0.2) + 0.3  →  {(0.1 + 0.2) + 0.3!r}', len(f'(0.1 + 0.2) + 0.3  →  {(0.1 + 0.2) + 0.3!r}') - 1)
        self.play(last.animate.set_color(WARNING).scale(1.3))
        self.at('rounding happens at every step')
        rounding = note('every step rounds to the nearest representable number', 24, GREY_A).next_to(sums, DOWN, buff=0.4)
        self.play(FadeIn(rounding))

        # [V11.10b] a search along a curve that ends on a near tie
        self.at('finding where along a curve')
        self.play(FadeOut(VGroup(sums, rounding)))
        curve = CubicBezier(LEFT * 5 + DOWN * 1.5, LEFT * 2 + UP * 2.5, RIGHT * 2 + DOWN * 2.5, RIGHT * 5 + UP * 1.0, color=BLUE)
        target = curve.point_from_proportion(0.62)
        goal = Dot(target, color=FOCUS, radius=0.1)
        self.play(Create(curve), FadeIn(goal))
        lo, hi = 0.0, 1.0
        marks = VGroup()
        for _ in range(5):
            mid = (lo + hi) / 2
            mark = Line(UP * 0.25, DOWN * 0.25, color=GREY_A, stroke_width=4).move_to(curve.point_from_proportion(mid))
            marks.add(mark)
            self.play(FadeIn(mark), run_time=0.35)
            lo, hi = (mid, hi) if mid < 0.62 else (lo, mid)
        self.at('can land on a near tie')
        pair = VGroup(Dot(curve.point_from_proportion(0.6199), radius=0.08, color=WARNING), Dot(curve.point_from_proportion(0.6201), radius=0.08, color=AFTER))
        tie = note('two candidates, a hair apart: the last digit decides', 24, WARNING).to_edge(DOWN, buff=0.9)
        self.play(FadeIn(pair), FadeIn(tie))

        # [V11.10c] same additions, same order
        self.at('the exact order in which num pie adds things up')
        order = note('same additions, in the same order as Manim', 30, AFTER).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(order))
        self.finish()


# ---------------------------------------------------------------- 11.11

class Segment_11_11(Segment):
    """What manim-lite is not."""
    EPISODE, SEGMENT = 11, '11.11'

    def construct(self):
        # [V11.11a] the subset inside Manim Community
        outer = Circle(radius=3.0, color=BLUE).set_fill(BLUE, 0.1).move_to([-2.6, 0.2, 0])
        inner = Circle(radius=1.3, color=AFTER).set_fill(AFTER, 0.2).move_to(outer).shift(DOWN * 0.6)
        outer_tag = Text('Manim Community', font_size=28, color=BLUE).move_to(outer.get_top() + DOWN * 0.55)
        inner_tag = Text('manim-lite', font_size=28, color=AFTER).move_to(inner)
        self.play(DrawBorderThenFill(outer), FadeIn(outer_tag), DrawBorderThenFill(inner), FadeIn(inner_tag))
        outside = [('real lay tek', 'real LaTeX packages'), ("your computer's fonts", 'your installed fonts'),
                   ('fifteen frames per second', '60 fps and high resolution'), ("features it doesn't support", 'OpenGL renderer, writing files')]
        labels = VGroup(*[note(words, 24, GREY_A) for _, words in outside]).arrange(DOWN, aligned_edge=LEFT, buff=0.45)
        labels.move_to([3.6, 0.6, 0])
        for (phrase, _), label in zip(outside, labels):
            self.at(phrase)
            self.play(FadeIn(label, shift=LEFT * 0.2), run_time=0.6)

        # [V11.11b] unsupported means an honest error
        self.at('say so with a clear error')
        self.play(FadeOut(VGroup(outer, inner, outer_tag, inner_tag, labels)))
        code = code_panel('self.play(self.camera.frame.animate.rotate(PI / 6))', font_size=26, line_numbers=False)
        error = Text(UNSUPPORTED.replace(': ', ':\n', 1), font=MONO, font_size=24, color=WARNING, line_spacing=0.9)
        panel = VGroup(box(error.width + 0.8, error.height + 0.7, WARNING, fill='#2a1517', radius=0.1), error)
        error.move_to(panel[0])
        VGroup(code, panel).arrange(DOWN, buff=0.5).move_to(UP * 0.6)
        self.play(FadeIn(code))
        self.play(FadeIn(panel, shift=UP * 0.2))
        self.at('A wrong picture that looks plausible')
        honest = note('unsupported means an honest error, never a silent guess', 30, FOCUS).to_edge(DOWN, buff=0.7)
        self.play(FadeIn(honest))
        self.finish()


# ---------------------------------------------------------------- 11.12

class Segment_11_12(Segment):
    """Recap."""
    EPISODE, SEGMENT = 11, '11.12'

    def construct(self):
        # [V11.12a] the episode in five icons
        items = [('straight paths', 'straight paths'), ('fixed tips', 'fixed tips'), ('two font scales', 'two font scales'),
                 ('exact random numbers', 'exact random numbers'), ('order of addition', 'even the order of addition')]
        icons = VGroup()
        cross = VGroup(Line(UL, DR), Line(UR, DL)).scale(0.5).set_stroke(BLUE, 5)
        icons.add(cross)
        icons.add(Arrow(LEFT * 0.7, RIGHT * 0.7, buff=0, color=YELLOW))
        icons.add(VGroup(Square(1.0).set_stroke(BLUE, 3), Square(0.75).set_stroke(AFTER, 3)).arrange(RIGHT, buff=0.15, aligned_edge=DOWN))
        icons.add(VGroup(Circle(radius=0.4, color=FOCUS), Text('0', font_size=30, color=FOCUS)))
        icons.add(code_text('0.6 ≠ 0.6000000000000001', 18, GREY_A))
        tiles = VGroup()
        for icon, (words, _) in zip(icons, items):
            if icon.width > 2.2:
                icon.scale_to_fit_width(2.2)
            tiles.add(VGroup(icon, note(words, 22, GREY_A).next_to(icon, DOWN, buff=0.25)))
        tiles.arrange(RIGHT, buff=0.45, aligned_edge=DOWN).move_to(DOWN * 0.6)
        sources = VGroup(*[chip(w, AFTER, 22) for w in ('recorded references', 'documentation examples', 'random scenes', "Manim's own tests")])
        sources.arrange(RIGHT, buff=0.3).move_to(UP * 2.2)
        measure = note('the only way to know is to measure', 28, FOCUS).next_to(sources, UP, buff=0.3)
        self.at('the only way to know is to measure')
        self.play(FadeIn(measure))
        for phrase, s in zip(('recorded references', 'every documentation example', 'random scenes', "Mannim's own tests"), sources):
            self.at(phrase)
            self.play(FadeIn(s, shift=DOWN * 0.1), run_time=0.4)
        for (_, phrase), tile in zip(items, tiles):
            self.at(phrase)
            self.play(FadeIn(tile, shift=UP * 0.15), run_time=0.5)

        # [V11.12b] the QR wall, 10 seconds
        self.at('One question remains', lead=0.5)
        wall = qr_wall([f'q11-0{i}' for i in range(1, 6)])
        heading = Text('Episode 11 · scan to open each scene', font_size=26, color=SCAFFOLD).to_corner(UL, buff=0.3)
        self.play(FadeOut(VGroup(measure, sources, tiles)), FadeIn(wall), FadeIn(heading))
        self.wait(10)

        # [V11.12c] teaser: a QR code dissolves into the letters it carries (episode 12)
        self.play(FadeOut(VGroup(wall, heading)))
        code = qr_code('q11-01', 2.6).move_to(UP * 0.6)
        self.play(FadeIn(code))
        cid = next(r['cid'] for r in json.loads((SERIES / 'qr-links.json').read_text()) if r['id'] == 'q11-01')
        letters = VGroup(*[Text(cid[i:i + 32], font=MONO, font_size=26, color=FOCUS) for i in range(0, len(cid), 32)]).arrange(DOWN, buff=0.12)
        letters.move_to(code)
        self.play(FadeTransform(code, letters), run_time=1.5)
        nxt = Text('Next: Links that carry code', font_size=34).to_edge(DOWN, buff=0.6)
        self.play(Write(nxt))
        self.wait(1.5)
        self.finish()
