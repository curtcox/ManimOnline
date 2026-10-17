"""Episode 7 · Graphs, areas and slopes. One Scene per script segment.

    python3 video-series/production/render.py 7 [-ql] [segment ...]

Shot ids in comments ([V7.2c] ...) refer to episodes/07-graphs-areas-and-slopes.md. Beats are
placed with Segment.at('phrase'), from the narration's ElevenLabs character timings.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403

PLOT_SNIPPET = 'ep07/01-first-plot.py'
RIEMANN_SNIPPET = 'ep07/02-riemann.py'
SECANT_SNIPPET = 'ep07/03-secant-to-tangent.py'
BOUND_SNIPPET = 'ep07/04-moving-bound.py'
GRID_SNIPPET = 'ep07/05-bend-the-grid.py'


# ---------------------------------------------------------------- the snippets' objects

def riemann_f(x):
    """q07-02's curve."""
    return x ** 2 / 4 + 0.5


def riemann_scene():
    """q07-02's axes and graph, where the snippet puts them."""
    axes = Axes(x_range=[0, 4, 1], y_range=[0, 5, 1], x_length=8, y_length=5).add_coordinates()
    return axes, axes.plot(riemann_f, color=YELLOW)


def rectangles(axes, graph, dx):
    return axes.get_riemann_rectangles(graph, x_range=[0, 4], dx=dx, fill_opacity=0.6)


def left_sum(dx):
    """The total area of q07-02's rectangles of width dx (heights from left edges)."""
    n = round(4 / dx)
    return dx * sum(riemann_f(k * dx) for k in range(n))


def gap(axes, k, dx):
    """The sliver between rectangle k's top and the rising curve above it."""
    xs = np.linspace(k * dx, (k + 1) * dx, 16)
    points = [axes.c2p(x, riemann_f(x)) for x in xs] + [axes.c2p((k + 1) * dx, riemann_f(k * dx))]
    return Polygon(*points).set_fill(WARNING, 0.75).set_stroke(width=0)


def plot_scene():
    """q07-01's axes, centred as in the snippet."""
    return Axes(x_range=[-3, 3, 1], y_range=[-2, 9, 1], x_length=7, y_length=6, tips=False)


def secant_f(x):
    """q07-03's curve."""
    return x ** 2 / 4 + 1


def bound_scene():
    """q07-04's axes and graph."""
    axes = Axes(x_range=[0, 6.5, 1], y_range=[-1.5, 1.5, 0.5], x_length=10, y_length=4).shift(DOWN * 0.5)
    return axes, axes.plot(math.sin, x_range=[0, 6.5], color=YELLOW)


def sample_points(graph):
    """Where plot evaluated the function: the anchors of its smooth curve, once each."""
    points = graph.get_points()
    return [points[i] for i in range(0, len(points), 4)] + [points[-1]]


def note(words, font_size=24, color=SCAFFOLD):
    return Text(words, font_size=font_size, color=color)


def backed(mob, opacity=0.85, buff=0.12):
    """A label kept readable over a grid."""
    return VGroup(BackgroundRectangle(mob, fill_opacity=opacity, buff=buff), mob)


def tint(text, source, needle, color=FOCUS, occurrence=0):
    return find_chars(text, source, needle, occurrence).animate.set_color(color)


class Segment_7_1(Segment):
    """Cold open: how much is under the curve?"""
    EPISODE, SEGMENT = 7, '7.1'

    def construct(self):
        # [V7.1a] the q07-02 curve, its region shaded with a question mark
        axes, graph = riemann_scene()
        self.play(Create(axes), run_time=1.2)
        self.play(Create(graph), run_time=1.2)
        area = axes.get_area(graph, x_range=[0, 4], color=BLUE, opacity=0.35)
        question = Text('?', font_size=110).move_to(axes.c2p(2.6, 1.1))
        self.play(FadeIn(area), FadeIn(question, scale=0.6))
        self.at('no formula')
        self.play(ShowPassingFlash(graph.copy().set_stroke(WHITE, 10), time_width=0.5), run_time=1.6)

        # but a rectangle's area is easy
        self.at('But there is a formula')
        box = Rectangle(width=1.8, height=1.1).set_fill(BLUE, 0.6).set_stroke(WHITE, 2)
        w = MathTex('w').next_to(box, DOWN, buff=0.12)
        h = MathTex('h').next_to(box, RIGHT, buff=0.12)
        formula = MathTex(r'\text{area} = w \times h', font_size=36).next_to(w, DOWN, buff=0.3)
        icon = VGroup(box, w, h, formula).move_to([5.6, 0.6, 0])
        self.play(FadeIn(VGroup(box, w, h), shift=LEFT * 0.3))
        self.play(Write(formula))

        # [V7.1b] four rectangles: a rough idea, with obvious gaps
        self.at('fill the region')
        self.play(FadeOut(question), FadeOut(area))
        self.at('Four of them')
        rects = rectangles(axes, graph, 1)

        def tally(n, dx):
            lines = VGroup(Text(f'{n} rectangles', font_size=26),
                           Text(f'total ≈ {left_sum(dx):.2f}', font_size=26, color=FOCUS))
            return lines.arrange(DOWN, aligned_edge=LEFT, buff=0.2).move_to([5.6, 2.3, 0])

        count = tally(4, 1)
        self.play(FadeOut(icon), Create(rects), FadeIn(count), run_time=1.5)
        self.at('obvious gaps')
        gaps = VGroup(*[gap(axes, k, 1) for k in range(4)])
        self.play(FadeIn(gaps), run_time=0.6)
        self.play(gaps.animate.set_fill(opacity=0.35), rate_func=there_and_back, run_time=1)

        # [V7.1c] eight, sixteen, forty, eighty
        for n, dx, phrase, seconds in ((8, 0.5, 'Eight', 1.0), (16, 0.25, 'Sixteen', 0.8),
                                       (40, 0.1, 'forty', 0.7), (80, 0.05, 'eighty', 0.7)):
            self.at(phrase)
            extra = [FadeOut(gaps)] if n == 8 else []
            self.play(Transform(rects, rectangles(axes, graph, dx)), Transform(count, tally(n, dx)), *extra,
                      run_time=seconds)
        self.at('settles towards')
        self.play(Indicate(count[1], scale_factor=1.15))

        # [V7.1d] the rectangles melt into the area, and its value appears
        self.at('the whole idea of an integral')
        smooth_area = axes.get_area(graph, x_range=[0, 4], color=BLUE, opacity=0.6)
        self.play(FadeOut(rects), FadeIn(smooth_area), run_time=1.5)
        value = MathTex(r'\frac{22}{3}', font_size=84).move_to(axes.c2p(2.55, 1.15))
        exact = VGroup(Text('exactly 22/3', font_size=26, color=AFTER), Text('≈ 7.33', font_size=26, color=AFTER))
        exact.arrange(DOWN, aligned_edge=LEFT, buff=0.2).next_to(count, DOWN, buff=0.35, aligned_edge=LEFT)
        self.play(Write(value), FadeIn(exact, shift=UP * 0.2))
        self.finish()


