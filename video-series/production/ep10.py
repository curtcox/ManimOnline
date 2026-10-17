"""Episode 10 · Python in a browser tab. One Scene per script segment.

    python3 video-series/production/render.py 10 [-ql] [segment ...]

Shot ids in comments ([V10.4c] ...) refer to episodes/10-python-in-a-browser-tab.md.
ManimOnline previews run at 15 frames per second; the snippet replays that depend on it
(q10-02's dot per frame) count frames at 15 per second, not at the production's 60.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403
from ep09 import (backed, box, check_mark, chip, cloud, cross_mark, file_icon, labelled_box,  # noqa: E402
                  note, on_stage, pointer, stage_frame, terminal)

WHERE_SNIPPET = 'ep10/01-where-am-i.py'
DOTS_SNIPPET = 'ep10/02-one-dot-per-frame.py'
NUMPY_SNIPPET = 'ep10/03-numpy-on-demand.py'
FORMULAS_SNIPPET = 'ep10/04-measured-formulas.py'
CLOCK_SNIPPET = 'ep10/05-frame-clock.py'

PREVIEW_FPS = 15
# What q10-01 printed in ManimOnline (Pyodide 0.27.0) and on the Mac this series was made on.
IN_BROWSER = ('3.12.7', 'emscripten', 'wasm32')
ON_LAPTOP = ('3.14.8', 'darwin', 'arm64')
# manim-lite's first-pass (estimated) boxes for q10-04's formulas, width by height in units.
ESTIMATED_BOXES = [(2.575, 0.85), (1.75, 0.85), (3.125, 0.85)]
# q10-02 rendered by manim-lite: 76 frames as plain JSON, and pooled as the worker sends them.
PLAIN_BYTES, POOLED_BYTES = 1_492_757, 129_908


# ---------------------------------------------------------------- small pieces

def facts(values, scale=1.0):
    """q10-01's three lines with the given Python version, platform and machine."""
    version, platform_name, machine = values
    lines = VGroup(Text(f'Python {version}', font_size=48), Text(f'sys.platform = {platform_name}', font_size=40, color=YELLOW),
                   Text(f'machine = {machine}', font_size=40, color=BLUE)).arrange(DOWN, buff=0.5)
    return lines.scale(scale)


def ticket(words, color=BLACK, paper='#f3efe0', font_size=20):
    text = Text(words, font_size=font_size, color=color)
    card = Rectangle(width=text.width + 0.3, height=text.height + 0.25).set_fill(paper, 1).set_stroke(GREY_B, 1)
    return VGroup(card, text.move_to(card))


def cook(apron=WHITE):
    head = Circle(radius=0.28).set_fill('#e8c39e', 1).set_stroke(width=0)
    hat = VGroup(RoundedRectangle(width=0.5, height=0.26, corner_radius=0.06),
                 Circle(radius=0.17).shift(UP * 0.2 + LEFT * 0.12), Circle(radius=0.2).shift(UP * 0.24 + RIGHT * 0.1))
    hat.set_fill(WHITE, 1).set_stroke(width=0).next_to(head, UP, buff=-0.1)
    body = RoundedRectangle(width=0.85, height=1.0, corner_radius=0.25).set_fill(apron, 1).set_stroke(GREY_B, 2)
    body.next_to(head, DOWN, buff=0.03)
    return VGroup(body, head, hat)


def stove():
    top = Rectangle(width=1.4, height=0.9).set_fill('#3a3f47', 1).set_stroke(GREY_B, 2)
    pot = Rectangle(width=0.75, height=0.45).set_fill('#7b8794', 1).set_stroke(GREY_A, 2).next_to(top, UP, buff=0)
    spoon = Line(pot.get_top() + DOWN * 0.1, pot.get_top() + UP * 0.45 + RIGHT * 0.15, color=GREY_A, stroke_width=5)
    return VGroup(top, pot, spoon)


def room(width, height, label, color=GREY_B):
    frame = box(width, height, color, fill='#101418', radius=0.1, stroke=3)
    tag = note(label, 24, color).next_to(frame, DOWN, buff=0.15)
    return VGroup(frame, tag)


def bin_icon(color=GREY_B):
    body = Polygon([-0.35, 0.35, 0], [0.35, 0.35, 0], [0.27, -0.4, 0], [-0.27, -0.4, 0]).set_stroke(color, 3)
    lid = Line([-0.45, 0.45, 0], [0.45, 0.45, 0], color=color, stroke_width=4)
    ribs = VGroup(*[Line([x, 0.25, 0], [x * 0.8, -0.3, 0], color=color, stroke_width=2) for x in (-0.15, 0, 0.15)])
    return VGroup(body, lid, ribs)


def field(key, value, color=GREY_A):
    return Text(f'{key}: {value}', font=MONO, font_size=18, color=color)


# ---------------------------------------------------------------- 10.1

class Segment_10_1(Segment):
    """Cold open: where is this Python? (q10-01)"""
    EPISODE, SEGMENT = 10, '10.1'

    def construct(self):
        code = code_panel(snippet_lines(WHERE_SNIPPET, 9, 13), font_size=20, line_numbers=False)
        fit(code, 8.6).to_corner(DL, buff=0.35)
        card = qr_card('q10-01')
        self.play(FadeIn(code), FadeIn(card, shift=UP * 0.2))

        # [V10.1b] on a laptop
        self.at('Run it on a laptop')
        shell = terminal(6.2, 3.0).move_to([3.4, 1.4, 0])
        laptop = facts(ON_LAPTOP, 0.55).move_to(shell[0]).shift(DOWN * 0.15)
        laptop_tag = note('on a laptop', 24, GREY_A).next_to(shell, UP, buff=0.15)
        self.play(FadeIn(shell), FadeIn(laptop_tag))
        self.play(LaggedStart(*[FadeIn(f) for f in laptop], lag_ratio=0.5), run_time=1.5)

        # [V10.1a] in ManimOnline
        self.at('Run it in Mannim Online')
        frame = stage_frame(6.2).move_to([-3.4, 1.4, 0])
        browser = facts(IN_BROWSER, 0.55).move_to(frame)
        browser_tag = note('in ManimOnline', 24, GREY_A).next_to(frame, UP, buff=0.15)
        self.play(FadeIn(frame), FadeIn(browser_tag))
        self.play(LaggedStart(*[Write(f) for f in browser], lag_ratio=0.5), run_time=2.5)

        # [V10.1c] emscripten and wasm32 circled
        self.at('Those words mean')
        rings = VGroup(*[Ellipse(width=browser[i][-len(word):].width + 0.4, height=browser[i].height + 0.35, color=FOCUS, stroke_width=4)
                         .move_to(browser[i][-len(word):]) for i, word in ((1, 'emscripten'), (2, 'wasm32'))])
        self.play(Create(rings), run_time=1.2)
        self.at('inside a single tab')
        tab = note('a browser tab', 24, FOCUS).next_to(frame, DOWN, buff=0.2)
        self.play(FadeIn(tab, shift=UP * 0.1))
        self.at('an imaginary processor')
        chip_ = chip('an imaginary processor', BLUE, 24).next_to(tab, DOWN, buff=0.25)
        self.play(FadeIn(chip_))
        self.at('the surprisingly delicate problem of stopping it')
        stop = RegularPolygon(8, radius=0.45).rotate(PI / 8).set_fill(WARNING, 1).set_stroke(WHITE, 3)
        stop = VGroup(stop, Text('STOP', font_size=18, weight=BOLD).move_to(stop)).next_to(shell, DOWN, buff=0.35)
        self.play(FadeIn(stop, scale=0.6))
        self.finish()


