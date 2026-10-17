"""Episode 8 · Cameras and the third dimension. One Scene per script segment.

    python3 video-series/production/render.py 8 [-ql] [segment ...]

Shot ids in comments ([V8.2c] ...) refer to episodes/08-cameras-and-the-third-dimension.md.
Segments mix Segment with the scene type they show (MovingCameraScene, ZoomedScene, ThreeDScene).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403

CAMERA_SNIPPET = 'ep08/01-moving-camera.py'
INSET_SNIPPET = 'ep08/02-zoomed-inset.py'
SURFACE_SNIPPET = 'ep08/03-surface.py'
SOLIDS_SNIPPET = 'ep08/04-solids.py'
HELIX_SNIPPET = 'ep08/05-helix.py'

CLASSIC = dict(phi=70 * DEGREES, theta=-50 * DEGREES)


# ---------------------------------------------------------------- the snippets' objects

def dot_grid():
    """q08-01: twenty five dots from blue to yellow, and the message under the middle one."""
    dots = VGroup(*[Dot(radius=0.12, color=interpolate_color(BLUE, YELLOW, i / 24)) for i in range(25)])
    dots.arrange_in_grid(rows=5, buff=0.8)
    secret = Text('hello from the middle', font_size=48).scale(8 / 48).move_to(dots[12]).shift(DOWN * 0.2)
    return dots, secret


def wavy(u, v):
    """q08-03's surface."""
    return math.sin(u) * math.cos(v)


def surface_axes(**lengths):
    sizes = dict(x_length=6, y_length=6, z_length=4) | lengths
    return ThreeDAxes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[-2, 2, 1], **sizes)


def wavy_surface(axes, resolution=(20, 20)):
    return axes.plot_surface(wavy, u_range=[-3, 3], v_range=[-3, 3], resolution=resolution,
                             colorscale=[BLUE, GREEN, YELLOW], fill_opacity=0.85)


# ---------------------------------------------------------------- placing things on screen

def on_screen(mob, frame):
    """Map a mobject laid out in ordinary screen coordinates onto wherever a moving camera's
    frame is now (only while the frame stands still)."""
    s = frame.height / 8
    return mob.scale(s, about_point=ORIGIN).shift(frame.get_center())


def flat(scene, *mobs):
    """Pin mobjects flat to the screen in a ThreeDScene (they still need adding or fading in)."""
    scene.add_fixed_in_frame_mobjects(*mobs)
    scene.remove(*mobs)
    return mobs[0] if len(mobs) == 1 else VGroup(*mobs)


def upright(scene, *mobs):
    """Labels that sit at a 3D point but always face the camera."""
    scene.add_fixed_orientation_mobjects(*mobs)
    scene.remove(*mobs)
    return mobs[0] if len(mobs) == 1 else VGroup(*mobs)


def note(words, font_size=24, color=SCAFFOLD):
    return Text(words, font_size=font_size, color=color)


def backed(mob, opacity=0.85, buff=0.12):
    return VGroup(BackgroundRectangle(mob, fill_opacity=opacity, buff=buff), mob)


def check_mark(size=0.5, color=AFTER):
    return VMobject().set_points_as_corners([[-0.5, 0, 0], [-0.15, -0.4, 0], [0.55, 0.45, 0]]).scale(size).set_stroke(color, 8)


def cross_mark(size=0.35, color=WARNING):
    return VGroup(Line(UL, DR), Line(UR, DL)).scale(size).set_stroke(color, 8)


def tint(text, source, needle, color=FOCUS, occurrence=0):
    return find_chars(text, source, needle, occurrence).animate.set_color(color)


def sphere_point(radius, phi, theta):
    return radius * np.array([math.sin(phi) * math.cos(theta), math.sin(phi) * math.sin(theta), math.cos(phi)])


class Segment_8_1(Segment, MovingCameraScene):
    """Cold open: a secret in the middle (q08-01)."""
    EPISODE, SEGMENT = 8, '8.1'

    def construct(self):
        # [V8.1a] twenty five dots; nothing else seems to be there
        frame = self.camera.frame
        dots, secret = dot_grid()
        self.play(LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.05), run_time=1.5)
        self.add(secret)
        frame.save_state()

        # [V8.1b] dive toward the centre dot: the message appears
        self.at("Let's go and look")
        self.play(frame.animate.scale(0.15).move_to(dots[12]), run_time=3)

        # [V8.1c] drift to the next dot, then pull back out
        self.at('In every scene so far')
        self.play(frame.animate.move_to(dots[13]))
        self.at('the camera gets to move')
        self.play(Restore(frame), run_time=2)
        self.finish()


