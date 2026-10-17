"""Episode 6 · Things that change. One Scene per script segment.

    python3 video-series/production/render.py 6 [-ql] [segment ...]

Shot ids in comments ([V6.2c] ...) refer to episodes/06-things-that-change.md.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403

LABEL_SNIPPET = 'ep06/01-label-follows-dot.py'
WHEEL_SNIPPET = 'ep06/02-time-based.py'
TRACKER_SNIPPET = 'ep06/03-tracker-and-number.py'
REDRAW_SNIPPET = 'ep06/04-always-redraw.py'
SINE_SNIPPET = 'ep06/05-circle-to-sine.py'


# ---------------------------------------------------------------- the snippets' objects

def wheel(color, radius=1.2):
    """The q06-02 wheel: a circle and three spokes, centred on the origin."""
    spokes = [Line(ORIGIN, RIGHT * radius).rotate(k * TAU / 3, about_point=ORIGIN) for k in range(3)]
    return VGroup(Circle(radius=radius, color=color), *spokes)


def spin(mob, turns_per_second):
    """A dt updater turning mob clockwise about its own centre, as in q06-02."""
    mob.add_updater(lambda m, dt: m.rotate(-dt * TAU * turns_per_second))
    return mob


class Unroll:
    """The q06-05 scene, drawn at any scale and offset: one tracker t drives every part."""

    def __init__(self, t, scale=1.0, shift=ORIGIN):
        self.t, self.s, self.o = t, scale, np.array(shift, dtype=float)
        self.center = self.p(LEFT * 4.5)

    def p(self, point):
        return self.o + self.s * np.array(point, dtype=float)

    def on_circle(self):
        a = self.t.get_value()
        return self.p(LEFT * 4.5 + 1.5 * (math.cos(a) * RIGHT + math.sin(a) * UP))

    def on_wave(self):
        a = self.t.get_value()
        return self.p(LEFT * 2.5 + RIGHT * a * 9 / TAU + UP * 1.5 * math.sin(a))

    def static(self):
        return VGroup(Circle(radius=1.5 * self.s, color=BLUE).move_to(self.center),
                      Line(self.p(LEFT * 2.5), self.p(RIGHT * 6.5), color=GREY))

    def parts(self):
        """The five moving parts, in the order 6.1 counts them."""
        r = DEFAULT_DOT_RADIUS * max(self.s, 0.7)
        return {
            'radius': always_redraw(lambda: Line(self.center, self.on_circle())),
            'dot': always_redraw(lambda: Dot(self.on_circle(), radius=r, color=YELLOW)),
            'link': always_redraw(lambda: DashedLine(self.on_circle(), self.on_wave(), color=GREY)),
            'wave dot': always_redraw(lambda: Dot(self.on_wave(), radius=r, color=YELLOW)),
            'trail': TracedPath(self.on_wave, stroke_color=YELLOW, stroke_width=4),
        }

    @staticmethod
    def drawn(parts):
        """The snippet's drawing order: radius, link, trail, then both dots on top."""
        return [parts[k] for k in ('radius', 'link', 'trail', 'dot', 'wave dot')]


def corner_triangle(angle, radius=2.5, **style):
    """The q06-04 triangle: centre, foot on the axis, tip on the circle."""
    foot = radius * math.cos(angle) * RIGHT
    tip = foot + radius * math.sin(angle) * UP
    return Polygon(ORIGIN, foot, tip, **({'color': YELLOW, 'fill_opacity': 0.3} | style))


# ---------------------------------------------------------------- icons

def gear(radius=0.35, teeth=8, color=GREY_A):
    points = []
    for k in range(teeth * 4):
        a = k * TAU / (teeth * 4)
        r = radius if k % 4 in (0, 1) else radius * 0.75
        points.append([r * math.cos(a), r * math.sin(a), 0])
    return VGroup(Polygon(*points, color=color, stroke_width=3), Circle(radius=radius * 0.3, color=color, stroke_width=3))


def stopwatch(radius=0.35, color=GREY_A):
    face = Circle(radius=radius, color=color, stroke_width=3)
    stem = Line(face.get_top(), face.get_top() + UP * 0.1, color=color, stroke_width=4)
    button = Line(LEFT * 0.08, RIGHT * 0.08, color=color, stroke_width=6).move_to(stem.get_end() + UP * 0.03)
    hand = Line(ORIGIN, UP * radius * 0.75, color=FOCUS, stroke_width=4).rotate(-PI / 3, about_point=ORIGIN)
    return VGroup(face, stem, button, hand)


def recycle_icon(radius=0.32, color=AFTER):
    arrows = VGroup()
    for k in range(3):
        arc = Arc(radius=radius, start_angle=PI / 2 + k * TAU / 3 + 0.3, angle=TAU / 3 - 0.6, color=color, stroke_width=4)
        arc.add_tip(tip_length=0.13, tip_width=0.13)
        arrows.add(arc)
    return arrows


def pen_icon(color=GREY_A):
    body = Rectangle(width=0.16, height=0.62).set_stroke(color, 3)
    nib = Polygon(body.get_corner(DL), body.get_corner(DR), body.get_bottom() + DOWN * 0.2, color=color, stroke_width=3)
    pen = VGroup(body, nib).rotate(-PI / 6)
    tip = nib.get_vertices()[2]
    trail = FunctionGraph(lambda x: 0.1 * math.sin(4 * x), x_range=[-0.9, 0], color=FOCUS, stroke_width=3)
    trail.shift(tip - trail.get_end())
    return VGroup(trail, pen)


def trash_can(color=GREY_B):
    body = Polygon([-0.35, 0.4, 0], [0.35, 0.4, 0], [0.27, -0.45, 0], [-0.27, -0.45, 0], color=color, stroke_width=3)
    lid = Line([-0.45, 0.5, 0], [0.45, 0.5, 0], color=color, stroke_width=4)
    handle = Line([-0.12, 0.6, 0], [0.12, 0.6, 0], color=color, stroke_width=4)
    ribs = VGroup(*[Line([x, 0.28, 0], [x * 0.8, -0.33, 0], color=color, stroke_width=2) for x in (-0.15, 0, 0.15)])
    return VGroup(body, lid, handle, ribs)


def tracker_icon(value='7.5'):
    """An invisible box holding a number, with two wires leading out of it."""
    number = Text(value, font_size=24, color=FOCUS)
    box = DashedVMobject(RoundedRectangle(width=0.9, height=0.55, corner_radius=0.08), num_dashes=24).set_stroke(GREY_B, 2)
    ends = [box.get_right() + RIGHT * 0.7 + UP * 0.35, box.get_right() + RIGHT * 0.7 + DOWN * 0.35]
    wires = VGroup(*[CubicBezier(box.get_right(), box.get_right() + RIGHT * 0.35, e + LEFT * 0.35, e).set_stroke(FOCUS, 2)
                     for e in ends])
    dots = VGroup(*[Dot(e, radius=0.06, color=GREY_A) for e in ends])
    return VGroup(box, number.move_to(box), wires, dots)


def check_mark(size=0.5, color=AFTER):
    return VMobject().set_points_as_corners([[-0.5, 0, 0], [-0.15, -0.4, 0], [0.55, 0.45, 0]]).scale(size).set_stroke(color, 8)


def cross_mark(size=0.4, color=WARNING):
    return VGroup(Line(UL, DR), Line(UR, DL)).scale(size).set_stroke(color, 8)


def badge(n, color=FOCUS):
    ring = Circle(radius=0.2, color=color, stroke_width=3).set_fill(BLACK, 0.85)
    return VGroup(ring, Text(str(n), font_size=22, color=color).move_to(ring))


def tracker_box(tracker, name='x', font_size=34, decimals=2):
    """A ValueTracker drawn as a dashed box: it holds a number and is never drawn itself."""
    title = Text('ValueTracker', font_size=18, color=SCAFFOLD)
    label = code_text(f'{name} =', 24, GREY_A)
    number = DecimalNumber(tracker.get_value(), num_decimal_places=decimals, font_size=font_size, color=FOCUS)
    row = VGroup(label, number).arrange(RIGHT, buff=0.18)
    body = VGroup(title, row).arrange(DOWN, buff=0.14)
    frame = DashedVMobject(RoundedRectangle(width=body.width + 0.5, height=body.height + 0.4, corner_radius=0.12),
                           num_dashes=40).set_stroke(GREY_B, 2).move_to(body)
    number.add_updater(lambda m: m.set_value(tracker.get_value()))
    return VGroup(frame, title, row)


