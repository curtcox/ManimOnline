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
    def __init__(self, color=WHITE, fill_opacity=0, stroke_width=2,
                 fill_color=None, stroke_color=None, stroke_opacity=1, z_index=0, **kwargs):
        if kwargs:
            raise NotImplementedError('Unsupported options: ' + ', '.join(kwargs))
        self.position = list(ORIGIN)
        self.color = color
        self.fill_color = color if fill_color is None else fill_color
        self.stroke_color = color if stroke_color is None else stroke_color
        self._validate_opacity(fill_opacity)
        self._validate_opacity(stroke_opacity)
        self._validate_width(stroke_width)
        self.fill_opacity = fill_opacity
        self.stroke_opacity = stroke_opacity
        self.stroke_width = stroke_width
        self.opacity = 1
        self.geometry_scale = 1
        self.angle = 0
        self.children = []
        self.set_z_index(z_index)
        self._type = 'mobject'

    def shift(self, direction):
        self.position = list(Vector(self.position) + direction)
        return self

    def move_to(self, point):
        target = point.get_center() if isinstance(point, Mobject) else Vector(point)
        if not all(math.isfinite(v) for v in target):
            raise ValueError('Position must be finite')
        return self.shift(target - self.get_center())

    def _critical_point(self, direction):
        left, bottom, right, top = self._bounds()
        x, y, _ = direction
        return Vector((right if x > 0 else left if x < 0 else (left + right) / 2,
                       top if y > 0 else bottom if y < 0 else (bottom + top) / 2,
                       self.get_center()[2]))

    def next_to(self, mobject_or_point, direction=RIGHT, buff=0.25, aligned_edge=ORIGIN):
        direction, aligned_edge = Vector(direction), Vector(aligned_edge)
        if not all(math.isfinite(v) for v in (*direction, *aligned_edge, buff)):
            raise ValueError('Layout coordinates and buffer must be finite')
        if direction[2] or aligned_edge[2]:
            raise NotImplementedError('Layout supports only XY directions')
        if not any(direction):
            raise ValueError('Layout direction must be nonzero')
        target = (mobject_or_point._critical_point(aligned_edge + direction)
                  if isinstance(mobject_or_point, Mobject) else Vector(mobject_or_point))
        if not all(math.isfinite(v) for v in target):
            raise ValueError('Layout target must be finite')
        anchor = self._critical_point(aligned_edge - direction)
        return self.shift(target - anchor + direction * buff)

    def _local_bounds(self):
        if self._type == 'circle':
            return (-self.radius, -self.radius, self.radius, self.radius)
        if self._type == 'arc':
            angles = [self.start_angle, self.start_angle + self.arc_angle]
            for angle in (0, PI / 2, PI, 3 * PI / 2):
                distance = ((angle - self.start_angle) % TAU if self.arc_angle >= 0
                            else (self.start_angle - angle) % TAU)
                if distance <= abs(self.arc_angle):
                    angles.append(angle)
            points = [(self.radius * math.cos(a), self.radius * math.sin(a)) for a in angles]
            return (min(p[0] for p in points), min(p[1] for p in points),
                    max(p[0] for p in points), max(p[1] for p in points))
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

    def point_from_proportion(self, alpha):
        """Sample supported XY outlines by distance, then apply SVG geometry transforms."""
        if not math.isfinite(alpha) or not 0 <= alpha <= 1:
            raise ValueError('Path proportion must be finite and between 0 and 1')
        if self._type in ('circle', 'arc'):
            if not math.isfinite(self.radius) or self.radius < 0:
                raise ValueError('Path radius must be nonnegative and finite')
            angle = TAU * alpha if self._type == 'circle' else self.start_angle + self.arc_angle * alpha
            point = Vector((self.radius * math.cos(angle), self.radius * math.sin(angle), 0))
        else:
            closed = True
            if self._type == 'line':
                vertices, closed = [self.start, self.end], False
            elif self._type == 'polygon':
                vertices = self.vertices
            elif self._type in ('square', 'rectangle'):
                width = self.side_length if self._type == 'square' else self.width
                height = self.side_length if self._type == 'square' else self.height
                vertices = [(width / 2, height / 2), (-width / 2, height / 2),
                            (-width / 2, -height / 2), (width / 2, -height / 2)]
            elif self._type == 'triangle':
                height = math.sqrt(3) / 2
                vertices = [(0, height * 2 / 3), (-0.5, -height / 3), (0.5, -height / 3)]
            else:
                raise NotImplementedError('Paths support Circle, Arc, Line, Polygon, Square, Rectangle, and Triangle')
            if len(vertices) < 2:
                raise ValueError('A path needs at least two vertices')
            vertices = [Vector(v) for v in vertices]
            if any(not all(math.isfinite(c) for c in v) for v in vertices):
                raise ValueError('Path coordinates must be finite')
            if any(v[2] for v in vertices):
                raise NotImplementedError('Paths support only the XY plane')
            points = vertices + [vertices[0]] if closed else vertices
            segments = [(a, b, math.dist(a, b)) for a, b in zip(points, points[1:])]
            total = sum(length for _, _, length in segments)
            if not math.isfinite(total):
                raise ValueError('Path length must be finite')
            remaining = total * alpha
            point = points[-1]
            for start, end, length in segments:
                if length > 0 and remaining <= length:
                    point = start + (end - start) * (remaining / length)
                    break
                remaining -= length
        return self._point_to_world(point)

    def _point_to_world(self, point):
        if self.position[2]:
            raise NotImplementedError('Paths support only the XY plane')
        center = self._geometry_center()
        offset = (point - center) * self.geometry_scale
        point = Vector(self.position) + center + Vector((
            offset[0] * math.cos(self.angle) - offset[1] * math.sin(self.angle),
            offset[0] * math.sin(self.angle) + offset[1] * math.cos(self.angle), 0))
        if not all(math.isfinite(v) for v in point):
            raise ValueError('Path coordinates must be finite')
        return point

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

    @staticmethod
    def _validate_opacity(opacity):
        if not math.isfinite(opacity) or not 0 <= opacity <= 1:
            raise ValueError('Opacity must be finite and between 0 and 1')

    @staticmethod
    def _validate_width(width):
        if not math.isfinite(width) or width < 0:
            raise ValueError('Stroke width must be nonnegative and finite')

    def set_color(self, color, family=True):
        self.color = color
        self.fill_color = self.stroke_color = color
        if family:
            for child in self.children:
                child.set_color(color)
        return self

    def set_fill(self, color=None, opacity=None, family=True):
        if opacity is not None:
            self._validate_opacity(opacity)
        if color is not None:
            self.fill_color = color
        if opacity is not None:
            self.fill_opacity = opacity
        if family:
            for child in self.children:
                child.set_fill(color, opacity)
        return self

    def set_stroke(self, color=None, width=None, opacity=None, family=True):
        if width is not None:
            self._validate_width(width)
        if opacity is not None:
            self._validate_opacity(opacity)
        if color is not None:
            self.stroke_color = color
        if width is not None:
            self.stroke_width = width
        if opacity is not None:
            self.stroke_opacity = opacity
        if family:
            for child in self.children:
                child.set_stroke(color, width, opacity)
        return self

    def set_opacity(self, opacity, family=True):
        self._validate_opacity(opacity)
        self.set_fill(opacity=opacity, family=family)
        self.set_stroke(opacity=opacity, family=family)
        return self

    def set_z_index(self, z_index_value, family=True):
        if not isinstance(z_index_value, (int, float)) or not math.isfinite(z_index_value):
            raise ValueError('z_index must be a finite number')
        self.z_index = z_index_value
        if family:
            for child in self.children:
                child.set_z_index(z_index_value, family=True)
        return self

    def copy(self):
        return copy.deepcopy(self)

    def save_state(self):
        # Replace the checkpoint without nesting earlier checkpoints inside it.
        self._saved_state = copy.deepcopy({key: value for key, value in self.__dict__.items()
                                          if key != '_saved_state'})
        return self

    def restore(self):
        if '_saved_state' not in self.__dict__:
            raise ValueError('Call save_state() before restoring an object')
        saved = self._saved_state
        self.__dict__ = copy.deepcopy(saved)
        self._saved_state = saved
        return self

    @property
    def animate(self):
        return Animate(self)

    def to_dict(self):
        result = copy.deepcopy({key: value for key, value in self.__dict__.items()
                                if key not in ('_saved_state', 'children')})
        result['type'] = result.pop('_type')
        result['geometry_center'] = list(self._geometry_center())
        result['children'] = [child.to_dict() for child in self.children]
        return result