class Segment_8_2(Segment, MovingCameraScene):
    """The camera is a rectangle."""
    EPISODE, SEGMENT = 8, '8.2'

    def construct(self):
        frame = self.camera.frame
        frame.save_state()
        dots, secret = dot_grid()
        world = NumberPlane(x_range=[-24, 24, 2], y_range=[-14, 14, 2],
                            background_line_style={'stroke_color': GREY_D, 'stroke_width': 2, 'stroke_opacity': 0.5},
                            axis_config={'stroke_opacity': 0})
        self.add(dots, secret)

        # [V8.2a] pull back: the scene goes on beyond the camera's view, which is a rectangle
        view = Rectangle(width=config.frame_width, height=config.frame_height).set_stroke(WHITE, 6)
        self.play(FadeIn(world), frame.animate.scale(2.4), Create(view), run_time=2.5)
        self.at('a rectangle called the frame')
        name = code_text('self.camera.frame', 26, WHITE).scale(2.4).next_to(view, UP, buff=0.3)
        self.play(FadeIn(name))
        self.at('fills the screen')
        self.play(view.animate.set_stroke(FOCUS), rate_func=there_and_back, run_time=1.5)

        # [V8.2c] it's a mobject: scale it and move it (code beats in sequence)
        self.at('everything you already know')
        lines = [snippet_lines(CAMERA_SNIPPET, n, n).strip() for n in (11, 12, 15)]
        code = fit(code_panel('\n'.join(lines), font_size=22, line_numbers=False), 9.2).to_corner(DL, buff=0.3)
        on_screen(code, frame)
        self.play(FadeIn(code))
        self.at('Scale it down')
        mark = line_highlight(code, 1)
        card = on_screen(qr_card('q08-01'), frame)
        self.play(Create(mark), FadeIn(card))
        self.play(view.animate.scale(0.15), FadeOut(name), run_time=2)
        zoom = Text('× 0.15: about 6.7 times closer', font_size=26, color=FOCUS).scale(2.4)
        zoom.next_to(dots, DOWN, buff=0.9)
        self.play(FadeIn(zoom))
        self.at('Move it to a dot')
        self.play(view.animate.move_to(dots[12]), run_time=1.5)

        # [V8.2b] animate the real camera into the rectangle: what it holds fills the screen
        self.at('Animate those changes')
        self.play(FadeOut(VGroup(code, mark, card, zoom)))
        self.play(frame.animate.scale(view.height / frame.height).move_to(view), run_time=3)
        self.play(FadeOut(view), FadeOut(world))

        # save state, restore
        self.at('Save state before')
        saved = on_screen(code_text('frame.save_state()  ...  Restore(frame)', 26, GREY_A).to_edge(DOWN, buff=0.5), frame)
        self.play(FadeIn(saved), frame.animate.move_to(dots[13]))
        self.at('restore takes you')
        self.play(FadeOut(saved), Restore(frame), run_time=2)
        self.at('That pattern')
        steps = VGroup(*[Text(w, font_size=30) for w in ('save', 'zoom in', 'explain', 'restore')]).arrange(RIGHT, buff=1.0)
        arrows = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.15, color=GREY_B, stroke_width=4,
                                max_tip_length_to_length_ratio=0.25) for a, b in zip(steps, steps[1:])])
        pattern = VGroup(steps, arrows).to_edge(DOWN, buff=0.6)
        steps[3].set_color(AFTER)
        self.play(LaggedStart(*[FadeIn(m) for m in (steps[0], arrows[0], steps[1], arrows[1], steps[2], arrows[2], steps[3])],
                              lag_ratio=0.3), run_time=2.5)

        # [V8.2d] zoomed in, strokes look thicker: they're measured in scene units
        self.at('One detail')
        sample = VGroup(Line(LEFT * 0.4, RIGHT * 0.4, color=BLUE), Circle(radius=0.25, color=AFTER).shift(RIGHT * 0.9))
        sample.move_to([5.6, 1.4, 0])
        tag = note('stroke width 4', 22).next_to(sample, DOWN, buff=0.25)
        self.play(FadeOut(pattern), Create(sample), FadeIn(tag))
        self.at('lines get thicker')
        self.play(FadeOut(tag), frame.animate.scale(0.15).move_to(sample), run_time=2.5)
        units = Text('stroke widths are in scene units', font_size=26, color=FOCUS)
        units = on_screen(units.to_edge(DOWN, buff=0.6), frame)
        self.play(FadeIn(units))
        self.at('If you need hairlines')
        hairline = on_screen(code_text('.set_stroke(width=0.6)', 26, AFTER).to_edge(UP, buff=0.6), frame)
        self.play(FadeIn(hairline), sample.animate.set_stroke(width=0.6), run_time=1.5)
        self.finish()


class Segment_8_3(Segment, ZoomedScene):
    """A magnifying glass (q08-02)."""
    EPISODE, SEGMENT = 8, '8.3'

    def __init__(self, **kwargs):
        ZoomedScene.__init__(self, zoom_factor=0.25, zoomed_display_height=3, zoomed_display_width=4,
                             image_frame_stroke_width=4, **kwargs)

    def construct(self):
        # [V8.3a] the ruler, the dot and the small frame
        ticks = VGroup(*[Line(UP * 0.1, DOWN * 0.1).shift(RIGHT * (i * 0.1 - 5)) for i in range(101)])
        ruler = VGroup(Line(LEFT * 5, RIGHT * 5), ticks).shift(DOWN * 1.5)
        dot = Dot(ruler.get_left(), color=YELLOW)
        self.play(Create(ruler), FadeIn(dot), run_time=1.5)
        frame = self.zoomed_camera.frame
        frame.move_to(dot).set_color(YELLOW)
        self.zoomed_display.to_corner(UR)
        self.zoomed_display.display_frame.set_color(YELLOW)

        # [V8.3b] a second camera and its display box
        self.at('It adds a second camera')
        self.play(Create(frame))
        frame_tag = code_text('zoomed_camera.frame', 20, YELLOW).next_to(frame, UP, buff=0.2).shift(RIGHT * 1.2)
        self.play(FadeIn(frame_tag))
        self.at('shows what that camera sees')
        self.activate_zooming(animate=True)
        display_tag = code_text('zoomed_display', 20, YELLOW).next_to(self.zoomed_display, DOWN, buff=0.15)
        self.play(FadeIn(display_tag))

        # an updater keeps the small frame on the dot
        self.at('Here the small frame')
        source = '\n'.join(snippet_lines(INSET_SNIPPET, n, n).strip() for n in (14, 18, 19))
        code = code_panel(source, font_size=22, line_numbers=False).to_edge(DOWN, buff=0.35)
        self.play(FadeOut(frame_tag), FadeIn(code))
        self.at('with an updater')
        mark = line_highlight(code, 1)
        self.play(Create(mark))
        frame.add_updater(lambda m: m.move_to(dot))

        # [V8.3c] the dot slides; the inset scrolls the ticks past
        self.at('As the dot slides')
        card = qr_card('q08-02', corner=UL)
        self.play(FadeOut(mark), FadeIn(card))
        self.play(dot.animate.move_to(ruler.get_right()), run_time=5, rate_func=linear)

        # [V8.3d] the zoom factor: the small frame is a quarter of the display
        self.at('The zoom factor')
        frame.clear_updaters()
        corners = (UL, UR, DL, DR)
        links = VGroup(*[DashedLine(frame.get_corner(c), self.zoomed_display.get_corner(c), color=YELLOW,
                                    stroke_width=2, dash_length=0.12) for c in corners])
        factor = code_text('zoom_factor=0.25', 24, YELLOW)
        self.play(FadeOut(code), FadeOut(display_tag), Create(links), run_time=1.5)
        factor.move_to([-1.2, 1.6, 0])
        self.play(FadeIn(factor))
        self.at('Zero point two five means')
        quarter = note('frame = ¼ of the display: everything looks 4 × larger', 26, GREY_A).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(quarter))
        self.finish()