class Segment_7_2(Segment):
    """Number lines."""
    EPISODE, SEGMENT = 7, '7.2'

    def construct(self):
        # [V7.2a] a NumberLine from -5 to 5 draws itself
        line = NumberLine(x_range=[-5, 5, 1], length=10, include_numbers=True).shift(DOWN * 0.6)
        self.play(Create(line), run_time=2)
        source = 'line = NumberLine(x_range=[-5, 5, 1], length=10, include_numbers=True)'
        code = fit(code_text(source, 24)).to_edge(UP, buff=0.6)
        self.at('You give it a range')
        self.play(FadeIn(code))
        self.at('a range')
        self.play(tint(code, source, '[-5, 5'))
        self.at('a step')
        step = Brace(Line(line.n2p(0), line.n2p(1)), UP, buff=0.35, color=SCAFFOLD)
        self.play(tint(code, source, ', 1]'), FadeIn(step))
        self.at('a length on screen')
        length = BraceBetweenPoints(line.n2p(-5), line.n2p(5), DOWN, buff=0.75, color=SCAFFOLD)
        units = note('10 units on screen', 22).next_to(length, DOWN, buff=0.1)
        self.play(tint(code, source, 'length=10'), FadeOut(step), FadeIn(length), FadeIn(units))
        self.at('label its own ticks')
        self.play(tint(code, source, 'include_numbers=True'),
                  LaggedStart(*[Indicate(n, scale_factor=1.4) for n in line.numbers], lag_ratio=0.08), run_time=1.6)

        # [V7.2b] number to point, and back
        self.at('converts in both directions')
        self.play(FadeOut(VGroup(length, units)), code.animate.set_color(GREY_A))
        n2p_source = 'dot = Dot(line.number_to_point(2.5))     # n2p for short'
        n2p = code_text(n2p_source, 24).next_to(code, DOWN, buff=0.3).align_to(code, LEFT)
        self.play(FadeIn(n2p))
        self.at('Number to point')
        dot = Dot(line.n2p(2.5), color=FOCUS, radius=0.12)
        tag = MathTex('2.5', color=FOCUS).next_to(dot, UP, buff=0.25)
        self.play(tint(n2p, n2p_source, 'number_to_point(2.5)'), FadeIn(dot, scale=3), FadeIn(tag))
        self.at('Point to number')
        p2n_source = 'line.point_to_number(dropped.get_center())    # 1.0'
        p2n = code_text(p2n_source, 24).move_to(n2p, aligned_edge=LEFT)
        dropped = Dot(line.n2p(1) + UP * 2.2, color=AFTER, radius=0.12)
        self.play(FadeOut(n2p), FadeIn(p2n), FadeIn(dropped))
        self.play(dropped.animate.move_to(line.n2p(1)), run_time=0.8, rate_func=rush_into)
        readback = MathTex('1.0', color=AFTER).next_to(dropped, DOWN, buff=0.75)
        self.play(TransformFromCopy(dropped, readback), tint(p2n, p2n_source, '# 1.0', AFTER))

        # [V7.2c] the conversions follow the line wherever it goes
        self.at('follow the line')
        self.play(FadeOut(VGroup(dropped, readback, p2n)))
        line.save_state()
        dot.add_updater(lambda m: m.move_to(line.n2p(2.5)))
        tag.add_updater(lambda m: m.next_to(dot, UP + LEFT * 0.4, buff=0.15))
        self.at('rotate it')
        self.play(Rotate(line, PI / 6), run_time=1)
        self.at('move it')
        self.play(line.animate.shift(UP * 1.2 + LEFT * 1.5), run_time=1)
        self.at('shrink it')
        self.play(line.animate.scale(0.6), run_time=1)
        self.at('is still exactly')
        self.play(Flash(dot, color=FOCUS, flash_radius=0.35), Indicate(line.numbers[7], scale_factor=1.6))

        # the pointer from episode 6 used n2p
        self.at('We used n two p')
        self.play(Restore(line), FadeOut(tag), FadeOut(dot), FadeOut(code))
        dot.clear_updaters()
        tag.clear_updaters()
        x = ValueTracker(-2)
        pointer = Triangle(color=YELLOW, fill_opacity=1).scale(0.2).rotate(PI)
        pointer.add_updater(lambda m: m.next_to(line.n2p(x.get_value()), UP, buff=0.1))
        recall = code_text('pointer.next_to(line.n2p(x.get_value()), UP)', 24).to_edge(UP, buff=0.6)
        episode = note('episode 6', 22).next_to(recall, DOWN, buff=0.2)
        self.play(FadeIn(pointer), FadeIn(recall), FadeIn(episode))
        self.play(x.animate.set_value(3.5), run_time=2.2)

        # [V7.2d] two number lines slide together: that is what Axes are
        self.at('put two number lines together')
        pointer.clear_updaters()
        self.play(FadeOut(VGroup(pointer, recall, episode)), line.animate.shift(DOWN * 1.9))
        upright = NumberLine(x_range=[-3, 3, 1], length=6, rotation=PI / 2, label_direction=LEFT,
                             include_numbers=True, numbers_to_exclude=[0]).shift(LEFT * 5)
        self.play(Create(upright), run_time=1)
        self.play(line.animate.shift(UP * 2.5), upright.animate.shift(RIGHT * 5), run_time=2)
        self.at('exactly what Axes are')
        caption = backed(Text('two number lines = Axes', font_size=34, color=FOCUS)).to_corner(UR, buff=0.5)
        self.play(FadeIn(caption, shift=DOWN * 0.2))
        self.finish()


