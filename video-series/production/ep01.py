"""Episode 1 · An animation is a program. One Scene per script segment.

    manim -qh video-series/production/ep01.py Segment_1_1      (one segment)
    manim -qh -a video-series/production/ep01.py               (all segments)

Shot ids in comments ([V1.1a] ...) refer to episodes/01-an-animation-is-a-program.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403

PREVIEW_FPS = 15


def square_to_circle_frame(index):
    """Frame `index` of q01-01 as ManimOnline previews it: Create 1 s, Transform 1 s, wait 1 s."""
    square, circle = Square(color=BLUE), Circle(color=YELLOW)
    t = index / PREVIEW_FPS
    if t < 1:
        return square.copy().pointwise_become_partial(square, 0, smooth(t))
    if t < 2:
        square.align_data(circle)
        shape = square.copy()
        return shape.interpolate(square, circle, smooth(t - 1))
    return circle


FRAME_COUNT = 46  # 3 s at 15 fps plus the terminal frame


class Segment_1_1(Segment):
    """Cold open: a square becomes a circle, then we count its frames."""
    EPISODE, SEGMENT = 1, '1.1'

    def construct(self):
        # [V1.1a] exactly q01-01
        square = Square(color=BLUE)
        circle = Circle(color=YELLOW)
        self.play(Create(square))
        self.play(Transform(square, circle))
        self.hold_until(0.16)

        # [V1.1b] rewind, then replay one frame at a time with a counter
        self.play(Transform(square, Square(color=BLUE)), run_time=0.6, rate_func=rush_from)
        self.remove(square)
        index = ValueTracker(0)
        shape = always_redraw(lambda: square_to_circle_frame(int(index.get_value())))
        label = Text('frame', font_size=30, color=SCAFFOLD).to_corner(UL)
        counter = Integer(1, font_size=48).next_to(label, RIGHT, buff=0.25)
        counter.add_updater(lambda m: m.set_value(int(index.get_value()) + 1))
        self.add(shape, label, counter)
        self.play(index.animate.set_value(FRAME_COUNT - 0.01), run_time=0.45 * self.target - self.renderer.time,
                  rate_func=linear)
        self.hold_until(0.5)

        # [V1.1c] the frames fan out into a flipbook strip
        picks = [0, 4, 8, 12, 16, 19, 22, 25, 28, 31, 45]
        thumbs = VGroup()
        for i in picks:
            frame = Rectangle(width=1.05, height=1.05, color=GREY_D, stroke_width=2).set_fill('#0b0d10', 1)
            thumbs.add(VGroup(frame, square_to_circle_frame(i).scale(0.38).move_to(frame),
                              Text(str(i + 1), font_size=16, color=SCAFFOLD).next_to(frame, DOWN, buff=0.08)))
        thumbs.arrange(RIGHT, buff=0.12).move_to(DOWN * 0.3)
        shape.clear_updaters()
        self.play(FadeOut(counter), FadeOut(label),
                  LaggedStart(*[TransformFromCopy(shape, t) for t in thumbs], lag_ratio=0.12),
                  FadeOut(shape), run_time=2.5)
        self.hold_until(0.82)
        question = Text('Who drew all of these?', font_size=40).next_to(thumbs, UP, buff=0.9)
        self.play(Write(question))
        self.finish()


class Segment_1_2(Segment):
    """Describing change instead of drawing it."""
    EPISODE, SEGMENT = 1, '1.2'

    def construct(self):
        # [V1.2a] a key-frame timeline: square at 0 s, circle at 3 s, a question mark between
        axis = NumberLine(x_range=[0, 3, 1], length=8, include_numbers=True, font_size=28).shift(DOWN * 1.5)
        seconds = Text('seconds', font_size=22, color=SCAFFOLD).next_to(axis, RIGHT)
        keys = VGroup()
        for x, mob, name in ((0, Square(color=BLUE), 'key frame'), (3, Circle(color=YELLOW), 'key frame')):
            diamond = Square(0.22).rotate(PI / 4).set_fill(FOCUS, 1).set_stroke(width=0).move_to(axis.n2p(x))
            picture = mob.scale(0.6).next_to(diamond, UP, buff=0.5)
            keys.add(VGroup(diamond, picture, Text(name, font_size=20, color=SCAFFOLD).next_to(diamond, DOWN, buff=0.55)))
        gap = Text('?', font_size=96, color=WARNING).move_to(axis.n2p(1.5) + UP * 1.1)
        self.play(Create(axis), FadeIn(seconds))
        self.play(LaggedStart(*[FadeIn(k, shift=UP * 0.3) for k in keys], lag_ratio=0.4))
        self.play(Write(gap))
        self.hold_until(0.2)

        # paragraph 2: things that must be exact
        timeline = VGroup(axis, seconds, keys, gap)
        self.play(timeline.animate.scale(0.55).to_edge(UP, buff=0.4))
        plot_axes = Axes(x_range=[-2, 2], y_range=[0, 4], x_length=2.6, y_length=2, tips=False)
        graph = plot_axes.plot(lambda x: x * x, color=FOCUS)
        ring = Circle(radius=1, color=SCAFFOLD)
        triangle = Polygon(*[ring.point_at_angle(a) for a in (0.3, 2.4, 4.2)], color=FOCUS)
        equation = MathTex('2x + 3', '=', '11').set_color_by_tex('x', FOCUS)
        exacts = VGroup(VGroup(plot_axes, graph), VGroup(ring, triangle), equation).arrange(RIGHT, buff=1.2).shift(DOWN * 0.8)
        tags = VGroup(*[Text('exactly', font_size=24, color=AFTER).next_to(m, DOWN, buff=0.3) for m in exacts])
        self.play(LaggedStart(*[FadeIn(m) for m in exacts], lag_ratio=0.5), run_time=2)
        self.play(LaggedStart(*[Write(t) for t in tags], lag_ratio=0.3))
        self.hold_until(0.38)
        guess = Text('software guesses the middle', font_size=32, color=WARNING).next_to(timeline, DOWN, buff=0.5)
        cross = Cross(guess, stroke_color=WARNING)
        self.play(FadeOut(VGroup(exacts, tags)), Indicate(gap, color=WARNING), FadeIn(guess, shift=UP * 0.2))
        self.play(Create(cross))
        self.play(FadeOut(VGroup(timeline, guess, cross)))

        # [V1.2c] four sentences that describe the change, lit as their part plays
        sentences = VGroup(*[Text(s, font_size=34) for s in
                             ('Make a square.', 'Draw it.', 'Turn it into a circle.', 'Pause.')])
        sentences.arrange(DOWN, aligned_edge=LEFT, buff=0.45).to_edge(LEFT, buff=1).set_opacity(0.35)
        stage = RIGHT * 3.5
        self.play(FadeIn(sentences))
        self.hold_until(0.45)
        square = Square(color=BLUE).move_to(stage)
        self.play(sentences[0].animate.set_opacity(1), FadeIn(DashedVMobject(square.copy(), num_dashes=24).set_stroke(SCAFFOLD)))
        self.play(sentences[1].animate.set_opacity(1), Create(square))
        self.play(sentences[2].animate.set_opacity(1), Transform(square, Circle(color=YELLOW).move_to(stage)), run_time=1.5)
        self.play(sentences[3].animate.set_opacity(1))
        self.wait(0.8)

        # [V1.2b] how far along are we? a progress slider drives the in-between shape
        self.play(*[FadeOut(m) for m in self.mobjects if m is not sentences], sentences.animate.set_opacity(0.35))
        alpha = ValueTracker(0)
        slider = NumberLine(x_range=[0, 1, 0.25], length=5, include_numbers=True, decimal_number_config={'num_decimal_places': 2},
                            font_size=24).move_to(stage + DOWN * 2.3)
        knob = always_redraw(lambda: Triangle(color=FOCUS, fill_opacity=1).scale(0.12).rotate(PI)
                             .next_to(slider.n2p(alpha.get_value()), UP, buff=0.05))
        start, end = Square(color=BLUE), Circle(color=YELLOW)
        start.align_data(end)
        morph = always_redraw(lambda: start.copy().interpolate(start, end, alpha.get_value()).move_to(stage + UP * 0.4))
        title = Text('how far along?', font_size=26, color=SCAFFOLD).next_to(slider, DOWN, buff=0.35)
        self.play(Create(slider), FadeIn(knob), FadeIn(morph), FadeIn(title))
        self.hold_until(0.66)
        for value, words in ((0.25, 'a quarter of the way'), (0.5, 'halfway')):
            note = Text(words, font_size=24, color=FOCUS).next_to(morph, UP, buff=0.3)
            self.play(alpha.animate.set_value(value), FadeIn(note), run_time=1.5)
            self.wait(1.2)
            self.play(FadeOut(note))
        self.play(alpha.animate.set_value(1), run_time=1.5)
        self.hold_until(0.86)

        # "It is a program": the sentences become code
        code = code_panel(snippet_source('ep01/01-square-to-circle.py'), font_size=20).to_edge(LEFT, buff=0.5)
        self.play(FadeOut(VGroup(slider, knob, morph, title)), FadeTransform(sentences.set_opacity(1), code), run_time=1.5)
        self.finish()


class Segment_1_3(Segment):
    """Where Manim comes from."""
    EPISODE, SEGMENT = 1, '1.3'

    def construct(self):
        # [V1.3a] a timeline of years
        years = NumberLine(x_range=[2015, 2026, 1], length=11.5, include_numbers=False, include_ticks=True,
                           tick_size=0.1, color=SCAFFOLD).shift(UP * 1.2)
        labels = VGroup(*[Text(str(y), font_size=28, color=SCAFFOLD).next_to(years.n2p(y), UP, buff=0.2)
                          for y in (2015, 2020, 2026)])
        self.play(Create(years), FadeIn(labels))
        start = Dot(years.n2p(2015), color=FOCUS, radius=0.1)
        origin = Text('Manim: written by Grant Sanderson\nfor his math videos', font_size=32, line_spacing=0.9)
        origin.next_to(start, DOWN, buff=0.35).align_to(start, LEFT).shift(LEFT * 0.2)
        self.play(GrowFromCenter(start), Write(origin))
        self.hold_until(0.27)

        # [V1.3b] the community branch in 2020; the original continues as ManimGL
        fork = years.n2p(2020)
        original = Line(fork, years.n2p(2026), color=OBJECT, stroke_width=6)
        early = Line(years.n2p(2015), fork, color=OBJECT, stroke_width=6)
        branch = VMobject(color=AFTER, stroke_width=6)
        branch.set_points_smoothly([fork, fork + RIGHT * 0.6 + DOWN * 1.1, fork + RIGHT * 1.6 + DOWN * 1.9,
                                    years.n2p(2026) + DOWN * 1.9])
        gl = Text('ManimGL', font_size=30, color=OBJECT).next_to(years.n2p(2023.5), UP, buff=0.2)
        ce = Text('Manim Community Edition', font_size=30, color=AFTER).next_to(branch.get_end(), DOWN, buff=0.2).align_to(branch.get_end(), RIGHT)
        self.play(FadeOut(origin), Create(early), run_time=1.2)
        self.play(Create(original), Create(branch), run_time=2)
        self.play(FadeIn(gl), FadeIn(ce))
        self.hold_until(0.45)

        # [V1.3c] this series follows the community edition
        here = Text('this series: Community conventions', font_size=28, color=FOCUS)
        here.next_to(ce, DOWN, buff=0.12).align_to(ce, RIGHT)
        self.play(Write(here), Indicate(branch, color=FOCUS, scale_factor=1))
        self.hold_until(0.6)

        # paragraph 3: the install hurdle
        history = VGroup(years, labels, start, early, original, branch, gl, ce, here)
        self.play(history.animate.scale(0.8).to_edge(UP, buff=0.3))
        needs = VGroup(*[Text(n, font_size=28) for n in
                         ('Python', 'Manim', 'drawing libraries', 'video encoding', 'LaTeX')])
        boxes = VGroup(*[VGroup(RoundedRectangle(width=3.6, height=0.55, corner_radius=0.1, color=SCAFFOLD), n)
                         for n in needs])
        for box in boxes:
            box[1].move_to(box[0])
        boxes.arrange(UP, buff=0.08).move_to(LEFT * 3.5 + DOWN * 2)
        self.play(LaggedStart(*[FadeIn(b, shift=DOWN * 0.4) for b in boxes], lag_ratio=0.25), run_time=2)
        self.hold_until(0.78)

        # [V1.3d] ManimOnline: a Manim-compatible engine in your browser
        browser = browser_icon(width=3.4, height=2).move_to(RIGHT * 3.5 + DOWN * 1.8)
        python = Text('Manim-compatible\nengine', font_size=28, color=AFTER, line_spacing=0.9).move_to(browser[0]).shift(DOWN * 0.15)
        caption = Text('ManimOnline: in your browser', font_size=30).next_to(browser, DOWN, buff=0.25)
        link = DashedLine(here.get_bottom(), browser.get_top(), color=SCAFFOLD)
        self.play(boxes.animate.set_opacity(0.25), Create(link))
        self.play(FadeIn(browser), Write(python), Write(caption))
        self.finish()


class Segment_1_4(Segment):
    """A tour of ManimOnline (screen recording)."""
    EPISODE, SEGMENT = 1, '1.4'

    def construct(self):
        card = footage_card('A tour of ManimOnline', [
            '[V1.4a] Page loads; outline the code editor, the preview, the toolbar',
            '[V1.4b] SquareToCircle in the editor; "Python loading", then the preview plays',
            '[V1.4c] Play, pause; drag the seek bar back and forth through the morph',
            '[V1.4d] Briefly highlight "Renderer: Auto" and "Sample gallery"',
        ])
        self.play(FadeIn(card))
        self.hold_until(0.3)
        qr = qr_card('q01-01')
        self.play(FadeIn(qr, shift=UP * 0.2))
        self.hold_until(0.56)
        self.play(FadeOut(qr))
        self.finish()


def toolbox():
    box = RoundedRectangle(width=1.6, height=1.0, corner_radius=0.12).set_stroke(SCAFFOLD, 3).set_fill('#1a1d22', 1)
    handle = Arc(radius=0.3, start_angle=0, angle=PI).set_stroke(SCAFFOLD, 3).next_to(box, UP, buff=0)
    return VGroup(handle, box)


def clapperboard():
    board = Rectangle(width=1.8, height=1.2).set_stroke(GREY_A, 3).set_fill('#1a1d22', 1)
    bar = Rectangle(width=1.8, height=0.3).set_fill(GREY_A, 1).set_stroke(GREY_A, 3).next_to(board, UP, buff=0)
    stripes = VGroup(*[Polygon(LEFT * 0.12, RIGHT * 0.05, RIGHT * 0.17 + UP * 0.3, UP * 0.3 + LEFT * 0.0)
                       .set_fill(BLACK, 1).set_stroke(width=0) for _ in range(5)])
    stripes.arrange(RIGHT, buff=0.18).move_to(bar)
    return VGroup(board, bar, stripes)


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


class Segment_1_5(Segment):
    """Reading the first scene, one line at a time."""
    EPISODE, SEGMENT = 1, '1.5'

    def construct(self):
        code = code_panel(snippet_source('ep01/01-square-to-circle.py'), font_size=24)
        code.scale_to_fit_width(6.6).to_edge(LEFT, buff=0.35)
        self.play(FadeIn(code, shift=RIGHT * 0.3))
        box = line_highlight(code, 0)
        right = RIGHT * 3.85
        self.hold_until(0.07)

        # [V1.5b] the import fills a toolbox with names
        tools = toolbox().move_to(right + DOWN * 1.5)
        names = VGroup(*[Text(n, font_size=28, color=c) for n, c in (
            ('Square', OBJECT), ('Circle', OBJECT), ('Create', AFTER), ('Transform', AFTER),
            ('BLUE', BLUE), ('YELLOW', YELLOW), ('UP', GREY_A), ('RIGHT', GREY_A))])
        spots = [right + 1.9 * np.array([np.cos(a), np.sin(a) * 0.9, 0]) + UP * 0.4
                 for a in np.linspace(PI * 0.05, PI * 0.95, len(names))]
        self.play(Create(box), FadeIn(tools))
        self.play(LaggedStart(*[FadeIn(n, target_position=tools.get_center()) for n in names], lag_ratio=0.1),
                  *[n.animate.move_to(p) for n, p in zip(names, spots)], run_time=2)
        self.hold_until(0.16)

        # [V1.5c] the class: a scene with a name
        clapper = clapperboard().move_to(right)
        title = Text('Scene: SquareToCircle', font_size=28).next_to(clapper, DOWN, buff=0.35)
        self.play(Transform(box, line_highlight(code, 3)), FadeOut(VGroup(tools, names)), FadeIn(clapper), Write(title))
        self.hold_until(0.33)

        # [V1.5d] construct: the script, run from top to bottom
        theatre = stage(width=4.8).move_to(right + DOWN * 0.2)
        order = Arrow(code_line(code, 5).get_left() + LEFT * 0.35, code_line(code, 9).get_left() + LEFT * 0.35,
                      buff=0, color=FOCUS, stroke_width=4)
        self.play(Transform(box, line_highlight(code, 4)), FadeOut(title), ReplacementTransform(clapper, theatre))
        self.play(GrowArrow(order))
        script = Text('top to bottom', font_size=24, color=FOCUS).next_to(theatre, DOWN, buff=0.3)
        self.play(FadeIn(script))
        self.hold_until(0.45)

        # [V1.5e] two objects exist, waiting in the wings
        square = Square(color=BLUE).scale(0.45).set_opacity(0.35).move_to(theatre[1].get_center() + UP * 2.4)
        circle = Circle(color=YELLOW).scale(0.45).set_opacity(0.35).move_to(theatre[2].get_center() + UP * 2.4)
        wings = Text('exist, but not on screen yet', font_size=24, color=SCAFFOLD).move_to(script)
        self.play(Transform(box, VGroup(line_highlight(code, 5), line_highlight(code, 6))),
                  FadeIn(square), FadeIn(circle), FadeOut(order), ReplacementTransform(script, wings))
        self.hold_until(0.58)

        # [V1.5f] play(Create(square)): time passes and the square is drawn on stage
        centre = theatre[0].get_center() + UP * 1.4
        drawn = Square(color=BLUE).scale(0.8).move_to(centre)
        self.play(Transform(box, line_highlight(code, 7)), FadeOut(wings))
        self.play(square.animate.move_to(centre).scale(0.8 / 0.55).set_opacity(0.15), run_time=0.8)
        self.play(Create(drawn), run_time=1.5)
        self.remove(square)
        self.hold_until(0.72)

        # [V1.5g] Transform: the square takes the circle's shape; the circle is only the target
        target = Text('target', font_size=24, color=FOCUS).next_to(circle, UP, buff=0.15)
        self.play(Transform(box, line_highlight(code, 8)), circle.animate.set_opacity(0.6), FadeIn(target))
        self.play(Transform(drawn, Circle(color=YELLOW).scale(0.8).move_to(centre)), run_time=1.5)
        note = Text('still called square', font_size=24, color=SCAFFOLD).next_to(drawn, DOWN, buff=0.3)
        self.play(FadeIn(note))
        self.hold_until(0.91)

        # [V1.5h] wait: a second of stillness
        clock = clock_icon().move_to(theatre[0].get_center() + UP * 3.2)
        self.play(Transform(box, line_highlight(code, 9)), FadeOut(VGroup(note, target)), FadeIn(clock))
        self.play(Rotate(clock[1], -TAU, about_point=clock[0].get_center()), run_time=1, rate_func=linear)
        self.finish()


class Segment_1_6(Segment):
    """Three nouns, one verb."""
    EPISODE, SEGMENT = 1, '1.6'

    def construct(self):
        def node(word, icon, color):
            label = Text(word, font_size=40, color=color)
            return VGroup(icon.next_to(label, UP, buff=0.25), label)

        scene = node('Scene', stage(width=2.2).scale(0.5), GREY_A).move_to(UP * 2.55)
        mob = node('Mobject', VGroup(Square(color=BLUE).scale(0.35), Circle(color=YELLOW).scale(0.35)).arrange(RIGHT),
                   OBJECT).move_to(LEFT * 4.2 + DOWN * 1.6)
        anim = node('Animation', CurvedArrow(LEFT * 0.6, RIGHT * 0.6, color=AFTER, angle=-PI / 2), AFTER)
        anim.move_to(RIGHT * 4.2 + DOWN * 1.6)
        self.play(LaggedStart(*[FadeIn(n, shift=UP * 0.2) for n in (scene, mob, anim)], lag_ratio=0.3))
        self.hold_until(0.17)

        meanings = [('the stage where everything happens', scene), ('anything you can see', mob),
                    ('how mobjects change over time', anim)]
        lines = VGroup()
        for i, (words, target) in enumerate(meanings):
            line = Text(words, font_size=24, color=SCAFFOLD).next_to(target, DOWN, buff=0.2)
            lines.add(line)
            self.play(Write(line))
            self.hold_until(0.17 + 0.43 * (i + 1) / 3)

        # [V1.6b] play in the middle: animations in, frames out
        play = Text('play', font_size=48, color=FOCUS).move_to(DOWN * 0.2)
        ring = SurroundingRectangle(play, color=FOCUS, corner_radius=0.2, buff=0.25)
        into = Arrow(anim.get_left(), ring.get_right(), color=AFTER, buff=0.2)
        strip = VGroup(*[square_to_circle_frame(i).scale(0.18) for i in (8, 18, 22, 26, 45)])
        for shape in strip:
            shape.add(Rectangle(width=0.5, height=0.5, color=GREY_D, stroke_width=1.5).move_to(shape))
        strip.arrange(RIGHT, buff=0.08).next_to(ring, DOWN, buff=1.2)
        out = Arrow(ring.get_bottom(), strip.get_top(), color=FOCUS, buff=0.15)
        frames = Text('frames', font_size=24, color=SCAFFOLD).next_to(strip, DOWN, buff=0.15)
        self.play(Write(play), Create(ring))
        self.play(GrowArrow(into))
        self.play(GrowArrow(out), LaggedStart(*[FadeIn(f) for f in strip], lag_ratio=0.2), FadeIn(frames))
        self.hold_until(0.8)

        # episode pointers
        two = Text('episode 2', font_size=24, color=OBJECT).next_to(mob, UP, buff=0.25)
        three = Text('episode 3', font_size=24, color=AFTER).next_to(anim, UP, buff=0.25)
        self.play(FadeIn(two, shift=DOWN * 0.2), Indicate(mob[1], color=OBJECT))
        self.play(FadeIn(three, shift=DOWN * 0.2), Indicate(anim[1], color=AFTER))
        self.finish()


class Segment_1_7(Segment):
    """Your first edits."""
    EPISODE, SEGMENT = 1, '1.7'

    def construct(self):
        card = footage_card('Your first edits', [
            '[V1.7a] Add fill_opacity=0.5 to the square; after a pause the preview re-renders, half-filled',
            '[V1.7b] Add a third line that transforms the shape into a red triangle; the preview ends red',
        ])
        self.play(FadeIn(card))
        self.hold_until(0.3)

        # [V1.7c] the edited code, with each change marked
        after = code_panel(snippet_source('ep01/02-three-shapes.py'), font_size=24)
        after.scale_to_fit_width(13).to_edge(UP, buff=0.5)
        self.play(FadeOut(card), FadeIn(after))
        notes = [(5, 'a fill, and a more general name'), (8, 'a third shape'), (9, 'your turn: a green star')]
        marks = VGroup()
        for i, words in notes:
            box = line_highlight(after, i, color=AFTER)
            tag = Text(words, font_size=24, color=AFTER).next_to(after, DOWN, buff=0.3).align_to(after, LEFT)
            marks.add(VGroup(box, tag))
        results = VGroup(Square(color=BLUE, fill_opacity=0.5), Circle(color=YELLOW, fill_opacity=0.5),
                         Triangle(color=RED, fill_opacity=0.5),
                         DashedVMobject(Star(color=GREEN), num_dashes=30)).scale(0.55)
        results.arrange(RIGHT, buff=0.9).move_to(DOWN * 2.5 + LEFT * 2.4)
        steps = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.15, color=SCAFFOLD, stroke_width=3)
                         for a, b in zip(results[:-1], results[1:])])
        self.play(Create(marks[0][0]), Write(marks[0][1]), DrawBorderThenFill(results[0]))
        self.hold_until(0.4)
        qr = qr_card('q01-02')
        self.play(FadeIn(qr, shift=UP * 0.2), ReplacementTransform(marks[0], marks[1]))
        self.play(GrowArrow(steps[0]), FadeIn(results[1]), GrowArrow(steps[1]), FadeIn(results[2]))
        self.hold_until(0.52)
        self.play(ReplacementTransform(marks[1], marks[2]), GrowArrow(steps[2]), Create(results[3]))
        self.hold_until(0.68)

        # names: shape, not square
        rename = Text('shape: a name that stays true', font_size=30, color=FOCUS).next_to(after, DOWN, buff=0.3).align_to(after, LEFT)
        self.play(FadeOut(qr), ReplacementTransform(marks[2], VGroup(line_highlight(after, 5, color=FOCUS), rename)))
        self.finish()