class Segment_8_4(Segment, ThreeDScene):
    """Stepping into 3D: phi and theta."""
    EPISODE, SEGMENT = 8, '8.4'

    def construct(self):
        # [V8.4a] a flat plane tilts away, revealing z
        floor = NumberPlane(x_range=[-4, 4, 1], y_range=[-4, 4, 1], x_length=8, y_length=8,
                            background_line_style={'stroke_color': BLUE_E, 'stroke_width': 1.5, 'stroke_opacity': 0.6},
                            axis_config={'stroke_opacity': 0})
        axes = surface_axes(x_length=8, y_length=8, z_length=5)
        axes.x_axis.set_color(BLUE)
        axes.y_axis.set_color(GREEN)
        axes.z_axis.set_color(RED)
        names = upright(self, *[MathTex(n, color=c).move_to(p) for n, c, p in
                                (('x', BLUE, [4.4, 0, 0]), ('y', GREEN, [0, 4.4, 0]), ('z', RED, [0, 0, 2.9]))])
        self.play(FadeIn(floor), Create(axes.x_axis), Create(axes.y_axis), FadeIn(names[0]), FadeIn(names[1]))
        self.add(axes.z_axis)
        self.at('Points now use their third number')
        self.move_camera(**CLASSIC, run_time=2.5)
        self.at('called z')
        self.play(FadeIn(names[2]), Indicate(axes.z_axis, color=RED, scale_factor=1.05))

        # [V8.4b] the camera on a globe: phi from the top, theta around from x
        self.at('two angles')
        R = 3.2
        phi, theta = ValueTracker(50 * DEGREES), ValueTracker(30 * DEGREES)
        globe = VGroup(Circle(radius=R, color=GREY_B, stroke_width=1.5, stroke_opacity=0.6),
                       Circle(radius=R, color=GREY_B, stroke_width=1.5, stroke_opacity=0.6).rotate(PI / 2, axis=RIGHT))
        icon = always_redraw(lambda: Dot3D(sphere_point(R, phi.get_value(), theta.get_value()), radius=0.14, color=YELLOW))
        sight = always_redraw(lambda: DashedLine(sphere_point(R, phi.get_value(), theta.get_value()), ORIGIN,
                                                 color=YELLOW, stroke_width=2))
        meridian = always_redraw(lambda: ParametricFunction(
            lambda a: sphere_point(R, a, theta.get_value()), t_range=[0, PI], color=GREY_B, stroke_width=1.5,
            stroke_opacity=0.6))
        self.play(Create(globe), Create(meridian), run_time=1.5)
        self.play(FadeIn(icon, scale=0.5), Create(sight))
        camera_tag = upright(self, Text('camera', font_size=24, color=YELLOW))
        camera_tag.add_updater(lambda m: m.move_to(sphere_point(R + 0.6, phi.get_value(), theta.get_value())))
        self.play(FadeIn(camera_tag))

        self.at('Phi is how far')
        phi_arc = always_redraw(lambda: ParametricFunction(
            lambda a: sphere_point(1.4, a, theta.get_value()), t_range=[0, max(phi.get_value(), 0.01)],
            color=FOCUS, stroke_width=5))
        phi_tag = upright(self, MathTex(r'\varphi', color=FOCUS, font_size=48))
        phi_tag.add_updater(lambda m: m.move_to(sphere_point(1.9, phi.get_value() / 2, theta.get_value())))
        self.play(Create(phi_arc), FadeIn(phi_tag))
        self.play(phi.animate.set_value(20 * DEGREES), run_time=1.5)
        self.play(phi.animate.set_value(50 * DEGREES), run_time=1.5)

        # [V8.4c] phi = 0 looks straight down; phi = 90 degrees looks from the side
        self.at('At zero')
        self.play(phi.animate.set_value(0.01), run_time=1.5)
        diagram = VGroup(globe, meridian, icon, sight, phi_arc, phi_tag, camera_tag)
        self.play(FadeOut(diagram))
        self.move_camera(phi=0, theta=-90 * DEGREES, run_time=2)
        down = flat(self, backed(note('φ = 0: looking straight down', 30, FOCUS)).to_edge(UP, buff=0.4))
        self.play(FadeIn(down))
        self.at('At ninety degrees')
        self.play(FadeOut(down))
        self.move_camera(phi=90 * DEGREES, theta=-90 * DEGREES, run_time=2)
        side = flat(self, backed(note('φ = 90°: edge-on, from the side', 30, FOCUS)).to_edge(UP, buff=0.4))
        self.play(FadeIn(side))

        # theta: walking round
        self.at('Theta is how far round')
        self.play(FadeOut(side))
        phi.set_value(50 * DEGREES)
        self.move_camera(**CLASSIC, run_time=2)
        theta_arc = always_redraw(lambda: Arc(radius=1.4, start_angle=0, angle=theta.get_value() % TAU, color=AFTER,
                                              stroke_width=5))
        theta_tag = upright(self, MathTex(r'\theta', color=AFTER, font_size=48))
        theta_tag.add_updater(lambda m: m.move_to(sphere_point(1.95, PI / 2, (theta.get_value() % TAU) / 2)))
        self.play(FadeIn(VGroup(globe, meridian, icon, sight, phi_arc, phi_tag, camera_tag)),
                  Create(theta_arc), FadeIn(theta_tag))
        self.at('walking in a circle')
        self.play(theta.animate.set_value(30 * DEGREES + TAU - 0.02), run_time=3, rate_func=linear)

        # [V8.4d] set_camera_orientation puts the camera anywhere on the globe
        self.at('Set camera orientation')
        source = 'self.set_camera_orientation(phi=70 * DEGREES, theta=-50 * DEGREES)'
        line = flat(self, backed(code_text(source, 24), 0.9).to_edge(DOWN, buff=0.4))
        for mob in (camera_tag, phi_tag, theta_tag):
            mob.clear_updaters()
        self.play(FadeOut(VGroup(globe, meridian, icon, sight, phi_arc, phi_tag, theta_arc, theta_tag, camera_tag)),
                  FadeIn(line))
        self.move_camera(phi=40 * DEGREES, theta=10 * DEGREES, run_time=2)
        self.at('Seventy degrees')
        self.play(tint(line[1], source, 'phi=70 * DEGREES'), tint(line[1], source, 'theta=-50 * DEGREES', AFTER))
        self.move_camera(**CLASSIC, run_time=2.5)
        self.at('the floor is still')
        floor_tag = flat(self, backed(note('depth, and the floor is still a floor', 28, GREY_A)).to_edge(UP, buff=0.4))
        self.play(FadeIn(floor_tag), Indicate(floor, color=BLUE_C, scale_factor=1.0))
        self.finish()


