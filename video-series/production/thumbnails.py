"""YouTube thumbnails (1280 × 720), one Scene per episode, drawn like the videos themselves.

    python3 video-series/tools/youtube.py --thumbnails      # renders all of them into youtube/

or one directly: manim -s -r 1280,720 video-series/production/thumbnails.py Thumb_4

Each has the episode's two title lines (youtube/episodes.json "thumb") on the left, an episode badge,
the series name, and on the right one picture from the episode. Episode 9's picture is a real frame
of its editor recording (tools/record_footage.cjs), never a drawn imitation of the interface.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403
from ep04 import control_polygon, scaffold  # noqa: E402
from ep08 import CLASSIC, surface_axes, wavy_surface  # noqa: E402

META = json.loads((SERIES / 'youtube' / 'episodes.json').read_text())
RIGHT_CENTRE = np.array([3.55, 0.1, 0])


def title_block(episode):
    info = META['episodes'][str(episode)]
    first, second = info['thumb']
    lines = VGroup(Text(first, font_size=80, weight=HEAVY), Text(second, font_size=80, weight=HEAVY, color=FOCUS))
    lines.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
    if lines.width > 6.4:
        lines.scale_to_fit_width(6.4)
    badge_text = Text(info['thumb_note'].upper(), font_size=28, weight=BOLD, color=BLUE)
    badge = VGroup(RoundedRectangle(width=badge_text.width + 0.5, height=badge_text.height + 0.4, corner_radius=0.12)
                   .set_stroke(BLUE, 3).set_fill(BLACK, 1), badge_text)
    series = VGroup(Text('Drawing with Code', font_size=34, weight=BOLD, color=GREY_A),
                    Text('Manim · ManimOnline', font_size=24, color=SCAFFOLD)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
    block = VGroup(badge, lines).arrange(DOWN, aligned_edge=LEFT, buff=0.45)
    block.to_edge(LEFT, buff=0.6).shift(UP * 0.35)
    series.to_corner(DL, buff=0.55)
    return VGroup(block, series)


def place(mob, width=5.8, height=6.4):
    mob.scale_to_fit_width(width)
    if mob.height > height:
        mob.scale_to_fit_height(height)
    return mob.move_to(RIGHT_CENTRE)


class Thumbnail(Scene):
    EPISODE = 0

    def picture(self):
        return VGroup()

    def construct(self):
        self.add(place(self.picture()), title_block(self.EPISODE))


def morph_stages(count, size=1.0):
    square = Square(side_length=2 * size, color=BLUE)
    circle = Circle(radius=size, color=YELLOW)
    square.align_points(circle)
    stages = VGroup()
    for k in range(count):
        alpha = k / (count - 1)
        stage = square.copy()
        stage.set_points(interpolate(square.points, circle.points, smooth(alpha)))
        stage.set_stroke(interpolate_color(BLUE, YELLOW, alpha), 6)
        stages.add(stage)
    return stages


# ---------------------------------------------------------------- pictures

class Thumb_0(Thumbnail):
    EPISODE = 0

    def picture(self):
        shapes = VGroup(Dot(radius=0.12, color=GREY_A), Line(LEFT, RIGHT, color=GREY_A, stroke_width=6),
                        Circle(radius=0.9, color=YELLOW, stroke_width=6), Square(1.8, color=BLUE, stroke_width=6))
        shapes.arrange(RIGHT, buff=0.45)
        star = Star(color=RED, fill_opacity=0.45, stroke_width=8).scale(2.1)
        arrows = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.08, color=SCAFFOLD, stroke_width=4,
                                max_tip_length_to_length_ratio=0.5) for a, b in zip(shapes[:-1], shapes[1:])])
        row = VGroup(shapes, arrows).scale(0.8)
        return VGroup(star, row).arrange(DOWN, buff=0.6)


class Thumb_1(Thumbnail):
    EPISODE = 1

    def picture(self):
        cards = VGroup()
        for k, stage in enumerate(morph_stages(5, 0.75)):
            card = RoundedRectangle(width=2.4, height=2.4, corner_radius=0.12).set_stroke(GREY_B, 2).set_fill('#101418', 1)
            cards.add(VGroup(card, stage.move_to(card)).shift(RIGHT * 0.95 * k + DOWN * 0.55 * k).rotate(-0.06 * k + 0.1))
        frame = Text('frame 1 … 46', font_size=30, color=SCAFFOLD).next_to(cards, DOWN, buff=0.35)
        return VGroup(cards, frame)


class Thumb_2(Thumbnail):
    EPISODE = 2

    def picture(self):
        plane = NumberPlane(x_range=[-4, 4, 1], y_range=[-3, 3, 1], background_line_style={'stroke_opacity': 0.35})
        square = Square(1.6, color=BLUE, fill_opacity=0.5).move_to(plane.c2p(-2, 1))
        circle = Circle(0.9, color=YELLOW, fill_opacity=0.5).move_to(plane.c2p(1.6, 1.3))
        triangle = Triangle(color=GREEN, fill_opacity=0.5).scale(1.0).move_to(plane.c2p(-1.2, -1.6))
        dot = Dot(plane.c2p(2, -1), radius=0.12, color=RED)
        label = MathTex('(2,-1)', font_size=44).next_to(dot, DR, buff=0.1)
        return VGroup(plane, square, circle, triangle, dot, label)


class Thumb_3(Thumbnail):
    EPISODE = 3

    def picture(self):
        axes = Axes(x_range=[0, 1, 0.5], y_range=[0, 1, 0.5], x_length=5, y_length=4.4,
                    axis_config={'include_tip': False, 'stroke_width': 3})
        curves = VGroup(axes.plot(linear, color=GREY_B, stroke_width=6),
                        axes.plot(smooth, color=BLUE, stroke_width=8),
                        axes.plot(there_and_back, color=YELLOW, stroke_width=8))
        names = VGroup(*[Text(n, font=MONO, font_size=26, color=c) for n, c in
                         (('linear', GREY_B), ('smooth', BLUE), ('there_and_back', YELLOW))])
        names.arrange(DOWN, aligned_edge=LEFT, buff=0.15).next_to(axes, DOWN, buff=0.35)
        t = MathTex('t', font_size=40).next_to(axes.x_axis, RIGHT, buff=0.15)
        return VGroup(axes, curves, names, t)


class Thumb_4(Thumbnail):
    EPISODE = 4

    def picture(self):
        points = [np.array(p) for p in ([-2.6, -1.6, 0], [-1.6, 2.2, 0], [1.9, 2.4, 0], [2.7, -1.5, 0])]
        curve = CubicBezier(*points, color=YELLOW, stroke_width=10)
        build = scaffold(points, 0.62)
        point = Dot(bezier(np.array(points))(0.62), radius=0.14, color=YELLOW)
        return VGroup(control_polygon(points), build, curve, point)


class Thumb_5(Thumbnail):
    EPISODE = 5

    def picture(self):
        euler = MathTex('e^{i\\pi}', '+', '1', '=', '0', font_size=120)
        euler[0].set_color(YELLOW)
        euler[2].set_color(BLUE)
        euler[4].set_color(GREEN)
        area = MathTex('\\int_0^1 x^2\\,dx = \\tfrac{1}{3}', font_size=72, color=GREY_A)
        return VGroup(euler, area).arrange(DOWN, buff=0.7)


class Thumb_6(Thumbnail):
    EPISODE = 6

    def picture(self):
        line = NumberLine(x_range=[0, 4, 1], length=5.4, include_numbers=True, font_size=34)
        dot = Dot(line.n2p(math.pi), radius=0.14, color=YELLOW)
        value = DecimalNumber(math.pi, num_decimal_places=2, font_size=72, color=YELLOW).next_to(dot, UP, buff=0.35)
        spiral = ParametricFunction(lambda t: np.array([0.32 * t * math.cos(t), 0.32 * t * math.sin(t), 0]),
                                    t_range=[0, 4.2 * math.pi], color=BLUE, stroke_width=6)
        head = Dot(spiral.get_end(), radius=0.12, color=YELLOW)
        trace = VGroup(spiral, head)
        return VGroup(trace, VGroup(value, dot, line)).arrange(DOWN, buff=0.5)


class Thumb_7(Thumbnail):
    EPISODE = 7

    def picture(self):
        axes = Axes(x_range=[0, 4, 1], y_range=[0, 4, 1], x_length=5.6, y_length=4.8,
                    axis_config={'include_tip': False, 'stroke_width': 3})
        graph = axes.plot(lambda x: 0.25 * x * x + 0.6, x_range=[0, 3.8], color=YELLOW, stroke_width=8)
        boxes = axes.get_riemann_rectangles(graph, x_range=[0.4, 3.2], dx=0.35, color=[BLUE, GREEN],
                                            fill_opacity=0.7, stroke_width=1)
        x0 = 2.8
        slope = 0.5 * x0
        tangent = axes.plot(lambda x: 0.25 * x0 * x0 + 0.6 + slope * (x - x0), x_range=[1.7, 3.8], color=RED, stroke_width=6)
        touch = Dot(axes.c2p(x0, 0.25 * x0 * x0 + 0.6), radius=0.11, color=RED)
        return VGroup(axes, boxes, graph, tangent, touch)


class Surface_8(ThreeDScene):
    """Episode 8's surface alone; Thumb_8 places this picture (render it first)."""

    def construct(self):
        axes = surface_axes(x_length=5, y_length=5, z_length=3.2)
        self.set_camera_orientation(**CLASSIC, zoom=1.25)
        self.add(axes, wavy_surface(axes, resolution=(28, 28)))


