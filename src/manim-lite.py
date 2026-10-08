"""Small, explicit Manim subset for SVG frame playback (not full Manim)."""
import copy
import inspect
import json
import math
import operator
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
BLUE_D = '#29ABCA'
BLUE, RED, GREEN = '#58C4DD', '#FC6255', '#83C167'
YELLOW, PURPLE, ORANGE = '#FFFF00', '#9A72AC', '#FF8C00'
WHITE, BLACK, GRAY = '#FFFFFF', '#000000', '#888888'
GREY, PINK = GRAY, '#FF69B4'
PI, TAU, DEGREES = math.pi, math.tau, math.pi / 180


class PreviewConfig:
    """Validated 2D preview settings; not the full Community config object."""
    def __init__(self, **kwargs):
        self.pixel_width, self.pixel_height = 800, 450
        self.frame_height, self.background_color = 9, BLACK
        for name, value in kwargs.items():
            setattr(self, name, value)

    @property
    def frame_width(self):
        return self.frame_height * self.pixel_width / self.pixel_height

    @frame_width.setter
    def frame_width(self, value):
        self.frame_height = value * self.pixel_height / self.pixel_width

    def __setattr__(self, name, value):
        if name in ('pixel_width', 'pixel_height'):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 4096:
                raise ValueError('Pixel dimensions must be integers from 1 to 4096')
        elif name in ('frame_width', 'frame_height'):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('Frame dimensions must be positive and finite')
        elif name == 'background_color':
            if not isinstance(value, str) or len(value) != 7 or value[0] != '#' or any(c not in '0123456789abcdefABCDEF' for c in value[1:]):
                raise ValueError('Background color must be a six-digit hex color')
        else:
            raise NotImplementedError('Unsupported preview configuration: ' + name)
        object.__setattr__(self, name, value)

    def __getitem__(self, name):
        return getattr(self, name)

    def __setitem__(self, name, value):
        setattr(self, name, value)

    def to_dict(self):
        return {name: getattr(self, name) for name in
                ('pixel_width','pixel_height','frame_width','frame_height','background_color')}


config = PreviewConfig()


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
        self.updaters = []
        self.updating_suspended = False
        self.set_z_index(z_index)
        self._type = 'mobject'

    def get_family(self, recurse=True):
        result, seen = [], set()
        def visit(mobject):
            if id(mobject) in seen:
                return
            seen.add(id(mobject))
            result.append(mobject)
            for child in mobject.children:
                visit(child)
        visit(self)
        return result

    def add_updater(self, update_function, index=None, call_updater=False):
        if not callable(update_function):
            raise TypeError('Updater must be callable')
        inspect.signature(update_function)
        if index is None:
            self.updaters.append(update_function)
        else:
            self.updaters.insert(index, update_function)
        if call_updater:
            if 'dt' in inspect.signature(update_function).parameters:
                update_function(self, 0)
            else:
                update_function(self)
        return self

    def remove_updater(self, update_function):
        self.updaters = [u for u in self.updaters if u != update_function]
        return self

    def clear_updaters(self, recursive=True):
        for mobject in self.get_family() if recursive else [self]:
            mobject.updaters = []
        return self

    def get_updaters(self):
        return self.updaters

    def get_time_based_updaters(self):
        return [u for u in self.updaters if 'dt' in inspect.signature(u).parameters]

    def has_time_based_updater(self):
        return bool(self.get_time_based_updaters())

    def get_family_updaters(self):
        return [u for m in self.get_family() for u in m.updaters]

    def update(self, dt=0, recursive=True):
        if not math.isfinite(dt) or dt < 0:
            raise ValueError('Updater dt must be nonnegative and finite')
        if self.updating_suspended:
            return self
        for updater in list(self.updaters):
            if 'dt' in inspect.signature(updater).parameters:
                updater(self, dt)
            else:
                updater(self)
        if recursive:
            for child in list(self.children):
                child.update(dt)
        return self

    def suspend_updating(self, recursive=True):
        for mobject in self.get_family() if recursive else [self]:
            mobject.updating_suspended = True
        return self

    def resume_updating(self, recursive=True):
        for mobject in self.get_family() if recursive else [self]:
            mobject.updating_suspended = False
        return self.update(0, recursive=recursive)

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
        if self._type == 'annulus':
            r = max(self.inner_radius, self.outer_radius)
            return (-r, -r, r, r)
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
        if self._type in ('rectangle', 'ellipse'):
            return (-self.width / 2, -self.height / 2, self.width / 2, self.height / 2)
        if self._type in ('line', 'arrow'):
            points = [self.start, self.end]
        elif self._type in ('polygon', 'polyline'):
            points = self.vertices
        elif self._type == 'bezierpath':
            points = [point for curve in self.curves for point in curve] + getattr(self, 'vertices', [])
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
        if '_sampled_geometry_center' in self.__dict__:
            return Vector(self._sampled_geometry_center)
        left, bottom, right, top = self._local_bounds()
        return Vector(((left + right) / 2, (bottom + top) / 2, 0))

    def get_center(self):
        return Vector(self.position) + self._geometry_center()

    def get_points(self):
        """Independent world-space anchors/handles for supported XY outlines."""
        if self._type not in ('polyline', 'polygon', 'bezierpath', 'circle', 'arc', 'ellipse',
                              'square', 'rectangle', 'triangle', 'line', 'annulus'):
            return []
        if self._type == 'polyline' and len(self.vertices) == 1:
            points = self.vertices
        else:
            points = [point for curve in _path_curves(self.to_dict()) for point in curve]
            if self._type == 'bezierpath':
                points += self.vertices
        return [list(self._point_to_world(Vector(point))) for point in points]

    def get_num_points(self):
        return len(self.get_points())

    def has_points(self):
        return self.get_num_points() > 0

    def get_num_curves(self):
        return self.get_num_points() // 4

    def get_start(self):
        points = self.get_points()
        if not points:
            raise ValueError('The path has no points')
        return Vector(points[0])

    def get_end(self):
        points = self.get_points()
        if not points:
            raise ValueError('The path has no points')
        return Vector(points[-1])

    def is_closed(self):
        points = self.get_points()
        return bool(points) and all(abs(a-b) <= 1e-6 for a,b in zip(points[0],points[-1]))

    def pointwise_become_partial(self, vmobject, a, b):
        if not isinstance(vmobject, Mobject) or vmobject._type not in (
                'polyline', 'polygon', 'bezierpath', 'circle', 'arc', 'ellipse',
                'square', 'rectangle', 'triangle', 'line', 'annulus'):
            raise TypeError('Partial geometry expects a supported vector outline')
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)
               for v in (a,b)):
            raise ValueError('Partial curve bounds must be finite real values')
        a, b = max(0,min(1,a)), max(0,min(1,b))
        if a > b:
            raise ValueError('Partial curve lower bound must not exceed its upper bound')
        points = vmobject.get_points()
        if a == 0 and b == 1:
            lengths = copy.deepcopy(vmobject.__dict__.get('subpath_lengths'))
            VMobject.set_points(self, points)
            if lengths:
                self.subpath_lengths = lengths
            return self
        count = len(points) // 4
        if not count:
            return self
        first, last = min(int(a*count),count-1), min(int(b*count),count-1)
        lower, upper = a*count-first, b*count-last
        curves = []
        for i in range(first,last+1):
            curve = points[i*4:i*4+4]
            lo, hi = lower if i == first else 0, upper if i == last else 1
            if lo == hi:
                point = list(VMobject._bezier_point(curve,lo))
                curves.append([point[:] for _ in range(4)])
            else:
                if hi < 1:
                    curve = _split_cubic(curve,hi)[0]
                if lo > 0:
                    curve = _split_cubic(curve,lo/hi)[1]
                curves.append(curve)
        # Record boundaries before replacing self (the source may be self).
        lengths, offset = [], 0
        for path in _path_subpaths(vmobject.to_dict(),include_pending=False):
            overlap = min(offset+len(path)-1,last) - max(offset,first) + 1
            if overlap > 0:
                lengths.append(overlap)
            offset += len(path)
        VMobject.set_points(self,[point for curve in curves for point in curve])
        if len(lengths) > 1:
            self.subpath_lengths = lengths
        return self

    def get_subcurve(self, a, b):
        result = self.copy()
        if (isinstance(a,(int,float)) and isinstance(b,(int,float)) and
                math.isfinite(a) and math.isfinite(b) and a > b and self.is_closed()):
            result.pointwise_become_partial(self,a,1)
            second = self.copy().pointwise_become_partial(self,0,b)
            VMobject.append_vectorized_mobject(result,second)
        else:
            result.pointwise_become_partial(self,a,b)
        return result

    def point_from_proportion(self, alpha):
        """Sample supported XY outlines by distance, then apply SVG geometry transforms."""
        if not math.isfinite(alpha) or not 0 <= alpha <= 1:
            raise ValueError('Path proportion must be finite and between 0 and 1')
        if self._type == 'bezierpath':
            if not self.curves:
                if getattr(self, 'vertices', []):
                    return self._point_to_world(Vector(self.vertices[0]))
                raise ValueError('The path has no points')
            if alpha in (0, 1):
                return self._point_to_world(Vector(self.curves[0][0] if alpha == 0 else self.curves[-1][-1]))
            lengths = []
            for curve in self.curves:
                samples = [VMobject._bezier_point(curve, i / 20) for i in range(21)]
                lengths.append(sum(math.dist(a, b) for a, b in zip(samples, samples[1:])))
            total = sum(lengths)
            if not math.isfinite(total):
                raise ValueError('Path length must be finite')
            remaining = alpha * total
            for curve, length in zip(self.curves, lengths):
                if remaining <= length:
                    return self._point_to_world(VMobject._bezier_point(curve, remaining / length if length else 0))
                remaining -= length
            return self._point_to_world(Vector(self.curves[-1][-1]))
        if self._type == 'annulus':
            # Traverse each contour independently; no radial connector is drawn.
            total = self.outer_radius + self.inner_radius
            distance = alpha * total
            if alpha in (0, 1):
                radius, angle = (self.outer_radius if alpha == 0 else self.inner_radius), 0
            elif distance <= self.outer_radius and self.outer_radius:
                radius, angle = self.outer_radius, TAU * distance / self.outer_radius
            else:
                radius = self.inner_radius
                angle = -TAU * (distance - self.outer_radius) / radius if radius else 0
            point = Vector((radius * math.cos(angle), radius * math.sin(angle), 0))
        elif self._type == 'ellipse':
            angle = TAU * alpha
            point = Vector((self.width / 2 * math.cos(angle), self.height / 2 * math.sin(angle), 0))
        elif self._type in ('circle', 'arc'):
            if not math.isfinite(self.radius) or self.radius < 0:
                raise ValueError('Path radius must be nonnegative and finite')
            angle = TAU * alpha if self._type == 'circle' else self.start_angle + self.arc_angle * alpha
            point = Vector((self.radius * math.cos(angle), self.radius * math.sin(angle), 0))
        else:
            closed = True
            if self._type == 'line':
                vertices, closed = [self.start, self.end], False
            elif self._type in ('polygon', 'polyline'):
                vertices = self.vertices
                closed = self._type == 'polygon'
            elif self._type in ('square', 'rectangle'):
                width = self.side_length if self._type == 'square' else self.width
                height = self.side_length if self._type == 'square' else self.height
                vertices = [(width / 2, height / 2), (-width / 2, height / 2),
                            (-width / 2, -height / 2), (width / 2, -height / 2)]
            elif self._type == 'triangle':
                height = math.sqrt(3) / 2
                vertices = [(0, height * 2 / 3), (-0.5, -height / 3), (0.5, -height / 3)]
            else:
                raise NotImplementedError('Paths support Circle, Arc, Line, Polygon, VMobject corners, Square, Rectangle, and Triangle')
            if self._type == 'polyline' and len(vertices) == 1:
                return self._point_to_world(Vector(vertices[0]))
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
            if alpha in (0, 1):
                return self._point_to_world(points[0] if alpha == 0 else points[-1])
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
        if self.angle == 0 and self.geometry_scale == 1:
            point = Vector(self.position) + point
        else:
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
        if self._type == 'ellipse':
            rx, ry = self.width / 2, self.height / 2
            dx = abs(self.geometry_scale) * math.hypot(rx * math.cos(self.angle), ry * math.sin(self.angle))
            dy = abs(self.geometry_scale) * math.hypot(rx * math.sin(self.angle), ry * math.cos(self.angle))
            return (self.position[0] - dx, self.position[1] - dy,
                    self.position[0] + dx, self.position[1] + dy)
        if self._type in ('circle', 'annulus'):
            radius = max(self.inner_radius, self.outer_radius) if self._type == 'annulus' else self.radius
            r = abs(radius * self.geometry_scale)
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

    def become(self, mobject):
        """Replace supported geometry while retaining identity and updater registrations."""
        if not isinstance(mobject, Mobject):
            raise TypeError('become expects a Mobject')
        for special in (CameraFrame, ValueTracker):
            if isinstance(self, special) != isinstance(mobject, special):
                raise ValueError('Camera frames and trackers can only become their own kind')
        target = mobject.copy()
        if isinstance(self, CameraFrame):
            if (target.angle or target.position[2] or target.get_width() <= 0 or target.get_height() <= 0 or
                    not all(math.isfinite(v) for v in (*target.position,target.get_width(),target.get_height()))):
                raise ValueError('Camera frames must remain positive axis-aligned XY rectangles')
        replacements, used = {}, set()
        def replace(source, replacement):
            replacements[id(replacement)] = source
            used.add(source)
            children = []
            for index, child in enumerate(replacement.children):
                if id(child) in replacements:
                    member = replacements[id(child)]
                else:
                    member = source.children[index] if index < len(source.children) else child.copy()
                    if member in used:
                        member = child.copy()
                    replace(member, child)
                children.append(member)
            retained = {key:source.__dict__[key] for key in ('updaters','updating_suspended','_saved_state')
                        if key in source.__dict__}
            state = copy.deepcopy({key:value for key,value in replacement.__dict__.items()
                                   if key not in ('children','updaters','updating_suspended','_saved_state','_sampled_geometry_center')})
            if 'traced_point_func' in source.__dict__:
                retained.update({key:source.__dict__[key] for key in
                                 ('traced_point_func', 'dissipating_time', 'time')})
            state.update(retained, children=children)
            source.__dict__ = state
        replace(self, target)
        return self

    def save_state(self):
        # Replace the checkpoint without nesting earlier checkpoints inside it.
        self._saved_state = copy.deepcopy({key: value for key, value in self.__dict__.items()
                                          if key != '_saved_state'})
        return self

    def restore(self):
        if '_saved_state' not in self.__dict__:
            raise ValueError('Call save_state() before restoring an object')
        saved = self._saved_state
        updaters, suspended = self.updaters, self.updating_suspended
        self.__dict__ = copy.deepcopy(saved)
        self.updaters, self.updating_suspended = updaters, suspended
        self._saved_state = saved
        return self

    @property
    def animate(self):
        return Animate(self)

    def to_dict(self):
        result = copy.deepcopy({key: value for key, value in self.__dict__.items()
                                if key not in ('_saved_state', 'children', 'updaters', 'updating_suspended', '_sampled_geometry_center', 'traced_point_func', '_parametric_function', 'underlying_function', '_coordinate_labels')})
        result['type'] = result.pop('_type')
        result['geometry_center'] = list(self._geometry_center())
        result['children'] = [child.to_dict() for child in self.children]
        return result