class Segment_8_5(Segment, ThreeDScene):
    """Points in space."""
    EPISODE, SEGMENT = 8, '8.5'

    def construct(self):
        self.set_camera_orientation(**CLASSIC, zoom=0.75)
        axes = ThreeDAxes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[-2, 2, 1])
        source = ('axes = ThreeDAxes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[-2, 2, 1])\n'
                  'point = axes.c2p(2, 1, 1.5)          # three graph coordinates in, one point out\n'
                  'dot = Dot3D(point, color=YELLOW)')
        code = flat(self, fit(code_panel(source, font_size=18, line_numbers=False), 12.6).to_edge(UP, buff=0.25))
        self.play(Create(axes), run_time=2)

        # [V8.5a] axes.c2p(2, 1, 1.5), with guides like the corner of a box
        self.at('third ruler')
        self.play(FadeIn(code))
        self.at('The point two, one')
        point = axes.c2p(2, 1, 1.5)
        dot = Dot(point, color=FOCUS, radius=0.32)
        self.play(FadeIn(dot, scale=3))
        guides = [
            (DashedLine(axes.c2p(0, 0, 0), axes.c2p(2, 0, 0), color=BLUE, stroke_width=5), 'two along x', 'x = 2', BLUE),
            (DashedLine(axes.c2p(2, 0, 0), axes.c2p(2, 1, 0), color=GREEN, stroke_width=5), 'one along y', 'y = 1', GREEN),
            (DashedLine(axes.c2p(2, 1, 0), point, color=RED, stroke_width=5), 'and a half up', 'z = 1.5', RED),
        ]
        readings = VGroup()
        for line, phrase, words, color in guides:
            self.at(phrase)
            reading = MathTex(words, color=color, font_size=40)
            readings.add(reading)
            reading.to_corner(DL, buff=0.6).shift(UP * 0.6 * (3 - len(readings)))
            flat(self, reading)
            self.play(Create(line), FadeIn(reading), run_time=0.9)

        # [V8.5b] OUT and IN join UP, DOWN, LEFT and RIGHT
        self.at('Directions gain')
        self.play(FadeOut(VGroup(code, readings, *[g[0] for g in guides])), dot.animate.set_opacity(0.3))
        compass = VGroup()
        labels = VGroup()
        for name, direction, color in (('RIGHT', RIGHT, BLUE), ('LEFT', LEFT, BLUE), ('UP', UP, GREEN),
                                       ('DOWN', DOWN, GREEN), ('OUT', OUT, RED), ('IN', IN, RED)):
            arrow = Arrow3D(ORIGIN, direction * 2, color=color)
            compass.add(arrow)
            labels.add(code_text(name, 24, color).move_to(direction * 2.5))
        upright(self, *labels)
        self.play(LaggedStart(*[Create(a) for a in compass[:4]], lag_ratio=0.2), FadeIn(labels[:4]), run_time=1.5)
        self.at('out, toward the viewer')
        self.play(Create(compass[4]), FadeIn(labels[4]))
        self.at('and in, away')
        self.play(Create(compass[5]), FadeIn(labels[5]))
        self.at('So up times two')
        target = UP * 2 + OUT
        spot = Dot3D(target, color=FOCUS, radius=0.1)
        sum_line = flat(self, backed(code_text('UP * 2 + OUT', 28, FOCUS)).to_corner(DL, buff=0.6))
        self.play(Create(DashedLine(UP * 2, target, color=FOCUS)), FadeIn(spot), FadeIn(sum_line))

        # [V8.5c] flat shapes lie flat; Dot3D is a little sphere
        self.at('Most flat shapes')
        cutouts = VGroup(Square(1.2, color=BLUE, fill_opacity=0.5).move_to(axes.c2p(-2, -1.5, 0)),
                         Circle(radius=0.6, color=AFTER, fill_opacity=0.5).move_to(axes.c2p(-1.5, 1.8, 0)))
        self.play(FadeOut(VGroup(compass, labels, spot, sum_line)), *[FadeOut(m) for m in self.mobjects if isinstance(m, DashedLine)],
                  FadeIn(cutouts), dot.animate.set_opacity(1))
        paper = flat(self, backed(note('flat shapes lie flat, like paper cut-outs', 26, GREY_A)).to_edge(UP, buff=0.4))
        self.play(FadeIn(paper))
        self.at('solid from every angle')
        ball = Dot3D(point, color=YELLOW, radius=0.22)
        self.play(FadeOut(paper), FadeOut(dot), FadeIn(ball))
        self.move_camera(phi=55 * DEGREES, theta=-20 * DEGREES, run_time=3)
        self.at('a little sphere')
        sphere_tag = flat(self, backed(code_text('Dot3D: a sphere, not a disc', 26, FOCUS)).to_edge(UP, buff=0.4))
        self.play(FadeIn(sphere_tag))
        self.finish()


