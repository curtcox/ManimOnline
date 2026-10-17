"""Episode 2 · Mobjects: the nouns. One Scene per script segment.

    python3 video-series/production/render.py 2 [-ql] [segment ...]

Shot ids in comments ([V2.2c] ...) refer to episodes/02-mobjects-the-nouns.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403

def ruler(length, ticks, vertical=False):
    line = Line(LEFT * length / 2, RIGHT * length / 2, color=GREY_B, stroke_width=3)
    marks = VGroup(*[Line(UP * 0.12, DOWN * 0.12, color=GREY_B, stroke_width=2).move_to(line.point_from_proportion(k / ticks))
                     for k in range(ticks + 1)])
    group = VGroup(line, marks)
    return group.rotate(PI / 2) if vertical else group


class Segment_2_1(Segment):
    """Cold open: where is (3, -1)?"""
    EPISODE, SEGMENT = 2, '2.1'

    def construct(self):
        # [V2.1a] a dot, and a question
        dot = Dot([3, -1, 0], color=FOCUS, radius=0.12)
        question = Text('Where is this dot?', font_size=40).to_edge(UP, buff=0.6)
        self.play(FadeIn(dot, scale=3))
        self.play(Write(question))
        self.hold_until(0.3)

        # [V2.1b] words are vague; rulers arrive
        vague = Text('"a bit right, a little below the middle"', font_size=30, color=SCAFFOLD).next_to(question, DOWN)
        self.play(FadeIn(vague))
        bottom = ruler(14, 14).to_edge(DOWN, buff=0.2)
        side = ruler(8, 8, vertical=True).to_edge(LEFT, buff=0.2)
        self.play(FadeIn(bottom, shift=UP * 0.5), FadeIn(side, shift=RIGHT * 0.5))
        self.hold_until(0.62)

        # [V2.1c] the rulers become a grid; the dot is at (3, -1)
        plane = NumberPlane(background_line_style={'stroke_opacity': 0.5})
        self.play(FadeOut(VGroup(bottom, side, vague)), Create(plane), run_time=2)
        self.bring_to_front(dot)
        origin = Dot(ORIGIN, color=WHITE)
        origin_label = Text('origin', font_size=26).next_to(origin, UL, buff=0.1).add_background_rectangle()
        self.play(FadeIn(origin), FadeIn(origin_label))
        right = Arrow(ORIGIN, RIGHT * 3, buff=0, color=OBJECT)
        down = Arrow(RIGHT * 3, [3, -1, 0], buff=0, color=OBJECT, max_tip_length_to_length_ratio=0.35)
        self.play(GrowArrow(right))
        self.play(GrowArrow(down))
        label = MathTex('(3,\\,-1)', font_size=48, color=FOCUS).next_to(dot, DR, buff=0.1).add_background_rectangle()
        self.play(Write(label))
        self.finish()


class Segment_2_2(Segment):
    """Manim's coordinate plane."""
    EPISODE, SEGMENT = 2, '2.2'

    def construct(self):
        plane = NumberPlane(background_line_style={'stroke_opacity': 0.35})
        self.add(plane)

        # [V2.2a] the frame's size
        height = DoubleArrow(DOWN * 4, UP * 4, buff=0, color=FOCUS).shift(LEFT * 6.6)
        width = DoubleArrow(LEFT * 7.1, RIGHT * 7.1, buff=0, color=FOCUS).shift(DOWN * 3.6)
        h_label = Text('8 units', font_size=30, color=FOCUS).next_to(height, RIGHT).add_background_rectangle()
        w_label = Text('about 14.2 units', font_size=30, color=FOCUS).next_to(width, UP).add_background_rectangle()
        self.play(GrowFromCenter(height), FadeIn(h_label))
        self.play(GrowFromCenter(width), FadeIn(w_label))
        self.hold_until(0.22)

        # [V2.2b] direction constants
        self.play(FadeOut(VGroup(height, width, h_label, w_label)))
        names = {'UP': UP, 'DOWN': DOWN, 'LEFT': LEFT, 'RIGHT': RIGHT}
        arrows = VGroup(*[Arrow(ORIGIN, v, buff=0, color=AFTER, stroke_width=6) for v in names.values()])
        tags = VGroup(*[code_text(n, 24, AFTER).next_to(v * 1.0, v, buff=0.15).add_background_rectangle()
                        for n, v in names.items()])
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.2), FadeIn(tags))
        full = code_text('RIGHT = [1, 0, 0]', 28, AFTER).next_to(tags[3], DOWN, buff=0.3).shift(RIGHT * 0.6)
        full.add_background_rectangle()
        self.play(TransformFromCopy(tags[3], full))
        self.hold_until(0.44)

        # [V2.2c] vector arithmetic as walking directions
        self.play(FadeOut(VGroup(arrows, tags, full)))
        walker = Dot(ORIGIN, color=FOCUS, radius=0.12)
        expression = VGroup(code_text('RIGHT * 3', 32), code_text('+ DOWN', 32), code_text('= [3, -1, 0]', 32, FOCUS))
        expression.arrange(RIGHT, buff=0.25).to_edge(UP, buff=0.5)
        backing = BackgroundRectangle(expression, buff=0.15)
        self.play(FadeIn(walker), FadeIn(backing))
        steps = VGroup()
        for k in range(3):
            step = Arrow(RIGHT * k, RIGHT * (k + 1), buff=0, color=AFTER)
            steps.add(step)
            self.play(GrowArrow(step), walker.animate.move_to(RIGHT * (k + 1)), run_time=0.6)
        self.play(Write(expression[0]))
        last = Arrow(RIGHT * 3, [3, -1, 0], buff=0, color=OBJECT)
        self.play(GrowArrow(last), walker.animate.move_to([3, -1, 0]), Write(expression[1]))
        self.play(Write(expression[2]))
        qr = qr_card('q02-01')
        self.play(FadeIn(qr))
        self.hold_until(0.68)

        # [V2.2d] diagonals
        self.play(FadeOut(qr), FadeOut(VGroup(steps, last, walker, expression, backing)))
        diagonals = {'UR': UR, 'UL': UL, 'DR': DR, 'DL': DL}
        diag = VGroup(*[Arrow(ORIGIN, v, buff=0, color=PURPLE_B) for v in diagonals.values()])
        diag_tags = VGroup(*[code_text(n, 24, PURPLE_B).next_to(v, v, buff=0.1).add_background_rectangle()
                             for n, v in diagonals.items()])
        self.play(LaggedStart(*[GrowArrow(a) for a in diag], lag_ratio=0.15), FadeIn(diag_tags))
        self.hold_until(0.77)

        # [V2.2e] a hint of depth: tilt the plane to show OUT, then flatten again
        self.play(FadeOut(VGroup(diag, diag_tags)))
        tilt = [[1, 0.35], [0, 0.45]]
        out = Arrow(ORIGIN, DL * 1.6 + DOWN * 0.4, buff=0, color=WARNING, stroke_width=6)
        out_tag = code_text('OUT = [0, 0, 1]', 26, WARNING).next_to(out.get_end(), DOWN, buff=0.15).add_background_rectangle()
        self.play(ApplyMatrix(tilt, plane), run_time=1.5)
        self.play(GrowArrow(out), FadeIn(out_tag))
        self.wait(1.5)
        self.play(FadeOut(VGroup(out, out_tag)))
        self.play(ApplyMatrix(np.linalg.inv(tilt), plane), run_time=1.5)
        self.hold_until(0.95)
        self.play(FadeIn(qr_card('q02-01')))
        self.finish()