class Circle(Mobject):
    def __init__(self, radius=1, **kwargs):
        super().__init__(**kwargs)
        self._type, self.radius = 'circle', radius


class Arc(Mobject):
    def __init__(self, radius=1, start_angle=0, angle=PI / 2, arc_center=ORIGIN, **kwargs):
        center = Vector(arc_center)
        if not all(math.isfinite(v) for v in (radius, start_angle, angle, *center)) or radius < 0:
            raise ValueError('Arc geometry must be finite with a nonnegative radius')
        if center[2]:
            raise NotImplementedError('Arcs support only the XY plane')
        if abs(angle) > TAU:
            raise NotImplementedError('Arcs support at most one full turn')
        super().__init__(**kwargs)
        self._type, self.radius = 'arc', radius
        self.start_angle, self.arc_angle = start_angle % TAU, angle
        self.position = list(center)

    def get_arc_center(self):
        return self._point_to_world(ORIGIN)

    def move_arc_center_to(self, point):
        point = Vector(point)
        if not all(math.isfinite(v) for v in point):
            raise ValueError('Arc center must be finite')
        if point[2]:
            raise NotImplementedError('Arcs support only the XY plane')
        return self.shift(point - self.get_arc_center())


class Dot(Circle):
    def __init__(self, point=ORIGIN, radius=0.08, **kwargs):
        kwargs.setdefault('fill_opacity', 1)
        kwargs.setdefault('stroke_width', 0)
        super().__init__(radius=radius, **kwargs)
        self.move_to(point)


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

    @staticmethod
    def _endpoints(start, end):
        start, end = Vector(start), Vector(end)
        if not all(math.isfinite(v) for v in (*start, *end)):
            raise ValueError('Line endpoints must be finite')
        if start[2] or end[2]:
            raise NotImplementedError('Line endpoints support only the XY plane')
        return start, end

    def get_start(self):
        self._endpoints(self.start, self.end)
        return self._point_to_world(Vector(self.start))

    def get_end(self):
        self._endpoints(self.start, self.end)
        return self._point_to_world(Vector(self.end))

    def get_start_and_end(self):
        return self.get_start(), self.get_end()

    def get_vector(self):
        return self.get_end() - self.get_start()

    def get_length(self):
        return math.dist(self.get_start(), self.get_end())

    def get_unit_vector(self):
        length = self.get_length()
        return self.get_vector() * (1 / length) if length else ORIGIN

    def get_angle(self):
        vector = self.get_vector()
        return math.atan2(vector[1], vector[0]) if any(vector) else 0

    def put_start_and_end_on(self, start, end):
        start, end = self._endpoints(start, end)
        # Encode the requested endpoints in the current transform's local space.
        # This keeps ordinary endpoint animations linear even on rotated lines.
        scale = self.geometry_scale or 1
        center = (start + end) * 0.5
        def local(point):
            dx, dy, _ = point - center
            return [(dx * math.cos(self.angle) + dy * math.sin(self.angle)) / scale,
                    (-dx * math.sin(self.angle) + dy * math.cos(self.angle)) / scale, 0]
        local_start, local_end = self._endpoints(local(start), local(end))
        self.start, self.end = list(local_start), list(local_end)
        self.position = list(center)
        self.geometry_scale = scale
        return self


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
        kwargs.setdefault('stroke_width', 0)
        super().__init__(**kwargs)
        self._type, self.text, self.font_size = 'text', str(text), font_size


