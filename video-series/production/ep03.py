"""Episode 3 · Animations: the verbs. One Scene per script segment.

    python3 video-series/production/render.py 3 [-ql] [segment ...]

Shot ids in comments ([V3.2c] ...) refer to episodes/03-animations-the-verbs.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403

RATES = [('linear', linear, GREY_A), ('smooth', smooth, OBJECT), ('rush_into', rush_into, AFTER),
         ('rush_from', rush_from, PURPLE_B), ('there_and_back', there_and_back, WARNING)]


def halfway(rate=smooth):
    """A rate function that stops at alpha = 0.5, for freezing an animation midway."""
    return lambda t: rate(t) / 2


def from_halfway(rate=smooth):
    return lambda t: 0.5 + rate(t) / 2


class Segment_3_1(Segment):
    """Cold open: two rotations."""
    EPISODE, SEGMENT = 3, '3.1'

    def construct(self):
        # [V3.1a] the same quarter turn, twice
        left = Square(2.6, color=OBJECT).shift(LEFT * 3.2)
        right = Square(2.6, color=FOCUS).shift(RIGHT * 3.2)
        self.play(FadeIn(left), FadeIn(right))
        self.play(left.animate.rotate(PI / 2), Rotate(right, PI / 2), run_time=3)
        self.wait(0.8)

        # watch the blue one again: it shrinks on the way
        outline = DashedVMobject(left.copy().set_stroke(GREY_B, 2), num_dashes=40)
        again = Text('watch again', font_size=28, color=SCAFFOLD).next_to(left, UP, buff=0.5)
        self.play(FadeIn(outline), FadeIn(again))
        target = left.copy().rotate(PI / 2)
        self.play(Transform(left, target, rate_func=halfway()), Rotate(right, PI / 4, rate_func=smooth), run_time=2)
        shrink = Text('smaller', font_size=30, color=WARNING).next_to(outline, DOWN, buff=0.3)
        self.play(FadeIn(shrink, shift=UP * 0.2))
        self.wait(0.6)
        self.play(Transform(left, target, rate_func=smooth), Rotate(right, PI / 4, rate_func=smooth), run_time=2)
        self.play(FadeOut(shrink), FadeOut(again))
        self.hold_until(0.34)

        # [V3.1b] half a turn: yellow spins, blue collapses to a point
        target = left.copy().rotate(PI)
        self.play(Transform(left, target, rate_func=halfway()), Rotate(right, PI / 2, rate_func=smooth), run_time=2.5)
        centre = Dot(left.get_center(), color=WARNING, radius=0.07)
        same = Text('Same instruction?', font_size=44).to_edge(UP, buff=0.6)
        self.play(FadeIn(centre, scale=3), Write(same))
        self.hold_until(0.66)

        self.play(FadeOut(centre), Transform(left, target, rate_func=smooth), Rotate(right, PI / 2, rate_func=smooth),
                  run_time=2.5)
        journey = Text('same ending, different journey', font_size=30, color=SCAFFOLD).to_edge(DOWN, buff=0.7)
        self.play(FadeOut(outline), FadeIn(journey))
        self.finish()


class Segment_3_2(Segment):
    """What play really does."""
    EPISODE, SEGMENT = 3, '3.2'

    def construct(self):
        alpha = ValueTracker(0)

        # [V3.2a] start, end, and a slider called alpha
        start, end = LEFT * 4 + UP * 1.6, RIGHT * 4 + UP * 1.6
        ghost = Dot(end, color=AFTER, radius=0.14).set_opacity(0.35)
        start_mark = Dot(start, color=OBJECT, radius=0.06)
        labels = VGroup(Text('start', font_size=28, color=OBJECT).next_to(start, UP, buff=0.35),
                        Text('end', font_size=28, color=AFTER).next_to(end, UP, buff=0.35))
        track = DashedLine(start, end, color=GREY_D)
        dot = always_redraw(lambda: Dot(start + alpha.get_value() * (end - start), color=FOCUS, radius=0.14))

        slider = NumberLine(x_range=[0, 1, 0.1], length=8, include_tip=False, color=GREY_B).shift(DOWN * 0.6)
        ends = VGroup(MathTex('0', font_size=34).next_to(slider.n2p(0), DOWN), MathTex('1', font_size=34).next_to(slider.n2p(1), DOWN))
        name = MathTex(r'\alpha', font_size=48, color=FOCUS).next_to(slider, LEFT, buff=0.5)
        knob = always_redraw(lambda: Triangle(color=FOCUS, fill_opacity=1).scale(0.14).rotate(PI)
                             .next_to(slider.n2p(alpha.get_value()), UP, buff=0.05))
        readout = always_redraw(lambda: DecimalNumber(alpha.get_value(), num_decimal_places=2, font_size=30, color=FOCUS)
                                .next_to(knob, UP, buff=0.1))
        self.play(FadeIn(start_mark), FadeIn(ghost), FadeIn(labels), Create(track))
        self.play(Create(slider), FadeIn(ends), Write(name), FadeIn(knob), FadeIn(readout), FadeIn(dot))
        self.hold_until(0.17)

        # alpha 0 is the start, 1 is the end, anything between is that far along
        self.play(alpha.animate.set_value(1), run_time=3)
        self.wait(0.5)
        self.play(alpha.animate.set_value(0), run_time=2)
        self.play(alpha.animate.set_value(0.3), run_time=1.5)
        self.play(alpha.animate.set_value(0.75), run_time=1.5)
        self.hold_until(0.32)

        # [V3.2b] linear interpolation, coloured to match
        formula = MathTex(r'\text{point}', '=', r'\text{start}', '+', r'\alpha', r'\,(', r'\text{end}', '-',
                          r'\text{start}', ')', font_size=46).shift(DOWN * 2.2)
        for index, color in ((0, FOCUS), (2, OBJECT), (4, FOCUS), (6, AFTER), (8, OBJECT)):
            formula[index].set_color(color)
        self.play(Write(formula), run_time=2)
        self.play(alpha.animate.set_value(0.5), run_time=1.5)
        middle = Text('exactly the middle', font_size=26, color=FOCUS).next_to(dot, DOWN, buff=0.35)
        self.play(FadeIn(middle, shift=UP * 0.2))
        lerp = VGroup(Text('linear interpolation', font_size=30), Text('"lerp"', font_size=30, color=FOCUS))
        lerp.arrange(RIGHT, buff=0.4).next_to(formula, DOWN, buff=0.4)
        self.play(FadeIn(lerp))
        self.hold_until(0.54)

        # [V3.2c] a shape is many points, each with its own little track
        self.play(FadeOut(VGroup(start_mark, ghost, labels, track, dot, middle, formula, lerp)))
        self.remove(dot)
        alpha.set_value(0)
        centre = UP * 1.95
        count, tracks_shown = 64, 16
        square = Square(2.9).move_to(centre)
        circle = Circle(radius=1.65).rotate(PI / 4).move_to(centre)
        a_points = [square.point_from_proportion(k / count) for k in range(count)]
        b_points = [circle.point_from_proportion(k / count) for k in range(count)]

        def shape():
            t = alpha.get_value()
            points = [a + t * (b - a) for a, b in zip(a_points, b_points)]
            return VMobject(color=interpolate_color(OBJECT, AFTER, t), stroke_width=4).set_points_as_corners(points + points[:1])

        morph = always_redraw(shape)
        target = circle.copy().set_stroke(AFTER, 3, opacity=0.35)
        step = count // tracks_shown
        tracks = VGroup(*[DashedLine(a_points[k], b_points[k], color=GREY_A, stroke_width=3, dash_length=0.05)
                          for k in range(0, count, step) if np.linalg.norm(b_points[k] - a_points[k]) > 0.05])
        riders = always_redraw(lambda: VGroup(*[Dot(a_points[k] + alpha.get_value() * (b_points[k] - a_points[k]),
                                                    radius=0.05, color=FOCUS) for k in range(0, count, step)]))
        self.play(Create(morph), FadeIn(target))
        self.play(Create(tracks), FadeIn(riders), run_time=1.5)
        self.hold_until(0.66)
        self.play(alpha.animate.set_value(1), run_time=3)
        self.wait(0.5)
        self.play(alpha.animate.set_value(0), run_time=2)
        self.play(alpha.animate.set_value(0.5), run_time=1.5)
        same = Text('every point, the same alpha', font_size=28, color=FOCUS).shift(DOWN * 2.2)
        self.play(FadeIn(same))
        self.hold_until(0.8)

        # [V3.2d] alpha comes from the clock: fifteen snapshots in one second
        self.play(FadeOut(same), FadeOut(tracks), alpha.animate.set_value(0))
        clock = NumberLine(x_range=[0, 1, 1 / 15], length=8, include_tip=False, color=GREY_B,
                           tick_size=0.08).shift(DOWN * 2.3)
        clock_ends = VGroup(Text('0 s', font_size=24).next_to(clock.n2p(0), DOWN), Text('1 s', font_size=24).next_to(clock.n2p(1), DOWN))
        clock_name = Text('time', font_size=28, color=GREY_A).next_to(clock, LEFT, buff=0.5)
        self.play(Create(clock), FadeIn(clock_ends), FadeIn(clock_name))
        counter = Text('snapshot 0 of 15', font_size=26, color=SCAFFOLD).next_to(clock, DOWN, buff=0.6)
        self.add(counter)
        for k in range(1, 16):
            flash = Dot(clock.n2p(k / 15), color=FOCUS, radius=0.07)
            alpha.set_value(k / 15)
            new = Text(f'snapshot {k} of 15', font_size=26, color=SCAFFOLD).move_to(counter)
            self.remove(counter)
            counter = new
            self.add(counter, flash)
            self.wait(0.3)
        engine = Text('start · end · alpha', font_size=36, color=FOCUS).next_to(slider, DOWN, buff=0.45)
        self.play(FadeOut(ends), Write(engine))
        self.finish()


class Segment_3_3(Segment):
    """Rate functions."""
    EPISODE, SEGMENT = 3, '3.3'

    def construct(self):
        # [V3.3a] time across, alpha up
        axes = Axes(x_range=[0, 1, 0.25], y_range=[0, 1, 0.25], x_length=4.6, y_length=4.6, tips=False,
                    axis_config={'color': GREY_B, 'include_ticks': True}).move_to(LEFT * 3.9 + UP * 0.2)
        x_label = Text('time, 0 to 1', font_size=24, color=GREY_A).next_to(axes.x_axis, DOWN, buff=0.3)
        y_label = MathTex(r'\alpha', font_size=40, color=FOCUS).next_to(axes.y_axis, LEFT, buff=0.3)
        between = VGroup(Text('clock', font_size=26), Arrow(LEFT * 0.6, RIGHT * 0.6, buff=0, color=GREY_B),
                         Text('rate function', font_size=26, color=FOCUS), Arrow(LEFT * 0.6, RIGHT * 0.6, buff=0, color=GREY_B),
                         MathTex(r'\alpha', font_size=40, color=FOCUS)).arrange(RIGHT, buff=0.25).to_edge(UP, buff=0.4)
        self.play(FadeIn(between))
        self.play(Create(axes), FadeIn(x_label), FadeIn(y_label))
        self.hold_until(0.12)

        lanes = VGroup()
        time = ValueTracker(0)

        def lane(index, name, rate, color):
            y = 2.0 - 0.95 * index
            line = Line(RIGHT * 1.2 + UP * y, RIGHT * 6.4 + UP * y, color=GREY_D)
            label = Text(name, font=MONO, font_size=22, color=color).next_to(line, UP, buff=0.12, aligned_edge=LEFT)
            curve = axes.plot(rate, x_range=[0, 1, 0.01], color=color, stroke_width=4)
            rider = always_redraw(lambda: Dot(axes.c2p(time.get_value(), rate(time.get_value())), color=color, radius=0.08))
            runner = always_redraw(lambda: Dot(line.point_from_proportion(rate(time.get_value())), color=color, radius=0.11))
            lanes.add(VGroup(line, label))
            return VGroup(line, label), curve, rider, runner

        def introduce(*indices):
            parts = [lane(i, *RATES[i]) for i in indices]
            self.play(*[Create(c) for _, c, _, _ in parts], *[FadeIn(l) for l, _, _, _ in parts], run_time=1.5)
            time.set_value(0)
            self.add(*[r for _, _, r, _ in parts], *[r for _, _, _, r in parts])
            self.play(time.animate.set_value(1), run_time=3, rate_func=linear)
            self.wait(0.6)
            return parts

        # linear: steady, like a conveyor belt
        linear_parts = introduce(0)
        self.hold_until(0.29)

        # [V3.3b] smooth: ease out, cruise, ease in
        smooth_parts = introduce(1)
        time.set_value(0)
        self.wait(0.3)
        self.play(time.animate.set_value(1), run_time=3, rate_func=linear)
        self.hold_until(0.52)

        # [V3.3c] rush_into and rush_from, then [V3.3d] there_and_back
        for parts in (linear_parts, smooth_parts):
            self.play(*[p.animate.set_stroke(opacity=0.35) for _, p, _, _ in parts], run_time=0.4)
        rush_parts = introduce(2, 3)
        self.hold_until(0.63)
        back_parts = introduce(4)
        home = Text('comes home', font_size=24, color=WARNING).next_to(lanes[-1], DOWN, buff=0.15)
        self.play(FadeIn(home))
        self.hold_until(0.73)

        # [V3.3e] the q03-01 race: five lanes, one rate function each
        everything = [m for m in self.mobjects]
        self.play(*[FadeOut(m) for m in everything])
        race_lanes, dots, animations = VGroup(), VGroup(), []
        for row, (name, rate, color) in enumerate(RATES):
            y = 2.7 - 0.85 * row
            label = Text(name, font=MONO, font_size=24, color=color).move_to(LEFT * 5.1 + UP * y)
            line = Line(LEFT * 3 + UP * y, RIGHT * 4 + UP * y, stroke_opacity=0.3)
            race_lanes.add(label, line)
            dots.add(Dot(LEFT * 3 + UP * y, color=FOCUS))
        code = VGroup(code_text('animations.append(dot.animate(rate_func=rate).shift(RIGHT * 7))', 22),
                      code_text('self.play(*animations, run_time=3)', 22))
        code.arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        code.scale_to_fit_width(min(code.width, 10.4)).to_corner(DL, buff=0.5)
        qr = qr_card('q03-01')
        self.play(FadeIn(race_lanes), FadeIn(dots), FadeIn(code), FadeIn(qr))
        for repeat in range(3):
            self.play(*[d.animate(rate_func=rate).shift(RIGHT * 7) for d, (_, rate, _) in zip(dots, RATES)], run_time=3)
            self.wait(1.2)
            for d in dots:
                d.move_to([-3, d.get_y(), 0])
            self.wait(0.6)
        own = code_text('rate_func=lambda t: t ** 3', 24, FOCUS).next_to(code, UP, buff=0.35, aligned_edge=LEFT)
        own_note = Text('or any function of your own', font_size=22, color=SCAFFOLD)
        own_note.next_to(own, RIGHT, buff=0.3)
        self.play(FadeIn(own), FadeIn(own_note))
        self.finish()


class Segment_3_4(Segment):
    """A tour of built-in animations."""
    EPISODE, SEGMENT = 3, '3.4'

    def construct(self):
        intro = Text('dozens of ready-made animations', font_size=40).shift(UP * 0.5)
        self.play(Write(intro))
        self.hold_until(0.09)

        # [V3.4a] the q03-02 scene, scaled to leave room for its QR code, captioned by its own code
        title = Text('Hello, Manim').shift(UP * 2)
        circle = Circle(color=BLUE).shift(DOWN * 1.5)
        star = Star(color=YELLOW, fill_opacity=1).scale(0.6).shift(RIGHT * 4 + DOWN * 1.5)
        square = Square(color=GREEN).scale(0.6).shift(LEFT * 4 + DOWN * 1.5)
        stage_group = VGroup(title, circle, star, square)
        stage_group.scale(0.75, about_point=ORIGIN).shift(LEFT * 1.2 + UP * 0.6)
        source = snippet_lines('ep03/02-entrances.py', 10, 17).splitlines()
        caption = None

        def show(line, family, *animations, wait=0.6):
            nonlocal caption
            new = VGroup(code_text(source[line], 24, FOCUS),
                         Text(family, font_size=22, color=SCAFFOLD))
            new.arrange(RIGHT, buff=0.4, aligned_edge=DOWN)
            new.scale_to_fit_width(min(new.width, 10.4)).to_corner(DL, buff=0.5)
            self.play(FadeOut(caption) if caption else Wait(0.01), FadeIn(new), run_time=0.4)
            caption = new
            self.play(*animations)
            self.wait(wait)

        qr = qr_card('q03-02')
        self.play(FadeOut(intro), FadeIn(qr))
        show(0, 'brings in', Write(title))
        show(1, 'brings in', Create(circle))
        show(2, 'brings in', GrowFromCenter(star))
        show(3, 'brings in', FadeIn(square, shift=UP * 0.75))
        self.hold_until(0.36)
        show(4, 'draws attention', Indicate(title))
        self.hold_until(0.45)
        show(5, 'draws attention', Circumscribe(circle))
        self.hold_until(0.53)
        show(6, 'changes', Rotate(star, PI))
        self.hold_until(0.59)
        show(7, 'takes away', FadeOut(title, circle, star, square, shift=DOWN * 0.75))
        self.play(FadeOut(caption), FadeOut(qr))

        # [V3.4b] names sorted into four bins
        bins = VGroup()
        for heading, color in (('brings in', AFTER), ('draws attention', FOCUS), ('changes', OBJECT), ('takes away', WARNING)):
            box = RoundedRectangle(width=3.2, height=3.9, corner_radius=0.15).set_stroke(color, 2)
            label = Text(heading, font_size=26, color=color).next_to(box, UP, buff=0.15)
            bins.add(VGroup(box, label))
        bins.arrange(RIGHT, buff=0.35).shift(DOWN * 0.5)
        families = Text('four families', font_size=36).to_edge(UP, buff=0.6)
        self.play(FadeIn(families), LaggedStart(*[FadeIn(b) for b in bins], lag_ratio=0.2))
        contents = [('Create', 'Write', 'GrowFromCenter', 'FadeIn'), ('Indicate', 'Circumscribe'),
                    ('Rotate', 'Transform'), ('FadeOut', 'Uncreate', 'ShrinkToCenter')]
        chips = VGroup()
        for bin_, names in zip(bins, contents):
            for k, name in enumerate(names):
                chip = code_text(name, 22, GREY_A)
                # the last bin leaves room for a note under Uncreate
                chip.move_to(bin_[0].get_top() + DOWN * (0.5 + 0.6 * k + (0.55 if name == 'ShrinkToCenter' else 0)))
                chips.add(chip)
        self.play(LaggedStart(*[FadeIn(c, target_position=ORIGIN + DOWN * 3.6, scale=0.5) for c in chips], lag_ratio=0.15),
                  run_time=3)
        removed = Text('removed when done', font_size=20, color=WARNING).next_to(chips[-2], DOWN, buff=0.15)
        self.play(FadeIn(removed))
        self.wait(0.5)
        shrink_chip = chips[-1]
        stays = Text('stays: zero size,\ninvisible but present', font_size=20, color=SCAFFOLD, line_spacing=0.8)
        stays.next_to(shrink_chip, DOWN, buff=0.15)
        self.play(shrink_chip.animate.set_color(FOCUS))
        self.play(FadeIn(stays))
        self.hold_until(0.87)

        # scan it: one line, one effect
        board = VGroup(families, bins, chips, removed, stays)
        self.play(board.animate.scale(0.8).to_edge(LEFT, buff=0.3), FadeIn(qr_card('q03-02')))
        self.finish()


CORNER_COLORS = (FOCUS, AFTER, PINK, ORANGE)


def corners(centre, side):
    """A square's corners in Manim's point order: upper right, then anticlockwise."""
    return [centre + side / 2 * np.array([x, y, 0]) for x, y in ((1, 1), (-1, 1), (-1, -1), (1, -1))]


class Segment_3_5(Segment):
    """The animate builder, and the shrinking square."""
    EPISODE, SEGMENT = 3, '3.5'

    def construct(self):
        # [V3.5a] animate: copy, apply instantly, then interpolate
        code = code_text('square.animate.shift(RIGHT * 2).scale(0.5)', 32).to_edge(UP, buff=0.5)
        square = Square(2.4, color=OBJECT).move_to(LEFT * 4.2 + DOWN * 0.4)
        self.play(Write(code), Create(square))
        self.hold_until(0.10)

        steps = VGroup(Text('1. copy the square', font_size=28),
                       Text('2. apply the methods to the copy, instantly', font_size=28),
                       Text('3. animate from the square to the copy', font_size=28))
        steps.arrange(DOWN, aligned_edge=LEFT, buff=0.35).to_edge(RIGHT, buff=0.5).shift(DOWN * 0.4)
        ghost = DashedVMobject(square.copy().set_stroke(GREY_B, 3), num_dashes=32)
        self.play(FadeIn(steps[0]), FadeIn(ghost))
        target_label = Text('target', font_size=24, color=SCAFFOLD)
        self.wait(1)
        self.play(FadeIn(steps[1]))
        shift_box = SurroundingRectangle(code[14:29], color=FOCUS, buff=0.06)
        scale_box = SurroundingRectangle(code[29:40], color=FOCUS, buff=0.06)
        self.play(Create(shift_box))
        self.play(ghost.animate.shift(RIGHT * 2), run_time=0.15)
        self.wait(0.6)
        self.play(ReplacementTransform(shift_box, scale_box))
        self.play(ghost.animate.scale(0.5), run_time=0.15)
        target_label.next_to(ghost, DOWN, buff=0.25)
        self.play(FadeIn(target_label), FadeOut(scale_box))
        self.wait(0.8)
        self.play(FadeIn(steps[2]))
        self.play(Transform(square, Square(1.2, color=OBJECT).move_to(ghost)), run_time=2)
        anywhere = Text('any method that changes a mobject can become an animation', font_size=26, color=FOCUS)
        anywhere.to_edge(DOWN, buff=0.6)
        self.play(FadeIn(anywhere))
        self.hold_until(0.28)

        # [V3.5b] the mystery: every corner moves in a straight line to its target
        self.play(FadeOut(VGroup(code, square, steps, ghost, target_label, anywhere)))
        centre, side = UP * 0.2, 3.2
        start = corners(centre, side)
        alpha = ValueTracker(0)
        turn = {'steps': 1}

        def goal(k):
            return start[(k + turn['steps']) % 4]

        def at(k):
            return start[k] + alpha.get_value() * (goal(k) - start[k])

        heading = code_text('square.animate.rotate(PI / 2)', 30).to_edge(UP, buff=0.5)
        outline = DashedVMobject(Square(side).move_to(centre).set_stroke(GREY_D, 2), num_dashes=40)
        live = always_redraw(lambda: Polygon(*[at(k) for k in range(4)], color=OBJECT, stroke_width=5))
        dots = always_redraw(lambda: VGroup(*[Dot(at(k), color=CORNER_COLORS[k], radius=0.1) for k in range(4)]))
        rings = VGroup(*[Circle(radius=0.17, color=CORNER_COLORS[k], stroke_width=3).move_to(goal(k)) for k in range(4)])
        tracks = VGroup(*[DashedLine(start[k], goal(k), color=CORNER_COLORS[k], stroke_width=3, dash_length=0.12)
                          for k in range(4)])
        self.play(Write(heading), FadeIn(outline), FadeIn(live), FadeIn(dots))
        self.play(FadeIn(rings))
        self.hold_until(0.37)
        straight = Text('each point: a straight line to where it ends', font_size=28, color=GREY_A).to_edge(DOWN, buff=0.6)
        self.play(Create(tracks), FadeIn(straight), run_time=1.5)
        self.hold_until(0.46)

        # [V3.5c] follow one corner, then all four: a smaller square halfway
        self.play(*[t.animate.set_stroke(opacity=0.2) for t in tracks[1:]], tracks[0].animate.set_stroke(width=6))
        self.play(alpha.animate.set_value(0.5), run_time=3)
        shortcut = Text('a shortcut, not a circle', font_size=26, color=FOCUS).next_to(at(0), UR, buff=0.2)
        self.play(FadeIn(shortcut))
        self.wait(0.6)
        self.play(*[t.animate.set_stroke(opacity=1, width=3) for t in tracks], FadeOut(shortcut))
        middle = [at(k) for k in range(4)]
        inward = normalize(centre - (middle[0] + middle[1]) / 2)
        small = BraceBetweenPoints(middle[1], middle[0], direction=inward, color=FOCUS)
        small_label = Text('71 %', font_size=30, color=FOCUS).move_to(small.get_tip() + inward * 0.45)
        full = BraceBetweenPoints(start[0], start[1], direction=UP, color=GREY_B)
        full_label = Text('100 %', font_size=26, color=GREY_B).next_to(full, UP, buff=0.08)
        self.play(GrowFromCenter(full), FadeIn(full_label), GrowFromCenter(small), FadeIn(small_label))
        self.hold_until(0.55)
        self.play(FadeOut(VGroup(full, full_label, small, small_label)))
        self.play(alpha.animate.set_value(1), run_time=2)
        self.hold_until(0.59)

        # [V3.5d] the half turn: every track crosses the centre
        heading_pi = code_text('square.animate.rotate(PI)', 30).move_to(heading)
        turn['steps'] = 2
        alpha.set_value(0)
        new_rings = VGroup(*[Circle(radius=0.17, color=CORNER_COLORS[k], stroke_width=3).move_to(goal(k)) for k in range(4)])
        new_tracks = VGroup(*[DashedLine(start[k], goal(k), color=CORNER_COLORS[k], stroke_width=3, dash_length=0.12)
                              for k in range(4)])
        listing = VGroup(*[code_text(line, 20) for line in snippet_lines('ep03/03-two-rotations.py', 11, 12).splitlines()])
        listing.arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        listing.scale_to_fit_width(min(listing.width, 10.2)).to_corner(DL, buff=0.45)
        qr = qr_card('q03-03')
        self.play(Transform(heading, heading_pi), ReplacementTransform(rings, new_rings), ReplacementTransform(tracks, new_tracks),
                  FadeOut(straight), FadeIn(listing), FadeIn(qr))
        self.play(alpha.animate.set_value(0.5), run_time=3)
        vanish = Text('all four meet: the square vanishes', font_size=26, color=WARNING).next_to(outline, DOWN, buff=0.3)
        self.play(Flash(centre, color=WARNING), FadeIn(vanish))
        self.wait(1)
        self.play(alpha.animate.set_value(1), run_time=2.5)
        self.hold_until(0.76)

        # [V3.5e] Rotate turns the original by a fraction of the angle: corners ride circles
        self.play(FadeOut(VGroup(heading, new_rings, new_tracks, vanish, listing, qr, outline)), FadeOut(live), FadeOut(dots))
        self.remove(live, dots)
        angle = ValueTracker(0)
        radius = side / np.sqrt(2)

        def turned(k):
            return centre + rotate_vector(start[k] - centre, angle.get_value())

        yellow = always_redraw(lambda: Polygon(*[turned(k) for k in range(4)], color=FOCUS, stroke_width=5))
        yellow_dots = always_redraw(lambda: VGroup(*[Dot(turned(k), color=CORNER_COLORS[k], radius=0.1) for k in range(4)]))
        arcs = VGroup(*[DashedVMobject(Arc(radius=radius, start_angle=PI / 4 + k * PI / 2, angle=PI, arc_center=centre,
                                           color=CORNER_COLORS[k], stroke_width=3), num_dashes=24) for k in range(4)])
        rotate_heading = code_text('Rotate(square, PI)', 30, FOCUS).to_edge(UP, buff=0.5)
        self.play(Write(rotate_heading), FadeIn(yellow), FadeIn(yellow_dots))
        self.play(Create(arcs), run_time=1.5)
        self.play(angle.animate.set_value(PI), run_time=4)
        rigid = Text('every corner on a circle; the square stays rigid', font_size=28, color=GREY_A).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(rigid))
        self.play(angle.animate.set_value(2 * PI), run_time=4)
        self.hold_until(0.92)

        # the rule
        rule = VGroup(VGroup(code_text('.animate', 30, OBJECT), Text('move, scale, recolour', font_size=30)).arrange(RIGHT, buff=0.4),
                      VGroup(code_text('Rotate', 30, FOCUS), Text('spin', font_size=30)).arrange(RIGHT, buff=0.4))
        rule.arrange(DOWN, aligned_edge=LEFT, buff=0.3).to_edge(DOWN, buff=0.5)
        self.play(FadeOut(rigid), FadeIn(rule))
        self.finish()


def timing_bars(starts, unit=1.0, length=1.0, color=OBJECT, height=0.26, gap=0.12):
    """One horizontal bar per animation, stacked, starting at the given times (seconds)."""
    bars = VGroup()
    for row, t in enumerate(starts):
        bar = Rectangle(width=length * unit, height=height).set_fill(color, 0.8).set_stroke(width=0)
        bar.move_to(RIGHT * (t + length / 2) * unit + DOWN * row * (height + gap))
        bars.add(bar)
    return bars


class Segment_3_6(Segment):
    """Many things at once."""
    EPISODE, SEGMENT = 3, '3.6'

    def construct(self):
        unit, origin = 2.1, LEFT * 5.6 + DOWN * 2.0
        axis = NumberLine(x_range=[0, 3, 1], length=3 * unit, include_numbers=True, font_size=22, color=GREY_B)
        axis.move_to(origin + RIGHT * 1.5 * unit + DOWN * 1.15)
        seconds = Text('seconds', font_size=20, color=SCAFFOLD).next_to(axis, RIGHT, buff=0.15)

        def place(bars):
            return bars.move_to(origin, aligned_edge=UL)

        def playhead(total):
            head = Line(UP * 0.55, DOWN * 0.95, color=FOCUS, stroke_width=3).move_to(origin + DOWN * 0.38, aligned_edge=UP)
            return head, head.animate(rate_func=linear, run_time=total).shift(RIGHT * total * unit)

        # [V3.6a] self.play(a, b, c): three bars, start and end together
        call = code_text('self.play(a, b, c)', 34).shift(UP * 1.2)
        bars = place(timing_bars([0, 0, 0], unit))
        self.play(Write(call), Create(axis), FadeIn(seconds))
        self.play(*[GrowFromEdge(b, LEFT) for b in bars])
        self.hold_until(0.2)

        # [V3.6b] the q03-04 scene, with a timeline for each tool
        balls = [Circle(radius=0.5, color=c, fill_opacity=0.8) for c in (RED, GREEN, BLUE)]
        VGroup(*balls).arrange(RIGHT, buff=1).shift(UP * 0.7)
        label = Text('AnimationGroup', font_size=32).to_edge(UP)
        qr = qr_card('q03-04')
        self.play(FadeOut(call), FadeIn(label), FadeIn(qr))
        head, sweep = playhead(1)
        self.add(head)
        self.play(AnimationGroup(*[GrowFromCenter(b) for b in balls]), sweep)
        together = Text('start together', font_size=24, color=SCAFFOLD).next_to(bars, RIGHT, buff=0.3)
        self.play(FadeIn(together), FadeOut(head))
        self.hold_until(0.32)

        # LaggedStart: each begins when the previous is halfway done
        lagged = place(timing_bars([0, 0.5, 1], unit))
        self.play(Transform(label, Text('LaggedStart', font_size=32).to_edge(UP)), ReplacementTransform(bars, lagged),
                  FadeOut(together))
        ratio = code_text('lag_ratio=0.5', 24, FOCUS).next_to(lagged, RIGHT, buff=0.3)
        self.play(FadeIn(ratio))
        head, sweep = playhead(2)
        self.add(head)
        self.play(LaggedStart(*[b.animate.shift(UP) for b in balls], lag_ratio=0.5), sweep)
        self.play(FadeOut(head))
        self.wait(0.6)
        for b in balls:
            b.shift(DOWN)
        self.play(*[FadeIn(b) for b in balls], run_time=0.01)
        head, sweep = playhead(2)
        self.add(head)
        self.play(LaggedStart(*[b.animate.shift(UP) for b in balls], lag_ratio=0.5), sweep)
        ripple = Text('overlap, like a ripple', font_size=24, color=SCAFFOLD).next_to(ratio, UP, buff=0.15, aligned_edge=LEFT)
        self.play(FadeIn(ripple), FadeOut(head))
        self.hold_until(0.61)

        # Succession: strictly one after another
        chain = place(timing_bars([0, 1, 2], unit))
        self.play(Transform(label, Text('Succession', font_size=32).to_edge(UP)), ReplacementTransform(lagged, chain),
                  FadeOut(ratio), FadeOut(ripple))
        head, sweep = playhead(3)
        self.add(head)
        self.play(Succession(*[b.animate.shift(DOWN * 2) for b in balls]), sweep)
        self.play(FadeOut(head))
        self.hold_until(0.71)

        # [V3.6d] the q03-05 wave: sixteen identical motions, a small lag
        self.play(FadeOut(VGroup(label, chain, axis, seconds, qr, *balls)))
        bars = VGroup(*[
            Rectangle(width=0.4, height=1, fill_opacity=1, stroke_width=0,
                      color=interpolate_color(BLUE, PURPLE, i / 15))
            for i in range(16)
        ]).arrange(RIGHT, buff=0.1).shift(UP * 0.4)
        code = code_text('bar.animate(rate_func=there_and_back).stretch(3, 1)', 22).to_corner(DL, buff=0.5)
        self.play(FadeIn(bars), FadeIn(code), FadeIn(qr_card('q03-05')))
        for _ in range(2):
            self.play(LaggedStart(*[bar.animate(rate_func=there_and_back).stretch(3, 1) for bar in bars],
                                  lag_ratio=0.15, run_time=3))
            self.wait(0.5)
        self.hold_until(0.9)
        self.play(LaggedStart(*[FadeOut(bar, shift=DOWN) for bar in bars], lag_ratio=0.05))
        self.finish()


class Segment_3_7(Segment):
    """Who is on screen after a Transform?"""
    EPISODE, SEGMENT = 3, '3.7'

    def construct(self):
        # [V3.7a] the q03-06 layout: a square on each side, its target circle drawn dashed
        a, b = Square(color=BLUE), Circle(color=YELLOW)
        c, d = Square(color=BLUE), Circle(color=YELLOW)
        VGroup(a, b).shift(LEFT * 3 + UP * 0.3)
        VGroup(c, d).shift(RIGHT * 3 + UP * 0.3)
        titles = VGroup(code_text('Transform(a, b)', 28).shift(LEFT * 3 + UP * 2.9),
                        code_text('ReplacementTransform(c, d)', 28).shift(RIGHT * 3 + UP * 2.9))
        ghost_b = DashedVMobject(b.copy().set_stroke(YELLOW, 2, opacity=0.6), num_dashes=30)
        ghost_d = DashedVMobject(d.copy().set_stroke(YELLOW, 2, opacity=0.6), num_dashes=30)
        notes = {k: sticky_note(k) for k in 'abcd'}
        strings = {'a': attach(notes['a'], a, UL), 'b': attach(notes['b'], ghost_b, UR),
                   'c': attach(notes['c'], c, UL), 'd': attach(notes['d'], ghost_d, UR)}
        for note in notes.values():
            note.update()
        self.play(FadeIn(titles), Create(a), Create(c))
        self.play(*[FadeIn(notes[k]) for k in 'ac'], *[FadeIn(strings[k]) for k in 'ac'])
        offstage = Text('dashed: a target, never added to the scene', font_size=24, color=SCAFFOLD).to_edge(DOWN, buff=0.5)
        self.play(Create(ghost_b), Create(ghost_d), *[FadeIn(notes[k]) for k in 'bd'], *[FadeIn(strings[k]) for k in 'bd'],
                  FadeIn(offstage))
        self.hold_until(0.16)

        # Transform(a, b): looks like b, still named a
        box = SurroundingRectangle(titles[0], color=FOCUS, buff=0.1)
        self.play(Create(box))
        self.play(Transform(a, b), run_time=2)
        still = Text('on screen: still a', font_size=28, color=FOCUS).move_to(LEFT * 3 + DOWN * 1.9)
        self.play(FadeIn(still), Indicate(notes['a'], scale_factor=1.3))
        self.hold_until(0.43)

        # ReplacementTransform(c, d): c leaves, d takes its place
        self.play(box.animate.become(SurroundingRectangle(titles[1], color=FOCUS, buff=0.1)))
        self.play(ReplacementTransform(c, d), run_time=2)
        notes['c'].clear_updaters()
        self.remove(strings['c'], ghost_d)
        strings['d'].clear_updaters()
        self.remove(strings['d'])
        notes['d'].clear_updaters()
        strings['d'] = attach(notes['d'], d, UR)
        self.add(strings['d'])
        self.play(FadeOut(notes['c'], shift=DOWN), FadeOut(offstage))
        now = Text('on screen: d', font_size=28, color=AFTER).move_to(RIGHT * 3 + DOWN * 1.9)
        self.play(FadeIn(now), Indicate(notes['d'], scale_factor=1.3))
        self.wait(1)

        # [V3.7c] moving what you see: animate a on the left, d on the right
        line = code_text('self.play(a.animate.shift(DOWN * 1.5), d.animate.shift(DOWN * 1.5))', 22, FOCUS)
        line.scale_to_fit_width(min(line.width, 10.2)).to_corner(DL, buff=0.5)
        qr = qr_card('q03-06')
        self.play(FadeOut(box), FadeOut(still), FadeOut(now), FadeIn(line), FadeIn(qr))
        self.play(a.animate.shift(DOWN * 1.5), d.animate.shift(DOWN * 1.5), run_time=1.5)
        self.hold_until(0.64)

        # neither is wrong: pick the name you want to keep using
        rules = VGroup(Text('Transform: keep talking about the same object', font_size=24),
                       Text('ReplacementTransform: use the new name', font_size=24))
        rules.arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_corner(DL, buff=0.45)
        self.play(FadeOut(line), FadeIn(rules[0]))
        self.wait(1.5)
        self.play(FadeIn(rules[1]))
        self.finish()


class Segment_3_8(Segment):
    """Choosing how long things take."""
    EPISODE, SEGMENT = 3, '3.8'

    def construct(self):
        checklist = VGroup()
        demo_centre = LEFT * 2.6 + UP * 0.4

        def check(words):
            item = VGroup(Text('✓', font_size=30, color=AFTER), Text(words, font_size=26)).arrange(RIGHT, buff=0.2)
            if checklist:
                item.next_to(checklist, DOWN, buff=0.3, aligned_edge=LEFT)
            else:
                item.move_to(RIGHT * 4.2 + UP * 2.4)
            checklist.add(item)
            return FadeIn(item, shift=LEFT * 0.3)

        # [V3.8a] one reveal at three speeds
        formula = MathTex('(a+b)^2', '=', 'a^2 + 2ab + b^2', font_size=56).move_to(demo_centre + UP * 1.0)
        watch = clock_icon(0.55).move_to(demo_centre + DOWN * 1.2)
        verdict = None
        self.play(FadeIn(watch))
        for seconds, words, color in ((0.3, 'too fast', WARNING), (1, 'about right', AFTER), (4, 'too slow  z z z', SCAFFOLD)):
            label = Text(f'{seconds:g} s', font_size=28).next_to(watch, LEFT, buff=0.3)
            reveal = formula.copy()
            self.play(FadeIn(label), *([FadeOut(verdict)] if verdict else []), run_time=0.3)
            self.play(Write(reveal), Rotate(watch[1], -TAU * seconds / 4, about_point=watch[0].get_center()), run_time=seconds)
            verdict = Text(words, font_size=28, color=color).next_to(watch, RIGHT, buff=0.3)
            self.play(FadeIn(verdict), watch[0].animate.set_color(color), run_time=0.4)
            self.wait(0.4)
            self.play(FadeOut(reveal), FadeOut(label), watch[0].animate.set_color(GREY_A), run_time=0.3)
        self.play(FadeOut(verdict), FadeOut(watch))
        self.hold_until(0.12)

        # big changes slower, small changes faster
        track = Line(LEFT * 0.8, RIGHT * 0.8, color=GREY_D).move_to(demo_centre + LEFT * 2.6 + UP * 0.6)
        dot = Dot(track.get_start(), color=FOCUS)
        quick = Text('small: quick', font_size=24, color=SCAFFOLD).next_to(track, DOWN, buff=0.6)
        grid = NumberPlane(x_range=[-2, 2], y_range=[-2, 2], x_length=3, y_length=3,
                           background_line_style={'stroke_opacity': 0.6}).move_to(demo_centre + RIGHT * 1.6 + UP * 0.2)
        slow = Text('big: two or three seconds', font_size=24, color=SCAFFOLD).next_to(grid, DOWN, buff=0.3)
        self.play(Create(track), FadeIn(dot), FadeIn(grid))
        self.wait(1)
        self.play(dot.animate.move_to(track.get_end()), run_time=0.5)
        self.play(FadeIn(quick))
        self.hold_until(0.25)
        centre = grid.get_center()
        self.play(grid.animate.apply_function(lambda p: centre + rotate_vector(p - centre, 0.5 * np.exp(-np.linalg.norm(p - centre) ** 2 / 2))),
                  run_time=3)
        self.play(FadeIn(slow), check('big changes: slower'), check('small changes: faster'))
        self.hold_until(0.45)

        # new text needs time to be read
        self.play(FadeOut(VGroup(track, dot, quick, grid, slow)))
        sentence = Text('A shape is just many points.', font_size=34).move_to(demo_centre + UP * 0.6)
        self.add(sentence)
        self.wait(0.25)
        self.remove(sentence)
        what = Text('?', font_size=60, color=WARNING).move_to(sentence)
        self.play(FadeIn(what), run_time=0.3)
        self.wait(0.8)
        self.play(FadeOut(what), run_time=0.3)
        reading = Line(sentence.get_corner(DL) + DOWN * 0.3, sentence.get_corner(DR) + DOWN * 0.3, color=AFTER, stroke_width=6)
        self.play(FadeIn(sentence))
        self.play(Create(reading), run_time=2.5, rate_func=linear)
        read_label = Text('time to read, growing with its length', font_size=22, color=SCAFFOLD).next_to(reading, DOWN, buff=0.2)
        self.play(FadeIn(read_label), check('new text: time to read'))
        self.hold_until(0.62)

        # after a reveal, a pause
        self.play(FadeOut(VGroup(sentence, reading, read_label)))
        reveal = formula.copy().move_to(demo_centre + UP * 0.8)
        self.play(Write(reveal), run_time=1.5)
        pause = Rectangle(width=0.01, height=0.32).set_fill(WHITE, 0.85).set_stroke(width=0)
        pause.move_to(demo_centre + DOWN * 0.6, aligned_edge=LEFT).shift(LEFT * 1.5)
        pause_label = code_text('self.wait(1.5)', 24).next_to(pause, DOWN, buff=0.25, aligned_edge=LEFT)
        self.play(FadeIn(pause_label))
        self.play(pause.animate.stretch_to_fit_width(3, about_edge=LEFT), run_time=1.5, rate_func=linear)
        aha = Text('"oh, I see"', font_size=30, color=FOCUS).next_to(pause, RIGHT, buff=0.4)
        self.play(FadeIn(aha), check('after a reveal: a pause'))
        mistake = Text('most common mistake: going too fast', font_size=26, color=WARNING).move_to(demo_centre + DOWN * 2.4)
        self.play(FadeIn(mistake))
        self.hold_until(0.82)

        # [V3.8b] write the words first, then fit animations and waits under them
        self.play(FadeOut(VGroup(reveal, pause, pause_label, aha, mistake)))
        left_x = -6.4
        sentences = [(0.0, 2.6), (3.0, 5.4), (6.0, 8.6), (9.1, 11.0)]   # narration, in seconds
        scale = 1.0

        def span(t0, t1, y, color, opacity):
            rect = Rectangle(width=(t1 - t0) * scale, height=0.4).set_fill(color, opacity).set_stroke(width=0)
            return rect.move_to([left_x + (t0 + t1) / 2 * scale, y, 0])

        voice = VGroup(*[span(t0, t1, -0.9, GREY_C, 0.7) for t0, t1 in sentences])
        voice_label = Text('narration', font_size=22, color=GREY_B).next_to(voice, UP, buff=0.15, aligned_edge=LEFT)
        rough = VGroup(*[span(k * 1.1, k * 1.1 + 1, -1.6, OBJECT, 0.85) for k in range(4)])
        anim_label = Text('animations', font_size=22, color=OBJECT).next_to(rough, DOWN, buff=0.15, aligned_edge=LEFT)
        words_first = Text('write the words first, then fit the animations to them', font_size=28, color=FOCUS)
        words_first.move_to(LEFT * 0.8 + DOWN * 3.1)
        self.play(FadeIn(voice), FadeIn(voice_label), FadeIn(words_first))
        self.play(FadeIn(rough), FadeIn(anim_label))
        self.wait(0.6)
        fitted = VGroup(*[span(t0, t1, -1.6, OBJECT, 0.85) for t0, t1 in sentences])
        gaps = VGroup(*[span(t1, t0, -1.6, WHITE, 0.85) for (_, t1), (t0, _) in zip(sentences, sentences[1:])])
        self.play(Transform(rough, fitted), run_time=2)
        wait_label = code_text('wait', 20, GREY_A).next_to(gaps[0], DOWN, buff=0.1)
        self.play(FadeIn(gaps), FadeIn(wait_label), anim_label.animate.next_to(fitted, DOWN, buff=0.45, aligned_edge=LEFT))
        self.finish()


class Segment_3_9(Segment):
    """Recap."""
    EPISODE, SEGMENT = 3, '3.9'

    def construct(self):
        # [V3.9a] one tile per idea
        slider = NumberLine(x_range=[0, 1, 0.1], length=2.8, include_tip=False, color=GREY_B)
        knob = Triangle(color=FOCUS, fill_opacity=1).scale(0.12).rotate(PI).next_to(slider.n2p(0.6), UP, buff=0.04)
        alpha_tile = VGroup(slider, knob, MathTex(r'\alpha', color=FOCUS).next_to(slider, LEFT, buff=0.2))

        axes = Axes(x_range=[0, 1, 1], y_range=[0, 1, 1], x_length=2, y_length=1.6, tips=False, axis_config={'color': GREY_D})
        curves = VGroup(axes, *[axes.plot(rate, x_range=[0, 1, 0.02], color=color, stroke_width=3) for _, rate, color in RATES])

        families = VGroup(*[Text(w, font_size=22, color=c) for w, c in
                            (('brings in', AFTER), ('draws attention', FOCUS), ('changes', OBJECT), ('takes away', WARNING))])
        families.arrange(DOWN, buff=0.1)

        start = corners(ORIGIN, 1.3)
        blue = VGroup(Square(1.3, color=OBJECT), *[DashedLine(start[k], start[(k + 2) % 4], color=GREY_B, stroke_width=2,
                                                              dash_length=0.08) for k in range(2)])
        yellow = VGroup(Square(1.3, color=FOCUS), DashedVMobject(Circle(radius=1.3 / np.sqrt(2), color=GREY_B, stroke_width=2),
                                                                 num_dashes=24))
        rotations = VGroup(blue, yellow).arrange(RIGHT, buff=0.5)

        diagrams = VGroup(*[timing_bars(starts, 0.45, height=0.12, gap=0.06) for starts in ([0, 0, 0], [0, 0.5, 1], [0, 1, 2])])
        diagrams.arrange(RIGHT, buff=0.35, aligned_edge=UP)

        keep = Square(1.1, color=AFTER)
        keep_note = sticky_note('a').scale(0.6).next_to(keep, UL, buff=0.05)
        names = VGroup(keep, keep_note)

        tiles = VGroup()
        for art, words in ((alpha_tile, 'start, end and alpha'), (curves, 'rate functions bend time'),
                           (families, 'four families'), (rotations, 'straight lines, or a spin'),
                           (diagrams, 'together, lagged, in turn'), (names, 'Transform keeps the name')):
            art.move_to(ORIGIN)
            caption = Text(words, font_size=22, color=SCAFFOLD).next_to(art, DOWN, buff=0.25)
            tiles.add(VGroup(art, caption))
        for k, tile in enumerate(tiles):
            tile.move_to([(-4.6, 0, 4.6)[k % 3], (1.7, -1.9)[k // 3], 0])
        self.play(LaggedStart(*[FadeIn(t, shift=UP * 0.2) for t in tiles], lag_ratio=0.35), run_time=5)
        self.hold_until(0.55)

        # [V3.9b] the QR wall, 10 seconds
        wall = qr_wall([f'q03-0{i}' for i in range(1, 7)])
        heading = Text('Episode 3 · scan to open each scene', font_size=26, color=SCAFFOLD).to_corner(UL, buff=0.3)
        self.play(FadeOut(tiles), FadeIn(wall), FadeIn(heading))
        self.wait(10)

        # [V3.9c] teaser: four corners become many points, and handles sprout (episode 4)
        self.play(FadeOut(VGroup(wall, heading)))
        four = VGroup(*[Dot(p, color=CORNER_COLORS[k], radius=0.1) for k, p in enumerate(corners(ORIGIN, 3))])
        self.play(FadeIn(four, scale=2))
        many = VGroup(*[Dot(2 * np.array([np.cos(a), np.sin(a), 0]), color=FOCUS, radius=0.07)
                        for a in np.linspace(0, TAU, 12, endpoint=False)])
        self.play(ReplacementTransform(VGroup(*[four[k % 4].copy() for k in range(12)]), many), FadeOut(four), run_time=2)
        handles = VGroup()
        for dot in many:
            p = dot.get_center()
            tangent = rotate_vector(p, PI / 2) / np.linalg.norm(p) * 0.45
            handles.add(Line(p - tangent, p + tangent, color=GREY_B, stroke_width=2),
                        Dot(p - tangent, radius=0.04, color=GREY_B), Dot(p + tangent, radius=0.04, color=GREY_B))
        self.play(Create(handles), run_time=2)
        nxt = Text('Next: What is a shape, really?', font_size=34).to_edge(DOWN, buff=0.6)
        self.play(Write(nxt))
        self.finish()