class Segment_2_3(Segment):
    """A zoo of shapes."""
    EPISODE, SEGMENT = 2, '2.3'

    def construct(self):
        zoo = [
            (Circle(color=BLUE), 'Circle()'),
            (Square(color=YELLOW), 'Square()'),
            (Rectangle(width=4, height=2, color=GREEN), 'Rectangle(width=4, height=2)'),
            (Triangle(color=RED), 'Triangle()'),
            (RegularPolygon(6, color=PURPLE), 'RegularPolygon(6)'),
            (Star(color=ORANGE), 'Star()'),
            (Line(LEFT, RIGHT, color=TEAL), 'Line(LEFT, RIGHT)'),
            (Arrow(LEFT, RIGHT, color=PINK), 'Arrow(LEFT, RIGHT)'),
            (Dot(color=WHITE), 'Dot()'),
        ]
        cells = VGroup()
        for k, (shape, call) in enumerate(zoo):
            x, y = (-4.6, 0, 4.6)[k % 3], (2.25, 0, -2.25)[k // 3]
            shape.scale(0.75).move_to([x, y + 0.3, 0])
            label = code_text(call, 22, SCAFFOLD).move_to([x, y - 0.8, 0])
            if label.width > 4.0:
                label.scale_to_fit_width(4.0)
            cells.add(VGroup(shape, label))
        for cell in cells:
            self.play(FadeIn(cell[0], scale=0.6), FadeIn(cell[1]), run_time=0.7)
        self.hold_until(0.33)

        # [V2.3b] the defaults: radius 1, side 2
        circle, square = cells[0][0], cells[1][0]
        radius = Line(circle.get_center(), circle.get_right(), color=FOCUS, stroke_width=4)
        r_tag = Text('radius 1', font_size=24, color=FOCUS).next_to(circle, LEFT, buff=0.25)
        side = BraceBetweenPoints(square.get_corner(UL), square.get_corner(DL), LEFT, buff=0.08, color=FOCUS)
        s_tag = Text('side 2', font_size=24, color=FOCUS).next_to(side, LEFT, buff=0.1)
        self.play(Create(radius), FadeIn(r_tag))
        self.play(GrowFromCenter(side), FadeIn(s_tag))
        centre = VGroup(*[Dot(c[0].get_center(), radius=0.04, color=FOCUS) for c in cells])
        self.play(LaggedStart(*[FadeIn(d, scale=3) for d in centre], lag_ratio=0.08))
        self.hold_until(0.6)
        bigger = Text('Circle(radius=2)   Square(side_length=3)   RegularPolygon(6)', font=MONO, font_size=22, color=AFTER)
        bigger.to_edge(DOWN, buff=0.3)
        self.play(FadeIn(bigger, shift=UP * 0.2))
        self.hold_until(0.8)

        # [V2.3c] every one is an outline made of curves
        self.play(FadeOut(VGroup(radius, r_tag, side, s_tag, centre, bigger)))
        outlines = VGroup(*[c[0].copy().set_fill(opacity=0).set_stroke(FOCUS, 3) for c in cells])
        self.play(LaggedStart(*[ShowPassingFlash(o, time_width=0.4) for o in outlines], lag_ratio=0.1), run_time=3)
        self.finish()


class Segment_2_4(Segment):
    """Stroke, fill and opacity."""
    EPISODE, SEGMENT = 2, '2.4'

    def construct(self):
        # [V2.4a] two layers of paint
        stroke_width = ValueTracker(6)
        fill_opacity = ValueTracker(0.5)
        hue = ValueTracker(0)
        palette = [BLUE, TEAL, GREEN, YELLOW, ORANGE, RED, PURPLE]

        def paint():
            colour = interpolate_color(ManimColor(palette[int(hue.get_value()) % len(palette)]),
                                       ManimColor(palette[(int(hue.get_value()) + 1) % len(palette)]),
                                       hue.get_value() % 1)
            return Circle(radius=1.8).move_to(LEFT * 3.5).set_stroke(WHITE, stroke_width.get_value()) \
                .set_fill(colour, fill_opacity.get_value())

        disc = always_redraw(paint)
        stroke_tag = Text('stroke', font_size=30).move_to(LEFT * 3.5 + UP * 2.4)
        stroke_arrow = Arrow(stroke_tag.get_bottom(), LEFT * 3.5 + UP * 1.85, buff=0.05, color=GREY_A)
        fill_tag = Text('fill', font_size=30).move_to(LEFT * 3.5)
        self.play(FadeIn(disc))
        self.play(FadeIn(stroke_tag), GrowArrow(stroke_arrow), FadeIn(fill_tag))

        # [V2.4b] four controls
        def slider(name, low, high, tracker, y, decimals=1):
            line = NumberLine(x_range=[low, high, (high - low) / 4], length=4, include_numbers=False, color=GREY_B)
            line.move_to(RIGHT * 3 + UP * y)
            title = Text(name, font_size=24).next_to(line, UP, buff=0.15).align_to(line, LEFT)
            knob = always_redraw(lambda: Dot(line.n2p(tracker.get_value()), color=FOCUS, radius=0.11))
            value = always_redraw(lambda: DecimalNumber(tracker.get_value(), num_decimal_places=decimals, font_size=24)
                                  .next_to(line, RIGHT, buff=0.3))
            return VGroup(line, title, knob, value)

        controls = VGroup(slider('stroke width', 0, 12, stroke_width, 1.6),
                          slider('fill colour', 0, 6, hue, 0.2, decimals=0),
                          slider('fill opacity', 0, 1, fill_opacity, -1.2, decimals=2))
        self.play(FadeIn(controls))
        self.play(stroke_width.animate.set_value(12), run_time=1.5)
        self.play(stroke_width.animate.set_value(2), run_time=1.5)
        self.play(hue.animate.set_value(5), run_time=3, rate_func=linear)
        self.play(fill_opacity.animate.set_value(1), run_time=1.2)
        self.play(fill_opacity.animate.set_value(0), run_time=1.5)
        self.hold_until(0.3)

        # most shapes start as outlines: fill opacity 0
        default = Text('default: fill opacity 0', font_size=28, color=FOCUS).next_to(controls, DOWN, buff=0.5)
        self.play(Indicate(controls[2][0], color=FOCUS), FadeIn(default))
        self.hold_until(0.48)

        # [V2.4c] the q02-02 row: outline only, fill only, both
        self.play(FadeOut(VGroup(disc, stroke_tag, stroke_arrow, fill_tag, controls, default)))
        row = VGroup(
            Circle().set_stroke(BLUE, width=8),
            Square().set_fill(GREEN, opacity=1).set_stroke(width=0),
            Triangle().set_fill(RED, opacity=0.4).set_stroke(YELLOW, width=4),
            RegularPolygon(6).set_fill(PURPLE, opacity=0.7).set_stroke(WHITE, width=2),
        ).arrange(RIGHT, buff=0.7).shift(UP * 1.2 + LEFT * 1.2)
        captions = VGroup(*[Text(t, font_size=24, color=SCAFFOLD).next_to(m, DOWN, buff=0.3)
                            for t, m in zip(('outline only', 'fill only', 'both', 'both'), row)])
        self.play(LaggedStart(*[Create(s) for s in row], lag_ratio=0.3), FadeIn(captions))
        qr = qr_card('q02-02')
        self.play(FadeIn(qr))
        self.play(row[0].animate.set_fill(BLUE, opacity=0.5))
        self.play(row[1].animate.set_color('#FF8800'))
        hexcode = code_text('"#FF8800"', 24, '#FF8800').next_to(captions[1], DOWN, buff=0.15)
        self.play(FadeIn(hexcode))
        self.hold_until(0.72)

        # [V2.4d] chaining: each call hands back the same square
        self.play(FadeOut(VGroup(row, captions, hexcode, qr)))
        links = VGroup(code_text('Square()', 30, OBJECT), code_text('.set_fill(GREEN, opacity=1)', 30),
                       code_text('.set_stroke(width=0)', 30)).arrange(RIGHT, buff=0.05).move_to(UP * 0.6)
        if links.width > 13:
            links.scale_to_fit_width(13)
        self.play(Write(links[0]))
        square = Square(color=WHITE).scale(0.6).next_to(links, DOWN, buff=1.2).align_to(links[0], LEFT)
        self.play(FadeIn(square))
        for link, change in ((links[1], lambda m: m.set_fill(GREEN, opacity=1)), (links[2], lambda m: m.set_stroke(width=0))):
            hop = CurvedArrow(square.get_top() + UP * 0.1, link.get_bottom() + DOWN * 0.1, color=FOCUS, angle=-PI / 3)
            self.play(Write(link), Create(hop))
            self.play(change(square.animate.next_to(link, DOWN, buff=1.2)), FadeOut(hop))
        same = Text('the same square, all the way along', font_size=28, color=FOCUS).to_edge(DOWN, buff=0.8)
        self.play(FadeIn(same))
        self.finish()


def verb_tag(verb, meaning):
    """The method name, large, with its one-word meaning (top-left)."""
    tag = VGroup(code_text(verb, 40, FOCUS), Text(meaning, font_size=30, color=SCAFFOLD))
    return tag.arrange(RIGHT, buff=0.35, aligned_edge=DOWN).to_corner(UL, buff=0.4)


def code_caption(source):
    line = code_text(source, 26)
    return VGroup(BackgroundRectangle(line, buff=0.12, fill_opacity=0.9), line).to_edge(DOWN, buff=0.35).shift(LEFT * 1.6)


def dashed_box(mob, color=SCAFFOLD):
    return DashedVMobject(SurroundingRectangle(mob, buff=0, color=color, stroke_width=2), num_dashes=24)


class Segment_2_5(Segment):
    """Putting things in their place."""
    EPISODE, SEGMENT = 2, '2.5'

    def construct(self):
        box = Square(1.5, color=BLUE)
        dot = Dot(color=FOCUS, radius=0.14)
        self.play(Create(box), FadeIn(dot))
        qr = qr_card('q02-03')
        self.play(FadeIn(qr))
        self.hold_until(0.11)

        def step(verb, meaning, source, previous=None):
            tag, caption = verb_tag(verb, meaning), code_caption(source)
            if previous:
                self.play(ReplacementTransform(previous[0], tag), ReplacementTransform(previous[1], caption))
            else:
                self.play(FadeIn(tag), FadeIn(caption))
            return tag, caption

        # [V2.5b] shift: by an offset
        current = step('shift', 'by', 'dot.animate.shift(RIGHT * 3)')
        ghost = dot.copy().set_opacity(0.3)
        offset = Arrow(dot.get_center(), RIGHT * 3, buff=0.15, color=GREY_A)
        self.add(ghost)
        self.play(dot.animate.shift(RIGHT * 3), GrowArrow(offset), run_time=2)
        self.play(FadeOut(qr))
        self.play(FadeOut(VGroup(ghost, offset)))

        # move_to: to a point
        current = step('move_to', 'to', 'dot.animate.move_to(UP * 2 + LEFT * 4)', current)
        target = UP * 2 + LEFT * 4
        cross = VGroup(Line(LEFT * 0.3, RIGHT * 0.3), Line(DOWN * 0.3, UP * 0.3), Circle(radius=0.22)).set_stroke(GREY_A, 2).move_to(target)
        self.play(Create(cross))
        self.play(dot.animate.move_to(target), run_time=2)
        self.play(FadeOut(cross))
        self.hold_until(0.24)

        # [V2.5c] next_to: beside another object, with a buffer
        current = step('next_to', 'beside', 'dot.animate.next_to(box, DOWN, buff=0.3)', current)
        box_bounds = dashed_box(box)
        self.play(Create(box_bounds))
        self.play(dot.animate.next_to(box, DOWN, buff=0.3), run_time=2)
        dot_bounds = dashed_box(dot)
        gap = BraceBetweenPoints(box.get_bottom() + RIGHT * 0.6, dot.get_top() + RIGHT * 0.6, RIGHT, buff=0.05,
                                 color=FOCUS)
        gap_tag = code_text('buff=0.3', 22, FOCUS).next_to(gap, RIGHT, buff=0.1)
        self.play(Create(dot_bounds), GrowFromCenter(gap), FadeIn(gap_tag))
        bound_note = Text('bounding boxes', font_size=26, color=SCAFFOLD).next_to(box, LEFT, buff=0.4)
        self.play(FadeIn(bound_note))
        self.hold_until(0.5)
        self.play(FadeOut(VGroup(box_bounds, dot_bounds, gap, gap_tag, bound_note)))

        # to_corner: against the frame, with a margin
        current = step('to_corner', 'edge', 'dot.animate.to_corner(UR)', current)
        margin = DashedVMobject(Rectangle(width=config.frame_width - 1, height=config.frame_height - 1), num_dashes=90)
        margin.set_stroke(GREY_D, 2)
        self.play(Create(margin))
        self.play(dot.animate.to_corner(UR), run_time=2)
        self.play(FadeOut(margin))

        # [V2.5d] align_to: line up one edge
        current = step('align_to', 'line up', 'box.animate.align_to(dot, UP)', current)
        guide = DashedLine(LEFT * 7 + UP * dot.get_top()[1], RIGHT * 7 + UP * dot.get_top()[1], color=FOCUS)
        self.play(Create(guide))
        self.play(box.animate.align_to(dot, UP), run_time=2)
        self.play(FadeOut(guide))
        self.hold_until(0.63)

        # .animate: jump versus glide
        self.play(FadeOut(VGroup(*current, box, dot)))
        jump, glide = Dot(LEFT * 5 + UP * 0.8, color=FOCUS, radius=0.14), Dot(LEFT * 5 + DOWN * 1.2, color=FOCUS, radius=0.14)
        jump_code = code_text('dot.shift(RIGHT * 6)', 28).next_to(jump, UP, buff=0.3).align_to(jump, LEFT)
        glide_code = code_text('self.play(dot.animate.shift(RIGHT * 6))', 28).next_to(glide, UP, buff=0.3).align_to(glide, LEFT)
        self.play(FadeIn(VGroup(jump, glide, jump_code, glide_code)))
        self.wait(0.5)
        jump.shift(RIGHT * 6)
        self.wait(0.5)
        self.play(glide.animate.shift(RIGHT * 6), run_time=2)
        tags = VGroup(Text('jumps', font_size=28, color=WARNING).next_to(jump, RIGHT),
                      Text('glides', font_size=28, color=AFTER).next_to(glide, RIGHT))
        self.play(FadeIn(tags))
        self.hold_until(0.8)

        # relative positions survive later moves
        self.play(FadeOut(VGroup(jump, glide, jump_code, glide_code, tags)))
        shape = Square(1.5, color=BLUE).move_to(LEFT * 3)
        label = Text('next_to', font_size=26, color=AFTER).next_to(shape, UP)
        label.add_updater(lambda m: m.next_to(shape, UP))
        fixed = Text('move_to', font_size=26, color=WARNING).move_to(shape.get_top() + UP * 1.1)
        self.play(Create(shape), FadeIn(label), FadeIn(fixed))
        self.play(shape.animate.move_to(RIGHT * 3 + DOWN * 1.5), run_time=2.5)
        self.finish()


class Segment_2_6(Segment):
    """Scale, rotate and measure."""
    EPISODE, SEGMENT = 2, '2.6'

    def construct(self):
        home = LEFT * 3
        square = Square(color=BLUE).move_to(home)
        self.play(Create(square))

        # [V2.6a] scale and rotate about the centre
        ghost = square.copy().set_stroke(opacity=0.3)
        self.add(ghost)
        call = code_caption('square.scale(2)')
        self.play(FadeIn(call), square.animate.scale(2), run_time=1.5)
        self.play(Transform(call, code_caption('square.rotate(PI / 4)')),
                  Rotate(square, PI / 4), run_time=1.5)
        self.wait(0.5)
        self.play(FadeOut(ghost), square.animate.become(Square(color=BLUE).move_to(home)))

        # [V2.6b] about_edge pins a corner
        pin = Dot(square.get_corner(DL), color=WARNING, radius=0.1)
        self.play(Transform(call, code_caption('square.scale(2, about_edge=DL)')), FadeIn(pin, scale=3))
        self.play(square.animate.scale(2, about_edge=DL), run_time=1.5)
        self.play(square.animate.scale(0.5, about_edge=DL), run_time=1.5)
        self.play(FadeOut(pin))
        self.hold_until(0.38)

        # radians and DEGREES
        dial = Circle(radius=1.4, color=GREY_D).move_to(RIGHT * 3.6)
        arm0 = Line(dial.get_center(), dial.get_center() + RIGHT * 1.4, color=GREY_A)
        arm = arm0.copy().set_color(FOCUS)
        angle = always_redraw(lambda: Arc(radius=0.5, start_angle=0, angle=arm.get_angle() % TAU,
                                          arc_center=dial.get_center(), color=FOCUS))
        self.play(Create(dial), Create(arm0), Create(arm), FadeIn(angle))
        self.play(Rotate(arm, PI / 4, about_point=dial.get_center()))
        equal = VGroup(code_text('PI / 4', 30, FOCUS), Text('=', font_size=30), code_text('45 * DEGREES', 30, FOCUS))
        equal.arrange(RIGHT, buff=0.25).next_to(dial, DOWN, buff=0.4)
        self.play(Write(equal))
        self.play(Rotate(arm, TAU - PI / 4 - 0.001, about_point=dial.get_center()), run_time=2)
        full = code_text('TAU = 2 * PI = a full turn', 26, GREY_A).next_to(equal, DOWN, buff=0.25)
        self.play(FadeIn(full))
        self.hold_until(0.62)

        # [V2.6c] asking where the parts are
        self.play(FadeOut(VGroup(dial, arm0, arm, angle, equal, full, call)))
        self.play(square.animate.scale(1.5).move_to(LEFT * 1.5))
        points = [('get_center()', square.get_center(), DOWN), ('get_top()', square.get_top(), UP),
                  ('get_right()', square.get_right(), RIGHT), ('get_corner(UR)', square.get_corner(UR), UR)]
        marks = VGroup()
        for name, point, direction in points:
            marker = Dot(point, color=FOCUS)
            tag = code_text(name, 24, FOCUS).next_to(marker, direction, buff=0.15)
            marks.add(VGroup(marker, tag))
            self.play(FadeIn(marker, scale=3), FadeIn(tag), run_time=0.8)
        width = BraceBetweenPoints(square.get_corner(DL), square.get_corner(DR), DOWN, color=GREY_A)
        width_tag = code_text('square.width', 24, GREY_A).next_to(width, DOWN, buff=0.1)
        self.play(GrowFromCenter(width), FadeIn(width_tag))
        self.hold_until(0.82)

        # [V2.6d] next_to is a point on a bounding box, a direction and a buffer
        label = Text('label', font_size=30)
        recipe = VGroup(code_text('get_top()', 26, FOCUS), Text('+', font_size=28), code_text('UP * buff', 26),
                        Text('→ next_to(square, UP)', font_size=26, color=AFTER)).arrange(RIGHT, buff=0.2)
        recipe.to_edge(RIGHT, buff=0.5).shift(UP * 2.8)
        self.play(FadeOut(VGroup(marks[0], marks[2], marks[3], marks[1][1])), Write(recipe))
        self.play(FadeIn(label.next_to(square, UP, buff=0.25), shift=DOWN * 0.3))
        self.finish()


class Segment_2_7(Segment):
    """Groups."""
    EPISODE, SEGMENT = 2, '2.7'

    def construct(self):
        # a VGroup: several objects acting as one
        trio = VGroup(Circle(color=BLUE), Square(color=YELLOW), Triangle(color=RED)).scale(0.6)
        trio[0].move_to(LEFT * 3 + UP * 1), trio[1].move_to(UP * 1.5), trio[2].move_to(RIGHT * 2.5 + DOWN * 0.5)
        self.play(LaggedStart(*[Create(m) for m in trio], lag_ratio=0.2))
        outline = always_redraw(lambda: dashed_box(trio).set_stroke(AFTER))
        name = code_text('VGroup(circle, square, triangle)', 28, AFTER).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(outline), Write(name))
        self.play(trio.animate.shift(LEFT * 1 + DOWN * 1).rotate(0.3), run_time=1.5)
        self.play(trio.animate.set_color(PURPLE), run_time=1)
        self.hold_until(0.27)

        # arrange: rows and columns
        self.play(trio.animate.arrange(RIGHT, buff=0.6).move_to(ORIGIN), run_time=1.5)
        self.play(Transform(name, code_text('trio.arrange(DOWN, buff=0.3)', 28, AFTER).to_edge(DOWN, buff=0.6)))
        self.play(trio.animate.arrange(DOWN, buff=0.3), run_time=1.5)
        self.hold_until(0.45)

        # [V2.7e] twelve dots from one line of Python
        self.play(FadeOut(VGroup(trio, outline, name)))
        code = code_text('Dot(radius=0.15, color=interpolate_color(BLUE, YELLOW, i / 11)) for i in range(12)', 22)
        code.scale_to_fit_width(13).to_edge(UP, buff=0.4)
        ramp = VGroup(*[Square(0.4).set_fill(interpolate_color(BLUE, YELLOW, i / 11), 1).set_stroke(width=0)
                        for i in range(12)]).arrange(RIGHT, buff=0).next_to(code, DOWN, buff=0.25)
        ticks = VGroup(*[Text(f'{i}/11', font_size=14, color=SCAFFOLD).next_to(sq, DOWN, buff=0.05)
                         for i, sq in enumerate(ramp) if i in (0, 5, 11)])
        self.play(FadeIn(code), FadeIn(ramp), FadeIn(ticks))

        # [V2.7a-b] stacked at the origin, then a row, then a grid
        dots = VGroup(*[Dot(radius=0.15, color=interpolate_color(BLUE, YELLOW, i / 11)) for i in range(12)])
        self.play(FadeIn(dots))
        count = Text('12 dots, all at the origin', font_size=26, color=SCAFFOLD).next_to(dots, DOWN, buff=0.4)
        self.play(FadeIn(count))
        self.play(FadeOut(count), dots.animate.arrange(RIGHT, buff=0.4), run_time=1.5)
        qr = qr_card('q02-04')
        self.play(FadeIn(qr))
        self.play(dots.animate.arrange_in_grid(rows=3, buff=0.5), run_time=1.5)
        self.hold_until(0.8)

        # [V2.7c] the group moves as one piece, with its own bounds
        self.play(FadeOut(qr), FadeOut(VGroup(code, ramp, ticks)))
        bounds = always_redraw(lambda: dashed_box(dots).set_stroke(AFTER))
        centre = always_redraw(lambda: Dot(dots.get_center(), color=AFTER, radius=0.06))
        self.play(FadeIn(bounds), FadeIn(centre))
        self.play(dots.animate.scale(1.5).rotate(PI / 6), run_time=2)
        self.play(dots.animate.arrange(DOWN, buff=0.2).to_edge(LEFT), run_time=2)
        self.finish()