class Segment_7_3(Segment):
    """Axes: a ruler inside the scene."""
    EPISODE, SEGMENT = 7, '7.3'

    def construct(self):
        # the screen's own coordinates, faintly
        screen = NumberPlane(x_range=[-8, 8, 1], y_range=[-5, 5, 1],
                             background_line_style={'stroke_color': GREY_D, 'stroke_opacity': 0.5, 'stroke_width': 1},
                             axis_config={'stroke_color': GREY_D, 'stroke_width': 2})
        screen_tag = backed(note('the screen', 22), 0.9).to_corner(UL, buff=0.3)
        self.play(FadeIn(screen), FadeIn(screen_tag))

        # [V7.3a] q07-01's axes
        self.at('That is what Axes are')
        axes = plot_scene()
        self.play(Create(axes), run_time=1.5)
        self.at('the range of numbers')
        across = BraceBetweenPoints(axes.c2p(-3, -2), axes.c2p(3, -2), DOWN, buff=0.08, color=SCAFFOLD)
        up = BraceBetweenPoints(axes.c2p(-3, 9), axes.c2p(-3, -2), LEFT, buff=0.08, color=SCAFFOLD)
        x_range = code_text('x_range=[-3, 3, 1]', 20).next_to(across, DOWN, buff=0.08).shift(LEFT * 1.6)
        y_range = code_text('y_range=[-2, 9, 1]', 20).next_to(up, LEFT, buff=0.15).shift(UP * 0.3)
        self.play(FadeIn(across), FadeIn(up), FadeIn(x_range), FadeIn(y_range))
        self.at('how long it should be')
        x_length = code_text('x_length=7', 20, FOCUS).next_to(x_range, RIGHT, buff=0.6)
        y_length = code_text('y_length=6', 20, FOCUS).next_to(y_range, DOWN, buff=0.2, aligned_edge=LEFT)
        self.play(FadeIn(x_length), FadeIn(y_length))
        self.at('from minus three')
        ends = VGroup(*[MathTex(t, font_size=30, color=FOCUS).next_to(axes.c2p(x, 0), DOWN, buff=0.15)
                        for t, x in (('-3', -3), ('3', 3))])
        self.play(FadeIn(ends), tint(x_range, 'x_range=[-3, 3, 1]', '-3, 3'))
        self.at('from minus two')
        tops = VGroup(*[MathTex(t, font_size=30, color=FOCUS).next_to(axes.c2p(0, y), RIGHT, buff=0.15)
                        for t, y in (('-2', -2), ('9', 9))])
        self.play(FadeIn(tops), tint(y_range, 'y_range=[-2, 9, 1]', '-2, 9'))
        self.at('squeezed into a box')
        box = DashedVMobject(Rectangle(width=7, height=6).move_to(axes), num_dashes=70).set_stroke(FOCUS, 2)
        self.play(Create(box), run_time=1.2)

        # add_coordinates numbers the ticks
        self.at('Add coordinates')
        self.play(FadeOut(VGroup(across, up, x_range, y_range, x_length, y_length, ends, tops, box)))
        axes.add_coordinates()
        add = code_text('.add_coordinates()', 22).to_edge(RIGHT, buff=0.5).shift(UP * 2.6)
        self.play(FadeIn(axes.coordinate_labels), FadeIn(add))

        # [V7.3b] one place, two descriptions
        self.at('two ways to describe')
        point = axes.c2p(2, 4)
        dot = Dot(point, color=FOCUS, radius=0.1)
        guides = axes.get_lines_to_point(point, color=FOCUS)
        graph_words = backed(VGroup(note('graph numbers', 20, FOCUS), MathTex('(2,\\ 4)', color=FOCUS))
                             .arrange(DOWN, buff=0.08), 0.85).next_to(dot, UL, buff=0.1)
        self.play(FadeOut(add), FadeIn(dot, scale=3), Create(guides), FadeIn(graph_words))
        self.at('or in screen units')
        crosshair = VGroup(Line(LEFT * 0.25, RIGHT * 0.25), Line(DOWN * 0.25, UP * 0.25)).set_stroke(GREY_A, 3)
        origin_tag = backed(note('screen (0, 0)', 18, GREY_A), 0.85).next_to(crosshair, DR, buff=0.05)
        screen_words = backed(VGroup(note('screen units', 20, GREY_A), MathTex('(2.33,\\ 0.27)', color=GREY_A))
                              .arrange(DOWN, buff=0.08), 0.85).next_to(dot, DR, buff=0.1)
        self.play(screen.animate.set_opacity(0.9), FadeIn(crosshair), FadeIn(origin_tag), FadeIn(screen_words))

        # c2p converts graph numbers into a screen point
        self.at('The method c to p')
        call = code_text('axes.c2p(2, 4)', 26, FOCUS)
        result = code_text('[2.33, 0.27, 0]', 26, GREY_A)
        convert = VGroup(call, Arrow(UP * 0.4, DOWN * 0.4, color=GREY_B, buff=0), result).arrange(DOWN, buff=0.15)
        convert = backed(convert, 0.9, 0.2).move_to([5.3, 2.2, 0])
        meaning = note('coordinates to point', 20).next_to(convert, DOWN, buff=0.15)
        self.play(FadeIn(convert[0]), FadeIn(call), FadeIn(meaning))
        self.at('Ask for the point')
        self.play(TransformFromCopy(graph_words[1][1], call), run_time=1.2)
        self.play(GrowArrow(convert[1][1]), FadeIn(result, shift=DOWN * 0.2))
        self.play(TransformFromCopy(result, screen_words[1][1]), run_time=1.2)
        self.play(Flash(dot, color=WHITE, flash_radius=0.3))

        # [V7.3c] think in the graph's own numbers
        self.at('This matters')
        self.play(FadeOut(VGroup(screen, screen_tag, crosshair, origin_tag, screen_words, graph_words, guides, dot,
                                 convert, meaning)))
        self.at('To put dots')
        card = qr_card('q07-01')
        parabola = axes.plot(lambda x: x ** 2, color=YELLOW)
        line = axes.plot(lambda x: 2 * x + 1, x_range=[-1.5, 3], color=BLUE)
        square_tag = axes.get_graph_label(parabola, 'x^2', x_val=-2.5)
        line_tag = axes.get_graph_label(line, '2x+1', x_val=2.5, direction=RIGHT)
        self.play(Create(parabola), Write(square_tag), FadeIn(card))
        self.play(Create(line), Write(line_tag))
        self.at('we solve')
        working = VGroup(MathTex('x^2 = 2x + 1'), MathTex(r'x = 1 \pm \sqrt{2}', color=WARNING))
        working.arrange(DOWN, buff=0.3).move_to([5.3, 2.2, 0])
        self.play(Write(working[0]))
        self.at('which gives')
        self.play(Write(working[1]))
        crossings = [1 - 2 ** 0.5, 1 + 2 ** 0.5]
        dots = VGroup(*[Dot(axes.c2p(x, x ** 2), color=RED) for x in crossings])
        self.play(LaggedStart(*[FadeIn(d, scale=3) for d in dots], lag_ratio=0.5))
        values = VGroup(MathTex(r'1 - \sqrt{2}', font_size=32, color=WARNING).next_to(dots[0], DL, buff=0.1),
                        MathTex(r'1 + \sqrt{2}', font_size=32, color=WARNING).next_to(dots[1], DR, buff=0.1))
        calls = code_text('Dot(axes.c2p(x, x ** 2))', 20).next_to(working, DOWN, buff=0.4).to_edge(RIGHT, buff=0.4)
        self.play(FadeIn(values), FadeIn(calls))

        # resize the axes: the dots still land on the crossings
        self.at('If you resize the axes')
        graph = VGroup(axes, parabola, line, square_tag, line_tag, dots, values)
        self.play(graph.animate.scale(0.75).to_edge(LEFT, buff=0.6), run_time=2)
        self.finish()