def film_strip(n, frame_w=2.3, frame_h=1.5, gap=0.9):
    """A strip of film: VGroup(band, sprocket holes, windows)."""
    windows = VGroup(*[Rectangle(width=frame_w, height=frame_h).set_stroke(GREY_B, 2).set_fill(BLACK, 1)
                       for _ in range(n)]).arrange(RIGHT, buff=gap)
    band = Rectangle(width=windows.width + 2 * gap, height=frame_h + 0.8).set_fill('#24282d', 1).set_stroke(width=0)
    band.move_to(windows)
    holes = VGroup()
    count = int(band.width / 0.42)
    for y in (band.get_top()[1] - 0.2, band.get_bottom()[1] + 0.2):
        for i in range(count):
            holes.add(RoundedRectangle(width=0.2, height=0.15, corner_radius=0.04).set_fill(BLACK, 1).set_stroke(width=0)
                      .move_to([band.get_left()[0] + 0.21 + i * band.width / count, y, 0]))
    return VGroup(band, holes, windows)


def snippet_line(path, n, font_size=24):
    """One snippet line without its trailing comment."""
    return code_text(snippet_lines(path, n, n).split('  #')[0].strip(), font_size)


def lines_box(code, first, last, color=FOCUS):
    """A highlight spanning several lines (0-based, inclusive) of a code_panel."""
    top, bottom = line_highlight(code, first, color), line_highlight(code, last, color)
    box = Rectangle(width=top.width, height=top.get_top()[1] - bottom.get_bottom()[1])
    return box.set_stroke(color, 3).move_to((top.get_top() + bottom.get_bottom()) / 2)


def flash_copy(mob, color=WHITE, width=10):
    return mob.copy().clear_updaters().set_fill(opacity=0).set_stroke(color, width)


class Segment_6_1(Segment):
    """Cold open: a circle unrolls into a wave."""
    EPISODE, SEGMENT = 6, '6.1'

    def construct(self):
        # [V6.1a] q06-05 at full screen, exactly as the snippet plays it
        t = ValueTracker(0)
        scene = Unroll(t)
        parts = scene.parts()
        self.add(scene.static(), *scene.drawn(parts))
        self.play(t.animate.set_value(TAU), run_time=6, rate_func=linear)
        self.hold_until(0.16)

        # again, stopping partway round so every part is easy to see
        self.play(t.animate.set_value(0), FadeOut(parts['trail']), run_time=1.2)
        self.remove(parts['trail'])
        parts['trail'] = TracedPath(scene.on_wave, stroke_color=YELLOW, stroke_width=4)
        self.add(parts['trail'])
        self.bring_to_front(parts['dot'], parts['wave dot'])
        self.play(t.animate.set_value(2.4), run_time=2.2)
        for part in parts.values():
            part.clear_updaters()

        # [V6.1b] the five parts glow in turn
        c, w = scene.on_circle(), scene.on_wave()
        spots = {
            'radius': (scene.center + c) / 2 + (DOWN + RIGHT) * 0.3,
            'dot': c + UL * 0.42,
            'link': c + (w - c) * 0.45 + UP * 0.38,
            'wave dot': w + UR * 0.42,
            'trail': scene.p(LEFT * 2.5 + RIGHT * 9 / 4 + UP * 1.5) + UP * 0.45,
        }
        flashes = {
            'radius': flash_copy(parts['radius']),
            'dot': Circle(radius=0.22).move_to(c).set_stroke(WHITE, 6),
            'link': Line(c, w).set_stroke(WHITE, 8),
            'wave dot': Circle(radius=0.22).move_to(w).set_stroke(WHITE, 6),
            'trail': flash_copy(parts['trail']),
        }
        badges = VGroup()
        for n, (key, fraction) in enumerate(zip(spots, (0.269, 0.29, 0.344, 0.376, 0.43)), start=1):
            self.hold_until(fraction)
            b = badge(n).move_to(spots[key])
            badges.add(b)
            self.play(ShowPassingFlash(flashes[key], time_width=0.6), FadeIn(b, scale=0.5), run_time=0.9)

        # five moving parts...
        counter = VGroup(Text('5 moving parts,', font_size=40), Text('1 number', font_size=40, color=FOCUS))
        counter.arrange(RIGHT, buff=0.25).to_edge(UP, buff=0.6)
        self.hold_until(0.505)
        self.play(FadeIn(counter[0], shift=DOWN * 0.2), LaggedStart(*[Indicate(b) for b in badges], lag_ratio=0.15))

        # ...and one number: the tracker t, which carries everything round the rest of the lap
        self.hold_until(0.871)
        box = tracker_box(t, 't').to_edge(DOWN, buff=0.45)
        self.play(FadeIn(counter[1], shift=DOWN * 0.2), FadeIn(box), FadeOut(badges))
        for key in ('radius', 'dot', 'link', 'wave dot'):
            self.remove(parts[key])
        live = scene.parts()
        self.add(*scene.drawn(live))
        self.play(t.animate.set_value(TAU), run_time=3.2, rate_func=linear)
        self.finish()


class Segment_6_2(Segment):
    """The problem with telling everything what to do."""
    EPISODE, SEGMENT = 6, '6.2'

    def construct(self):
        # [V6.2a] only the dot is animated; the label stays behind
        dot = Dot(LEFT * 4, color=FOCUS, radius=0.12)
        label = Text('I follow', font_size=28).next_to(dot, UP)
        self.play(FadeIn(dot), FadeIn(label))
        code = code_text('self.play(dot.animate.shift(RIGHT * 6))', 26).to_edge(UP, buff=0.7)
        self.hold_until(0.089)
        self.play(FadeIn(code))
        self.play(dot.animate.shift(RIGHT * 6), run_time=2)
        caption = Text('only the dot was animated', font_size=30, color=SCAFFOLD).to_edge(DOWN, buff=0.9)
        self.play(FadeIn(caption), Indicate(label, color=WARNING))

        # [V6.2b] animate the label too: it works, for this one motion
        self.hold_until(0.214)
        both = code_text('self.play(dot.animate.shift(RIGHT * 6),\n          label.animate.shift(RIGHT * 6))', 26)
        both.to_edge(UP, buff=0.7)
        self.play(FadeOut(caption), dot.animate.move_to(LEFT * 4), ReplacementTransform(code, both))
        self.play(dot.animate.shift(RIGHT * 6), label.animate.shift(RIGHT * 6), run_time=2)
        self.hold_until(0.304)
        tick = check_mark().next_to(label, RIGHT, buff=0.5)
        self.play(Create(tick))

        # every move, twice: and you have to work out how
        self.hold_until(0.357)
        self.play(FadeOut(VGroup(dot, label, both, tick)))
        moves = [('dot.animate.shift(UP * 2)', 'label.animate.shift(UP * 2)'),
                 ('dot.animate.move_to(ORIGIN)', 'label.animate.move_to(UP * 0.45)'),
                 ('dot.animate.scale(2)', 'label.animate.shift(UP * 0.12)')]
        rows = VGroup(*[VGroup(code_text(a, 24), code_text(b, 24, ORANGE)) for a, b in moves])
        for row in rows:
            row.arrange(RIGHT, buff=0.8)
        rows.arrange(DOWN, buff=0.45)
        for row in rows:
            row[1].align_to(rows[0][1], LEFT)
        for row in rows:
            row[0].align_to(rows[0][0], LEFT)
        rows.move_to(UP * 0.4)
        twice = Text('every move, twice, and worked out by hand', font_size=30, color=SCAFFOLD).to_edge(DOWN, buff=0.9)
        self.play(LaggedStart(*[FadeIn(r[0]) for r in rows], lag_ratio=0.3))
        self.play(LaggedStart(*[FadeIn(r[1], shift=LEFT * 0.3) for r in rows], lag_ratio=0.5), FadeIn(twice), run_time=2.5)

        # [V6.2c] along an arc, a straight shift can't keep up
        self.hold_until(0.554)
        self.play(FadeOut(VGroup(rows, twice)))
        dot = Dot(LEFT * 2.5, color=FOCUS, radius=0.12)
        label = Text('I follow', font_size=28).next_to(dot, UP)
        track = DashedVMobject(Circle(radius=2.5), num_dashes=60).set_stroke(GREY_D, 2)
        centre = Dot(ORIGIN, radius=0.05, color=GREY_B)
        arc_code = code_text('self.play(Rotate(dot, -PI, about_point=ORIGIN),\n          label.animate.shift(RIGHT * 5))', 24)
        arc_code.to_edge(UP, buff=0.35).to_edge(LEFT, buff=0.5)
        self.play(FadeIn(VGroup(track, centre, dot, label, arc_code)))
        dot_trail = TracedPath(dot.get_center, stroke_color=FOCUS, stroke_width=3)
        label_trail = TracedPath(label.get_bottom, stroke_color=WARNING, stroke_width=3)
        self.add(dot_trail, label_trail)
        # halfway: the same motion, frozen at its midpoint
        self.play(Rotate(dot, -PI, about_point=ORIGIN), label.animate.shift(RIGHT * 5),
                  rate_func=lambda a: 0.5 * smooth(a), run_time=1.8)
        ghost = DashedVMobject(SurroundingRectangle(label.copy().next_to(dot, UP), buff=0.08), num_dashes=30)
        ghost.set_stroke(GREY_B, 2)
        apart = DashedLine(label.get_top(), dot.get_bottom(), color=WARNING)
        miss = cross_mark(0.25).next_to(label, RIGHT, buff=0.4)
        self.play(Create(ghost), Create(apart), Create(miss))
        self.wait(1.5)
        self.play(FadeOut(VGroup(ghost, apart)))
        self.play(Rotate(dot, -PI / 2, about_point=ORIGIN), label.animate.shift(RIGHT * 2.5), miss.animate.shift(RIGHT * 2.5),
                  rate_func=lambda a: 2 * (smooth(0.5 + 0.5 * a) - 0.5), run_time=1.8)
        dot_trail.clear_updaters()
        label_trail.clear_updaters()

        # it's a relationship: the label is always just above the dot
        self.hold_until(0.696)
        self.play(FadeOut(VGroup(track, centre, dot, label, arc_code, dot_trail, label_trail, miss)))
        order = Text('"move the label to here"', font_size=40, color=GREY_B).shift(UP * 1.2)
        strike = Line(order.get_left(), order.get_right(), color=WARNING, stroke_width=5)
        self.play(FadeIn(order))
        self.play(Create(strike))
        relation = Text('"the label is always just above the dot"', font_size=40, color=FOCUS).shift(DOWN * 0.3)
        self.hold_until(0.77)
        self.play(FadeIn(relation, shift=UP * 0.2))
        self.hold_until(0.92)
        cog = spin(gear(0.45, color=FOCUS), 0.25).next_to(relation, DOWN, buff=0.7)
        self.play(FadeIn(cog, scale=0.6))
        self.finish()