class MathTex(Text):
    """A single formula rendered as SVG paths by the browser's math backend."""
    def __init__(self, *tex_strings, arg_separator=' ', font_size=48, **kwargs):
        if not all(isinstance(value, str) for value in (*tex_strings, arg_separator)):
            raise TypeError('MathTex expects TeX strings')
        if not math.isfinite(font_size) or font_size <= 0:
            raise ValueError('MathTex font_size must be positive and finite')
        text = arg_separator.join(tex_strings)
        if len(text) > 4096:
            raise ValueError('MathTex expressions are limited to 4096 characters')
        super().__init__(text, font_size=font_size, **kwargs)
        self._type = 'mathtex'


class VGroup(Mobject):
    def __init__(self, *mobjects, **kwargs):
        super().__init__(**kwargs)
        self._type, self.children = 'vgroup', list(mobjects)

    def add(self, *mobjects):
        self.children.extend(mobjects)
        return self

    def __iter__(self):
        return iter(self.children)

    def arrange(self, direction=RIGHT, buff=0.25, center=True, aligned_edge=ORIGIN):
        if self.geometry_scale != 1 or self.angle != 0:
            raise NotImplementedError('Arrange the group before scaling or rotating it')
        # Child positions are local to this group; its translation is preserved
        # when center=False, and centering moves the whole arranged group.
        for previous, current in zip(self.children, self.children[1:]):
            current.next_to(previous, direction, buff, aligned_edge)
        if center:
            self.move_to(ORIGIN)
        return self


