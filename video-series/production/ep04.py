"""Episode 4 · What is a shape, really? One Scene per script segment.

    python3 video-series/production/render.py 4 [-ql] [segment ...]

Shot ids in comments ([V4.2c] ...) refer to episodes/04-what-is-a-shape-really.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403

# Level colours of the de Casteljau construction: controls, first lerps, second lerps, the curve.
LEVELS = (GREY_B, BLUE, GREEN, YELLOW)


def lerp_levels(points, t):
    """Every level of de Casteljau's construction: the controls, then each round of lerps."""
    levels = [[np.array(p, dtype=float) for p in points]]
    while len(levels[-1]) > 1:
        prev = levels[-1]
        levels.append([interpolate(prev[i], prev[i + 1], t) for i in range(len(prev) - 1)])
    return levels


def scaffold(points, t):
    """The moving lines and dots between the controls and the point on the curve."""
    levels = lerp_levels(points, t)
    group = VGroup()
    for depth, level in enumerate(levels[1:-1], start=1):
        color = LEVELS[depth]
        group.add(*[Line(level[i], level[i + 1], color=color, stroke_width=3) for i in range(len(level) - 1)])
        group.add(*[Dot(q, radius=0.07, color=color) for q in level])
    return group


def tip_color(points):
    return LEVELS[len(points) - 1] if len(points) > 2 else YELLOW


def curve_upto(points, t, color=YELLOW, width=6):
    """The curve from t = 0 to t, as Create would show it."""
    if t < 1e-3:
        return VMobject()
    return ParametricFunction(bezier(np.array(points, dtype=float)), t_range=[0, t, t / 60], color=color,
                              stroke_width=width)


def control_polygon(points, names=None, label_dirs=None):
    """Grey control points joined in order, optionally labelled."""
    group = VGroup(*[Line(points[i], points[i + 1], color=GREY_B, stroke_width=2) for i in range(len(points) - 1)],
                   *[Dot(p, color=GREY_B, radius=0.09) for p in points])
    if names:
        for p, name, direction in zip(points, names, label_dirs or [UP] * len(points)):
            group.add(MathTex(name, font_size=36, color=GREY_A).next_to(p, direction, buff=0.15))
    return group


def handle_sticks(points, color=GREY_B):
    """A single cubic's two handles: lines from each anchor to its handle, and the handle dots."""
    return VGroup(Line(points[0], points[1], color=color, stroke_width=2), Line(points[3], points[2], color=color, stroke_width=2),
                  Dot(points[1], color=color, radius=0.07), Dot(points[2], color=color, radius=0.07),
                  Dot(points[0], color=FOCUS, radius=0.09), Dot(points[3], color=FOCUS, radius=0.09))


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