class Segment_8_6(Segment, ThreeDScene):
    """Surfaces (q08-03)."""
    EPISODE, SEGMENT = 8, '8.6'

    def construct(self):
        # [V8.6a] q08-03: axes, then the wavy surface
        axes = surface_axes()
        self.set_camera_orientation(**CLASSIC)
        card = flat(self, qr_card('q08-03'))
        formula = flat(self, MathTex(r'z = \sin u \, \cos v', font_size=44).to_corner(UL, buff=0.5))
        self.play(Create(axes), FadeIn(card), FadeIn(formula))
        self.at('Plot surface')
        surface = wavy_surface(axes)
        self.play(Create(surface), run_time=2)

        # [V8.6b] the surface is a grid of 20 by 20 flat patches
        self.at('Resolution twenty')
        count = flat(self, backed(MathTex(r'20 \times 20 = 400 \text{ patches}', font_size=40)).to_corner(UR, buff=0.5))
        self.play(FadeOut(card), FadeIn(count), surface.animate.set_stroke(WHITE, width=1.2, opacity=0.9))
        self.move_camera(zoom=1.7, run_time=2)
        self.at('Raise the resolution')
        self.move_camera(zoom=1.0, run_time=1.5)
        finer = wavy_surface(axes, resolution=(40, 40)).set_stroke(WHITE, width=0.8, opacity=0.6)
        finer_count = flat(self, backed(MathTex(r'40 \times 40 = 1600 \text{ patches}', font_size=40)).to_corner(UR, buff=0.5))
        self.play(FadeOut(surface), FadeIn(finer), FadeOut(count), FadeIn(finer_count))

        # colorscale: blue valleys, green slopes, yellow peaks
        self.at('Colorscale paints')
        surface.set_stroke(width=0.5, opacity=0.3)
        bar = Rectangle(width=0.4, height=3).set_stroke(width=0).set_fill([YELLOW, GREEN, BLUE], opacity=1)
        bar.set_sheen_direction(DOWN)
        scale = VGroup(bar, Text('peaks', font_size=22).next_to(bar, RIGHT, buff=0.15).align_to(bar, UP),
                       Text('valleys', font_size=22).next_to(bar, RIGHT, buff=0.15).align_to(bar, DOWN))
        scale.to_edge(RIGHT, buff=0.5).shift(UP * 0.2)
        flat(self, scale)
        self.play(FadeOut(finer), FadeIn(surface), FadeOut(finer_count), FadeIn(scale))

        # [V8.6c] a slow ambient orbit
        self.at('begin ambient camera rotation')
        orbit = flat(self, backed(code_text('self.begin_ambient_camera_rotation(rate=0.3)', 24), 0.9).to_edge(DOWN, buff=0.4))
        self.play(FadeIn(orbit))
        self.begin_ambient_camera_rotation(rate=0.3)
        self.finish()


class Segment_8_7(Segment, ThreeDScene):
    """Solids (q08-04)."""
    EPISODE, SEGMENT = 8, '8.7'

    def construct(self):
        # [V8.7a] a sphere, a teal cube and a torus
        self.set_camera_orientation(phi=65 * DEGREES, theta=-40 * DEGREES)
        sphere = Sphere(radius=0.9, resolution=(16, 8)).shift(LEFT * 2.8)
        cube = Cube(side_length=1.4, fill_color=TEAL)
        torus = Torus(major_radius=0.8, minor_radius=0.25, resolution=(16, 8)).shift(RIGHT * 2.8)
        card = flat(self, qr_card('q08-04'))
        self.play(FadeIn(sphere), FadeIn(cube), FadeIn(torus), FadeIn(card))
        self.at('spheres, cubes')
        names = upright(self, *[note(w, 26, GREY_A).move_to(solid.get_center() + OUT * 1.5) for w, solid in
                                (('Sphere', sphere), ('Cube', cube), ('Torus', torus))])
        self.play(LaggedStart(*[FadeIn(n, shift=DOWN * 0.2) for n in names], lag_ratio=0.3))

        # built from flat faces
        self.at('built from flat faces')
        solids = VGroup(sphere, cube, torus)
        self.play(solids.animate.set_stroke(WHITE, width=1.5, opacity=1), run_time=1)
        self.play(solids.animate.set_stroke(width=0.5, opacity=0.4), run_time=1)

        # [V8.7b] shading: faces turned from the light are darker
        self.at('First, shading')
        self.play(FadeOut(card))
        self.play(Rotate(cube, PI / 2, axis=UP), Rotate(torus, PI / 2, axis=RIGHT), run_time=2)
        lit = flat(self, backed(note('each face is lit by the way it points', 28, GREY_A)).to_edge(DOWN, buff=0.5))
        self.play(FadeIn(lit))

        # [V8.7c] the camera swings round
        self.at('Second, depth sorting')
        self.play(FadeOut(lit), FadeOut(names))
        self.move_camera(phi=40 * DEGREES, theta=30 * DEGREES, run_time=3)

        # [V8.7d] painter's algorithm: farthest first, nearest last
        self.at('painted in that order')
        self.play(solids.animate.set_opacity(0.15))
        cards = VGroup()
        for k, (color, words) in enumerate(((BLUE_E, '1 · farthest'), (TEAL_D, '2'), (TEAL_B, '3 · nearest'))):
            face = Square(2.2).set_fill(color, 1).set_stroke(WHITE, 2)
            face.move_to([-1.2 + 1.1 * k, 0.8 - 0.7 * k, 0])
            label = Text(words, font_size=22).next_to(face.get_corner(UL), DR, buff=0.12)
            cards.add(VGroup(face, label))
        flat(self, *cards)
        for c in cards:
            self.play(FadeIn(c, shift=DOWN * 0.15), run_time=0.7)
        self.at("painter's algorithm")
        title = flat(self, backed(Text("the painter's algorithm", font_size=36, color=FOCUS)).to_edge(UP, buff=0.4))
        self.play(Write(title))
        self.finish()