def linear(t):
    return t


def smooth(t):
    return t * t * (3 - 2 * t)


def there_and_back(t):
    return smooth(2 * t if t <= 0.5 else 2 * (1 - t))


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

    def objects(self):
        return [self.mobject]

    def prepare(self, scene):
        self.begin(scene)
        # Compute the held terminal frame without changing the live scene early.
        terminal = copy.deepcopy(self)
        staging = Scene().add(terminal.mobject)
        terminal.finish(staging)
        self._terminal = [m.to_dict() for m in staging.mobjects]

    def states(self, alpha, rate_func=None):
        if alpha >= 1:
            result = self._terminal
        else:
            result = self.sample((rate_func or self.rate_func)(max(0, alpha)))
        return {self.mobject: result}


class FadeIn(Animation):
    def sample(self, alpha):
        result = copy.deepcopy(self.start)
        result['opacity'] *= alpha
        return [result]


class GrowFromPoint(Animation):
    """Scale a snapshot from a fixed XY point to its original geometry."""
    def __init__(self, mobject, point, **kwargs):
        super().__init__(mobject, **kwargs)
        self.point = Vector(point)
        if not all(math.isfinite(v) for v in self.point):
            raise ValueError('Growth point must be finite')
        if self.point[2]:
            raise NotImplementedError('Growth supports only the XY plane')

    def begin(self, scene):
        center = self.mobject.get_center()
        if not all(math.isfinite(v) for v in center):
            raise ValueError('Growth center must be finite')
        if center[2]:
            raise NotImplementedError('Growth supports only the XY plane')
        super().begin(scene)
        self.original = self.mobject.copy()

    def sample(self, alpha):
        current = self.original.copy().scale(alpha, about_point=self.point)
        return [current.to_dict()]


class GrowFromCenter(GrowFromPoint):
    def __init__(self, mobject, **kwargs):
        super().__init__(mobject, ORIGIN, **kwargs)

    def begin(self, scene):
        # Resolve the center at playback start, after any previous animations.
        self.point = self.mobject.get_center()
        super().begin(scene)


class ShrinkToCenter(GrowFromCenter):
    def __init__(self, mobject, remover=False, **kwargs):
        super().__init__(mobject, **kwargs)
        self.remover = remover

    def sample(self, alpha):
        return super().sample(1 - alpha)

    def finish(self, scene):
        self.mobject.scale(0)
        if self.remover:
            scene.remove(self.mobject)