class Segment_2_8(Segment):
    """The copy trap."""
    EPISODE, SEGMENT = 2, '2.8'

    def construct(self):
        lines = VGroup(*[code_text(t, 28) for t in
                         ('a = Square(color=BLUE)', 'b = a', 'b.animate.set_color(RED)', 'c = a.copy()')])
        lines.arrange(DOWN, aligned_edge=LEFT, buff=0.2).to_corner(UL, buff=0.4)

        # [V2.8a] a square called a
        square = Square(1.8, color=BLUE).move_to(LEFT * 1 + DOWN * 0.8)
        note_a = sticky_note('a')
        string_a = attach(note_a, square, UL)
        self.play(Write(lines[0]), Create(square))
        self.play(FadeIn(note_a, shift=DOWN * 0.2), FadeIn(string_a))
        question = Text('How many squares?', font_size=34, color=FOCUS).to_edge(RIGHT, buff=0.8).shift(UP * 1.5)
        self.hold_until(0.12)
        self.play(Write(lines[1]))
        self.play(Write(question))
        self.hold_until(0.2)

        # [V2.8b] b = a: a second note on the same square
        note_b = sticky_note('b')
        string_b = attach(note_b, square, UR)
        self.play(FadeIn(note_b, shift=DOWN * 0.2), FadeIn(string_b))
        answer = Text('one', font_size=40, color=AFTER).next_to(question, DOWN, buff=0.3)
        self.play(Write(answer))
        self.hold_until(0.47)

        # [V2.8d] turning b red turns a red: one object, two names
        qr = qr_card('q02-05')
        self.play(Write(lines[2]), FadeIn(qr))
        self.play(square.animate.set_color(RED), run_time=1.5)
        self.play(Wiggle(note_a), Wiggle(note_b))
        self.hold_until(0.72)

        # [V2.8c] c = a.copy(): a genuinely new square
        self.play(Write(lines[3]), FadeOut(VGroup(question, answer)))
        twin = square.copy().clear_updaters()
        note_c = sticky_note('c')
        string_c = attach(note_c, twin, UR)
        self.add(twin)
        self.play(twin.animate.shift(RIGHT * 4).set_color(GREEN), FadeIn(note_c), FadeIn(string_c), run_time=2)
        independent = Text('separate objects', font_size=30, color=AFTER).next_to(VGroup(square, twin), DOWN, buff=0.5)
        self.play(FadeIn(independent))
        self.finish()