class Segment_8_8(Segment, ThreeDScene):
    """Same curve, three views (q08-05)."""
    EPISODE, SEGMENT = 8, '8.8'

    def construct(self):
        # [V8.8a] q08-05: a helix grows; its title stays flat
        axes = ThreeDAxes(x_range=[-2, 2, 1], y_range=[-2, 2, 1], z_range=[-2, 2, 1], x_length=4, y_length=4, z_length=4)
        title = Text('A helix: (cos t, sin t, t / 4)', font_size=32).to_corner(UL)
        self.add_fixed_in_frame_mobjects(title)
        self.set_camera_orientation(phi=75 * DEGREES, theta=-30 * DEGREES)
        helix = axes.plot_parametric_curve(lambda t: (math.cos(t), math.sin(t), t / 4), t_range=[-TAU, TAU], color=YELLOW)
        card = flat(self, qr_card('q08-05'))
        self.add(axes)
        self.play(Write(title), Create(helix), FadeIn(card), run_time=3)

        # world objects tilt; fixed-in-frame ones don't
        self.at('ordinary objects tilt')
        tilted = Text('I tilt with the world', font_size=30, color=GREY_A).move_to(axes.c2p(0, -1.6, -2))
        self.play(FadeIn(tilted))
        self.move_camera(phi=60 * DEGREES, theta=-60 * DEGREES, run_time=2)
        self.at('titles and labels')
        fixed = flat(self, backed(fit(code_text('self.add_fixed_in_frame_mobjects(title)      # stays flat on the screen', 22)), 0.9)
                     .to_edge(DOWN, buff=0.4))
        self.play(FadeOut(card), FadeIn(fixed), Indicate(title, color=FOCUS, scale_factor=1.05))
        self.move_camera(phi=75 * DEGREES, theta=-30 * DEGREES, run_time=2)

        # [V8.8b] from straight above: a circle
        self.at('Now watch')
        self.play(FadeOut(fixed), FadeOut(tilted))
        self.at('From straight above')
        self.move_camera(phi=10 * DEGREES, theta=-90 * DEGREES, run_time=3)
        above = flat(self, backed(note('from above: a circle', 30, FOCUS)).to_corner(DR, buff=0.6))
        self.play(FadeIn(above))

        # [V8.8c] from the side: a wave
        self.at('From the side')
        self.play(FadeOut(above))
        self.move_camera(phi=88 * DEGREES, theta=0, run_time=3)
        side = flat(self, backed(note('from the side: a wave', 30, FOCUS)).to_corner(DR, buff=0.6))
        self.play(FadeIn(side))

        # [V8.8d] episode 6's circle and its wave, turned upright beside the helix
        self.at('exactly the sine wave')
        # Seen from (phi 88°, theta 0) the helix is x = sin t, y = t / 4 on screen (one unit per axis
        # unit), so this wave, beside it, is the same curve: the circle's sideways shadow over time.
        t = ValueTracker(-TAU)
        left = -3.4
        base = np.array([left, -TAU / 4 - 1.35, 0])

        def on_circle():
            return base + np.array([math.sin(t.get_value()), math.cos(t.get_value()), 0])

        def on_wave():
            return np.array([left + math.sin(t.get_value()), t.get_value() / 4, 0])

        circle = Circle(radius=1, color=BLUE).move_to(base)
        mover = always_redraw(lambda: Dot(on_circle(), color=FOCUS))
        link = always_redraw(lambda: DashedLine(on_circle(), on_wave(), color=GREY))
        wave_dot = always_redraw(lambda: Dot(on_wave(), color=FOCUS))
        trail = TracedPath(on_wave, stroke_color=YELLOW, stroke_width=4)
        caption = Text('episode 6,\nturned upright', font_size=22, color=SCAFFOLD).next_to(circle, LEFT, buff=0.3)
        flat(self, circle, mover, link, wave_dot, trail, caption)
        self.play(FadeOut(side), FadeIn(circle), FadeIn(caption))
        self.add(trail, link, mover, wave_dot)
        self.play(t.animate.set_value(TAU), run_time=5, rate_func=linear)
        self.at('two shadows')
        shadows = flat(self, backed(note('two shadows of one spiral', 30, FOCUS)).to_corner(DR, buff=0.6))
        self.play(FadeIn(shadows))
        self.finish()


def view_matrix(phi, theta):
    """What ThreeDCamera applies for (phi, theta): applying it to an object and viewing it
    straight down shows the object as that camera would."""
    return rotation_matrix(-phi, RIGHT) @ rotation_matrix(-theta - PI / 2, OUT)


def surface_view(phi, theta, size=0.42):
    axes = surface_axes()
    view = VGroup(axes, wavy_surface(axes, resolution=(14, 14)))
    view.apply_matrix(view_matrix(phi, theta), about_point=ORIGIN)
    return view.scale(size, about_point=ORIGIN)


class Segment_8_9(Segment, ThreeDScene):
    """Choosing a good view. One camera looking straight down; each copy is turned the way the
    camera would see it from its own phi and theta."""
    EPISODE, SEGMENT = 8, '8.9'

    def construct(self):
        # [V8.9a] four views of one surface
        heading = Text('one surface, four camera positions', font_size=30, color=SCAFFOLD).to_edge(UP, buff=0.3)
        self.play(FadeIn(heading))
        views = [(0, -PI / 2, 'straight down', 'Straight down', False),
                 (PI / 2, -PI / 2, 'from the side', 'Straight from the side', False),
                 (150 * DEGREES, -50 * DEGREES, 'from below', 'From underneath', False),
                 (70 * DEGREES, -50 * DEGREES, 'φ = 70°, θ = −50°', 'A tilt of sixty', True)]
        spots = [np.array([x, y, 0]) for y in (1.55, -2.05) for x in (-3.3, 3.3)]
        tiles = VGroup()
        for (phi, theta, words, phrase, good), spot in zip(views, spots):
            self.at(phrase)
            view = surface_view(phi, theta).move_to(spot)
            name = Text(words, font_size=24, color=GREY_A).move_to(spot + DOWN * 1.45)
            verdict = (check_mark(0.45) if good else cross_mark(0.25)).move_to(spot + LEFT * 2.4 + UP * 0.6)
            self.play(FadeIn(view), FadeIn(name), run_time=1)
            self.play(Create(verdict), run_time=0.5)
            tiles.add(VGroup(view, name, verdict))
        self.at('it shows depth')
        self.play(Indicate(tiles[3][1], color=AFTER, scale_factor=1.15))

        # [V8.9b] a slow orbit beside a fast spin
        self.at('Motion helps')
        self.play(FadeOut(tiles), FadeOut(heading))
        slow, fast = ValueTracker(-50 * DEGREES), ValueTracker(-50 * DEGREES)
        left = always_redraw(lambda: surface_view(65 * DEGREES, slow.get_value(), 0.55).move_to([-3.4, 0.2, 0]))
        right = always_redraw(lambda: surface_view(65 * DEGREES, fast.get_value(), 0.55).move_to([3.4, 0.2, 0]))
        slow_tag = Text('slow orbit', font_size=28, color=AFTER).move_to([-3.4, -2.6, 0])
        fast_tag = Text('fast spin', font_size=28, color=WARNING).move_to([3.4, -2.6, 0])
        self.add(left, right)
        self.play(FadeIn(slow_tag), FadeIn(fast_tag))
        self.at('A slow orbit')
        dizzy = VGroup(*[Arc(radius=0.12 + 0.06 * k, start_angle=k * 1.3, angle=4.2, color=WARNING, stroke_width=3)
                         for k in range(4)]).next_to(fast_tag, RIGHT, buff=0.3)
        self.play(slow.animate.increment_value(0.9), fast.animate.increment_value(9 * TAU / 4),
                  FadeIn(dizzy, rate_func=lambda a: smooth(min(1, 2 * a))), run_time=4, rate_func=linear)
        self.play(slow.animate.increment_value(0.4), fast.animate.increment_value(TAU), run_time=2, rate_func=linear)

        # stop the camera before people read
        self.at('stop the camera first')
        stop = Text('stop, then label', font_size=28, color=FOCUS).to_edge(UP, buff=0.5)
        self.play(FadeIn(stop))

        # [V8.9c] establish, move, hold, point
        self.at('A good rhythm')
        self.play(FadeOut(VGroup(left, right, slow_tag, fast_tag, dizzy, stop)))
        words = ('establish', 'move', 'hold', 'point')
        details = ('a wide view', 'slowly, to the action', 'still', 'only now: labels')
        chips = VGroup()
        for word, detail in zip(words, details):
            chip = VGroup(Text(word, font_size=34), Text(detail, font_size=22, color=SCAFFOLD)).arrange(DOWN, buff=0.15)
            chips.add(chip)
        chips.arrange(RIGHT, buff=1.1)
        fit(chips)
        arrows = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.15, color=GREY_B, stroke_width=4,
                                max_tip_length_to_length_ratio=0.2) for a, b in zip(chips, chips[1:])])
        for chip, phrase, arrow in zip(chips, ('establish', 'move slowly', 'hold still', 'point at things'), (None, *arrows)):
            self.at(phrase)
            self.play(*([GrowArrow(arrow)] if arrow else []), FadeIn(chip, shift=UP * 0.2), run_time=0.7)
        chips[3][0].set_color(FOCUS)
        self.finish()