class Create(Animation):
    """Trace primitive outlines; groups reveal their children simultaneously."""
    def sample(self, alpha):
        result = copy.deepcopy(self.start)
        progress = max(0, min(1, alpha))
        def reveal(data):
            if data['type'] == 'vgroup':
                for child in data['children']:
                    reveal(child)
            elif data['type'] in ('text', 'mathtex'):
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
        if (self.start['type'] == target['type'] and
                (target['type'] != 'mathtex' or self.start['text'] == target['text'])):
            return [interpolate(self.start, target, alpha)]
        # Different geometry is crossfaded rather than claiming path morphing.
        source = copy.deepcopy(self.start)
        source['opacity'] *= 1 - alpha
        target['opacity'] *= alpha
        return [source, target]

    def finish(self, scene):
        saved = self.mobject.__dict__.get('_saved_state')
        self.mobject.__dict__ = copy.deepcopy(self.target.__dict__)
        self.mobject.__dict__.pop('_saved_state', None)
        if saved is not None:
            self.mobject._saved_state = saved


class TransformFromCopy(Transform):
    """Animate the target from a source snapshot, leaving both live objects intact."""
    def __init__(self, mobject, target_mobject, **kwargs):
        if not isinstance(mobject, Mobject) or not isinstance(target_mobject, Mobject):
            raise TypeError('TransformFromCopy expects two mobjects')
        if mobject is target_mobject:
            raise ValueError('TransformFromCopy source and target must be different objects')
        super().__init__(target_mobject, target_mobject, **kwargs)
        self.source = mobject

    def begin(self, scene):
        # Only the target is animated/added. The source is a read-only snapshot,
        # so it may also move independently or belong to a scene-added group.
        super().begin(scene)
        self.start = self.source.to_dict()
        self.target = self.mobject.copy()

    def sample(self, alpha):
        if alpha == 0:
            return [copy.deepcopy(self.start)]
        return super().sample(alpha)

    def finish(self, scene):
        pass


class Restore(Transform):
    def __init__(self, mobject, **kwargs):
        # The target is snapshotted now, as for other Transform animations.
        super().__init__(mobject, mobject.copy().restore(), **kwargs)


class Indicate(Animation):
    """Temporarily scale and recolor a snapshot without changing live state."""
    def __init__(self, mobject, scale_factor=1.2, color=YELLOW,
                 rate_func=there_and_back, **kwargs):
        super().__init__(mobject, rate_func=rate_func, **kwargs)
        if not math.isfinite(scale_factor) or scale_factor < 0:
            raise ValueError('Indicate scale_factor must be nonnegative and finite')
        self.scale_factor, self.color = scale_factor, color

    def begin(self, scene):
        super().begin(scene)
        self.highlight = self.mobject.copy().scale(self.scale_factor).set_color(self.color).to_dict()

    def sample(self, alpha):
        if alpha == 0:
            return [copy.deepcopy(self.start)]
        return [interpolate(self.start, self.highlight, alpha)]


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


class MoveAlongPath(Animation):
    def __init__(self, mobject, path, **kwargs):
        if not isinstance(path, Mobject):
            raise TypeError('MoveAlongPath expects a supported shape as its path')
        if mobject is path:
            raise ValueError('The moving object and path must be different objects')
        super().__init__(mobject, **kwargs)
        self.path = path

    def begin(self, scene):
        self.path_snapshot = self.path.copy()
        # Validate before adding the moving object to the scene.
        self.path_snapshot.point_from_proportion(0)
        super().begin(scene)
        self.original = self.mobject.copy()

    def sample(self, alpha):
        current = self.original.copy().move_to(self.path_snapshot.point_from_proportion(alpha))
        return [current.to_dict()]

    def finish(self, scene):
        self.mobject.move_to(self.path_snapshot.point_from_proportion(1))


class ReplacementTransform(Transform):
    def __init__(self, mobject, target_mobject, **kwargs):
        super().__init__(mobject, target_mobject, **kwargs)
        self.replacement = target_mobject

    def finish(self, scene):
        scene.remove(self.mobject)
        scene.add(self.replacement)

    def objects(self):
        return [self.mobject, self.replacement]