class Segment_4_1(Segment):
    """Cold open: how do you store a circle?"""
    EPISODE, SEGMENT = 4, '4.1'

    def zoom_on(self, base, label, magnifications, note):
        """Bring base's right-hand edge to the centre, then magnify around it."""
        edge = base.get_right()
        shift, zoom = ValueTracker(0), ValueTracker(0)   # zoom is log10 of the magnification
        live = always_redraw(lambda: base.copy().shift(-shift.get_value() * edge).scale(10 ** zoom.get_value(), about_point=ORIGIN))
        readout = always_redraw(lambda: Text(f'× {10 ** zoom.get_value():,.0f}', font_size=40, color=FOCUS)
                                .to_corner(UR, buff=0.5))
        self.play(Create(base), FadeIn(label))
        self.remove(base)
        self.add(live)
        self.play(shift.animate.set_value(1), run_time=1.5)
        self.add(readout)
        for power in magnifications:
            self.play(zoom.animate.set_value(power), run_time=2)
            self.wait(0.8)
        self.play(FadeIn(note))
        return live, readout, shift, zoom

    def construct(self):
        # [V4.1a] a smooth circle, magnified a thousand times
        circle = Circle(radius=2.6, color=OBJECT, stroke_width=6)
        smooth_label = Text('a circle', font_size=30, color=SCAFFOLD).to_corner(UL, buff=0.5)
        still = Text('still perfectly smooth', font_size=30, color=AFTER).to_edge(DOWN, buff=0.6)
        live, readout, shift, zoom = self.zoom_on(circle, smooth_label, (1, 2, 3), still)
        self.hold_until(0.19)

        # [V4.1b] 24 straight segments give themselves away at once
        self.play(FadeOut(VGroup(live, readout, smooth_label, still)))
        self.remove(live, readout)
        polygon = RegularPolygon(24, radius=2.6, color=GREY_A, stroke_width=6)
        polygon_label = Text('24 straight segments', font_size=30, color=SCAFFOLD).to_corner(UL, buff=0.5)
        corner = Text('a corner, at only ten times', font_size=30, color=WARNING).to_edge(DOWN, buff=0.6)
        live, readout, shift, zoom = self.zoom_on(polygon, polygon_label, (1,), corner)
        ring = Circle(radius=0.5, color=WARNING, stroke_width=4)
        self.play(Create(ring))
        self.hold_until(0.36)

        # [V4.1c] finite memory, infinitely many points
        self.play(FadeOut(VGroup(live, readout, polygon_label, corner, ring)))
        self.remove(live, readout)
        puzzle = VGroup(Text('A computer has finite memory.', font_size=40),
                        Text('A circle has infinitely many points.', font_size=40)).arrange(DOWN, buff=0.4)
        self.play(FadeIn(puzzle[0]))
        self.play(FadeIn(puzzle[1]))
        self.hold_until(0.5)

        # [V4.1d] eight pieces, four points each
        self.play(FadeOut(puzzle))
        circle = Circle(radius=2.6, color=OBJECT, stroke_width=6)
        anchors, _ = anchors_and_handles(circle, anchor_radius=0.1)
        self.play(Create(circle))
        self.play(LaggedStart(*[FadeIn(d, scale=2) for d in anchors], lag_ratio=0.15))
        pieces = Text('8 pieces of one kind of curve, 4 points each', font_size=30, color=FOCUS).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(pieces))
        self.hold_until(0.72)

        # the same curves draw letters and drawing-tool paths
        self.play(VGroup(circle, anchors).animate.scale(0.6).shift(LEFT * 4))
        letter = Text('S', font_size=260, weight=BOLD).set_fill(opacity=0).set_stroke(GREY_A, 3)
        letter_dots, _ = anchors_and_handles(letter[0], anchor_radius=0.06)
        VGroup(letter, letter_dots).move_to(ORIGIN + UP * 0.2)
        pen_points = [LEFT * 1.3 + DOWN * 1, LEFT * 0.8 + UP * 1.5, RIGHT * 0.8 + DOWN * 1.5, RIGHT * 1.3 + UP * 1]
        pen = VGroup(CubicBezier(*pen_points, color=AFTER, stroke_width=5), handle_sticks(pen_points)).shift(RIGHT * 4 + UP * 0.2)
        self.play(Create(letter), FadeIn(letter_dots), run_time=2)
        self.play(Create(pen), run_time=2)
        self.finish()