# ---------------------------------------------------------------- 10.2

def server_rack(color=GREY_B):
    units = VGroup(*[box(1.8, 0.45, color, radius=0.05, stroke=2) for _ in range(4)]).arrange(DOWN, buff=0.08)
    lights = VGroup(*[Dot(u.get_left() + RIGHT * 0.2, radius=0.05, color=AFTER) for u in units])
    return VGroup(units, lights)


class Segment_10_2(Segment):
    """Why not just use a server?"""
    EPISODE, SEGMENT = 10, '10.2'

    def construct(self):
        # [V10.2a] code goes to a server, video comes back
        browser = browser_icon(3.6, 2.4).move_to([-4.6, 1.2, 0])
        server = server_rack().move_to([4.4, 1.2, 0])
        tags = VGroup(note('your browser', 24, GREY_A).next_to(browser, UP, buff=0.15),
                      note('a server', 24, GREY_A).next_to(server, UP, buff=0.15))
        self.play(FadeIn(browser), FadeIn(server), FadeIn(tags))
        self.at('Your browser sends code')
        there = Arrow(browser.get_right() + UP * 0.4, server.get_left() + UP * 0.4, buff=0.2, color=GREY_B, stroke_width=4)
        back = Arrow(server.get_left() + DOWN * 0.4, browser.get_right() + DOWN * 0.4, buff=0.2, color=GREY_B, stroke_width=4)
        code = chip('code', BLUE, 22, mono=True).move_to(there.get_start())
        video = chip('video', AFTER, 22).move_to(back.get_start())
        self.play(GrowArrow(there), FadeIn(code))
        self.play(code.animate.move_to(there.get_end() + LEFT * 0.5), run_time=1.2)
        self.at('the video comes back')
        self.play(GrowArrow(back), FadeIn(video))
        self.play(video.animate.move_to(back.get_end() + RIGHT * 0.6), run_time=1.2)

        # [V10.2b] what the server takes on
        problems = [('Run arbitrary code', "strangers' code"), ('loop forever', 'runs forever'), ('fill the disk', 'fills the disk'),
                    ('attack the machine', 'attacks the machine'), ('locked-down sandbox', 'isolation'),
                    ('limits on time and memory', 'time and memory limits'), ('storage for every result', 'storage'),
                    ('costs real money', 'cost per render')]
        labels = VGroup(*[chip(words, WARNING, 22) for _, words in problems])
        labels.arrange_in_grid(rows=4, cols=2, buff=(0.3, 0.25), flow_order='dr').move_to([2.2, -2.0, 0])
        for (phrase, _), label in zip(problems, labels):
            self.at(phrase)
            self.play(FadeIn(label, shift=DOWN * 0.15), run_time=0.5)

        # [V10.2c] a static site: just files; the browser runs the Python
        self.at('a static site')
        outline = DashedVMobject(RoundedRectangle(width=2.4, height=2.4, corner_radius=0.15), num_dashes=40).set_stroke(GREY_B, 2)
        outline.move_to(server)
        files = VGroup(*[file_icon(kind, GREY_B, 0.6, 0.78) for kind in ('html', 'js', 'py')]).arrange(RIGHT, buff=0.15).move_to(outline)
        static = note('static site: just files', 24, GREY_A).next_to(outline, UP, buff=0.15)
        self.play(FadeOut(VGroup(server, labels, code, video, there, back)), FadeOut(tags[1]), Create(outline), FadeIn(files), FadeIn(static))
        self.at('GitHub Pages')
        pages = note('GitHub Pages', 24, GREY_B).next_to(outline, DOWN, buff=0.15)
        self.play(FadeIn(pages))
        self.at('no server-side program')
        none = note('no program runs here', 24, WARNING).next_to(pages, DOWN, buff=0.2)
        self.play(FadeIn(none))
        self.at('the only computer available')
        python = chip('Python', FOCUS, 30).move_to(browser).shift(DOWN * 0.2)
        self.play(browser.animate.scale(1.25, about_edge=DOWN), FadeIn(python, scale=0.5))
        python.move_to(browser).shift(DOWN * 0.2)
        self.play(Indicate(python, color=FOCUS))
        self.finish()


# ---------------------------------------------------------------- 10.3