class Animate(Transform):
    def __init__(self, mobject):
        super().__init__(mobject, mobject)
        self.operations = []

    def begin(self, scene):
        # Relative method chains resolve against the state at this stage's start.
        self.target = self.mobject.copy()
        for name, args, kwargs in self.operations:
            getattr(self.target, name)(*args, **kwargs)
        super().begin(scene)

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        if name not in ('shift', 'move_to', 'move_arc_center_to', 'put_start_and_end_on', 'next_to', 'arrange', 'set_color', 'set_fill', 'set_stroke', 'set_opacity', 'set_z_index', 'restore', 'scale', 'rotate'):
            raise NotImplementedError(f'animate.{name} is not supported yet')
        def apply(*args, **kwargs):
            getattr(self.target, name)(*args, **kwargs)
            self.operations.append((name, args, kwargs))
            return self
        return apply


class AnimationGroup:
    """Combine independent animations on a timeline, optionally overlapping."""
    def __init__(self, *animations, lag_ratio=0, run_time=None, rate_func=linear):
        if not animations or any(not isinstance(a, (Animation, AnimationGroup)) for a in animations):
            raise TypeError('AnimationGroup expects at least one supported animation')
        if not math.isfinite(lag_ratio) or lag_ratio < 0:
            raise ValueError('lag_ratio must be nonnegative and finite')
        self.animations, self.rate_func = animations, rate_func
        self.timings = []
        start = 0
        for animation in animations:
            if not math.isfinite(animation.run_time) or animation.run_time <= 0:
                raise ValueError('Animation run_time must be positive and finite')
            self.timings.append((start, animation.run_time))
            start += lag_ratio * animation.run_time
        self.natural_duration = max(start + duration for start, duration in self.timings)
        if not math.isfinite(self.natural_duration):
            raise ValueError('Animation timeline duration must be finite')
        self.run_time = self.natural_duration if run_time is None else run_time
        if not math.isfinite(self.run_time) or self.run_time <= 0:
            raise ValueError('Animation run_time must be positive and finite')

    def objects(self):
        return [m for animation in self.animations for m in animation.objects()]

    def prepare(self, scene):
        for animation in self.animations:
            animation.prepare(scene)

    def states(self, alpha, rate_func=None):
        time = self.natural_duration if alpha >= 1 else (rate_func or self.rate_func)(max(0, alpha)) * self.natural_duration
        result = {}
        for animation, (start, duration) in zip(self.animations, self.timings):
            result.update(animation.states((time - start) / duration))
        return result

    def finish(self, scene):
        for animation in self.animations:
            animation.finish(scene)


class LaggedStart(AnimationGroup):
    def __init__(self, *animations, lag_ratio=0.05, **kwargs):
        super().__init__(*animations, lag_ratio=lag_ratio, **kwargs)