class Segment_6_3(Segment):
    """Updaters."""
    EPISODE, SEGMENT = 6, '6.3'

    def construct(self):
        # [V6.3a] before every frame is captured, the updaters run
        strip = film_strip(4).shift(UP * 0.4)
        band, holes, windows = strip
        gears = VGroup(*[spin(gear(0.28), 0.4).move_to(w.get_left() + LEFT * 0.45) for w in windows])
        dots, labels, arrows, captured = VGroup(), VGroup(), VGroup(), VGroup()
        for k, w in enumerate(windows):
            d = Dot(w.get_center() + RIGHT * (-0.7 + 0.45 * k) + DOWN * 0.3, radius=0.07, color=FOCUS)
            stale = Text('I follow', font_size=16).next_to(d.get_center() + LEFT * 0.45, UP, buff=0.12)
            dots.add(d)
            labels.add(stale)
            arrows.add(Arrow(gears[k].get_right(), stale.get_left(), buff=0.06, stroke_width=3, color=FOCUS,
                             max_tip_length_to_length_ratio=0.3))
            captured.add(Text('captured', font_size=16, color=SCAFFOLD).next_to(w, DOWN, buff=0.5))
        legend = VGroup(gear(0.18), Text('updaters run', font_size=22, color=SCAFFOLD),
                        Square(0.3).set_stroke(WHITE, 2), Text('then the frame is captured', font_size=22, color=SCAFFOLD))
        legend.arrange(RIGHT, buff=0.2)
        legend[2].shift(RIGHT * 0.5)
        legend[3].shift(RIGHT * 0.5)
        legend.next_to(strip, DOWN, buff=0.6)
        self.play(FadeIn(VGroup(band, holes, windows, gears, dots, labels)), FadeIn(legend))
        for k in range(4):
            self.play(Indicate(gears[k], color=FOCUS, scale_factor=1.3), GrowArrow(arrows[k]), run_time=0.6)
            self.play(labels[k].animate.next_to(dots[k], UP, buff=0.12), run_time=0.5)
            shot = windows[k].copy().set_fill(WHITE, 0.6).set_stroke(WHITE, 4)
            self.play(FadeIn(shot, rate_func=there_and_back), FadeOut(arrows[k]), FadeIn(captured[k]), run_time=0.5)
            self.remove(shot)
        self.hold_until(0.134)

        # [V6.3d] the updater: m is the object being updated; lambda is a one-line function
        self.play(FadeOut(VGroup(band, holes, windows, gears, dots, labels, captured, legend)))
        source = 'label.add_updater(lambda m: m.next_to(dot, UP))'
        line = code_text(source, 32).to_edge(UP, buff=0.9)
        dot = Dot(LEFT * 3.5 + DOWN * 1.2, color=FOCUS, radius=0.12)
        label = Text('I follow', font_size=28).add_updater(lambda m: m.next_to(dot, UP))
        self.play(FadeIn(line), FadeIn(dot), FadeIn(label))
        self.hold_until(0.203)
        param = source.index('lambda m') + 7
        used = source.index(': m.') + 2
        rings = VGroup(*[Circle(color=FOCUS, stroke_width=3).surround(chars(line, source, i, i + 1), buffer_factor=1.8)
                         for i in (param, used)])
        pointer = Arrow(rings[1].get_bottom(), label.get_right() + RIGHT * 0.1, buff=0.1, color=FOCUS, stroke_width=4)
        meaning = Text('the object being updated', font_size=26, color=FOCUS).next_to(pointer.get_end(), RIGHT, buff=0.3)
        meaning.shift(DOWN * 0.1)
        self.play(Create(rings), run_time=0.8)
        self.play(GrowArrow(pointer), FadeIn(meaning))
        self.hold_until(0.291)
        self.play(FadeOut(VGroup(rings, pointer, meaning)))
        start = source.index('lambda')
        lam = SurroundingRectangle(chars(line, source, start, source.index(':') + 1), color=TEAL, buff=0.08)
        same = code_text('def follow(m):\n    m.next_to(dot, UP)\n\nlabel.add_updater(follow)', 26)
        same.move_to(RIGHT * 2.6 + DOWN * 1.2)
        note = Text('a small function, in one line', font_size=26, color=TEAL).next_to(lam, DOWN, buff=0.35)
        same_note = Text('the same thing, written out', font_size=22, color=SCAFFOLD).next_to(same, UP, buff=0.35)
        self.play(Create(lam), FadeIn(note))
        self.play(FadeIn(same), FadeIn(same_note))

        # [V6.3b] q06-01: only the dot is animated; the label follows every frame
        self.hold_until(0.424)
        self.play(FadeOut(VGroup(line, dot, label, lam, note, same, same_note)))
        dot = Dot(LEFT * 4, color=YELLOW)
        label = Text("I follow", font_size=28)
        label.add_updater(lambda m: m.next_to(dot, UP))
        card = qr_card('q06-01')
        current = snippet_line(LABEL_SNIPPET, 8).to_corner(UL, buff=0.4)
        self.play(FadeIn(dot), FadeIn(label), FadeIn(card), FadeIn(current))

        def show_line(n):
            nonlocal current
            new = snippet_line(LABEL_SNIPPET, n).to_corner(UL, buff=0.4)
            self.play(FadeOut(current), FadeIn(new), run_time=0.4)
            current = new

        self.hold_until(0.459)
        show_line(10)
        self.play(dot.animate.shift(RIGHT * 8), run_time=2)
        self.hold_until(0.494)
        show_line(11)
        self.play(dot.animate.move_to(UP * 2), run_time=1.5)
        self.hold_until(0.529)
        show_line(12)
        orbit = DashedVMobject(Circle(radius=2), num_dashes=50).set_stroke(GREY_D, 2)
        self.play(FadeIn(orbit), run_time=0.4)
        self.play(Rotate(dot, TAU, about_point=ORIGIN), run_time=3)
        self.play(FadeOut(orbit), run_time=0.4)
        never = Text('the label is never mentioned in these animations', font_size=26, color=SCAFFOLD).to_edge(DOWN, buff=0.5)
        never.to_edge(LEFT, buff=0.5)
        self.hold_until(0.628)
        self.play(FadeIn(never))

        # [V6.3c] clear_updaters: the relationship ends and the label stays put
        self.hold_until(0.686)
        self.play(FadeOut(never))
        show_line(13)
        label.clear_updaters()
        self.play(Indicate(current, color=FOCUS, scale_factor=1.05))
        show_line(14)
        self.play(dot.animate.move_to(DOWN * 3))
        stays = Text('the label stays where it was', font_size=26, color=SCAFFOLD).next_to(label, RIGHT, buff=0.6)
        self.play(FadeIn(stays))

        # script a few objects; describe how the rest relate to them
        self.hold_until(0.831)
        self.play(FadeOut(VGroup(dot, label, card, current, stays)))
        leader = Dot(LEFT * 4.5 + DOWN * 1.5, color=FOCUS, radius=0.14)
        name = Text('scripted', font_size=24, color=FOCUS).add_updater(lambda m: m.next_to(leader, UP, buff=0.15))
        ring = Circle(radius=0.38, color=BLUE, stroke_width=3).add_updater(lambda m: m.move_to(leader))
        anchor = Dot(DOWN * 3.4 + LEFT * 6.5, radius=0.06, color=GREY_B)
        tether = always_redraw(lambda: Line(anchor.get_center(), leader.get_center(), color=GREY_B, stroke_width=2))
        shadow = Ellipse(width=0.6, height=0.18, color=GREY_D).set_fill(GREY_D, 0.6)
        shadow.add_updater(lambda m: m.move_to([leader.get_x(), -3.3, 0]))
        trail = TracedPath(leader.get_center, stroke_color=FOCUS, stroke_width=3, dissipating_time=1.5)
        heading = VGroup(Text('script a few,', font_size=36),
                         Text('describe how the rest relate', font_size=36, color=BLUE)).arrange(RIGHT, buff=0.25)
        heading.to_edge(UP, buff=0.6)
        self.add(trail, tether)
        self.play(FadeIn(VGroup(leader, name, ring, anchor, shadow)), FadeIn(heading))
        path = VMobject().set_points_smoothly([LEFT * 4.5 + DOWN * 1.5, LEFT * 2 + UP * 1.6, RIGHT * 0.5 + DOWN * 0.8,
                                               RIGHT * 3 + UP * 1.4, RIGHT * 4.8 + DOWN * 1.2])
        self.play(MoveAlongPath(leader, path), run_time=5, rate_func=smooth)
        self.finish()