class Segment_10_3(Segment):
    """WebAssembly and Pyodide (q10-03)."""
    EPISODE, SEGMENT = 10, '10.3'

    def construct(self):
        # [V10.3b] WebAssembly runs sandboxed in the browser, next to JavaScript
        browser = browser_icon(6.4, 3.6).move_to([-3.2, 1.0, 0])
        sandbox = DashedVMobject(RoundedRectangle(width=5.6, height=2.4, corner_radius=0.12), num_dashes=50).set_stroke(FOCUS, 2)
        sandbox.move_to(browser).shift(DOWN * 0.2)
        sandbox_tag = note('sandbox', 20, FOCUS).next_to(sandbox, UP, buff=0.05).align_to(sandbox, RIGHT)
        js = labelled_box('JavaScript', 2.3, 1.0, 26).move_to(sandbox).shift(LEFT * 1.35)
        wasm = labelled_box('WebAssembly', 2.5, 1.0, 26, BLUE).move_to(sandbox).shift(RIGHT * 1.3)
        self.play(FadeIn(browser), Create(sandbox), FadeIn(sandbox_tag), FadeIn(js))
        self.play(FadeIn(wasm, shift=UP * 0.2))
        self.at('nearly as fast as native code')
        fast = note('nearly as fast as native code', 22, GREY_A).next_to(browser, DOWN, buff=0.2)
        self.play(FadeIn(fast))

        # [V10.3a] CPython is a C program: compile it to WebAssembly
        self.at('the standard Python interpreter')
        cpython = labelled_box('CPython\n(written in C)', 2.8, 1.3, 26).move_to([2.4, 2.4, 0])
        self.play(FadeIn(cpython))
        self.at('Compile that C to WebAssembly')
        result = labelled_box('WebAssembly', 2.8, 1.0, 26, BLUE).move_to([2.4, -0.4, 0])
        compile_ = Arrow(cpython.get_bottom(), result.get_top(), buff=0.12, color=GREY_B, stroke_width=4)
        compile_tag = note('compile with Emscripten', 22, GREY_A).next_to(compile_, RIGHT, buff=0.15)
        self.play(GrowArrow(compile_), FadeIn(compile_tag), FadeIn(result))
        self.at('That project is called')
        pyodide = note('Pyodide', 34, FOCUS).next_to(result, DOWN, buff=0.2)
        self.play(FadeIn(pyodide, scale=0.7), result[0].animate.set_stroke(FOCUS))
        self.at('are the names')
        names = VGroup(VGroup(Text('emscripten', font=MONO, font_size=24, color=FOCUS), note('the compiler toolchain', 22, GREY_A)),
                       VGroup(Text('wasm32', font=MONO, font_size=24, color=FOCUS), note('the imaginary processor', 22, GREY_A)))
        for pair in names:
            pair.arrange(RIGHT, buff=0.3)
        names.arrange(DOWN, aligned_edge=LEFT, buff=0.25).to_edge(DOWN, buff=0.4).shift(LEFT * 2.6)
        self.play(FadeOut(fast), LaggedStart(*[FadeIn(n, shift=RIGHT * 0.2) for n in names], lag_ratio=0.5))

        # [V10.3c] the first visit downloads the interpreter; later visits keep it
        self.at('The cost is a download')
        self.play(FadeOut(VGroup(browser, sandbox, sandbox_tag, js, wasm, cpython, compile_, compile_tag, result, pyodide, names)))
        bars = VGroup()
        for words in ('first visit: download the interpreter', 'later visits: the browser kept a copy'):
            track = RoundedRectangle(width=7.0, height=0.4, corner_radius=0.2).set_stroke(GREY_B, 2)
            fill = RoundedRectangle(width=7.0, height=0.4, corner_radius=0.2).set_fill(BLUE, 0.8).set_stroke(width=0)
            label = note(words, 26, GREY_A).next_to(track, UP, buff=0.15).align_to(track, LEFT)
            bars.add(VGroup(track, fill, label))
        bars.arrange(DOWN, buff=0.8).move_to(UP * 0.4)
        self.play(FadeIn(bars[0][0]), FadeIn(bars[0][2]))
        self.play(GrowFromEdge(bars[0][1], LEFT), run_time=3.0, rate_func=linear)
        self.at('After that, the browser keeps a copy')
        self.play(FadeIn(bars[1][0]), FadeIn(bars[1][2]))
        self.play(GrowFromEdge(bars[1][1], LEFT), run_time=0.3)

        # [V10.3d] q10-03: NumPy arrives because this file says np
        self.at('Libraries are downloaded only')
        self.play(FadeOut(bars))
        package = VGroup(box(1.5, 1.1, BLUE, radius=0.08), Text('NumPy', font_size=26, color=BLUE))
        package[1].move_to(package[0])
        package.move_to([-7.8, -2.6, 0])
        why = note('loaded only because this file says np', 24, FOCUS).to_corner(DL, buff=0.4)
        self.at('This scene says n p')
        card = qr_card('q10-03')
        self.play(package.animate.move_to([-5.6, -2.0, 0]), FadeIn(card, shift=UP * 0.2), run_time=1.0)
        self.play(FadeIn(why), package.animate.scale(0.8).next_to(why, UP, buff=0.2).align_to(why, LEFT))
        xs = np.linspace(-6, 6, 49)
        sine = VGroup(*[Dot([x, np.sin(x), 0], radius=0.06, color=YELLOW) for x in xs])
        cosine = VGroup(*[Dot([x, np.cos(x), 0], radius=0.06, color=BLUE) for x in xs])
        caption = Text('49 points from np.linspace', font_size=32).to_edge(UP)
        self.play(Write(caption), LaggedStart(*[FadeIn(d) for d in sine], lag_ratio=0.05))
        self.play(Transform(sine, cosine), run_time=2)
        self.at('the one that lays out graphs')
        graphs = VGroup(box(1.8, 0.8, GREY_B, radius=0.08), Text('networkx', font_size=24, color=GREY_A))
        graphs[1].move_to(graphs[0])
        graphs.next_to(package, RIGHT, buff=0.3)
        self.play(FadeIn(graphs, shift=RIGHT * 0.2))

        # Manim itself: an engine of its own, in plain Python
        self.at('what about Mannim itself')
        self.play(FadeOut(VGroup(sine, caption, card, why, package, graphs)))
        outer = labelled_box('', 6.4, 3.0, 26, BLUE).move_to(UP * 0.3)
        outer_tag = note('Pyodide', 28, BLUE).next_to(outer, UP, buff=0.15)
        engine = labelled_box('its own engine,\nin plain Python', 3.6, 1.4, 28, FOCUS).move_to(outer)
        self.play(FadeIn(outer), FadeIn(outer_tag))
        self.at('brings its own engine')
        self.play(FadeIn(engine, scale=0.8))
        nxt = note('more next episode', 24, GREY_A).next_to(outer, DOWN, buff=0.3)
        self.play(FadeIn(nxt))
        self.finish()


# ---------------------------------------------------------------- 10.4

