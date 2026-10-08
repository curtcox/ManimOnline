"""Small, explicit Manim subset for SVG frame playback (not full Manim)."""
import copy
import json
import math
import sys
import types

FPS = 15
MAX_FRAMES = 901  # 900 timed samples plus a final seekable state.


class Vector(tuple):
    def __new__(cls, values):
        values = list(values)
        return super().__new__(cls, values[:3] + [0] * max(0, 3 - len(values)))

    def __mul__(self, value):
        return Vector(x * value for x in self)

    __rmul__ = __mul__

    def __add__(self, other):
        return Vector(a + b for a, b in zip(self, Vector(other)))

    def __sub__(self, other):
        return Vector(a - b for a, b in zip(self, Vector(other)))


UP, DOWN = Vector((0, 1, 0)), Vector((0, -1, 0))
LEFT, RIGHT = Vector((-1, 0, 0)), Vector((1, 0, 0))
ORIGIN = Vector((0, 0, 0))
OUT, IN = Vector((0, 0, 1)), Vector((0, 0, -1))
UL, UR, DL, DR = UP + LEFT, UP + RIGHT, DOWN + LEFT, DOWN + RIGHT
BLUE, RED, GREEN = '#58C4DD', '#FC6255', '#83C167'
YELLOW, PURPLE, ORANGE = '#FFFF00', '#9A72AC', '#FF8C00'
WHITE, BLACK, GRAY = '#FFFFFF', '#000000', '#888888'
GREY, PINK = GRAY, '#FF69B4'
PI, TAU, DEGREES = math.pi, math.tau, math.pi / 180


class Mobject:
    def __init__(self, color=WHITE, fill_opacity=0, stroke_width=2, **kwargs):
        if kwargs:
            raise NotImplementedError('Unsupported options: ' + ', '.join(kwargs))
        self.position = list(ORIGIN)
        self.color = color
        self.fill_opacity = fill_opacity
        self.stroke_width = stroke_width
        self.opacity = 1
        self.geometry_scale = 1
        self.angle = 0
        self.children = []
        self._type = 'mobject'

    def shift(self, direction):
        self.position = list(Vector(self.position) + direction)
        return self

    def move_to(self, point):
        self.position = list(Vector(point))
        return self

    def _local_bounds(self):
        if self._type == 'circle':
            return (-self.radius, -self.radius, self.radius, self.radius)
        if self._type == 'square':
            half = self.side_length / 2
            return (-half, -half, half, half)
        if self._type == 'rectangle':
            return (-self.width / 2, -self.height / 2, self.width / 2, self.height / 2)
        if self._type in ('line', 'arrow'):
            points = [self.start, self.end]
        elif self._type == 'polygon':
            points = self.vertices
        elif self._type == 'triangle':
            height = math.sqrt(3) / 2
            points = [(0, height * 2 / 3), (-0.5, -height / 3), (0.5, -height / 3)]
        elif self.children:
            bounds = [child._bounds() for child in self.children]
            return (min(b[0] for b in bounds), min(b[1] for b in bounds),
                    max(b[2] for b in bounds), max(b[3] for b in bounds))
        else:
            # Text is anchored at its visual center; font metrics are browser-owned.
            return (0, 0, 0, 0)
        if not points:
            return (0, 0, 0, 0)
        return (min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points))

    def _geometry_center(self):
        left, bottom, right, top = self._local_bounds()
        return Vector(((left + right) / 2, (bottom + top) / 2, 0))

    def get_center(self):
        return Vector(self.position) + self._geometry_center()

    def _bounds(self):
        left, bottom, right, top = self._local_bounds()
        center = self._geometry_center()
        points = []
        for x, y in ((left, bottom), (left, top), (right, bottom), (right, top)):
            dx, dy = (x - center[0]) * self.geometry_scale, (y - center[1]) * self.geometry_scale
            points.append((self.position[0] + center[0] + dx * math.cos(self.angle) - dy * math.sin(self.angle),
                           self.position[1] + center[1] + dx * math.sin(self.angle) + dy * math.cos(self.angle)))
        if self._type == 'circle':
            r = abs(self.radius * self.geometry_scale)
            return (self.position[0] - r, self.position[1] - r, self.position[0] + r, self.position[1] + r)
        return (min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points))

    def scale(self, scale_factor, *, about_point=None):
        if not math.isfinite(scale_factor):
            raise ValueError('Scale factor must be finite')
        if about_point is not None:
            pivot = Vector(about_point)
            center = self.get_center()
            self.shift((center - pivot) * (scale_factor - 1))
        self.geometry_scale *= scale_factor
        return self

    def rotate(self, angle, *, about_point=None):
        if not math.isfinite(angle):
            raise ValueError('Rotation angle must be finite')
        if about_point is not None:
            pivot = Vector(about_point)
            center = self.get_center()
            offset = center - pivot
            rotated = Vector((offset[0] * math.cos(angle) - offset[1] * math.sin(angle),
                              offset[0] * math.sin(angle) + offset[1] * math.cos(angle), offset[2]))
            self.shift(rotated - offset)
        self.angle += angle
        return self

    def set_color(self, color):
        self.color = color
        return self

    def set_fill(self, color=None, opacity=None):
        if color is not None:
            self.color = color
        if opacity is not None:
            self.fill_opacity = opacity
        return self

    def set_stroke(self, color=None, width=None):
        if color is not None:
            self.color = color
        if width is not None:
            self.stroke_width = width
        return self

    def copy(self):
        return copy.deepcopy(self)

    @property
    def animate(self):
        return Animate(self)

    def to_dict(self):
        result = copy.deepcopy(self.__dict__)
        result['type'] = result.pop('_type')
        result['geometry_center'] = list(self._geometry_center())
        result['children'] = [child.to_dict() for child in self.children]
        return result