class Segment_4_2(Segment):
    """Lerp, then lerp again."""
    EPISODE, SEGMENT = 4, '4.2'

    def build(self, points, names, label_dirs, caption, run_time=4, caption_shift=ORIGIN):
        t = ValueTracker(0)
        controls = control_polygon(points, names, label_dirs)
        trail = always_redraw(lambda: curve_upto(points, t.get_value(), tip_color(points)))
        moving = always_redraw(lambda: scaffold(points, t.get_value()))
        tip = always_redraw(lambda: Dot(lerp_levels(points, t.get_value())[-1][0], color=tip_color(points), radius=0.11))
        readout = always_redraw(lambda: VGroup(MathTex('t =', font_size=36), DecimalNumber(t.get_value(), font_size=36))
                                .arrange(RIGHT, buff=0.15).to_corner(UR, buff=0.5))
        self.play(FadeIn(controls), FadeIn(readout))
        self.add(trail, moving, tip)
        self.play(t.animate.set_value(1), run_time=run_time, rate_func=linear)
        caption.to_edge(DOWN, buff=0.5).shift(caption_shift)
        self.play(FadeIn(caption))
        return VGroup(controls, trail, moving, tip, readout, caption), t

    def construct(self):
        intro = VGroup(Text('one tool:', font_size=40, color=SCAFFOLD), Text('lerp', font_size=56, color=FOCUS)).arrange(RIGHT, buff=0.3)
        self.play(FadeIn(intro))
        self.hold_until(0.09)
        self.play(FadeOut(intro))

        # [V4.2a] two points: one lerp traces a line
        two = [LEFT * 4 + DOWN * 1.5, RIGHT * 4 + UP * 1.5]
        group, _ = self.build(two, ['P_0', 'P_1'], [DOWN, UP], Text('one lerp: a line', font_size=32), run_time=3)
        self.hold_until(0.19)

        # [V4.2b] three points: a lerp of lerps traces a quadratic curve
        self.play(FadeOut(group))
        three = [LEFT * 5 + DOWN * 2, UP * 3, RIGHT * 5 + DOWN * 2]
        group, t = self.build(three, ['P_0', 'P_1', 'P_2'], [DOWN, UP, DOWN], Text('lerp of lerps: a quadratic curve', font_size=32),
                              run_time=6)
        never = Text('never touches the middle point', font_size=26, color=SCAFFOLD).next_to(three[1], RIGHT, buff=0.5)
        self.play(FadeIn(never))
        self.hold_until(0.48)

        # [V4.2c] four points: the q04-01 construction, which traces a cubic
        self.play(FadeOut(group), FadeOut(never))
        offset = LEFT * 0.9 + UP * 0.2
        p = [LEFT * 5 + DOWN * 2 + offset, LEFT * 2 + UP * 3 + offset, RIGHT * 2 + UP * 3 + offset, RIGHT * 5 + DOWN * 2 + offset]
        qr = qr_card('q04-01')
        self.play(FadeIn(qr))
        group, t = self.build(p, ['P_0', 'P_1', 'P_2', 'P_3'], [DOWN, UP, UP, DOWN],
                              Text('three lerps, then two, then one: a cubic Bézier curve', font_size=30), run_time=6,
                              caption_shift=LEFT * 1.4)

        # [V4.2d] the scaffolding fades, leaving the curve and its controls
        curve = CubicBezier(*p, color=YELLOW, stroke_width=6)
        self.add(curve)
        self.play(FadeOut(group[2]), FadeOut(group[3]), FadeOut(group[4]))
        self.remove(group[1])
        self.hold_until(0.63)

        # history: de Casteljau at Citroën, Bézier at Renault
        self.play(FadeOut(group[5]))
        people = VGroup(
            VGroup(Text('Paul de Casteljau', font_size=30), Text('Citroën, late 1950s', font_size=24, color=SCAFFOLD)).arrange(DOWN, buff=0.1),
            VGroup(Text('Pierre Bézier', font_size=30), Text('Renault, popularised them', font_size=24, color=SCAFFOLD)).arrange(DOWN, buff=0.1))
        people.arrange(RIGHT, buff=1.2).to_edge(DOWN, buff=0.5).shift(LEFT * 1.4)
        self.play(FadeIn(people[0], shift=UP * 0.2))
        self.wait(1.5)
        self.play(FadeIn(people[1], shift=UP * 0.2))
        self.hold_until(0.82)

        # scan it and edit the list p
        line = snippet_lines('ep04/01-de-casteljau.py', 6, 6)
        cut = line.index('RIGHT * 2')
        code = VGroup(code_text(line[:cut].rstrip(), 22, FOCUS), code_text(' ' * 5 + line[cut:], 22, FOCUS))
        code.arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_corner(DL, buff=0.5)
        self.play(FadeOut(people), FadeIn(code))
        self.play(Indicate(group[0][3:7], color=FOCUS))
        self.finish()