class Segment_7_4(Segment):
    """What a plot really is."""
    EPISODE, SEGMENT = 7, '7.4'

    def construct(self):
        axes = plot_scene().add_coordinates()
        axes.coordinate_labels.set_opacity(0.6)
        parabola = axes.plot(lambda x: x ** 2, color=YELLOW)
        self.play(FadeIn(axes), Create(parabola))
        self.at("can't draw a function exactly")
        exactly = backed(note("plot can't draw x² exactly", 28, GREY_A)).to_edge(UP, buff=0.3).shift(RIGHT * 2.8)
        self.play(FadeIn(exactly))

        # [V7.4a] the samples: where plot evaluated the function
        self.at('evaluates your function')
        samples = sample_points(parabola)
        dots = VGroup(*[Dot(p, radius=0.045, color=WHITE) for p in samples])
        self.play(parabola.animate.set_stroke(opacity=0.35),
                  LaggedStart(*[FadeIn(d, scale=2) for d in dots], lag_ratio=0.04), run_time=2.5)
        count = backed(note(f'x = −3, −2.9, …, 3: {len(samples)} samples', 26, GREY_A)).move_to(exactly)
        self.play(FadeOut(exactly), FadeIn(count))

        # [V7.4b] cubic pieces threaded through them (episode 4's anchors and handles)
        self.at('threads a smooth chain')
        world = VGroup(axes, parabola)
        world.save_state()
        small_dots = dots.copy()
        focus = axes.c2p(1.5, 2.25)
        zoomed = VGroup(*[Dot((d.get_center() - focus) * 12, radius=0.09, color=WHITE) for d in dots])
        self.play(parabola.animate.set_stroke(opacity=1), run_time=0.5)
        self.play(world.animate.scale(12, about_point=focus).shift(-focus), Transform(dots, zoomed), run_time=2.5)
        anchors, handles = anchors_and_handles(parabola, handle_color=BLUE_B, anchor_radius=0.1)
        handles = VGroup(*[h for h in handles if abs(h.get_center()[0]) < 7.5 and abs(h.get_center()[1]) < 4.2])
        self.play(Create(handles), run_time=1.5)
        self.at('Episode four')
        recall = backed(note('episode 4: cubic curves through anchors', 26, FOCUS)).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(recall))

        # [V7.4c] a jump: 1/x plotted straight through zero
        self.at('That works beautifully')
        self.play(FadeOut(VGroup(handles, recall, count)), Restore(world), Transform(dots, small_dots), run_time=1.5)
        self.at("doesn't know about jumps")
        self.play(FadeOut(VGroup(axes, parabola, dots)))

        def small_axes():
            return Axes(x_range=[-3, 3, 1], y_range=[-4, 4, 2], x_length=5.4, y_length=4.4, tips=False,
                        axis_config={'color': GREY_B})

        naive_axes, fixed_axes = small_axes().move_to([-3.4, 0.4, 0]), small_axes().move_to([3.4, 0.4, 0])
        self.play(FadeIn(naive_axes), FadeIn(fixed_axes))
        self.at('Plot one over x')
        naive = naive_axes.plot(lambda x: 1 / x, x_range=[-2.75, 2.75, 0.5], color=YELLOW)
        naive_code = fit(code_text('axes.plot(lambda x: 1 / x, x_range=[-2.75, 2.75, 0.5])', 20), 6.4)
        naive_code.next_to(naive_axes, DOWN, buff=0.35)
        self.play(Create(naive), FadeIn(naive_code), run_time=2)
        false_line = Line(naive_axes.c2p(-0.25, -4), naive_axes.c2p(0.25, 4)).set_stroke(WARNING, 8, opacity=0.6)
        nothing = backed(note("a line that isn't there", 22, WARNING)).next_to(false_line, RIGHT, buff=0.15)
        self.play(FadeIn(false_line), FadeIn(nothing))
        self.play(FadeIn(cross_mark().move_to(naive_axes.get_corner(UL) + RIGHT * 0.4)))

        # split the range, or declare a gap
        self.at('The fix is')
        left = fixed_axes.plot(lambda x: 1 / x, x_range=[-3, -0.25], color=AFTER)
        right = fixed_axes.plot(lambda x: 1 / x, x_range=[0.25, 3], color=AFTER)
        split = VGroup(code_text('axes.plot(lambda x: 1 / x, x_range=[-3, -0.25])', 20),
                       code_text('axes.plot(lambda x: 1 / x, x_range=[0.25, 3])', 20)).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        fit(split, 6.4).next_to(fixed_axes, DOWN, buff=0.35)
        self.play(Create(left), Create(right), FadeIn(split), run_time=1.5)
        self.at('tell plot where')
        gap_code = fit(code_text('axes.plot(lambda x: 1 / x, discontinuities=[0], dt=0.25)', 20), 6.4)
        gap_code.move_to(split)
        self.play(FadeOut(split), FadeIn(gap_code))
        self.play(FadeIn(check_mark().move_to(fixed_axes.get_corner(UL) + RIGHT * 0.4)))
        caption = note('split the range, or declare a gap', 28, AFTER).to_edge(UP, buff=0.3)
        self.play(FadeIn(caption))
        self.finish()


def check_mark(size=0.5, color=AFTER):
    return VMobject().set_points_as_corners([[-0.5, 0, 0], [-0.15, -0.4, 0], [0.55, 0.45, 0]]).scale(size).set_stroke(color, 8)


def cross_mark(size=0.35, color=WARNING):
    return VGroup(Line(UL, DR), Line(UR, DL)).scale(size).set_stroke(color, 8)


class Segment_7_5(Segment):
    """Rectangles become area."""
    EPISODE, SEGMENT = 7, '7.5'

    def construct(self):
        # [V7.5a] q07-02 in full
        axes, graph = riemann_scene()
        card = qr_card('q07-02')
        self.play(FadeIn(axes), Create(graph), FadeIn(card))
        self.at('a method called')
        source = snippet_lines(RIEMANN_SNIPPET, 9, 9).strip()
        code = fit(code_text(source, 22)).to_edge(UP, buff=0.35)
        rects = rectangles(axes, graph, 1)
        self.play(FadeIn(code))
        self.play(Create(rects), run_time=1.5)
        self.at('give it a graph')
        self.play(tint(code, source, 'graph'))
        self.at('a range')
        self.play(tint(code, source, 'x_range=[0, 4]'))
        self.at('a width d x')
        width = BraceBetweenPoints(axes.c2p(1, 0), axes.c2p(2, 0), DOWN, buff=0.45, color=FOCUS)
        self.play(tint(code, source, 'dx=1'), FadeIn(width))

        # height from the left edge; colour shifts along the set
        self.at("Each rectangle's height")
        corner = Dot(axes.c2p(2, riemann_f(2)), color=FOCUS)
        height = DashedLine(axes.c2p(2, 0), axes.c2p(2, riemann_f(2)), color=FOCUS)
        f_of_2 = MathTex('f(2)', color=FOCUS, font_size=36).next_to(height, LEFT, buff=0.15)
        self.play(FadeOut(width), Create(height), FadeIn(corner, scale=2), FadeIn(f_of_2))
        edge = backed(note('height from the left edge', 22, FOCUS)).move_to(axes.c2p(1.1, 2.9))
        self.play(FadeIn(edge))
        self.at('colour shifts')
        self.play(FadeOut(VGroup(height, corner, f_of_2, edge)),
                  LaggedStart(*[r.animate(rate_func=there_and_back).shift(UP * 0.25) for r in rects], lag_ratio=0.25),
                  run_time=2)

        # [V7.5b] refine: transform into narrower rectangles
        self.at('To refine')
        loop = VGroup(code_text('for dx in [0.5, 0.25, 0.1, 0.05]:', 20),
                      code_text('    self.play(Transform(rectangles, axes.get_riemann_rectangles(..., dx=dx, ...)))', 20))
        loop.arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        fit(loop).to_edge(UP, buff=0.3)

        def tally(dx):
            lines = VGroup(MathTex(f'dx = {dx:g}', font_size=34), Text(f'total ≈ {left_sum(dx):.2f}', font_size=26, color=FOCUS))
            return lines.arrange(DOWN, aligned_edge=LEFT, buff=0.2).move_to([5.6, 1.6, 0])

        count = tally(1)
        self.play(FadeOut(code), FadeIn(loop), FadeOut(card), FadeIn(count))
        self.play(Transform(rects, rectangles(axes, graph, 0.5)), Transform(count, tally(0.5)), run_time=1.5)
        self.at('Transform pairs up')
        slow = note('slowly: each new rectangle grows out of an old one', 22).to_edge(DOWN, buff=0.15)
        self.play(FadeIn(slow))
        self.play(Transform(rects, rectangles(axes, graph, 0.25)), Transform(count, tally(0.25)), run_time=3)
        self.at('the extra ones grow')
        self.play(FadeOut(slow), Transform(rects, rectangles(axes, graph, 0.1)), Transform(count, tally(0.1)), run_time=1.5)
        self.at('splitting motion')
        self.play(Transform(rects, rectangles(axes, graph, 0.05)), Transform(count, tally(0.05)), run_time=1.5)

        # [V7.5c] the exact area, and its value
        self.at('Finally, get area')
        area_source = snippet_lines(RIEMANN_SNIPPET, 13, 13).strip()
        area_code = fit(code_text(area_source, 22)).to_edge(UP, buff=0.35)
        area = axes.get_area(graph, x_range=[0, 4], color=BLUE, opacity=0.6)
        self.play(FadeOut(loop), FadeIn(area_code))
        self.play(FadeOut(rects), FadeIn(area), run_time=1.5)
        self.at('the exact answer')
        exact = MathTex(r'\int_0^4 \left(\frac{x^2}{4} + \frac{1}{2}\right) dx = \frac{22}{3}').to_corner(UL)
        self.play(FadeOut(area_code))
        self.play(Write(exact))
        self.at('twenty two thirds')
        about = Text('22/3 ≈ 7.33', font_size=26, color=AFTER).next_to(count, DOWN, buff=0.3, aligned_edge=LEFT)
        self.play(Indicate(exact[0][-4:]), FadeIn(about, shift=UP * 0.2))
        self.at('closing in on')
        self.play(Indicate(count[1], scale_factor=1.15))
        self.finish()