class Thumb_8(Thumbnail):
    EPISODE = 8

    def picture(self):
        rendered = sorted((SERIES / 'build' / 'media' / 'images' / 'thumbnails').glob('Surface_8*.png'))
        if not rendered:
            raise FileNotFoundError('render Surface_8 first (tools/youtube.py --thumbnails does)')
        shot = ImageMobject(str(rendered[-1]))
        shot.pixel_array = shot.pixel_array[60:660, 240:1040]     # crop the empty margin
        shot.pixel_array[(shot.pixel_array[:, :, :3].max(axis=2) < 8)] = [0, 0, 0, 0]
        return Group(ImageMobject(shot.pixel_array))


class Thumb_9(Thumbnail):
    EPISODE = 9

    def picture(self):
        still = SERIES / 'build' / 'youtube' / 'v92-gallery.png'
        clip = SERIES / 'build' / 'footage' / 'V9.2.mp4'
        still.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '18.9', '-i', str(clip), '-frames:v', '1', str(still)], check=True)
        shot = ImageMobject(str(still)).scale_to_fit_width(6.2)
        frame = Rectangle(width=shot.width, height=shot.height).set_stroke(GREY_B, 3).move_to(shot)
        qr = qr_code('q09-01', 1.9).next_to(frame, DR, buff=-0.6)
        backing = SurroundingRectangle(qr, buff=0.08, color=BLACK, fill_opacity=1, stroke_width=0)
        return Group(shot, frame, backing, qr)