class Segment_6_4(Segment):
    """Updaters that know what time it is."""
    EPISODE, SEGMENT = 6, '6.4'

    def construct(self):
        # [V6.4a] q06-02: two wheels with dt updaters, turning even with nothing playing
        slow, fast = wheel(BLUE).shift(LEFT * 3.6 + DOWN * 1.1), wheel(YELLOW).shift(RIGHT * 1.2 + DOWN * 1.1)
        spin(slow, 0.25)
        spin(fast, 0.5)
        card = qr_card('q06-02')
        self.play(FadeIn(slow), FadeIn(fast), FadeIn(card))
        self.hold_until(0.1)
        code = code_panel(snippet_lines(WHEEL_SNIPPET, 12, 16), font_size=20)
        fit(code, 12).to_edge(UP, buff=0.3)
        self.play(FadeIn(code))
        dt_word = Text('dt: the time since the last frame', font_size=24, color=FOCUS).next_to(code, DOWN, buff=0.2)
        self.play(FadeIn(dt_word))
        self.hold_until(0.217)
        mark = line_highlight(code, 0)
        self.play(FadeOut(dt_word), Create(mark))
        self.play(Transform(mark, line_highlight(code, 1)))
        self.hold_until(0.292)
        rates = VGroup(Text('¼ turn per second', font_size=26, color=BLUE).next_to(slow, DOWN, buff=0.3),
                       Text('½ turn per second', font_size=26, color=YELLOW).next_to(fast, DOWN, buff=0.3))
        self.play(FadeOut(mark), FadeIn(rates[0]))
        self.play(FadeIn(rates[1]))
        self.hold_until(0.41)
        mark = line_highlight(code, 3)
        playing = Text('self.wait(): no animation playing', font_size=24, color=SCAFFOLD).next_to(code, DOWN, buff=0.2)
        self.play(Create(mark), FadeIn(playing))
        self.hold_until(0.46)
        self.play(Transform(mark, line_highlight(code, 4)))
        fast.clear_updaters()
        stopped = Text('stopped', font_size=26, color=WARNING).move_to(rates[1])
        self.play(ReplacementTransform(rates[1], stopped))

        # [V6.4b] the same second at 15 and 60 frames per second
        self.hold_until(0.516)
        self.play(FadeOut(VGroup(slow, fast, card, code, mark, playing, rates[0], stopped)))
        s = ValueTracker(0)
        x0, x1 = -4.6, 2.4
        rows = []
        for y, fps, name in ((1.5, 15, 'ManimOnline preview · 15 fps'), (-1.1, 60, 'finished video · 60 fps')):
            axis = Line([x0, y, 0], [x1, y, 0], color=GREY_B)
            ticks = VGroup(*[Line([x0 + (x1 - x0) * i / fps, y - 0.14 * (15 / fps) ** 0.3, 0],
                                  [x0 + (x1 - x0) * i / fps, y + 0.14 * (15 / fps) ** 0.3, 0], color=GREY_B, stroke_width=2)
                             for i in range(fps + 1)])
            ticks.add_updater(lambda m, fps=fps: [t.set_color(FOCUS if i <= s.get_value() * fps + 1e-6 else GREY_B)
                                                  for i, t in enumerate(m)])
            title = Text(name, font_size=26).next_to([x0, y, 0], UP, buff=0.35, aligned_edge=LEFT)
            spot = np.array([5.0, y, 0])
            turned = always_redraw(lambda fps=fps, spot=spot: wheel(BLUE, 0.75).rotate(
                -math.floor(s.get_value() * fps + 1e-6) / fps * PI / 2, about_point=ORIGIN).shift(spot))
            rows.append(VGroup(axis, ticks, title, turned))
        ends = VGroup(*[Text(w, font_size=20, color=SCAFFOLD).next_to([x, -2.0, 0], DOWN, buff=0.1)
                        for x, w in ((x0, '0 s'), (x1, '1 s'))])
        self.play(FadeIn(rows[0][0:2]), FadeIn(rows[1][0:2]), FadeIn(rows[0][3]), FadeIn(rows[1][3]), FadeIn(ends))
        self.hold_until(0.627)
        self.play(FadeIn(rows[0][2]))
        self.hold_until(0.671)
        self.play(FadeIn(rows[1][2]))
        self.hold_until(0.708)
        gaps = VGroup()
        for row, fps, side, words in ((rows[0], 15, DOWN, 'dt = 1/15 s'), (rows[1], 60, DOWN, 'dt = 1/60 s')):
            ticks = row[1]
            span = Line(ticks[0].get_center(), ticks[1].get_center())
            brace = Brace(span, side, buff=0.2)
            gaps.add(VGroup(brace, Text(words, font_size=22, color=FOCUS).next_to(brace, side, buff=0.1, aligned_edge=LEFT)))
        self.play(FadeIn(gaps))
        slowed = Text('one second, slowed down ×6', font_size=22, color=SCAFFOLD).to_edge(UP, buff=0.3)
        playhead = always_redraw(lambda: Line([x0 + (x1 - x0) * s.get_value(), 2.1, 0], [x0 + (x1 - x0) * s.get_value(), -1.6, 0],
                                              color=FOCUS, stroke_width=3))
        self.play(FadeIn(slowed), FadeIn(playhead))
        self.play(s.animate.set_value(1), run_time=6, rate_func=linear)
        self.hold_until(0.826)
        same = VGroup(*[Text('¼ turn', font_size=24, color=AFTER).next_to(row[3], DOWN, buff=0.15) for row in rows])
        self.play(FadeIn(same), Indicate(rows[0][3], color=AFTER), Indicate(rows[1][3], color=AFTER))

        # [V6.4c] angle per frame = speed × dt
        self.hold_until(0.894)
        formula = MathTex(r"\text{angle per frame}", "=", r"\text{speed}", r"\times", "dt", font_size=40)
        formula.to_edge(DOWN, buff=0.75).shift(LEFT * 1)
        units = VGroup(*[Text(u, font_size=20, color=SCAFFOLD).next_to(formula[i], DOWN, buff=0.15)
                         for i, u in ((0, 'rad'), (2, 'rad / s'), (4, 's'))])
        formula[4].set_color(FOCUS)
        self.play(FadeOut(VGroup(ends, gaps)), Write(formula), FadeIn(units))
        self.finish()