class Segment_4_3(Segment):
    """Anchors and handles."""
    EPISODE, SEGMENT = 4, '4.3'

    def construct(self):
        # [V4.3a] two anchors the curve passes through, two handles it leans toward
        a0, a1 = LEFT * 4 + DOWN * 1.5, RIGHT * 4 + DOWN * 1.5
        h0, h1 = Dot(LEFT * 2.5 + UP * 1.5, color=GREY_B, radius=0.07), Dot(RIGHT * 2 + UP * 1.5, color=GREY_B, radius=0.07)
        curve = always_redraw(lambda: CubicBezier(a0, h0.get_center(), h1.get_center(), a1, color=OBJECT, stroke_width=6))
        sticks = always_redraw(lambda: VGroup(Line(a0, h0.get_center(), color=GREY_B, stroke_width=2),
                                              Line(a1, h1.get_center(), color=GREY_B, stroke_width=2)))
        anchors = VGroup(Dot(a0, color=FOCUS, radius=0.13), Dot(a1, color=FOCUS, radius=0.13))
        anchor_labels = VGroup(*[Text('anchor', font_size=26, color=FOCUS).next_to(a, DOWN, buff=0.2) for a in (a0, a1)])
        handle_labels = always_redraw(lambda: VGroup(*[Text('handle', font_size=24, color=GREY_B).next_to(h, UP, buff=0.15)
                                                       for h in (h0, h1)]))
        self.play(Create(curve), run_time=1.5)
        self.play(FadeIn(anchors, scale=2), FadeIn(anchor_labels))
        self.play(Create(sticks), FadeIn(h0), FadeIn(h1), FadeIn(handle_labels))
        heading = Text('leaves heading toward its handle', font_size=28, color=GREY_A).to_edge(UP, buff=0.5)
        self.play(FadeIn(heading))
        self.hold_until(0.22)

        # [V4.3b] pull a handle further: the curve leans harder; swing it: the start direction follows
        self.play(h0.animate.move_to(LEFT * 0.8 + UP * 2.5), run_time=2)
        self.wait(0.5)
        self.play(Rotate(h0, -PI / 2.2, about_point=a0), run_time=2.5)
        self.play(Rotate(h0, PI / 2.2, about_point=a0), run_time=2)
        self.hold_until(0.39)

        # [V4.3c] two curves share an anchor; aligned handles make the join smooth
        self.play(FadeOut(VGroup(curve, sticks, anchors, anchor_labels, handle_labels, h0, h1, heading)))
        self.remove(curve, sticks, handle_labels)
        left, joint, right = LEFT * 5.2 + DOWN * 1.2, DOWN * 0.2, RIGHT * 5.2 + DOWN * 1.2
        angle_in, angle_out = ValueTracker(PI * 0.62), ValueTracker(PI * 0.05)
        reach = 1.6

        def h_in():
            return joint + reach * np.array([np.cos(angle_in.get_value()), np.sin(angle_in.get_value()), 0])

        def h_out():
            return joint + reach * np.array([np.cos(angle_out.get_value()), np.sin(angle_out.get_value()), 0])

        pieces = always_redraw(lambda: VGroup(
            CubicBezier(left, left + UP * 2.4 + RIGHT * 0.6, h_in(), joint, color=OBJECT, stroke_width=6),
            CubicBezier(joint, h_out(), right + UP * 2.4 + LEFT * 0.6, right, color=AFTER, stroke_width=6)))
        handles = always_redraw(lambda: VGroup(Line(h_in(), joint, color=GREY_B, stroke_width=2), Line(joint, h_out(), color=GREY_B, stroke_width=2),
                                               Dot(h_in(), radius=0.07, color=GREY_B), Dot(h_out(), radius=0.07, color=GREY_B),
                                               Dot(joint, radius=0.12, color=FOCUS)))
        chain = Text('chained end to end: one shared anchor', font_size=28, color=GREY_A).to_edge(UP, buff=0.5)
        self.play(Create(pieces), FadeIn(chain), run_time=2)
        self.play(FadeIn(handles))
        kink = Circle(radius=0.45, color=WARNING, stroke_width=4).move_to(joint)
        kink_label = Text('handles not in line: a corner', font_size=26, color=WARNING).next_to(kink, DOWN, buff=0.25)
        self.play(Create(kink), FadeIn(kink_label))
        self.hold_until(0.55)
        self.play(FadeOut(kink), FadeOut(kink_label))
        self.play(angle_in.animate.set_value(PI * 0.93), angle_out.animate.set_value(-PI * 0.07), run_time=2.5)
        smooth = Text('in line: smooth', font_size=26, color=AFTER).next_to(joint, DOWN, buff=0.6)
        self.play(FadeIn(smooth))
        self.hold_until(0.67)

        # [V4.3d] the circle from the cold open, exactly as q04-02 draws it
        self.play(FadeOut(VGroup(pieces, handles, chain, smooth)))
        self.remove(pieces, handles)
        circle = Circle(radius=2.6, color=BLUE).shift(LEFT * 1.2 + UP * 0.4)
        dots, sticks = anchors_and_handles(circle)
        self.play(Create(circle))
        self.play(LaggedStart(*[FadeIn(d, scale=2) for d in dots], lag_ratio=0.2))
        self.play(Create(sticks), run_time=2)
        count = Text(f'{len(circle.get_points()) // 4} cubic curves, {len(circle.get_points())} points', font_size=32)
        count.to_edge(DOWN, buff=0.4).shift(LEFT * 1.2)
        self.play(Write(count), FadeIn(qr_card('q04-02')))
        self.hold_until(0.86)
        error = Text('not exactly circular: the error is far smaller than a pixel', font_size=22, color=SCAFFOLD)
        error.to_corner(UL, buff=0.4)
        self.play(FadeIn(error))
        self.finish()