def sheet(color, y, x=1.6):
    shape = Polygon([-1.6, -0.35, 0], [1.2, -0.35, 0], [1.8, 0.35, 0], [-1.0, 0.35, 0])
    return shape.set_fill(color, 0.35).set_stroke(color, 3).move_to([x, y, 0])


class Segment_2_9(Segment):
    """Who is on top?"""
    EPISODE, SEGMENT = 2, '2.9'

    def construct(self):
        back = Circle(radius=1.5, color=BLUE, fill_opacity=1).shift(LEFT)
        middle = Square(2.5, color=GREEN, fill_opacity=1)
        front = Triangle(color=RED, fill_opacity=1).scale(1.5).shift(RIGHT)
        shapes = VGroup(back, middle, front)
        shapes.scale(0.8).move_to(LEFT * 4)
        self.play(LaggedStart(*[FadeIn(s) for s in shapes], lag_ratio=0.4))
        front_label = Text('front view', font_size=26, color=SCAFFOLD).next_to(shapes, DOWN, buff=0.5)

        # [V2.9a] side view: one sheet per object, in drawing order (first at the bottom)
        slots = [-1.3, -0.2, 0.9]
        sheets = [sheet(BLUE, slots[0]), sheet(GREEN, slots[1]), sheet(RED, slots[2])]
        side_label = Text('side view', font_size=26, color=SCAFFOLD).move_to([1.6, -2.5, 0])
        first = Text('drawn first', font_size=22, color=SCAFFOLD).next_to(sheets[0], LEFT, buff=0.35)
        last = Text('drawn last', font_size=22, color=SCAFFOLD).next_to(sheets[2], LEFT, buff=0.35)
        qr = qr_card('q02-06')
        self.play(FadeIn(front_label), FadeIn(side_label), LaggedStart(*[FadeIn(s, shift=UP * 0.3) for s in sheets], lag_ratio=0.3),
                  FadeIn(first), FadeIn(last))
        self.play(FadeIn(qr))
        self.hold_until(0.3)

        def restack(order):
            return [s.animate.move_to([1.6, slots[k], 0]) for k, s in enumerate(order)]

        # [V2.9b] the circle's z_index becomes 1: it is drawn last
        z1 = code_text('back.set_z_index(1)', 28, BLUE).move_to([1.6, 2.6, 0])
        self.play(Write(z1))
        self.play(*restack([sheets[1], sheets[2], sheets[0]]), back.animate.set_z_index(1), run_time=2)
        self.hold_until(0.62)

        # [V2.9c] the triangle's z_index becomes 2
        z2 = code_text('front.set_z_index(2)', 28, RED).move_to(z1)
        self.play(FadeOut(qr), ReplacementTransform(z1, z2))
        self.play(*restack([sheets[1], sheets[0], sheets[2]]), front.animate.set_z_index(2), run_time=2)
        self.finish()