class ValueTracker(Mobject):
    """An invisible finite real parameter, encoded in its x coordinate."""
    def __init__(self, value=0, **kwargs):
        super().__init__(**kwargs)
        self._type = 'valuetracker'
        self.set_value(value)

    def get_value(self):
        return self.position[0]

    def set_value(self, value):
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('ValueTracker requires a finite real number')
        self.position[0] = value
        return self

    def increment_value(self, d_value):
        if not isinstance(d_value, (int, float)):
            raise ValueError('ValueTracker increments must be real numbers')
        return self.set_value(self.get_value() + d_value)

    def __bool__(self):
        return bool(self.get_value())


def _tracker_arithmetic(operation, inplace=False):
    def calculate(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError('ValueTracker arithmetic expects a real scalar')
        result = operation(self.get_value(), value)
        return self.set_value(result) if inplace else ValueTracker(result)
    return calculate


for _name, _operation in [('add', operator.add), ('sub', operator.sub),
                           ('mul', operator.mul), ('truediv', operator.truediv),
                           ('floordiv', operator.floordiv), ('mod', operator.mod),
                           ('pow', operator.pow)]:
    setattr(ValueTracker, '__' + _name + '__', _tracker_arithmetic(_operation))
    setattr(ValueTracker, '__i' + _name + '__', _tracker_arithmetic(_operation, True))


def always_redraw(func):
    if not callable(func):
        raise TypeError('always_redraw expects a callable returning a Mobject')
    mobject = func()
    if not isinstance(mobject, Mobject):
        raise TypeError('always_redraw factory must return a Mobject')
    # Use the updater argument so copies regenerate themselves, not the original.
    return mobject.add_updater(lambda current: current.become(func()))


class VMobject(Mobject):
    """XY paths made of straight or cubic segments, with separate contours."""
    def __init__(self, **kwargs):
        kwargs.setdefault('stroke_width', 4)
        super().__init__(**kwargs)
        self._type, self.vertices = 'polyline', []

    @staticmethod
    def _corners(points):
        vertices = [list(Vector(point)) for point in points]
        if any(not all(math.isfinite(v) for v in point) for point in vertices):
            raise ValueError('Path coordinates must be finite')
        if any(point[2] for point in vertices):
            raise NotImplementedError('Paths support only the XY plane')
        return vertices

    def set_points(self, points):
        points = VMobject._corners(points)
        if len(points) % 4 not in (0, 1):
            raise ValueError('Cubic points need groups of four, optionally followed by one new anchor')
        completed = len(points) - len(points) % 4
        self.curves = [points[i:i+4] for i in range(0, completed, 4)]
        self.vertices = points[completed:]
        self._type = 'bezierpath'
        # Raw point arrays are world coordinates, just as native stored points.
        self.position, self.angle, self.geometry_scale = list(ORIGIN), 0, 1
        self.__dict__.pop('_sampled_geometry_center', None)
        self.__dict__.pop('subpath_lengths', None)
        return self

    def append_points(self, new_points):
        points = self._corners(new_points)
        if not points:
            return self
        return self.set_points(self.get_points() + points)

    def clear_points(self):
        return self.set_points([])

    def add_subpath(self, points):
        points = self._corners(points)
        if len(points) % 4:
            raise ValueError('A subpath needs complete groups of four cubic points')
        return self.append_points(points)

    def append_vectorized_mobject(self, vectorized_mobject):
        if not isinstance(vectorized_mobject, Mobject) or vectorized_mobject._type not in (
                'polyline', 'polygon', 'bezierpath', 'circle', 'arc', 'ellipse',
                'square', 'rectangle', 'triangle', 'line', 'annulus'):
            raise TypeError('Expected a supported vector outline')
        incoming = vectorized_mobject.get_points()
        existing = self.get_points()
        if len(existing) % 4:
            existing = existing[:-1]
        return VMobject.set_points(self, existing + incoming)

    def set_points_as_corners(self, points):
        vertices = self._corners(points)
        self._type, self.vertices = 'polyline', vertices
        self.__dict__.pop('curves', None)
        self.__dict__.pop('subpath_lengths', None)
        return self

    def change_anchor_mode(self, mode):
        if mode not in ('smooth','jagged'):
            raise ValueError('Anchor mode must be smooth or jagged')
        center = self._geometry_center()
        paths = _path_subpaths(self.to_dict(),include_pending=False)
        curves, lengths = [], []
        for path in paths:
            anchors = [Vector(path[0][0])] + [Vector(curve[-1]) for curve in path]
            new = (_smooth_path_curves(anchors) if mode == 'smooth' else
                   [[list(a),list(a*(2/3)+b*(1/3)),list(a*(1/3)+b*(2/3)),list(b)]
                    for a,b in zip(anchors,anchors[1:])])
            curves.extend(new)
            lengths.append(len(new))
        points = self._corners([point for curve in curves for point in curve])
        pending = (copy.deepcopy(self.vertices) if self._type == 'bezierpath' else
                   copy.deepcopy(self.vertices) if self._type == 'polyline' and len(self.vertices) == 1 else [])
        self.curves = [points[i:i+4] for i in range(0,len(points),4)]
        self._type,self.vertices = 'bezierpath',pending
        self.__dict__.pop('subpath_lengths',None)
        self.__dict__.pop('_sampled_geometry_center',None)
        if len(lengths) > 1:
            self.subpath_lengths = lengths
        # Bounds can change with new handles. Preserve the world anchors and the
        # existing transform so animated smoothing keeps them fixed as well.
        delta = center-self._geometry_center()
        rotated = Vector((delta[0]*math.cos(self.angle)-delta[1]*math.sin(self.angle),
                          delta[0]*math.sin(self.angle)+delta[1]*math.cos(self.angle),0))*self.geometry_scale
        self.shift(delta-rotated)
        return self

    def make_smooth(self):
        return self.change_anchor_mode('smooth')

    def make_jagged(self):
        return self.change_anchor_mode('jagged')

    def set_points_smoothly(self, points):
        target = self.copy().set_points_as_corners(points).make_smooth()
        return self.become(target)

    def start_new_path(self, point):
        point = self._corners([point])[0]
        existing = self.get_points()
        if len(existing) % 4:
            existing.extend([existing[-1][:] for _ in range(3)])
        return self.set_points(existing + [point])

    def has_new_path_started(self):
        return bool(self.vertices) if self._type == 'bezierpath' else len(self.vertices) == 1

    def get_subpaths(self):
        return [[self._point_to_world(Vector(point)) for curve in path for point in curve]
                for path in _path_subpaths(self.to_dict(), include_pending=False)]

    def close_path(self):
        paths = _path_subpaths(self.to_dict())
        if paths and (self.has_new_path_started() or paths[-1][-1][-1] != paths[-1][0][0]):
            self.add_line_to(paths[-1][0][0])
        return self

    def add_points_as_corners(self, points):
        vertices = self._corners(points)
        if self._type == 'bezierpath':
            if not vertices:
                return self
            start = Vector(self.vertices[0] if self.vertices else self.curves[-1][-1])
            for point in vertices:
                end = Vector(point)
                self.curves.append([list(start), list(start + (end-start) * (1/3)),
                                    list(start + (end-start) * (2/3)), list(end)])
                start = end
            self.vertices = []
            self.__dict__.pop('subpath_lengths', None)
        else:
            self.vertices.extend(vertices)
        return self

    def add_line_to(self, point):
        return self.add_points_as_corners([point])

    def reverse_direction(self):
        if self._type == 'bezierpath':
            if self.vertices:
                self.curves.append([self.vertices[0][:] for _ in range(4)])
                self.vertices = []
            self.curves = [list(reversed(curve)) for curve in reversed(self.curves)]
            if 'subpath_lengths' in self.__dict__:
                self.subpath_lengths.reverse()
        else:
            self.vertices.reverse()
        return self

    @staticmethod
    def _bezier_point(curve, t):
        # De Casteljau interpolation avoids large polynomial coefficients.
        points = [Vector(p) for p in curve]
        while len(points) > 1:
            points = [a * (1-t) + b * t for a, b in zip(points, points[1:])]
        return points[0]

    def add_cubic_bezier_curve_to(self, handle1, handle2, anchor):
        points = self._corners([handle1, handle2, anchor])
        if self._type != 'bezierpath':
            if not self.vertices:
                raise ValueError('Start the path with a corner before adding a cubic curve')
            curves = []
            for a, b in zip(self.vertices, self.vertices[1:]):
                a, b = Vector(a), Vector(b)
                curves.append([list(a), list(a + (b-a) * (1/3)),
                               list(a + (b-a) * (2/3)), list(b)])
            curves.append([self.vertices[-1][:], *points])
            self._type, self.curves, self.vertices = 'bezierpath', curves, []
        else:
            start = self.vertices[0] if self.vertices else self.curves[-1][-1]
            self.curves.append([start[:], *points])
            self.vertices = []
        self.__dict__.pop('subpath_lengths', None)
        return self

    def get_start(self):
        if self._type == 'bezierpath':
            if not self.curves and not self.vertices:
                raise ValueError('The path has no points')
            return self._point_to_world(Vector(self.curves[0][0] if self.curves else self.vertices[0]))
        if not self.vertices:
            raise ValueError('The path has no points')
        return self._point_to_world(Vector(self.vertices[0]))

    def get_end(self):
        if self._type == 'bezierpath':
            if not self.curves and not self.vertices:
                raise ValueError('The path has no points')
            return self._point_to_world(Vector(self.vertices[0] if self.vertices else self.curves[-1][-1]))
        if not self.vertices:
            raise ValueError('The path has no points')
        return self._point_to_world(Vector(self.vertices[-1]))


def _smooth_path_curves(anchors):
    """C2 cubic spline: natural open ends or a periodic closed-loop system."""
    anchors = [Vector(point) for point in anchors]
    count = len(anchors)-1
    if count <= 0:
        return []
    if count == 1:
        a,b = anchors
        return [[list(a),list(a*(2/3)+b*(1/3)),list(a*(1/3)+b*(2/3)),list(b)]]

    def solve(diagonal, lower, rhs):
        diagonal,rhs = diagonal[:],rhs[:]
        for i in range(1,count):
            factor = lower[i-1]/diagonal[i-1]
            diagonal[i] -= factor
            rhs[i] = rhs[i]-rhs[i-1]*factor
        result = [ORIGIN]*count
        result[-1] = rhs[-1]*(1/diagonal[-1])
        for i in range(count-2,-1,-1):
            result[i] = (rhs[i]-result[i+1])*(1/diagonal[i])
        return result

    closed = all(abs(a-b) <= 1e-6 for a,b in zip(anchors[0],anchors[-1]))
    if closed:
        # Trigonometric endpoints can differ by machine rounding. A periodic
        # contour needs one shared anchor for its spline seam and SVG closure.
        anchors[-1] = anchors[0]
        rhs = [anchors[i]*4+anchors[i+1]*2 for i in range(count)]
        if count == 2:
            handles = [(rhs[0]*4-rhs[1]*2)*(1/12),(rhs[1]*4-rhs[0]*2)*(1/12)]
        else:
            diagonal = [3]+[4]*(count-2)+[3]
            y = solve(diagonal,[1]*(count-1),rhs)
            q = solve(diagonal,[1]*(count-1),[RIGHT]+[ORIGIN]*(count-2)+[RIGHT])
            correction = (y[0]+y[-1])*(1/(1+q[0][0]+q[-1][0]))
            handles = [point-correction*value[0] for point,value in zip(y,q)]
        second = [anchors[i+1]*2-handles[(i+1)%count] for i in range(count)]
    else:
        rhs = [anchors[0]+anchors[1]*2]
        rhs.extend(anchors[i]*4+anchors[i+1]*2 for i in range(1,count-1))
        rhs.append(anchors[-2]*8+anchors[-1])
        handles = solve([2]+[4]*(count-2)+[7],[1]*(count-2)+[2],rhs)
        second = [anchors[i+1]*2-handles[i+1] for i in range(count-1)]
        second.append((anchors[-1]+handles[-1])*.5)
    return [[list(a),list(h1),list(h2),list(b)] for a,h1,h2,b in
            zip(anchors,handles,second,anchors[1:])]


class ParametricFunction(VMobject):
    """Finite XY samples with optional C2 smoothing and declared contour gaps."""
    def __init__(self, function, t_range=(0,1), dt=1e-8, discontinuities=None,
                 use_smoothing=True, use_vectorized=False, **kwargs):
        if not callable(function):
            raise TypeError('ParametricFunction expects a callable returning an XY point')
        if use_vectorized:
            raise NotImplementedError('Vectorized plotting is not implemented')
        if not isinstance(use_smoothing,bool) or not isinstance(use_vectorized,bool):
            raise ValueError('Plotting flags must be booleans')
        values = self._range(t_range,.01)
        NumberLine._real(dt,'discontinuity buffer',nonnegative=True)
        discontinuities = sorted(set(NumberLine._numbers(discontinuities or [])))
        super().__init__(**kwargs)
        self._parametric_function = function
        self.t_min,self.t_max,self.t_step = values
        self.dt,self.discontinuities,self.use_smoothing = dt,discontinuities,use_smoothing
        self.generate_points()

    @staticmethod
    def _range(values, step):
        values = list(values)
        if len(values) == 2:
            values.append(step)
        if len(values) != 3:
            raise ValueError('Plot range needs [minimum, maximum, positive sample step]')
        for value in values:
            NumberLine._real(value,'Plot range')
        if values[0] > values[1] or values[2] <= 0 or not math.isfinite(values[1]-values[0]):
            raise ValueError('Plot range must increase with a positive sample step')
        return values

    def get_function(self):
        return self._parametric_function

    def get_point_from_function(self, t):
        NumberLine._real(t,'Function input')
        return Vector(self._corners([self._parametric_function(t)])[0])

    def generate_points(self):
        intervals,cursor = [],self.t_min
        active = [value for value in self.discontinuities if self.t_min <= value <= self.t_max]
        for value in active:
            left,right = max(self.t_min,value-self.dt),min(self.t_max,value+self.dt)
            if left > cursor:
                intervals.append((cursor,left))
            cursor = max(cursor,right)
        if cursor < self.t_max or not active and cursor == self.t_max:
            intervals.append((cursor,self.t_max))
        # Bound all sampling before executing user functions or changing geometry.
        counts = []
        for start,end in intervals:
            size = (end-start)/self.t_step
            if not math.isfinite(size) or size > 10000:
                raise ValueError('Plots are limited to 10001 sampled points')
            counts.append(math.ceil(size))
        if sum(count+1 for count in counts) > 10001:
            raise ValueError('Plots are limited to 10001 sampled points')
        curves,lengths,pending = [],[],[]
        for (start,end),count in zip(intervals,counts):
            times = [start+i*self.t_step for i in range(count) if start+i*self.t_step < end]+[end]
            anchors = [self.get_point_from_function(t) for t in times]
            if len(anchors) == 1:
                pending = [list(anchors[0])]
                continue
            new = (_smooth_path_curves(anchors) if self.use_smoothing else
                   [[list(a),list(a*(2/3)+b*(1/3)),list(a*(1/3)+b*(2/3)),list(b)]
                    for a,b in zip(anchors,anchors[1:])])
            curves.extend(new)
            lengths.append(len(new))
        VMobject.set_points(self,[point for curve in curves for point in curve]+pending)
        if len(lengths) > 1:
            self.subpath_lengths = lengths
        return self


class FunctionGraph(ParametricFunction):
    def __init__(self, function, x_range=None, color=YELLOW, **kwargs):
        if not callable(function):
            raise TypeError('FunctionGraph expects a scalar function')
        values = (-config.frame_width/2,config.frame_width/2) if x_range is None else x_range
        self.underlying_function = function
        self.x_range = self._range(values,.01)
        super().__init__(lambda t: (t,function(t),0),t_range=self.x_range,color=color,**kwargs)

    def get_function(self):
        return self.underlying_function


class TracedPath(VMobject):
    """Connect sampled XY points, optionally dropping old segments over time."""
    def __init__(self, traced_point_func, stroke_width=2, stroke_color=WHITE,
                 dissipating_time=None, **kwargs):
        if not callable(traced_point_func):
            raise TypeError('TracedPath expects a callable returning an XY point')
        if (dissipating_time is not None and
                (not isinstance(dissipating_time, (int, float)) or
                 not math.isfinite(dissipating_time) or dissipating_time < 0)):
            raise ValueError('dissipating_time must be nonnegative and finite')
        super().__init__(stroke_width=stroke_width,
                         stroke_color=WHITE if stroke_color is None else stroke_color, **kwargs)
        self.traced_point_func = traced_point_func
        self.dissipating_time = dissipating_time
        self.time = 1.0 if dissipating_time else None
        # Act on the updater argument so copied traces extend their own path.
        self.add_updater(lambda m, dt: m.update_path(m, dt))

    def update_path(self, mob, dt):
        point = self._corners([self.traced_point_func()])[0]
        # Bake accumulated transforms before adding a new world-space sample.
        # Otherwise a changing path bounding box would move the old rotation pivot.
        if self._type == 'bezierpath':
            curves = [[list(self._point_to_world(Vector(p))) for p in curve]
                      for curve in self.curves]
            vertices = []
        else:
            vertices = [list(self._point_to_world(Vector(p))) for p in self.vertices]
            curves = None
        self.position, self.angle, self.geometry_scale = list(ORIGIN), 0, 1
        self.__dict__.pop('_sampled_geometry_center', None)
        if curves:
            self.curves = curves
            self.add_line_to(point)
        else:
            self.set_points_as_corners(vertices or [point])
            self.add_line_to(point)
        if self.dissipating_time:
            self.time += dt
            if self.time - 1 > self.dissipating_time:
                if self._type == 'bezierpath':
                    self.curves = self.curves[1:]
                    if not self.curves:
                        self.set_points_as_corners([point])
                else:
                    self.vertices = self.vertices[1:]
        return self


class CubicBezier(VMobject):
    def __init__(self, start_anchor, start_handle, end_handle, end_anchor, **kwargs):
        super().__init__(**kwargs)
        self.curves = [self._corners([start_anchor, start_handle, end_handle, end_anchor])]
        self._type = 'bezierpath'


class Circle(Mobject):
    def __init__(self, radius=1, **kwargs):
        super().__init__(**kwargs)
        self._type, self.radius = 'circle', radius


class Ellipse(Circle):
    def __init__(self, width=2, height=1, **kwargs):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
               not math.isfinite(v) or v < 0 for v in (width, height)):
            raise ValueError('Ellipse dimensions must be nonnegative and finite')
        super().__init__(**kwargs)
        self._type, self.width, self.height = 'ellipse', width, height


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