class Segment_7_6(Segment):
    """Area as a running total."""
    EPISODE, SEGMENT = 7, '7.6'

    def construct(self):
        # [V7.6a] q07-04: the right-hand edge b lives in a ValueTracker
        axes, graph = bound_scene()
        card = qr_card('q07-04')
        self.play(FadeIn(axes), Create(graph), FadeIn(card))
        b = ValueTracker(0.01)
        area = always_redraw(lambda: axes.get_area(graph, x_range=[0, b.get_value()], color=[BLUE, GREEN], opacity=0.5))
        edge = always_redraw(lambda: axes.get_vertical_line(axes.i2gp(b.get_value(), graph), color=WHITE))
        b_tag = always_redraw(lambda: MathTex('b', font_size=34).next_to(axes.c2p(b.get_value(), 0), UP + RIGHT * 0.6, buff=0.1))
        self.at('Store the right-hand edge')
        panel = code_panel('b = ValueTracker(0.01)\n'
                           'area = always_redraw(lambda: axes.get_area(\n'
                           '    graph, x_range=[0, b.get_value()], color=[BLUE, GREEN], opacity=0.5))',
                           font_size=18, line_numbers=False)
        fit(panel).to_edge(UP, buff=0.25)
        self.play(FadeIn(panel))
        self.add(area)
        self.play(Create(edge), FadeIn(b_tag))
        self.at('Then animate b')
        self.play(b.animate.set_value(1.6), run_time=3, rate_func=linear)

        # the readout: one minus cos b
        self.at('The readout shows')
        caption = MathTex(r'\int_0^{b} \sin x \, dx =').to_corner(UL)
        value = DecimalNumber(0, num_decimal_places=2).next_to(caption, RIGHT)
        value.add_updater(lambda m: m.set_value(1 - math.cos(b.get_value())))
        closed = MathTex(r'= 1 - \cos b', color=SCAFFOLD).next_to(caption, DOWN, buff=0.25, aligned_edge=LEFT).shift(RIGHT * 1.1)
        self.play(FadeOut(panel), FadeIn(caption), FadeIn(value))
        self.at('works out to')
        self.play(Write(closed))

        # [V7.6b] at pi, exactly two
        self.at('As b grows to pi')
        self.play(b.animate.set_value(PI), run_time=2.5, rate_func=linear)
        pi_tag = MathTex(r'\pi', font_size=34).next_to(axes.c2p(PI, 0), DOWN, buff=0.2)
        self.at('exactly two')
        self.play(FadeIn(pi_tag), Indicate(value, scale_factor=1.4), Flash(value, color=FOCUS, flash_radius=0.5))

        # [V7.6c] past pi the area is below the axis, and the total falls back to zero
        self.at('something interesting')
        self.play(FadeOut(card))
        self.at('Past pi')
        self.play(b.animate.set_value(TAU), run_time=7, rate_func=linear)
        tau_tag = MathTex(r'2\pi', font_size=34).next_to(axes.c2p(TAU, 0), DOWN, buff=0.2)
        self.play(FadeIn(tau_tag), Indicate(value, scale_factor=1.4))

        # [V7.6d] +2 above, -2 below
        self.at('the part below cancels')
        plus = MathTex('+2', font_size=56, color=AFTER).move_to(axes.c2p(PI / 2, 0.45))
        minus = MathTex('-2', font_size=56, color=WARNING).move_to(axes.c2p(3 * PI / 2, -0.45))
        upper = axes.get_area(graph, x_range=[0, PI], color=AFTER, opacity=0.6)
        lower = axes.get_area(graph, x_range=[PI, TAU], color=WARNING, opacity=0.6)
        self.play(FadeIn(upper), FadeIn(plus, scale=1.5))
        self.play(FadeIn(lower), FadeIn(minus, scale=1.5))

        # an accumulation: the running total 1 - cos b, traced as b sweeps again
        self.at('running total')
        self.play(FadeOut(VGroup(upper, lower, plus, minus, tau_tag)), b.animate.set_value(0.01), run_time=1.5)
        total = always_redraw(lambda: axes.plot(lambda x: 1 - math.cos(x), x_range=[0, max(b.get_value(), 0.02)],
                                                color=FOCUS, stroke_width=5).set_color(AFTER))
        total_tag = backed(MathTex(r'\text{running total} = 1 - \cos b', font_size=40, color=AFTER), 0.8)
        total_tag.move_to(axes.c2p(PI, 2) + UP * 0.45 + RIGHT * 2)
        self.add(total)
        self.play(FadeIn(total_tag))
        self.play(b.animate.set_value(TAU), run_time=5, rate_func=linear)
        self.finish()