class Thumb_10(Thumbnail):
    EPISODE = 10

    def picture(self):
        window = browser_icon(width=5.6, height=3.8, color=GREY_A)
        facts = VGroup(*[Text(t, font=MONO, font_size=34, color=c) for t, c in
                         (('>>> import sys', GREY_A), ('3.12.7', YELLOW), ('emscripten', BLUE), ('wasm32', GREEN))])
        facts.arrange(DOWN, aligned_edge=LEFT, buff=0.22).move_to(window[0]).shift(DOWN * 0.15)
        return VGroup(window, facts)


class Thumb_11(Thumbnail):
    EPISODE = 11

    def picture(self):
        def panel(label, color):
            frame = RoundedRectangle(width=4.4, height=2.475, corner_radius=0.1).set_stroke(color, 4).set_fill(BLACK, 1)
            arrow = Arrow(LEFT * 1.5, RIGHT * 1.5, buff=0, color=YELLOW, stroke_width=6).shift(UP * 0.55)
            word = Text('Manim', font='Helvetica', font_size=56).shift(DOWN * 0.5 + LEFT * 0.6)
            square = Square(0.7, color=BLUE, fill_opacity=0.4).next_to(word, RIGHT, buff=0.45)
            name = Text(label, font_size=30, color=color).next_to(frame, UP, buff=0.15, aligned_edge=LEFT)
            return VGroup(frame, VGroup(arrow, word, square).move_to(frame), name)
        top = panel('Manim Community', BLUE)
        bottom = panel('ManimOnline', GREEN)
        both = VGroup(top, bottom).arrange(DOWN, buff=0.75)
        same = Text('=', font_size=72, weight=BOLD, color=GREY_A).rotate(PI / 2).move_to(both)
        same.move_to((top[0].get_bottom() + bottom[2].get_top()) / 2)
        return VGroup(both, same)


class Thumb_12(Thumbnail):
    EPISODE = 12

    def picture(self):
        code = qr_code('q12-03', 4.2)
        backing = SurroundingRectangle(code, buff=0.1, color=WHITE, fill_opacity=1, stroke_width=0)
        caption = Text('the code is in the link', font_size=32, color=FOCUS).next_to(code, DOWN, buff=0.35)
        return VGroup(backing, code, caption)