class AnnularSector(Arc, VMobject):
    """One connected outline: inner arc, radial edge, reversed outer arc, edge."""
    def __init__(self, inner_radius=1, outer_radius=2, angle=PI/2, start_angle=0,
                 fill_opacity=1, stroke_width=0, color=WHITE, arc_center=ORIGIN, **kwargs):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
               not math.isfinite(v) or v < 0 for v in (inner_radius, outer_radius)):
            raise ValueError('Sector radii must be nonnegative and finite')
        super().__init__(radius=outer_radius, angle=angle, start_angle=start_angle,
                         arc_center=arc_center, fill_opacity=fill_opacity,
                         stroke_width=stroke_width, color=color, **kwargs)
        self.inner_radius, self.outer_radius = inner_radius, outer_radius
        arcs = []
        for radius in (inner_radius, outer_radius):
            snapshot = {'type':'arc', 'radius':radius,
                        'start_angle':self.start_angle, 'arc_angle':self.arc_angle}
            arcs.append(_path_curves(snapshot))
        inner, outer = arcs
        outer = [list(reversed(curve)) for curve in reversed(outer)]
        def edge(a, b):
            a, b = Vector(a), Vector(b)
            return [list(a), list(a + (b-a)*(1/3)),
                    list(a + (b-a)*(2/3)), list(b)]
        self.curves = inner + [edge(inner[-1][-1], outer[0][0])] + outer + [edge(outer[-1][-1], inner[0][0])]
        self._type, self.vertices = 'bezierpath', []


class Sector(AnnularSector):
    def __init__(self, radius=1, **kwargs):
        super().__init__(inner_radius=0, outer_radius=radius, **kwargs)


class Annulus(Circle):
    def __init__(self, inner_radius=1, outer_radius=2, fill_opacity=1,
                 stroke_width=0, color=WHITE, mark_paths_closed=False,
                 arc_center=ORIGIN, **kwargs):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
               not math.isfinite(v) or v < 0 for v in (inner_radius, outer_radius)):
            raise ValueError('Annulus radii must be nonnegative and finite')
        center = Vector(arc_center)
        if not all(math.isfinite(v) for v in center):
            raise ValueError('Annulus center must be finite')
        if center[2]:
            raise NotImplementedError('Annuli support only the XY plane')
        if not isinstance(mark_paths_closed, bool):
            raise ValueError('mark_paths_closed must be a boolean')
        super().__init__(radius=outer_radius, fill_opacity=fill_opacity,
                         stroke_width=stroke_width, color=color, **kwargs)
        self._type = 'annulus'
        self.inner_radius, self.outer_radius = inner_radius, outer_radius
        self.mark_paths_closed = mark_paths_closed
        self.position = list(center)

    get_arc_center = Arc.get_arc_center
    move_arc_center_to = Arc.move_arc_center_to

    def get_start(self):
        return self.point_from_proportion(0)

    def get_end(self):
        if self._type == 'bezierpath':
            return Mobject.get_end(self)
        return self._point_to_world(Vector((self.inner_radius, 0, 0)))


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


class RoundedRectangle(Rectangle, VMobject):
    """A closed rectangle with circular, optionally concave corner cuts."""
    def __init__(self, corner_radius=0.5, width=4, height=2, **kwargs):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
               not math.isfinite(v) or v < 0 for v in (width, height)):
            raise ValueError('Rounded rectangle dimensions must be nonnegative and finite')
        radii = list(corner_radius) if isinstance(corner_radius, (list, tuple)) else [corner_radius]
        if not radii or any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                            not math.isfinite(v) for v in radii):
            raise ValueError('Corner radii must be finite real values in a nonempty sequence')
        super().__init__(width=width, height=height, **kwargs)
        self.corner_radius = copy.deepcopy(corner_radius)
        corners = [Vector(p) for p in ((width/2,height/2), (-width/2,height/2),
                                      (-width/2,-height/2), (width/2,-height/2))]
        incoming = [UP, LEFT, DOWN, RIGHT]
        outgoing = [LEFT, DOWN, RIGHT, UP]
        arcs = []
        # Native rounding assigns the first radius to the second vertex (UL),
        # then rotates its arc list to begin at the first vertex (UR).
        for i, (corner, before, after) in enumerate(zip(corners, incoming, outgoing)):
            radius = radii[(i-1) % 4 % len(radii)]
            cut = min(abs(radius), min(width, height)/2)
            start = corner - before * cut
            center = corner - before * cut + after * cut if radius >= 0 else corner
            angle = math.atan2(start[1]-center[1], start[0]-center[0])
            curves = _path_curves({'type':'arc', 'radius':cut, 'start_angle':angle,
                                   'arc_angle':PI/2 if radius >= 0 else -PI/2})
            curves = [[list(Vector(p) + center) for p in curve] for curve in curves]
            # Pin joins exactly to avoid tiny floating-point closing seams.
            curves[0][0], curves[-1][-1] = list(start), list(corner + after * cut)
            arcs.append(curves)
        self.curves = []
        for i, arc in enumerate(arcs):
            self.curves.extend(arc)
            a, b = Vector(arc[-1][-1]), Vector(arcs[(i+1)%4][0][0])
            self.curves.append([list(a), list(a+(b-a)*(1/3)), list(a+(b-a)*(2/3)), list(b)])
        self._type, self.vertices = 'bezierpath', []


class CameraFrame(Rectangle):
    """Invisible, axis-aligned view rectangle used by MovingCameraScene."""
    def scale(self, scale_factor, *, about_point=None):
        if not math.isfinite(scale_factor) or scale_factor <= 0:
            raise ValueError('Camera scale must be positive and finite')
        return super().scale(scale_factor, about_point=about_point)

    def shift(self, direction):
        direction = Vector(direction)
        if not all(math.isfinite(v) for v in direction) or direction[2]:
            raise ValueError('Camera position must be finite and in the XY plane')
        return super().shift(direction)

    def rotate(self, *args, **kwargs):
        raise NotImplementedError('Moving camera frames support pan and zoom, not rotation')

    def get_width(self):
        return self.width * self.geometry_scale

    def get_height(self):
        return self.height * self.geometry_scale

    def set_width(self, width):
        return self.scale(width / self.get_width())

    def set_height(self, height):
        return self.scale(height / self.get_height())