class Segment_7_7(Segment):
    """The slope of a curve."""
    EPISODE, SEGMENT = 7, '7.7'

    def construct(self):
        first = note('the first big idea: area under a curve', 34, GREY_A)
        self.play(FadeIn(first))
        self.at('Here is the second')
        second = Text('the second: the slope of a curve at a single point', font_size=34)
        self.play(FadeOut(first, shift=UP * 0.5), FadeIn(second, shift=UP * 0.5))

        # q07-03's axes and curve, with the point x = 1.5
        self.at('a single point')
        axes = Axes(x_range=[-1, 5, 1], y_range=[0, 7, 1], x_length=8, y_length=5.5).to_edge(LEFT)
        graph = axes.plot(secant_f, x_range=[-1, 4.8], color=YELLOW)
        point = Dot(axes.c2p(1.5, secant_f(1.5)), color=FOCUS)
        self.play(FadeOut(second), Create(axes), Create(graph), run_time=1.5)
        self.play(FadeIn(point, scale=3))

        # a straight line has one slope: rise over run
        self.at('A straight line has a slope')
        start, end = np.array([2.6, -2.2, 0]), np.array([5.8, 0.2, 0])
        straight = Line(start + (start - end) * 0.15, end + (end - start) * 0.15, color=BLUE)
        corner = np.array([end[0], start[1], 0])
        run = DashedLine(start, corner, color=GREY_A)
        rise = DashedLine(corner, end, color=GREY_A)
        labels = VGroup(note('run', 22, GREY_A).next_to(run, DOWN, buff=0.1),
                        note('rise', 22, GREY_A).next_to(rise, RIGHT, buff=0.1))
        rule = MathTex(r'\text{slope} = \frac{\text{rise}}{\text{run}}', font_size=36).move_to([4.2, 1.5, 0])
        self.play(Create(straight))
        self.at('how far it rises')
        self.play(Create(run), Create(rise), FadeIn(labels), Write(rule))

        # a curve keeps changing direction
        self.at("A curve doesn't")
        self.play(FadeOut(VGroup(straight, run, rise, labels, rule)))
        directions = VGroup()
        for x in (-0.5, 1.0, 2.6, 4.0):
            p = axes.c2p(x, secant_f(x))
            q = axes.c2p(x + 0.6, secant_f(x) + 0.6 * x / 2)
            u = (q - p) / np.linalg.norm(q - p)
            directions.add(Arrow(p - u * 0.1, p + u * 0.9, buff=0, color=GREY_A, stroke_width=4,
                                 max_tip_length_to_length_ratio=0.25))
        self.play(LaggedStart(*[GrowArrow(a) for a in directions], lag_ratio=0.3), run_time=1.8)

        # [V7.7a] a secant through two points, with dx and dy
        self.at('But we can pick two points')
        dx = ValueTracker(2.5)
        secant = always_redraw(lambda: axes.get_secant_slope_group(
            x=1.5, graph=graph, dx=dx.get_value(), dx_label='dx', dy_label='dy',
            secant_line_color=GREEN, secant_line_length=6))
        second_point = always_redraw(lambda: Dot(axes.c2p(1.5 + dx.get_value(), secant_f(1.5 + dx.get_value())), color=FOCUS))
        card = qr_card('q07-03')
        self.play(FadeOut(directions), FadeIn(second_point, scale=3), FadeIn(card))
        self.play(FadeIn(secant))
        self.bring_to_front(point, second_point)
        self.at('called a secant')
        secant_tag = note('secant', 26, GREEN).next_to(axes.c2p(4, secant_f(4)), RIGHT, buff=0.35)
        self.play(FadeIn(secant_tag))
        self.at('the rise')
        slope = DecimalNumber(0, num_decimal_places=3).to_corner(UR)
        slope.add_updater(lambda m: m.set_value((secant_f(1.5 + dx.get_value()) - secant_f(1.5)) / dx.get_value()))
        caption = MathTex(r'\frac{dy}{dx} =').next_to(slope, LEFT)
        self.play(FadeIn(caption), FadeIn(slope))
        self.play(Indicate(slope, scale_factor=1.3))

        # put dx in a ValueTracker and redraw the secant from it
        self.at('Now put d x in a value tracker')
        panel = code_panel('dx = ValueTracker(2.5)\n'
                           'secant = always_redraw(lambda:\n'
                           '    axes.get_secant_slope_group(\n'
                           '        x=1.5, graph=graph,\n'
                           '        dx=dx.get_value(), ...))\n'
                           'self.play(dx.animate.set_value(0.01))',
                           font_size=20, line_numbers=False)
        fit(panel, 5.3).move_to([4.25, -1.4, 0])
        dx_value = VGroup(MathTex('dx =', font_size=36), DecimalNumber(2.5, num_decimal_places=3, font_size=36))
        dx_value.arrange(RIGHT, buff=0.15).next_to(VGroup(caption, slope), DOWN, buff=0.35, aligned_edge=RIGHT)
        dx_value[1].add_updater(lambda m: m.set_value(dx.get_value()))
        self.play(FadeOut(card), FadeOut(secant_tag), FadeIn(panel), FadeIn(dx_value))

        # [V7.7b] dx shrinks: the second point slides in and the secant pivots
        self.at('As d x shrinks')
        mark = line_highlight(panel, 5)
        self.play(Create(mark))
        self.play(dx.animate.set_value(0.01), run_time=5)
        self.at('and then settles')
        self.play(Indicate(slope, scale_factor=1.3))
        self.at('For this curve')
        formula = MathTex(r'f(x) = \frac{x^2}{4} + 1', color=YELLOW, font_size=40).move_to(axes.c2p(0.6, 6.2))
        at_x = MathTex('x = 1.5', font_size=32, color=FOCUS).next_to(point, DR, buff=0.15)
        self.play(FadeOut(VGroup(panel, mark)), Write(formula), FadeIn(at_x))
        self.at('it settles at')
        self.play(dx.animate.set_value(0.001), run_time=1.5)
        settled = SurroundingRectangle(slope, color=AFTER, buff=0.12)
        self.play(Create(settled))

        # [V7.7c] it touches the curve at one point: the tangent, whose slope is the derivative
        self.at('touches the curve')
        p = np.array([1.5, secant_f(1.5)])
        tangent = Line(axes.c2p(*(p - [2.2, 0.75 * 2.2])), axes.c2p(*(p + [2.2, 0.75 * 2.2])))
        self.play(ShowPassingFlash(tangent.copy().set_stroke(WHITE, 10), time_width=0.6), run_time=1.5)
        self.play(Flash(point, color=WHITE, flash_radius=0.3))
        self.at("It's the tangent line")
        name = note('tangent', 28, GREEN).next_to(axes.c2p(3.7, secant_f(1.5) + 0.75 * 2.2), UP, buff=0.1)
        derivative = MathTex(r"\text{slope} = f'(1.5) = 0.75", font_size=36, color=AFTER)
        derivative.next_to(dx_value, DOWN, buff=0.45, aligned_edge=RIGHT)
        self.play(FadeIn(name))
        self.at('derivative')
        self.play(Write(derivative))

        # the limit, happening once more
        self.at('the limit happening')
        self.play(FadeOut(VGroup(settled, name, at_x)), dx.animate.set_value(2.5), run_time=1.5)
        self.play(dx.animate.set_value(0.001), run_time=3)
        self.finish()


