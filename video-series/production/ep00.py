"""Episode 0 · Trailer: Drawing with code. One Scene per script segment.

    python3 video-series/production/render.py 0 [-ql] [segment ...]

Shot ids in comments ([V0.3a] ...) refer to episodes/00-trailer.md. The montage in 0.3 redraws
moments from later episodes in miniature; 0.2's editor recording is a footage card.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403
from ep09 import chip  # noqa: E402
from ep12 import bit_grid, bits_of  # noqa: E402

SHOWCASE = 'ep00/01-showcase.py'
STAR_LINE = 7      # Star(color=RED...) in the excerpt below (0-based)


def hook_star():
    return Star(color=RED, fill_opacity=0.4).scale(1.5)


def showcase_excerpt(colour='RED'):
    source = snippet_lines(SHOWCASE, 8, 15).replace('Star(color=RED', f'Star(color={colour}')
    return fit(code_panel(source, font_size=22, line_numbers=False), 8.4)


def trailer_card():
    """q00-01 in the corner, as it stays from 0.2 to the end."""
    return qr_card('q00-01')


# ---------------------------------------------------------------- 0.1

class Segment_0_1(Segment):
    """Hook."""
    EPISODE, SEGMENT = 0, '0.1'

    def construct(self):
        # [V0.1a] a single dot pulses
        dot = Dot(radius=0.12, color=WHITE)
        self.play(FadeIn(dot, scale=0.3))
        self.play(dot.animate.scale(1.8), rate_func=there_and_back, run_time=0.8)

        # [V0.1b] dot → line → circle → square → star, smoothly
        self.at('Put a dot here')
        self.play(Indicate(dot, color=FOCUS))
        line = Line(LEFT * 2, RIGHT * 2, color=WHITE, stroke_width=6)
        self.at('Turn it into a circle')
        self.play(Transform(dot, line), run_time=1.0)
        circle = Circle(radius=1.5, color=YELLOW, fill_opacity=0.4)
        self.play(Transform(dot, circle), run_time=1.2)
        self.at('fold that circle into a square')
        square = Square(3.0, color=BLUE, fill_opacity=0.4)
        self.play(Transform(dot, square), run_time=1.5)
        self.at('What if you could write')
        self.play(Rotate(dot, PI / 2), run_time=1.0)
        self.play(Transform(dot, hook_star()), run_time=1.5)
        self.finish()


# ---------------------------------------------------------------- 0.2

class Segment_0_2(Segment):
    """The reveal (q00-01)."""
    EPISODE, SEGMENT = 0, '0.2'

    def construct(self):
        # [V0.2a] the star slides right; the Showcase code types itself on the left
        star = hook_star()
        self.add(star)
        code = showcase_excerpt().to_edge(LEFT, buff=0.5)
        self.play(star.animate.scale(0.8).move_to(RIGHT * 4.9), FadeIn(code.background))
        lines = code.code_lines
        self.play(LaggedStart(*[Write(line) for line in lines if len(line)], lag_ratio=0.8), run_time=4.5)

        # [V0.2b] the editor recording, and the QR code that stays to the end of 0.3
        self.at('And this is Mannim Online')
        card = footage_card('ManimOnline', ['[V0.2b] The Showcase code in the editor, the preview playing on the right',
                                            '[V0.2c] Change RED to GREEN on the Star line; a second later the star is green'], height=4.6)
        card.move_to(UP * 0.4)
        corner = trailer_card()
        self.play(FadeOut(VGroup(code, star)), FadeIn(card), FadeIn(corner, shift=UP * 0.2))
        self.at('No install')
        self.play(Indicate(card[2][1], color=FOCUS))

        # [V0.2c] edit RED to GREEN; a moment later it plays
        self.at('You stop typing')
        code = showcase_excerpt().to_edge(LEFT, buff=0.5).shift(UP * 0.4)
        star = hook_star().scale(0.8).move_to([4.9, 1.2, 0])
        self.play(FadeOut(card), FadeIn(code), FadeIn(star))
        green = showcase_excerpt('GREEN').move_to(code, aligned_edge=UL)
        mark = line_highlight(code, STAR_LINE)
        self.play(Create(mark), Transform(code_line(code, STAR_LINE), code_line(green, STAR_LINE)), run_time=0.8)
        self.wait(1.0)
        self.play(star.animate.set_color(GREEN).set_fill(GREEN, 0.4))
        self.finish()


# ---------------------------------------------------------------- 0.3

def casteljau(points, t):
    levels = [points]
    while len(levels[-1]) > 1:
        prev = levels[-1]
        levels.append([interpolate(a, b, t) for a, b in zip(prev, prev[1:])])
    return levels


class Segment_0_3(Segment, ThreeDScene):
    """What the series covers: a montage."""
    EPISODE, SEGMENT = 0, '0.3'

    def show(self, shot):
        self.play(FadeIn(shot, scale=0.9), run_time=0.4)

    def clear_shot(self, shot):
        self.play(FadeOut(shot), run_time=0.3)

    def construct(self):
        corner = trailer_card()
        self.add(corner)

        # a single square
        square = Square(2.0, color=BLUE, fill_opacity=0.4)
        self.show(square)

        # [V0.3a] de Casteljau tracing a curve (episode 4)
        self.at('build up to curves')
        self.clear_shot(square)
        controls = [np.array(p) for p in ([-3, -1.5, 0], [-1.5, 2, 0], [1.5, 2, 0], [3, -1.5, 0])]
        t = ValueTracker(0)
        hull = VMobject().set_points_as_corners(controls).set_stroke(GREY_B, 2)
        dots = VGroup(*[Dot(p, radius=0.07, color=GREY_B) for p in controls])
        scaffold = always_redraw(lambda: VGroup(*[
            VGroup(VMobject().set_points_as_corners(level).set_stroke(c, 2) if len(level) > 1 else VGroup(),
                   *[Dot(p, radius=0.06, color=c) for p in level])
            for level, c in zip(casteljau(controls, t.get_value())[1:], (BLUE, GREEN, FOCUS))]))
        curve = always_redraw(lambda: ParametricFunction(lambda s: bezier(controls)(s), t_range=[0, max(t.get_value(), 1e-3)],
                                                         color=FOCUS, stroke_width=5))
        shot = VGroup(hull, dots)
        self.show(shot)
        self.add(scaffold, curve)
        self.play(t.animate.set_value(1), run_time=2.0, rate_func=linear)
        self.remove(scaffold)
        curve.clear_updaters()
        self.clear_shot(VGroup(shot, curve))

        # [V0.3a] 2x + 3 = 11 solves itself (episode 5)
        self.at('equations')
        steps = [MathTex('2x', '+', '3', '=', '11', font_size=72), MathTex('2x', '=', '8', font_size=72), MathTex('x', '=', '4', font_size=72)]
        self.show(steps[0])
        self.play(TransformMatchingTex(steps[0], steps[1]), run_time=0.8)
        self.play(TransformMatchingTex(steps[1], steps[2]), run_time=0.8)
        self.clear_shot(steps[2])

        # [V0.3a] Riemann rectangles thinning into an area (episode 7)
        self.at('graphs')
        axes = Axes(x_range=[0, 3, 1], y_range=[0, 5, 1], x_length=6, y_length=3.6, tips=False).move_to(UP * 0.2)
        graph = axes.plot(lambda x: 0.5 * x * x + 0.3, color=FOCUS)
        rects = axes.get_riemann_rectangles(graph, x_range=[0, 3], dx=0.5, fill_opacity=0.7)
        self.show(VGroup(axes, graph, rects))
        for dx in (0.25, 0.1, 0.04):
            self.play(Transform(rects, axes.get_riemann_rectangles(graph, x_range=[0, 3], dx=dx, fill_opacity=0.7)), run_time=0.5)
        self.clear_shot(VGroup(axes, graph, rects))

        # [V0.3a] a surface turning in 3D (episode 8)
        self.at('cameras that fly')
        surface = Surface(lambda u, v: np.array([u, v, 0.6 * math.sin(u) * math.cos(v)]), u_range=[-2.5, 2.5], v_range=[-2.5, 2.5],
                          resolution=(18, 18), fill_opacity=0.9, checkerboard_colors=[BLUE_D, BLUE_E])
        surface.rotate(-62 * DEGREES, axis=RIGHT)
        normal = rotate_vector(OUT, -62 * DEGREES, RIGHT)
        self.show(surface)
        self.play(Rotate(surface, PI / 2, axis=normal), run_time=2.0, rate_func=linear)
        self.clear_shot(surface)

        # [V0.3a] a circle unrolling into a sine wave (episode 6)
        self.at('changing numbers')
        angle = ValueTracker(0)
        centre = LEFT * 4.0
        wheel = Circle(radius=1.0, color=BLUE).move_to(centre)
        spoke = always_redraw(lambda: Line(centre, centre + np.array([math.cos(angle.get_value()), math.sin(angle.get_value()), 0]), color=GREY_B))
        tip = always_redraw(lambda: Dot(centre + np.array([math.cos(angle.get_value()), math.sin(angle.get_value()), 0]), color=FOCUS))
        wave = always_redraw(lambda: FunctionGraph(lambda x: math.sin(x + 3.0), x_range=[-3.0, -3.0 + max(angle.get_value(), 1e-3)],
                                                   color=FOCUS) if angle.get_value() > 0.01 else VMobject())
        reach = always_redraw(lambda: DashedLine(tip.get_center(), [-3.0 + angle.get_value(), math.sin(angle.get_value()), 0], color=GREY_D))
        self.show(wheel)
        self.add(spoke, tip, wave, reach)
        self.play(angle.animate.set_value(2 * TAU * 0.9), run_time=2.2, rate_func=linear)
        for m in (spoke, tip, wave, reach):
            m.clear_updaters()
        self.clear_shot(VGroup(wheel, spoke, tip, wave, reach))

        # the hood: Python in a tab, an engine that matches, fingerprints for links (episodes 10 to 12)
        self.at('how Python can run in a browser tab')
        browser = browser_icon(5.0, 3.0)
        python = chip('Python', FOCUS, 32).move_to(browser).shift(DOWN * 0.2)
        self.show(VGroup(browser, python))
        self.at('how you rebuild an animation engine')
        self.clear_shot(VGroup(browser, python))
        pair = VGroup(Square(2.4, color=BLUE).set_fill(BLUE, 0.35), Square(2.4, color=AFTER).set_fill(AFTER, 0.35))
        self.show(pair)
        self.play(pair[0].animate.rotate(PI / 2), pair[1].animate.rotate(PI / 2), run_time=1.2)

        # [V0.3a] 512 squares flickering between two fingerprints (episode 12)
        self.at('how a link')
        self.clear_shot(pair)
        grids = [bit_grid(bits_of(m), cell=0.2) for m in (b'Hello, Manim', b'Hello, Manin')]
        for g in grids:
            g.move_to(UP * 0.3)
        self.show(grids[0])
        for k in range(4):
            self.play(Transform(grids[0], grids[(k + 1) % 2].copy()), run_time=0.35)

        # [V0.3b] the title card
        self.at('can carry an entire program')
        title = VGroup(Text('Drawing with Code', font_size=72), note_text('Manim and ManimOnline')).arrange(DOWN, buff=0.35).move_to(UP * 0.4)
        self.play(FadeOut(grids[0]), FadeIn(title, scale=0.9))
        self.finish()


def note_text(words):
    return Text(words, font_size=32, color=GREY_A)


# ---------------------------------------------------------------- 0.4

class Segment_0_4(Segment):
    """Call to action."""
    EPISODE, SEGMENT = 0, '0.4'

    def construct(self):
        title = VGroup(Text('Drawing with Code', font_size=72), note_text('Manim and ManimOnline')).arrange(DOWN, buff=0.35).move_to(UP * 0.4)
        corner = trailer_card()
        self.add(title, corner)

        # [V0.4a] the code grows a little; a new caption
        self.at('a code like this')
        code = corner[2]
        caption = wrapped_text("Scan to edit this trailer's final scene", 4.2, font_size=22, color=FOCUS)
        self.play(FadeOut(corner[:2]), code.animate.scale(1.25, about_edge=DR))
        caption.next_to(code, UP, buff=0.15).align_to(code, RIGHT)
        self.play(FadeIn(caption, shift=UP * 0.1))
        self.at("Let's begin")
        self.play(Indicate(title[0], color=FOCUS, scale_factor=1.05))
        self.finish()