class Segment_6_5(Segment):
    """A number you can animate."""
    EPISODE, SEGMENT = 6, '6.5'

    def construct(self):
        # [V6.5a] an invisible number in the corner
        x = ValueTracker(0)
        box = tracker_box(x).to_corner(UL, buff=0.45)
        faint = box.copy().set_opacity(0.4)
        self.play(FadeIn(faint), run_time=1.5)
        never = Text('holds one number, never drawn', font_size=24, color=SCAFFOLD).next_to(box, RIGHT, buff=0.4)
        self.play(FadeIn(never))
        self.hold_until(0.115)
        mobject = Text('but it is a mobject: you can animate it', font_size=24, color=FOCUS).move_to(never, aligned_edge=LEFT)
        self.remove(faint)
        self.add(box)
        self.play(Flash(box.get_center(), color=FOCUS, flash_radius=1.2), ReplacementTransform(never, mobject))

        # x.animate.set_value(7.5): episode 3's alpha, interpolation and rate function, on a bare number
        self.hold_until(0.23)
        line = code_text('self.play(x.animate.set_value(7.5), run_time=3)', 26).move_to(UP * 1.3)
        axes = Axes(x_range=[0, 3, 1], y_range=[0, 7.5, 2.5], x_length=5, y_length=2.6, tips=False,
                    axis_config={'color': GREY_B, 'stroke_width': 2}).move_to(DOWN * 1.3)
        axis_names = VGroup(Text('time (s)', font_size=20, color=SCAFFOLD).next_to(axes.x_axis, DOWN, buff=0.15),
                            Text('x', font_size=22, color=SCAFFOLD).next_to(axes.y_axis, LEFT, buff=0.15))
        graph = axes.plot(lambda u: 7.5 * smooth(u / 3), x_range=[0, 3], color=FOCUS)
        self.play(FadeOut(mobject), FadeIn(line), FadeIn(axes), FadeIn(axis_names))
        self.play(x.animate.set_value(7.5), Create(graph, rate_func=linear), run_time=3)
        ideas = VGroup(*[Text(w, font_size=22, color=GREY_A) for w in ('alpha: 0 → 1', 'rate function: smooth', 'interpolate: 0 → 7.5')])
        ideas.arrange(DOWN, aligned_edge=LEFT, buff=0.2).next_to(axes, RIGHT, buff=0.6)
        self.play(LaggedStart(*[FadeIn(i, shift=LEFT * 0.2) for i in ideas], lag_ratio=0.5), run_time=2)

        # [V6.5b] q06-03: other objects read the number in their updaters
        self.hold_until(0.43)
        self.play(FadeOut(VGroup(line, axes, axis_names, graph, ideas)), x.animate.set_value(0))
        number_line = NumberLine(x_range=[0, 10, 1], length=10, include_numbers=True).shift(DOWN * 0.5)
        pointer = Triangle(color=YELLOW, fill_opacity=1).scale(0.2).rotate(PI)
        pointer.add_updater(lambda m: m.next_to(number_line.n2p(x.get_value()), UP, buff=0.1))
        readout = DecimalNumber(0, num_decimal_places=2, font_size=48)
        readout.add_updater(lambda m: m.set_value(x.get_value()).next_to(pointer, UP))
        card = qr_card('q06-03')
        caption = snippet_line(TRACKER_SNIPPET, 13, 22).next_to(box, RIGHT, buff=0.5).align_to(box, UP)
        self.play(FadeIn(VGroup(number_line, pointer, readout)), FadeIn(card), FadeIn(caption))
        self.play(x.animate.set_value(7.5), run_time=3)

        def show(text):
            nonlocal caption
            new = code_text(text, 22).next_to(box, RIGHT, buff=0.5).align_to(box, UP)
            fit(new, 6.7 - new.get_left()[0])
            new.next_to(box, RIGHT, buff=0.5).align_to(box, UP)
            self.play(FadeOut(caption), FadeIn(new), run_time=0.4)
            caption = new

        # [V6.5c] wires from the tracker to the pointer and to the readout
        chips = VGroup(code_text('pointer: line.n2p(x.get_value())', 20, GREY_A),
                       code_text('readout: set_value(x.get_value())', 20, GREY_A)).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        chips.next_to(box, DOWN, buff=0.35, aligned_edge=LEFT)

        def wire(chip, target, approach):
            def build():
                start, end = chip.get_right() + RIGHT * 0.1, target()
                return CubicBezier(start, start + RIGHT * 1.2, end + approach * 1.1, end).set_stroke(FOCUS, 2.5)
            return always_redraw(build)

        self.hold_until(0.485)
        show(snippet_lines(TRACKER_SNIPPET, 9, 9).strip())
        to_pointer = wire(chips[0], lambda: pointer.get_left() + LEFT * 0.05, LEFT)
        self.play(FadeIn(chips[0]), Create(to_pointer))
        self.hold_until(0.55)
        self.play(x.animate.set_value(4), run_time=2)
        self.hold_until(0.636)
        show(snippet_lines(TRACKER_SNIPPET, 11, 11).strip())
        to_readout = wire(chips[1], lambda: readout.get_top() + UP * 0.05, UP)
        self.play(FadeIn(chips[1]), Create(to_readout))
        self.hold_until(0.69)
        show(snippet_lines(TRACKER_SNIPPET, 13, 13).strip())
        self.play(x.animate.set_value(7.5), run_time=3)

        # [V6.5d] back to 2, then increment_value(5) to 7
        self.hold_until(0.758)
        show(snippet_lines(TRACKER_SNIPPET, 14, 14).strip())
        self.play(x.animate.set_value(2), run_time=2)
        show(snippet_lines(TRACKER_SNIPPET, 15, 15).strip())
        self.play(x.animate.increment_value(5), run_time=2)

        # the pattern
        self.hold_until(0.842)
        steps = VGroup(*[Text(w, font_size=26) for w in ('decide which numbers matter', 'store them in ValueTrackers',
                                                         'let everything else follow')])
        steps.arrange(RIGHT, buff=0.8).to_edge(DOWN, buff=0.7)
        fit(steps, 12.6)
        arrows = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.12, color=GREY_B, stroke_width=3,
                                max_tip_length_to_length_ratio=0.3) for a, b in zip(steps, steps[1:])])
        self.play(FadeOut(card))
        self.play(LaggedStart(*[FadeIn(m) for m in (steps[0], arrows[0], steps[1], arrows[1], steps[2])], lag_ratio=0.4), run_time=3)
        self.finish()