class Segment_7_8(Segment):
    """Curves that aren't functions."""
    EPISODE, SEGMENT = 7, '7.8'

    def construct(self):
        axes = Axes(x_range=[-1.5, 1.5, 0.5], y_range=[-1.5, 1.5, 0.5], x_length=6.4, y_length=6.4, tips=False,
                    axis_config={'color': GREY_B}).to_edge(LEFT, buff=0.6).shift(DOWN * 0.3)
        self.play(Create(axes))

        # one height for each x
        wave = axes.plot(lambda x: 0.8 * (x ** 3 - x), x_range=[-1.45, 1.45], color=BLUE)
        self.play(Create(wave))
        sweep = ValueTracker(-1.4)

        def probe(heights):
            def build():
                x = sweep.get_value()
                line = DashedLine(axes.c2p(x, -1.5), axes.c2p(x, 1.5), color=GREY_A)
                return VGroup(line, *[Dot(axes.c2p(x, y), color=WARNING) for y in heights(x)])
            return always_redraw(build)

        self.at('one height for each x')
        one = probe(lambda x: [0.8 * (x ** 3 - x)])
        self.add(one)
        self.play(sweep.animate.set_value(1.4), run_time=1.8)
        self.remove(one)

        # [V7.8d] a circle has two heights: the vertical line test
        self.at('A circle has two heights')
        circle = axes.plot_parametric_curve(lambda t: (math.cos(t), math.sin(t)), t_range=[0, TAU], color=BLUE)
        self.play(FadeOut(wave), Create(circle), run_time=1)
        sweep.set_value(-0.95)
        two = probe(lambda x: [math.sqrt(max(1 - x * x, 0)), -math.sqrt(max(1 - x * x, 0))])
        self.add(two)
        self.play(sweep.animate.set_value(0.95), run_time=2)
        self.remove(two)
        verdict = VGroup(note('not a function of x,', 28, GREY_A),
                         note('but a perfectly good curve', 28, AFTER)).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        verdict.move_to([3.4, 2.3, 0])
        self.play(FadeIn(verdict[0]))
        self.play(FadeIn(verdict[1]))

        # [V7.8a] a parameter t drives the point
        self.at('describe the curve with a parameter')
        self.play(FadeOut(circle))

        def panel(source):
            return fit(code_panel(source, font_size=20, line_numbers=False), 6.6).move_to([3.5, 1.9, 0])

        circle_code = panel('axes.plot_parametric_curve(\n'
                            '    lambda t: (math.cos(t), math.sin(t)),\n'
                            '    t_range=[0, TAU])')
        self.at('Plot parametric curve')
        self.play(FadeOut(verdict), FadeIn(circle_code))
        t = ValueTracker(0)
        readout = VGroup(MathTex('t ='), DecimalNumber(0, num_decimal_places=2)).arrange(RIGHT, buff=0.2)
        readout.move_to([3.5, -1.2, 0])
        readout[1].add_updater(lambda m: m.set_value(t.get_value()))

        def tracer(x_of, y_of):
            return always_redraw(lambda: Dot(axes.c2p(x_of(t.get_value()), y_of(t.get_value())), color=FOCUS, radius=0.1))

        self.at('traces the point')
        dot = tracer(math.cos, math.sin)
        self.play(FadeIn(readout), FadeIn(dot))
        self.play(t.animate.set_value(TAU), Create(circle), run_time=4, rate_func=linear)
        self.at('give a circle')
        self.play(Indicate(circle_code))

        # [V7.8b] cos 3t, sin 2t: a Lissajous figure
        self.at('Cosine of three t')
        lissajous_code = panel('curve = axes.plot_parametric_curve(\n'
                               '    lambda t: (math.cos(3 * t), math.sin(2 * t)),\n'
                               '    t_range=[0, TAU])')
        lissajous = axes.plot_parametric_curve(lambda u: (math.cos(3 * u), math.sin(2 * u)), t_range=[0, TAU], color=FOCUS)
        self.remove(dot)
        t.set_value(0)
        dot = tracer(lambda u: math.cos(3 * u), lambda u: math.sin(2 * u))
        self.play(FadeOut(circle), FadeOut(circle_code), FadeIn(lissajous_code), FadeIn(dot))
        self.play(t.animate.set_value(TAU), Create(lissajous), run_time=6, rate_func=linear)
        name = note('a Lissajous curve', 26, FOCUS).next_to(readout, DOWN, buff=0.4)
        self.play(FadeIn(name))

        # [V7.8c] axis labels
        self.at('get axis labels')
        labels_code = panel('labels = axes.get_axis_labels(\n    x_label="x", y_label="y")')
        labels = axes.get_axis_labels(x_label='x', y_label='y')
        self.play(FadeOut(VGroup(lissajous_code, dot, readout, name)), FadeIn(labels_code))
        self.play(Write(labels))
        self.at('a picture without a caption')
        self.play(LaggedStart(*[Indicate(l, scale_factor=1.6) for l in labels], lag_ratio=0.4))
        self.finish()


class Segment_7_9(Segment, LinearTransformationScene):
    """Grids that bend: q07-05's LinearTransformationScene."""
    EPISODE, SEGMENT = 7, '7.9'

    def __init__(self, **kwargs):
        LinearTransformationScene.__init__(self, show_coordinates=True, leave_ghost_vectors=True, **kwargs)

    def setup(self):
        # Segment first: LinearTransformationScene.setup then empties foreground_mobjects, which
        # apply_matrix animates, so a review clock (SEGMENT_LABELS) is never animated with them.
        Segment.setup(self)
        LinearTransformationScene.setup(self)

    def apply_matrix(self, matrix, **kwargs):
        # Scene.play overwrites self.moving_mobjects (LinearTransformationScene's list of extra
        # mobjects to move) with whatever the last play animated; this scene adds none.
        self.moving_mobjects = []
        super().apply_matrix(matrix, **kwargs)

    def construct(self):
        # [V7.9a] the grid and the two basis arrows
        self.play(FadeIn(self.background_plane), FadeIn(self.plane), run_time=1.5)
        self.play(GrowArrow(self.i_hat), GrowArrow(self.j_hat))

        # what a linear transformation keeps
        self.at('A linear transformation')
        keeps = VGroup(*[backed(note(w, 26, GREY_A)) for w in ('lines stay straight', 'parallel', 'evenly spaced')])
        keeps.arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_corner(UR, buff=0.4)
        for words, phrase in zip(keeps, ('straight', 'parallel', 'evenly spaced')):
            self.at(phrase)
            self.play(FadeIn(words, shift=LEFT * 0.2), run_time=0.6)

        # [V7.9b] a two by two matrix describes one completely
        self.at('two by two matrix')
        matrix = Matrix([[1, 1], [0, 1]])
        columns = matrix.get_columns()
        columns[0].set_color(GREEN_C)
        columns[1].set_color(RED_C)
        matrix.to_corner(UL, buff=0.5)
        matrix_back = BackgroundRectangle(matrix, fill_opacity=0.9, buff=0.15)
        card = qr_card('q07-05')
        self.play(FadeOut(keeps), FadeIn(matrix_back), FadeIn(matrix), FadeIn(card))
        self.at('Its first column')
        first = SurroundingRectangle(columns[0], color=GREEN_C, buff=0.1)
        self.add_transformable_label(self.i_hat, r'\hat{\imath}', new_label=r'\hat{\imath}')
        first_link = CurvedArrow(first.get_bottom() + DOWN * 0.05, self.i_hat.get_end() + UP * 0.25, color=GREEN_C, angle=PI / 3)
        self.play(Create(first), Create(first_link))
        self.at('Its second column')
        second = SurroundingRectangle(columns[1], color=RED_C, buff=0.1)
        self.add_transformable_label(self.j_hat, r'\hat{\jmath}', new_label=r'\hat{\jmath}')
        second_link = CurvedArrow(second.get_bottom() + DOWN * 0.05, self.j_hat.get_end() + RIGHT * 0.3, color=RED_C,
                                  angle=PI / 3)
        self.play(Create(second), Create(second_link))
        self.at('Everything else follows')
        self.play(FadeOut(VGroup(first, first_link, second, second_link)))

        # Manim's LinearTransformationScene
        self.at('has a scene type')
        lines = snippet_source(GRID_SNIPPET).splitlines()
        source = '\n'.join([lines[3]] + [l.split('  #')[0].rstrip() for l in lines[7:13] if 'wait' not in l])
        panel = fit(code_panel(source, font_size=18, line_numbers=False), 7.4).to_corner(DL, buff=0.3)
        self.play(FadeOut(card), FadeIn(panel))
        self.at('It draws the grid')
        self.play(Indicate(self.i_hat, scale_factor=1.3), Indicate(self.j_hat, scale_factor=1.3))

        # [V7.9b] apply_matrix: a shear
        self.at('Call apply matrix')
        mark = line_highlight(panel, 2)
        self.play(Create(mark))
        vector = self.add_vector([1, 2], color=YELLOW)
        coords = self.add_transformable_label(vector, '(1, 2)', new_label='(3, 2)', at_tip=True)
        self.at('This shear')
        self.play(Transform(mark, line_highlight(panel, 3)))
        self.apply_matrix([[1, 1], [0, 1]], run_time=3)

        # [V7.9c] each column is where a basis arrow landed
        slides = VGroup()
        for column, target in ((columns[0], self.i_hat), (columns[1], self.j_hat)):
            copy = column.copy()
            slides.add(copy)
        self.play(slides[0].animate.next_to(self.i_hat.get_end(), DR, buff=0.1),
                  slides[1].animate.next_to(self.j_hat.get_end(), UR, buff=0.1), run_time=1.5)
        self.at('rides along')
        self.play(Indicate(coords, scale_factor=1.4), Indicate(vector))

        # [V7.9d] a quarter turn spins the sheared plane
        self.at('a quarter-turn')
        turn = Matrix([[0, -1], [1, 0]])
        turn.get_columns()[0].set_color(GREEN_C)
        turn.get_columns()[1].set_color(RED_C)
        turn.move_to(matrix, aligned_edge=LEFT)
        coords.target_text = '(-2, 3)'
        self.play(FadeOut(slides), ReplacementTransform(matrix, turn), Transform(mark, line_highlight(panel, 4)))
        self.apply_matrix([[0, -1], [1, 0]], run_time=3)

        # pause, scan the code, try your own matrices
        self.at('worth slowing down')
        self.play(FadeOut(mark), FadeIn(qr_card('q07-05')))
        self.wait(8)        # a QR card stays up at least 8 seconds, even past the narration
        self.finish()