class Segment_4_4(Segment):
    """Why cubic?"""
    EPISODE, SEGMENT = 4, '4.4'

    def construct(self):
        question = Text('Why four points?', font_size=44).to_edge(UP, buff=0.5)
        self.play(Write(question))
        self.hold_until(0.05)

        # [V4.4a] a quadratic: one handle sets both end directions, and it bends only one way
        a0, a1 = LEFT * 3.5 + DOWN * 1.5, RIGHT * 3.5 + DOWN * 1.5
        handle = Dot(UP * 2, color=GREY_B, radius=0.08)

        def quadratic_view():
            h = handle.get_center()
            curve = ParametricFunction(bezier(np.array([a0, h, a1])), t_range=[0, 1, 0.01], color=OBJECT, stroke_width=6)
            return VGroup(curve, DashedLine(a0, h, color=GREY_B, stroke_width=2), DashedLine(a1, h, color=GREY_B, stroke_width=2))

        quadratic = always_redraw(quadratic_view)
        ends = VGroup(Dot(a0, color=FOCUS, radius=0.12), Dot(a1, color=FOCUS, radius=0.12))
        tag = Text('quadratic: 3 points, 1 handle', font_size=28, color=GREY_A).next_to(question, DOWN, buff=0.3)
        self.play(Transform(question, tag), Create(quadratic), FadeIn(ends), FadeIn(handle))
        self.play(handle.animate.move_to(LEFT * 2 + UP * 2.6), run_time=2)
        both = Text('both ends swing together', font_size=26, color=FOCUS).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(both))
        self.play(handle.animate.move_to(RIGHT * 2.5 + UP * 1.5), run_time=2)
        self.hold_until(0.17)
        self.play(handle.animate.move_to(DOWN * 3.2 + RIGHT * 0.5), run_time=2.5)
        one_way = Text('an S shape? it only ever bends one way', font_size=26, color=WARNING).move_to(both)
        self.play(ReplacementTransform(both, one_way))
        self.hold_until(0.28)

        # [V4.4b] a cubic: two handles, each end independent, and an S forms easily
        self.play(FadeOut(VGroup(quadratic, handle, one_way)))
        self.remove(quadratic)
        h0, h1 = Dot(LEFT * 1.5 + UP * 2, color=GREY_B, radius=0.08), Dot(RIGHT * 1.5 + UP * 2, color=GREY_B, radius=0.08)
        cubic = always_redraw(lambda: VGroup(
            CubicBezier(a0, h0.get_center(), h1.get_center(), a1, color=AFTER, stroke_width=6),
            DashedLine(a0, h0.get_center(), color=GREY_B, stroke_width=2), DashedLine(a1, h1.get_center(), color=GREY_B, stroke_width=2)))
        self.play(Transform(question, Text('cubic: 4 points, 2 handles', font_size=28, color=GREY_A).move_to(question)),
                  Create(cubic), FadeIn(h0), FadeIn(h1))
        self.play(h0.animate.move_to(LEFT * 3.5 + UP * 2.5), run_time=1.5)
        self.play(h1.animate.move_to(RIGHT * 4.5 + UP * 0.5), run_time=1.5)
        independent = Text('each end chooses its own direction', font_size=26, color=AFTER).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(independent))
        self.play(h0.animate.move_to(LEFT * 1 + UP * 3.2), h1.animate.move_to(RIGHT * 1 + DOWN * 2.7), run_time=2.5)
        s_shape = Text('an S, in one piece', font_size=26, color=AFTER).move_to(independent)
        self.play(ReplacementTransform(independent, s_shape))
        self.hold_until(0.5)

        # [V4.4c] six control points: moving one ripples the whole curve
        self.play(FadeOut(VGroup(cubic, h0, h1, s_shape, ends)))
        self.remove(cubic)
        xs = np.linspace(-5.5, 5.5, 6)
        controls = [Dot([x, y, 0], color=GREY_B, radius=0.08) for x, y in zip(xs, (-1.8, 1.4, -1.2, 1.9, -0.8, -1.8))]
        quintic = always_redraw(lambda: ParametricFunction(bezier(np.array([d.get_center() for d in controls])), t_range=[0, 1, 0.01],
                                                           color=PURPLE_B, stroke_width=6))
        polygon = always_redraw(lambda: VGroup(*[DashedLine(controls[i].get_center(), controls[i + 1].get_center(), color=GREY_D,
                                                            stroke_width=2) for i in range(5)]))
        self.play(Transform(question, Text('degree 5: 6 control points', font_size=28, color=GREY_A).move_to(question)),
                  Create(quintic), FadeIn(polygon), *[FadeIn(d) for d in controls])
        ghost = quintic.copy().clear_updaters().set_stroke(opacity=0.3)
        self.add(ghost)
        self.play(controls[1].animate.shift(UP * 1.2 + LEFT * 0.4), run_time=2)
        ripple = Text('more points, less local control', font_size=26, color=PURPLE_B).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(ripple))
        self.hold_until(0.64)

        # [V4.4d] a chain of cubics: moving a joint's handles changes only its two pieces
        self.play(FadeOut(VGroup(quintic, polygon, ghost, ripple, *controls)))
        self.remove(quintic, polygon)
        chain_points = VMobject().set_points_smoothly([LEFT * 6 + DOWN * 1, LEFT * 3 + UP * 1.5, ORIGIN + DOWN * 0.5, RIGHT * 3 + UP * 1.5,
                                                       RIGHT * 6 + DOWN * 1]).get_points()
        pieces = [chain_points[i:i + 4].copy() for i in range(0, len(chain_points), 4)]
        lift = ValueTracker(0)

        def chain():
            moved = [p.copy() for p in pieces]
            moved[1][2] += UP * lift.get_value()      # the handles on either side of the middle joint
            moved[2][1] -= UP * lift.get_value()
            curves = VGroup(*[CubicBezier(*p, color=(OBJECT, AFTER, AFTER, OBJECT)[k] if lift.get_value() > 0.01 else OBJECT,
                                          stroke_width=6) for k, p in enumerate(moved)])
            sticks = VGroup(Line(moved[1][2], moved[1][3], color=GREY_B, stroke_width=2), Line(moved[2][0], moved[2][1], color=GREY_B, stroke_width=2),
                            Dot(moved[1][2], radius=0.07, color=GREY_B), Dot(moved[2][1], radius=0.07, color=GREY_B))
            joints = VGroup(*[Dot(p[0], radius=0.09, color=FOCUS) for p in moved], Dot(moved[-1][3], radius=0.09, color=FOCUS))
            return VGroup(curves, sticks, joints)

        live = always_redraw(chain)
        self.play(Transform(question, Text('a chain of cubic pieces', font_size=28, color=GREY_A).move_to(question)), FadeIn(live))
        before = live.copy().clear_updaters()
        before[0].set_stroke(opacity=0.25)
        self.add(before[0])
        self.play(lift.animate.set_value(1.6), run_time=2)
        local = Text('only the neighbouring pieces change', font_size=26, color=AFTER).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(local))
        self.hold_until(0.76)

        # [V4.4e] quadratic pieces convert exactly into cubic ones
        self.play(FadeOut(VGroup(live, before[0], local)))
        self.remove(live)
        q = [LEFT * 4 + DOWN * 1.5, UP * 1.9 + LEFT * 1, RIGHT * 4 + DOWN * 1.5]
        c = [q[0], q[0] + 2 / 3 * (q[1] - q[0]), q[2] + 2 / 3 * (q[1] - q[2]), q[2]]
        quad = ParametricFunction(bezier(np.array(q)), t_range=[0, 1, 0.01], color=OBJECT, stroke_width=10)
        quad_controls = control_polygon(q)
        cubic_twin = CubicBezier(*c, color=FOCUS, stroke_width=4)
        cubic_controls = VGroup(*[Line(c[i], c[i + 1], color=FOCUS, stroke_width=2) for i in range(3)],
                                *[Dot(p, color=FOCUS, radius=0.07) for p in c])
        self.play(Transform(question, Text('some fonts use quadratic pieces', font_size=28, color=GREY_A).move_to(question)),
                  Create(quad), FadeIn(quad_controls))
        self.wait(1)
        self.play(Create(cubic_twin), FadeIn(cubic_controls), run_time=2)
        exact = Text('the same curve, rewritten exactly as a cubic', font_size=26, color=FOCUS).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(exact))
        self.finish()