class MovingCamera(PreviewConfig):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, '_frame', CameraFrame(width=self.frame_width, height=self.frame_height))

    @property
    def frame(self):
        return self._frame

    def __getattribute__(self, name):
        if name in ('frame_width','frame_height') and '_frame' in object.__getattribute__(self,'__dict__'):
            frame = object.__getattribute__(self,'_frame')
            return frame.get_width() if name == 'frame_width' else frame.get_height()
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name == 'frame_center' and '_frame' in self.__dict__:
            self.frame.move_to(value)
            return
        if '_frame' in self.__dict__ and name in ('frame_width','frame_height'):
            getattr(self.frame, 'set_width' if name == 'frame_width' else 'set_height')(value)
            return
        super().__setattr__(name, value)
        if '_frame' in self.__dict__ and name in ('pixel_width','pixel_height'):
            self.frame.width = self.frame.height * self.pixel_width / self.pixel_height

    @property
    def frame_center(self):
        return self.frame.get_center()

    @staticmethod
    def _object_bounds(mobject):
        if not isinstance(mobject, Mobject):
            raise TypeError('Camera framing expects Mobjects')
        bounds = mobject._bounds()
        if not all(math.isfinite(v) for v in bounds):
            raise ValueError('Camera framing bounds must be finite')
        if any(member.position[2] for member in mobject.get_family()):
            raise NotImplementedError('Camera framing supports only the XY plane')
        return bounds

    def is_in_frame(self, mobject):
        left, bottom, right, top = self._object_bounds(mobject)
        x, y, _ = self.frame_center
        return not (right < x - self.frame_width / 2 or left > x + self.frame_width / 2 or
                    bottom > y + self.frame_height / 2 or top < y - self.frame_height / 2)

    def auto_zoom(self, mobjects, margin=0, only_mobjects_in_frame=False, animate=True):
        """Fit XY bounds; margin adds to the chosen dimension, as in Manim."""
        if not isinstance(margin, (int, float)) or not math.isfinite(margin):
            raise ValueError('Camera margin must be finite')
        objects = [mobjects] if isinstance(mobjects, Mobject) else list(mobjects)
        bounds = []
        for mobject in objects:
            box = self._object_bounds(mobject)
            if mobject is self.frame or (only_mobjects_in_frame and not self.is_in_frame(mobject)):
                continue
            bounds.append(box)
        if not bounds:
            raise ValueError('Cannot frame an empty selection')
        left, bottom = min(b[0] for b in bounds), min(b[1] for b in bounds)
        right, top = max(b[2] for b in bounds), max(b[3] for b in bounds)
        width, height = right - left, top - bottom
        use_width = width / self.frame_width > height / self.frame_height
        extent = (width if use_width else height) + margin
        if not math.isfinite(extent) or extent <= 0:
            raise ValueError('Camera framing must produce a positive finite extent')
        target = self.frame.animate if animate else self.frame
        return getattr(target.move_to(((left + right) / 2, (bottom + top) / 2, 0)),
                       'set_width' if use_width else 'set_height')(extent)

    def to_dict(self, frame_snapshot=None):
        result = super().to_dict()
        frame = frame_snapshot if frame_snapshot is not None else self.frame.to_dict()
        width, height = frame['width'] * frame['geometry_scale'], frame['height'] * frame['geometry_scale']
        center = list(Vector(frame['position']) + Vector(frame['geometry_center']))
        if (frame['type'] != 'rectangle' or frame['angle'] != 0 or center[2] or
                not all(math.isfinite(v) for v in (*center,width,height)) or width <= 0 or height <= 0):
            raise ValueError('Camera frames must remain positive, finite, axis-aligned XY rectangles')
        result.update(frame_width=width, frame_height=height, frame_center=center)
        return result


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


def _number_text(number, options):
    if not isinstance(number, (int, float)) or not math.isfinite(number):
        raise ValueError('Numeric labels require a finite real value')
    precision = options['num_decimal_places']
    spec = ('+' if options['include_sign'] else '') + (',' if options['group_with_commas'] else '')
    text = format(number, spec + '.' + str(precision) + 'f')
    if text.startswith('-') and all(c in '0,.' for c in text[1:]):
        text = ('+' if options['include_sign'] else '') + text[1:]
    return text + ('…' if options['show_ellipsis'] else '') + (options['unit'] or '')


class DecimalNumber(Text):
    """A finite real numeric label using the preview's centered SVG text."""
    def __init__(self, number=0, num_decimal_places=2, include_sign=False,
                 group_with_commas=True, show_ellipsis=False, unit=None, font_size=48, **kwargs):
        if (isinstance(num_decimal_places, bool) or not isinstance(num_decimal_places, int) or
                not 0 <= num_decimal_places <= 12):
            raise ValueError('num_decimal_places must be an integer from 0 to 12')
        if not all(isinstance(v, bool) for v in (include_sign, group_with_commas, show_ellipsis)):
            raise ValueError('Numeric formatting flags must be booleans')
        if unit is not None and (not isinstance(unit, str) or len(unit) > 256):
            raise ValueError('Numeric unit must be a string of at most 256 characters')
        if not isinstance(font_size, (int, float)) or not math.isfinite(font_size) or font_size <= 0:
            raise ValueError('Numeric font size must be positive and finite')
        options = dict(num_decimal_places=num_decimal_places, include_sign=include_sign,
                       group_with_commas=group_with_commas, show_ellipsis=show_ellipsis, unit=unit)
        super().__init__(_number_text(number, options), font_size=font_size, **kwargs)
        self.number, self._number_format = number, options

    def get_value(self):
        return self.number

    def set_value(self, number):
        text = _number_text(number, self._number_format)
        self.number, self.text = number, text
        return self

    def increment_value(self, delta_t=1):
        if not isinstance(delta_t,(int, float)):
            raise ValueError('Numeric increments must be real values')
        return self.set_value(self.get_value() + delta_t)

    def to_dict(self):
        result = super().to_dict()
        if result['type'] == 'text' and '_number_format' in result:
            result['text'] = _number_text(self.number, self._number_format)
        return result


class Integer(DecimalNumber):
    def __init__(self, number=0, num_decimal_places=0, **kwargs):
        super().__init__(number, num_decimal_places=num_decimal_places, **kwargs)

    def get_value(self):
        return int(round(self.number))


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


class Group(Mobject):
    def __init__(self, *mobjects, **kwargs):
        super().__init__(**kwargs)
        self._type = 'vgroup'
        self.add(*mobjects)

    def _validate_children(self, mobjects):
        if any(not isinstance(m, Mobject) for m in mobjects):
            raise TypeError('Group children must be Mobjects')
        if any(isinstance(member, CameraFrame) for m in mobjects for member in m.get_family()):
            raise ValueError('Camera frames cannot be children of a display group')
        if any(self in m.get_family() for m in mobjects):
            raise ValueError('A group cannot contain itself or create a family cycle')

    @property
    def submobjects(self):
        return self.children

    @submobjects.setter
    def submobjects(self, mobjects):
        mobjects = list(mobjects)
        self._validate_children(mobjects)
        self.children = list(dict.fromkeys(mobjects))

    def add(self, *mobjects):
        self._validate_children(mobjects)
        unique = list(dict.fromkeys(mobjects))
        self.children = [m for m in self.children if m not in unique] + unique
        return self

    def add_to_back(self, *mobjects):
        self._validate_children(mobjects)
        unique = list(dict.fromkeys(mobjects))
        self.children = unique + [m for m in self.children if m not in unique]
        return self

    def remove(self, *mobjects):
        if any(not isinstance(m, Mobject) for m in mobjects):
            raise TypeError('Group removal expects Mobjects')
        self.children = [m for m in self.children if m not in mobjects]
        return self

    def __iter__(self):
        return iter(self.children)

    def __len__(self):
        return len(self.children)

    def __getitem__(self, value):
        if isinstance(value, slice):
            group_class = VGroup if isinstance(self, VGroup) else Group
            return group_class(*self.children[value])
        return self.children[value]

    def split(self):
        return list(self.children)

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


class VGroup(Group):
    """Container for the supported vector/text geometry in this runtime."""
    pass


class _SecantSlopeGroup(VGroup):
    def _component(self, role):
        for child in self.children:
            if child.__dict__.get('_secant_role') == role:
                return child
        raise AttributeError('Secant group has no ' + role)

    dx_line = property(lambda self:self._component('dx_line'))
    df_line = property(lambda self:self._component('df_line'))
    dy_line = property(lambda self:self.df_line)
    dx_label = property(lambda self:self._component('dx_label'))
    df_label = property(lambda self:self._component('df_label'))
    dy_label = property(lambda self:self.df_label)
    secant_line = property(lambda self:self._component('secant_line'))