class Succession(AnimationGroup):
    """Prepare consecutive stages from preceding terminal states on an isolated scene."""
    def __init__(self, *animations, lag_ratio=1, **kwargs):
        if lag_ratio != 1:
            raise NotImplementedError('Succession supports non-overlapping stages with lag_ratio=1')
        super().__init__(*animations, lag_ratio=1, **kwargs)

    def objects(self):
        return list(dict.fromkeys(super().objects()))

    def prepare(self, scene):
        owned = self.objects()
        self._initial = [m for m in owned if m in scene.mobjects]
        memo = {}
        roots, animations = copy.deepcopy((scene.mobjects, self.animations), memo)
        staging = Scene().add(*roots)
        originals = {}
        def remember(mobject):
            originals[id(memo[id(mobject)])] = mobject
            for child in mobject.children:
                remember(child)
        for root in scene.mobjects + owned:
            remember(root)
        self._stages = []
        for animation in animations:
            staging.validate(animation)
            animation.prepare(staging)
            baseline = {originals[id(m)]: [m.to_dict()] for m in staging.mobjects
                        if originals[id(m)] in owned}
            # Remap only identity keys; start/terminal geometry stays snapshotted.
            prepared = copy.deepcopy(animation, originals.copy())
            self._stages.append((baseline, prepared))
            animation.finish(staging)
        # Placeholder roots allow capture() to include later introductions. Their
        # states remain empty until the relevant stage; geometry stays untouched.
        scene.add(*owned)

    def states(self, alpha, rate_func=None):
        time = self.natural_duration if alpha >= 1 else (rate_func or self.rate_func)(max(0, alpha)) * self.natural_duration
        stage = 0
        for index, (start, _) in enumerate(self.timings):
            if start <= time:
                stage = index
        start, duration = self.timings[stage]
        baseline, animation = self._stages[stage]
        result = {m: [] for m in self.objects()}
        result.update(baseline)
        result.update(animation.states((time - start) / duration))
        return result

    def finish(self, scene):
        scene.remove(*(m for m in self.objects() if m not in self._initial))
        for animation in self.animations:
            animation.prepare(scene)
            animation.finish(scene)


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

    def _ordered_roots(self, mobjects):
        if any(not isinstance(m, Mobject) for m in mobjects):
            raise TypeError('Scene ordering expects Mobjects')
        roots = list(dict.fromkeys(mobjects))
        def family(m):
            return [m] + [member for child in m.children for member in family(child)]
        # Reject unsupported family restructuring before changing the scene.
        for root in self.mobjects + roots:
            for obj in roots:
                if obj is not root and (obj in family(root) or root in family(obj)):
                    raise NotImplementedError('Reorder whole scene groups, not individual group children')
        return roots

    def bring_to_front(self, *mobjects):
        roots = self._ordered_roots(mobjects)
        self.remove(*roots)
        self.add(*roots)
        return self

    def bring_to_back(self, *mobjects):
        roots = self._ordered_roots(mobjects)
        self.remove(*roots)
        self.mobjects = roots + self.mobjects
        return self

    def clear(self):
        self.mobjects = []
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
        if not animations or any(not isinstance(a, (Animation, AnimationGroup)) for a in animations):
            raise TypeError('play() expects supported animations such as Create or Transform')
        self.validate(*animations)
        durations = [a.run_time if run_time is None else run_time for a in animations]
        if any(not math.isfinite(d) or d <= 0 for d in durations):
            raise ValueError('Animation run_time must be positive and finite')
        count = max(1, math.ceil(max(durations) * FPS))
        if count + len(self.frames) >= MAX_FRAMES:
            raise ValueError('Preview exceeds 60 seconds / 900 frames. Shorten the scene.')
        for animation in animations:
            animation.prepare(self)
        for frame in range(count):
            time = frame / FPS
            overrides = {}
            for animation, duration in zip(animations, durations):
                overrides.update(animation.states(time / duration, rate_func))
            self.capture(overrides)
        for animation in animations:
            animation.finish(self)

    def validate(self, *animations):
        objects = [m for a in animations for m in a.objects()]
        def family(mobject):
            return [mobject] + [m for child in mobject.children for m in family(child)]
        members = [m for obj in objects for m in family(obj)]
        if len({id(m) for m in members}) != len(members):
            raise ValueError('Use one animation per object in each play() call')
        for root in self.mobjects:
            for obj in objects:
                if obj is not root and obj in family(root):
                    raise NotImplementedError('Animate the whole scene-added group, not an individual child')
                if root is not obj and root in family(obj):
                    raise NotImplementedError('Remove scene-added children before animating their containing group')

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


EXPORTS = ['Scene', 'Mobject', 'Circle', 'Arc', 'Dot', 'Square', 'Rectangle', 'Line', 'Arrow',
           'Triangle', 'Polygon', 'Text', 'MathTex', 'VGroup', 'Create', 'Write', 'FadeIn',
           'AnimationGroup', 'LaggedStart', 'Succession', 'MoveAlongPath',
           'GrowFromCenter', 'GrowFromPoint', 'ShrinkToCenter', 'Restore', 'Indicate', 'TransformFromCopy',
           'FadeOut', 'Uncreate', 'Rotate', 'Rotating', 'Transform', 'ReplacementTransform', 'UP', 'DOWN', 'LEFT',
           'RIGHT', 'ORIGIN', 'OUT', 'IN', 'UL', 'UR', 'DL', 'DR', 'BLUE', 'RED', 'GREEN',
           'YELLOW', 'PURPLE', 'ORANGE', 'WHITE', 'BLACK', 'GRAY', 'GREY', 'PINK',
           'linear', 'smooth', 'there_and_back', 'PI', 'TAU', 'DEGREES']


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