# ---------------------------------------------------------------- recap pictures

def tile_axes(width=2.6, height=1.7, x_max=3, y_max=3):
    return Axes(x_range=[0, x_max, 1], y_range=[0, y_max, 1], x_length=width, y_length=height, tips=False,
                axis_config={'color': GREY_B, 'stroke_width': 2, 'include_ticks': False})


def ruler_tile():
    axes = tile_axes()
    dot = Dot(axes.c2p(2, 2), color=FOCUS, radius=0.07)
    numbers = MathTex('(2,\\ 2)', font_size=24, color=FOCUS).next_to(dot, UL, buff=0.05)
    screen = Rectangle(width=1.1, height=0.75).set_stroke(GREY_A, 2).next_to(axes, RIGHT, buff=0.7)
    pixel = Dot(screen.get_center() + RIGHT * 0.2 + UP * 0.1, color=GREY_A, radius=0.06)
    arrow = CurvedArrow(dot.get_center() + RIGHT * 0.15, pixel.get_center() + LEFT * 0.1, angle=-PI / 3, color=GREY_B)
    word = code_text('c2p', 20, FOCUS).next_to(arrow, UP, buff=0.05)
    return VGroup(axes, dot, numbers, screen, pixel, arrow, word)


def samples_tile():
    axes = tile_axes()
    curve = axes.plot(lambda x: 0.3 * x ** 2 + 0.2, x_range=[0, 3, 0.25], color=YELLOW, stroke_opacity=0.5)
    dots = VGroup(*[Dot(p, radius=0.04, color=WHITE) for p in sample_points(curve)])
    return VGroup(axes, curve, dots)


def area_tile():
    axes = tile_axes()
    curve = axes.plot(lambda x: 0.3 * x ** 2 + 0.2, x_range=[0, 3], color=YELLOW)
    rects = axes.get_riemann_rectangles(curve, x_range=[0, 1.5], dx=0.25, fill_opacity=0.6, stroke_width=0.5)
    area = axes.get_area(curve, x_range=[1.5, 3], color=BLUE, opacity=0.6)
    return VGroup(axes, rects, area, curve)


def bound_tile():
    axes = Axes(x_range=[0, 6.5, 1], y_range=[-1.2, 1.2, 1], x_length=2.8, y_length=1.7, tips=False,
                axis_config={'color': GREY_B, 'stroke_width': 2, 'include_ticks': False})
    curve = axes.plot(math.sin, x_range=[0, 6.5], color=YELLOW)
    area = axes.get_area(curve, x_range=[0, 4.2], color=[BLUE, GREEN], opacity=0.5)
    edge = axes.get_vertical_line(axes.i2gp(4.2, curve), color=WHITE)
    return VGroup(axes, area, curve, edge)


def tangent_tile():
    axes = tile_axes()
    curve = axes.plot(lambda x: 0.3 * x ** 2 + 0.2, x_range=[0, 3], color=YELLOW)
    p = np.array([1.3, 0.3 * 1.3 ** 2 + 0.2])
    secant = DashedLine(axes.c2p(0.4, 0.3 * 0.4 ** 2 + 0.2 - 0.3), axes.c2p(3, 0.3 * 9 + 0.2 + 0.4), color=GREY_B)
    slope = 0.6 * 1.3
    tangent = Line(axes.c2p(*(p - [1.1, 1.1 * slope])), axes.c2p(*(p + [1.4, 1.4 * slope])), color=GREEN)
    return VGroup(axes, curve, secant, tangent, Dot(axes.c2p(*p), color=FOCUS, radius=0.06))


def grid_tile():
    plane = NumberPlane(x_range=[-3, 3, 0.5], y_range=[-2, 2, 0.5], x_length=3, y_length=2,
                        background_line_style={'stroke_color': BLUE_D, 'stroke_width': 1.5})
    plane.apply_matrix([[1, 0.6], [0, 1]])
    arrows = VGroup(Arrow(plane.c2p(0, 0), plane.c2p(1, 0), buff=0, color=GREEN_C, stroke_width=4),
                    Arrow(plane.c2p(0, 0), plane.c2p(0, 1), buff=0, color=RED_C, stroke_width=4))
    return VGroup(plane, arrows)


class Segment_7_10(Segment):
    """Recap."""
    EPISODE, SEGMENT = 7, '7.10'

    def construct(self):
        # [V7.10a] one picture per idea, on its words
        items = [(ruler_tile(), 'c2p: graph → screen', 'Axes give'),
                 (samples_tile(), 'sampled curves', 'Plots are sampled'),
                 (area_tile(), 'rectangles → area', 'and get area'),
                 (bound_tile(), 'accumulation', 'a moving bound'),
                 (tangent_tile(), 'secant → tangent', 'a shrinking'),
                 (grid_tile(), 'matrices move space', 'And linear transformation')]
        tiles = VGroup()
        for picture, words, _ in items:
            picture.scale_to_fit_height(2.1)
            if picture.width > 3.9:
                picture.scale_to_fit_width(3.9)
            caption = note(words, 26, GREY_A).next_to(picture, DOWN, buff=0.25)
            tiles.add(VGroup(picture, caption))
        for k, tile in enumerate(tiles):
            tile.move_to([(-4.6, 0, 4.6)[k % 3], (1.85, -1.95)[k // 3], 0])
        for tile, (_, _, phrase) in zip(tiles, items):
            self.at(phrase)
            self.play(FadeIn(tile, shift=UP * 0.2), run_time=0.8)

        # [V7.10b] the QR wall, 10 seconds
        self.at('So far, the camera', lead=0.5)
        wall = qr_wall([f'q07-0{i}' for i in range(1, 6)])
        heading = Text('Episode 7 · scan to open each scene', font_size=26, color=SCAFFOLD).to_corner(UL, buff=0.3)
        self.play(FadeOut(tiles), FadeIn(wall), FadeIn(heading))
        self.wait(10)

        # [V7.10c] teaser: the camera dives into one dot of a grid (episode 8)
        self.play(FadeOut(VGroup(wall, heading)))
        dots = VGroup(*[Dot([x * 0.9, y * 0.9, 0], radius=0.06, color=GREY_B) for x in range(-7, 8) for y in range(-4, 5)])
        chosen = dots[7 * 9 + 5 + 2 * 9]
        chosen.set_color(FOCUS)
        self.play(FadeIn(dots, lag_ratio=0.01), run_time=1)
        self.play(dots.animate.shift(-chosen.get_center()), run_time=0.8)
        self.play(dots.animate.scale(40, about_point=ORIGIN), run_time=2, rate_func=rush_into)
        nxt = Text('Next: Cameras and the third dimension', font_size=34).to_edge(DOWN, buff=0.5)
        self.play(Write(nxt))
        self.wait(1.5)
        self.finish()