class NumberLine(VGroup):
    """Linear XY coordinates, composed from a shaft, ticks and numeric labels."""
    def __init__(self, x_range=None, length=None, unit_size=1, include_ticks=True,
                 tick_size=.1, numbers_with_elongated_ticks=None, longer_tick_multiple=2,
                 exclude_origin_tick=False, rotation=0, include_tip=False,
                 tip_width=.35, tip_height=.35, include_numbers=False, font_size=36,
                 label_direction=DOWN, line_to_number_buff=.25,
                 decimal_number_config=None, numbers_to_exclude=None,
                 numbers_to_include=None, **kwargs):
        radius = max(1, round(config.frame_width/2))
        values = list(x_range) if x_range is not None else [-radius,radius,1]
        if len(values) == 2:
            values.append(1)
        if len(values) != 3:
            raise ValueError('NumberLine x_range needs [minimum, maximum, positive step]')
        for value in values:
            self._real(value, 'NumberLine range')
        if values[0] >= values[1] or values[2] <= 0 or not math.isfinite(values[1]-values[0]):
            raise ValueError('NumberLine range must increase and have a positive step')
        for value, name in ((unit_size,'unit_size'),(font_size,'font_size'),
                            (tip_width,'tip_width'),(tip_height,'tip_height')):
            self._real(value,name,positive=True)
        for value, name in ((tick_size,'tick_size'),(longer_tick_multiple,'longer_tick_multiple'),
                            (line_to_number_buff,'line_to_number_buff')):
            self._real(value,name,nonnegative=True)
        self._real(rotation,'rotation')
        if not all(isinstance(v,bool) for v in
                   (include_ticks,exclude_origin_tick,include_tip,include_numbers)):
            raise ValueError('NumberLine inclusion flags must be booleans')
        label_direction = self._direction(label_direction)
        length = (values[1]-values[0])*unit_size if length is None else length
        self._real(length,'length',positive=True)
        super().__init__(**kwargs)
        self.x_range = values[:]
        self.x_min,self.x_max,self.x_step = values
        self.tick_size,self.longer_tick_multiple = tick_size,longer_tick_multiple
        self.include_tip,self.exclude_origin_tick = include_tip,exclude_origin_tick
        self.font_size,self.label_direction = font_size,list(label_direction)
        self.line_to_number_buff = line_to_number_buff
        self.numbers_with_elongated_ticks = self._numbers(numbers_with_elongated_ticks or [])
        self.numbers_to_exclude = self._numbers(numbers_to_exclude or [])
        self.numbers_to_include = None if numbers_to_include is None else self._numbers(numbers_to_include)
        decimals = len(format(values[2],'.12f').rstrip('0').split('.')[-1])
        self.decimal_number_config = dict(decimal_number_config) if decimal_number_config is not None else dict(num_decimal_places=decimals)
        # Validate label formatting even when labels are deferred.
        DecimalNumber(0,font_size=font_size,**self.decimal_number_config)
        shaft = Line(LEFT*(length/2),RIGHT*(length/2),color=self.color,
                     stroke_color=self.stroke_color,stroke_width=self.stroke_width,
                     stroke_opacity=self.stroke_opacity).rotate(rotation)
        shaft._number_line_role = 'shaft'
        self.add(shaft)
        if include_tip:
            end = shaft.get_end()
            direction = shaft.get_unit_vector()
            normal = Vector((-direction[1],direction[0],0))
            base = end - direction*tip_height
            tip = Polygon(end,base+normal*(tip_width/2),base-normal*(tip_width/2),
                          color=self.stroke_color,fill_opacity=1,
                          stroke_width=self.stroke_width,stroke_opacity=self.stroke_opacity)
            tip._number_line_role = 'tip'
            self.add(tip)
        if include_ticks:
            self.add_ticks()
        if include_numbers or self.numbers_to_include is not None:
            self.add_numbers(self.numbers_to_include)

    @staticmethod
    def _real(value, name, positive=False, nonnegative=False):
        if (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)
                or positive and value <= 0 or nonnegative and value < 0):
            raise ValueError(name + ' must be a finite real value' + (' greater than zero' if positive else ''))
        return value

    @classmethod
    def _numbers(cls, values):
        result = list(values)
        if len(result) > 1000:
            raise ValueError('NumberLine supports at most 1000 ticks or labels per addition')
        for value in result:
            cls._real(value,'NumberLine value')
        return result

    @staticmethod
    def _direction(value):
        direction = Vector(value)
        if not all(math.isfinite(v) for v in direction) or direction == ORIGIN:
            raise ValueError('NumberLine label direction must be finite and nonzero')
        if direction[2]:
            raise NotImplementedError('NumberLine supports only XY label directions')
        return direction

    def _part(self, role):
        for child in reversed(self.children):
            if child.__dict__.get('_number_line_role') == role:
                return child
        raise ValueError('NumberLine has no ' + role)

    @property
    def ticks(self):
        return self._part('ticks')

    @property
    def numbers(self):
        return self._part('numbers')

    @property
    def tip(self):
        return self._part('tip')

    def get_start(self):
        return self._point_to_world(self._part('shaft').get_start())

    def get_end(self):
        return self._point_to_world(self._part('shaft').get_end())

    get_start_and_end = Line.get_start_and_end
    get_vector = Line.get_vector
    get_length = Line.get_length
    get_angle = Line.get_angle

    def get_unit_size(self):
        return self.get_length()/(self.x_max-self.x_min)

    def get_unit_vector(self):
        return self.get_vector()*(1/(self.x_max-self.x_min))

    def set_length(self, length):
        self._real(length,'length',positive=True)
        current = self.get_length()
        if current == 0:
            raise ValueError('Cannot resize a collapsed NumberLine')
        return self.scale(length/current,about_point=(self.get_start()+self.get_end())*.5)

    def point_from_proportion(self, alpha):
        self._real(alpha,'Path proportion')
        if not 0 <= alpha <= 1:
            raise ValueError('Path proportion must be between zero and one')
        return self.get_start() + self.get_vector()*alpha

    def number_to_point(self, number):
        if isinstance(number,(list,tuple)):
            return [self.number_to_point(value) for value in self._numbers(number)]
        self._real(number,'NumberLine value')
        result = self.get_start()+self.get_vector()*((number-self.x_min)/(self.x_max-self.x_min))
        if not all(math.isfinite(v) for v in result):
            raise ValueError('NumberLine coordinates must be finite')
        return result

    n2p = number_to_point

    def point_to_number(self, point):
        point = Vector(point)
        if not all(math.isfinite(v) for v in point):
            raise ValueError('NumberLine point must be finite')
        start, end = self.get_start_and_end()
        direction = end-start
        length = math.hypot(*direction)
        if length == 0:
            raise ValueError('Cannot convert coordinates on a collapsed NumberLine')
        alpha = sum(a*(b/length) for a,b in zip(point-start,direction))/length
        return self._real(self.x_min+alpha*(self.x_max-self.x_min),'NumberLine result')

    p2n = point_to_number

    def __matmul__(self, number):
        return self.n2p(number)

    def __rmatmul__(self, point):
        return self.p2n(point)

    def get_tick_range(self):
        span = (self.x_max-self.x_min)/self.x_step
        if not math.isfinite(span) or span > 999:
            raise ValueError('NumberLine supports at most 1000 ticks or labels per addition')
        if self.x_min > 0 or self.x_max < 0:
            values = [self.x_min+i*self.x_step for i in range(math.floor(span+1e-9)+1)]
        else:
            lo = math.ceil(self.x_min/self.x_step-1e-9)
            hi = math.floor(self.x_max/self.x_step+1e-9)
            values = [i*self.x_step for i in range(lo,hi+1)]
        return [value for value in values if
                not (self.include_tip and abs(value-self.x_max) <= 1e-9)
                and not (self.exclude_origin_tick and value == 0)]

    def get_tick(self, x, size=None):
        size = self.tick_size if size is None else size
        self._real(size,'tick size',nonnegative=True)
        vector = self.get_vector()
        length = self.get_length()
        if length == 0:
            raise ValueError('Cannot place ticks on a collapsed NumberLine')
        normal = Vector((-vector[1],vector[0],0))*(size/length)
        point = self.n2p(x)
        return Line(point-normal,point+normal,color=self.stroke_color,
                    stroke_width=self.stroke_width,stroke_opacity=self.stroke_opacity)

    def _add_world_decoration(self, decoration, role):
        # New geometry is positioned in world coordinates. Invert this parent,
        # then compensate for its changed bounding-box pivot after insertion.
        if self.geometry_scale == 0:
            raise ValueError('Cannot add decorations to a collapsed NumberLine')
        center = self._geometry_center()
        def local(point):
            offset = Vector(point)-Vector(self.position)-center
            return center+Vector((offset[0]*math.cos(self.angle)+offset[1]*math.sin(self.angle),
                                  -offset[0]*math.sin(self.angle)+offset[1]*math.cos(self.angle),0))*(1/self.geometry_scale)
        for child in decoration.children:
            if isinstance(child, Line):
                child.put_start_and_end_on(local(child.get_start()),local(child.get_end()))
            else:
                child.move_to(local(child.get_center()))
                child.angle -= self.angle
                child.geometry_scale /= self.geometry_scale
        decoration._number_line_role = role
        self.add(decoration)
        delta = center-self._geometry_center()
        rotated = Vector((delta[0]*math.cos(self.angle)-delta[1]*math.sin(self.angle),
                          delta[0]*math.sin(self.angle)+delta[1]*math.cos(self.angle),0))*self.geometry_scale
        self.shift(delta-rotated)
        return self

    def add_ticks(self):
        ticks = VGroup(*(self.get_tick(value,self.tick_size*(self.longer_tick_multiple
                         if value in self.numbers_with_elongated_ticks else 1))
                         for value in self.get_tick_range()))
        return self._add_world_decoration(ticks,'ticks')

    def get_tick_marks(self):
        return self.ticks

    def get_number_mobject(self, x, direction=None, buff=None, font_size=None, **number_config):
        direction = self._direction(self.label_direction if direction is None else direction)
        buff = self.line_to_number_buff if buff is None else buff
        self._real(buff,'label buffer',nonnegative=True)
        options = dict(self.decimal_number_config,**number_config)
        options.setdefault('color',self.color)
        return DecimalNumber(x,font_size=self.font_size if font_size is None else font_size,
                             **options).next_to(self.n2p(x),direction=direction,buff=buff)

    def add_numbers(self, x_values=None, excluding=None, font_size=None, **kwargs):
        values = self.get_tick_range() if x_values is None else self._numbers(x_values)
        excluding = self.numbers_to_exclude if excluding is None else self._numbers(excluding)
        labels = VGroup(*(self.get_number_mobject(value,font_size=font_size,**kwargs)
                          for value in values if value not in excluding))
        return self._add_world_decoration(labels,'numbers')