class Segment_8_10(Segment, ThreeDScene):
    """Behind the scenes in ManimOnline."""
    EPISODE, SEGMENT = 8, '8.10'

    def construct(self):
        # [V8.10a] Python records shapes and camera; the browser shades, sorts and projects
        boxes = VGroup()
        for title, body, color in (('Python', '3D points + camera angles,\nevery frame', BLUE),
                                   ('Browser', 'shade, sort, project', AFTER),
                                   ('Frame', 'a flat SVG picture', FOCUS)):
            text = VGroup(Text(title, font_size=30, color=color), Text(body, font_size=20, color=GREY_A, line_spacing=0.8))
            text.arrange(DOWN, buff=0.15)
            box = RoundedRectangle(width=4.0, height=1.7, corner_radius=0.15).set_stroke(color, 3)
            fit(text, box.width - 0.4)
            boxes.add(VGroup(box, text.move_to(box)))
        boxes.arrange(RIGHT, buff=0.6).shift(UP * 1.8)
        links = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.1, color=GREY_B) for a, b in zip(boxes, boxes[1:])])
        self.play(FadeIn(boxes[0]))
        self.at("doesn't flatten")
        self.play(Indicate(boxes[0][1][1], color=BLUE))
        self.at('Each frame records')
        self.play(GrowArrow(links[0]), FadeIn(boxes[1]))
        self.at('the browser does')
        self.play(GrowArrow(links[1]), FadeIn(boxes[2]))

        # [V8.10b] a rigid spin: the shape once, then a small rotation per frame
        self.at('moves rigidly')
        cube = Cube(side_length=1.6, fill_color=TEAL).rotate(25 * DEGREES, axis=RIGHT).rotate(-35 * DEGREES, axis=UP)
        cube.move_to([-4.2, -1.6, 0])
        axis = np.array([0.3, 1, 0.2])
        cube.add_updater(lambda m, dt: m.rotate(dt * 0.9, axis=axis))
        self.play(FadeIn(cube))
        cards = VGroup()
        for k in range(5):
            card = RoundedRectangle(width=3.8, height=1.5, corner_radius=0.1).set_fill('#15191e', 1).set_stroke(GREY_B, 2)
            card.move_to([0.6 + 0.5 * k, -0.9 - 0.4 * k, 0])
            words = Text("frame 1: all the cube's points" if k == 0 else f'frame {k + 1}: turn by', font_size=18)
            words.next_to(card.get_corner(UL), DR, buff=0.1)
            body = VGroup(words)
            if k:
                body.add(MathTex(r'R_{%d}' % (k + 1), font_size=28, color=AFTER).next_to(words, RIGHT, buff=0.15))
            else:
                corners = VGroup(*[Dot(radius=0.04, color=TEAL).move_to(card.get_center() + np.array([x, y, 0]) * 0.35)
                                   for x in (-1, 0, 1, 2) for y in (-1, 0)])
                body.add(corners.shift(DOWN * 0.15))
            cards.add(VGroup(card, body))
        self.at('Instead of sending')
        self.play(FadeIn(cards[0], shift=LEFT * 0.3))
        self.at('the same cube as before')
        self.play(LaggedStart(*[FadeIn(c, shift=LEFT * 0.3) for c in cards[1:]], lag_ratio=0.3), run_time=2)
        rigid = Text('rigid motion: send the shape once', font_size=28, color=FOCUS).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(rigid))
        self.at('Episode ten')
        self.play(Indicate(rigid, scale_factor=1.05))
        self.finish()


# ---------------------------------------------------------------- recap pictures (flat drawings)

def camera_tile():
    world = VGroup(*[Dot(radius=0.06, color=interpolate_color(BLUE, YELLOW, i / 24)) for i in range(25)])
    world.arrange_in_grid(rows=5, buff=0.3)
    view = Rectangle(width=1.6, height=0.9).set_stroke(WHITE, 3).move_to(world[12])
    small = Rectangle(width=0.4, height=0.225).set_stroke(FOCUS, 3).move_to(world[12])
    return VGroup(world, view, small, Arrow(view.get_corner(UR), small.get_corner(UR), buff=0.05, color=FOCUS,
                                             stroke_width=3, max_tip_length_to_length_ratio=0.3))


def inset_tile():
    ruler = VGroup(Line(LEFT * 1.6, RIGHT * 1.6), *[Line(UP * 0.06, DOWN * 0.06).shift(RIGHT * (i * 0.16 - 1.6))
                                                    for i in range(21)]).shift(DOWN * 0.7)
    small = Rectangle(width=0.4, height=0.3).set_stroke(YELLOW, 3).move_to(ruler).shift(LEFT * 0.4)
    big = Rectangle(width=1.6, height=1.2).set_stroke(YELLOW, 3).move_to([0.9, 0.5, 0])
    links = VGroup(*[DashedLine(small.get_corner(c), big.get_corner(c), color=YELLOW, stroke_width=1.5) for c in (UL, UR, DL, DR)])
    return VGroup(ruler, small, big, links)