class Segment_2_10(Segment):
    """Recap."""
    EPISODE, SEGMENT = 2, '2.10'

    def construct(self):
        # [V2.10a] one tile per idea
        grid = NumberPlane(x_range=[-2, 2], y_range=[-1, 1], x_length=3, y_length=1.6,
                           background_line_style={'stroke_opacity': 0.4})
        grid.add(Arrow(ORIGIN, RIGHT * 0.75, buff=0, color=AFTER), Arrow(ORIGIN, UP * 0.75, buff=0, color=AFTER))
        paint = Circle(radius=0.75).set_stroke(WHITE, 6).set_fill(BLUE, 0.6)
        verbs = VGroup(*[code_text(v, 22) for v in ('shift', 'move_to', 'next_to', 'to_corner', 'align_to')]).arrange(DOWN, buff=0.08)
        group = VGroup(*[Dot(radius=0.1, color=interpolate_color(BLUE, YELLOW, i / 11)) for i in range(12)]).arrange_in_grid(rows=3, buff=0.25)
        group = VGroup(group, dashed_box(group).set_stroke(AFTER))
        one = Square(0.9, color=RED)
        notes = VGroup(sticky_note('a').scale(0.6).next_to(one, UL, buff=0.05), sticky_note('b').scale(0.6).next_to(one, UR, buff=0.05))
        names = VGroup(one, notes)
        layers = VGroup(*[sheet(c, 0).scale(0.55).shift(UP * 0.35 * k) for k, c in enumerate((BLUE, GREEN, RED))])
        tiles = VGroup()
        for art, words in ((grid, 'positions are vectors'), (paint, 'stroke and fill'), (verbs, 'place by offset, point or relation'),
                           (group, 'groups act as one'), (names, 'names are sticky notes'), (layers, 'z_index decides who is on top')):
            art.move_to(ORIGIN)
            caption = Text(words, font_size=22, color=SCAFFOLD).next_to(art, DOWN, buff=0.25)
            tiles.add(VGroup(art, caption))
        for k, tile in enumerate(tiles):
            tile.move_to([(-4.6, 0, 4.6)[k % 3], (1.7, -1.9)[k // 3], 0])
        self.play(LaggedStart(*[FadeIn(t, shift=UP * 0.2) for t in tiles], lag_ratio=0.35), run_time=5)
        self.hold_until(0.6)

        # [V2.10b] the QR wall, 10 seconds
        wall = qr_wall([f'q02-0{i}' for i in range(1, 7)])
        heading = Text('Episode 2 · scan to open each scene', font_size=26, color=SCAFFOLD).to_corner(UL, buff=0.3)
        self.play(FadeOut(tiles), FadeIn(wall), FadeIn(heading))
        self.wait(10)

        # [V2.10c] teaser: five dots racing at different speeds (episode 3)
        self.play(FadeOut(VGroup(wall, heading)))
        racers = VGroup(*[Dot(LEFT * 5 + UP * (1.6 - 0.8 * k), color=FOCUS) for k in range(5)])
        lanes = VGroup(*[Line(LEFT * 5, RIGHT * 5, color=GREY_D).move_to(UP * (1.6 - 0.8 * k)) for k in range(5)])
        self.play(FadeIn(lanes), FadeIn(racers))
        self.play(*[r.animate(rate_func=f).shift(RIGHT * 10) for r, f in
                    zip(racers, (linear, smooth, rush_into, rush_from, there_and_back))], run_time=3)
        nxt = Text('Next: Animations, the verbs', font_size=34).to_edge(DOWN, buff=0.8)
        self.play(Write(nxt))
        self.finish()