class Axes(VGroup):
    """Two linear NumberLines with transform-aware XY coordinate conversion."""
    def __init__(self, x_range=None, y_range=None, x_length=None, y_length=None,
                 axis_config=None, x_axis_config=None, y_axis_config=None, tips=True, **kwargs):
        if not isinstance(tips,bool):
            raise ValueError('Axes tips must be a boolean')
        super().__init__(**kwargs)
        common = dict(color=self.color,stroke_color=self.stroke_color,
                      stroke_width=self.stroke_width,stroke_opacity=self.stroke_opacity,
                      include_tip=tips,numbers_to_exclude=[0],exclude_origin_tick=True)
        def merge(base, options):
            result = copy.deepcopy(base)
            if options is not None:
                if not isinstance(options,dict):
                    raise TypeError('Axis configuration must be a dictionary')
                for key,value in options.items():
                    if isinstance(value,dict) and isinstance(result.get(key),dict):
                        result[key] = dict(result[key],**value)
                    else:
                        result[key] = copy.deepcopy(value)
            return result
        common = merge(common,axis_config)
        x_options = merge(common,x_axis_config)
        y_options = merge(merge(common,dict(rotation=PI/2,label_direction=LEFT)),y_axis_config)
        if y_range is None:
            radius = max(1,round(config.frame_height/2))
            y_range = [-radius,radius,1]
        x_options['length'] = max(1,round(config.frame_width)-2) if x_length is None else x_length
        y_options['length'] = max(1,round(config.frame_height)-2) if y_length is None else y_length
        x_axis = NumberLine(x_range,**x_options)
        y_axis = NumberLine(y_range,**y_options)
        for axis, role in ((x_axis,'x'),(y_axis,'y')):
            axis.shift(axis.n2p(self._origin_shift(axis.x_range))*(-1))
            axis._axes_role = role
        self.add(x_axis,y_axis)
        self.x_range,self.y_range = x_axis.x_range[:],y_axis.x_range[:]
        self.num_sampled_graph_points_per_tick = 10
        # Center the coordinate rectangle, including ranges which exclude zero.
        middle = self.c2p((x_axis.x_min+x_axis.x_max)/2,(y_axis.x_min+y_axis.x_max)/2)
        self.shift(middle*(-1))

    @staticmethod
    def _origin_shift(axis_range):
        return max(axis_range[0],min(axis_range[1],0))

    def _axis(self, role):
        for child in self.children:
            if child.__dict__.get('_axes_role') == role:
                return child
        raise ValueError('Axes has no ' + role + ' axis')

    @property
    def x_axis(self):
        return self._axis('x')

    @property
    def y_axis(self):
        return self._axis('y')

    @property
    def axes(self):
        return VGroup(self.x_axis,self.y_axis)

    def get_axes(self):
        return self.axes

    def get_axis(self, index):
        return self.axes[index]

    def get_x_axis(self):
        return self.x_axis

    def get_y_axis(self):
        return self.y_axis

    def coords_to_point(self, *coords):
        if len(coords) == 1 and isinstance(coords[0],(list,tuple)):
            coords = coords[0]
            if coords and isinstance(coords[0],(list,tuple)):
                if len(coords) > 1000:
                    raise ValueError('Axes coordinate batches are limited to 1000 points')
                return [self.coords_to_point(*point) for point in coords]
        if len(coords) not in (2,3):
            raise ValueError('Axes coordinates need x, y and optionally zero z')
        sequences = [value for value in coords if isinstance(value,(list,tuple))]
        if sequences:
            count = len(sequences[0])
            if count > 1000 or any(len(value) != count for value in sequences):
                raise ValueError('Axes coordinate arrays need equal lengths of at most 1000')
            return [self.coords_to_point(*(value[i] if isinstance(value,(list,tuple)) else value
                                          for value in coords)) for i in range(count)]
        for value in coords:
            NumberLine._real(value,'Axes coordinate')
        if len(coords) == 3 and coords[2] != 0:
            raise NotImplementedError('Axes supports only the XY plane')
        origin = self.x_axis.n2p(self._origin_shift(self.x_axis.x_range))
        return self._point_to_world(self.x_axis.n2p(coords[0])+self.y_axis.n2p(coords[1])-origin)

    c2p = coords_to_point

    def get_origin(self):
        return self.c2p(0,0)

    def _basis(self):
        # Query the nested NumberLines in Axes-local space, then apply this parent.
        origin = self.x_axis.n2p(self._origin_shift(self.x_axis.x_range))
        world = self._point_to_world(origin)
        vectors = [self._point_to_world(origin+axis.get_unit_vector())-world
                   for axis in (self.x_axis,self.y_axis)]
        return vectors

    def get_x_unit_size(self):
        return math.hypot(*self._basis()[0])

    def get_y_unit_size(self):
        return math.hypot(*self._basis()[1])

    def point_to_coords(self, point):
        if isinstance(point,(list,tuple)) and point and isinstance(point[0],(list,tuple)):
            if len(point) > 1000:
                raise ValueError('Axes coordinate batches are limited to 1000 points')
            return [self.point_to_coords(value) for value in point]
        point = Vector(point)
        if not all(math.isfinite(v) for v in point):
            raise ValueError('Axes point must be finite')
        x,y = self._basis()
        lx,ly = math.hypot(*x),math.hypot(*y)
        if lx == 0 or ly == 0:
            raise ValueError('Cannot invert collapsed Axes')
        x,y = x*(1/lx),y*(1/ly)
        determinant = x[0]*y[1]-x[1]*y[0]
        if abs(determinant) < 1e-12:
            raise ValueError('Cannot invert parallel Axes')
        offset = point-self.get_origin()
        result = [(offset[0]*y[1]-offset[1]*y[0])/determinant/lx,
                  (x[0]*offset[1]-x[1]*offset[0])/determinant/ly]
        for value in result:
            NumberLine._real(value,'Axes result')
        return result

    p2c = point_to_coords

    def __matmul__(self, coords):
        return self.c2p(coords.get_center() if isinstance(coords,Mobject) else coords)

    def __rmatmul__(self, point):
        return self.p2c(point)

    def add_coordinates(self, *axes_numbers, **kwargs):
        if len(axes_numbers) > 2:
            raise ValueError('Axes accepts number lists for x and y only')
        center = self._geometry_center()
        targets = []
        for index, axis in enumerate((self.x_axis,self.y_axis)):
            target = axis.copy()
            target.add_numbers(axes_numbers[index] if index < len(axes_numbers) else None,**kwargs)
            targets.append(target)
        # Validate both additions before mutating either live axis.
        for axis,target in zip((self.x_axis,self.y_axis),targets):
            axis.become(target)
        delta = center-self._geometry_center()
        rotated = Vector((delta[0]*math.cos(self.angle)-delta[1]*math.sin(self.angle),
                          delta[0]*math.sin(self.angle)+delta[1]*math.cos(self.angle),0))*self.geometry_scale
        return self.shift(delta-rotated)

    def get_x_axis_label(self, label, direction=UR, buff=.1, **kwargs):
        label = label if isinstance(label,Mobject) else MathTex(str(label))
        return label.next_to(self._point_to_world(self.x_axis.get_end()),direction,buff,**kwargs)

    def get_y_axis_label(self, label, direction=UR, buff=.1, **kwargs):
        label = label if isinstance(label,Mobject) else MathTex(str(label))
        return label.next_to(self._point_to_world(self.y_axis.get_end()),direction,buff,**kwargs)

    def get_axis_labels(self, x_label='x', y_label='y'):
        return VGroup(self.get_x_axis_label(x_label),self.get_y_axis_label(y_label))

    def plot(self, function, x_range=None, use_vectorized=False, **kwargs):
        if not callable(function):
            raise TypeError('Axes.plot expects a scalar function')
        values = self.x_range[:] if x_range is None else list(x_range)
        density = NumberLine._real(self.num_sampled_graph_points_per_tick,'Plot samples per tick',positive=True)
        step = self.x_range[2]/density
        if x_range is None:
            values[2] = step
        values = ParametricFunction._range(values,step)
        graph = ParametricFunction(lambda t: self.c2p(t,function(t)),t_range=values,
                                   use_vectorized=use_vectorized,**kwargs)
        graph.underlying_function = function
        return graph

    def plot_parametric_curve(self, function, **kwargs):
        if not callable(function):
            raise TypeError('Parametric plotting expects a callable returning XY coordinates')
        return ParametricFunction(lambda t: self.c2p(function(t)),**kwargs)

    @staticmethod
    def _scalar_graph_function(graph):
        function = getattr(graph,'underlying_function',None)
        if not isinstance(graph,Mobject) or not callable(function):
            raise TypeError('Graph queries need a scalar plotted function')
        return function

    def input_to_graph_coords(self, x, graph):
        NumberLine._real(x,'Graph input')
        y = self._scalar_graph_function(graph)(x)
        NumberLine._real(y,'Graph output')
        return x,y

    i2gc = input_to_graph_coords

    def input_to_graph_point(self, x, graph):
        return self.c2p(*self.input_to_graph_coords(x,graph))

    i2gp = input_to_graph_point

    def _tangent_difference(self, x, graph, dx):
        NumberLine._real(dx,'Tangent dx')
        if dx == 0:
            raise ValueError('Tangent dx must be nonzero')
        x0,y0 = self.i2gc(x,graph)
        x1 = x0+dx
        NumberLine._real(x1,'Tangent sample')
        if x1 == x0:
            raise ValueError('Tangent dx is too small to change this input')
        _,y1 = self.i2gc(x1,graph)
        delta = y1-y0
        NumberLine._real(delta,'Tangent difference')
        return x1-x0,delta

    def angle_of_tangent(self, x, graph, dx=1e-8):
        dx,dy = self._tangent_difference(x,graph,dx)
        return math.atan2(dy,dx)

    def slope_of_tangent(self, x, graph, dx=1e-8):
        dx,dy = self._tangent_difference(x,graph,dx)
        return NumberLine._real(dy/dx,'Tangent slope')

    def plot_derivative_graph(self, graph, color=GREEN, **kwargs):
        self._scalar_graph_function(graph)
        return self.plot(lambda x:self.slope_of_tangent(x,graph),color=color,**kwargs)

    def plot_antiderivative_graph(self, graph, y_intercept=0, samples=50,
                                  use_vectorized=False, **kwargs):
        function = self._scalar_graph_function(graph)
        NumberLine._real(y_intercept,'Antiderivative intercept')
        if isinstance(samples,bool) or not isinstance(samples,int) or not 2 <= samples <= 10000:
            raise ValueError('Antiderivative samples must be an integer from 2 to 10000')
        def integral(x):
            values = [NumberLine._real(function(x*(index/(samples-1))),'Integral sample')
                      for index in range(samples)]
            step = x/(samples-1)
            terms = [NumberLine._real((a*.5+b*.5)*step,'Integral interval')
                     for a,b in zip(values,values[1:])]
            try:
                result = math.fsum(terms)+y_intercept
            except OverflowError as error:
                raise ValueError('Integral result must be finite') from error
            return NumberLine._real(result,'Integral result')
        return self.plot(integral,use_vectorized=use_vectorized,**kwargs)

    def get_riemann_rectangles(self, graph, x_range=None, dx=.1, input_sample_type='left',
                               stroke_width=1, stroke_color=BLACK, fill_opacity=1,
                               color=(BLUE,GREEN), show_signed_area=True, bounded_graph=None,
                               blend=False, width_scale_factor=1.001):
        self._scalar_graph_function(graph)
        if bounded_graph is not None:
            self._scalar_graph_function(bounded_graph)
        NumberLine._real(dx,'Riemann dx',positive=True)
        NumberLine._real(width_scale_factor,'Rectangle width scale',positive=True)
        Mobject._validate_width(stroke_width)
        Mobject._validate_opacity(fill_opacity)
        if not isinstance(show_signed_area,bool) or not isinstance(blend,bool):
            raise ValueError('Riemann area and blend flags must be booleans')
        if input_sample_type not in ('left','right','center'):
            raise ValueError('Riemann input_sample_type must be left, right or center')
        if x_range is None:
            low,high = graph.t_min,graph.t_max
            if bounded_graph is not None:
                low,high = max(low,bounded_graph.t_min),min(high,bounded_graph.t_max)
            values = [low,high]
        else:
            values = list(x_range)
            if len(values) not in (2,3):
                raise ValueError('Riemann x_range needs two or three values')
        low,high,_ = ParametricFunction._range([*values[:2],dx],dx)
        count = (high-low)/dx
        if not math.isfinite(count) or count > 1000:
            raise ValueError('Riemann groups are limited to 1000 rectangles')
        count = math.ceil(count)
        palette = list(color) if isinstance(color,(list,tuple)) else [color]
        if not palette or len(palette) > 64:
            raise ValueError('Riemann colors need between 1 and 64 colors')
        def channels(value):
            if not isinstance(value,str) or len(value) != 7 or value[0] != '#':
                raise ValueError('Riemann colors must be six-digit hex colors')
            try:
                return [int(value[index:index+2],16) for index in (1,3,5)]
            except ValueError as error:
                raise ValueError('Riemann colors must be six-digit hex colors') from error
        stops = [channels(value) for value in palette]
        channels(stroke_color)
        rectangles = VGroup()
        fraction = {'left':0,'center':.5,'right':1}[input_sample_type]
        for index in range(count):
            x = low+index*dx
            if x >= high:
                break
            right = x+max(width_scale_factor,fraction)*dx
            sample = x+fraction*dx
            NumberLine._real(right,'Rectangle endpoint')
            if right == x or fraction and sample == x:
                raise ValueError('Riemann dx is too small to change this input')
            top = self.i2gc(sample,graph)[1]
            baseline = (self._origin_shift(self.y_range) if bounded_graph is None else
                        self.i2gc(x,bounded_graph)[1])
            location = (len(stops)-1)*index/max(1,count-1)
            stop = min(len(stops)-1,math.floor(location))
            alpha = location-stop
            rgb = [round(a+(b-a)*alpha) for a,b in zip(stops[stop],stops[min(stop+1,len(stops)-1)])]
            if show_signed_area and top < baseline:
                rgb = [255-value for value in rgb]
            fill = '#' + ''.join(f'{value:02X}' for value in rgb)
            bottom,upper = min(baseline,top),max(baseline,top)
            # Keep Rectangle identity but use four XY corners for transformed axes.
            outline = Polygon(self.c2p(right,upper),self.c2p(x,upper),
                              self.c2p(x,bottom),self.c2p(right,bottom),
                              color=fill,fill_opacity=fill_opacity,
                              stroke_color=fill if blend else stroke_color,stroke_width=stroke_width)
            rectangles.add(Rectangle().become(outline))
        return rectangles

    def get_area(self, graph, x_range=None, color=(BLUE,GREEN), opacity=.3,
                 bounded_graph=None, **kwargs):
        graphs = [graph] if bounded_graph is None else [graph,bounded_graph]
        for curve in graphs:
            if not isinstance(curve,ParametricFunction):
                raise TypeError('Area boundaries must be plotted parametric graphs')
        values = [graph.t_min,graph.t_max] if x_range is None else list(x_range)
        if len(values) != 2:
            raise ValueError('Area x_range needs exactly two values')
        low,high,_ = ParametricFunction._range(values,1)
        if bounded_graph is not None:
            if bounded_graph.t_min > high or bounded_graph.t_max < low:
                raise ValueError('Area and bounding graph ranges do not overlap')
            low,high = max(low,bounded_graph.t_min),min(high,bounded_graph.t_max)
        Mobject._validate_opacity(opacity)
        palette = list(color) if isinstance(color,(list,tuple)) else [color]
        if not 1 <= len(palette) <= 64 or any(
                not isinstance(value,str) or len(value) != 7 or value[0] != '#' or
                any(char not in '0123456789abcdefABCDEF' for char in value[1:])
                for value in palette):
            raise ValueError('Area colors need 1 to 64 six-digit hex colors')
        # Validate styles before invoking either boundary provider.
        area = Polygon(**kwargs)
        boundaries = []
        for curve in graphs:
            points = [Vector(point) for point in curve.get_points()
                      if low <= self.p2c(point)[0] <= high]
            boundaries.append([curve.get_point_from_function(low),*points,
                               curve.get_point_from_function(high)])
        if bounded_graph is None:
            points = [self.c2p(low,0),*boundaries[0],self.c2p(high,0)]
        else:
            points = boundaries[0]+list(reversed(boundaries[1]))
        # Keep the Community Polygon convention, including sampled control points.
        area.vertices = [list(point) for point in points]
        return area.set_opacity(opacity).set_color(palette if len(palette)>1 else palette[0])

    def get_secant_slope_group(self, x, graph, dx=None, dx_line_color=YELLOW,
                                dy_line_color=None, dx_label=None, dy_label=None,
                                include_secant_line=True, secant_line_color=GREEN,
                                secant_line_length=10):
        self._scalar_graph_function(graph)
        NumberLine._real(x,'Secant input')
        if dx is not None:
            NumberLine._real(dx,'Secant dx')
        dx = (self.x_range[1]-self.x_range[0])/10 if dx is None or dx == 0 else dx
        NumberLine._real(dx,'Secant dx')
        if x+dx == x:
            raise ValueError('Secant dx is too small to change this input')
        NumberLine._real(secant_line_length,'Secant length',positive=True)
        if not isinstance(include_secant_line,bool):
            raise ValueError('Secant inclusion flag must be a boolean')
        def make_label(value):
            if value is None:
                return None
            if isinstance(value,Mobject):
                return value.copy()
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                NumberLine._real(value,'Secant label')
            elif not isinstance(value,str):
                raise TypeError('Secant labels must be strings, real numbers or Mobjects')
            return MathTex(str(value))
        dx_mob,df_mob = make_label(dx_label),make_label(dy_label)
        p1,p2 = self.i2gp(x,graph),self.i2gp(x+dx,graph)
        corner = Vector((p2[0],p1[1],0))
        dy_line_color = graph.color if dy_line_color is None else dy_line_color
        group = _SecantSlopeGroup()
        for role,line in (('dx_line',Line(p1,corner,color=dx_line_color)),
                          ('df_line',Line(corner,p2,color=dy_line_color))):
            line._secant_role = role
            group.add(line)
        def label_bounds(label):
            # Font metrics live in the browser; use an explicit size estimate here.
            if label._type in ('text','mathtex'):
                height = label.font_size/50
                width = max(1,len(label.text))*.6*height
                center = label._geometry_center()
                corners = [label._point_to_world(center+Vector((a*width/2,b*height/2,0)))
                           for a in (-1,1) for b in (-1,1)]
            elif label.children:
                corners = []
                for child in label.children:
                    left,bottom,right,top = label_bounds(child)
                    corners.extend(label._point_to_world((a,b,0))
                                   for a in (left,right) for b in (bottom,top))
            else:
                return label._bounds()
            return (min(p[0] for p in corners),min(p[1] for p in corners),
                    max(p[0] for p in corners),max(p[1] for p in corners))
        labels = VGroup(*(label for label in (dx_mob,df_mob) if label is not None))
        if len(labels):
            left,bottom,right,top = label_bounds(labels)
            width,height = right-left,top-bottom
            span_x,span_y = abs(p2[0]-p1[0]),abs(p2[1]-p1[1])
            factor = min(1,.8*span_x/width if width else 1,
                         .8*span_y/height if height else 1)
            for label in labels:
                label.scale(factor)
        sign = 1 if dx > 0 else -1
        for label,role,line,direction in ((dx_mob,'dx_label',group.dx_line,DOWN*sign),
                                          (df_mob,'df_label',group.df_line,RIGHT*sign)):
            if label is not None:
                left,bottom,right,top = label_bounds(label)
                # Center anchors lack glyph bounds: explicitly leave room for text.
                offset = (top-bottom)/2
                if label._type in ('text','mathtex'):
                    offset += (top-bottom)/2 if direction[1] else (right-left)/2
                label.next_to(line,direction,buff=offset).set_color(line.color)
                label._secant_role = role
                group.add(label)
        if include_secant_line:
            vector = p2-p1
            length = math.hypot(*vector)
            if length == 0:
                raise ValueError('Cannot extend a collapsed secant')
            center = (p1+p2)*.5
            NumberLine._real(length,'Secant span',positive=True)
            half = Vector(value/length for value in vector)*(secant_line_length/2)
            start,end = Line._endpoints(center-half,center+half)
            secant = Line(start,end,color=secant_line_color)
            secant._secant_role = 'secant_line'
            group.add(secant)
        return group