class Segment_10_4(Segment):
    """The cook who cannot be interrupted."""
    EPISODE, SEGMENT = 10, '10.4'

    def construct(self):
        # [V10.4a] one cook, one stove: the main thread, serving tickets from the event loop
        kitchen = room(5.6, 4.0, 'main thread').move_to([-3.5, 0.0, 0])
        chef = cook().move_to(kitchen[0]).shift(LEFT * 1.0 + DOWN * 0.3)
        range_ = stove().next_to(chef, RIGHT, buff=0.4).align_to(chef, DOWN)
        queue_tag = note('event loop: order tickets', 22, GREY_A).next_to(kitchen[0], UP, buff=0.95).align_to(kitchen[0], LEFT)
        self.play(FadeIn(kitchen), FadeIn(chef), FadeIn(range_), FadeIn(queue_tag))
        slots = [kitchen[0].get_corner(UL) + UP * 0.45 + RIGHT * (0.9 + 1.75 * k) for k in range(4)]

        def serve(words):
            t = ticket(words).move_to(slots[0] + LEFT * 2.2)
            self.play(FadeIn(t), t.animate.move_to(slots[0]), run_time=0.5)
            self.play(t.animate.scale(0.5).move_to(chef[1]), run_time=0.4)
            self.play(FadeOut(t), Wiggle(range_[2], scale_value=1.1, n_wiggles=2), run_time=0.5)

        self.at('Clicks, key presses')
        for words in ('user clicked', 'draw frame', 'key pressed'):
            serve(words)

        # [V10.4b] a loop that never ends: stirring forever while the tickets pile up
        self.at('a loop that never ends')
        stuck = ticket('run Python: while True', WARNING).move_to(slots[0])
        self.play(FadeIn(stuck, shift=RIGHT * 0.3))
        self.play(stuck.animate.scale(0.6).next_to(range_, UP, buff=0.15))
        pivot = range_[1].get_top()
        range_[2].add_updater(lambda m, dt: m.rotate(4 * dt, about_point=pivot))
        self.at('stuck stirring one pot')
        pile = VGroup()
        for k, words in enumerate(('user clicked', 'draw frame', 'key pressed', 'draw frame')):
            t = ticket(words).move_to(slots[min(k, 3)] + DOWN * 0.08 * (k // 4))
            pile.add(t)
            self.play(FadeIn(t, shift=RIGHT * 0.3), run_time=0.4)
        frozen = VGroup(pointer().scale(0.9), note('the page freezes', 24, WARNING)).arrange(RIGHT, buff=0.25)
        frozen.next_to(kitchen, DOWN, buff=0.25)
        self.play(FadeIn(frozen))
        self.at('click a button to stop it')
        stop = ticket('stop!', WARNING).next_to(pile, RIGHT, buff=0.15)
        self.play(FadeIn(stop, shift=RIGHT * 0.3))

        # [V10.4c] a second cook in her own kitchen: the worker
        self.at('its own cook')
        range_[2].clear_updaters()
        self.play(FadeOut(VGroup(pile, stop, frozen)))
        worker = room(5.0, 4.0, 'worker (a separate thread)', BLUE).move_to([3.6, 0.0, 0])
        chef2 = cook('#cfe3f5').move_to(worker[0]).shift(LEFT * 0.9 + DOWN * 0.3)
        range2 = stove().next_to(chef2, RIGHT, buff=0.4).align_to(chef2, DOWN)
        self.play(FadeIn(worker), FadeIn(chef2), FadeIn(range2))
        self.play(stuck.animate.next_to(range2, UP, buff=0.15), run_time=1.0)
        pivot2 = range2[1].get_top()
        range2[2].add_updater(lambda m, dt: m.rotate(4 * dt, about_point=pivot2))
        self.at('The page stays responsive')
        for words in ('user clicked', 'draw frame'):
            serve(words)

        # [V10.4d] a timer inside the worker is just another ticket, behind the loop
        self.at('set a timer inside the worker')
        timer = clock_icon(0.35).next_to(worker[0], UP, buff=0.3).align_to(worker[0], LEFT).shift(RIGHT * 0.3)
        timer_tag = note('90 s', 22, GREY_A).next_to(timer, RIGHT, buff=0.15)
        self.play(FadeIn(timer), FadeIn(timer_tag))
        self.at('joins the queue behind')
        check = ticket('check the timer').next_to(timer_tag, RIGHT, buff=0.3)
        self.play(FadeIn(check, shift=RIGHT * 0.2))
        behind = note('waits behind the loop', 22, WARNING).next_to(check, UP, buff=0.12)
        self.play(FadeIn(behind))
        self.at("can't interrupt it")
        no_timer = cross_mark(0.3).next_to(check, RIGHT, buff=0.2)
        self.play(Create(no_timer))

        # [V10.4e] the page holds the stopwatch and dismisses the worker
        self.at('someone outside it')
        watch = clock_icon(0.35).next_to(chef, LEFT, buff=0.15).shift(UP * 0.2)
        self.play(FadeIn(watch, scale=0.5))
        self.play(Rotate(watch[1], -TAU, about_point=watch[0].get_center()), run_time=1.5)
        reasons = VGroup(*[chip(w, FOCUS, 20) for w in ('90 seconds pass', 'Cancel render', 'you edit the code')])
        reasons.arrange(RIGHT, buff=0.25).to_edge(DOWN, buff=0.35)
        for phrase, reason in zip(('ninety seconds pass', 'press Cancel render', 'edit the code'), reasons):
            self.at(phrase)
            self.play(FadeIn(reason, shift=UP * 0.15), run_time=0.5)
        self.at('terminates the worker')
        range2[2].clear_updaters()
        self.play(FadeOut(VGroup(chef2, stuck, check, behind, no_timer, timer, timer_tag)),
                  worker[0].animate.set_stroke(WARNING))
        self.at('starts a new one')
        fresh = cook('#cfe3f5').move_to(chef2)
        self.play(FadeIn(fresh, shift=DOWN * 0.3), worker[0].animate.set_stroke(BLUE))

        self.at('Cancel render is instant')
        instant = note('instant, even for stuck code', 24, AFTER).next_to(worker[0], UP, buff=0.3).align_to(worker[0], RIGHT)
        self.play(FadeIn(instant))
        self.at('The trade-off')
        reload = note('the new worker loads Python again: a few seconds', 22, GREY_A).next_to(instant, UP, buff=0.15).align_to(worker[0], RIGHT)
        self.play(FadeIn(reload))
        self.finish()


# ---------------------------------------------------------------- 10.5

class Segment_10_5(Segment):
    """Fresh starts and stale answers."""
    EPISODE, SEGMENT = 10, '10.5'

    def construct(self):
        title = Text('Two more pieces of care', font_size=40)
        self.play(FadeIn(title))

        # [V10.5a] every render gets a new, empty namespace
        self.at('every render starts fresh')
        self.play(FadeOut(title))
        spaces = VGroup()
        for k in (1, 2):
            frame = box(5.2, 3.0, GREY_B, radius=0.12)
            spaces.add(VGroup(frame, note(f'render {k}: namespace', 24, GREY_A).next_to(frame, UP, buff=0.15)))
        spaces.arrange(RIGHT, buff=1.2).move_to(UP * 0.6)
        self.play(FadeIn(spaces))
        library = VGroup(*[chip('library names, rebuilt', BLUE, 20).move_to(s[0]).align_to(s[0], UP).shift(DOWN * 0.3) for s in spaces])
        self.at('library definitions rebuilt')
        self.play(FadeIn(library))
        leftover = Text('x = 5', font=MONO, font_size=28).move_to(spaces[0][0]).shift(DOWN * 0.4)
        self.play(FadeIn(leftover))
        self.at('nothing left over')
        ask = Text('print(x)', font=MONO, font_size=28).move_to(spaces[1][0]).shift(DOWN * 0.2)
        error = Text('NameError', font=MONO, font_size=24, color=WARNING).next_to(ask, DOWN, buff=0.2)
        self.play(FadeIn(ask))
        self.play(FadeIn(error, shift=UP * 0.1))
        self.at("because of what's on the screen")
        self.play(Indicate(spaces[1][0], color=AFTER, scale_factor=1.03))

        # [V10.5b] a race: the late, older result is dropped
        self.at('answers can arrive out of order')
        self.play(FadeOut(VGroup(spaces, library, leftover, ask, error)))
        axis = Arrow(LEFT * 6, RIGHT * 6, buff=0, color=GREY_D, stroke_width=3).shift(DOWN * 2.6)
        time_tag = note('time', 20, DIM).next_to(axis, DOWN, buff=0.1).align_to(axis, RIGHT)
        self.play(GrowArrow(axis), FadeIn(time_tag))
        x = lambda t: -5.5 + t  # noqa: E731

        def bar(start, end, y, color, words):
            rect = Rectangle(width=end - start, height=0.5).set_fill(color, 0.6).set_stroke(color, 2)
            rect.move_to([x((start + end) / 2), y, 0])
            return VGroup(rect, note(words, 22, WHITE).move_to(rect))

        edit_a = chip('edit 1', GREY_A, 20).move_to([x(0.5), 1.8, 0])
        render_a = bar(0.5, 8.5, 0.8, BLUE, 'render 1 (slow)')
        self.play(FadeIn(edit_a))
        self.play(GrowFromEdge(render_a[0], LEFT), FadeIn(render_a[1]), run_time=1.0)
        self.at('then you edit again')
        edit_b = chip('edit 2', GREY_A, 20).move_to([x(2.5), 1.8, 0])
        render_b = bar(2.5, 5.5, -0.4, AFTER, 'render 2')
        self.play(FadeIn(edit_b))
        self.play(GrowFromEdge(render_b[0], LEFT), FadeIn(render_b[1]), run_time=0.8)
        self.at('The second render might finish')
        shown = VGroup(check_mark(0.3), note('shown', 22, AFTER)).arrange(RIGHT, buff=0.15).next_to(render_b, DOWN, buff=0.2)
        self.play(Create(shown[0]), FadeIn(shown[1]))
        self.at('stamped with a revision number')
        stamps = VGroup(note('revision 1', 20, BLUE).next_to(render_a, RIGHT, buff=0.2),
                        note('revision 2', 20, AFTER).next_to(render_b, RIGHT, buff=0.2))
        current = note('current revision: 2', 24, FOCUS).to_corner(UR, buff=0.5)
        self.play(FadeIn(stamps), FadeIn(current))
        self.at('Anything older is quietly thrown away')
        verdict = note('1 < 2: stale', 22, WARNING).next_to(stamps[0], DOWN, buff=0.15)
        trash = bin_icon().move_to([5.3, -1.5, 0])
        self.play(FadeIn(verdict), FadeIn(trash))
        self.play(VGroup(render_a, stamps[0], verdict).animate.scale(0.2).move_to(trash), run_time=1.0)
        self.play(FadeOut(VGroup(render_a, stamps[0], verdict)))
        rule = note('show only the newest answer', 30, FOCUS).move_to(UP * 3.0)
        self.play(FadeIn(rule))
        self.at('The same rule protects loads')
        loads = note('also: loads from the gallery and HashBin', 24, GREY_A).next_to(rule, DOWN, buff=0.2)
        self.play(FadeIn(loads))
        self.finish()


# ---------------------------------------------------------------- 10.6

def preview_trail(scene, mover, start):
    """q10-02's trail at the preview's 15 frames per second: one dot for each frame drawn."""
    trail = VGroup()

    def grow(m):
        frames = int((scene.renderer.time - start) * PREVIEW_FPS + 1e-6) + 1
        while len(m) < frames:
            m.add(Dot(mover.get_center(), radius=0.04, color=BLUE))
    trail.add_updater(grow)
    return trail


def frame_tree():
    """One frame of q10-02 as manim-lite sends it (frame 30): four root mobjects."""
    root = labelled_box('frame 30', 2.2, 0.7, 24, FOCUS)
    kids = VGroup(labelled_box('vgroup: 31 dots', 3.0, 0.6, 20), labelled_box('circle: the mover', 3.0, 0.6, 20),
                  labelled_box('text: 31', 3.0, 0.6, 20), labelled_box('text: frames so far', 3.0, 0.6, 20))
    kids.arrange(DOWN, buff=0.2)
    root.next_to(kids, LEFT, buff=1.0)
    links = VGroup(*[Line(root.get_right(), k.get_left(), color=GREY_B, stroke_width=2) for k in kids])
    fields = VGroup(field('type', '"circle"'), field('radius', '0.08'), field('color', '"#f7d96f"'),
                    field('fill_opacity', '1.0'), field('position', '[-2.8, 0, 0]'), field('angle', '0.0'))
    fields.arrange(DOWN, aligned_edge=LEFT, buff=0.12)
    panel = VGroup(box(fields.width + 0.5, fields.height + 0.4, GREY_B, radius=0.08), fields)
    fields.move_to(panel[0])
    panel.next_to(kids[1], RIGHT, buff=0.6)
    detail = Line(kids[1].get_right(), panel.get_left(), color=GREY_B, stroke_width=2)
    return VGroup(root, kids, links), VGroup(detail, panel)


class Segment_10_6(Segment):
    """From Python objects to frames (q10-02)."""
    EPISODE, SEGMENT = 10, '10.6'

    def construct(self):
        title = Text('Not a video. Frames.', font_size=44)
        self.play(FadeIn(title))
        self.at('every play and every wait advances a clock')
        ticks = VGroup(*[Line(DOWN * 0.15, UP * 0.15, color=GREY_A, stroke_width=3).move_to([-6 + k * 0.4, -1.0, 0]) for k in range(31)])
        seconds = VGroup(*[note(f'{s} s', 20, GREY_B).next_to(ticks[15 * s], DOWN, buff=0.15) for s in range(3)])
        rate = note('15 snapshots per second of animation', 26, FOCUS).next_to(ticks, UP, buff=0.4)
        self.play(title.animate.to_edge(UP, buff=0.5), LaggedStart(*[FadeIn(t) for t in ticks], lag_ratio=0.05), FadeIn(seconds), run_time=1.5)
        self.play(FadeIn(rate))
        self.at('At each tick')
        snap = note("every shape's points, colours, opacity and position", 24, GREY_A).next_to(seconds, DOWN, buff=0.4)
        self.play(FadeIn(snap))

        # [V10.6a] q10-02: one dot per frame
        self.at('This scene makes that visible')
        self.play(FadeOut(VGroup(title, ticks, seconds, rate, snap)))
        card = qr_card('q10-02')
        self.play(FadeIn(card, shift=UP * 0.2), run_time=0.3)
        mover = Dot(LEFT * 6, color=YELLOW)
        start = self.renderer.time
        trail = preview_trail(self, mover, start)
        counter = Integer(0, font_size=60).shift(UP * 2)
        counter.add_updater(lambda m: m.set_value(len(trail)))
        caption = Text('frames so far', font_size=28).next_to(counter, DOWN)
        self.add(trail, mover, counter, caption)
        self.play(mover.animate.move_to(RIGHT * 6), run_time=4, rate_func=linear)
        trail.clear_updaters()
        counter.clear_updaters()
        self.at('Four seconds, about sixty dots')
        self.play(Indicate(counter, color=FOCUS))
        self.wait(1.5)

        # [V10.6b] one frame, unfolded into a tree of objects
        self.at('Each snapshot is written')
        counter.clear_updaters()
        self.play(FadeOut(VGroup(trail, mover, counter, caption, card)))
        tree, detail = frame_tree()
        VGroup(tree, detail).move_to(DOWN * 0.2)
        self.play(FadeIn(tree[0]), LaggedStart(*[AnimationGroup(Create(l), FadeIn(k)) for l, k in zip(tree[2], tree[1])], lag_ratio=0.2), run_time=1.5)
        self.play(Create(detail[0]), FadeIn(detail[1]))
        snapshot = note('one frame = a snapshot of every mobject', 26, FOCUS).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(snapshot))

        # [V10.6c] pooling: unchanged pieces are sent once
        self.at('That could be a lot of data')
        self.play(FadeOut(VGroup(tree, detail, snapshot)))
        big = note('2 minutes = 1,800 frames, often hundreds of shapes each', 26, GREY_A).to_edge(UP, buff=0.5)
        self.play(FadeIn(big))
        self.at('identical pieces are pooled')
        frames = VGroup()
        for k in (30, 31):
            items = VGroup(labelled_box('vgroup: dots', 2.6, 0.55, 20), labelled_box('circle: mover', 2.6, 0.55, 20),
                           labelled_box('text: frames so far', 2.6, 0.55, 20)).arrange(DOWN, buff=0.15)
            head = note(f'frame {k}', 24, GREY_A).next_to(items, UP, buff=0.2)
            frames.add(VGroup(head, items))
        frames.arrange(RIGHT, buff=4.0).move_to(DOWN * 0.2)
        self.play(FadeIn(frames))
        shared = labelled_box('text: frames so far', 2.6, 0.55, 20, GREY_D).move_to(DOWN * 2.4)
        shared_tag = note('pooled: sent once', 22, AFTER).next_to(shared, DOWN, buff=0.12)
        same = VGroup(frames[0][1][2], frames[1][1][2])
        self.play(same.animate.set_opacity(0.35))
        refs = VGroup(*[Arrow(s.get_bottom(), shared.get_top(), buff=0.1, color=AFTER, stroke_width=3) for s in same])
        self.play(TransformFromCopy(same[0], shared), FadeIn(shared_tag), GrowArrow(refs[0]), GrowArrow(refs[1]))
        self.at('In 3D')
        turned = note('3D: "the same as before, rotated"', 24, GREY_A).next_to(frames, UP, buff=0.3)
        self.play(FadeIn(turned))
        measured = note(f'this scene: {PLAIN_BYTES:,} bytes as plain frames, {POOLED_BYTES:,} pooled', 22, FOCUS)
        measured.next_to(big, DOWN, buff=0.15)
        self.play(FadeIn(measured))
        self.at('there\'s a ceiling')
        page = labelled_box('the page', 2.2, 0.8, 24).to_edge(RIGHT, buff=0.4).shift(DOWN * 2.4)
        limit = Arrow(shared.get_right(), page.get_left(), buff=0.2, color=WARNING, stroke_width=4)
        limit_tag = note('at most 32 MiB', 22, WARNING).next_to(limit, UP, buff=0.1)
        self.play(FadeIn(page), GrowArrow(limit), FadeIn(limit_tag))
        self.finish()


# ---------------------------------------------------------------- 10.7

def svg_path_text(circle):
    """The start of an S V G path for a circle's cubics, in scene units."""
    points = circle.get_points()
    fmt = lambda p: f'{p[0]:.2f} {p[1]:.2f}'  # noqa: E731
    lines = [f'M {fmt(points[0])}']
    for i in range(0, 8, 4):
        lines.append(f'C {fmt(points[i + 1])}, {fmt(points[i + 2])}, {fmt(points[i + 3])}')
    return lines + ['…']


class Segment_10_7(Segment):
    """Drawing, playing and measuring (q10-04)."""
    EPISODE, SEGMENT = 10, '10.7'

    def construct(self):
        # [V10.7a] a frame becomes SVG: paths of cubic Bézier curves
        circle = Circle(radius=1.6, color=BLUE).move_to([-4.0, 0.6, 0])
        self.play(Create(circle))
        self.at('Every outline becomes')
        rows = svg_path_text(Circle(radius=1.6))
        markup = VGroup(Text('<path d="', font=MONO, font_size=24, color=GREY_A),
                        *[Text(r, font=MONO, font_size=24, color=GREY_A) for r in rows],
                        Text('"/>', font=MONO, font_size=24, color=GREY_A)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        for line in markup[1:-1]:
            line.shift(RIGHT * 0.4)
        markup.move_to([2.6, 0.6, 0])
        self.play(FadeIn(markup, lag_ratio=0.1), run_time=1.2)
        self.at('cubic Bezz ee ay curves')
        cs = VGroup(*[markup[i][0] for i in (2, 3)])
        anchors, handles = anchors_and_handles(circle)
        self.play(cs.animate.set_color(FOCUS), FadeIn(handles), FadeIn(anchors))
        self.at('Episode four all the way down')
        four = note('episode 4', 24, FOCUS).next_to(circle, DOWN, buff=0.4)
        self.play(FadeIn(four))

        # [V10.7b] the player is a flipbook of finished frames
        self.at('the player is just a flipbook')
        self.play(FadeOut(VGroup(circle, markup, anchors, handles, four)))
        strip = VGroup()
        for k in range(8):
            frame = box(1.35, 0.85, GREY_B, fill='#000000', radius=0.05, stroke=2)
            dot = Dot(frame.get_left() + RIGHT * (0.2 + 0.95 * k / 7), radius=0.08, color=YELLOW)
            strip.add(VGroup(frame, dot))
        strip.arrange(RIGHT, buff=0.12).move_to(UP * 1.0)
        bar = Line(strip.get_left(), strip.get_right(), color=GREY_B, stroke_width=4).next_to(strip, DOWN, buff=0.5)
        head = Dot(bar.get_start(), radius=0.12, color=FOCUS)
        self.play(FadeIn(strip, lag_ratio=0.1), Create(bar), FadeIn(head))
        self.at('Seeking is instant')
        mark = SurroundingRectangle(strip[0], color=FOCUS, buff=0.05)
        self.add(mark)
        for k in (5, 2, 7, 3):
            head.move_to(bar.point_from_proportion((k + 0.5) / 8))
            mark.become(SurroundingRectangle(strip[k], color=FOCUS, buff=0.05))
            self.wait(0.5)

        # [V10.7c] q10-04: formulas need a second pass with measured sizes
        self.at('Formulas need one extra round trip')
        self.play(FadeOut(VGroup(strip, bar, head, mark)))
        formulas = VGroup(MathTex(r'\int_0^1 x^2 \, dx = \frac{1}{3}'), MathTex(r'\sqrt{\frac{a^2 + b^2}{2}}'),
                          MathTex(r'\sum_{k=0}^{n} \binom{n}{k} = 2^n')).arrange(DOWN, buff=0.8).shift(LEFT * 2.5)
        card = qr_card('q10-04')
        self.play(LaggedStart(*[Write(f) for f in formulas], lag_ratio=0.4), FadeIn(card, shift=UP * 0.2))
        self.at('on the first pass')
        guesses = VGroup(*[DashedVMobject(Rectangle(width=w, height=h), num_dashes=30).set_stroke(WARNING, 3).move_to(f)
                           for (w, h), f in zip(ESTIMATED_BOXES, formulas)])
        pass_one = note('pass 1: estimated sizes', 24, WARNING).move_to([2.6, 2.2, 0]).align_to([1.2, 0, 0], LEFT)
        self.play(Create(guesses), FadeIn(pass_one))
        self.at('The page typesets and measures them')
        measure = note('the page measures each formula\nwith MathJax', 22, GREY_A).next_to(pass_one, DOWN, buff=0.4).align_to(pass_one, LEFT)
        self.play(FadeIn(measure))
        self.at('a second render with the real sizes')
        boxes = VGroup(*[SurroundingRectangle(f, buff=0.05, color=YELLOW) for f in formulas])
        pass_two = note('pass 2: measured sizes', 24, FOCUS).next_to(measure, DOWN, buff=0.4).align_to(pass_one, LEFT)
        self.play(FadeIn(pass_two), Create(boxes))
        self.at('A guess wouldn')
        self.play(Indicate(guesses, color=WARNING, scale_factor=1.0))
        self.finish()


# ---------------------------------------------------------------- 10.8

def frame_clock(scene, scale=1.0, centre=ORIGIN):
    """q10-05 at any scale; its readouts follow the scene's own clock."""
    start = scene.renderer.time
    face = Circle(radius=2, color=GREY)
    hand = Line(ORIGIN, UP * 1.8, color=YELLOW, stroke_width=8)
    hand.add_updater(lambda m, dt: m.rotate(-TAU * dt, about_point=face.get_center()))
    seconds = DecimalNumber(0, num_decimal_places=2, font_size=48).to_corner(UL)
    frame = Integer(0, font_size=48).to_corner(UR)
    labels = VGroup(Text('seconds', font_size=24).next_to(seconds, DOWN), Text('frame', font_size=24).next_to(frame, DOWN))
    group = VGroup(face, hand, seconds, frame, labels).scale(scale, about_point=ORIGIN).shift(centre)
    seconds.add_updater(lambda m: m.set_value(scene.renderer.time - start))
    frame.add_updater(lambda m: m.set_value(round((scene.renderer.time - start) * PREVIEW_FPS)))
    return group


class Segment_10_8(Segment):
    """Turning frames into a video file (q10-05)."""
    EPISODE, SEGMENT = 10, '10.8'

    def construct(self):
        # [V10.8a] q10-05 runs
        clock = frame_clock(self)
        card = qr_card('q10-05')
        self.add(clock)
        self.play(FadeIn(card, shift=UP * 0.2), run_time=0.5)
        self.wait(3.5)

        # [V10.8b] frames go into the encoder; packets come out
        self.at('The page draws each frame')
        for m in clock:
            m.clear_updaters()
        self.play(FadeOut(clock))
        frames = VGroup(*[box(0.9, 0.6, GREY_B, fill='#000000', radius=0.05, stroke=2) for _ in range(4)]).arrange(DOWN, buff=0.15)
        frames.move_to([-5.2, 0.6, 0])
        encoder = labelled_box('VideoEncoder\n(WebCodecs)', 3.2, 1.4, 26, BLUE).move_to([-0.8, 0.6, 0])
        into = Arrow(frames.get_right(), encoder.get_left(), buff=0.2, color=GREY_B, stroke_width=4)
        self.play(FadeIn(frames, lag_ratio=0.2), FadeIn(encoder), GrowArrow(into))
        packets = VGroup(*[box(1.0, 0.35, AFTER, radius=0.05, stroke=2).set_fill(AFTER, 0.3) for _ in range(4)]).arrange(DOWN, buff=0.2)
        packets.move_to([3.0, 0.6, 0])
        out = Arrow(encoder.get_right(), packets.get_left(), buff=0.2, color=GREY_B, stroke_width=4)
        self.play(GrowArrow(out), FadeIn(packets, lag_ratio=0.2))
        self.play(FadeOut(card))

        self.at('Each frame needs a timestamp')
        good = VGroup(*[note(f'frame {n} ÷ 15 = {n / 15:.3f} s', 20, AFTER).next_to(p, RIGHT, buff=0.2) for n, p in zip(range(4), packets)])
        self.play(FadeIn(good, lag_ratio=0.2))

        # [V10.8c] wall-clock stamps are uneven, so the video would stutter (an illustration)
        self.at('the clock on the wall')
        self.play(FadeOut(VGroup(frames, encoder, into, out, packets, good)))
        rows = VGroup()
        jitter = [0, 0.012, -0.02, 0.035, -0.006, 0.05, -0.03, 0.018, 0.04, -0.015, 0.0, 0.026, -0.024]
        for words, color, uneven in (('frame number ÷ 15', AFTER, False), ('wall clock while encoding', WARNING, True)):
            axis = Line(LEFT * 5.5, RIGHT * 5.5, color=GREY_D, stroke_width=3)
            marks = VGroup(*[Line(DOWN * 0.2, UP * 0.2, color=color, stroke_width=4)
                             .move_to(axis.point_from_proportion(min(1, max(0, (k / 15 + (jitter[k] * 6 if uneven else 0)) / (12 / 15)))))
                             for k in range(13)])
            label = note(words, 24, color).next_to(axis, UP, buff=0.3).align_to(axis, LEFT)
            rows.add(VGroup(axis, marks, label))
        rows.arrange(DOWN, buff=1.2).move_to(UP * 0.3)
        self.play(FadeIn(rows[1]))
        self.at('Wall-clock timestamps would make the video stutter')
        stutter = note('uneven: the video stutters', 24, WARNING).next_to(rows[1], DOWN, buff=0.25)
        self.play(FadeIn(stutter))
        self.at('from the frame number alone')
        self.play(FadeIn(rows[0]))
        self.at('frame forty five')
        exact = note('frame 45 ÷ 15 = 3.000 s, exactly', 30, AFTER).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(exact))
        self.at("This scene's clock is a good test")
        test = note('export q10-05 and scrub: the readout matches the player', 22, GREY_A).next_to(exact, UP, buff=0.2)
        self.play(FadeIn(test))

        # [V10.8d] MP4: the index (moov) before the data (mdat)
        self.at('packaged into an MP4')
        self.play(FadeOut(VGroup(rows, stutter, exact, test)))
        moov = VGroup(Rectangle(width=1.6, height=1.6).set_fill(FOCUS, 0.35).set_stroke(FOCUS, 3), Text('moov', font=MONO, font_size=28))
        mdat = VGroup(Rectangle(width=7.6, height=1.6).set_fill(BLUE, 0.25).set_stroke(BLUE, 3), Text('mdat', font=MONO, font_size=28))
        for block in (moov, mdat):
            block[1].move_to(block[0])
        file_ = VGroup(moov, mdat).arrange(RIGHT, buff=0).move_to(UP * 0.4)
        tags = VGroup(note('index', 22, FOCUS).next_to(moov, UP, buff=0.15), note('frame data', 22, BLUE).next_to(mdat, UP, buff=0.15))
        memory = note('built in memory', 24, GREY_A).next_to(file_, DOWN, buff=0.3)
        self.play(FadeIn(mdat), FadeIn(tags[1]), FadeIn(memory))
        self.at('the index that describes where every frame lives')
        self.play(FadeIn(moov, shift=RIGHT * 0.3), FadeIn(tags[0]))
        self.at('without reading the whole file first')
        first = note('index first: playback can start immediately', 28, FOCUS).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(first))
        self.finish()