class Segment_4_5(Segment):
    """Every outline is a list of points."""
    EPISODE, SEGMENT = 4, '4.5'

    def construct(self):
        # [V4.5a] a square and its sixteen points, read in groups of four
        square = Square(3, color=OBJECT, stroke_width=6).shift(LEFT * 3.6)
        points = Square(3).get_points()
        rows = VGroup()
        for i, p in enumerate(points):
            role = ('anchor', 'handle', 'handle', 'anchor')[i % 4]
            row = VGroup(code_text(f'[{p[0]:5.2f}, {p[1]:5.2f}]', 20, GREY_A),
                         Text(role, font_size=18, color=FOCUS if role == 'anchor' else GREY_B))
            row.arrange(RIGHT, buff=0.3)
            rows.add(row)
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        for k in range(1, 4):
            rows[4 * k:].shift(DOWN * 0.18)
        rows.move_to(RIGHT * 2.8)
        brackets = VGroup(*[Brace(rows[4 * k:4 * k + 4], LEFT, buff=0.1, color=GREY_B) for k in range(4)])
        heading = Text('VMobject: a list of points, read in fours', font_size=30).to_corner(UL, buff=0.4)
        self.play(FadeIn(heading), Create(square))
        self.play(LaggedStart(*[FadeIn(r) for r in rows], lag_ratio=0.05), FadeIn(brackets), run_time=2)
        drawn = square.get_points()
        edges = [Line(drawn[4 * k], drawn[4 * k + 3], color=FOCUS, stroke_width=10) for k in range(4)]
        for k in range(4):
            box = SurroundingRectangle(rows[4 * k:4 * k + 4], color=FOCUS, buff=0.06)
            self.play(Create(edges[k]), Create(box), run_time=0.6)
            self.wait(0.9)
            self.play(FadeOut(edges[k]), FadeOut(box), run_time=0.4)
        count = Text('Square: 4 curves, 16 points', font_size=28, color=FOCUS).next_to(square, DOWN, buff=0.5)
        self.play(FadeIn(count))
        self.hold_until(0.32)

        # [V4.5b] a straight edge keeps its handles on the edge, at a third and two thirds
        top = drawn[0:4]
        handle_dots = VGroup(*[Dot(top[j], color=GREY_A, radius=0.09) for j in (1, 2)])
        anchor_dots = VGroup(*[Dot(top[j], color=FOCUS, radius=0.11) for j in (0, 3)])
        thirds = VGroup(MathTex(r'\tfrac{1}{3}', font_size=34).next_to(top[1], UP, buff=0.2),
                        MathTex(r'\tfrac{2}{3}', font_size=34).next_to(top[2], UP, buff=0.2))
        self.play(FadeIn(anchor_dots, scale=2), FadeIn(handle_dots, scale=2), FadeIn(thirds))
        straight = Text('handles on the line: a perfectly straight cubic', font_size=24, color=GREY_A).next_to(count, DOWN, buff=0.25)
        self.play(FadeIn(straight))
        self.hold_until(0.63)

        # [V4.5c] other shapes, the same kind of thing
        self.play(FadeOut(VGroup(square, rows, brackets, count, handle_dots, anchor_dots, thirds, straight)))
        letter = Text('S', font_size=200, weight=BOLD)[0]
        gallery = [(Triangle(color=AFTER).scale(1.3), 'Triangle'), (Star(color=FOCUS).scale(1.4), 'Star'),
                   (letter.set_fill(opacity=0).set_stroke(GREY_A, 3), 'the letter S')]
        shown = VGroup()
        for k, (shape, name) in enumerate(gallery):
            shape.move_to([(-4.5, 0, 4.5)[k], 0.3, 0])
            dots, _ = anchors_and_handles(shape, anchor_radius=0.06)
            n = len(shape.get_points()) // 4
            label = Text(f'{name}: {n} curves', font_size=26, color=SCAFFOLD).next_to(shape, DOWN, buff=0.45)
            label.move_to([shape.get_x(), -2.0, 0])
            self.play(Create(shape), FadeIn(dots), FadeIn(label), run_time=1.2)
            shown.add(shape, dots, label)
            self.wait(0.6)

        # [V4.5d] one representation for everything
        summary = Text('VMobject = vectorised mobject = list of cubic curves', font_size=32, color=FOCUS).to_edge(DOWN, buff=0.5)
        self.play(Write(summary))
        self.finish()