class NumberPlane(Axes):
    """A linear Cartesian grid using the same local coordinates as its axes."""
    def __init__(self, x_range=None, y_range=None, x_length=None, y_length=None,
                 background_line_style=None, faded_line_style=None, faded_line_ratio=1,
                 make_smooth_after_applying_functions=True, **kwargs):
        if isinstance(faded_line_ratio,bool) or not isinstance(faded_line_ratio,int) or faded_line_ratio < 0:
            raise ValueError('NumberPlane faded_line_ratio must be a nonnegative integer')
        if not isinstance(make_smooth_after_applying_functions,bool):
            raise ValueError('NumberPlane smoothing flag must be a boolean')
        xr = ParametricFunction._range(x_range if x_range is not None else
                                      [-config.frame_width/2,config.frame_width/2,1],1)
        yr = ParametricFunction._range(y_range if y_range is not None else
                                      [-config.frame_height/2,config.frame_height/2,1],1)
        if xr[0] == xr[1] or yr[0] == yr[1]:
            raise ValueError('NumberPlane ranges must increase')
        offsets = [self._grid_offsets(values,faded_line_ratio) for values in (yr,xr)]
        if sum(len(values) for values in offsets) > 1000:
            raise ValueError('NumberPlane grids are limited to 1000 lines')
        def merged(defaults, options):
            if options is not None and not isinstance(options,dict):
                raise TypeError('NumberPlane styles and axis configurations must be dictionaries')
            result = copy.deepcopy(defaults)
            result.update(copy.deepcopy(options or {}))
            return result
        background = merged(dict(stroke_color=BLUE_D,stroke_width=2,stroke_opacity=1),background_line_style)
        faded = ({key: value*.5 if isinstance(value,(int,float)) and not isinstance(value,bool) else value
                  for key,value in background.items()} if faded_line_style is None else
                 merged({},faded_line_style))
        # Validate styles even if the chosen grid has no faded lines.
        Line(**background)
        Line(**faded)
        axis_options = merged(dict(stroke_width=2,include_ticks=False,include_tip=False,
                                   line_to_number_buff=.1,label_direction=DR,font_size=24),
                              kwargs.pop('axis_config',None))
        y_options = merged(dict(label_direction=DR),kwargs.pop('y_axis_config',None))
        super().__init__(xr,yr,x_length=xr[1]-xr[0] if x_length is None else x_length,
                         y_length=yr[1]-yr[0] if y_length is None else y_length,
                         axis_config=axis_options,y_axis_config=y_options,**kwargs)
        self.background_line_style,self.faded_line_style = background,faded
        self.faded_line_ratio = faded_line_ratio
        self.make_smooth_after_applying_functions = make_smooth_after_applying_functions
        major,minor = VGroup(),VGroup()
        major._plane_role,minor._plane_role = 'background','faded'
        for axis,perpendicular,values,role in ((self.x_axis,self.y_axis,offsets[0],'x'),
                                             (self.y_axis,self.x_axis,offsets[1],'y')):
            for offset,is_major in values:
                direction = perpendicular.get_unit_vector()*offset
                line = Line(axis.get_start()+direction,axis.get_end()+direction,
                            **(background if is_major else faded))
                line._grid_axis = role
                (major if is_major else minor).add(line)
        # Grid points are already Axes-local. Do not bake this parent's translation.
        self.add_to_back(minor,major)

    @staticmethod
    def _grid_offsets(values, ratio):
        low,high,freq = values
        ratio = max(1,ratio)
        try:
            step = freq/ratio
        except OverflowError as error:
            raise ValueError('NumberPlane grid ratio is too large') from error
        if step == 0 or not math.isfinite(step):
            raise ValueError('NumberPlane grid step must be finite and positive')
        extents = (min(high-low,high),-max(low-high,low))
        result = [(0,ratio == 1)]
        for sign,extent in zip((1,-1),extents):
            count = extent/step
            if not math.isfinite(count) or count > 1001:
                raise ValueError('NumberPlane grids are limited to 1000 lines')
            for index in range(1,max(1,math.ceil(count))):
                offset = sign*index*step
                if abs(offset) < extent:
                    result.append((offset,index % ratio == 0))
        return result

    def _plane_group(self, role):
        for child in self.children:
            if child.__dict__.get('_plane_role') == role:
                return child
        raise ValueError('NumberPlane has no ' + role + ' lines')

    @property
    def background_lines(self):
        return self._plane_group('background')

    @property
    def faded_lines(self):
        return self._plane_group('faded')

    @property
    def x_lines(self):
        return VGroup(*(line for line in self.background_lines if line.__dict__.get('_grid_axis') == 'x'))

    @property
    def y_lines(self):
        return VGroup(*(line for line in self.background_lines if line.__dict__.get('_grid_axis') == 'y'))

    def get_vector(self, coords, **kwargs):
        kwargs.pop('buff',None)  # Manim always makes these vectors touch the origin.
        start,end = Line._endpoints(self.c2p(0,0),self.c2p(coords))
        return Arrow(start,end,**kwargs)


class ComplexPlane(NumberPlane):
    """Linear complex coordinates on the Cartesian grid."""
    @staticmethod
    def _complex(number):
        try:
            value = complex(number)
        except (TypeError,ValueError,OverflowError) as error:
            raise ValueError('Complex coordinates need a finite complex-compatible scalar') from error
        if not math.isfinite(value.real) or not math.isfinite(value.imag):
            raise ValueError('Complex coordinates must be finite')
        return value

    def number_to_point(self, number):
        value = self._complex(number)
        return self.c2p(value.real,value.imag)

    n2p = number_to_point

    def point_to_number(self, point):
        x,y = self.p2c(point)
        return complex(x,y)

    p2n = point_to_number

    def _get_default_coordinate_values(self):
        return self.x_axis.get_tick_range()+[complex(0,y) for y in self.y_axis.get_tick_range() if y != 0]

    @property
    def coordinate_labels(self):
        if '_coordinate_labels' in self.__dict__:
            return self._coordinate_labels
        for child in reversed(self.children):
            if child.__dict__.get('_complex_labels'):
                return child
        raise ValueError('ComplexPlane has no coordinate labels')

    def get_coordinate_labels(self, *numbers, **kwargs):
        values = numbers if numbers else self._get_default_coordinate_values()
        if len(values) > 1000:
            raise ValueError('Complex coordinate labels are limited to 1000 values')
        values = [self._complex(number) for number in values]
        labels = VGroup()
        for value in values:
            imaginary = abs(value.imag) > abs(value.real)
            axis = self.y_axis if imaginary else self.x_axis
            coefficient = value.imag if imaginary else value.real
            options = dict(kwargs)
            if imaginary:
                options['unit'] = 'i'
            label = axis.get_number_mobject(coefficient,**options)
            label.next_to(self._point_to_world(axis.n2p(coefficient)),
                          direction=axis.label_direction if options.get('direction') is None else options['direction'],
                          buff=axis.line_to_number_buff if options.get('buff') is None else options['buff'])
            labels.add(label)
        labels._complex_labels = True
        # Only unattached label queries need a runtime reference; JSON excludes it.
        self._coordinate_labels = labels
        return labels

    def add_coordinates(self, *numbers, **kwargs):
        if self.geometry_scale == 0:
            raise ValueError('Cannot add labels to a collapsed ComplexPlane')
        labels = self.get_coordinate_labels(*numbers,**kwargs)
        center = self._geometry_center()
        for label in labels:
            offset = label.get_center()-Vector(self.position)-center
            local = center+Vector((offset[0]*math.cos(self.angle)+offset[1]*math.sin(self.angle),
                                   -offset[0]*math.sin(self.angle)+offset[1]*math.cos(self.angle),0))*(1/self.geometry_scale)
            label.move_to(local)
            label.angle -= self.angle
            label.geometry_scale /= self.geometry_scale
        self.add(labels)
        del self._coordinate_labels
        delta = center-self._geometry_center()
        rotated = Vector((delta[0]*math.cos(self.angle)-delta[1]*math.sin(self.angle),
                          delta[0]*math.sin(self.angle)+delta[1]*math.cos(self.angle),0))*self.geometry_scale
        return self.shift(delta-rotated)


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
        result = {key: interpolate(value, end.get(key, value), alpha)
                  for key, value in start.items()}
        if 'subpath_lengths' in start:
            result['subpath_lengths'] = copy.deepcopy(end.get('subpath_lengths', start['subpath_lengths'])
                                                      if alpha >= 1 else start['subpath_lengths'])
        if start.get('type') == end.get('type') == 'text' and '_number_format' in start and '_number_format' in end:
            # Formatting switches discretely; only the real value interpolates.
            result['_number_format'] = copy.deepcopy(end['_number_format'] if alpha >= 1 else start['_number_format'])
            result['text'] = _number_text(result['number'], result['_number_format'])
        return result
    if isinstance(start, str) and isinstance(end, str) and start.startswith('#') and end.startswith('#') and len(start) == len(end) == 7:
        try:
            channels = [round(int(start[i:i+2], 16) * (1-alpha) + int(end[i:i+2], 16) * alpha) for i in (1, 3, 5)]
            return '#' + ''.join(f'{channel:02x}' for channel in channels)
        except ValueError:
            pass
    return copy.deepcopy(end if alpha >= 1 else start)


def _path_curves(snapshot):
    kind = snapshot['type']
    if kind == 'bezierpath':
        return copy.deepcopy(snapshot['curves'])
    if kind == 'annulus':
        outer = _path_curves({'type':'circle', 'radius':snapshot['outer_radius']})
        inner = _path_curves({'type':'circle', 'radius':snapshot['inner_radius']})
        return outer + [list(reversed(curve)) for curve in reversed(inner)]
    if kind in ('circle', 'arc', 'ellipse'):
        radius = 1 if kind == 'ellipse' else snapshot['radius']
        if not math.isfinite(radius) or radius < 0:
            raise ValueError('Path radius must be nonnegative and finite')
        start = snapshot.get('start_angle', 0)
        sweep = snapshot.get('arc_angle', TAU)
        count = max(1, math.ceil(abs(sweep) / (PI / 4)))
        step = sweep / count
        factor = 4 / 3 * math.tan(step / 4)
        anchors = [Vector((radius * math.cos(start + step*i),
                           radius * math.sin(start + step*i), 0)) for i in range(count + 1)]
        if abs(sweep) == TAU:
            anchors[-1] = anchors[0]
        curves = []
        for a, b in zip(anchors, anchors[1:]):
            tangent_a, tangent_b = Vector((-a[1], a[0], 0)), Vector((-b[1], b[0], 0))
            curves.append([list(a), list(a + tangent_a * factor),
                           list(b - tangent_b * factor), list(b)])
        if kind == 'ellipse':
            curves = [[[p[0] * snapshot['width'] / 2, p[1] * snapshot['height'] / 2, 0]
                       for p in curve] for curve in curves]
        return curves
    if kind in ('square', 'rectangle'):
        width = snapshot['side_length'] if kind == 'square' else snapshot['width']
        height = snapshot['side_length'] if kind == 'square' else snapshot['height']
        vertices = [(width/2,height/2), (-width/2,height/2),
                    (-width/2,-height/2), (width/2,-height/2)]
    elif kind == 'triangle':
        height = math.sqrt(3) / 2
        vertices = [(0,height*2/3), (-0.5,-height/3), (0.5,-height/3)]
    elif kind == 'line':
        vertices = [snapshot['start'], snapshot['end']]
    else:
        vertices = snapshot['vertices']
    if not vertices:
        return []
    points = [Vector(p) for p in vertices]
    if kind in ('polygon', 'square', 'rectangle', 'triangle'):
        points.append(points[0])
    if len(points) == 1:
        return [[list(points[0]) for _ in range(4)]]
    return [[list(a), list(a * (2/3) + b * (1/3)),
             list(a * (1/3) + b * (2/3)), list(b)]
            for a, b in zip(points, points[1:])]


def _split_cubic(curve, t):
    p0, p1, p2, p3 = [Vector(p) for p in curve]
    a, b, c = [p * (1-t) + q * t for p, q in ((p0,p1), (p1,p2), (p2,p3))]
    d, e = a * (1-t) + b * t, b * (1-t) + c * t
    midpoint = d * (1-t) + e * t
    return ([list(p) for p in (p0,a,d,midpoint)],
            [list(p) for p in (midpoint,e,c,p3)])


def _subdivide_curves(curves, count):
    # Distribute inserted curves across existing segments, preserving every join.
    quotient, remainder = divmod(count, len(curves))
    result = []
    for index, curve in enumerate(curves):
        parts = quotient + (index < remainder)
        remaining = curve
        for part in range(parts - 1):
            left, remaining = _split_cubic(remaining, 1 / (parts - part))
            result.append(left)
        result.append(remaining)
    return result


def _path_subpaths(snapshot, include_pending=True):
    if not include_pending and snapshot['type'] == 'polyline' and len(snapshot['vertices']) < 2:
        return []
    curves = _path_curves(snapshot)
    lengths = snapshot.get('subpath_lengths')
    if snapshot['type'] == 'annulus':
        lengths = [8, 8]
    paths = []
    if lengths:
        offset = 0
        for count in lengths:
            paths.append(curves[offset:offset+count])
            offset += count
    else:
        for curve in curves:
            if not paths or paths[-1][-1][-1] != curve[0]:
                paths.append([])
            paths[-1].append(curve)
    if include_pending and snapshot['type'] == 'bezierpath' and snapshot.get('vertices'):
        paths.append([[snapshot['vertices'][0][:] for _ in range(4)]])
    return paths