class Circle(Mobject):
    def __init__(self, radius=1, **kwargs):
        super().__init__(**kwargs)
        self._type, self.radius = 'circle', radius


class Square(Mobject):
    def __init__(self, side_length=2, **kwargs):
        super().__init__(**kwargs)
        self._type, self.side_length = 'square', side_length


class Rectangle(Mobject):
    def __init__(self, width=4, height=2, **kwargs):
        super().__init__(**kwargs)
        self._type, self.width, self.height = 'rectangle', width, height


class Line(Mobject):
    def __init__(self, start=LEFT, end=RIGHT, **kwargs):
        super().__init__(**kwargs)
        self._type = 'line'
        self.start, self.end = list(Vector(start)), list(Vector(end))


class Arrow(Line):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._type = 'arrow'


class Triangle(Mobject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._type = 'triangle'


class Polygon(Mobject):
    def __init__(self, *vertices, **kwargs):
        super().__init__(**kwargs)
        self._type = 'polygon'
        self.vertices = [list(Vector(v)) for v in vertices]


class Text(Mobject):
    def __init__(self, text, font_size=48, **kwargs):
        kwargs.setdefault('fill_opacity', 1)
        super().__init__(**kwargs)
        self._type, self.text, self.font_size = 'text', str(text), font_size


class VGroup(Mobject):
    def __init__(self, *mobjects, **kwargs):
        super().__init__(**kwargs)
        self._type, self.children = 'vgroup', list(mobjects)

    def add(self, *mobjects):
        self.children.extend(mobjects)
        return self


def linear(t):
    return t


def smooth(t):
    return t * t * (3 - 2 * t)


def interpolate(start, end, alpha):
    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
        return start + (end - start) * alpha
    if isinstance(start, list) and isinstance(end, list) and len(start) == len(end):
        return [interpolate(a, b, alpha) for a, b in zip(start, end)]
    if isinstance(start, dict) and isinstance(end, dict):
        return {key: interpolate(value, end.get(key, value), alpha)
                for key, value in start.items()}
    if isinstance(start, str) and isinstance(end, str) and start.startswith('#') and end.startswith('#') and len(start) == len(end) == 7:
        try:
            channels = [round(int(start[i:i+2], 16) * (1-alpha) + int(end[i:i+2], 16) * alpha) for i in (1, 3, 5)]
            return '#' + ''.join(f'{channel:02x}' for channel in channels)
        except ValueError:
            pass
    return copy.deepcopy(end if alpha >= 1 else start)


class Animation:
    def __init__(self, mobject, run_time=1, rate_func=smooth):
        self.mobject, self.run_time, self.rate_func = mobject, run_time, rate_func

    def begin(self, scene):
        scene.add(self.mobject)
        self.start = self.mobject.to_dict()

    def sample(self, alpha):
        return [self.start]

    def finish(self, scene):
        pass


class FadeIn(Animation):
    def sample(self, alpha):
        result = copy.deepcopy(self.start)
        result['opacity'] *= alpha
        return [result]


class Create(Animation):
    """Trace primitive outlines; groups reveal their children simultaneously."""
    def sample(self, alpha):
        result = copy.deepcopy(self.start)
        progress = max(0, min(1, alpha))
        def reveal(data):
            if data['type'] == 'vgroup':
                for child in data['children']:
                    reveal(child)
            elif data['type'] == 'text':
                data['opacity'] *= progress
            else:
                data['draw_progress'] = progress
                data['fill_opacity'] *= progress
        reveal(result)
        return [result]


class Uncreate(Create):
    def sample(self, alpha):
        return super().sample(1 - alpha)

    def finish(self, scene):
        scene.remove(self.mobject)


# Text glyph path tracing is not implemented; Write remains an opacity reveal.
class Write(FadeIn):
    pass


class FadeOut(Animation):
    def sample(self, alpha):
        result = copy.deepcopy(self.start)
        result['opacity'] *= 1 - alpha
        return [result]

    def finish(self, scene):
        scene.remove(self.mobject)


class Transform(Animation):
    def __init__(self, mobject, target_mobject, **kwargs):
        super().__init__(mobject, **kwargs)
        self.target = target_mobject.copy()

    def sample(self, alpha):
        target = self.target.to_dict()
        if self.start['type'] == target['type']:
            return [interpolate(self.start, target, alpha)]
        # Different geometry is crossfaded rather than claiming path morphing.
        source = copy.deepcopy(self.start)
        source['opacity'] *= 1 - alpha
        target['opacity'] *= alpha
        return [source, target]

    def finish(self, scene):
        self.mobject.__dict__ = copy.deepcopy(self.target.__dict__)


class Rotate(Animation):
    """Sample a rigid rotation from the original object rather than its endpoints."""
    def __init__(self, mobject, angle=PI, axis=OUT, about_point=None, **kwargs):
        super().__init__(mobject, **kwargs)
        if not math.isfinite(angle):
            raise ValueError('Rotation angle must be finite')
        axis = Vector(axis)
        if axis not in (OUT, IN):
            raise NotImplementedError('Only 2D rotation about OUT or IN is supported')
        self.angle = angle if axis == OUT else -angle
        self.about_point = Vector(about_point) if about_point is not None else None

    def begin(self, scene):
        super().begin(scene)
        self.original = self.mobject.copy()

    def sample(self, alpha):
        current = self.original.copy()
        current.rotate(self.angle * alpha, about_point=self.about_point)
        return [current.to_dict()]

    def finish(self, scene):
        final = self.original.copy().rotate(self.angle, about_point=self.about_point)
        self.mobject.__dict__ = copy.deepcopy(final.__dict__)


class Rotating(Rotate):
    def __init__(self, mobject, angle=TAU, axis=OUT, about_point=None,
                 run_time=5, rate_func=linear, **kwargs):
        super().__init__(mobject, angle, axis, about_point,
                         run_time=run_time, rate_func=rate_func, **kwargs)


class ReplacementTransform(Transform):
    def __init__(self, mobject, target_mobject, **kwargs):
        super().__init__(mobject, target_mobject, **kwargs)
        self.replacement = target_mobject

    def finish(self, scene):
        scene.remove(self.mobject)
        scene.add(self.replacement)


class Animate(Transform):
    def __init__(self, mobject):
        super().__init__(mobject, mobject)

    def __getattr__(self, name):
        if name not in ('shift', 'move_to', 'set_color', 'set_fill', 'set_stroke', 'scale', 'rotate'):
            raise NotImplementedError(f'animate.{name} is not supported yet')
        def apply(*args, **kwargs):
            getattr(self.target, name)(*args, **kwargs)
            return self
        return apply


class Scene:
    def __init__(self):
        self.mobjects, self.frames = [], []

    def add(self, *mobjects):
        for mobject in mobjects:
            if mobject not in self.mobjects:
                self.mobjects.append(mobject)
        return self

    def remove(self, *mobjects):
        self.mobjects = [m for m in self.mobjects if m not in mobjects]
        return self

    def capture(self, overrides=None):
        if len(self.frames) >= MAX_FRAMES:
            raise ValueError('Preview exceeds 60 seconds / 900 frames. Shorten the scene.')
        objects = []
        for mobject in self.mobjects:
            objects.extend(overrides[mobject] if overrides and mobject in overrides else [mobject.to_dict()])
        self.frames.append({'mobjects': objects})

    def play(self, *animations, run_time=None, rate_func=None, **kwargs):
        if kwargs:
            raise NotImplementedError('Unsupported play options: ' + ', '.join(kwargs))
        if not animations or any(not isinstance(a, Animation) for a in animations):
            raise TypeError('play() expects supported animations such as Create or Transform')
        if len({id(a.mobject) for a in animations}) != len(animations):
            raise ValueError('Use one animation per object in each play() call')
        durations = [a.run_time if run_time is None else run_time for a in animations]
        if any(not math.isfinite(d) or d <= 0 for d in durations):
            raise ValueError('Animation run_time must be positive and finite')
        count = max(1, math.ceil(max(durations) * FPS))
        if count + len(self.frames) >= MAX_FRAMES:
            raise ValueError('Preview exceeds 60 seconds / 900 frames. Shorten the scene.')
        for animation in animations:
            animation.begin(self)
        for frame in range(count):
            time = frame / FPS
            overrides = {a.mobject: a.sample((rate_func or a.rate_func)(min(1, time / duration)))
                         for a, duration in zip(animations, durations)}
            self.capture(overrides)
        for animation in animations:
            animation.finish(self)

    def wait(self, duration=1):
        if not math.isfinite(duration) or duration < 0:
            raise ValueError('Wait duration must be nonnegative and finite')
        count = math.ceil(duration * FPS)
        if count + len(self.frames) >= MAX_FRAMES:
            raise ValueError('Preview exceeds 60 seconds / 900 frames. Shorten the scene.')
        for _ in range(count):
            self.capture()

    def construct(self):
        pass

    def render(self):
        self.construct()
        # A final state is always seekable, including after FadeOut or Transform.
        self.capture()
        return {'frames': self.frames, 'fps': FPS, 'duration': (len(self.frames)-1)/FPS}


EXPORTS = ['Scene', 'Mobject', 'Circle', 'Square', 'Rectangle', 'Line', 'Arrow',
           'Triangle', 'Polygon', 'Text', 'VGroup', 'Create', 'Write', 'FadeIn',
           'FadeOut', 'Uncreate', 'Rotate', 'Rotating', 'Transform', 'ReplacementTransform', 'UP', 'DOWN', 'LEFT',
           'RIGHT', 'ORIGIN', 'OUT', 'IN', 'UL', 'UR', 'DL', 'DR', 'BLUE', 'RED', 'GREEN',
           'YELLOW', 'PURPLE', 'ORANGE', 'WHITE', 'BLACK', 'GRAY', 'GREY', 'PINK',
           'linear', 'smooth', 'PI', 'TAU', 'DEGREES']


def render_scene(source, scene_name=None):
    module = types.ModuleType('manim')
    module.__all__ = EXPORTS
    for name in EXPORTS:
        setattr(module, name, globals()[name])
    sys.modules['manim'] = module
    namespace = {'__name__': '__scene__'}
    exec(compile(source, '<scene>', 'exec'), namespace)
    scenes = {name: cls for name, cls in namespace.items()
              if isinstance(cls, type) and issubclass(cls, Scene) and cls is not Scene
              and cls.__module__ == '__scene__'}
    if not scenes:
        raise ValueError('No Scene class found. Define a Scene subclass with construct().')
    if scene_name and scene_name not in scenes:
        raise ValueError(f'Scene {scene_name!r} was not found in this source.')
    name = scene_name or next(iter(scenes))
    result = scenes[name]().render()
    result['scene'] = name
    result['scenes'] = list(scenes)
    return json.dumps(result, allow_nan=False)