def globe_tile():
    globe = Circle(radius=1.0, color=GREY_B, stroke_width=2)
    equator = Ellipse(width=2.0, height=0.5, color=GREY_B, stroke_width=2)
    cam = Dot([0.55, 0.65, 0], color=YELLOW)
    phi_arc = ArcBetweenPoints(UP * 0.55, [0.3, 0.38, 0], angle=-0.6, color=FOCUS, stroke_width=4)
    theta_arc = Arc(radius=0.55, start_angle=-PI / 2 - 0.3, angle=0.9, color=AFTER, stroke_width=4).stretch(0.25, 1)
    labels = VGroup(MathTex(r'\varphi', color=FOCUS, font_size=30).move_to([0.25, 0.75, 0]),
                    MathTex(r'\theta', color=AFTER, font_size=30).move_to([0.35, -0.38, 0]))
    return VGroup(globe, equator, Line(ORIGIN, UP * 1.0, color=RED, stroke_width=2),
                  DashedLine(ORIGIN, cam.get_center(), color=YELLOW, stroke_width=2), cam, phi_arc, theta_arc, labels)


def patches_tile():
    grid = VGroup()
    for i in range(6):
        for j in range(6):
            h = 0.25 * math.sin(i * 0.9) * math.cos(j * 0.9)
            color = interpolate_color(BLUE, YELLOW, (h + 0.25) / 0.5)
            corner = np.array([i * 0.32 + j * 0.16, j * 0.16 + h, 0])
            quad = Polygon(corner, corner + [0.32, 0, 0], corner + [0.48, 0.16, 0], corner + [0.16, 0.16, 0])
            grid.add(quad.set_fill(color, 0.85).set_stroke(WHITE, 1))
    return grid.center()


def painter_tile():
    faces = VGroup()
    for k, color in enumerate((BLUE_E, TEAL_D, TEAL_B)):
        face = Square(1.0).set_fill(color, 1).set_stroke(WHITE, 2).move_to([-0.45 + 0.45 * k, 0.35 - 0.35 * k, 0])
        faces.add(VGroup(face, Text(str(k + 1), font_size=24).move_to(face).shift(DOWN * 0.3 + RIGHT * 0.3)))
    return faces


def helix_tile():
    curve = ParametricFunction(lambda t: np.array([0.8 * math.cos(t), 0.12 * t + 0.25 * math.sin(t), 0]),
                               t_range=[-2 * TAU, 2 * TAU], color=YELLOW)
    label = Text('A helix', font_size=22).next_to(curve, UP, buff=0.15).shift(LEFT * 0.5)
    pin = Square(0.12).set_fill(GREY_B, 1).set_stroke(width=0).next_to(label, LEFT, buff=0.08)
    return VGroup(curve, label, pin)


class Segment_8_11(Segment):
    """Recap."""
    EPISODE, SEGMENT = 8, '8.11'

    def construct(self):
        # [V8.11a] one picture per idea, on its words
        items = [(camera_tile(), 'the camera is a mobject', 'The camera is'),
                 (inset_tile(), 'a magnifying inset', 'A zoomed scene'),
                 (globe_tile(), 'phi and theta', 'phi and theta'),
                 (patches_tile(), 'surfaces of flat patches', 'surfaces and solids'),
                 (painter_tile(), 'shaded, sorted faces', 'flat shaded faces'),
                 (helix_tile(), 'fixed-in-frame text', 'fixed-in-frame')]
        tiles = VGroup()
        for picture, words, _ in items:
            picture.scale_to_fit_height(2.0)
            if picture.width > 3.9:
                picture.scale_to_fit_width(3.9)
            caption = note(words, 26, GREY_A).next_to(picture, DOWN, buff=0.25)
            tiles.add(VGroup(picture, caption))
        for k, tile in enumerate(tiles):
            tile.move_to([(-4.6, 0, 4.6)[k % 3], (1.85, -1.95)[k // 3], 0])
        for tile, (_, _, phrase) in zip(tiles, items):
            self.at(phrase)
            self.play(FadeIn(tile, shift=UP * 0.2), run_time=0.8)

        # [V8.11b] the QR wall, 10 seconds
        self.at('That completes our tour', lead=0.5)
        wall = qr_wall([f'q08-0{i}' for i in range(1, 6)])
        heading = Text('Episode 8 · scan to open each scene', font_size=26, color=SCAFFOLD).to_corner(UL, buff=0.3)
        self.play(FadeOut(tiles), FadeIn(wall), FadeIn(heading))
        self.wait(10)

        # [V8.11c] teaser: a scene becomes a video file (episode 9)
        self.play(FadeOut(VGroup(wall, heading)))
        strip = VGroup(*[RoundedRectangle(width=1.5, height=1.0, corner_radius=0.08).set_stroke(GREY_B, 2)
                         for _ in range(5)]).arrange(RIGHT, buff=0.15)
        frames = VGroup(*[Dot(radius=0.1, color=interpolate_color(BLUE, YELLOW, k / 4)).move_to(s).shift(RIGHT * (0.4 * k / 4 - 0.2))
                          for k, s in enumerate(strip)])
        page = RoundedRectangle(width=1.6, height=2.0, corner_radius=0.12).set_stroke(FOCUS, 3)
        file = VGroup(page, Text('MP4', font_size=30, color=FOCUS).move_to(page))
        file.next_to(strip, RIGHT, buff=1.0)
        group = VGroup(strip, frames, file).move_to(UP * 0.4)
        self.play(LaggedStart(*[FadeIn(VGroup(s, f)) for s, f in zip(strip, frames)], lag_ratio=0.2), run_time=1.5)
        self.play(TransformFromCopy(VGroup(strip, frames), file[0]), FadeIn(file[1]), run_time=1.2)
        nxt = Text('Next: From sketch to shareable', font_size=34).to_edge(DOWN, buff=0.6)
        self.play(Write(nxt))
        self.wait(1.5)
        self.finish()