class Segment_6_6(Segment):
    """Redrawing from scratch."""
    EPISODE, SEGMENT = 6, '6.6'

    def construct(self):
        # [V6.6a] q06-04: the triangle is rebuilt from the angle every frame
        radius = 2.5
        angle = ValueTracker(0.3)

        def tip():
            a = angle.get_value()
            return radius * (math.cos(a) * RIGHT + math.sin(a) * UP)

        def foot():
            return radius * math.cos(angle.get_value()) * RIGHT

        figure = VGroup(Circle(radius=radius, color=GREY), Line(LEFT * 3, RIGHT * 3, color=GREY))
        triangle = always_redraw(lambda: Polygon(ORIGIN, foot(), tip(), color=YELLOW, fill_opacity=0.3))
        cos_label = always_redraw(lambda: MathTex(r"\cos\theta", color=BLUE).next_to(Line(ORIGIN, foot()), DOWN))
        sin_label = always_redraw(lambda: MathTex(r"\sin\theta", color=GREEN).next_to(Line(foot(), tip()), RIGHT))
        card = qr_card('q06-04')
        self.add(figure, triangle, cos_label, sin_label)
        self.play(FadeIn(card), run_time=0.6)
        self.play(angle.animate.set_value(1.3), run_time=3)

        # no shift or scale turns one of these triangles into another
        self.hold_until(0.09)
        ghosts = VGroup(*[DashedVMobject(corner_triangle(a, fill_opacity=0), num_dashes=40).set_stroke(GREY_A, 2)
                          for a in (0.35, 0.8, 1.25)])
        why = Text('no single shift or scale does this', font_size=26, color=SCAFFOLD).to_corner(DL, buff=0.5)
        self.play(LaggedStart(*[Create(g) for g in ghosts], lag_ratio=0.4), FadeIn(why), run_time=2)
        self.wait(2)
        self.play(FadeOut(ghosts), FadeOut(why))

        # always_redraw takes a function that builds the object from scratch
        self.hold_until(0.272)
        code = code_panel(snippet_lines(REDRAW_SNIPPET, 19, 20), font_size=20, line_numbers=False)
        fit(code, 13).to_edge(UP, buff=0.2)
        self.play(FadeIn(code))
        self.hold_until(0.353)
        mark = line_highlight(code, 0)
        self.play(Create(mark))
        self.play(angle.animate.set_value(0.6), run_time=2)
        self.hold_until(0.456)
        self.play(Transform(mark, line_highlight(code, 1)))
        self.play(angle.animate.set_value(1.05), run_time=2)

        # [V6.6b] a film strip: a brand new triangle each frame, the old one thrown away
        self.hold_until(0.5)
        self.remove(triangle, cos_label, sin_label)
        self.play(FadeOut(VGroup(figure, code, mark, card, triangle.copy().clear_updaters(),
                                 cos_label.copy().clear_updaters(), sin_label.copy().clear_updaters())))
        strip = film_strip(3, 2.6, 1.7, 0.6).shift(UP * 1.9)
        band, holes, windows = strip
        can = trash_can().move_to(RIGHT * 5 + DOWN * 2)
        bin_label = Text('thrown away', font_size=20, color=SCAFFOLD).next_to(can, DOWN, buff=0.15)
        caption = Text('always_redraw: build a new one every frame', font_size=30).to_edge(DOWN, buff=0.45)
        caption.shift(LEFT * 1)
        self.play(FadeIn(strip), FadeIn(can), FadeIn(bin_label), FadeIn(caption))
        old, frames = None, VGroup()
        for k, a in enumerate((0.5, 0.85, 1.2)):
            new = corner_triangle(a, 1.6).move_to(DOWN * 1.1)
            framed = corner_triangle(a, 1.1).move_to(windows[k])
            frames.add(framed)
            built = Text(f'new Polygon #{k + 1}', font_size=20, color=FOCUS).next_to(new, LEFT, buff=0.4)
            anims = [Create(new), FadeIn(built), windows[k].animate.set_stroke(FOCUS, 3), FadeIn(framed)]
            if old is not None:
                anims += [old[0].animate.scale(0.2).move_to(can.get_center() + UP * 0.15).set_opacity(0), FadeOut(old[1]),
                          windows[k - 1].animate.set_stroke(GREY_B, 2)]
            self.play(*anims, run_time=1.2)
            self.wait(0.9)
            old = (new, built)
        self.play(old[0].animate.scale(0.2).move_to(can.get_center() + UP * 0.15).set_opacity(0), FadeOut(old[1]),
                  windows[2].animate.set_stroke(GREY_B, 2))

        # flexible, but it builds new objects every frame
        self.hold_until(0.662)
        self.play(FadeOut(VGroup(strip, frames, can, bin_label, caption)))
        tags = VGroup(Text('the most flexible', font_size=34, color=AFTER), Text('the most expensive', font_size=34, color=WARNING))
        tags.arrange(RIGHT, buff=1.2).to_edge(UP, buff=0.8)
        self.play(FadeIn(tags[0]))
        self.play(FadeIn(tags[1]))
        self.hold_until(0.809)
        few = VGroup(*[corner_triangle(a, 0.5) for a in (0.5, 0.9, 1.3)]).arrange(RIGHT, buff=0.25)
        few_sum = Text('3 shapes × 60 frames a second = 180 new objects a second', font_size=26)
        few_row = VGroup(few, few_sum, check_mark(0.4)).arrange(RIGHT, buff=0.5).move_to(UP * 0.6)
        fit(few_row, 13)
        self.play(FadeIn(few_row))
        self.hold_until(0.882)
        many = VGroup(*[corner_triangle(0.4 + (i % 7) * 0.15, 0.16, stroke_width=1) for i in range(60)])
        many.arrange_in_grid(rows=4, buff=0.05)
        many_sum = Text('300 shapes × 60 = 18,000 new objects a second', font_size=26, color=WARNING)
        many_row = VGroup(many, many_sum).arrange(RIGHT, buff=0.5).move_to(DOWN * 1.1)
        fit(many_row, 13)
        instead = Text('→ an updater that adjusts them instead', font_size=26, color=AFTER).next_to(many_row, DOWN, buff=0.5)
        self.play(FadeIn(many_row))
        self.play(FadeIn(instead))
        self.finish()


class Segment_6_7(Segment):
    """Putting it together."""
    EPISODE, SEGMENT = 6, '6.7'

    def construct(self):
        # [V6.7a] the q06-05 code beside its animation
        code = code_panel(snippet_lines(SINE_SNIPPET, 8, 27), font_size=18)
        code.scale_to_fit_width(8.6)
        code.to_corner(DL, buff=0.3)
        t = ValueTracker(0)
        scene = Unroll(t, scale=0.6, shift=[2.9 - 0.6 * 0.25, 2.25, 0])
        parts = scene.parts()
        box = tracker_box(t, 't', font_size=30).move_to([3.4, 0.0, 0])
        card = qr_card('q06-05')
        self.add(scene.static(), *scene.drawn(parts))
        self.play(FadeIn(code), FadeIn(card), FadeIn(box))

        # one tracker, t
        self.hold_until(0.052)
        mark = line_highlight(code, 0)
        self.play(Create(mark), Indicate(box, color=FOCUS, scale_factor=1.1))

        # two little functions turn t into positions
        self.hold_until(0.121)
        self.play(Transform(mark, lines_box(code, 4, 10)))
        self.play(t.animate.set_value(1.2), run_time=2)
        positions = VGroup(*[Circle(radius=0.15).move_to(p).set_stroke(WHITE, 4) for p in (scene.on_circle(), scene.on_wave())])
        self.play(LaggedStart(*[ShowPassingFlash(p, time_width=0.6) for p in positions], lag_ratio=0.4), run_time=1.4)

        # the radius, the link and both dots are always redrawn from those positions
        for key, row, fraction in (('radius', 13, 0.25), ('link', 14, 0.28), ('dot', 16, 0.31), ('wave dot', 17, 0.34)):
            self.hold_until(fraction)
            if key in ('dot', 'wave dot'):
                where = scene.on_circle() if key == 'dot' else scene.on_wave()
                glow = Circle(radius=0.15).move_to(where).set_stroke(WHITE, 5)
            else:
                glow = flash_copy(parts[key], width=7)
            self.play(Transform(mark, line_highlight(code, row)), ShowPassingFlash(glow, time_width=0.6), run_time=0.8)

        # [V6.7b] the wave is a traced path: drawn by the moving point
        self.hold_until(0.371)
        self.play(Transform(mark, line_highlight(code, 15)))
        self.play(t.animate.set_value(TAU), run_time=6, rate_func=linear)
        drawn = Text('drawn by the moving point', font_size=22, color=SCAFFOLD).next_to(box, UP, buff=0.2)
        self.hold_until(0.612)
        self.play(FadeIn(drawn))

        # [V6.7c] one line drives every part
        self.hold_until(0.733)
        self.play(Transform(mark, line_highlight(code, 19)), FadeOut(drawn), FadeOut(card), FadeOut(parts['trail']),
                  t.animate.set_value(0), run_time=1)
        self.remove(parts['trail'])
        parts['trail'] = TracedPath(scene.on_wave, stroke_color=YELLOW, stroke_width=4)
        self.add(parts['trail'])
        self.bring_to_front(parts['dot'], parts['wave dot'])
        hub = mark.get_right() + RIGHT * 0.15
        targets = [lambda: (scene.center + scene.on_circle()) / 2, scene.on_circle,
                   lambda: (scene.on_circle() + scene.on_wave()) / 2, scene.on_wave,
                   lambda: scene.on_wave() + LEFT * 0.25 * scene.s]
        links = VGroup(*[always_redraw(lambda f=f: Line(hub, f(), color=FOCUS, stroke_width=1.5, stroke_opacity=0.7))
                         for f in targets])
        self.play(Create(links), run_time=0.8)
        self.play(t.animate.set_value(TAU), run_time=6, rate_func=linear)
        five = Text('one number changes; five things move', font_size=26, color=FOCUS).to_corner(DR, buff=0.5)
        self.hold_until(0.93)
        self.play(FadeIn(five))
        self.finish()