def _align_path_snapshots(start, target):
    path_types = ('polyline', 'polygon', 'bezierpath', 'circle', 'arc', 'ellipse',
                  'square', 'rectangle', 'triangle', 'line', 'annulus')
    if start['type'] not in path_types or target['type'] not in path_types:
        return None
    if start['type'] == target['type'] and start['type'] not in ('polyline', 'polygon', 'bezierpath'):
        return None  # Matching primitives retain their analytical interpolation.
    paths1, paths2 = _path_subpaths(start), _path_subpaths(target)
    if not paths1 or not paths2:
        return None  # Empty geometry has no endpoint to align; retain the fade.
    if (start['type'] == target['type'] and
            (len(paths1) == len(paths2) == 1 and len(paths1[0]) == len(paths2[0]) if start['type'] == 'bezierpath'
             else len(start['vertices']) == len(target['vertices']))):
        return None
    path_count = max(len(paths1), len(paths2))
    for paths in (paths1, paths2):
        while len(paths) < path_count:
            paths.append([[paths[-1][-1][-1][:] for _ in range(4)]])
    counts = [max(len(a), len(b)) for a, b in zip(paths1, paths2)]
    result = []
    for snapshot, paths in ((start, paths1), (target, paths2)):
        aligned = copy.deepcopy(snapshot)
        aligned['type'] = 'bezierpath'
        aligned['curves'] = [curve for path, count in zip(paths, counts)
                             for curve in _subdivide_curves(path, count)]
        aligned['vertices'] = []
        aligned['subpath_lengths'] = counts[:]
        # Keep the original pivot. Subdivision changes control-point bounds but
        # must not move a previously scaled/rotated curve at either endpoint.
        result.append(aligned)
    return tuple(result)


def _transform_plan(start, target):
    """Align immutable family snapshots once, before sampling their timeline."""
    if start['type'] == 'vgroup' or target['type'] == 'vgroup':
        def as_group(snapshot):
            if snapshot['type'] == 'vgroup':
                return copy.deepcopy(snapshot)
            group = VGroup().to_dict()
            group['children'] = [copy.deepcopy(snapshot)]
            return group
        start, target = as_group(start), as_group(target)
        count = max(len(start['children']), len(target['children']))
        def expand(children, other):
            if not children:
                # An empty family grows/shrinks at each corresponding child's
                # own center, without moving the containing group's pivot.
                result = copy.deepcopy(other)
                for child in result:
                    child['opacity'] = 0
                    child['geometry_scale'] = 0
                return result
            result, seen = [], set()
            for index in range(count):
                source_index = index * len(children) // count
                child = copy.deepcopy(children[source_index])
                if source_index in seen:
                    child['opacity'] = 0
                seen.add(source_index)
                result.append(child)
            return result
        first, last = start['children'], target['children']
        children = [_transform_plan(a, b) for a, b in
                    zip(expand(first, last), expand(last, first))]
        start.pop('children')
        target.pop('children')
        return ('group', start, target, children)
    aligned = _align_path_snapshots(start, target)
    if aligned:
        return ('interpolate', *aligned, [])
    matching = (start['type'] == target['type'] and
                (target['type'] != 'mathtex' or start['text'] == target['text']) and
                (target['type'] not in ('polygon', 'polyline') or
                 len(start['vertices']) == len(target['vertices'])) and
                (target['type'] != 'bezierpath' or
                 len(start['curves']) == len(target['curves'])))
    return ('interpolate' if matching else 'fade', start, target, [])


def _sample_transform(plan, alpha):
    kind, start, target, children = plan
    if kind == 'fade':
        first, last = copy.deepcopy(start), copy.deepcopy(target)
        first['opacity'] *= 1 - alpha
        last['opacity'] *= alpha
        return [first, last]
    result = interpolate(start, target, alpha)
    if kind == 'group':
        result['children'] = [snapshot for child in children
                              for snapshot in _sample_transform(child, alpha)]
    return [result]


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


class ShowPassingFlash(Animation):
    """Move a temporary cubic-parameter window over supported vector outlines."""
    def __init__(self, mobject, time_width=.1, **kwargs):
        super().__init__(mobject, **kwargs)
        if (isinstance(time_width, bool) or not isinstance(time_width, (int, float))
                or not math.isfinite(time_width) or time_width < 0):
            raise ValueError('ShowPassingFlash time_width must be nonnegative and finite')
        self.time_width = time_width

    def begin(self, scene):
        def validate(mobject):
            if not isinstance(mobject, Mobject):
                raise TypeError('ShowPassingFlash expects a supported vector outline or group')
            if mobject._type == 'vgroup':
                for child in mobject.children:
                    validate(child)
            elif mobject._type not in ('polyline', 'polygon', 'bezierpath', 'circle',
                                      'arc', 'ellipse', 'square', 'rectangle',
                                      'triangle', 'line', 'annulus'):
                raise TypeError('ShowPassingFlash expects supported vector outlines; glyphs and arrows are unsupported')
        validate(self.mobject)
        self.original = self.mobject.copy()
        super().begin(scene)

    def sample(self, alpha):
        upper = (1 + self.time_width) * max(0, min(1, alpha))
        lower, upper = max(0, upper - self.time_width), min(1, upper)
        def clip(source, snapshot):
            if source._type == 'vgroup':
                result = copy.deepcopy(snapshot)
                result['children'] = [clip(child, data) for child, data in
                                      zip(source.children, snapshot['children'])]
                # Keep the original group pivot even as child bounds shrink.
                return result
            return source.get_subcurve(lower, upper).to_dict()
        return [clip(self.original, self.start)]

    def finish(self, scene):
        # Sampling never changes live geometry, so the removed object is reusable.
        scene.remove(self.mobject)


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

    def begin(self, scene):
        super().begin(scene)
        self._transform_plan = None

    def sample(self, alpha):
        if self._transform_plan is None:
            self._transform_plan = _transform_plan(self.start, self.target.to_dict())
        return _sample_transform(self._transform_plan, alpha)

    def finish(self, scene):
        saved = self.mobject.__dict__.get('_saved_state')
        updaters, suspended = self.mobject.updaters, self.mobject.updating_suspended
        self.mobject.__dict__ = copy.deepcopy(self.target.__dict__)
        self.mobject.updaters, self.mobject.updating_suspended = updaters, suspended
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
        if name not in ('become', 'set_value', 'increment_value', 'shift', 'move_to', 'set_width', 'set_height', 'set_length', 'move_arc_center_to', 'put_start_and_end_on', 'next_to', 'arrange', 'set_color', 'set_fill', 'set_stroke', 'set_opacity', 'set_z_index', 'pointwise_become_partial', 'set_points', 'append_points', 'clear_points', 'add_subpath', 'append_vectorized_mobject', 'start_new_path', 'close_path', 'set_points_as_corners', 'set_points_smoothly', 'make_smooth', 'make_jagged', 'change_anchor_mode', 'add_points_as_corners', 'add_line_to', 'add_cubic_bezier_curve_to', 'reverse_direction', 'restore', 'scale', 'rotate'):
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
    camera_class = PreviewConfig

    def __init__(self, camera_config=None):
        self.camera = self.camera_class(**config.to_dict())
        for name, value in (camera_config or {}).items():
            setattr(self.camera, name, value)
        self.mobjects, self.frames = [], []
        self.foreground_mobjects = []
        self._elapsed_frames = 0

    @property
    def time(self):
        return self._elapsed_frames / FPS

    def add(self, *mobjects):
        for mobject in mobjects:
            if mobject not in self.mobjects:
                self.mobjects.append(mobject)
        self.mobjects = [m for m in self.mobjects if m not in self.foreground_mobjects] + self.foreground_mobjects
        return self

    def remove(self, *mobjects):
        self.mobjects = [m for m in self.mobjects if m not in mobjects]
        self.foreground_mobjects = [m for m in self.foreground_mobjects if m not in mobjects]
        return self

    def add_foreground_mobjects(self, *mobjects):
        roots = self._ordered_roots(mobjects)
        self.foreground_mobjects = [m for m in self.foreground_mobjects if m not in roots] + roots
        return self.add(*roots)

    def add_foreground_mobject(self, mobject):
        return self.add_foreground_mobjects(mobject)

    def remove_foreground_mobjects(self, *mobjects):
        roots = self._ordered_roots(mobjects)
        self.foreground_mobjects = [m for m in self.foreground_mobjects if m not in roots]
        return self

    def remove_foreground_mobject(self, mobject):
        return self.remove_foreground_mobjects(mobject)

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
        # Moving a root forward preserves its foreground membership.
        self.mobjects = [m for m in self.mobjects if m not in roots]
        self.add(*roots)
        return self

    def bring_to_back(self, *mobjects):
        roots = self._ordered_roots(mobjects)
        self.remove(*roots)
        self.mobjects = roots + self.mobjects
        return self

    def clear(self):
        self.mobjects = []
        self.foreground_mobjects = []
        return self

    def _update_mobjects(self, dt, overrides=None):
        """Expose sampled geometry to dependent callbacks without committing animations."""
        roots = list(self.mobjects)
        if isinstance(self.camera, MovingCamera) and self.camera.frame not in roots:
            roots.append(self.camera.frame)
        if not any(m.get_family_updaters() for m in roots):
            return
        saved, blocked = {}, set()
        def expose(mobject, snapshot):
            if mobject in saved:
                return
            saved[mobject] = mobject.__dict__
            mobject.__dict__ = dict(mobject.__dict__)
            for key, value in snapshot.items():
                if key not in ('type', 'children', 'geometry_center'):
                    mobject.__dict__[key] = copy.deepcopy(value)
            mobject._type = snapshot['type']
            mobject._sampled_geometry_center = snapshot['geometry_center']
            children = []
            for index, child in enumerate(snapshot['children']):
                member = mobject.children[index] if index < len(mobject.children) else Mobject()
                expose(member, child)
                children.append(member)
            mobject.children = children
        try:
            for mobject, states in (overrides or {}).items():
                blocked.update(mobject.get_family())
                if states:
                    # Crossfades have two visual objects; geometry queries use the
                    # more visible one. Continuous morphs have a single snapshot.
                    expose(mobject, max(states, key=lambda state:state['opacity']))
                    blocked.update(mobject.get_family())
            seen = set()
            def visit(mobject):
                if mobject in seen or mobject in blocked or mobject.updating_suspended:
                    return
                seen.add(mobject)
                mobject.update(dt, recursive=False)
                for child in list(mobject.children):
                    visit(child)
            for root in roots:
                visit(root)
        finally:
            for mobject, state in saved.items():
                mobject.__dict__ = state

    def capture(self, overrides=None, *, advance_time=True):
        if len(self.frames) >= MAX_FRAMES:
            raise ValueError('Preview exceeds 60 seconds / 900 frames. Shorten the scene.')
        objects = []
        for mobject in self.mobjects:
            if isinstance(mobject, (CameraFrame, ValueTracker)):
                continue
            objects.extend(overrides[mobject] if overrides and mobject in overrides else [mobject.to_dict()])
        if isinstance(self.camera, MovingCamera):
            states = overrides.get(self.camera.frame) if overrides else None
            if states is not None and len(states) != 1:
                raise ValueError('Camera animation must produce one frame rectangle')
            camera = self.camera.to_dict(states[0] if states else None)
        else:
            camera = self.camera.to_dict()
        self.frames.append({'mobjects': objects, 'camera': camera})
        if advance_time:
            self._elapsed_frames += 1

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
            self._update_mobjects(0 if frame == 0 else 1 / FPS, overrides)
            self.capture(overrides)
        for animation in animations:
            animation.finish(self)
        self._update_mobjects(1 / FPS, {m: [m.to_dict()] for a in animations for m in a.objects()})

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
        for frame in range(count):
            self._update_mobjects(0 if frame == 0 else 1 / FPS)
            self.capture()
        if count:
            self._update_mobjects(1 / FPS)

    def setup(self):
        pass

    def construct(self):
        pass

    def tear_down(self):
        pass

    def render(self):
        self.setup()
        self.construct()
        self.tear_down()
        self._update_mobjects(0)
        # A final state is seekable without advancing the scene clock.
        self.capture(advance_time=False)
        return {'frames': self.frames, 'fps': FPS, 'duration': (len(self.frames)-1)/FPS}


class MovingCameraScene(Scene):
    camera_class = MovingCamera


EXPORTS = ['config', 'Scene', 'MovingCameraScene', 'Mobject', 'ValueTracker', 'always_redraw', 'VMobject', 'TracedPath', 'ParametricFunction', 'FunctionGraph', 'CubicBezier', 'Circle', 'Ellipse', 'Arc', 'AnnularSector', 'Sector', 'Annulus', 'Dot', 'Square', 'Rectangle', 'RoundedRectangle', 'Line', 'Arrow',
           'Triangle', 'Polygon', 'Text', 'DecimalNumber', 'Integer', 'MathTex', 'Group', 'VGroup', 'NumberLine', 'Axes', 'NumberPlane', 'ComplexPlane', 'Create', 'Write', 'FadeIn',
           'AnimationGroup', 'LaggedStart', 'Succession', 'MoveAlongPath',
           'GrowFromCenter', 'GrowFromPoint', 'ShrinkToCenter', 'Restore', 'Indicate', 'ShowPassingFlash', 'TransformFromCopy',
           'FadeOut', 'Uncreate', 'Rotate', 'Rotating', 'Transform', 'ReplacementTransform', 'UP', 'DOWN', 'LEFT',
           'RIGHT', 'ORIGIN', 'OUT', 'IN', 'UL', 'UR', 'DL', 'DR', 'BLUE', 'BLUE_D', 'RED', 'GREEN',
           'YELLOW', 'PURPLE', 'ORANGE', 'WHITE', 'BLACK', 'GRAY', 'GREY', 'PINK',
           'linear', 'smooth', 'there_and_back', 'PI', 'TAU', 'DEGREES']


def _render_scene(source, scene_name=None):
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


def render_scene(source, scene_name=None):
    global config
    previous = config
    config = PreviewConfig()
    try:
        return _render_scene(source, scene_name)
    finally:
        config = previous