# ---------------------------------------------------------------- 10.9

class Segment_10_9(Segment):
    """Recap: the whole journey."""
    EPISODE, SEGMENT = 10, '10.9'

    def construct(self):
        # [V10.9a] the pipeline, step by step
        steps = [('You stop typing', 'editor', GREY_B), ('worker running Python', 'worker (Pyodide)', BLUE),
                 ('fresh namespace', 'fresh namespace', BLUE), ('Identical pieces are pooled', 'frames, pooled', BLUE),
                 ('ignores anything stale', 'the page', GREY_B), ('draws S V G', 'SVG renderer', GREY_B),
                 ('plays the flipbook', 'player', AFTER)]
        nodes = VGroup(*[labelled_box(words, 2.6, 0.8, 22, color) for _, words, color in steps])
        top = VGroup(*nodes[:4]).arrange(RIGHT, buff=0.6)
        bottom = VGroup(*nodes[4:]).arrange(LEFT, buff=0.6)
        top.move_to(UP * 1.4)
        bottom.next_to(top, DOWN, buff=1.3).align_to(top, RIGHT)
        arrows = VGroup()
        order = list(nodes)
        for a, b in zip(order, order[1:]):
            if a is nodes[3]:
                arrows.add(Arrow(a.get_bottom(), b.get_top(), buff=0.1, color=GREY_B, stroke_width=3))
            elif a in bottom:
                arrows.add(Arrow(a.get_left(), b.get_right(), buff=0.1, color=GREY_B, stroke_width=3))
            else:
                arrows.add(Arrow(a.get_right(), b.get_left(), buff=0.1, color=GREY_B, stroke_width=3))
        watch = clock_icon(0.28).next_to(nodes[1], UP, buff=0.2)
        quiet = note('1 s quiet', 18, GREY_B).next_to(arrows[0], DOWN, buff=0.12)
        mathjax = labelled_box('MathJax', 2.0, 0.7, 22, FOCUS).next_to(nodes[4], DOWN, buff=0.9)
        down = Arrow(nodes[4].get_bottom(), mathjax.get_top(), buff=0.1, color=FOCUS, stroke_width=3)
        second = CurvedArrow(mathjax.get_left(), nodes[1].get_bottom() + DOWN * 0.05, angle=-0.8, color=FOCUS, stroke_width=3)
        second_tag = note('second pass', 20, FOCUS).next_to(mathjax, LEFT, buff=0.3)
        for k, (phrase, _, _) in enumerate(steps):
            if k == 6:
                self.at('measures formulas')
                self.play(FadeIn(mathjax), GrowArrow(down))
                self.play(Create(second), FadeIn(second_tag))
            self.at(phrase)
            anims = [FadeIn(nodes[k], shift=UP * 0.1)]
            if k:
                anims.append(GrowArrow(arrows[k - 1]))
            if k == 1:
                anims += [FadeIn(watch), FadeIn(quiet)]
            self.play(*anims, run_time=0.6)
        self.at('if you ask for a video')
        codecs = labelled_box('WebCodecs', 2.2, 0.7, 22, AFTER).next_to(nodes[6], DOWN, buff=0.9)
        video = labelled_box('MP4 / WebM', 2.2, 0.7, 22, AFTER).next_to(codecs, LEFT, buff=0.6)
        to_codecs = Arrow(nodes[6].get_bottom(), codecs.get_top(), buff=0.1, color=AFTER, stroke_width=3)
        to_video = Arrow(codecs.get_left(), video.get_right(), buff=0.1, color=AFTER, stroke_width=3)
        self.play(FadeIn(codecs), GrowArrow(to_codecs))
        self.play(FadeIn(video), GrowArrow(to_video))

        # [V10.9b] the QR wall, 10 seconds
        self.at('But we skipped the biggest question', lead=0.5)
        wall = qr_wall([f'q10-0{i}' for i in range(1, 6)])
        heading = Text('Episode 10 · scan to open each scene', font_size=26, color=SCAFFOLD).to_corner(UL, buff=0.3)
        self.play(FadeOut(VGroup(nodes, arrows, watch, quiet, mathjax, down, second, second_tag, codecs, video, to_codecs, to_video)),
                  FadeIn(wall), FadeIn(heading))
        self.wait(10)

        # [V10.9c] teaser: Manim and manim-lite turning in step (episode 11)
        self.play(FadeOut(VGroup(wall, heading)))
        pair = VGroup(*[Square(2.0, color=c).set_fill(c, 0.4) for c in (BLUE, AFTER)]).arrange(RIGHT, buff=2.5).shift(UP * 0.3)
        names = VGroup(Text('Manim', font_size=30, color=BLUE).next_to(pair[0], DOWN, buff=0.5),
                       Text('manim-lite', font_size=30, color=AFTER).next_to(pair[1], DOWN, buff=0.5))
        self.play(FadeIn(pair), FadeIn(names))
        self.play(*[Rotate(s, PI / 2) for s in pair], run_time=1.5)
        nxt = Text('Next: Rebuilding an engine to match', font_size=34).to_edge(DOWN, buff=0.6)
        self.play(Write(nxt), *[Rotate(s, PI / 2) for s in pair], run_time=1.5)
        self.wait(1.5)
        self.finish()