class Segment_6_8(Segment):
    """Two surprises worth knowing."""
    EPISODE, SEGMENT = 6, '6.8'

    def construct(self):
        # [V6.8a] updaters keep running during animations, on the start and end copies too
        heading = Text('1 · updaters keep running during animations', font_size=30).to_edge(UP, buff=0.4)
        w = spin(wheel(BLUE), 0.25).shift(LEFT * 2 + DOWN * 0.4)
        cog = spin(gear(0.3, color=FOCUS), 0.4).next_to(w, UL, buff=0.1)
        cog.add_updater(lambda m: m.move_to(w.get_center() + UL * 1.25), call_updater=False)
        self.play(FadeIn(w), FadeIn(cog))
        self.hold_until(0.047)
        self.play(FadeIn(heading))
        self.hold_until(0.109)
        ghosts = VGroup(spin(wheel(GREY_B), 0.25).shift(LEFT * 2 + DOWN * 0.4), spin(wheel(GREY_B), 0.25).shift(RIGHT * 2 + DOWN * 0.4))
        for g in ghosts:
            g.set_stroke(opacity=0.35)
        names = VGroup(Text('start copy', font_size=22, color=SCAFFOLD).next_to(ghosts[0], DOWN, buff=0.25),
                       Text('end copy', font_size=22, color=SCAFFOLD).next_to(ghosts[1], DOWN, buff=0.25))
        self.play(FadeIn(ghosts[1]), FadeIn(names))
        self.add(ghosts[0])
        self.hold_until(0.194)
        line = code_text('self.play(wheel.animate.shift(RIGHT * 4), run_time=3)', 24).next_to(heading, DOWN, buff=0.3)
        self.play(FadeIn(line))
        self.play(w.animate.shift(RIGHT * 4), run_time=3)
        still = Text('it kept spinning while it glided', font_size=24, color=AFTER).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(still))

        # [V6.8b] an updater that decides where something is beats an animation that moves it
        self.hold_until(0.287)
        for g in ghosts:
            g.clear_updaters()
        self.play(FadeOut(VGroup(w, cog, ghosts, names, line, still)))
        dot = Dot(LEFT * 1, color=YELLOW, radius=0.12)
        label = Text('I follow', font_size=30).add_updater(lambda m: m.next_to(dot, UP))
        self.play(FadeIn(dot), FadeIn(label))
        line = code_text('self.play(label.animate.shift(DOWN * 2))', 24).next_to(heading, DOWN, buff=0.3)
        wanted = DashedVMobject(SurroundingRectangle(label.copy().shift(DOWN * 2), buff=0.08), num_dashes=30).set_stroke(GREY_B, 2)
        self.play(FadeIn(line), Create(wanted))
        self.play(label.animate.shift(DOWN * 2), run_time=1.5)
        miss = cross_mark(0.25).next_to(label, RIGHT, buff=0.5)
        put_back = Text("the updater puts it back, every frame", font_size=24, color=WARNING).to_edge(DOWN, buff=0.6)
        self.play(Create(miss), FadeIn(put_back))
        self.hold_until(0.45)
        colour = code_text('self.play(label.animate.set_color(RED))', 24).next_to(heading, DOWN, buff=0.3)
        self.play(FadeOut(line), FadeIn(colour), FadeOut(wanted), FadeOut(put_back))
        self.play(label.animate.set_color(RED))
        ok = check_mark(0.4).move_to(miss)
        never = Text('the updater never touches colour', font_size=24, color=AFTER).to_edge(DOWN, buff=0.6)
        self.play(ReplacementTransform(miss, ok), FadeIn(never))
        self.hold_until(0.527)
        lead = code_text('self.play(dot.animate.shift(RIGHT * 3))', 24).next_to(heading, DOWN, buff=0.3)
        self.play(FadeOut(colour), FadeIn(lead), FadeOut(ok), FadeOut(never))
        self.play(dot.animate.shift(RIGHT * 3), run_time=1.5)
        advice = Text('to move a follower, move what it follows', font_size=24, color=AFTER).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(advice))

        # [V6.8c] update order: A reads B before B's updater has run, so A lags a frame behind
        self.hold_until(0.628)
        label.clear_updaters()
        second = Text('2 · updaters run in order', font_size=30).to_edge(UP, buff=0.4)
        self.play(FadeOut(VGroup(dot, label, lead, advice)), ReplacementTransform(heading, second))
        order = VGroup(Text('A: move onto B', font_size=24, color=FOCUS), Text('B: step right', font_size=24, color=BLUE),
                       Text('capture the frame', font_size=24, color=GREY_A))
        numbers = VGroup(*[Text(f'{i}.', font_size=24, color=SCAFFOLD) for i in (1, 2, 3)])
        steps = VGroup(*[VGroup(n, o).arrange(RIGHT, buff=0.15) for n, o in zip(numbers, order)])
        steps.arrange(DOWN, aligned_edge=LEFT, buff=0.25).to_edge(LEFT, buff=0.8).shift(UP * 1.2)
        track = NumberLine(x_range=[0, 6, 1], length=7.2, include_ticks=True, color=GREY_D).shift(RIGHT * 2.4 + DOWN * 1.2)
        b = Dot(track.n2p(1), radius=0.12, color=BLUE)
        a = Circle(radius=0.3, color=FOCUS, stroke_width=4).move_to(track.n2p(1))
        names = VGroup(Text('B', font_size=24, color=BLUE).add_updater(lambda m: m.next_to(b, DOWN, buff=0.35)),
                       Text('A', font_size=24, color=FOCUS).add_updater(lambda m: m.next_to(a, UP, buff=0.12)))
        self.play(FadeIn(steps), FadeIn(track), FadeIn(b), FadeIn(a), FadeIn(names))
        self.hold_until(0.667)
        pointer = Arrow(LEFT * 0.6, ORIGIN, buff=0, color=FOCUS, stroke_width=5, max_tip_length_to_length_ratio=0.4)
        for frame in (2, 3):
            self.play(pointer.animate.next_to(steps[0], LEFT, buff=0.15) if frame == 3 else
                      FadeIn(pointer.next_to(steps[0], LEFT, buff=0.15)), run_time=0.4)
            self.play(a.animate.move_to(b), run_time=0.6)
            self.play(pointer.animate.next_to(steps[1], LEFT, buff=0.15), run_time=0.4)
            self.play(b.animate.move_to(track.n2p(frame)), run_time=0.6)
            self.play(pointer.animate.next_to(steps[2], LEFT, buff=0.15), run_time=0.4)
            shot = SurroundingRectangle(VGroup(track, a, b), buff=0.35, color=WHITE).set_fill(WHITE, 0.25)
            self.play(FadeIn(shot, rate_func=there_and_back), run_time=0.5)
            self.remove(shot)
            self.wait(0.6)
        behind = Text('A is one frame behind', font_size=26, color=WARNING).next_to(track, UP, buff=1.1).shift(RIGHT * 0.5)
        gap = DashedLine(a.get_center(), b.get_center(), color=WARNING).shift(DOWN * 0.55)
        self.play(FadeIn(behind), Create(gap))
        matters = Text('order matters', font_size=24, color=SCAFFOLD).next_to(steps, DOWN, buff=0.5, aligned_edge=LEFT)
        self.play(FadeIn(matters))

        # the cure: both read the same value tracker
        self.hold_until(0.876)
        self.play(FadeOut(VGroup(pointer, behind, gap, steps, matters)))
        x = ValueTracker(3)
        box = tracker_box(x).to_edge(LEFT, buff=0.8).shift(UP * 1.2)
        b.add_updater(lambda m: m.move_to(track.n2p(x.get_value())))
        a.add_updater(lambda m: m.move_to(track.n2p(x.get_value())))
        wires = VGroup(*[always_redraw(lambda m=m, s=s: CubicBezier(box.get_right(), box.get_right() + RIGHT * 1.5,
                                                                    m.get_center() + s * 1.2, m.get_center() + s * 0.32)
                                       .set_stroke(FOCUS, 2)) for m, s in ((a, UP), (b, DOWN))])
        self.play(FadeIn(box), Create(wires))
        self.play(x.animate.set_value(5.5), run_time=2.5)
        both = Text('both read x: no lag', font_size=26, color=AFTER).next_to(track, DOWN, buff=0.9)
        self.play(FadeIn(both))
        self.finish()


class Segment_6_9(Segment):
    """Choosing the right tool."""
    EPISODE, SEGMENT = 6, '6.9'

    def construct(self):
        # [V6.9a] a decision tree, one branch per tool
        root = VGroup(Text('Something should', font_size=26), Text('change over time', font_size=26)).arrange(DOWN, buff=0.1)
        root_box = SurroundingRectangle(root, color=GREY_A, buff=0.25, corner_radius=0.12)
        root = VGroup(root_box, root).move_to([-5.6, 0.4, 0])
        dt_tool = VGroup(code_text('add_updater', 24, BLUE), Text('with', font_size=22, color=GREY_A),
                         code_text('dt', 24, FOCUS)).arrange(RIGHT, buff=0.15)
        play_tool = code_text('self.play(...)', 24, AFTER)
        branches = [
            ('It follows another object', code_text('add_updater', 24, BLUE), gear(0.28)),
            ('It changes at a steady rate by itself', dt_tool, stopwatch(0.28)),
            ('Several things depend on one quantity', code_text('ValueTracker', 24, FOCUS), tracker_icon().scale(0.7)),
            ('Its shape must be rebuilt from scratch', code_text('always_redraw', 24, AFTER), recycle_icon()),
            ('It should leave a trail', code_text('TracedPath', 24, PURPLE_B), pen_icon()),
            ('It changes once, at a known moment', play_tool, check_mark(0.4)),
        ]
        rows = VGroup()
        for (words, tool, icon), y in zip(branches, (2.95, 1.85, 0.75, -0.35, -1.45, -2.85)):
            condition = Text(words, font_size=22).move_to([-3.75, y, 0], aligned_edge=LEFT)
            tool.move_to([2.4, y, 0], aligned_edge=LEFT)
            icon.move_to([6.45, y, 0])
            branch = Line(root_box.get_right(), condition.get_left() + LEFT * 0.15, color=GREY_B, stroke_width=2)
            arrow = Arrow(condition.get_right(), tool.get_left(), buff=0.2, color=GREY_B, stroke_width=2,
                          max_tip_length_to_length_ratio=0.15)
            rows.add(VGroup(branch, condition, arrow, tool, icon))
        self.play(FadeIn(root))
        for row, fraction in zip(rows[:5], (0.06, 0.14, 0.225, 0.33, 0.435)):
            self.hold_until(fraction)
            self.play(Create(row[0]), FadeIn(row[1]), run_time=0.8)
            self.play(GrowArrow(row[2]), FadeIn(row[3]), FadeIn(row[4], scale=0.6), run_time=0.8)

        # [V6.9b] always_redraw is an updater that calls become every frame
        self.hold_until(0.505)
        redraw = rows[3][3]
        home = redraw.get_center()
        self.play(FadeOut(VGroup(root, *rows[:3], rows[4], rows[3][0:3], rows[3][4])),
                  redraw.animate.scale(1.2).move_to(UP * 3.2))
        source = ('triangle = Polygon(ORIGIN, foot(), tip())\n'
                  'triangle.add_updater(lambda m: m.become(Polygon(ORIGIN, foot(), tip())))   # what always_redraw does')
        code = fit(code_panel(source, font_size=20, line_numbers=False), 12.5).next_to(redraw, DOWN, buff=0.35)
        self.play(FadeIn(code))
        angle = ValueTracker(0.5)
        live = corner_triangle(0.5, 1.6).shift(LEFT * 3.4 + DOWN * 2.2)
        tag = VGroup(sticky_note('t'), Text('triangle', font_size=22, color=GREY_A))
        tag[1].next_to(tag[0], RIGHT, buff=0.12)
        tag.add_updater(lambda m: m.next_to(live, LEFT, buff=0.3))
        factory = Text('built fresh each frame', font_size=22, color=SCAFFOLD).move_to([3.4, 0.3, 0])
        become = Text('become', font_size=24, color=FOCUS).move_to([0, -1.1, 0])
        arrow = Arrow(RIGHT * 1.6 + DOWN * 1.5, LEFT * 1.6 + DOWN * 1.5, color=FOCUS, stroke_width=4)
        self.play(FadeIn(live), FadeIn(tag), FadeIn(factory), GrowArrow(arrow), FadeIn(become))
        for a in (0.85, 1.2, 0.7):
            fresh = DashedVMobject(corner_triangle(a, 1.6, fill_opacity=0), num_dashes=40).set_stroke(FOCUS, 2)
            fresh.move_to([3.4, -1.6, 0])
            self.play(Create(fresh), run_time=0.6)
            target = corner_triangle(a, 1.6)
            target.shift(live.get_corner(DL) - target.get_corner(DL))
            self.play(Indicate(arrow, color=WHITE, scale_factor=1.1), run_time=0.4)
            live.become(target)
            self.play(Flash(live.get_center(), color=FOCUS, flash_radius=0.9), FadeOut(fresh), run_time=0.6)
        self.hold_until(0.585)
        same = Text('same object, new shape: it stays in the scene and keeps its name', font_size=24, color=AFTER)
        same.to_edge(DOWN, buff=0.3)
        self.play(FadeIn(same), Indicate(tag, color=FOCUS))
        self.hold_until(0.725)
        mark = line_highlight(code, 1)
        yourself = Text('write it yourself for a variation', font_size=22, color=FOCUS).next_to(code, DOWN, buff=0.2)
        self.play(Create(mark), FadeIn(yourself))

        # [V6.9c] the simplest option: an ordinary animation
        self.hold_until(0.78)
        tag.clear_updaters()
        self.play(FadeOut(VGroup(code, mark, yourself, live, tag, factory, become, arrow, same)),
                  redraw.animate.scale(1 / 1.2).move_to(home))
        self.play(FadeIn(VGroup(root, *rows[:3], rows[3][0:3], rows[3][4], rows[4])))
        self.play(Create(rows[5][0]), FadeIn(rows[5][1]), run_time=0.8)
        self.play(GrowArrow(rows[5][2]), FadeIn(rows[5][3]), Create(rows[5][4]), run_time=0.8)
        simplest = Text('the simplest option', font_size=22, color=AFTER).next_to(rows[5][3], DOWN, buff=0.12, aligned_edge=LEFT)
        glow = SurroundingRectangle(VGroup(rows[5][1], rows[5][4]), color=AFTER, buff=0.15, corner_radius=0.1)
        self.play(Create(glow), FadeIn(simplest))
        self.hold_until(0.95)
        always = SurroundingRectangle(VGroup(*[r[1:4] for r in rows[:5]]), color=GREY_B, buff=0.12, corner_radius=0.1)
        hold = Text('relationships that hold all the time', font_size=20, color=SCAFFOLD)
        hold.next_to(always, UP, buff=0.05).align_to(always, RIGHT)
        self.play(Create(always), FadeIn(hold))
        self.finish()


class Segment_6_10(Segment):
    """Recap."""
    EPISODE, SEGMENT = 6, '6.10'

    def construct(self):
        # [V6.10a] one tile per tool, on its sentence of the recap
        items = [
            (gear(0.45, color=BLUE), 'add_updater', 'relationships, every frame'),
            (stopwatch(0.45), 'dt', 'change at any frame rate'),
            (tracker_icon().scale(1.1), 'ValueTracker', 'the numbers a scene is about'),
            (recycle_icon(0.45), 'always_redraw', 'rebuilt from those numbers'),
            (pen_icon().scale(1.3), 'TracedPath', 'the history of a moving point'),
        ]
        tiles = VGroup()
        for icon, name, words in items:
            title = code_text(name, 26, GREY_A).next_to(icon, DOWN, buff=0.3)
            caption = Text(words, font_size=22, color=SCAFFOLD).next_to(title, DOWN, buff=0.15)
            tiles.add(VGroup(icon, title, caption))
        for k, tile in enumerate(tiles):
            tile.move_to([(-4.8, 0, 4.8)[k % 3] + (2.4 if k >= 3 else 0), (1.6, -1.8)[k // 3], 0])
        for tile, fraction in zip(tiles, (0.0, 0.086, 0.235, 0.457, 0.58)):
            self.hold_until(fraction)
            self.play(FadeIn(tile, shift=UP * 0.2), run_time=0.8)
        self.hold_until(0.62)

        # [V6.10b] the QR wall, 10 seconds
        wall = qr_wall([f'q06-0{i}' for i in range(1, 6)])
        heading = Text('Episode 6 · scan to open each scene', font_size=26, color=SCAFFOLD).to_corner(UL, buff=0.3)
        self.play(FadeOut(tiles), FadeIn(wall), FadeIn(heading))
        self.wait(10)

        # [V6.10c] teaser: Riemann rectangles narrowing under a curve (episode 7)
        self.play(FadeOut(VGroup(wall, heading)))
        axes = Axes(x_range=[0, 4, 1], y_range=[0, 4, 1], x_length=7, y_length=4, tips=False,
                    axis_config={'color': GREY_B}).shift(UP * 0.3)
        curve = axes.plot(lambda u: 0.2 * u ** 2 + 0.4, x_range=[0, 4], color=FOCUS)
        rects = axes.get_riemann_rectangles(curve, x_range=[0, 4], dx=0.5, color=[BLUE, GREEN], fill_opacity=0.6)
        self.play(Create(axes), Create(curve), run_time=1)
        self.play(FadeIn(rects))
        for dx in (0.25, 0.1):
            self.play(Transform(rects, axes.get_riemann_rectangles(curve, x_range=[0, 4], dx=dx, color=[BLUE, GREEN],
                                                                   fill_opacity=0.6)), run_time=0.9)
        nxt = Text('Next: Graphs, areas and slopes', font_size=34).to_edge(DOWN, buff=0.5)
        self.play(Write(nxt))
        self.wait(1.5)
        self.finish()
