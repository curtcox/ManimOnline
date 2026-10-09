"""Small, explicit Manim subset for SVG frame playback (not full Manim)."""
import bisect
import cmath
import copy
import inspect
import json
import math
import numbers
import operator
import random
import struct
import sys
import types

FPS = 15
MAX_FRAMES = 901  # 900 timed samples plus a final seekable state.


_REAL = numbers.Real  # Includes NumPy scalars; bool is excluded where it matters.


_PLAIN_VALUE_TYPES = frozenset((int, float, str, bool, type(None)))


def _holds_mobject(value):
    """True for mobject references (also inside lists/dicts), which frames never store."""
    kind = type(value)
    if kind in _PLAIN_VALUE_TYPES or kind.__name__ == 'Vector':
        return False
    if isinstance(value, (list, tuple)):
        # Point arrays are large; skip plain items without a call per coordinate.
        plain = _PLAIN_VALUE_TYPES
        return any(_holds_mobject(item) for item in value if type(item) not in plain)
    if isinstance(value, dict):
        return any(_holds_mobject(item) for item in value.values())
    return hasattr(value, 'get_family') and hasattr(value, 'to_dict')
_BOUNDS_WITH_HANDLES = False  # Set only while measuring width/height.


def _snapshot_copy(value):
    """Deep-copy JSON-shaped frame data much faster than copy.deepcopy (no memo bookkeeping)."""
    kind = type(value)
    if kind is dict:
        return {key: item if type(item) in _PLAIN_VALUE_TYPES else _snapshot_copy(item)
                for key, item in value.items()}
    if kind is list:
        return [item if type(item) in _PLAIN_VALUE_TYPES else _snapshot_copy(item) for item in value]
    if kind in _PLAIN_VALUE_TYPES or kind.__name__ == 'Vector':
        return value  # Immutable.
    if kind is tuple:
        return tuple(_snapshot_copy(item) for item in value)
    return copy.deepcopy(value)


def _partial_cubics(points, a, b):
    """Cubic curves covering parameters a..b (0 <= a <= b <= 1) of a flat 4-point-per-curve list."""
    count = len(points) // 4
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
    return curves, first, last


def _plain_number(value):
    # NumPy scalars become Python numbers so frames stay JSON-serializable.
    if type(value) in (int, float) or not isinstance(value, numbers.Real):
        return value
    return int(value) if isinstance(value, numbers.Integral) else float(value)


class Vector(tuple):
    def __new__(cls, values):
        if type(values) is cls:
            return values  # Immutable, so the same coordinates can be shared.
        values = list(values)
        for index, value in enumerate(values):
            kind = type(value)
            if kind is not float and kind is not int:
                values[index] = _plain_number(value)
        count = len(values)
        if count != 3:
            values = values[:3] if count > 3 else values + [0] * (3 - count)
        return tuple.__new__(cls, values)

    def __mul__(self, value):
        return Vector(x * value for x in self)

    __rmul__ = __mul__

    def __add__(self, other):
        return Vector(a + b for a, b in zip(self, Vector(other)))

    def __sub__(self, other):
        return Vector(a - b for a, b in zip(self, Vector(other)))

    def __truediv__(self, value):
        return Vector(x / value for x in self)

    def __neg__(self):
        return Vector(-x for x in self)


UP, DOWN = Vector((0, 1, 0)), Vector((0, -1, 0))
LEFT, RIGHT = Vector((-1, 0, 0)), Vector((1, 0, 0))
ORIGIN = Vector((0, 0, 0))
OUT, IN = Vector((0, 0, 1)), Vector((0, 0, -1))
UL, UR, DL, DR = UP + LEFT, UP + RIGHT, DOWN + LEFT, DOWN + RIGHT
# Manim Community's named palette (manim.utils.color.manim_colors).
_PALETTE = {
    'WHITE': '#FFFFFF', 'GRAY_A': '#DDDDDD', 'GRAY_B': '#BBBBBB', 'GRAY_C': '#888888',
    'GRAY_D': '#444444', 'GRAY_E': '#222222', 'BLACK': '#000000',
    'PURE_RED': '#FF0000', 'PURE_GREEN': '#00FF00', 'PURE_BLUE': '#0000FF',
    'PURE_CYAN': '#00FFFF', 'PURE_MAGENTA': '#FF00FF', 'PURE_YELLOW': '#FFFF00',
    'BLUE_A': '#C7E9F1', 'BLUE_B': '#9CDCEB', 'BLUE_C': '#58C4DD', 'BLUE_D': '#29ABCA', 'BLUE_E': '#236B8E',
    'TEAL_A': '#ACEAD7', 'TEAL_B': '#76DDC0', 'TEAL_C': '#5CD0B3', 'TEAL_D': '#55C1A7', 'TEAL_E': '#49A88F',
    'GREEN_A': '#C9E2AE', 'GREEN_B': '#A6CF8C', 'GREEN_C': '#83C167', 'GREEN_D': '#77B05D', 'GREEN_E': '#699C52',
    'YELLOW_A': '#FFF1B6', 'YELLOW_B': '#FFEA94', 'YELLOW_C': '#F7D96F', 'YELLOW_D': '#F4D345', 'YELLOW_E': '#E8C11C',
    'GOLD_A': '#F7C797', 'GOLD_B': '#F9B775', 'GOLD_C': '#F0AC5F', 'GOLD_D': '#E1A158', 'GOLD_E': '#C78D46',
    'RED_A': '#F7A1A3', 'RED_B': '#FF8080', 'RED_C': '#FC6255', 'RED_D': '#E65A4C', 'RED_E': '#CF5044',
    'MAROON_A': '#ECABC1', 'MAROON_B': '#EC92AB', 'MAROON_C': '#C55F73', 'MAROON_D': '#A24D61', 'MAROON_E': '#94424F',
    'PURPLE_A': '#CAA3E8', 'PURPLE_B': '#B189C6', 'PURPLE_C': '#9A72AC', 'PURPLE_D': '#715582', 'PURPLE_E': '#644172',
    'PINK': '#D147BD', 'LIGHT_PINK': '#DC75CD', 'ORANGE': '#FF862F', 'LIGHT_BROWN': '#CD853F',
    'DARK_BROWN': '#8B4513', 'GRAY_BROWN': '#736357', 'LOGO_WHITE': '#ECE7E2', 'LOGO_GREEN': '#87C2A5',
    'LOGO_BLUE': '#525893', 'LOGO_RED': '#E07A5F', 'LOGO_BLACK': '#343434'}
for _name in ('BLUE', 'TEAL', 'GREEN', 'YELLOW', 'GOLD', 'RED', 'MAROON', 'PURPLE'):
    _PALETTE[_name] = _PALETTE[_name + '_C']
_PALETTE.update(GRAY=_PALETTE['GRAY_C'], LIGHTER_GRAY=_PALETTE['GRAY_A'], LIGHT_GRAY=_PALETTE['GRAY_B'],
                DARK_GRAY=_PALETTE['GRAY_D'], DARKER_GRAY=_PALETTE['GRAY_E'], DARK_BLUE=_PALETTE['BLUE_E'])
for _name in [n for n in _PALETTE if 'GRAY' in n]:
    _PALETTE[_name.replace('GRAY', 'GREY')] = _PALETTE[_name]
globals().update(_PALETTE)
PI, TAU, DEGREES = math.pi, math.tau, math.pi / 180
SMALL_BUFF, MED_SMALL_BUFF, MED_LARGE_BUFF, LARGE_BUFF = 0.1, 0.25, 0.5, 1
DEFAULT_MOBJECT_TO_EDGE_BUFFER, DEFAULT_MOBJECT_TO_MOBJECT_BUFFER = MED_LARGE_BUFF, MED_SMALL_BUFF
DEFAULT_STROKE_WIDTH, DEFAULT_FONT_SIZE = 4, 48
DEFAULT_DOT_RADIUS, DEFAULT_SMALL_DOT_RADIUS = 0.08, 0.04
DEFAULT_ARROW_TIP_LENGTH = 0.35


def _color_rgb(color):
    if (not isinstance(color, str) or len(color) != 7 or color[0] != '#' or
            any(c not in '0123456789abcdefABCDEF' for c in color[1:])):
        raise ValueError('Colors must be six-digit hex strings such as #58C4DD')
    return [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]


def _rgb_color(rgb):
    # Community's ManimColor.to_hex truncates each channel (int(value * 255)).
    return '#' + ''.join('%02X' % int(min(1, max(0, v)) * 255 + 1e-9) for v in rgb)


def color_to_rgb(color):
    return _color_rgb(color)


def rgb_to_color(rgb):
    rgb = list(rgb)
    if len(rgb) != 3 or any(isinstance(v, bool) or not isinstance(v, _REAL) or
                            not math.isfinite(v) for v in rgb):
        raise ValueError('RGB colors need three finite components')
    if any(v > 1 for v in rgb):
        rgb = [v / 255 for v in rgb]
    return _rgb_color(rgb)


rgb_to_hex, hex_to_rgb = rgb_to_color, color_to_rgb


def interpolate_color(color1, color2, alpha):
    if isinstance(alpha, bool) or not isinstance(alpha, _REAL) or not math.isfinite(alpha):
        raise ValueError('Color interpolation alpha must be finite')
    a, b = _color_rgb(color1), _color_rgb(color2)
    return _rgb_color([x * (1 - alpha) + y * alpha for x, y in zip(a, b)])


def color_gradient(reference_colors, length_of_output):
    colors = list(reference_colors)
    if isinstance(length_of_output, bool) or not isinstance(length_of_output, numbers.Integral) or not 0 <= length_of_output <= 10000:
        raise ValueError('Gradient length must be an integer from 0 to 10000')
    if not colors:
        raise ValueError('A color gradient needs at least one color')
    rgbs = [_color_rgb(color) for color in colors]
    if length_of_output == 0:
        return []
    if len(rgbs) == 1:
        return [_rgb_color(rgbs[0])] * length_of_output
    result = []
    for i in range(length_of_output):
        # Community's linspace quirk: the final sample is always the last color.
        position = 0 if length_of_output == 1 else i * (len(rgbs) - 1) / (length_of_output - 1)
        floor, alpha = int(position), position % 1
        if i == length_of_output - 1:
            floor, alpha = len(rgbs) - 2, 1
        result.append(_rgb_color([a * (1 - alpha) + b * alpha for a, b in zip(rgbs[floor], rgbs[floor + 1])]))
    return result


def average_color(*colors):
    rgbs = [_color_rgb(color) for color in colors]
    if not rgbs:
        raise ValueError('Averaging needs at least one color')
    return _rgb_color([sum(values) / len(rgbs) for values in zip(*rgbs)])


def invert_color(color):
    return _rgb_color([1 - v for v in _color_rgb(color)])


class PreviewConfig:
    """Validated 2D preview settings; not the full Community config object."""
    def __init__(self, **kwargs):
        # Community's default frame: 8 units tall, 16:9 (14.22 units wide).
        self.pixel_width, self.pixel_height = 800, 450
        self.frame_height, self.background_color = 8, BLACK
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
            if isinstance(value, bool) or not isinstance(value, numbers.Integral) or not 1 <= value <= 4096:
                raise ValueError('Pixel dimensions must be integers from 1 to 4096')
        elif name in ('frame_width', 'frame_height'):
            if isinstance(value, bool) or not isinstance(value, _REAL) or not math.isfinite(value) or value <= 0:
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
        result = {name: getattr(self, name) for name in
                  ('pixel_width','pixel_height','frame_width','frame_height','background_color')}
        # Strokes keep Community's on-screen width relative to the configured frame,
        # even while a moving camera zooms.
        result['reference_frame_width'] = self.__dict__['frame_height'] * self.pixel_width / self.pixel_height
        return result


config = PreviewConfig()


class Mobject:
    # Subclass bookkeeping (e.g. Graph adjacency) that frames never store.
    _frame_excluded = ()

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

    def _validate_children(self, mobjects):
        if any(not isinstance(m, Mobject) for m in mobjects):
            raise TypeError('Mobject children must be Mobjects')
        if any(isinstance(member, CameraFrame) for m in mobjects for member in m.get_family()):
            raise ValueError('Camera frames cannot be children of a display family')
        if any(self in m.get_family() for m in mobjects):
            raise ValueError('A mobject cannot contain itself or create a family cycle')

    @property
    def submobjects(self):
        return self.children

    @submobjects.setter
    def submobjects(self, mobjects):
        mobjects = list(mobjects)
        self._validate_children(mobjects)
        self._replace_children(list(dict.fromkeys(mobjects)))

    def add(self, *mobjects):
        self._validate_children(mobjects)
        unique = list(dict.fromkeys(mobjects))
        self._replace_children([m for m in self.children if m not in unique] + unique)
        return self

    def add_to_back(self, *mobjects):
        self._validate_children(mobjects)
        unique = list(dict.fromkeys(mobjects))
        self._replace_children(unique + [m for m in self.children if m not in unique])
        return self

    def remove(self, *mobjects):
        if any(not isinstance(m, Mobject) for m in mobjects):
            raise TypeError('Mobject removal expects Mobjects')
        self._replace_children([m for m in self.children if m not in mobjects])
        return self

    def _replace_children(self, children):
        # Keep the affine mapping fixed when any family's bounds change.
        previous = self._geometry_center()
        self.children = children
        self.__dict__.pop('_family_pivot_cache',None)
        if previous is not None:
            delta = self._geometry_center()-previous
            transformed = Vector((delta[0]*math.cos(self.angle)-delta[1]*math.sin(self.angle),
                                  delta[0]*math.sin(self.angle)+delta[1]*math.cos(self.angle),0))*self.geometry_scale
            self.shift(transformed-delta)

    def _layout_targets(self):
        if self.geometry_scale == 0:
            raise NotImplementedError('Cannot arrange a collapsed family')
        self._geometry_center()
        targets = []
        for child in self.children:
            target = child.copy()
            pivot = target._geometry_center()
            center_point = self._point_to_world(child._pivot_point())
            target.position = list(center_point-pivot)
            target.angle += self.angle
            target.geometry_scale *= self.geometry_scale
            targets.append(target)
        return targets

    def _apply_layout_targets(self, targets):
        # Invert translations only; keep the parent pose for animated layouts.
        shifts = []
        for child,target in zip(self.children,targets):
            delta = target._pivot_point()-self._point_to_world(child._pivot_point())
            shifts.append(Vector((delta[0]*math.cos(self.angle)+delta[1]*math.sin(self.angle),
                                  -delta[0]*math.sin(self.angle)+delta[1]*math.cos(self.angle),0))*(1/self.geometry_scale))
        if any(not math.isfinite(value) for delta in shifts for value in delta):
            raise ValueError('Layout translations must be finite')
        for child,delta in zip(self.children,shifts):
            child.shift(delta)
        self._geometry_center()
        return self

    def arrange(self, direction=RIGHT, buff=0.25, center=True, aligned_edge=ORIGIN):
        direction, aligned_edge = Vector(direction), Vector(aligned_edge)
        if not all(math.isfinite(v) for v in (*direction,*aligned_edge,buff)):
            raise ValueError('Layout coordinates and buffer must be finite')
        if direction[2] or aligned_edge[2]:
            raise NotImplementedError('Layout supports only the XY plane')
        if direction == ORIGIN:
            raise ValueError('Layout direction must be nonzero')
        targets = self._layout_targets()
        for previous,current in zip(targets,targets[1:]):
            current.next_to(previous,direction,buff,aligned_edge)
        self._apply_layout_targets(targets)
        if center:
            self.move_to(ORIGIN)
        return self

    def arrange_in_grid(self, rows=None, cols=None, buff=.25, cell_alignment=ORIGIN,
                        row_alignments=None, col_alignments=None, row_heights=None,
                        col_widths=None, flow_order='rd'):
        alignment = Vector(cell_alignment)
        if not all(math.isfinite(v) for v in alignment):
            raise ValueError('Grid alignment must be finite')
        if alignment[2]:
            raise NotImplementedError('Grid layout supports only the XY plane')
        gaps = list(buff) if isinstance(buff,(list,tuple)) else [buff,buff]
        if len(gaps) != 2 or any(isinstance(v,bool) or not isinstance(v,_REAL) or not math.isfinite(v) for v in gaps):
            raise ValueError('Grid buffer needs a finite number or horizontal/vertical pair')
        if flow_order not in ('rd','dr','ld','dl','ru','ur','lu','ul'):
            raise ValueError('Grid flow_order must be rd, dr, ld, dl, ru, ur, lu or ul')
        sizes = [None if row_heights is None else list(row_heights),
                 None if col_widths is None else list(col_widths)]
        aligns = [row_alignments,col_alignments]
        dimensions = [rows,cols]
        for i,chars in enumerate(('ucd','lcr')):
            if aligns[i] is not None and (not isinstance(aligns[i],str) or any(c not in chars for c in aligns[i])):
                raise ValueError('Invalid grid row/column alignment')
            if dimensions[i] is None:
                dimensions[i] = len(aligns[i]) if aligns[i] is not None else len(sizes[i]) if sizes[i] is not None else None
            if dimensions[i] is not None and (isinstance(dimensions[i],bool) or not isinstance(dimensions[i], numbers.Integral) or not 1 <= dimensions[i] <= 1000):
                raise ValueError('Grid dimensions must be integers from 1 to 1000')
        count = len(self.children)
        rows,cols = dimensions
        if rows is None and cols is None:
            cols = max(1,math.ceil(math.sqrt(count)))
        if rows is None:
            rows = max(1,math.ceil(count/cols))
        if cols is None:
            cols = max(1,math.ceil(count/rows))
        if rows*cols < count or rows*cols > 1000:
            raise ValueError('Grid needs enough cells and at most 1000 cells')
        for size,align,num in zip(sizes,aligns,(rows,cols)):
            if size is not None and len(size) != num or align is not None and len(align) != num:
                raise ValueError('Grid row/column options must match its dimensions')
            if size is not None and any(v is not None and (isinstance(v,bool) or not isinstance(v,_REAL) or not math.isfinite(v) or v < 0) for v in size):
                raise ValueError('Grid cell sizes must be nonnegative finite numbers or None')
        targets = self._layout_targets()
        start = self.get_center()
        cells = []
        for index in range(count):
            row,col = divmod(index,cols) if flow_order[0] in 'rl' else (index%rows,index//rows)
            if 'u' in flow_order:
                row = rows-1-row
            if 'l' in flow_order:
                col = cols-1-col
            cells.append((row,col))
        heights,widths = [0.0]*rows,[0.0]*cols
        for target,(row,col) in zip(targets,cells):
            heights[row] = max(heights[row],target.get_height())
            widths[col] = max(widths[col],target.get_width())
        heights = [v if v is not None else measured for v,measured in zip(sizes[0] or [None]*rows,heights)]
        widths = [v if v is not None else measured for v,measured in zip(sizes[1] or [None]*cols,widths)]
        xs,ys = [0.0],[0.0]
        for width in widths[:-1]:
            xs.append(xs[-1]+width+gaps[0])
        for height in heights[:-1]:
            ys.append(ys[-1]-height-gaps[1])
        if any(not math.isfinite(v) for v in (*xs,*ys,*heights,*widths)):
            raise ValueError('Grid cell coordinates must be finite')
        for target,(row,col) in zip(targets,cells):
            ax = {'l':-1,'c':0,'r':1}[col_alignments[col]] if col_alignments is not None else (1 if alignment[0]>0 else -1 if alignment[0]<0 else 0)
            ay = {'u':1,'c':0,'d':-1}[row_alignments[row]] if row_alignments is not None else (1 if alignment[1]>0 else -1 if alignment[1]<0 else 0)
            point = Vector((xs[col]+widths[col]*(ax+1)/2,ys[row]-heights[row]*(1-ay)/2,0))
            target.shift(point-target._critical_point(Vector((ax,ay,0))))
        self._apply_layout_targets(targets)
        return self.move_to(start)

    def arrange_submobjects(self, *args, **kwargs):
        return self.arrange(*args, **kwargs)

    def split(self):
        return ([self] if self.has_points() else []) + list(self.children)

    def __iter__(self):
        return iter(self.split())

    def __len__(self):
        return len(self.children) + int(self.has_points())

    def __getitem__(self, value):
        members = self.split()
        if isinstance(value,slice):
            return self.get_group_class()(*members[value])
        return members[value]

    def get_group_class(self):
        return Group if self._type in ('mobject','valuetracker') else VGroup

    def family_members_with_points(self):
        return [member for member in self.get_family() if member.has_points()]

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

    def _world_container(self):
        # Pure containers pass rigid motions to their children, so children keep
        # Community's world-space coordinates instead of parent-local ones.
        return (self._type in ('vgroup', 'mobject') and self.children and self.angle == 0 and
                self.geometry_scale == 1 and not any(self.position) and
                '_sampled_geometry_center' not in self.__dict__)

    def shift(self, direction):
        if self._world_container():
            direction = Vector(direction)
            for child in self.children:
                child.shift(direction)
            self.__dict__.pop('_family_pivot_cache', None)
            return self
        self.position = list(Vector(self.position) + direction)
        return self

    def move_to(self, point, aligned_edge=ORIGIN, coor_mask=(1, 1, 1)):
        aligned_edge, mask = Vector(aligned_edge), Vector(coor_mask)
        if not all(math.isfinite(v) for v in (*aligned_edge, *mask)):
            raise ValueError('Alignment edge and coordinate mask must be finite')
        if aligned_edge[2]:
            raise NotImplementedError('Alignment supports only XY directions')
        if any(aligned_edge):
            target = (point.get_critical_point(aligned_edge) if isinstance(point, Mobject)
                      else Vector(point))
            current = self.get_critical_point(aligned_edge)
        else:
            target = point.get_center() if isinstance(point, Mobject) else Vector(point)
            current = self.get_center()
        if not all(math.isfinite(v) for v in target):
            raise ValueError('Position must be finite')
        return self.shift(Vector(a * m for a, m in zip(target - current, mask)))

    def _critical_point(self, direction):
        left, bottom, right, top = self._bounds()
        x, y, _ = direction
        return Vector((right if x > 0 else left if x < 0 else (left + right) / 2,
                       top if y > 0 else bottom if y < 0 else (bottom + top) / 2,
                       self.position[2]))

    def get_critical_point(self, direction):
        direction = Vector(direction)
        if not all(math.isfinite(value) for value in direction):
            raise ValueError('Boundary direction must be finite')
        if direction[2]:
            raise NotImplementedError('Boundary queries support only the XY plane')
        return self._critical_point(direction)

    get_edge_center = get_critical_point
    get_corner = get_critical_point

    def get_left(self):
        return self.get_critical_point(LEFT)

    def get_right(self):
        return self.get_critical_point(RIGHT)

    def get_top(self):
        return self.get_critical_point(UP)

    def get_bottom(self):
        return self.get_critical_point(DOWN)

    def _handle_bounds(self):
        # Community measures width/height over all points (handles included),
        # while centers and edges use anchors only.
        global _BOUNDS_WITH_HANDLES
        previous, _BOUNDS_WITH_HANDLES = _BOUNDS_WITH_HANDLES, True
        try:
            return self._bounds()
        finally:
            _BOUNDS_WITH_HANDLES = previous

    def get_width(self):
        left,_,right,_ = self._handle_bounds()
        return right-left

    def get_height(self):
        _,bottom,_,top = self._handle_bounds()
        return top-bottom

    @staticmethod
    def _fit_dimension(dim):
        if isinstance(dim,bool) or not isinstance(dim, numbers.Integral) or dim not in (0,1):
            raise ValueError('Size fitting dimension must be 0 (width) or 1 (height)')
        return dim

    def length_over_dim(self, dim):
        self._fit_dimension(dim)
        return self.get_width() if dim == 0 else self.get_height()

    def stretch(self, factor, dim, *, about_point=None, about_edge=None):
        NumberLine._real(factor,'Stretch factor')
        self._fit_dimension(dim)
        def function(point):
            values = list(point)
            values[dim] *= factor
            return values
        return self._apply_xy_map(function,about_point,about_edge,linear=True)

    def apply_matrix(self, matrix, *, about_point=None, about_edge=None):
        rows = [list(row) for row in matrix]
        if not rows or len(rows)>3 or not rows[0] or len(rows[0])>3 or any(len(row)!=len(rows[0]) for row in rows):
            raise ValueError('Matrix needs a rectangular block of one to three rows and columns')
        full = [[1 if i==j else 0 for j in range(3)] for i in range(3)]
        for i,row in enumerate(rows):
            for j,value in enumerate(row):
                NumberLine._real(value,'Matrix entry')
                full[i][j] = value
        if full[2][0] or full[2][1]:
            raise NotImplementedError('Matrices must preserve the XY plane')
        if about_point is None and about_edge is None:
            about_point = ORIGIN
        return self._apply_xy_map(lambda point:[sum(a*b for a,b in zip(row,point)) for row in full],
                                  about_point,about_edge,linear=True)

    def apply_function(self, function, *, about_point=None, about_edge=None):
        if not callable(function):
            raise TypeError('apply_function expects a callable point map')
        if about_point is None and about_edge is None:
            about_point = ORIGIN
        return self._apply_xy_map(function,about_point,about_edge)

    def apply_complex_function(self, function, *, about_point=None, about_edge=None):
        if not callable(function):
            raise TypeError('apply_complex_function expects a callable complex map')
        def point_map(point):
            value = complex(function(complex(point[0],point[1])))
            return (value.real,value.imag,point[2])
        return self.apply_function(point_map,about_point=about_point,about_edge=about_edge)

    def _apply_xy_map(self, function, about_point=None, about_edge=None, *, linear=False):
        if about_point is not None:
            pivot = Vector(about_point)
        else:
            edge = ORIGIN if about_edge is None else Vector(about_edge)
            pivot = self.get_critical_point(edge)
        if not all(math.isfinite(value) for value in pivot) or pivot[2]:
            raise ValueError('Point-map pivot must be finite and in the XY plane')
        if isinstance(self,CameraFrame):
            raise NotImplementedError('Camera point mapping is not implemented')
        source,target = self.copy(),self.copy()
        seen = set()
        def mapped(point):
            values = list(function(Vector(point)-pivot))
            if len(values) not in (2,3):
                raise ValueError('Point maps must return two or three coordinates')
            for value in values:
                NumberLine._real(value,'Mapped coordinate')
            result = Vector(values)+pivot
            if result[2]:
                raise NotImplementedError('Point maps must preserve the XY plane')
            if not all(math.isfinite(value) for value in result):
                raise ValueError('Mapped geometry must be finite')
            return result
        def visit(old,new,parent_world,parent_origin):
            if id(old) in seen:
                raise NotImplementedError('Mapping shared nested children is not implemented')
            seen.add(id(old))
            old._geometry_center()
            def world(point):
                return parent_world(old._point_to_world(Vector(point)))
            origin = mapped(world(ORIGIN)) if linear else world(ORIGIN)
            def local(point):
                return list(mapped(world(point))-origin)
            kind = old._type
            snapshot = old.to_dict()
            if kind in ('line','arrow') and linear:
                new.start,new.end = local(old.start),local(old.end)
            elif kind in ('polygon','polyline') and linear:
                new.vertices = [local(point) for point in old.vertices]
            elif kind in ('circle','ellipse','arc','square','rectangle','triangle','annulus','bezierpath','line','arrow','polygon','polyline'):
                paths = _path_subpaths(snapshot,include_pending=False)
                if linear:
                    new.curves = [[local(point) for point in curve] for path in paths for curve in path]
                else:
                    # Community's VMobject.apply_function pulls handles to 1% of their anchor
                    # distance, maps, then scales back: handles follow the map's local derivative.
                    def curve_map(curve):
                        a0, h1, h2, a1 = (Vector(point) for point in curve)
                        m0, m1 = local(a0), local(a1)
                        near1, near2 = local(a0 + (h1 - a0) * .01), local(a1 + (h2 - a1) * .01)
                        return [m0, [m0[i] + (near1[i] - m0[i]) * 100 for i in range(3)],
                                [m1[i] + (near2[i] - m1[i]) * 100 for i in range(3)], m1]
                    new.curves = [curve_map(curve) for path in paths for curve in path]
                pending = (old.vertices if kind == 'bezierpath' else
                           old.vertices if kind == 'polyline' and len(old.vertices)==1 else [])
                new.vertices = [local(point) for point in pending]
                new._type = 'bezierpath'
                if kind in ('line','arrow'):
                    new.start,new.end = local(old.start),local(old.end)
                new.__dict__.pop('subpath_lengths',None)
                if len(paths)>1:
                    new.subpath_lengths = [len(path) for path in paths]
                # Bake the displayed shaft before deforming its tip family. A
                # similarity refit after a nonuniform map would change the curve.
                new.__dict__.pop('_curved_tip_path',None)
            elif kind in ('text','mathtex') and linear:
                # Glyphs keep a pose plus an axis-aligned stretch in their own frame.
                axis = world(RIGHT)-world(ORIGIN)
                angle, size = math.atan2(axis[1],axis[0]), math.hypot(axis[0],axis[1])
                quarter = round(angle/(PI/2))
                columns = [mapped(pivot+direction)-mapped(pivot) for direction in (RIGHT,UP)]
                if abs(angle-quarter*PI/2) > 1e-9 or abs(columns[0][1]) > 1e-12 or abs(columns[1][0]) > 1e-12:
                    raise NotImplementedError('Text and formulas support axis-aligned stretching only')
                sx, sy = old.__dict__.get('glyph_stretch', (1, 1))
                mx, my = (columns[0][0], columns[1][1]) if quarter % 2 == 0 else (columns[1][1], columns[0][0])
                new.glyph_stretch = [sx*mx, sy*my]
                new.position,new.angle,new.geometry_scale = list(origin-parent_origin),quarter*PI/2,size
                for key in ('_family_pivot_cache','_sampled_geometry_center'):
                    new.__dict__.pop(key,None)
                for old_child,new_child in zip(old.children,new.children):
                    visit(old_child,new_child,world,origin)
                return
            elif kind not in ('vgroup','mobject','valuetracker'):
                raise NotImplementedError('Point mapping requires editable vector geometry')
            if '_curve_arc_center' in old.__dict__:
                new._curve_arc_center = (local(old._curve_arc_center) if linear else
                                         list(world(old._curve_arc_center)-origin))
            new.position,new.angle,new.geometry_scale = list(origin-parent_origin),0,1
            new._stretch_baked = True
            for key in ('_family_pivot_cache','_sampled_geometry_center','shaft_curves','shaft_start','shaft_end'):
                new.__dict__.pop(key,None)
            for old_child,new_child in zip(old.children,new.children):
                visit(old_child,new_child,world,origin)
        visit(source,target,lambda point:point,ORIGIN)
        return self.become(target)

    def stretch_to_fit_width(self, width, **kwargs):
        return self.rescale_to_fit(width,0,stretch=True,**kwargs)

    def stretch_to_fit_height(self, height, **kwargs):
        return self.rescale_to_fit(height,1,stretch=True,**kwargs)

    def rescale_to_fit(self, length, dim, stretch=False, **kwargs):
        NumberLine._real(length,'Fitted length',nonnegative=True)
        self._fit_dimension(dim)
        if not isinstance(stretch,bool):
            raise ValueError('stretch must be a boolean')
        old_length = self.length_over_dim(dim)
        if not math.isfinite(old_length):
            raise ValueError('Existing length must be finite')
        if old_length == 0:
            return self
        if stretch:
            target = self.copy().stretch(1,dim)
            old_length = target.length_over_dim(dim)
            if old_length == 0:
                return self
            factor = length/old_length
            if not math.isfinite(factor):
                raise ValueError('Fitted scale must be finite')
            target.stretch(factor,dim,**kwargs)
            return self.become(target)
        factor = length/old_length
        if not math.isfinite(factor):
            raise ValueError('Fitted scale must be finite')
        return self.scale(factor,**kwargs)

    def scale_to_fit_width(self, width, **kwargs):
        return self.rescale_to_fit(width,0,**kwargs)

    def scale_to_fit_height(self, height, **kwargs):
        return self.rescale_to_fit(height,1,**kwargs)

    def replace(self, mobject, dim_to_match=0, stretch=False):
        if not isinstance(mobject,Mobject):
            raise TypeError('replace expects a Mobject')
        if not mobject.get_num_points() and not mobject.children and mobject._type not in ('text', 'mathtex'):
            raise ValueError('Cannot fit to a mobject with no points or children')
        length = mobject.length_over_dim(dim_to_match)
        center = mobject.get_center()
        if not all(math.isfinite(value) for value in center):
            raise ValueError('Fit center must be finite')
        if not isinstance(stretch,bool):
            raise ValueError('stretch must be a boolean')
        if stretch:
            width,height = mobject.get_width(),mobject.get_height()
            target = self.copy().stretch_to_fit_width(width).stretch_to_fit_height(height).move_to(center)
            return self.become(target)
        return self.rescale_to_fit(length,dim_to_match).move_to(center)

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

    @staticmethod
    def _xy_vector(value, name):
        value = Vector(value)
        if not all(isinstance(v, _REAL) and not isinstance(v, bool) and math.isfinite(v) for v in value):
            raise ValueError(name + ' must be finite')
        if value[2]:
            raise NotImplementedError(name + ' supports only the XY plane')
        return value

    def align_on_border(self, direction, buff=DEFAULT_MOBJECT_TO_EDGE_BUFFER):
        direction = self._xy_vector(direction, 'Border direction')
        NumberLine._real(buff, 'Border buffer')
        sign = [(v > 0) - (v < 0) for v in direction]
        target = Vector((sign[0] * config.frame_width / 2, sign[1] * config.frame_height / 2, 0))
        offset = target - self.get_critical_point(direction) - direction * buff
        return self.shift(Vector((offset[0] * abs(sign[0]), offset[1] * abs(sign[1]), 0)))

    def to_edge(self, edge=LEFT, buff=DEFAULT_MOBJECT_TO_EDGE_BUFFER):
        return self.align_on_border(edge, buff)

    def to_corner(self, corner=DL, buff=DEFAULT_MOBJECT_TO_EDGE_BUFFER):
        return self.align_on_border(corner, buff)

    def center(self):
        return self.shift(Vector(ORIGIN) - self.get_center())

    @staticmethod
    def _coordinate_dim(dim):
        if isinstance(dim, bool) or not isinstance(dim, numbers.Integral) or dim not in (0, 1, 2):
            raise ValueError('Coordinate dimension must be 0, 1 or 2')
        return dim

    def get_coord(self, dim, direction=ORIGIN):
        self._coordinate_dim(dim)
        direction = self._xy_vector(direction, 'Coordinate direction')
        return self.get_critical_point(direction)[dim]

    def get_x(self, direction=ORIGIN):
        return self.get_coord(0, direction)

    def get_y(self, direction=ORIGIN):
        return self.get_coord(1, direction)

    def get_z(self, direction=ORIGIN):
        return self.get_coord(2, direction)

    def set_coord(self, value, dim, direction=ORIGIN):
        NumberLine._real(value, 'Coordinate')
        if self._coordinate_dim(dim) == 2:
            if value != self.get_coord(2, direction):
                raise NotImplementedError('Preview objects stay in the XY plane')
            return self
        offset = [0, 0, 0]
        offset[dim] = value - self.get_coord(dim, direction)
        return self.shift(Vector(offset))

    def set_x(self, x, direction=ORIGIN):
        return self.set_coord(x, 0, direction)

    def set_y(self, y, direction=ORIGIN):
        return self.set_coord(y, 1, direction)

    def set_z(self, z, direction=ORIGIN):
        return self.set_coord(z, 2, direction)

    def align_to(self, mobject_or_point, direction=ORIGIN):
        direction = self._xy_vector(direction, 'Alignment direction')
        point = (mobject_or_point.get_critical_point(direction) if isinstance(mobject_or_point, Mobject)
                 else self._xy_vector(mobject_or_point, 'Alignment point'))
        offset = [point[dim] - self.get_coord(dim, direction) if direction[dim] else 0 for dim in (0, 1)]
        return self.shift(Vector(offset))

    def match_dim_size(self, mobject, dim, **kwargs):
        if not isinstance(mobject, Mobject):
            raise TypeError('Size matching expects a Mobject')
        return self.rescale_to_fit(mobject.length_over_dim(dim), dim, **kwargs)

    def match_width(self, mobject, **kwargs):
        return self.match_dim_size(mobject, 0, **kwargs)

    def match_height(self, mobject, **kwargs):
        return self.match_dim_size(mobject, 1, **kwargs)

    def match_coord(self, mobject, dim, direction=ORIGIN):
        if not isinstance(mobject, Mobject):
            raise TypeError('Coordinate matching expects a Mobject')
        return self.set_coord(mobject.get_coord(dim, direction), dim, direction)

    def match_x(self, mobject, direction=ORIGIN):
        return self.match_coord(mobject, 0, direction)

    def match_y(self, mobject, direction=ORIGIN):
        return self.match_coord(mobject, 1, direction)

    def match_z(self, mobject, direction=ORIGIN):
        return self.match_coord(mobject, 2, direction)

    def flip(self, axis=UP, *, about_point=None, about_edge=None):
        return self.rotate(TAU / 2, axis, about_point=about_point, about_edge=about_edge)

    def _pivot(self, about_point, about_edge):
        if about_point is not None and about_edge is not None:
            raise ValueError('Pass about_point or about_edge, not both')
        if about_edge is not None:
            return self.get_critical_point(self._xy_vector(about_edge, 'Pivot edge'))
        return None if about_point is None else self._xy_vector(about_point, 'Pivot point')

    def _own_local_bounds(self):
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
        if self._type in ('rectangle', 'ellipse', 'image'):
            return (-self.width / 2, -self.height / 2, self.width / 2, self.height / 2)
        if self._type in ('line', 'arrow'):
            points = [self.start, self.end]
        elif self._type in ('polygon', 'polyline'):
            points = self.vertices
        elif self._type == 'bezierpath':
            # Community edges use anchors (get_points_defining_boundary); sizes include handles.
            points = ([point for curve in self.curves for point in curve] if _BOUNDS_WITH_HANDLES else
                      [point for curve in self.curves for point in (curve[0], curve[-1])]) + getattr(self, 'vertices', [])
        elif self._type == 'triangle':
            height = math.sqrt(3) / 2
            points = [(0, height * 2 / 3), (-0.5, -height / 3), (0.5, -height / 3)]
        elif self._type in ('text', 'mathtex'):
            # Text is centered on its estimated (Text) or measured (MathTex) ink box.
            if self._type == 'mathtex' and 'part' in self.__dict__:
                width, height = _math_parts(self.text, self.part_strings, self.font_size)[self.part][2:]
            else:
                width, height = (_math_box(self.text, self.font_size) if self._type == 'mathtex' else
                                 _text_extent(self.__dict__))
            sx, sy = self.__dict__.get('glyph_stretch', (1, 1))
            width, height = width * abs(sx), height * abs(sy)
            return (-width / 2, -height / 2, width / 2, height / 2)
        else:
            return (0, 0, 0, 0)
        if not points:
            return (0, 0, 0, 0)
        return (min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points))

    def _is_pointless(self):
        """Community leaves members without points (empty text or groups) out of bounds."""
        if self._type in ('mobject', 'vgroup', 'valuetracker'):
            return all(child._is_pointless() for child in self.children)
        if self._type == 'text' and not self.children:
            return not self.text.strip()
        return False

    def _local_bounds(self):
        if not self.children:
            return self._own_local_bounds()
        bounds = [child._bounds() for child in self.children if not child._is_pointless()]
        if not bounds:
            return self._own_local_bounds()
        has_outline = self._type not in ('mobject','vgroup','valuetracker')
        if self._type in ('polyline','polygon') and not self.vertices:
            has_outline = False
        if self._type == 'bezierpath' and not self.curves and not self.vertices:
            has_outline = False
        if has_outline:
            bounds.append(self._own_local_bounds())
        return (min(b[0] for b in bounds),min(b[1] for b in bounds),
                max(b[2] for b in bounds),max(b[3] for b in bounds))

    def _geometry_center(self):
        if '_sampled_geometry_center' in self.__dict__:
            return Vector(self._sampled_geometry_center)
        # Pivots always use anchor bounds, even while measuring width/height.
        global _BOUNDS_WITH_HANDLES
        flag, _BOUNDS_WITH_HANDLES = _BOUNDS_WITH_HANDLES, False
        try:
            return self._anchor_center()
        finally:
            _BOUNDS_WITH_HANDLES = flag

    def _anchor_center(self):
        left, bottom, right, top = self._local_bounds()
        center = Vector(((left + right) / 2, (bottom + top) / 2, 0))
        if self.children:
            own = self._own_local_bounds()
            child_bounds = tuple(child._bounds() for child in self.children)
            previous = self.__dict__.get('_family_pivot_cache')
            if previous is not None and previous[0] == own and previous[1] != child_bounds:
                delta = center-Vector(previous[2])
                transformed = Vector((delta[0]*math.cos(self.angle)-delta[1]*math.sin(self.angle),
                                      delta[0]*math.sin(self.angle)+delta[1]*math.cos(self.angle),0))*self.geometry_scale
                self.shift(transformed-delta)
            self._family_pivot_cache = (own,child_bounds,list(center))
        else:
            self.__dict__.pop('_family_pivot_cache',None)
        return center

    def _pivot_point(self):
        """World position of the internal transform pivot (local bounds center)."""
        return Vector(self.position) + self._geometry_center()

    def get_center(self):
        # Community's center is the bounds center; it differs from the pivot only
        # for rotated point-based outlines, whose bounds use rotated points.
        if (math.sin(2 * self.angle) and not self.children and
                (self._own_bound_points() or self._type in ('arc', 'ellipse'))) or (self.children and self._rotated_family()):
            left, bottom, right, top = self._bounds()
            return Vector(((left + right) / 2, (bottom + top) / 2, self.position[2]))
        return self._pivot_point()

    def get_points(self):
        """Independent world-space anchors/handles for supported XY outlines."""
        if self._type not in ('polyline', 'polygon', 'bezierpath', 'circle', 'arc', 'ellipse',
                              'square', 'rectangle', 'triangle', 'line', 'arrow', 'annulus'):
            return []
        if self._type == 'polyline' and len(self.vertices) == 1:
            points = self.vertices
        else:
            points = [point for curve in _path_curves(self.to_dict()) for point in curve]
            if self._type == 'bezierpath':
                points += self.vertices
        return [list(self._point_to_world(Vector(point))) for point in points]

    def get_arc_length(self, sample_points_per_curve=10):
        lengths,_ = _curve_length_data(self,sample_points_per_curve)
        return lengths[-1]

    def get_num_points(self):
        return len(self.get_points())

    def has_points(self):
        return self.get_num_points() > 0

    def has_no_points(self):
        return not self.has_points()

    def get_cubic_bezier_tuples(self):
        points = self.get_points()
        return [tuple(Vector(p) for p in points[i:i + 4]) for i in range(0, len(points) - len(points) % 4, 4)]

    def get_start_anchors(self):
        return [curve[0] for curve in self.get_cubic_bezier_tuples()]

    def get_end_anchors(self):
        return [curve[3] for curve in self.get_cubic_bezier_tuples()]

    def get_anchors(self):
        return [point for curve in self.get_cubic_bezier_tuples() for point in (curve[0], curve[3])]

    def get_boundary_point(self, direction):
        """Community's family anchor farthest along direction (first one on ties)."""
        direction = Vector(direction)
        points = [p for member in self.get_family() for p in
                  (member.get_anchors() or [Vector(q) for q in member.get_points()])]
        if not points:
            return self.get_center()
        return max(points, key=lambda p: p[0] * direction[0] + p[1] * direction[1] + p[2] * direction[2])

    def get_center_of_mass(self):
        points = [Vector(p) for member in self.get_family() for p in member.get_points()]
        if not points:
            return self.get_center()
        return Vector(sum(p[i] for p in points) / len(points) for i in range(3))

    def set(self, **kwargs):
        """Community's set(attr=value): sizes and styles use their setters, others are stored."""
        setters = {'width': self.scale_to_fit_width, 'height': self.scale_to_fit_height,
                   'color': self.set_color, 'opacity': self.set_opacity, 'z_index': self.set_z_index,
                   'fill_color': lambda v: self.set_fill(color=v), 'fill_opacity': lambda v: self.set_fill(opacity=v),
                   'stroke_color': lambda v: self.set_stroke(color=v), 'stroke_width': lambda v: self.set_stroke(width=v),
                   'stroke_opacity': lambda v: self.set_stroke(opacity=v)}
        for name, value in kwargs.items():
            if name in setters:
                setters[name](value)
            else:
                setattr(self, name, value)
        return self

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
        if any(isinstance(v,bool) or not isinstance(v,_REAL) or not math.isfinite(v)
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
        if not len(points) // 4:
            return self
        curves, first, last = _partial_cubics(points, a, b)
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
        if (isinstance(a,_REAL) and isinstance(b,_REAL) and
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

    def _own_bound_points(self):
        """Local points that define a point-based outline's bounds, or None."""
        if self._type in ('polygon', 'polyline'):
            return self.vertices
        if self._type in ('line', 'arrow'):
            return [self.start, self.end]
        if self._type == 'bezierpath':
            return ([p for curve in self.curves for p in curve] if _BOUNDS_WITH_HANDLES else
                    [p for curve in self.curves for p in (curve[0], curve[-1])]) + getattr(self, 'vertices', [])
        if self._type in ('square', 'rectangle', 'triangle'):
            return [curve[0] for curve in _path_curves(self.to_dict() if self._type == 'triangle' else
                    {'type': self._type, 'side_length': getattr(self, 'side_length', 0),
                     'width': getattr(self, 'width', 0), 'height': getattr(self, 'height', 0)})]
        return None

    def _rotated_family(self):
        return any(math.sin(2 * member.angle) for member in self.get_family())

    def _family_bound_points(self):
        """Bounds-defining points of this family in its parent's coordinates."""
        own = self._own_bound_points()
        if own is None:
            if self._type in ('circle', 'arc', 'ellipse', 'annulus'):
                curves = _path_curves({key: value for key, value in self.__dict__.items()
                                       if key in ('radius', 'start_angle', 'arc_angle', 'width', 'height',
                                                  'inner_radius', 'outer_radius')} | {'type': self._type})
                own = ([p for c in curves for p in c] if _BOUNDS_WITH_HANDLES else
                       [p for c in curves for p in (c[0], c[-1])])
            elif self._type in ('text', 'mathtex'):
                l, b, r, t = self._own_local_bounds()
                own = [(l, b), (l, t), (r, b), (r, t)]
            else:
                own = []
        local = [Vector(p) for p in own]
        for child in self.children:
            local.extend(child._family_bound_points())
        return [self._point_to_world(p) for p in local]

    def _bounds(self):
        if self.children and self._rotated_family():
            # Rotated families: bound their transformed points, as Community does.
            points = self._family_bound_points()
            if points:
                return (min(p[0] for p in points), min(p[1] for p in points),
                        max(p[0] for p in points), max(p[1] for p in points))
        left, bottom, right, top = self._local_bounds()
        center = self._geometry_center()
        own = None
        if math.sin(2 * self.angle) and not self.children:
            own = self._own_bound_points()
            if own is None and self._type in ('arc', 'ellipse'):
                own = self._family_bound_points()
                return (min(p[0] for p in own), min(p[1] for p in own),
                        max(p[0] for p in own), max(p[1] for p in own))
        if own:
            # Rotated outlines: bound the rotated points, as Community does.
            c, s_ = math.cos(self.angle), math.sin(self.angle)
            moved = [(self.position[0] + center[0] + ((p[0] - center[0]) * c - (p[1] - center[1]) * s_) * self.geometry_scale,
                      self.position[1] + center[1] + ((p[0] - center[0]) * s_ + (p[1] - center[1]) * c) * self.geometry_scale)
                     for p in own]
            return (min(p[0] for p in moved), min(p[1] for p in moved),
                    max(p[0] for p in moved), max(p[1] for p in moved))
        points = []
        for x, y in ((left, bottom), (left, top), (right, bottom), (right, top)):
            dx, dy = (x - center[0]) * self.geometry_scale, (y - center[1]) * self.geometry_scale
            points.append((self.position[0] + center[0] + dx * math.cos(self.angle) - dy * math.sin(self.angle),
                           self.position[1] + center[1] + dx * math.sin(self.angle) + dy * math.cos(self.angle)))
        if self._type == 'ellipse' and not self.children:
            rx, ry = self.width / 2, self.height / 2
            dx = abs(self.geometry_scale) * math.hypot(rx * math.cos(self.angle), ry * math.sin(self.angle))
            dy = abs(self.geometry_scale) * math.hypot(rx * math.sin(self.angle), ry * math.cos(self.angle))
            return (self.position[0] - dx, self.position[1] - dy,
                    self.position[0] + dx, self.position[1] + dy)
        if self._type in ('circle', 'annulus') and not self.children:
            radius = max(self.inner_radius, self.outer_radius) if self._type == 'annulus' else self.radius
            r = abs(radius * self.geometry_scale)
            return (self.position[0] - r, self.position[1] - r, self.position[0] + r, self.position[1] + r)
        return (min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points))

    def scale(self, scale_factor, *, about_point=None, about_edge=None):
        if not math.isfinite(scale_factor):
            raise ValueError('Scale factor must be finite')
        about_point = self._pivot(about_point, about_edge)
        if self._world_container():
            pivot = self.get_center() if about_point is None else Vector(about_point)
            for child in self.children:
                Mobject.scale(child, scale_factor, about_point=pivot)
            self.__dict__.pop('_family_pivot_cache', None)
            return self
        self._geometry_center()
        if about_point is None and self.get_center() != self._pivot_point():
            about_point = self.get_center()  # Community scales about the bounds center.
        if about_point is not None:
            pivot = Vector(about_point)
            center = self._pivot_point()
            self.shift((center - pivot) * (scale_factor - 1))
        self.geometry_scale *= scale_factor
        return self

    def rotate(self, angle, axis=OUT, *, about_point=None, about_edge=None):
        if not math.isfinite(angle):
            raise ValueError('Rotation angle must be finite')
        axis = Vector(axis)
        if not all(math.isfinite(v) for v in axis) or not any(axis):
            raise ValueError('Rotation axis must be finite and nonzero')
        about_point = self._pivot(about_point, about_edge)
        if not axis[0] and not axis[1]:
            angle = angle if axis[2] > 0 else -angle
        elif not axis[2] and abs(math.sin(angle)) < 1e-12 and math.cos(angle) < 0:
            # A half turn about an in-plane axis is the XY reflection across it.
            length = math.hypot(axis[0], axis[1])
            ux, uy = axis[0] / length, axis[1] / length
            return self.apply_matrix([[2*ux*ux-1, 2*ux*uy], [2*ux*uy, 2*uy*uy-1]],
                                     about_point=self.get_center() if about_point is None else about_point)
        elif angle % TAU:
            raise NotImplementedError('Only rotations about OUT/IN or in-plane half turns are supported')
        else:
            return self
        self._geometry_center()
        if about_point is None and self.get_center() != self._pivot_point():
            about_point = self.get_center()  # Community rotates about the bounds center.
        if about_point is not None:
            pivot = Vector(about_point)
            center = self._pivot_point()
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
        if not isinstance(z_index_value, _REAL) or not math.isfinite(z_index_value):
            raise ValueError('z_index must be a finite number')
        self.z_index = z_index_value
        if family:
            for child in self.children:
                child.set_z_index(z_index_value, family=True)
        return self

    def set_style(self, fill_color=None, fill_opacity=None, stroke_color=None, stroke_width=None,
                  stroke_opacity=None, family=True, **kwargs):
        unsupported = [key for key in kwargs if not key.startswith('background_stroke') and key not in ('sheen_factor', 'sheen_direction')]
        if unsupported:
            raise NotImplementedError('Unsupported style options: ' + ', '.join(unsupported))
        self.set_fill(fill_color, fill_opacity, family=family)
        return self.set_stroke(stroke_color, stroke_width, stroke_opacity, family=family)

    def get_color(self):
        return self.color

    def get_fill_color(self):
        return self.fill_color

    def get_stroke_color(self):
        return self.stroke_color

    def get_fill_opacity(self):
        return self.fill_opacity

    def get_stroke_opacity(self):
        return self.stroke_opacity

    def get_stroke_width(self):
        return self.stroke_width

    def match_color(self, mobject):
        if not isinstance(mobject, Mobject):
            raise TypeError('Color matching expects a Mobject')
        return self.set_color(mobject.get_color())

    def match_style(self, mobject, family=True):
        if not isinstance(mobject, Mobject):
            raise TypeError('Style matching expects a Mobject')
        self.color = mobject.color
        self.set_fill(mobject.fill_color, mobject.fill_opacity, family=False)
        self.set_stroke(mobject.stroke_color, mobject.stroke_width, mobject.stroke_opacity, family=False)
        if family:
            # Community pairs children by position after aligning family sizes;
            # here unmatched children keep their style.
            for child, source in zip(self.children, mobject.children):
                child.match_style(source)
        return self

    def _painted_members(self):
        return [m for m in self.get_family() if m.has_points() or m._type in ('text', 'mathtex')]

    def set_color_by_gradient(self, *colors):
        if not colors:
            raise ValueError('Need at least one color')
        if len(colors) == 1:
            return self.set_color(colors[0])
        members = self._painted_members()
        for member, color in zip(members, color_gradient(colors, len(members))):
            member.set_color(color, family=False)
        return self

    set_submobject_colors_by_gradient = set_color_by_gradient

    def set_colors_by_radial_gradient(self, center=None, radius=1, inner_color=WHITE, outer_color=BLACK):
        NumberLine._real(radius, 'Gradient radius', positive=True)
        center = self.get_center() if center is None else self._xy_vector(center, 'Gradient center')
        _color_rgb(inner_color), _color_rgb(outer_color)
        for member in self._painted_members():
            offset = member.get_center() - center
            t = min(math.hypot(offset[0], offset[1]) / radius, 1)
            member.set_color(interpolate_color(inner_color, outer_color, t), family=False)
        return self

    set_submobject_colors_by_radial_gradient = set_colors_by_radial_gradient

    def fade(self, darkness=0.5, family=True):
        NumberLine._real(darkness, 'Fade darkness')
        if not 0 <= darkness <= 1:
            raise ValueError('Fade darkness must be between 0 and 1')
        for member in (self.get_family() if family else [self]):
            member.fill_opacity *= 1 - darkness
            member.stroke_opacity *= 1 - darkness
        return self

    def fade_to(self, color, alpha, family=True):
        _color_rgb(color)
        painted = self._painted_members()
        for member in (self.get_family() if family else [self]):
            if member in painted:
                member.set_color(interpolate_color(member.get_color(), color, alpha), family=False)
        return self

    def sort(self, point_to_num_func=lambda point: point[0], submob_func=None):
        key = submob_func or (lambda mobject: point_to_num_func(mobject.get_center()))
        self.children = sorted(self.children, key=key)
        return self

    def invert(self, recursive=False):
        if recursive:
            for child in self.children:
                child.invert(True)
        self.children = self.children[::-1]
        return self

    def _to_local_pose(self, mobject):
        """Re-pose a world-placed mobject so that, as a child, it keeps its world geometry."""
        if self.angle == 0 and self.geometry_scale == 1 and not any(self.position):
            return mobject
        if not self.geometry_scale:
            raise NotImplementedError('Cannot attach world geometry to a collapsed parent')
        center = self._geometry_center()
        offset = mobject._pivot_point() - Vector(self.position) - center
        c, s = math.cos(-self.angle), math.sin(-self.angle)
        local = center + Vector((offset[0]*c - offset[1]*s, offset[0]*s + offset[1]*c, 0)) * (1 / self.geometry_scale)
        mobject.rotate(-self.angle).scale(1 / self.geometry_scale)
        return mobject.shift(local - mobject._pivot_point())

    def generate_target(self, use_deepcopy=False):
        self.target = None  # Do not copy an earlier target into the new one.
        self.target = self.copy()
        return self.target

    def add_background_rectangle(self, color=None, opacity=0.75, **kwargs):
        rectangle = BackgroundRectangle(self, color=color, fill_opacity=opacity, **kwargs)
        self.background_rectangle = self._to_local_pose(rectangle)
        return self.add_to_back(rectangle)

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
            # References to replaced descendants (e.g. Graph.vertices) resolve to the
            # retained live members rather than the target's copies.
            state = copy.deepcopy({key:value for key,value in replacement.__dict__.items()
                                   if key not in ('children','updaters','updating_suspended','_saved_state','_sampled_geometry_center')},
                                  dict(replacements))
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
        center = self._geometry_center()
        result = _snapshot_copy({key: value for key, value in self.__dict__.items()
                                if not _holds_mobject(value) and not callable(value) and
                                key not in ('_saved_state', 'children', 'updaters', 'updating_suspended', '_sampled_geometry_center', 'traced_point_func', '_parametric_function', 'underlying_function', '_coordinate_labels', '_angle_lines', '_family_pivot_cache', '_flow_points') and
                                key not in self._frame_excluded})
        result['type'] = result.pop('_type')
        result['geometry_center'] = list(center)
        result['children'] = [child.to_dict() for child in self.children]
        return _refresh_tip_shafts(result)


class ValueTracker(Mobject):
    """An invisible finite real parameter, encoded in its x coordinate."""
    def __init__(self, value=0, **kwargs):
        super().__init__(**kwargs)
        self._type = 'valuetracker'
        self.set_value(value)

    def get_value(self):
        return self.position[0]

    def set_value(self, value):
        if not isinstance(value, _REAL) or not math.isfinite(value):
            raise ValueError('ValueTracker requires a finite real number')
        # Community stores tracker values in a float point array.
        self.position[0] = float(value)
        return self

    def increment_value(self, d_value):
        if not isinstance(d_value, _REAL):
            raise ValueError('ValueTracker increments must be real numbers')
        return self.set_value(self.get_value() + d_value)

    def __bool__(self):
        return bool(self.get_value())


def _tracker_arithmetic(operation, inplace=False):
    def calculate(self, value):
        if not isinstance(value, _REAL):
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


def always(method, *args, **kwargs):
    mobject = getattr(method, '__self__', None)
    if not isinstance(mobject, Mobject):
        raise TypeError('always expects a method bound to a Mobject')
    function = method.__func__
    mobject.add_updater(lambda m: function(m, *args, **kwargs))
    return mobject


def f_always(method, *arg_generators, **kwargs):
    mobject = getattr(method, '__self__', None)
    if not isinstance(mobject, Mobject) or not all(callable(g) for g in arg_generators):
        raise TypeError('f_always expects a bound Mobject method and callables')
    function = method.__func__
    mobject.add_updater(lambda m: function(m, *(g() for g in arg_generators), **kwargs))
    return mobject


def always_shift(mobject, direction=RIGHT, rate=0.1):
    direction = Mobject._xy_vector(direction, 'Shift direction')
    length = math.hypot(direction[0], direction[1])
    unit = direction * (1 / length) if length else direction
    NumberLine._real(rate, 'Shift rate')
    mobject.add_updater(lambda m, dt: m.shift(unit * (dt * rate)))
    return mobject


def always_rotate(mobject, rate=20 * DEGREES, **kwargs):
    NumberLine._real(rate, 'Rotation rate')
    mobject.add_updater(lambda m, dt: m.rotate(dt * rate, **kwargs))
    return mobject


class VMobject(Mobject):
    """XY paths made of straight or cubic segments, with separate contours."""
    def __init__(self, **kwargs):
        kwargs.setdefault('stroke_width', 4)
        super().__init__(**kwargs)
        self._type, self.vertices = 'polyline', []

    def get_direction(self):
        """Community's shoelace orientation of the start anchors: 'CW' or 'CCW'."""
        anchors = self.get_start_anchors()
        area = sum((b[0] - a[0]) * (b[1] + a[1]) / 2 for a, b in zip(anchors, anchors[1:]))
        return 'CW' if area > 0 else 'CCW'

    def force_direction(self, target_direction):
        if target_direction not in ('CW', 'CCW'):
            raise ValueError('Invalid input for force_direction. Use "CW" or "CCW"')
        if self.get_direction() != target_direction:
            self.reverse_direction()
        return self

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
        return (bool(self.vertices) if self._type == 'bezierpath' else
                self._type == 'polyline' and len(self.vertices) == 1)

    def get_subpaths(self):
        return [[self._point_to_world(Vector(point)) for curve in path for point in curve]
                for path in _path_subpaths(self.to_dict(), include_pending=False)]

    def close_path(self):
        paths = _path_subpaths(self.to_dict())
        if paths and (self.has_new_path_started() or paths[-1][-1][-1] != paths[-1][0][0]):
            self.add_line_to(paths[-1][0][0])
        return self

    def _materialize_path(self):
        # Analytical/closed outlines continue from Community's stored points.
        if self._type not in ('polyline', 'bezierpath'):
            VMobject.set_points(self, self.get_points())
        return self

    def add_points_as_corners(self, points):
        vertices = self._corners(points)
        if vertices:
            self._materialize_path()
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
        self._materialize_path()
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
        self._materialize_path()
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
        if self._type not in ('bezierpath', 'polyline'):
            return Mobject.get_start(self)
        if self._type == 'bezierpath':
            if not self.curves and not self.vertices:
                raise ValueError('The path has no points')
            return self._point_to_world(Vector(self.curves[0][0] if self.curves else self.vertices[0]))
        if not self.vertices:
            raise ValueError('The path has no points')
        return self._point_to_world(Vector(self.vertices[0]))

    def get_end(self):
        if self._type not in ('bezierpath', 'polyline'):
            return Mobject.get_end(self)
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


def _curve_length_data(mobject, samples):
    if isinstance(samples,bool) or not isinstance(samples, numbers.Integral) or not 2 <= samples <= 1000:
        raise ValueError('Curve length samples must be an integer from 2 to 1000')
    points = mobject.get_points()
    count = len(points)//4
    if count*(samples-1) > 200000:
        raise ValueError('Curve length lookup supports at most 200000 segments')
    lengths,parameters = [0.0],[0.0]
    total = 0.0
    for index in range(count):
        curve = points[index*4:index*4+4]
        previous = Vector(curve[0])
        constant = all(point == curve[0] for point in curve[1:])
        for step in range(1,samples):
            alpha = step/(samples-1)
            point = previous if constant else VMobject._bezier_point(curve,alpha)
            total += math.dist(previous,point)
            if not math.isfinite(total):
                raise ValueError('Curve arc length must be finite')
            lengths.append(total)
            parameters.append((index+alpha)/count)
            previous = point
    return lengths,parameters


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
                (not isinstance(dissipating_time, _REAL) or
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


class TipableVMobject(VMobject):
    """Shared XY path-tip geometry, factories and family management."""
    def __init__(self, tip_length=.35, tip_style=None, normal_vector=OUT, **kwargs):
        ArrowTip._tip_dimension(tip_length,'length')
        if tip_style is not None and not isinstance(tip_style,dict):
            raise TypeError('tip_style must be a dictionary')
        normal = Vector(normal_vector)
        if not all(math.isfinite(value) for value in normal):
            raise ValueError('Tip normal must be finite')
        if normal[0] or normal[1] or not normal[2]:
            raise NotImplementedError('Tip paths support only the XY plane')
        super().__init__(**kwargs)
        self.tip_length = tip_length
        self.tip_style = copy.deepcopy(tip_style or {})
        self.normal_vector = list(normal)

    def _tip(self, at_start=False):
        role = 'start' if at_start else 'end'
        return next((child for child in self.children if child.__dict__.get('_tip_role') == role),None)

    @property
    def tip(self):
        tip = self._tip()
        if tip is None:
            raise ValueError('The path has no end tip')
        return tip

    @property
    def start_tip(self):
        tip = self._tip(True)
        if tip is None:
            raise ValueError('The path has no start tip')
        return tip

    def has_tip(self):
        return self._tip() is not None

    def has_start_tip(self):
        return self._tip(True) is not None

    def get_tip(self):
        tip = self._tip()
        if tip is None:
            tip = self._tip(True)
        if tip is None:
            raise ValueError('The path has no tip')
        return tip

    def get_tips(self):
        return VGroup(*(tip for tip in (self._tip(),self._tip(True)) if tip is not None))

    def get_default_tip_length(self):
        return getattr(self,'tip_length',.35)

    def _orient_tip(self, tip, at_start):
        curves = self._raw_curves()
        if not curves:
            raise ValueError('The curve has no completed segments')
        curve = curves[0] if at_start else curves[-1]
        anchor = Vector(curve[0] if at_start else curve[-1])
        handle = Vector(curve[1] if at_start else curve[-2])
        vector = anchor-handle
        angle = math.atan2(vector[1],vector[0]) if any(vector) else 0
        tip.rotate(angle-tip.tip_angle)
        tip.shift(anchor-tip.tip_point)

    def get_unpositioned_tip(self, tip_shape=None, tip_length=None, tip_width=None):
        shape = ArrowTriangleFilledTip if tip_shape is None else tip_shape
        if not isinstance(shape,type) or not issubclass(shape,ArrowTip) or shape is ArrowTip:
            raise TypeError('tip_shape must be a concrete ArrowTip class')
        length = self.get_default_tip_length() if tip_length is None else tip_length
        ArrowTip._tip_dimension(length,'length')
        if tip_width is not None:
            ArrowTip._tip_dimension(tip_width,'width')
        if not isinstance(self.tip_style,dict):
            raise TypeError('tip_style must be a dictionary')
        style = dict(color=self.stroke_color,fill_color=self.stroke_color,stroke_color=self.stroke_color)
        if shape is ArrowTriangleFilledTip:
            style['width'] = self.get_default_tip_length() if tip_width is None else tip_width
        style.update(copy.deepcopy(self.tip_style))
        return shape(length=length,**style)

    def position_tip(self, tip, at_start=False):
        if not isinstance(at_start,bool):
            raise ValueError('at_start must be a boolean')
        if not isinstance(tip,ArrowTip):
            raise TypeError('tip must be an ArrowTip')
        self._validate_children([tip])
        self._geometry_center()
        # Tip coordinates, like other children, are local to this parent.
        self._orient_tip(tip,at_start)
        return tip

    def create_tip(self, tip_shape=None, tip_length=None, tip_width=None, at_start=False):
        if not isinstance(at_start,bool):
            raise ValueError('at_start must be a boolean')
        if self.geometry_scale == 0:
            raise ValueError('Cannot create a positioned tip on collapsed geometry')
        tip = self.get_unpositioned_tip(tip_shape,tip_length,tip_width)
        tip.scale(1/abs(self.geometry_scale))
        return self.position_tip(tip,at_start)

    def add_tip(self, tip=None, tip_shape=None, tip_length=None, tip_width=None, at_start=False):
        if not isinstance(at_start,bool):
            raise ValueError('at_start must be a boolean')
        if self.geometry_scale == 0:
            raise ValueError('Cannot add a tip to collapsed geometry')
        tip = (self.create_tip(tip_shape,tip_length,tip_width,at_start) if tip is None
               else self.position_tip(tip,at_start))
        self._prepare_tip_path()
        role = 'start' if at_start else 'end'
        old = self._tip(at_start)
        tip._tip_role = role
        self._replace_children([child for child in self.children if child is not old and child is not tip]+[tip])
        self.explicit_tips = True
        return self

    def pop_tips(self):
        tips = self.get_tips()
        self.remove(*tips.children)
        self.explicit_tips = True
        return tips

    def _raw_curves(self):
        snapshot = self.to_dict()
        snapshot.pop('shaft_curves',None)
        snapshot.pop('shaft_start',None)
        snapshot.pop('shaft_end',None)
        return _path_curves(snapshot)

    def get_start(self):
        tip = self._tip(True)
        curves = self._raw_curves() if tip is None else None
        if curves == []:
            raise ValueError('The curve has no completed segments')
        point = tip.tip_point if tip is not None else Vector(curves[0][0])
        return self._point_to_world(point)

    def get_end(self):
        tip = self._tip()
        curves = self._raw_curves() if tip is None else None
        if curves == []:
            raise ValueError('The curve has no completed segments')
        point = tip.tip_point if tip is not None else Vector(curves[-1][-1])
        return self._point_to_world(point)

    def put_start_and_end_on(self, start, end):
        start,end = Line._endpoints(start,end)
        old_start,old_end = self.get_start_and_end()
        old_vector,new_vector = old_end-old_start,end-start
        old_length,new_length = math.hypot(*old_vector),math.hypot(*new_vector)
        if not math.isfinite(new_length):
            raise ValueError('Curve endpoint span must be finite')
        if not old_length:
            if new_length:
                raise ValueError('Cannot expand a collapsed curve with endpoint fitting')
            return self.shift(start-old_start)
        factor = new_length/old_length
        if not math.isfinite(factor):
            raise ValueError('Curve endpoint scale must be finite')
        angle = math.atan2(new_vector[1],new_vector[0])-math.atan2(old_vector[1],old_vector[0])
        self.rotate(angle,about_point=old_start).scale(factor,about_point=old_start)
        return self.shift(start-old_start)

    def get_start_and_end(self):
        return self.get_start(), self.get_end()

    def get_vector(self):
        return self.get_end() - self.get_start()

    def get_length(self):
        return math.dist(self.get_start(), self.get_end())

    def get_unit_vector(self):
        length = self.get_length()
        if not math.isfinite(length):
            raise ValueError('Line length must be finite')
        return Vector(value/length for value in self.get_vector()) if length else ORIGIN

    def _prepare_tip_path(self):
        if self._type in ('line','arrow') or self.__dict__.get('_curved_tip_path'):
            return
        curves = self._raw_curves()
        if not curves:
            raise ValueError('The path has no completed segments')
        before = self._geometry_center()
        self.curves,self.vertices = curves,[]
        self._type = 'bezierpath'
        self._curved_tip_path = True
        self.__dict__.pop('_family_pivot_cache',None)
        after = self._geometry_center()
        delta = after-before
        transformed = Vector((delta[0]*math.cos(self.angle)-delta[1]*math.sin(self.angle),
                              delta[0]*math.sin(self.angle)+delta[1]*math.cos(self.angle),0))*self.geometry_scale
        self.shift(transformed-delta)

    def get_first_handle(self):
        curves = _path_curves(self.to_dict())
        if not curves:
            raise ValueError('The path has no completed segments')
        return self._point_to_world(Vector(curves[0][1]))

    def get_last_handle(self):
        curves = _path_curves(self.to_dict())
        if not curves:
            raise ValueError('The path has no completed segments')
        return self._point_to_world(Vector(curves[-1][-2]))


class Arc(TipableVMobject):
    def __init__(self, radius=1, start_angle=0, angle=PI / 2, arc_center=ORIGIN, **kwargs):
        center = Vector(arc_center)
        if not all(math.isfinite(v) for v in (radius, start_angle, angle, *center)) or radius < 0:
            raise ValueError('Arc geometry must be finite with a nonnegative radius')
        if center[2]:
            raise NotImplementedError('Arcs support only the XY plane')
        if abs(angle) > TAU:
            raise NotImplementedError('Arcs support at most one full turn')
        kwargs.setdefault('stroke_width',2)
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


class Circle(Arc):
    def __init__(self, radius=1, **kwargs):
        kwargs.setdefault('color', RED)  # Community's Circle (and Ellipse) default to RED.
        super().__init__(radius=1 if radius is None else radius, start_angle=0, angle=TAU, **kwargs)
        self._type = 'circle'

    def surround(self, mobject, dim_to_match=0, stretch=False, buffer_factor=1.2):
        if not isinstance(mobject,Mobject):
            raise TypeError('surround expects a Mobject')
        self._fit_dimension(dim_to_match)
        if not isinstance(stretch,bool):
            raise ValueError('stretch must be a boolean')
        NumberLine._real(buffer_factor,'Circle buffer factor',nonnegative=True)
        if not mobject.get_num_points() and not mobject.children and mobject._type not in ('text', 'mathtex'):
            raise ValueError('Cannot surround a mobject with no points or children')
        diameter = math.hypot(mobject.get_width(),mobject.get_height())*buffer_factor
        center = mobject.get_center()
        if not all(math.isfinite(value) for value in (*center,diameter)):
            raise ValueError('Surround geometry must be finite')
        target = self.copy()
        if stretch:
            target.replace(mobject,dim_to_match,stretch=True)
        target.scale_to_fit_width(diameter).move_to(center)
        return self.become(target)

    def point_at_angle(self, angle):
        NumberLine._real(angle,'Circle point angle')
        return self.point_from_proportion((angle % TAU)/TAU)

    @staticmethod
    def from_three_points(p1, p2, p3, **kwargs):
        points = VMobject._corners([p1,p2,p3])
        origin,a,b = map(Vector,points)
        u,v = a-origin,b-origin
        extent = max(math.hypot(*u),math.hypot(*v))
        if not math.isfinite(extent) or not extent:
            raise ValueError('Circle points require a finite nonzero span')
        u,v = Vector(value/extent for value in u),Vector(value/extent for value in v)
        determinant = u[0]*v[1]-u[1]*v[0]
        if not determinant:
            raise ValueError('Circle points must be distinct and noncollinear')
        uu,vv = sum(value*value for value in u),sum(value*value for value in v)
        offset = Vector(((v[1]*uu-u[1]*vv)/(2*determinant),
                         (u[0]*vv-v[0]*uu)/(2*determinant),0))*extent
        center,radius = origin+offset,math.hypot(*offset)
        if not all(math.isfinite(value) for value in (*center,radius)):
            raise ValueError('Three-point circle geometry must be finite')
        return Circle(radius=radius,**kwargs).shift(center)


class Ellipse(Circle):
    def __init__(self, width=2, height=1, **kwargs):
        if any(isinstance(v, bool) or not isinstance(v, _REAL) or
               not math.isfinite(v) or v < 0 for v in (width, height)):
            raise ValueError('Ellipse dimensions must be nonnegative and finite')
        super().__init__(**kwargs)
        self._type, self.width, self.height = 'ellipse', width, height


class ArcBetweenPoints(Arc):
    """A circular XY arc spanning two endpoints, or a straight zero-angle path."""
    def __init__(self, start, end, angle=PI/2, radius=None, **kwargs):
        kwargs.setdefault('stroke_width',4)
        start,end = Line._endpoints(start,end)
        if isinstance(angle,bool) or not isinstance(angle,_REAL) or not math.isfinite(angle):
            raise ValueError('Arc angle must be finite')
        if radius is not None and (isinstance(radius,bool) or not isinstance(radius,_REAL)
                or not math.isfinite(radius) or radius == 0):
            raise ValueError('Endpoint arc radius must be finite and nonzero')
        chord = end-start
        length = math.hypot(*chord)
        if not math.isfinite(length):
            raise ValueError('Endpoint arc span must be finite')
        if radius is not None:
            if abs(radius) < length/2:
                raise ValueError('Arc radius must be at least half the endpoint distance')
            angle = math.copysign(2*math.asin(min(1,length/2/abs(radius))),radius)
        if abs(angle) >= TAU:
            raise ValueError('Endpoint arcs require less than one full turn')
        if angle == 0 or length == 0:
            super().__init__(radius=0,angle=0,**kwargs)
            self.set_points_as_corners([start,end])
            return
        half = angle/2
        extent = length/2/abs(math.sin(half))
        normal = Vector((-chord[1]/length,chord[0]/length,0))
        center = start*.5+end*.5+normal*(length/2/math.tan(half))
        initial = math.atan2(start[1]-center[1],start[0]-center[0])
        super().__init__(radius=extent,start_angle=initial,angle=angle,arc_center=center,**kwargs)
        # Reject unresolvable extreme geometry rather than return a different path.
        tolerance = max(length,1)*1e-9
        if math.dist(self.get_start(),start)>tolerance or math.dist(self.get_end(),end)>tolerance:
            raise ValueError('Endpoint arc cannot resolve these coordinates at floating-point precision')


class AnnularSector(Arc, VMobject):
    """One connected outline: inner arc, radial edge, reversed outer arc, edge."""
    def __init__(self, inner_radius=1, outer_radius=2, angle=PI/2, start_angle=0,
                 fill_opacity=1, stroke_width=0, color=WHITE, arc_center=ORIGIN, **kwargs):
        if any(isinstance(v, bool) or not isinstance(v, _REAL) or
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
        if any(isinstance(v, bool) or not isinstance(v, _REAL) or
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
        kwargs.setdefault('color', WHITE)
        kwargs.setdefault('fill_opacity', 1)
        kwargs.setdefault('stroke_width', 0)
        super().__init__(radius=radius, **kwargs)
        self.move_to(point)


def _regular_vertices(n, radius=1, start_angle=None):
    if start_angle is None:
        start_angle = 0 if n % 2 == 0 else TAU / 4
    return [[radius * math.cos(start_angle + TAU * k / n),
             radius * math.sin(start_angle + TAU * k / n), 0] for k in range(n)], start_angle


class Polygram(VMobject):
    """Closed straight-edged contours, one per vertex group."""
    def __init__(self, *vertex_groups, color=BLUE, **kwargs):
        groups = [VMobject._corners(group) for group in vertex_groups]
        if sum(len(group) for group in groups) > 100000:
            raise ValueError('Polygrams support at most 100000 vertices')
        if len(groups) > 1 and not all(groups):
            raise ValueError('Each polygram vertex group needs at least one vertex')
        super().__init__(color=color, **kwargs)
        if len(groups) <= 1:
            self._type, self.vertices = 'polygon', groups[0] if groups else []
            return
        self.curves, self.subpath_lengths = [], []
        for group in groups:
            curves = _path_curves({'type': 'polygon', 'vertices': group})
            self.curves.extend(curves)
            self.subpath_lengths.append(len(curves))
        self._type, self.vertices = 'bezierpath', []

    def get_vertices(self):
        return [list(self._point_to_world(Vector(curve[0])))
                for path in _path_subpaths(self.to_dict(), include_pending=False) for curve in path]

    def get_vertex_groups(self):
        return [[list(self._point_to_world(Vector(curve[0]))) for curve in path]
                for path in _path_subpaths(self.to_dict(), include_pending=False)]

    def round_corners(self, radius=0.5, evenly_distribute_anchors=False, components_per_rounded_corner=2):
        radii = list(radius) if isinstance(radius, (list, tuple)) else [radius]
        if not radii or any(isinstance(r, bool) or not isinstance(r, _REAL) or
                            not math.isfinite(r) for r in radii):
            raise ValueError('Corner radii must be finite real values in a nonempty sequence')
        if not isinstance(evenly_distribute_anchors, bool):
            raise ValueError('evenly_distribute_anchors must be a boolean')
        if (isinstance(components_per_rounded_corner, bool) or not isinstance(components_per_rounded_corner, numbers.Integral)
                or not 2 <= components_per_rounded_corner <= 64):
            raise ValueError('components_per_rounded_corner must be an integer from 2 to 64')
        if radii == [0]:
            return self
        paths, lengths = [], []
        for group in self.get_vertex_groups():
            vertices = [Vector(v) for v in group]
            arcs = []
            for i, v2 in enumerate(vertices):
                v1, v3 = vertices[i-1], vertices[(i+1) % len(vertices)]
                # Community zips radii with corners starting at the second vertex.
                r = radii[(i-1) % len(vertices) % len(radii)]
                a, b = v2 - v1, v3 - v2
                la, lb = math.hypot(a[0], a[1]), math.hypot(b[0], b[1])
                if not la or not lb:
                    arcs.append((v2, v2, []))
                    continue
                ua, ub = a * (1/la), b * (1/lb)
                angle = math.acos(max(-1, min(1, ua[0]*ub[0] + ua[1]*ub[1])))
                cut = min(abs(r) * math.tan(angle / 2), min(la, lb) / 2)
                cross = a[0]*b[1] - a[1]*b[0]
                sweep = ((cross > 0) - (cross < 0)) * ((r > 0) - (r < 0)) * angle
                start, end = v2 - ua * cut, v2 + ub * cut
                if not cut or not sweep:
                    arcs.append((v2, v2, []))
                    continue
                pieces = components_per_rounded_corner - 1
                chord = end - start
                half = math.hypot(chord[0], chord[1]) / 2
                radius_ = half / math.sin(abs(sweep) / 2)
                normal = Vector((-chord[1], chord[0], 0)) * (1 / (2 * half))
                center = start + chord * .5 + normal * (radius_ * math.cos(sweep / 2) * (1 if sweep > 0 else -1))
                begin = math.atan2(start[1] - center[1], start[0] - center[0])
                step, factor = sweep / pieces, 4 / 3 * math.tan(sweep / pieces / 4)
                curves = []
                for k in range(pieces):
                    p0, p1 = [Vector((center[0] + radius_ * math.cos(begin + step * j),
                                      center[1] + radius_ * math.sin(begin + step * j), 0)) for j in (k, k + 1)]
                    t0, t1 = [Vector((center[1] - q[1], q[0] - center[0], 0)) for q in (p0, p1)]
                    curves.append([list(p0), list(p0 + t0 * factor), list(p1 - t1 * factor), list(p1)])
                curves[0][0], curves[-1][-1] = list(start), list(end)
                arcs.append((start, end, curves))
            average = 1.0
            if evenly_distribute_anchors:
                # Community averages only arcs with more than one cubic piece.
                long_arcs = [curves for _, _, curves in arcs if len(curves) > 1]
                if long_arcs:
                    total = sum(_curve_length_data(VMobject().set_points(
                        [p for curve in curves for p in curve]), 10)[0][-1] for curves in long_arcs)
                    average = total / sum(len(curves) for curves in long_arcs)
            # arcs is already ordered from the first vertex, as after Community's rotation.
            curves = []
            for i, (_, a, arc) in enumerate(arcs):
                curves.extend(arc)
                b = arcs[(i + 1) % len(arcs)][0]
                segments = 1 + (math.ceil(math.hypot(b[0]-a[0], b[1]-a[1]) / average)
                                if evenly_distribute_anchors else 0)
                for k in range(segments):
                    p, q = a + (b - a) * (k / segments), a + (b - a) * ((k + 1) / segments)
                    curves.append([list(p), list(p + (q - p) * (1/3)), list(p + (q - p) * (2/3)), list(q)])
            paths.extend(curves)
            lengths.append(len(curves))
        if not paths:
            return self
        self.set_points([point for curve in paths for point in curve])
        if len(lengths) > 1:
            self.subpath_lengths = lengths
        return self


class Polygon(Polygram):
    def __init__(self, *vertices, **kwargs):
        super().__init__(vertices, **kwargs)


class Rectangle(Polygon):
    """Community Rectangle (a Polygon); keeps analytical width/height geometry."""
    def __init__(self, width=4, height=2, color=WHITE, **kwargs):
        super().__init__(color=color, **kwargs)
        self._type, self.width, self.height = 'rectangle', width, height


class Square(Rectangle):
    def __init__(self, side_length=2, **kwargs):
        super().__init__(**kwargs)
        del self.width, self.height
        self._type, self.side_length = 'square', side_length


class RoundedRectangle(Rectangle):
    """A closed rectangle with circular, optionally concave corner cuts."""
    def __init__(self, corner_radius=0.5, width=4, height=2, **kwargs):
        if any(isinstance(v, bool) or not isinstance(v, _REAL) or
               not math.isfinite(v) or v < 0 for v in (width, height)):
            raise ValueError('Rounded rectangle dimensions must be nonnegative and finite')
        radii = list(corner_radius) if isinstance(corner_radius, (list, tuple)) else [corner_radius]
        if not radii or any(isinstance(v, bool) or not isinstance(v, _REAL) or
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
    def scale(self, scale_factor, **kwargs):
        if not math.isfinite(scale_factor) or scale_factor <= 0:
            raise ValueError('Camera scale must be positive and finite')
        return super().scale(scale_factor, **kwargs)

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
        if not isinstance(margin, _REAL) or not math.isfinite(margin):
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


class Line(TipableVMobject):
    def __init__(self, start=LEFT, end=RIGHT, buff=0, tip_length=.35, tip_style=None, **kwargs):
        start,end = self._endpoints(*self._resolve_ends(start,end))
        ArrowTip._tip_dimension(tip_length,'length')
        if tip_style is not None and not isinstance(tip_style,dict):
            raise TypeError('tip_style must be a dictionary')
        if isinstance(buff,bool) or not isinstance(buff,_REAL) or not math.isfinite(buff) or buff < 0:
            raise ValueError('Line buffer must be nonnegative and finite')
        span = math.dist(start,end)
        if not math.isfinite(span):
            raise ValueError('Line length must be finite')
        if span > 2*buff and buff:
            offset = (end-start)*(buff/span)
            start,end = start+offset,end-offset
        kwargs.setdefault('stroke_width',2)
        super().__init__(tip_length=tip_length,tip_style=tip_style,**kwargs)
        self._type = 'line'
        self.start, self.end = list(start),list(end)
        self.buff = buff

    def _orient_tip(self, tip, at_start):
        vector = Vector(self.start)-Vector(self.end) if at_start else Vector(self.end)-Vector(self.start)
        angle = math.atan2(vector[1],vector[0]) if any(vector) else 0
        tip.rotate(angle-tip.tip_angle)
        tip.shift(Vector(self.start if at_start else self.end)-tip.tip_point)

    @staticmethod
    def _pointify(mob_or_point, direction=None):
        if isinstance(mob_or_point, Mobject):
            return mob_or_point.get_center() if direction is None else mob_or_point.get_boundary_point(direction)
        return Vector(mob_or_point)

    @classmethod
    def _resolve_ends(cls, start, end):
        """Community's endpoints: a Mobject end stops at its boundary point facing the other end."""
        if not isinstance(start, Mobject) and not isinstance(end, Mobject):
            return start, end
        rough = cls._pointify(end) - cls._pointify(start)
        length = math.sqrt(sum(v * v for v in rough))
        direction = rough / length if length else Vector(ORIGIN)
        return cls._pointify(start, direction), cls._pointify(end, -direction)

    def set_points_by_ends(self, start, end, buff=0, path_arc=0):
        if path_arc:
            raise NotImplementedError('set_points_by_ends supports straight lines (path_arc=0)')
        start, end = self._endpoints(*self._resolve_ends(start, end))
        span = math.dist(start, end)
        if buff and span > 2 * buff:
            offset = (end - start) * (buff / span)
            start, end = start + offset, end - offset
        return self.put_start_and_end_on(start, end)

    @staticmethod
    def _endpoints(start, end):
        start, end = Vector(start), Vector(end)
        if not all(math.isfinite(v) for v in (*start, *end)):
            raise ValueError('Line endpoints must be finite')
        if start[2] or end[2]:
            raise NotImplementedError('Line endpoints support only the XY plane')
        return start, end

    def get_start(self):
        if self._type not in ('line','arrow','vgroup'):
            return Mobject.get_start(self)
        self._endpoints(self.start, self.end)
        return self._point_to_world(Vector(self.start))

    def get_end(self):
        if self._type not in ('line','arrow','vgroup'):
            return Mobject.get_end(self)
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
        if not math.isfinite(length):
            raise ValueError('Line length must be finite')
        return Vector(value/length for value in self.get_vector()) if length else ORIGIN

    def get_angle(self):
        vector = self.get_vector()
        return math.atan2(vector[1], vector[0]) if any(vector) else 0

    def get_slope(self):
        return math.tan(self.get_angle())

    def set_angle(self, angle, about_point=None):
        if isinstance(angle,bool) or not isinstance(angle,_REAL) or not math.isfinite(angle):
            raise ValueError('Line angle must be finite')
        pivot = self.get_start() if about_point is None else about_point
        return self.rotate(angle-self.get_angle(),about_point=pivot)

    def set_length(self, length):
        if isinstance(length,bool) or not isinstance(length,_REAL) or not math.isfinite(length) or length < 0:
            raise ValueError('Line length must be nonnegative and finite')
        current = self.get_length()
        if not math.isfinite(current) or current == 0:
            raise ValueError('Cannot resize a collapsed or nonfinite line')
        return self.scale(length/current)

    def get_projection(self, point):
        point,_ = Line._endpoints(point,point)
        start,end = self.get_start_and_end()
        vector = end-start
        length = math.hypot(*vector)
        if not math.isfinite(length):
            raise ValueError('Projection line length must be finite')
        if not length:
            return start
        unit = Vector(value/length for value in vector)
        distance = sum(a*b for a,b in zip(point-start,unit))
        result = start+unit*distance
        Line._endpoints(result,result)
        return result

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
        self.geometry_scale = scale
        for at_start in (False,True):
            tip = self._tip(at_start)
            if tip is not None:
                self._orient_tip(tip,at_start)
        self.__dict__.pop('_family_pivot_cache',None)
        pivot = self._geometry_center()
        rotated = Vector((pivot[0]*math.cos(self.angle)-pivot[1]*math.sin(self.angle),
                          pivot[0]*math.sin(self.angle)+pivot[1]*math.cos(self.angle),0))*scale
        self.position = list(center-pivot+rotated)
        return self


class TangentLine(Line):
    """Finite-difference tangent to a supported world-space path."""
    def __init__(self, vmob, alpha, length=1, d_alpha=1e-6, **kwargs):
        if not isinstance(vmob,Mobject) or vmob._type not in (
                'polyline','polygon','bezierpath','circle','arc','ellipse',
                'square','rectangle','triangle','line','annulus'):
            raise TypeError('TangentLine needs a supported vector outline')
        if isinstance(alpha,bool) or not isinstance(alpha,_REAL) or not math.isfinite(alpha) or not 0 <= alpha <= 1:
            raise ValueError('Tangent proportion must be finite and between 0 and 1')
        if isinstance(length,bool) or not isinstance(length,_REAL) or not math.isfinite(length) or length < 0:
            raise ValueError('Tangent length must be nonnegative and finite')
        if isinstance(d_alpha,bool) or not isinstance(d_alpha,_REAL) or not math.isfinite(d_alpha) or d_alpha <= 0:
            raise ValueError('Tangent sample distance must be positive and finite')
        super().__init__(LEFT,RIGHT,**kwargs)
        a,b = max(0,alpha-d_alpha),min(1,alpha+d_alpha)
        if a == b:
            raise ValueError('Tangent sample distance cannot change this proportion')
        if a == 0 and b == 1 and vmob.is_closed():
            raise ValueError('A full closed path has coincident tangent samples')
        p1,p2 = Line._endpoints(vmob.point_from_proportion(a),vmob.point_from_proportion(b))
        vector = p2-p1
        span = math.hypot(*vector)
        if not math.isfinite(span) or not span:
            raise ValueError('Cannot construct a tangent from coincident or nonfinite samples')
        center = p1*.5+p2*.5
        half = Vector(value/span for value in vector)*(length/2)
        start,end = Line._endpoints(center-half,center+half)
        self.start,self.end = list(start),list(end)
        self.length,self.d_alpha = length,d_alpha


class ArrowTip(VMobject):
    """Editable tip geometry; subclasses supply their closed outline."""
    def __init__(self, **kwargs):
        if type(self) is ArrowTip:
            raise NotImplementedError('ArrowTip requires a concrete tip shape')
        super().__init__(**kwargs)

    @property
    def tip_point(self):
        return self.get_start()

    @property
    def base(self):
        # Native tips use the midpoint of their ordered cubic curve array.
        curves = _path_curves(self.to_dict())
        if not curves:
            raise ValueError('The tip has no completed curves')
        index = len(curves)/2
        return self._point_to_world(VMobject._bezier_point(curves[min(int(index),len(curves)-1)],index-int(index)))

    @property
    def vector(self):
        return self.tip_point-self.base

    @property
    def tip_angle(self):
        vector = self.vector
        return math.atan2(vector[1],vector[0])

    @property
    def length(self):
        return math.hypot(*self.vector)

    @staticmethod
    def _tip_dimension(value, name):
        if isinstance(value,bool) or not isinstance(value,_REAL) or not math.isfinite(value) or value < 0:
            raise ValueError('Tip '+name+' must be nonnegative and finite')


class ArrowTriangleTip(ArrowTip):
    def __init__(self, length=.35, width=.35, start_angle=PI,
                 fill_opacity=0, stroke_width=3, **kwargs):
        self._tip_dimension(length,'length')
        self._tip_dimension(width,'width')
        if isinstance(start_angle,bool) or not isinstance(start_angle,_REAL) or not math.isfinite(start_angle):
            raise ValueError('Tip start_angle must be finite')
        super().__init__(fill_opacity=fill_opacity,stroke_width=stroke_width,**kwargs)
        phase = math.atan2(math.sin(start_angle),math.cos(start_angle))
        vertices = [Vector((math.cos(phase+i*TAU/3),math.sin(phase+i*TAU/3),0)) for i in range(3)]
        xs,ys = [v[0] for v in vertices],[v[1] for v in vertices]
        cx,cy = (min(xs)+max(xs))/2,(min(ys)+max(ys))/2
        sx,sy = max(xs)-min(xs),max(ys)-min(ys)
        points = [Vector(((v[0]-cx)*length/sx,(v[1]-cy)*width/sy,0)) for v in vertices]
        self.set_points_as_corners(points+[points[0]])
        self.start_angle = start_angle


class ArrowTriangleFilledTip(ArrowTriangleTip):
    def __init__(self, fill_opacity=1, stroke_width=0, **kwargs):
        super().__init__(fill_opacity=fill_opacity,stroke_width=stroke_width,**kwargs)


class ArrowCircleTip(ArrowTip):
    def __init__(self, length=.35, start_angle=PI, fill_opacity=0,
                 stroke_width=3, **kwargs):
        self._tip_dimension(length,'length')
        if isinstance(start_angle,bool) or not isinstance(start_angle,_REAL) or not math.isfinite(start_angle):
            raise ValueError('Tip start_angle must be finite')
        super().__init__(fill_opacity=fill_opacity,stroke_width=stroke_width,**kwargs)
        phase = math.atan2(math.sin(start_angle),math.cos(start_angle))
        curves = _path_curves({'type':'circle','radius':length/2,'start_angle':phase})
        self.set_points([point for curve in curves for point in curve])
        self.start_angle = start_angle


class ArrowCircleFilledTip(ArrowCircleTip):
    def __init__(self, fill_opacity=1, stroke_width=0, **kwargs):
        super().__init__(fill_opacity=fill_opacity,stroke_width=stroke_width,**kwargs)


class ArrowSquareTip(ArrowTip):
    def __init__(self, length=.35, start_angle=PI, fill_opacity=0,
                 stroke_width=3, **kwargs):
        self._tip_dimension(length,'length')
        if isinstance(start_angle,bool) or not isinstance(start_angle,_REAL) or not math.isfinite(start_angle):
            raise ValueError('Tip start_angle must be finite')
        super().__init__(fill_opacity=fill_opacity,stroke_width=stroke_width,**kwargs)
        half = length/2
        self.set_points_as_corners([(half,half,0),(-half,half,0),
                                   (-half,-half,0),(half,-half,0),(half,half,0)])
        # Native Square uses its default corner ordering; this is metadata.
        self.start_angle = start_angle


class ArrowSquareFilledTip(ArrowSquareTip):
    def __init__(self, fill_opacity=1, stroke_width=0, **kwargs):
        super().__init__(fill_opacity=fill_opacity,stroke_width=stroke_width,**kwargs)


class StealthTip(ArrowTip):
    def __init__(self, length=.175, start_angle=PI, fill_opacity=1,
                 stroke_width=3, **kwargs):
        self._tip_dimension(length,'length')
        if isinstance(start_angle,bool) or not isinstance(start_angle,_REAL) or not math.isfinite(start_angle):
            raise ValueError('Tip start_angle must be finite')
        super().__init__(fill_opacity=fill_opacity,stroke_width=stroke_width,**kwargs)
        factor = length/3.2
        points = [Vector((x*factor,y*factor,0)) for x,y in ((2,0),(-1.2,1.6),(0,0),(-1.2,-1.6),(2,0))]
        self.set_points_as_corners(points)
        self.start_angle = start_angle

    @property
    def length(self):
        return math.hypot(*self.vector)*1.6


class Arrow(Line):
    def __init__(self, start=LEFT, end=RIGHT, buff=.25, stroke_width=6, tip_length=.35,
                 tip_shape=None, max_tip_length_to_length_ratio=.25,
                 max_stroke_width_to_length_ratio=5, **kwargs):
        for value,name in ((tip_length,'length'),(max_tip_length_to_length_ratio,'length ratio'),
                           (max_stroke_width_to_length_ratio,'stroke ratio')):
            ArrowTip._tip_dimension(value,name)
        super().__init__(start,end,buff=buff,stroke_width=stroke_width,tip_length=tip_length,**kwargs)
        self._type = 'arrow'
        self.tip_length = tip_length
        self.max_tip_length_to_length_ratio = max_tip_length_to_length_ratio
        self.max_stroke_width_to_length_ratio = max_stroke_width_to_length_ratio
        self.initial_stroke_width = stroke_width
        self.add_tip(tip_shape=tip_shape)
        self._set_stroke_width_from_length()

    def get_default_tip_length(self):
        return min(self.tip_length,self.max_tip_length_to_length_ratio*self.get_length())

    def _set_stroke_width_from_length(self):
        self.stroke_width = min(self.initial_stroke_width,self.max_stroke_width_to_length_ratio*self.get_length())

    def scale(self, factor, scale_tips=False, **kwargs):
        if not isinstance(scale_tips,bool):
            raise ValueError('scale_tips must be a boolean')
        super().scale(factor,**kwargs)
        if factor and not scale_tips:
            for tip in self.get_tips().children:
                tip.scale(1/abs(factor),about_point=tip.tip_point)
            self._geometry_center()
        self._set_stroke_width_from_length()
        return self

    def put_start_and_end_on(self, start, end):
        super().put_start_and_end_on(start,end)
        self._set_stroke_width_from_length()
        return self


class DoubleArrow(Arrow):
    """Straight Arrow with independently configurable start and end tips."""
    def __init__(self, *args, **kwargs):
        if 'tip_shape_end' in kwargs:
            kwargs['tip_shape'] = kwargs.pop('tip_shape_end')
        tip_shape_start = kwargs.pop('tip_shape_start',ArrowTriangleFilledTip)
        super().__init__(*args,**kwargs)
        self.add_tip(at_start=True,tip_shape=tip_shape_start)


class CurvedArrow(ArcBetweenPoints):
    """An editable endpoint arc with tangent-aligned tip children."""
    def __init__(self, start_point, end_point, tip_shape=None, tip_length=.35, tip_style=None, **kwargs):
        if tip_style is not None and not isinstance(tip_style,dict):
            raise TypeError('tip_style must be a dictionary')
        ArrowTip._tip_dimension(tip_length,'length')
        super().__init__(start_point,end_point,**kwargs)
        center = Arc.get_arc_center(self)
        points = Mobject.get_points(self)
        VMobject.set_points(self,points)
        self._curve_arc_center = list(center)
        self._curved_tip_path = True
        self.tip_length = tip_length
        self.tip_style = copy.deepcopy(tip_style or {})
        self.add_tip(tip_shape=tip_shape)

    def get_arc_center(self):
        return self._point_to_world(Vector(self.__dict__.get('_curve_arc_center',ORIGIN)))



class CurvedDoubleArrow(CurvedArrow):
    def __init__(self, start_point, end_point, **kwargs):
        if 'tip_shape_end' in kwargs:
            kwargs['tip_shape'] = kwargs.pop('tip_shape_end')
        tip_shape_start = kwargs.pop('tip_shape_start',ArrowTriangleFilledTip)
        super().__init__(start_point,end_point,**kwargs)
        self.add_tip(at_start=True,tip_shape=tip_shape_start)


class RegularPolygram(Polygram):
    def __init__(self, num_vertices, *, density=2, radius=1, start_angle=None, **kwargs):
        if isinstance(num_vertices, bool) or not isinstance(num_vertices, numbers.Integral) or not 1 <= num_vertices <= 10000:
            raise ValueError('num_vertices must be an integer from 1 to 10000')
        if isinstance(density, bool) or not isinstance(density, numbers.Integral) or density < 1:
            raise ValueError('density must be a positive integer')
        NumberLine._real(radius, 'Polygram radius')
        if start_angle is not None:
            NumberLine._real(start_angle, 'Polygram start angle')
        num_gons = math.gcd(num_vertices, density)
        num_vertices, density = num_vertices // num_gons, density // num_gons

        def group(angle):
            vertices, angle = _regular_vertices(num_vertices, radius, angle)
            order, i = [], 0
            while True:
                order.append(vertices[i])
                i = (i + density) % num_vertices
                if i == 0:
                    return order, angle
        first, self_start = group(start_angle)
        groups = [first] + [group(self_start + i / num_gons * TAU / num_vertices)[0] for i in range(1, num_gons)]
        super().__init__(*groups, **kwargs)
        self.start_angle = self_start


class RegularPolygon(RegularPolygram):
    def __init__(self, n=6, **kwargs):
        super().__init__(n, density=1, **kwargs)


class Star(Polygon):
    def __init__(self, n=5, *, outer_radius=1, inner_radius=None, density=2, start_angle=TAU / 4, **kwargs):
        if isinstance(n, bool) or not isinstance(n, numbers.Integral) or not 2 <= n <= 10000:
            raise ValueError('Star points must be an integer from 2 to 10000')
        NumberLine._real(outer_radius, 'Star outer radius')
        inner_angle = TAU / (2 * n)
        if inner_radius is None:
            if isinstance(density, bool) or not isinstance(density, _REAL) or density <= 0 or density >= n / 2:
                raise ValueError(f'Incompatible density {density} for number of points {n}')
            outer_angle = TAU * density / n
            inverse_x = 1 - math.tan(inner_angle) * ((math.cos(outer_angle) - 1) / math.sin(outer_angle))
            inner_radius = outer_radius / (math.cos(inner_angle) * inverse_x)
        NumberLine._real(inner_radius, 'Star inner radius')
        if start_angle is not None:
            NumberLine._real(start_angle, 'Star start angle')
        outer, angle = _regular_vertices(n, outer_radius, start_angle)
        inner, _ = _regular_vertices(n, inner_radius, angle + inner_angle)
        super().__init__(*[v for pair in zip(outer, inner) for v in pair], **kwargs)
        self.start_angle, self.inner_radius, self.outer_radius = angle, inner_radius, outer_radius


class Triangle(RegularPolygon):
    def __init__(self, **kwargs):
        super().__init__(n=3, **kwargs)


# Liberation Sans (Arial-metric) advance and ink box per glyph, in 1/1000 em:
# (advance, x_min, x_max, y_min, y_max). The renderer draws this family and pins
# each line's advance with textLength, so preview bounds match the drawn text.
_SANS_GLYPHS = {' ':(278,0,0,0,0), '!':(278,90,187,0,688), '"':(355,42,312,472,688), '#':(556,4,551,0,684), '$':(556,11,540,-69,740), '%':(889,36,854,-6,694), '&':(667,35,651,-10,692), "'":(191,51,141,472,688), '(':(333,62,327,-207,725), ')':(333,6,271,-207,725), '*':(389,16,374,337,688), '+':(584,49,535,88,577), ',':(278,90,188,-128,107), '-':(333,44,289,227,305), '.':(278,91,187,0,107), '/':(278,0,278,-10,725), '0':(556,39,517,-10,698), '1':(556,76,507,0,688), '2':(556,50,506,0,698), '3':(556,38,512,-10,698), '4':(556,23,527,0,688), '5':(556,40,514,-10,688), '6':(556,51,512,-10,698), '7':(556,51,506,0,688), '8':(556,43,513,-10,698), '9':(556,47,509,-10,698), ':':(278,91,187,0,528), ';':(278,90,188,-128,528), '<':(584,49,535,75,583), '=':(584,49,535,168,490), '>':(584,49,535,75,583), '?':(556,41,519,0,698), '@':(1015,79,929,-138,725), 'A':(667,2,665,0,688), 'B':(667,82,614,0,688), 'C':(722,51,684,-10,698), 'D':(722,82,674,0,688), 'E':(667,82,624,0,688), 'F':(611,82,571,0,688), 'G':(778,50,703,-10,698), 'H':(722,82,641,0,688), 'I':(278,92,186,0,688), 'J':(500,16,426,-10,688), 'K':(667,82,656,0,688), 'L':(556,82,523,0,688), 'M':(833,82,751,0,688), 'N':(722,82,641,0,688), 'O':(778,47,730,-10,698), 'P':(667,82,614,0,688), 'Q':(778,47,730,-189,698), 'R':(722,82,676,0,688), 'S':(667,45,621,-10,698), 'T':(611,22,588,0,688), 'U':(722,77,645,-10,688), 'V':(667,4,663,0,688), 'W':(944,4,940,0,688), 'X':(667,22,646,0,688), 'Y':(667,22,645,0,688), 'Z':(611,32,580,0,688), '[':(278,71,270,-208,725), '\\':(278,0,278,-10,725), ']':(278,8,207,-208,725), '^':(469,5,464,329,688), '_':(556,-15,567,-199,-135), '`':(333,52,259,586,736), 'a':(556,42,556,-10,538), 'b':(556,64,514,-10,725), 'c':(500,42,474,-10,538), 'd':(556,42,492,-10,725), 'e':(556,42,512,-10,538), 'f':(278,14,279,0,724), 'g':(556,42,492,-208,537), 'h':(556,69,491,0,725), 'i':(222,67,155,0,725), 'j':(222,-24,155,-208,725), 'k':(500,67,501,0,725), 'l':(222,67,155,0,725), 'm':(833,66,767,0,538), 'n':(556,66,491,0,538), 'o':(556,42,514,-10,538), 'p':(556,64,514,-208,538), 'q':(556,42,492,-208,538), 'r':(333,66,316,0,538), 's':(500,28,464,-10,537), 't':(278,15,271,-8,646), 'u':(556,65,490,-10,528), 'v':(500,3,497,0,528), 'w':(722,-1,725,0,528), 'x':(500,11,489,0,528), 'y':(500,2,498,-208,528), 'z':(500,41,450,0,528), '{':(334,17,316,-208,725), '|':(260,89,170,-212,725), '}':(334,17,316,-208,725), '~':(584,45,539,270,394), '\xa0':(278,0,0,0,0), '¡':(333,118,215,-160,528), '¢':(556,66,497,-15,688), '£':(556,28,539,0,698), '¤':(556,55,501,110,556), '¥':(556,-1,558,0,688), '¦':(260,89,170,-212,725), '§':(556,56,500,-84,725), '¨':(333,22,294,595,685), '©':(737,15,721,-8,698), 'ª':(370,13,374,318,699), '«':(556,41,516,69,459), '¬':(584,49,535,88,368), '\xad':(333,44,289,227,305), '®':(737,15,721,-8,698), '¯':(552,-8,561,709,755), '°':(400,60,340,420,698), '±':(549,32,518,0,595), '²':(333,20,314,275,694), '³':(333,13,313,269,694), '´':(333,35,242,586,736), 'µ':(576,68,553,-208,528), '¶':(537,39,495,-129,688), '·':(333,119,214,218,325), '¸':(333,58,236,-212,0), '¹':(333,39,311,275,688), 'º':(365,13,353,318,699), '»':(556,41,516,69,459), '¼':(834,27,845,-18,688), '½':(834,27,807,0,688), '¾':(834,36,845,-18,694), '¿':(611,64,542,-170,528), 'À':(667,2,665,0,867), 'Á':(667,2,665,0,867), 'Â':(667,2,665,0,874), 'Ã':(667,2,665,0,878), 'Ä':(667,2,665,0,837), 'Å':(667,2,665,0,873), 'Æ':(1000,12,957,0,688), 'Ç':(722,51,684,-212,698), 'È':(667,82,624,0,867), 'É':(667,82,624,0,867), 'Ê':(667,82,624,0,874), 'Ë':(667,82,624,0,837), 'Ì':(278,4,211,0,867), 'Í':(278,69,276,0,867), 'Î':(278,-22,301,0,874), 'Ï':(278,3,275,0,837), 'Ð':(722,7,674,0,688), 'Ñ':(722,82,641,0,878), 'Ò':(778,47,730,-10,867), 'Ó':(778,47,730,-10,867), 'Ô':(778,47,730,-10,874), 'Õ':(778,47,730,-10,878), 'Ö':(778,47,730,-10,837), '×':(584,69,515,110,556), 'Ø':(778,35,744,-26,716), 'Ù':(722,77,645,-10,867), 'Ú':(722,77,645,-10,867), 'Û':(722,77,645,-10,874), 'Ü':(722,77,645,-10,837), 'Ý':(667,22,645,0,867), 'Þ':(667,82,614,0,688), 'ß':(611,69,570,-10,725), 'à':(556,42,556,-10,736), 'á':(556,42,556,-10,736), 'â':(556,42,556,-10,728), 'ã':(556,42,556,-10,717), 'ä':(556,42,556,-10,685), 'å':(556,42,556,-10,806), 'æ':(889,32,845,-10,538), 'ç':(500,42,474,-212,538), 'è':(556,42,512,-10,736), 'é':(556,42,512,-10,736), 'ê':(556,42,512,-10,728), 'ë':(556,42,512,-10,685), 'ì':(278,5,212,0,736), 'í':(278,66,273,0,736), 'î':(278,-22,301,0,728), 'ï':(278,4,276,0,685), 'ð':(556,42,519,-10,739), 'ñ':(556,68,493,0,717), 'ò':(556,42,514,-10,736), 'ó':(556,42,514,-10,736), 'ô':(556,42,514,-10,728), 'õ':(556,42,514,-10,717), 'ö':(556,42,514,-10,685), '÷':(549,32,518,109,557), 'ø':(611,21,588,-19,545), 'ù':(556,68,493,-10,736), 'ú':(556,68,493,-10,736), 'û':(556,68,493,-10,728), 'ü':(556,68,493,-10,685), 'ý':(500,2,498,-208,736), 'þ':(556,67,514,-208,725), 'ÿ':(500,2,498,-208,685), 'Α':(667,2,665,0,688), 'Β':(667,82,614,0,688), 'Γ':(551,82,523,0,688), 'Δ':(668,30,638,0,688), 'Ε':(667,82,624,0,688), 'Ζ':(611,32,580,0,688), 'Η':(722,82,641,0,688), 'Θ':(778,47,730,-10,698), 'Ι':(278,92,186,0,688), 'Κ':(667,82,656,0,688), 'Λ':(668,5,663,0,688), 'Μ':(833,82,751,0,688), 'Ν':(722,82,641,0,688), 'Ξ':(650,44,606,0,688), 'Ο':(778,47,730,-10,698), 'Π':(722,82,641,0,688), 'Ρ':(667,82,614,0,688), 'Σ':(618,53,579,0,688), 'Τ':(611,22,588,0,688), 'Υ':(667,22,645,0,688), 'Φ':(798,57,741,-5,693), 'Χ':(667,22,646,0,688), 'Ψ':(835,71,765,0,688), 'Ω':(748,42,705,0,698), 'Ϊ':(278,3,275,0,837), 'Ϋ':(667,22,645,0,837), 'ά':(578,42,549,-10,753), 'έ':(446,34,427,-10,753), 'ή':(556,52,491,-207,753), 'ί':(222,67,212,0,753), 'ΰ':(547,65,499,-10,782), 'α':(578,42,549,-10,538), 'β':(575,69,536,-208,725), 'γ':(500,3,497,-207,528), 'δ':(557,42,514,-10,725), 'ε':(446,34,427,-10,538), 'ζ':(441,42,422,-172,725), 'η':(556,52,491,-207,538), 'θ':(556,52,504,-10,724), 'ι':(222,67,194,0,528), 'κ':(500,67,501,0,528), 'λ':(500,7,491,0,725), 'μ':(576,67,503,-192,528), 'ν':(500,0,462,0,528), 'ξ':(448,42,427,-172,725), 'ο':(556,42,514,-10,538), 'π':(690,39,646,-10,528), 'ρ':(569,64,529,-208,539), 'ς':(482,42,451,-172,538), 'σ':(617,42,602,-10,528), 'τ':(395,14,387,-10,528), 'υ':(547,65,499,-10,528), 'φ':(648,42,606,-208,540), 'χ':(525,10,513,-207,539), 'ψ':(713,66,646,-208,654), 'ω':(781,41,740,-10,539), '–':(556,0,556,220,287), '—':(1000,0,1000,220,287), '‘':(222,62,160,465,688), '’':(222,62,160,465,688), '“':(333,37,296,465,688), '”':(333,37,296,465,688), '•':(350,40,311,196,467), '…':(1000,136,864,0,107), '€':(556,8,542,-10,698), '−':(584,49,535,297,368), '∞':(713,42,670,99,480), '≤':(549,31,518,0,601), '≥':(549,32,518,0,601), '≠':(549,32,518,27,633), '→':(1000,204,796,49,283), '←':(1000,204,796,49,283), '↑':(500,133,367,-30,562), '↓':(500,133,367,-30,562), '≈':(549,27,521,164,494), '√':(549,25,548,-7,791), '∑':(713,75,648,-212,688), '∫':(274,-48,322,-212,736), '∂':(494,27,466,-13,721), '∆':(612,2,610,0,688), 'π':(690,39,646,-10,528), 'θ':(556,52,504,-10,724)}
# DejaVu Sans Mono, the usual fontconfig match for Community's "Monospace" (Code), per 1000 em.
_MONO_GLYPHS = {' ': (602, 0, 0, 0, 0), '!': (602, 252, 351, 0, 729), '"': (602, 165, 437, 458, 729), '#': (602, 1, 600, 0, 718), '$': (602, 93, 544, -147, 760), '%': (602, 16, 586, 0, 699), '&': (602, 28, 596, -14, 742), "'": (602, 258, 343, 458, 729), '(': (602, 208, 432, -132, 759), ')': (602, 170, 394, -132, 759), '*': (602, 81, 521, 286, 742), '+': (602, 43, 559, 55, 572), ',': (602, 197, 368, -140, 148), '-': (602, 174, 428, 234, 314), '.': (602, 239, 362, 0, 149), '/': (602, 50, 527, -93, 729), '0': (602, 65, 537, -14, 742), '1': (602, 120, 534, 0, 729), '2': (602, 74, 517, 0, 742), '3': (602, 67, 527, -14, 742), '4': (602, 50, 554, 0, 729), '5': (602, 70, 522, -14, 729), '6': (602, 65, 537, -14, 742), '7': (602, 68, 527, 0, 729), '8': (602, 64, 538, -14, 742), '9': (602, 62, 534, -14, 742), ':': (602, 239, 362, 0, 519), ';': (602, 197, 368, -140, 519), '<': (602, 43, 559, 69, 558), '=': (602, 43, 559, 172, 454), '>': (602, 43, 559, 69, 558), '?': (602, 119, 508, 0, 742), '@': (602, 13, 575, -156, 681), 'A': (602, 18, 584, 0, 729), 'B': (602, 81, 555, 0, 729), 'C': (602, 68, 524, -14, 742), 'D': (602, 67, 540, 0, 729), 'E': (602, 96, 538, 0, 729), 'F': (602, 114, 543, 0, 729), 'G': (602, 50, 539, -14, 742), 'H': (602, 67, 535, 0, 729), 'I': (602, 98, 503, 0, 729), 'J': (602, 53, 467, -14, 729), 'K': (602, 67, 598, 0, 729), 'L': (602, 105, 556, 0, 729), 'M': (602, 42, 559, 0, 729), 'N': (602, 68, 534, 0, 729), 'O': (602, 57, 545, -14, 742), 'P': (602, 96, 557, 0, 729), 'Q': (602, 57, 545, -132, 742), 'R': (602, 70, 602, 0, 729), 'S': (602, 68, 536, -14, 742), 'T': (602, 23, 579, 0, 729), 'U': (602, 72, 530, -14, 729), 'V': (602, 28, 574, 0, 729), 'W': (602, 0, 602, 0, 729), 'X': (602, 9, 593, 0, 729), 'Y': (602, 18, 584, 0, 729), 'Z': (602, 76, 571, 0, 729), '[': (602, 226, 433, -132, 760), '\\': (602, 50, 527, -93, 729), ']': (602, 169, 376, -132, 760), '^': (602, 35, 567, 457, 729), '_': (602, 0, 602, -236, -197), '`': (602, 136, 370, 616, 800), 'a': (602, 65, 517, -14, 560), 'b': (602, 94, 543, -14, 760), 'c': (602, 95, 518, -14, 560), 'd': (602, 60, 509, -14, 760), 'e': (602, 60, 543, -14, 560), 'f': (602, 95, 519, 0, 760), 'g': (602, 60, 509, -215, 560), 'h': (602, 95, 513, 0, 760), 'i': (602, 87, 533, 0, 760), 'j': (602, 91, 383, -208, 760), 'k': (602, 115, 587, 0, 760), 'l': (602, 78, 505, 0, 765), 'm': (602, 53, 554, 0, 560), 'n': (602, 95, 513, 0, 560), 'o': (602, 67, 535, -14, 560), 'p': (602, 93, 541, -208, 560), 'q': (602, 67, 515, -210, 558), 'r': (602, 177, 564, 0, 560), 's': (602, 104, 503, -14, 560), 't': (602, 64, 504, 0, 702), 'u': (602, 95, 513, -14, 546), 'v': (602, 49, 553, 0, 547), 'w': (602, 0, 602, 0, 547), 'x': (602, 37, 565, 0, 547), 'y': (602, 51, 563, -208, 547), 'z': (602, 99, 508, 0, 548), '{': (602, 108, 494, -163, 760), '|': (602, 259, 343, -236, 764), '}': (602, 108, 494, -163, 760), '~': (602, 43, 559, 240, 381)}
_MONO_FONTS = ('monospace', 'mono', 'dejavu sans mono', 'liberation mono', 'courier', 'courier new',
               'consolas', 'menlo', 'monaco', 'ubuntu mono', 'source code pro', 'fira code', 'fira mono')


def _is_mono(font):
    font = (font or '').strip().lower()
    return font in _MONO_FONTS or font.endswith(' mono')


def _glyph_table(font):
    return _MONO_GLYPHS if _is_mono(font) else _SANS_GLYPHS


# Computer Modern (cmr10/cmsy10 AFM) glyphs used by Community's DecimalNumber.
_CM_GLYPHS = {'0': (500,39,460,-22,666), '1': (500,89,419,0,666), '2': (500,50,449,0,666),
              '3': (500,42,457,-22,666), '4': (500,28,471,0,677), '5': (500,50,449,-22,666),
              '6': (500,42,457,-22,666), '7': (500,56,485,-22,676), '8': (500,42,457,-22,666),
              '9': (500,42,457,-22,666), '.': (277,86,192,0,106), ',': (277,86,203,-193,106),
              '+': (777,56,721,-83,583), '-': (777,83,694,230,270), '…': (1172,86,1086,0,106)}
# Community scales Pango text so an em is font_size/72 units and TeX so it is
# font_size/96 units; Text lines are 1.3 * font_size/96 apart by default.
TEXT_EM_PER_POINT, TEX_EM_PER_POINT = 1 / 72, 1 / 96
NORMAL, ITALIC, OBLIQUE, BOLD = 'NORMAL', 'ITALIC', 'OBLIQUE', 'BOLD'
THIN, ULTRALIGHT, LIGHT, SEMILIGHT, BOOK, MEDIUM = 'THIN', 'ULTRALIGHT', 'LIGHT', 'SEMILIGHT', 'BOOK', 'MEDIUM'
SEMIBOLD, ULTRABOLD, HEAVY, ULTRAHEAVY = 'SEMIBOLD', 'ULTRABOLD', 'HEAVY', 'ULTRAHEAVY'
_MATH_METRICS = {}  # expression -> (width_em, height_em), measured by the browser
_MATH_ESTIMATED = set()


def _glyph_box(char, table):
    if char in table:
        return table[char]
    if table is _MONO_GLYPHS:
        return (602, 0, 0, 0, 0) if char.isspace() else (602, 60, 540, 0, 729)
    import unicodedata
    if unicodedata.east_asian_width(char) in 'WF':
        return (1000, 50, 950, -120, 830)
    if unicodedata.category(char) in ('Mn', 'Me', 'Cf', 'Cc'):
        return (0, 0, 0, 0, 0)
    return (556, 50, 506, 0, 716)


_TEXT_LAYOUTS = {}


def _text_layout(snapshot):
    """Ink-centered line layout for a Text/DecimalNumber snapshot, in scene units."""
    key = (snapshot['text'], snapshot['font_size'], snapshot.get('line_spacing', .3), '_number_format' in snapshot,
           _is_mono(snapshot.get('font')))
    if key not in _TEXT_LAYOUTS:
        if len(_TEXT_LAYOUTS) > 4096:
            _TEXT_LAYOUTS.clear()
        _TEXT_LAYOUTS[key] = _compute_text_layout(*key)
    return copy.deepcopy(_TEXT_LAYOUTS[key])


def _text_extent(snapshot):
    layout = _TEXT_LAYOUTS.get((snapshot['text'], snapshot['font_size'], snapshot.get('line_spacing', .3),
                                '_number_format' in snapshot, _is_mono(snapshot.get('font'))))
    if layout is None:
        layout = _text_layout(snapshot)
    return layout['width'], layout['height']


def _compute_text_layout(text, font_size, line_spacing, numeric, mono=False):
    snapshot = {'text': text, 'font_size': font_size, 'line_spacing': line_spacing}
    em = font_size * (TEX_EM_PER_POINT if numeric else TEXT_EM_PER_POINT) / 1000
    lines, ink = [], None
    def merge(box):
        nonlocal ink
        ink = box if ink is None else (min(ink[0], box[0]), min(ink[1], box[1]),
                                       max(ink[2], box[2]), max(ink[3], box[3]))
    if numeric:
        # Community arranges separate TeX glyphs with 0.001 * font_size gaps,
        # bottom-aligned; commas drop by half their height.
        gap, x, boxes = 0.001 * font_size, 0, []
        for char in snapshot['text']:
            _, x0, x1, y0, y1 = _glyph_box(char, _CM_GLYPHS)
            width, height = (x1 - x0) * em, (y1 - y0) * em
            boxes.append([x, x + width, 0, height, y0 * em])
            x += width + gap
        for i, (char, box) in enumerate(zip(snapshot['text'], boxes)):
            if char == ',':
                box[2] -= (box[3] - box[2]) / 2
                box[3] = box[2] + (_CM_GLYPHS[','][4] - _CM_GLYPHS[','][3]) * em
            elif char == '-' and i + 1 < len(boxes):
                following = boxes[i + 1]
                height = box[3] - box[2]
                box[3] = following[3] - (following[3] - following[2]) / 2
                box[2] = box[3] - height
            merge((box[0], box[2], box[1], box[3]))
        if ink is not None:
            # Draw the string on a baseline that puts digit bottoms on y = 0.
            lines.append({'text': snapshot['text'], 'x': ink[0], 'y': 0, 'length': ink[2] - ink[0]})
    else:
        pitch = font_size * (1 + snapshot.get('line_spacing', .3)) * TEX_EM_PER_POINT
        for row, line in enumerate(snapshot['text'].split('\n')):
            x, baseline = 0, -row * pitch
            for char in line:
                advance, x0, x1, y0, y1 = _glyph_box(char, _MONO_GLYPHS if mono else _SANS_GLYPHS)
                if x1 > x0 or y1 > y0:
                    merge(((x + x0) * em, baseline + y0 * em, (x + x1) * em, baseline + y1 * em))
                x += advance
            lines.append({'text': line, 'x': 0, 'y': baseline, 'length': x * em})
    if ink is None:
        return {'width': 0, 'height': 0, 'lines': [], 'em': em * 1000}
    cx, cy = (ink[0] + ink[2]) / 2, (ink[1] + ink[3]) / 2
    for line in lines:
        line['x'] -= cx
        line['y'] -= cy
    return {'width': ink[2] - ink[0], 'height': ink[3] - ink[1], 'lines': lines, 'em': em * 1000,
            'family': 'serif' if numeric else 'mono' if mono else 'sans'}


def _math_estimate(text, font_size):
    # Rough placeholder until the browser measures the typeset formula.
    import re
    em = font_size * TEX_EM_PER_POINT
    body = re.sub(r'\\class\{manim-part-\d+\}', '', text)
    rows = [body]
    array = re.search(r'\\begin\{array\}\{[^}]*\}(.*?)\\end\{array\}', body, re.S)
    if array:
        rows = [row for row in array.group(1).split('\\\\') if row.strip()] or ['']
        rows = [row if row.strip() != '\\quad' else '' for row in rows]
    def width(row):
        # Fractions stack: replace each innermost one by its wider (scaled) operand.
        pattern = re.compile(r'\\([dt]?)frac\{([^{}]*)\}\{([^{}]*)\}')
        while True:
            match = pattern.search(row)
            if match is None:
                break
            size = max(width(match.group(2)), width(match.group(3))) / .55
            size *= .7 if match.group(1) == 't' else 1
            row = row[:match.start()] + 'x' * max(1, int(round(size))) + row[match.end():]
        delimiters = len(re.findall(r'\\(?:left|right)[^.a-zA-Z]|\\(?:left|right)\\[a-zA-Z]+', row))
        row = re.sub(r'\\begin\{array\}\{[^}]*\}|\\end\{array\}|\\quad|\\(?:left|right)\.?|\\[,;! ]', '', row)
        cells = row.count('&')
        row = re.sub(r'\\[a-zA-Z]+', 'x', row.replace('&', ''))
        row = re.sub(r'[{}^_\s\\\[\]()|.]', '', row)
        return len(row) * .55 + cells * 1.0 + delimiters * .4
    tall = 2 if re.search(r'\\(frac|sum|int|prod|binom|dfrac|tfrac)', text) else 1
    outer = .4 * len(re.findall(r'\\(?:left|right)[\[\]()|]', body)) if array else 0
    total = max(width(row) for row in rows) + outer
    return max(.3, total) * em, .75 * max(tall, 1.6 * len(rows) if array else 1) * em


def _math_box(text, font_size):
    em = font_size * TEX_EM_PER_POINT
    if text in _MATH_METRICS:
        width, height = _MATH_METRICS[text][:2]
        return width * em, height * em
    _MATH_ESTIMATED.add(text)
    return _math_estimate(text, font_size)


def _math_parts(text, parts, font_size):
    """Centers and sizes of each \\class part relative to the formula's ink center."""
    em = font_size * TEX_EM_PER_POINT
    metric = _MATH_METRICS.get(text)
    if metric is not None and len(metric) == 3 and len(metric[2]) == len(parts):
        return [tuple(value * em for value in part) for part in metric[2]]
    _MATH_ESTIMATED.add(text)
    sizes = [_math_estimate(part, font_size) for part in parts]
    gap = .15 * em
    x = -(sum(width for width, _ in sizes) + gap * (len(sizes) - 1)) / 2
    result = []
    for width, height in sizes:
        result.append((x + width / 2, 0, width, height))
        x += width + gap
    return result


class Text(Mobject):
    def __init__(self, text, font_size=48, line_spacing=-1, font='', slant=NORMAL, weight=NORMAL,
                 t2c=None, t2f=None, t2g=None, t2s=None, t2w=None, gradient=None, disable_ligatures=False, **kwargs):
        if isinstance(font_size, bool) or not isinstance(font_size, _REAL) or not math.isfinite(font_size) or font_size <= 0:
            raise ValueError('font_size must be positive and finite')
        if isinstance(line_spacing, bool) or not isinstance(line_spacing, _REAL) or not math.isfinite(line_spacing):
            raise ValueError('line_spacing must be finite')
        if not isinstance(font, str) or len(font) > 128 or any(c in font for c in '<>;{}"\\'):
            raise ValueError('font must be a plain font family name')
        if slant not in (NORMAL, ITALIC, OBLIQUE):
            raise ValueError('slant must be NORMAL, ITALIC or OBLIQUE')
        if weight not in (NORMAL, THIN, ULTRALIGHT, LIGHT, SEMILIGHT, BOOK, MEDIUM, SEMIBOLD, BOLD, ULTRABOLD, HEAVY, ULTRAHEAVY):
            raise ValueError('Unsupported font weight')
        kwargs.setdefault('fill_opacity', 1)
        kwargs.setdefault('stroke_width', 0)
        super().__init__(**kwargs)
        self._type, self.text, self.font_size = 'text', str(text), font_size
        if len(self.text) > 10000:
            raise ValueError('Text is limited to 10000 characters')
        if line_spacing != -1:
            self.line_spacing = line_spacing
        if font:
            self.font = font
        if slant != NORMAL:
            self.slant = slant
        if weight != NORMAL:
            self.weight = weight
        styles = [(t2f, 'font'), (t2s, 'slant'), (t2w, 'weight'), (t2c, 'color'), (t2g, 'gradient')]
        if gradient or any(mapping for mapping, _ in styles):
            self._explode()
            if gradient:
                self.set_color_by_gradient(*gradient)
            for mapping, kind in styles:
                for key, value in (mapping or {}).items():
                    glyphs = [g for g in self.children if g._char_index in self._indices(key)]
                    if kind == 'color':
                        for glyph in glyphs:
                            glyph.set_color(value)
                    elif kind == 'gradient':
                        VGroup(*glyphs).set_color_by_gradient(*value) if glyphs else None
                    else:
                        for glyph in glyphs:
                            setattr(glyph, kind, value)

    def _indices(self, key):
        """Original-text character indices for a t2* key: a substring or '[start:stop]'."""
        import re
        match = re.fullmatch(r'\[(-?\d*):(-?\d*)\]', key)
        if match:
            start = int(match.group(1)) if match.group(1) else None
            stop = int(match.group(2)) if match.group(2) else None
            return set(range(len(self.text))[start:stop])
        indices, at = set(), self.text.find(key)
        while key and at >= 0:
            indices.update(range(at, at + len(key)))
            at = self.text.find(key, at + 1)
        return indices

    def _explode(self):
        """Split into Community-style glyph children placed by the same ink layout."""
        if self._type != 'text' or '_number_format' in self.__dict__:
            return
        layout = _text_layout(self.__dict__)
        em = layout['em'] / 1000
        style = {key: self.__dict__[key] for key in ('color', 'fill_color', 'stroke_color', 'fill_opacity',
                                                    'stroke_opacity', 'stroke_width', 'z_index')}
        options = {key: self.__dict__[key] for key in ('font', 'slant', 'weight', 'line_spacing') if key in self.__dict__}
        glyphs, index = [], 0
        for line in layout['lines']:
            x = line['x']
            for char in line['text']:
                advance, x0, x1, y0, y1 = _glyph_box(char, _glyph_table(self.__dict__.get('font')))
                if not char.isspace() and (x1 > x0 or y1 > y0):
                    glyph = Text(char, font_size=self.font_size, **options, **style)
                    center = Vector((x + (x0 + x1) / 2 * em, line['y'] + (y0 + y1) / 2 * em, 0))
                    glyph.position = list(self._point_to_world(center))
                    glyph.angle, glyph.geometry_scale, glyph.opacity = self.angle, self.geometry_scale, self.opacity
                    if 'glyph_stretch' in self.__dict__:
                        glyph.glyph_stretch = list(self.glyph_stretch)
                    glyph._char_index = index
                    glyphs.append(glyph)
                x += advance * em
                index += 1
            index += 1  # the newline
        self.position, self.angle, self.geometry_scale, self.opacity = [0, 0, 0], 0, 1, 1
        self.__dict__.pop('glyph_stretch', None)
        self.__dict__.pop('_family_pivot_cache', None)
        self.children, self._type = glyphs, 'vgroup'

    def __getitem__(self, value):
        self._explode()
        return super().__getitem__(value)

    def __iter__(self):
        self._explode()
        return iter(self.split())

    def __len__(self):
        self._explode()
        return len(self.split())


class MarkupText(Text):
    """Pango-style markup for <b>, <i>, <span> colors/weights/styles and entities."""
    def __init__(self, text, **kwargs):
        import re, html
        plain, styles, stack, at = '', [], [{}], 0
        for match in re.finditer(r'<(/?)(\w+)([^>]*)>|([^<]+)', str(text)):
            closing, tag, attributes, content = match.groups()
            if content is not None:
                content = html.unescape(content)
                styles.extend([dict(stack[-1])] * len(content))
                plain += content
            elif closing:
                if len(stack) > 1:
                    stack.pop()
            else:
                style = dict(stack[-1])
                tag = tag.lower()
                if tag in ('b', 'bold'):
                    style['weight'] = BOLD
                elif tag in ('i', 'italic'):
                    style['slant'] = ITALIC
                elif tag == 'span':
                    for name, value in re.findall(r'(\w+)\s*=\s*["\']([^"\']*)["\']', attributes):
                        if name in ('foreground', 'fgcolor', 'color'):
                            style['color'] = value.upper() if value.startswith('#') else _PALETTE.get(value.upper(), value)
                        elif name in ('font_weight', 'weight') and value.upper() in globals():
                            style['weight'] = value.upper()
                        elif name in ('font_style', 'style') and value.upper() in (NORMAL, ITALIC, OBLIQUE):
                            style['slant'] = value.upper()
                        elif name in ('font', 'font_family', 'face'):
                            style['font'] = value
                elif tag not in ('u', 'small', 'big', 's', 'tt', 'sub', 'sup'):
                    raise NotImplementedError(f'MarkupText does not support <{tag}> in this preview')
                stack.append(style)
        super().__init__(plain, **kwargs)
        self.markup = str(text)
        if any(styles):
            self._explode()
            for glyph in self.children:
                for key, value in styles[glyph._char_index].items():
                    if key == 'color':
                        glyph.set_color(value)
                    else:
                        setattr(glyph, key, value)


def _number_text(number, options):
    if not isinstance(number, _REAL) or not math.isfinite(number):
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
        if (isinstance(num_decimal_places, bool) or not isinstance(num_decimal_places, numbers.Integral) or
                not 0 <= num_decimal_places <= 12):
            raise ValueError('num_decimal_places must be an integer from 0 to 12')
        if not all(isinstance(v, bool) for v in (include_sign, group_with_commas, show_ellipsis)):
            raise ValueError('Numeric formatting flags must be booleans')
        if unit is not None and (not isinstance(unit, str) or len(unit) > 256):
            raise ValueError('Numeric unit must be a string of at most 256 characters')
        if not isinstance(font_size, _REAL) or not math.isfinite(font_size) or font_size <= 0:
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
        if not isinstance(delta_t,_REAL):
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


_PART_CLASS = '\\class{manim-part-%d}{%s}'


def _reject_tex(value):
    raise TypeError('MathTex expects TeX strings or numbers')


def _class_wrap(piece, index):
    """Tag a tex piece in place: braces and ^/_ stay structural, balanced runs get the class."""
    out, buffer, i = [], '', 0
    def flush():
        nonlocal buffer
        if buffer.strip():
            out.append(_PART_CLASS % (index, buffer))
        else:
            out.append(buffer)
        buffer = ''
    def token(at):
        # One TeX token starting at `at`: a command, an escaped char, a braced group or a char.
        if piece[at] == '\\':
            end = at + 1
            while end < len(piece) and piece[end].isalpha():
                end += 1
            return piece[at:max(end, at + 2)]
        if piece[at] == '{':
            depth = 0
            for end in range(at, len(piece)):
                if piece[end] == '\\':
                    continue
                if piece[end] == '{' and (end == 0 or piece[end - 1] != '\\'):
                    depth += 1
                elif piece[end] == '}' and piece[end - 1] != '\\':
                    depth -= 1
                    if depth == 0:
                        return piece[at:end + 1]
            return None
        return piece[at]
    while i < len(piece):
        char = piece[i]
        if char in '^_':
            flush()
            out.append(char)
            i += 1
            while i < len(piece) and piece[i] == ' ':
                i += 1
            if i >= len(piece):
                break
            argument = token(i)
            if argument is None:
                continue  # An unmatched brace opens here; handled below.
            inner = argument[1:-1] if argument.startswith('{') else argument
            out.append('{' + _class_wrap(inner, index) + '}')
            i += len(argument)
            continue
        if char == '{':
            group = token(i)
            if group is None:
                flush()
                out.append('{')
                i += 1
                continue
            buffer += group
            i += len(group)
            continue
        if char == '}':
            flush()
            out.append('}')
            i += 1
            continue
        part = token(i)
        buffer += part
        i += len(part)
    flush()
    return ''.join(out)


class _MathTexPart(Text):
    """One tex string of a multi-part MathTex, drawn from the shared typeset formula."""
    def __init__(self, text, index, part_strings, font_size, **kwargs):
        super().__init__(text, font_size=font_size, **kwargs)
        self._type, self.part, self.part_strings = 'mathtex', index, list(part_strings)
        self.tex_string = part_strings[index]


class MathTex(Text):
    """Formulas rendered as SVG paths by MathJax; several strings become parts."""
    def __init__(self, *tex_strings, arg_separator=' ', substrings_to_isolate=None, tex_to_color_map=None,
                 font_size=48, tex_environment='align*', **kwargs):
        # Community converts non-string entries (e.g. matrix numbers) with str().
        tex_strings = tuple(value if isinstance(value, str) else str(value) for value in tex_strings
                            if isinstance(value, (str, numbers.Number)) or _reject_tex(value))
        if not isinstance(arg_separator, str):
            raise TypeError('MathTex expects TeX strings')
        if isinstance(font_size, bool) or not isinstance(font_size, _REAL) or not math.isfinite(font_size) or font_size <= 0:
            raise ValueError('MathTex font_size must be positive and finite')
        if tex_environment not in ('align*', None):
            raise NotImplementedError('MathTex environments other than align* are not supported')
        color_map = dict(tex_to_color_map or {})
        isolate = [s for s in list(substrings_to_isolate or []) + list(color_map) if s]
        parts = self._break_up(tex_strings, isolate)
        text = arg_separator.join(parts)
        if len(text) > 4096:
            raise ValueError('MathTex expressions are limited to 4096 characters')
        if len(parts) <= 1:
            super().__init__(text, font_size=font_size, **kwargs)
            self._type = 'mathtex'
            self.tex_string, self.tex_strings = text, [text]
        else:
            # Each part is tagged with \class so MathJax keeps TeX spacing while
            # the browser measures and draws every part separately.
            classed = arg_separator.join(_class_wrap(part, i) for i, part in enumerate(parts))
            super().__init__(classed, font_size=font_size, **kwargs)
            self._type = 'vgroup'
            self.tex_string, self.tex_strings = text, parts
            style = {key: kwargs[key] for key in kwargs
                     if key in ('color', 'fill_color', 'stroke_color', 'fill_opacity', 'stroke_width', 'stroke_opacity', 'z_index')}
            members = []
            for index, (cx, cy, _, _) in enumerate(_math_parts(classed, parts, font_size)):
                member = _MathTexPart(classed, index, parts, font_size, **style)
                members.append(member.move_to((cx, cy, 0)))
            self.add(*members)
        for tex, color in color_map.items():
            self.set_color_by_tex(tex, color)

    @staticmethod
    def _break_up(tex_strings, isolate):
        import re
        if not isolate:
            return [s for s in tex_strings if s] or ['']
        pattern = '(' + '|'.join(re.escape(s) for s in sorted(isolate, key=len, reverse=True)) + ')'
        return [piece for s in tex_strings for piece in re.split(pattern, s) if piece and piece.strip()] or ['']

    def _parts(self):
        return list(self.children) if self._type == 'vgroup' else [self]

    def __getitem__(self, value):
        if self._type != 'vgroup':
            return self._parts()[value] if not isinstance(value, slice) else VGroup(*self._parts()[value])
        return super().__getitem__(value)

    def __len__(self):
        return len(self._parts())

    def get_parts_by_tex(self, tex, substring=True, case_sensitive=True):
        def matches(part):
            a, b = (tex, part.tex_string) if case_sensitive else (tex.lower(), part.tex_string.lower())
            return a in b if substring else a == b
        return VGroup(*[part for part in self._parts() if matches(part)]) if self._type == 'vgroup' else (
            [self] if matches(self) else [])

    def get_part_by_tex(self, tex, **kwargs):
        parts = self.get_parts_by_tex(tex, **kwargs)
        return parts[0] if len(parts) else None

    def index_of_part_by_tex(self, tex, **kwargs):
        part = self.get_part_by_tex(tex, **kwargs)
        return -1 if part is None else self._parts().index(part)

    def set_color_by_tex(self, tex, color, **kwargs):
        for part in list(self.get_parts_by_tex(tex, **kwargs)):
            part.set_color(color)
        return self

    def set_color_by_tex_to_color_map(self, texs_to_color_map, **kwargs):
        for tex, color in texs_to_color_map.items():
            self.set_color_by_tex(tex, color, **kwargs)
        return self

    def set_opacity_by_tex(self, tex, opacity=0.5, remaining_opacity=None, **kwargs):
        if remaining_opacity is not None:
            self.set_opacity(remaining_opacity)
        for part in list(self.get_parts_by_tex(tex, **kwargs)):
            part.set_opacity(opacity)
        return self


SingleStringMathTex = MathTex


def _tex_text_to_math(text):
    """Typeset LaTeX text mode with MathJax: text runs become \\text{...}."""
    import re
    parts, math_mode, current, i = [], False, '', 0
    while i < len(text):
        char = text[i]
        if char == '\\' and i + 1 < len(text):
            current += text[i:i+2]
            i += 2
            continue
        if char == '$':
            parts.append((math_mode, current))
            current, math_mode = '', not math_mode
            i += 2 if text[i:i+2] == '$$' else 1
            continue
        current += char
        i += 1
    if math_mode:
        raise ValueError('Unbalanced $ in Tex string')
    parts.append((False, current))
    result = []
    for is_math, chunk in parts:
        if is_math:
            result.append(chunk)
            continue
        # Keep common font commands; everything else is literal text.
        for piece in re.split(r'(\\(?:textbf|textit|emph|texttt|textrm|textsf)\{[^{}]*\})', chunk):
            if not piece:
                continue
            command = re.match(r'\\(textbf|textit|emph|texttt|textrm|textsf)\{([^{}]*)\}', piece)
            if command:
                name = {'emph': 'textit'}.get(command.group(1), command.group(1))
                result.append('\\' + name + '{' + command.group(2) + '}')
            else:
                literal = piece.replace('\\\\', ' ').replace('~', ' ')
                literal = re.sub(r'\\([%&#_{}$])', r'\1', literal)
                if '\\' in literal or '{' in literal or '}' in literal:
                    raise NotImplementedError('Tex supports text, $math$ and basic font commands in this preview')
                result.append('\\text{' + literal + '}')
    return ''.join(result)


class Tex(MathTex):
    """LaTeX text mode (with $math$), typeset by MathJax as \\text runs."""
    def __init__(self, *tex_strings, arg_separator='', tex_environment='center', font_size=48, **kwargs):
        if tex_environment not in ('center', None):
            raise NotImplementedError('Tex environments other than center are not supported')
        if not all(isinstance(value, str) for value in (*tex_strings, arg_separator)):
            raise TypeError('Tex expects LaTeX strings')
        source = arg_separator.join(tex_strings)
        super().__init__(_tex_text_to_math(source), font_size=font_size, **kwargs)
        self.tex_string = source



class Group(Mobject):
    def __init__(self, *mobjects, **kwargs):
        super().__init__(**kwargs)
        self._type = 'vgroup'
        self.add(*mobjects)

    def get_group_class(self):
        return VGroup if isinstance(self,VGroup) else Group

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



class VGroup(Group):
    """Container for the supported vector/text geometry in this runtime."""
    pass


def _union_bounds(mobjects):
    if not all(isinstance(m, Mobject) for m in mobjects):
        raise TypeError('Expected all inputs for parameter mobjects to be Mobjects')
    if not mobjects:
        return 0, 0, 0, 0
    corners = [(m.get_critical_point(DL), m.get_critical_point(UR)) for m in mobjects]
    return (min(a[0] for a, _ in corners), min(a[1] for a, _ in corners),
            max(b[0] for _, b in corners), max(b[1] for _, b in corners))


class SurroundingRectangle(RoundedRectangle):
    """An axis-aligned rectangle around the current bounds of one or more mobjects."""
    def __init__(self, *mobjects, color=PURE_YELLOW, buff=SMALL_BUFF, corner_radius=0.0, **kwargs):
        left, bottom, right, top = _union_bounds(mobjects)
        buffs = tuple(buff) if isinstance(buff, (tuple, list)) else (buff, buff)
        if len(buffs) != 2:
            raise ValueError('buff must be a number or an (x, y) pair')
        for value in buffs:
            NumberLine._real(value, 'Surrounding buffer')
        width, height = right - left + 2 * buffs[0], top - bottom + 2 * buffs[1]
        radii = corner_radius if isinstance(corner_radius, (list, tuple)) else [corner_radius]
        if all(not isinstance(r, bool) and isinstance(r, _REAL) and r == 0 for r in radii):
            if any(not math.isfinite(v) or v < 0 for v in (width, height)):
                raise ValueError('Surrounding dimensions must be nonnegative and finite')
            Rectangle.__init__(self, width=width, height=height, color=color, **kwargs)
            self.corner_radius = copy.deepcopy(corner_radius)
        else:
            super().__init__(corner_radius=corner_radius, width=width, height=height, color=color, **kwargs)
        self.buff = copy.deepcopy(buff)
        self.move_to(((left + right) / 2, (bottom + top) / 2, 0))


class BackgroundRectangle(SurroundingRectangle):
    """A filled, stroke-free SurroundingRectangle in the background color."""
    def __init__(self, *mobjects, color=None, stroke_width=0, stroke_opacity=0, fill_opacity=0.75,
                 buff=0, **kwargs):
        super().__init__(*mobjects, color=config.background_color if color is None else color,
                         stroke_width=stroke_width, stroke_opacity=stroke_opacity,
                         fill_opacity=fill_opacity, buff=buff, **kwargs)
        self.original_fill_opacity = self.fill_opacity


class Cross(VGroup):
    """Two crossing lines, optionally stretched over a mobject's bounds."""
    def __init__(self, mobject=None, stroke_color=RED, stroke_width=6.0, scale_factor=1.0, **kwargs):
        super().__init__(Line(UP + LEFT, DOWN + RIGHT), Line(UP + RIGHT, DOWN + LEFT), **kwargs)
        if mobject is not None:
            self.replace(mobject, stretch=True)
        self.scale(scale_factor)
        self.set_stroke(color=stroke_color, width=stroke_width)


class Underline(Line):
    """A line matched to a mobject's width and placed below it."""
    def __init__(self, mobject, buff=SMALL_BUFF, **kwargs):
        if not isinstance(mobject, Mobject):
            raise TypeError('Underline expects a Mobject')
        super().__init__(LEFT, RIGHT, buff=buff, **kwargs)
        self.match_width(mobject)
        self.next_to(mobject, DOWN, buff=self.buff)



def _svg_path_curves(d):
    """Cubic curves from a relative/absolute SVG path using M, C, L, H, V and Z."""
    import re
    tokens = re.findall(r'[MmCcLlHhVvZz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?', d)
    curves, start, point, command, index = [], None, Vector(ORIGIN), None, 0
    def number():
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value
    def line_to(end):
        nonlocal point
        curves.append([list(point), list(point + (end - point) * (1/3)), list(point + (end - point) * (2/3)), list(end)])
        point = end
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
            if command in 'Zz':
                if start is not None and point != start:
                    line_to(start)
                point = start
                continue
        relative = command.islower()
        base = point if relative else Vector(ORIGIN)
        kind = command.upper()
        if kind == 'M':
            point = base + Vector((number(), number()))
            start = point
            command = 'l' if relative else 'L'
        elif kind == 'C':
            p1, p2, p3 = (base + Vector((number(), number())) for _ in range(3))
            curves.append([list(point), list(p1), list(p2), list(p3)])
            point = p3
        elif kind == 'L':
            line_to(base + Vector((number(), number())))
        elif kind == 'H':
            value = number()
            line_to(Vector((point[0] + value if relative else value, point[1])))
        elif kind == 'V':
            value = number()
            line_to(Vector((point[0], point[1] + value if relative else value)))
        else:
            raise ValueError('Unsupported SVG path command: ' + command)
    return curves


def _extent_points(mobject):
    """World points (or text box corners) that define a family's extent."""
    points = []
    for member in mobject.get_family():
        if member._type in ('text', 'mathtex'):
            points.extend(member.get_critical_point(d) for d in (UL, UR, DL, DR))
        elif member.has_points():
            # Community's get_points_defining_boundary uses anchors, not handles.
            points.extend(Vector(p) for i, p in enumerate(member.get_points()) if i % 4 in (0, 3))
    return points


class Brace(VMobject):
    """Community's brace outline, fitted below a mobject in any XY direction."""
    _TEMPLATE = ('m0.01216 0c-0.01152 0-0.01216 6.103e-4 -0.01216 0.01311v0.007762c0.06776 0.122 0.1799 0.1455 '
                 '0.2307 0.1455h{0}c0.03046 3.899e-4 0.07964 0.00449 0.1246 0.02636 0.0537 0.02695 0.07418 0.05816 '
                 '0.08648 0.07769 0.001562 0.002538 0.004539 0.002563 0.01098 0.002563 0.006444-2e-8 0.009421-2.47e-5 '
                 '0.01098-0.002563 0.0123-0.01953 0.03278-0.05074 0.08648-0.07769 0.04491-0.02187 0.09409-0.02597 '
                 '0.1246-0.02636h{0}c0.05077 0 0.1629-0.02346 0.2307-0.1455v-0.007762c-1.78e-6 -0.0125-6.365e-4 '
                 '-0.01311-0.01216-0.01311-0.006444-3.919e-8 -0.009348 2.448e-5 -0.01091 0.002563-0.0123 0.01953-0.03278 '
                 '0.05074-0.08648 0.07769-0.04491 0.02187-0.09416 0.02597-0.1246 0.02636h{1}c-0.04786 0-0.1502 0.02094'
                 '-0.2185 0.1256-0.06833-0.1046-0.1706-0.1256-0.2185-0.1256h{1}c-0.03046-3.899e-4 -0.07972-0.004491'
                 '-0.1246-0.02636-0.0537-0.02695-0.07418-0.05816-0.08648-0.07769-0.001562-0.002538-0.004467-0.002563'
                 '-0.01091-0.002563z')

    def __init__(self, mobject, direction=DOWN, buff=0.2, sharpness=2, stroke_width=0, fill_opacity=1.0,
                 background_stroke_width=0, background_stroke_color=BLACK, **kwargs):
        if not isinstance(mobject, Mobject):
            raise TypeError('Brace expects a Mobject')
        direction = Mobject._xy_vector(direction, 'Brace direction')
        if not any(direction):
            raise ValueError('Brace direction must be nonzero')
        for value, name in ((buff, 'Brace buff'), (sharpness, 'Brace sharpness')):
            NumberLine._real(value, name)
        super().__init__(stroke_width=stroke_width, fill_opacity=fill_opacity, **kwargs)
        self.buff = buff
        angle = -math.atan2(direction[0], direction[1]) + PI
        c, s_ = math.cos(-angle), math.sin(-angle)
        points = [Vector((p[0]*c - p[1]*s_, p[0]*s_ + p[1]*c, 0)) for p in _extent_points(mobject)]
        if not points:
            raise ValueError('Cannot brace a mobject with no extent')
        left = Vector((min(p[0] for p in points), min(p[1] for p in points), 0))
        right = Vector((max(p[0] for p in points), left[1], 0))
        target_width = right[0] - left[0]
        linear = max(0, (target_width * sharpness - 0.90552) / 2)
        curves = _svg_path_curves(self._TEMPLATE.format(linear, -linear))
        VMobject.set_points(self, [p for curve in curves for p in curve])
        self.flip(RIGHT)
        bottom = self.get_bottom()
        points = self.get_points()
        self._tip_point_index = min(range(len(points)), key=lambda i: math.dist(points[i][:2], bottom[:2]))
        self.stretch_to_fit_width(target_width)
        self.shift(left - self.get_corner(UL) + DOWN * self.buff)
        self.rotate(angle, about_point=ORIGIN)

    def get_tip(self):
        return Vector(self.get_points()[self._tip_point_index])

    def get_direction(self):
        vector = self.get_tip() - self.get_center()
        length = math.hypot(vector[0], vector[1])
        return vector * (1 / length) if length else Vector(DOWN)

    def put_at_tip(self, mob, use_next_to=True, **kwargs):
        if use_next_to:
            mob.next_to(self.get_tip(), Vector(round(v) for v in self.get_direction()), **kwargs)
        else:
            mob.move_to(self.get_tip())
            buff = kwargs.get('buff', DEFAULT_MOBJECT_TO_MOBJECT_BUFFER)
            mob.shift(self.get_direction() * (mob.get_width() / 2.0 + buff))
        return self

    def get_text(self, *text, **kwargs):
        label = Tex(*text)
        self.put_at_tip(label, **kwargs)
        return label

    def get_tex(self, *tex, **kwargs):
        label = MathTex(*tex)
        self.put_at_tip(label, **kwargs)
        return label


class BraceBetweenPoints(Brace):
    def __init__(self, point_1, point_2, direction=ORIGIN, **kwargs):
        start, end = Mobject._xy_vector(point_1, 'Brace point'), Mobject._xy_vector(point_2, 'Brace point')
        direction = Mobject._xy_vector(direction, 'Brace direction')
        if not any(direction):
            vector = end - start
            direction = Vector((vector[1], -vector[0], 0))
        super().__init__(Line(start, end), direction=direction, **kwargs)


class BraceLabel(VGroup):
    """A brace with a label at its tip."""
    def __init__(self, obj, text, brace_direction=DOWN, label_constructor=None, font_size=DEFAULT_FONT_SIZE,
                 buff=0.2, brace_config=None, **kwargs):
        self.label_constructor = MathTex if label_constructor is None else label_constructor
        super().__init__()
        self.brace_direction = brace_direction
        self.brace = Brace(obj, brace_direction, buff, **(brace_config or {}))
        if isinstance(text, (tuple, list)):
            self.label = self.label_constructor(*text, font_size=font_size, **kwargs)
        else:
            self.label = self.label_constructor(str(text), font_size=font_size)
        self.brace.put_at_tip(self.label)
        self.add(self.brace, self.label)

    def creation_anim(self, label_anim=None, brace_anim=None):
        label_anim = FadeIn if label_anim is None else label_anim
        brace_anim = GrowFromCenter if brace_anim is None else brace_anim
        return AnimationGroup(brace_anim(self.brace), label_anim(self.label))

    def shift_brace(self, obj, **kwargs):
        if isinstance(obj, list):
            obj = self.get_group_class()(*obj)
        brace = Brace(obj, self.brace_direction, **kwargs)
        self.brace.become(brace)
        self.brace._tip_point_index = brace._tip_point_index
        self.brace.put_at_tip(self.label)
        return self

    def change_label(self, *text, **kwargs):
        label = self.label_constructor(*text, **kwargs)
        self.brace.put_at_tip(label)
        self.label.become(label)
        return self

    def change_brace_label(self, obj, *text, **kwargs):
        self.shift_brace(obj)
        return self.change_label(*text, **kwargs)


class BraceText(BraceLabel):
    def __init__(self, obj, text, label_constructor=None, **kwargs):
        super().__init__(obj, text, label_constructor=Text if label_constructor is None else label_constructor, **kwargs)


class Title(VGroup):
    """Tex at the top edge with an optional full-width underline."""
    def __init__(self, *text_parts, include_underline=True, match_underline_width_to_text=False,
                 underline_buff=MED_SMALL_BUFF, **kwargs):
        super().__init__()
        self.text = Tex(*text_parts, **kwargs).to_edge(UP)
        self.add(self.text)
        if include_underline:
            underline = Line(LEFT, RIGHT).next_to(self.text, DOWN, buff=underline_buff)
            if match_underline_width_to_text:
                underline.match_width(self.text)
            else:
                underline.scale_to_fit_width(config.frame_width - 2)
            self.underline = underline
            self.add(underline)


class BulletedList(VGroup):
    """Tex items with bullet dots, arranged downward and left-aligned."""
    def __init__(self, *items, buff=MED_LARGE_BUFF, dot_scale_factor=2, tex_environment=None, **kwargs):
        super().__init__()
        for item in items:
            text = Tex(item, **kwargs)
            dot = MathTex('\\cdot').scale(dot_scale_factor).next_to(text, LEFT, SMALL_BUFF)
            self.add(VGroup(dot, text))
        self.arrange(DOWN, aligned_edge=LEFT, buff=buff)

    def fade_all_but(self, index_or_string, opacity=0.5):
        rows = list(self.children)
        if isinstance(index_or_string, str):
            matches = [i for i, row in enumerate(rows) if index_or_string in row[1].tex_string]
            if not matches:
                raise ValueError(f'Item not found: {index_or_string!r}')
            index_or_string = matches[0]
        for i, row in enumerate(rows):
            row.set_opacity(1 if i == index_or_string else opacity)
        return self


class VectorArrow(Arrow):
    """Community's Vector: an arrow from the origin, exported to scenes as Vector."""
    def __init__(self, direction=RIGHT, buff=0, **kwargs):
        direction = Mobject._xy_vector(direction, 'Vector direction')
        super().__init__(ORIGIN, direction, buff=buff, **kwargs)


class Paragraph(VGroup):
    """Lines of Text on Community's baseline pitch, left-aligned unless told otherwise."""
    def __init__(self, *text, line_spacing=-1, alignment=None, **kwargs):
        if alignment not in (None, 'left', 'center', 'right'):
            raise ValueError("alignment must be None, 'left', 'center' or 'right'")
        super().__init__()
        self.alignment = alignment
        lines = '\n'.join(str(t) for t in text).split('\n')
        font_size = kwargs.get('font_size', DEFAULT_FONT_SIZE)
        spacing = .3 if line_spacing == -1 else line_spacing
        pitch = font_size * (1 + spacing) * TEX_EM_PER_POINT
        self.lines_text = lines
        for index, line in enumerate(lines):
            mob = Text(line, line_spacing=line_spacing, **kwargs)
            layout = _text_layout(mob.__dict__)
            baseline = layout['lines'][0]['y'] if layout['lines'] else 0
            mob.move_to((0, -index * pitch - baseline, 0))
            mob._paragraph_left = layout['lines'][0]['x'] if layout['lines'] else 0
            self.add(mob)
        self._align(alignment or 'left')
        self.center()

    def _align(self, alignment):
        lines = list(self.children)
        if not lines:
            return
        if alignment == 'left':
            # Pango starts every line at the same pen position (not the ink edge).
            for line in lines:
                line.shift(RIGHT * (lines[0].get_center()[0] + lines[0]._paragraph_left - line.get_center()[0] - line._paragraph_left))
        elif alignment == 'center':
            for line in lines:
                line.set_x(lines[0].get_center()[0])
        else:
            right = max(line.get_right()[0] for line in lines)
            for line in lines:
                line.shift(RIGHT * (right - line.get_right()[0]))


class Table(VGroup):
    """Community's Table: entries on a grid with optional labels, lines and highlights."""
    def __init__(self, table, row_labels=None, col_labels=None, top_left_entry=None, v_buff=0.8, h_buff=1.3,
                 include_outer_lines=False, include_inner_lines=True, add_background_rectangles_to_entries=False,
                 entries_background_color=BLACK, include_background_rectangle=False,
                 background_rectangle_color=BLACK, element_to_mobject=None, element_to_mobject_config=None,
                 arrange_in_grid_config=None, line_config=None, **kwargs):
        data = [list(row) for row in table]
        if not data or not data[0]:
            raise ValueError('Table needs at least one row and column')
        if any(len(row) != len(data[0]) for row in data):
            raise ValueError('Not all rows in table have the same length.')
        if len(data) * len(data[0]) > 400:
            raise ValueError('Tables are limited to 400 entries in this preview')
        self.row_labels = list(row_labels) if row_labels else None
        self.col_labels = list(col_labels) if col_labels else None
        self.top_left_entry = top_left_entry
        self.row_dim, self.col_dim = len(data), len(data[0])
        self.v_buff, self.h_buff = v_buff, h_buff
        self.include_outer_lines, self.include_inner_lines = include_outer_lines, include_inner_lines
        self.line_config = dict(line_config or {})
        make = Paragraph if element_to_mobject is None else element_to_mobject
        options = dict(element_to_mobject_config or {})
        super().__init__(**kwargs)
        mob_table = [[make(item, **options) for item in row] for row in data]
        self.elements_without_labels = VGroup(*(mob for row in mob_table for mob in row))
        mob_table = self._add_labels(mob_table)
        grid = VGroup(*(mob for row in mob_table for mob in row))
        grid.arrange_in_grid(rows=len(mob_table), cols=len(mob_table[0]), buff=(h_buff, v_buff),
                             **dict(arrange_in_grid_config or {}))
        self.elements = VGroup(*(mob for row in mob_table for mob in row))
        if not self.elements[0]._painted_members():
            self.elements.remove(self.elements[0])
        self.add(self.elements)
        self.center()
        self.mob_table = mob_table
        self._add_horizontal_lines()
        self._add_vertical_lines()
        if add_background_rectangles_to_entries:
            self.add_background_to_entries(color=entries_background_color)
        if include_background_rectangle:
            self.add_background_rectangle(color=background_rectangle_color)

    def _add_labels(self, mob_table):
        if self.row_labels is not None:
            for k, label in enumerate(self.row_labels):
                mob_table[k] = [label] + mob_table[k]
        if self.col_labels is not None:
            if self.row_labels is not None:
                corner = self.top_left_entry if self.top_left_entry is not None else VMobject()
                mob_table.insert(0, [corner] + self.col_labels)
            else:
                mob_table.insert(0, list(self.col_labels))
        return mob_table

    def _line(self, start, end):
        line = Line(start, end, **self.line_config)
        self.add(line)
        return line

    def _add_horizontal_lines(self):
        left, right = self.get_left()[0] - .5 * self.h_buff, self.get_right()[0] + .5 * self.h_buff
        rows, group = self.get_rows(), VGroup()
        if self.include_outer_lines:
            for y in (rows[0].get_top()[1] + .5 * self.v_buff, rows[-1].get_bottom()[1] - .5 * self.v_buff):
                group.add(self._line((left, y, 0), (right, y, 0)))
        if self.include_inner_lines:
            for k in range(len(self.mob_table) - 1):
                y = rows[k + 1].get_top()[1] + .5 * (rows[k].get_bottom()[1] - rows[k + 1].get_top()[1])
                group.add(self._line((left, y, 0), (right, y, 0)))
        self.horizontal_lines = group
        return self

    def _add_vertical_lines(self):
        rows = self.get_rows()
        top, bottom = rows.get_top()[1] + .5 * self.v_buff, rows.get_bottom()[1] - .5 * self.v_buff
        columns, group = self.get_columns(), VGroup()
        if self.include_outer_lines:
            for x in (columns[0].get_left()[0] - .5 * self.h_buff, columns[-1].get_right()[0] + .5 * self.h_buff):
                group.add(self._line((x, top, 0), (x, bottom, 0)))
        if self.include_inner_lines:
            for k in range(len(self.mob_table[0]) - 1):
                x = columns[k + 1].get_left()[0] + .5 * (columns[k].get_right()[0] - columns[k + 1].get_left()[0])
                group.add(self._line((x, bottom, 0), (x, top, 0)))
        self.vertical_lines = group
        return self

    def get_horizontal_lines(self):
        return self.horizontal_lines

    def get_vertical_lines(self):
        return self.vertical_lines

    def get_columns(self):
        return VGroup(*(VGroup(*(row[i] for row in self.mob_table)) for i in range(len(self.mob_table[0]))))

    def get_rows(self):
        return VGroup(*(VGroup(*row) for row in self.mob_table))

    def set_column_colors(self, *colors):
        for color, column in zip(colors, self.get_columns()):
            column.set_color(color)
        return self

    def set_row_colors(self, *colors):
        for color, row in zip(colors, self.get_rows()):
            row.set_color(color)
        return self

    def get_entries(self, pos=None):
        if pos is None:
            return self.elements
        offset = 2 if self.row_labels is not None and self.col_labels is not None and self.top_left_entry is None else 1
        return self.elements[len(self.mob_table[0]) * (pos[0] - 1) + pos[1] - offset]

    def get_entries_without_labels(self, pos=None):
        if pos is None:
            return self.elements_without_labels
        return self.elements_without_labels[self.col_dim * (pos[0] - 1) + pos[1] - 1]

    def get_row_labels(self):
        return VGroup(*self.row_labels) if self.row_labels else VGroup()

    def get_col_labels(self):
        return VGroup(*self.col_labels) if self.col_labels else VGroup()

    def get_labels(self):
        group = VGroup()
        if self.top_left_entry is not None:
            group.add(self.top_left_entry)
        for labels in (self.col_labels, self.row_labels):
            if labels:
                group.add(*labels)
        return group

    def add_background_to_entries(self, color=BLACK):
        for mob in self.get_entries():
            mob.add_background_rectangle(color=color)
        return self

    def get_cell(self, pos=(1, 1), **kwargs):
        row, column = self.get_rows()[pos[0] - 1], self.get_columns()[pos[1] - 1]
        left, right = column.get_left()[0] - self.h_buff / 2, column.get_right()[0] + self.h_buff / 2
        top, bottom = row.get_top()[1] + self.v_buff / 2, row.get_bottom()[1] - self.v_buff / 2
        return Polygon((left, top, 0), (right, top, 0), (right, bottom, 0), (left, bottom, 0), **kwargs)

    def get_highlighted_cell(self, pos=(1, 1), color=PURE_YELLOW, **kwargs):
        return BackgroundRectangle(self.get_cell(pos), color=color, **kwargs)

    def add_highlighted_cell(self, pos=(1, 1), color=PURE_YELLOW, **kwargs):
        cell = self.get_highlighted_cell(pos, color=color, **kwargs)
        self.add_to_back(cell)
        self.get_entries(pos).background_rectangle = cell
        return self

    def create(self, lag_ratio=1, line_animation=None, label_animation=None, element_animation=None,
               entry_animation=None, **kwargs):
        line_animation = Create if line_animation is None else line_animation
        label_animation = Write if label_animation is None else label_animation
        element_animation = Create if element_animation is None else element_animation
        entry_animation = FadeIn if entry_animation is None else entry_animation
        animations = [line_animation(VGroup(self.vertical_lines, self.horizontal_lines), **kwargs),
                      element_animation(self.elements_without_labels.set_z_index(2), **kwargs)]
        if len(self.get_labels()):
            animations.append(label_animation(self.get_labels(), **kwargs))
        for entry in self.elements_without_labels:
            if isinstance(entry.__dict__.get('background_rectangle'), Mobject):
                animations.append(entry_animation(entry.background_rectangle, **kwargs))
        return AnimationGroup(*animations, lag_ratio=lag_ratio)

    def scale(self, scale_factor, scale_stroke=False, **kwargs):
        self.h_buff *= scale_factor
        self.v_buff *= scale_factor
        return super().scale(scale_factor, **kwargs)


class MathTable(Table):
    def __init__(self, table, element_to_mobject=None, **kwargs):
        super().__init__(table, element_to_mobject=MathTex if element_to_mobject is None else element_to_mobject, **kwargs)


class MobjectTable(Table):
    def __init__(self, table, element_to_mobject=None, **kwargs):
        super().__init__(table, element_to_mobject=(lambda m: m) if element_to_mobject is None else element_to_mobject,
                         **kwargs)


class IntegerTable(Table):
    def __init__(self, table, element_to_mobject=None, **kwargs):
        super().__init__(table, element_to_mobject=Integer if element_to_mobject is None else element_to_mobject, **kwargs)


class DecimalTable(Table):
    def __init__(self, table, element_to_mobject=None, element_to_mobject_config=None, **kwargs):
        super().__init__(table, element_to_mobject=DecimalNumber if element_to_mobject is None else element_to_mobject,
                         element_to_mobject_config={'num_decimal_places': 1} if element_to_mobject_config is None
                         else element_to_mobject_config, **kwargs)


def matrix_to_tex_string(matrix):
    rows = [list(row) if isinstance(row, (list, tuple)) or hasattr(row, '__iter__') else [row] for row in matrix]
    columns = len(rows[0]) if rows else 0
    body = ' \\\\ '.join(' & '.join(str(item) for item in row) for row in rows)
    return '\\left[ \\begin{array}{%s}' % ('c' * columns) + body + '\\end{array} \\right]'


def matrix_to_mobject(matrix):
    return MathTex(matrix_to_tex_string(matrix))


class Matrix(VGroup):
    """Entries on a grid between stretched TeX brackets, as in Community."""
    BRACKET_HEIGHT = 0.5977

    def __init__(self, matrix, v_buff=0.8, h_buff=1.3, bracket_h_buff=MED_SMALL_BUFF, bracket_v_buff=MED_SMALL_BUFF,
                 add_background_rectangles_to_entries=False, include_background_rectangle=False,
                 element_to_mobject=None, element_to_mobject_config=None, element_alignment_corner=DR,
                 left_bracket='[', right_bracket=']', stretch_brackets=True, bracket_config=None, **kwargs):
        rows = [list(row) for row in matrix]
        if not rows or any(len(row) != len(rows[0]) for row in rows) or not rows[0]:
            raise ValueError('Matrix needs a nonempty rectangular list of rows')
        if len(rows) * len(rows[0]) > 400:
            raise ValueError('Matrices are limited to 400 entries in this preview')
        super().__init__(**kwargs)
        self.v_buff, self.h_buff = v_buff, h_buff
        self.bracket_h_buff, self.bracket_v_buff = bracket_h_buff, bracket_v_buff
        self.element_alignment_corner = Mobject._xy_vector(element_alignment_corner, 'Alignment corner')
        make = MathTex if element_to_mobject is None else element_to_mobject
        config_ = dict(element_to_mobject_config or {})
        self.mob_matrix = [[make(item, **config_) for item in row] for row in rows]
        for i, row in enumerate(self.mob_matrix):
            for j, mob in enumerate(row):
                mob.move_to(DOWN * (i * v_buff) + RIGHT * (j * h_buff), self.element_alignment_corner)
        self.elements = VGroup(*(mob for row in self.mob_matrix for mob in row))
        self.add(self.elements)
        self._add_brackets(left_bracket, right_bracket, stretch_brackets, **dict(bracket_config or {}))
        self.center()
        if add_background_rectangles_to_entries:
            for mob in self.elements:
                mob.add_background_rectangle()
        if include_background_rectangle:
            self.add_background_rectangle()

    def _add_brackets(self, left, right, stretch, **kwargs):
        count = int(self.get_height() / self.BRACKET_HEIGHT) + 1
        empty = '\\begin{array}{c}' + '\\quad \\\\' * count + '\\end{array}'
        l_bracket = MathTex('\\left' + left + empty + '\\right.', **kwargs)
        r_bracket = MathTex('\\left.' + empty + '\\right' + right, **kwargs)
        pair = VGroup(l_bracket, r_bracket)
        if stretch:
            pair.stretch_to_fit_height(self.get_height() + 2 * self.bracket_v_buff)
        l_bracket.next_to(self, LEFT, self.bracket_h_buff)
        r_bracket.next_to(self, RIGHT, self.bracket_h_buff)
        self.brackets = pair
        self.add(l_bracket, r_bracket)
        return self

    def get_columns(self):
        return VGroup(*(VGroup(*(row[i] for row in self.mob_matrix)) for i in range(len(self.mob_matrix[0]))))

    def get_rows(self):
        return VGroup(*(VGroup(*row) for row in self.mob_matrix))

    def set_column_colors(self, *colors):
        for color, column in zip(colors, self.get_columns()):
            column.set_color(color)
        return self

    def set_row_colors(self, *colors):
        for color, row in zip(colors, self.get_rows()):
            row.set_color(color)
        return self

    def add_background_to_entries(self):
        for mob in self.get_entries():
            mob.add_background_rectangle()
        return self

    def get_mob_matrix(self):
        return self.mob_matrix

    def get_entries(self):
        return self.elements

    def get_brackets(self):
        return self.brackets


class DecimalMatrix(Matrix):
    def __init__(self, matrix, element_to_mobject=None, element_to_mobject_config=None, **kwargs):
        super().__init__(matrix, element_to_mobject=DecimalNumber if element_to_mobject is None else element_to_mobject,
                         element_to_mobject_config={'num_decimal_places': 1} if element_to_mobject_config is None
                         else element_to_mobject_config, **kwargs)


class IntegerMatrix(Matrix):
    def __init__(self, matrix, element_to_mobject=None, **kwargs):
        super().__init__(matrix, element_to_mobject=Integer if element_to_mobject is None else element_to_mobject, **kwargs)


class MobjectMatrix(Matrix):
    def __init__(self, matrix, element_to_mobject=None, **kwargs):
        super().__init__(matrix, element_to_mobject=(lambda m: m) if element_to_mobject is None else element_to_mobject,
                         **kwargs)


def get_det_text(matrix, determinant=None, background_rect=False, initial_scale_factor=2):
    parens = MathTex('(', ')')
    parens.scale(initial_scale_factor)
    parens.stretch_to_fit_height(matrix.get_height())
    l_paren, r_paren = parens
    l_paren.next_to(matrix, LEFT, buff=0.1)
    r_paren.next_to(matrix, RIGHT, buff=0.1)
    det = Tex('det').scale(initial_scale_factor).next_to(l_paren, LEFT, buff=0.1)
    if background_rect:
        det.add_background_rectangle()
    det_text = VGroup(det, l_paren, r_paren)
    if determinant is not None:
        eq = MathTex('=').next_to(r_paren, RIGHT, buff=0.1)
        result = MathTex(str(determinant)).next_to(eq, RIGHT, buff=0.2)
        det_text.add(eq, result)
    return det_text


class AnnotationDot(Dot):
    def __init__(self, radius=DEFAULT_DOT_RADIUS * 1.3, stroke_width=5, stroke_color=WHITE, fill_color=BLUE, **kwargs):
        super().__init__(radius=radius, stroke_width=stroke_width, stroke_color=stroke_color,
                         fill_color=fill_color, **kwargs)


class Label(VGroup):
    """A label with a background box and a thin frame."""
    def __init__(self, label, label_config=None, box_config=None, frame_config=None, **kwargs):
        super().__init__(**kwargs)
        label_config = {'color': WHITE, 'font_size': DEFAULT_FONT_SIZE} | dict(label_config or {})
        box_config = {'color': None, 'buff': 0.05, 'fill_opacity': 1, 'stroke_width': 0.5} | dict(box_config or {})
        frame_config = {'color': WHITE, 'buff': 0.05, 'stroke_width': 0.5} | dict(frame_config or {})
        if isinstance(label, str):
            self.rendered_label = MathTex(label, **label_config)
        elif isinstance(label, Text):
            self.rendered_label = label
        else:
            raise TypeError('Unsupported label type. Must be MathTex, Tex or Text.')
        self.background_rect = BackgroundRectangle(self.rendered_label, **box_config)
        self.frame = SurroundingRectangle(self.rendered_label, **frame_config)
        self.add(self.background_rect, self.rendered_label, self.frame)


class LabeledLine(Line):
    def __init__(self, label, label_position=0.5, label_config=None, box_config=None, frame_config=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        NumberLine._real(label_position, 'label_position')
        self.label = Label(label, label_config, box_config, frame_config)
        start, end = self.get_start_and_end()
        self.label.move_to(start + (end - start) * label_position)
        self.add(self._to_local_pose(self.label))


class LabeledArrow(LabeledLine, Arrow):
    pass


class LabeledDot(Dot):
    """A dot sized to hold a MathTex (or given) label at its center."""
    def __init__(self, label, radius=None, **kwargs):
        rendered = MathTex(label, color=BLACK) if isinstance(label, str) else label
        if not isinstance(rendered, Mobject):
            raise TypeError('LabeledDot label must be a string or Mobject')
        if radius is None:
            radius = 0.1 + max(rendered.get_width(), rendered.get_height()) / 2
        super().__init__(radius=radius, **kwargs)
        rendered.move_to(self.get_center())
        self.add(rendered)


class Variable(VGroup):
    """A label, an equals sign and a tracked DecimalNumber or Integer value."""
    def __init__(self, var, label, var_type=None, num_decimal_places=2, **kwargs):
        var_type = DecimalNumber if var_type is None else var_type
        label = MathTex(label) if isinstance(label, str) else label
        if not isinstance(label, Mobject):
            raise TypeError('Variable label must be a string or Mobject')
        equals = MathTex('=').next_to(label, RIGHT)
        self.label = VGroup(label, equals)
        self.tracker = ValueTracker(var)
        if var_type is Integer:
            self.value = Integer(self.tracker.get_value())
        elif var_type is DecimalNumber:
            self.value = DecimalNumber(self.tracker.get_value(), num_decimal_places=num_decimal_places)
        else:
            raise NotImplementedError('Variable supports DecimalNumber or Integer values')
        tracker = self.tracker
        self.value.add_updater(lambda v: v.set_value(tracker.get_value())).next_to(self.label, RIGHT)
        super().__init__(**kwargs)
        self.add(self.label, self.value)


class ArcPolygonFromArcs(VMobject):
    """Closed cubic outline with independently styled defining arc children."""

    def __init__(self, *arcs, **kwargs):
        if len(arcs) > 256 or any(not isinstance(arc,Arc) for arc in arcs):
            raise ValueError('Arc polygon needs at most 256 Arc objects')
        super().__init__(**kwargs)
        curves = []
        for arc in arcs:
            points = arc.get_points()
            if len(points)%4:
                raise ValueError('Arc polygon needs complete arc curves')
            incoming = [points[index:index+4] for index in range(0,len(points),4)]
            if not incoming:
                continue
            if curves:
                self._connect(curves,incoming[0][0])
                incoming[0][0] = curves[-1][-1][:]
            curves.extend(incoming)
        if curves:
            self._connect(curves,curves[0][0])
            curves[-1][-1] = curves[0][0][:]
        self.set_points([point for curve in curves for point in curve])
        self.add(*arcs)
        self._arc_polygon_outline = True

    @staticmethod
    def _connect(curves, end):
        start,end = Vector(curves[-1][-1]),Vector(end)
        if math.dist(start,end) <= 1e-9:
            curves[-1][-1] = list(end)
        else:
            curves.append([list(start),list(start+(end-start)*(1/3)),
                           list(start+(end-start)*(2/3)),list(end)])

    @property
    def arcs(self):
        return self.children


class ArcPolygon(ArcPolygonFromArcs):
    def __init__(self, *vertices, angle=PI/4, radius=None, arc_config=None, **kwargs):
        vertices = VMobject._corners(vertices)
        if not 2 <= len(vertices) <= 256:
            raise ValueError('Arc polygon requires 2 to 256 vertices')
        if arc_config is None:
            options = {'angle':angle} if radius is None else {'radius':radius}
            configs = [options]*len(vertices)
        elif isinstance(arc_config,dict):
            configs = [arc_config]*len(vertices)
        elif isinstance(arc_config,(list,tuple)) and len(arc_config)==len(vertices) and all(
                isinstance(options,dict) for options in arc_config):
            configs = arc_config
        else:
            raise ValueError('Arc configuration needs a dictionary or one dictionary per edge')
        arcs = [ArcBetweenPoints(start,vertices[(index+1)%len(vertices)],**dict(configs[index]))
                for index,start in enumerate(vertices)]
        super().__init__(*arcs,**kwargs)


class Elbow(VMobject):
    """An open two-segment corner, rotated about the origin."""
    def __init__(self, width=.2, angle=0, **kwargs):
        for value in (width, angle):
            if isinstance(value, bool) or not isinstance(value, _REAL) or not math.isfinite(value):
                raise ValueError('Elbow dimensions must be finite real numbers')
        if width < 0:
            raise ValueError('Elbow width must be nonnegative')
        super().__init__(**kwargs)
        self.set_points_as_corners([UP*width, (UP+RIGHT)*width, RIGHT*width])
        self.rotate(angle, about_point=ORIGIN)


class Angle(VMobject):
    """A snapshot arc/corner path, with the optional dot as a child."""
    def __init__(self, line1, line2, radius=None, quadrant=(1,1),
                 other_angle=False, dot=False, dot_radius=None, dot_distance=.55,
                 dot_color=WHITE, elbow=False, **kwargs):
        if not all(isinstance(line, Line) for line in (line1,line2)):
            raise TypeError('Angle requires two Lines')
        if not isinstance(quadrant,(tuple,list)) or len(quadrant) != 2 or any(
                isinstance(q,bool) or not isinstance(q, numbers.Integral) or q not in (-1,1) for q in quadrant):
            raise ValueError('Angle quadrant needs two signs, each -1 or 1')
        if not all(isinstance(value,bool) for value in (other_angle,dot,elbow)):
            raise ValueError('Angle flags must be booleans')
        for value in (radius,dot_radius,dot_distance):
            if value is not None and (isinstance(value,bool) or not isinstance(value,_REAL)
                    or not math.isfinite(value) or value < 0):
                raise ValueError('Angle radii and dot distance must be nonnegative and finite')
        if dot_distance is None:
            raise ValueError('Dot distance must be finite')
        super().__init__(**kwargs)
        self.set_points([])
        self._angle_lines = (line1,line2)
        self.quadrant, self.elbow, self.angle_value = tuple(quadrant), elbow, 0
        a,b = Line._endpoints(line1.get_start(),line1.get_end())
        c,d = Line._endpoints(line2.get_start(),line2.get_end())
        u,v = line1.get_unit_vector(),line2.get_unit_vector()
        cross = u[0]*v[1]-u[1]*v[0]
        if cross == 0:
            return
        delta = c-a
        distance = (delta[0]*v[1]-delta[1]*v[0])/cross
        intersection = a+u*distance
        if not all(math.isfinite(value) for value in intersection):
            raise ValueError('Angle intersection must be finite')
        if radius is None:
            nearest = min(math.dist(b if quadrant[0]==1 else a,intersection),
                          math.dist(d if quadrant[1]==1 else c,intersection))
            radius = nearest*2/3 if nearest < .6 else .4
        self.radius = radius
        first = intersection+u*(quadrant[0]*radius)
        last = intersection+v*(quadrant[1]*radius)
        start = math.atan2(u[1]*quadrant[0],u[0]*quadrant[0])
        end = math.atan2(v[1]*quadrant[1],v[0]*quadrant[1])
        sweep = (end-start)%TAU
        self.angle_value = sweep-TAU if other_angle else sweep
        if elbow:
            middle = first+v*(quadrant[1]*radius)
            mark = Elbow(**kwargs).set_points_as_corners([first,middle,last])
        else:
            mark = Arc(radius=radius,start_angle=start,angle=self.angle_value,
                       arc_center=intersection,**kwargs)
        self.set_points(mark.get_points())
        if dot and not elbow:
            offset = mark.get_center()-intersection
            span = math.hypot(*offset)
            anchor = intersection if span == 0 else intersection+Vector(
                value/span for value in offset)*(radius*dot_distance)
            self.add(Dot(anchor,radius=radius/10 if dot_radius is None else dot_radius,color=dot_color))

    @property
    def lines(self):
        return self._angle_lines

    def get_lines(self):
        return VGroup(*self.lines)

    def get_value(self, degrees=False):
        return self.angle_value/DEGREES if degrees else self.angle_value

    @staticmethod
    def from_three_points(A,B,C,**kwargs):
        return Angle(Line(B,A),Line(B,C),**kwargs)


class RightAngle(Angle):
    def __init__(self, line1, line2, length=None, **kwargs):
        super().__init__(line1,line2,radius=length,elbow=True,**kwargs)


class DashedVMobject(VMobject,VGroup):
    """Independent exact cubic dashes, spaced by approximate length or parameter."""
    def __init__(self, vmobject, num_dashes=15, dashed_ratio=.5, dash_offset=0,
                 color=WHITE, equal_lengths=True, **kwargs):
        if not isinstance(vmobject,Mobject) or vmobject._type not in (
                'polyline','polygon','bezierpath','circle','arc','ellipse',
                'square','rectangle','triangle','line','annulus'):
            raise TypeError('DashedVMobject needs a supported vector outline')
        if isinstance(num_dashes,bool) or not isinstance(num_dashes, numbers.Integral) or not 0 <= num_dashes <= 1000:
            raise ValueError('Dash count must be an integer from 0 to 1000')
        if isinstance(dashed_ratio,bool) or not isinstance(dashed_ratio,_REAL) or not math.isfinite(dashed_ratio) or not 0 <= dashed_ratio <= 1:
            raise ValueError('Dashed ratio must be finite and between 0 and 1')
        if isinstance(dash_offset,bool) or not isinstance(dash_offset,_REAL) or not math.isfinite(dash_offset):
            raise ValueError('Dash offset must be finite')
        if not isinstance(equal_lengths,bool):
            raise ValueError('Equal lengths must be a boolean')
        super().__init__(color=color,**kwargs)
        self._type = 'vgroup'
        self.num_dashes,self.dashed_ratio = num_dashes,dashed_ratio
        self.dash_offset,self.equal_lengths = dash_offset,equal_lengths
        # Children retain source styling, like Community's copied subcurves.
        for name in ('color','fill_color','stroke_color','fill_opacity','stroke_opacity','stroke_width'):
            setattr(self,name,copy.deepcopy(getattr(vmobject,name)))
        if not num_dashes:
            return
        source = vmobject.copy()
        closed = source.is_closed()
        dash = dashed_ratio/num_dashes
        gap = ((1-dashed_ratio)/num_dashes if closed else
               1-dashed_ratio if num_dashes == 1 else (1-dashed_ratio)/(num_dashes-1))
        period = dash+gap
        phase = (dash_offset % 1)*period
        intervals = []
        for index in range(num_dashes):
            a = index*period+phase
            b = a+dash
            if closed:
                start,end = a % 1,b % 1
                if b == 1:
                    end = 1
                intervals.append((start,end,dash == 1))
            else:
                if a <= 1:
                    intervals.append((a,min(1,b),False))
                if b > 1+gap:
                    intervals.append((0,min(1,b-(1+gap)),False))
        if equal_lengths:
            lengths,parameters = _curve_length_data(source,21)
            def parameter(alpha):
                if alpha <= 0 or not lengths[-1]:
                    return 0
                if alpha >= 1:
                    return 1
                distance = alpha*lengths[-1]
                index = min(bisect.bisect_right(lengths,distance)-1,len(lengths)-2)
                span = lengths[index+1]-lengths[index]
                fraction = (distance-lengths[index])/span if span else 0
                return parameters[index]+(parameters[index+1]-parameters[index])*fraction
        else:
            def parameter(alpha):
                return alpha
        for start,end,whole in intervals:
            a,b = parameter(start),parameter(end)
            if whole and a:
                child = source.get_subcurve(a,1)
                VMobject.append_vectorized_mobject(child,source.get_subcurve(0,a))
            elif whole:
                child = source.get_subcurve(0,1)
            else:
                child = source.get_subcurve(a,b)
            child._dash_interval = [a,b]
            self.children.append(child)


class DashedLine(Line,VGroup):
    """A straight line made from individually addressable dash segments."""
    def __init__(self, start=LEFT, end=RIGHT, dash_length=.05, dashed_ratio=.5, **kwargs):
        start,end = Line._endpoints(start,end)
        if isinstance(dash_length,bool) or not isinstance(dash_length,_REAL) or not math.isfinite(dash_length) or dash_length <= 0:
            raise ValueError('Dash length must be positive and finite')
        if isinstance(dashed_ratio,bool) or not isinstance(dashed_ratio,_REAL) or not math.isfinite(dashed_ratio) or not 0 <= dashed_ratio <= 1:
            raise ValueError('Dashed ratio must be finite and between 0 and 1')
        length = math.hypot(*(end-start))
        count = length/dash_length*dashed_ratio
        if not math.isfinite(count) or count > 1000:
            raise ValueError('DashedLine supports at most 1000 dashes')
        self.num_dashes = max(2,math.ceil(count))
        self.dash_length,self.dashed_ratio = dash_length,dashed_ratio
        super().__init__(start,end,**kwargs)
        self._type = 'vgroup'
        dash = dashed_ratio/self.num_dashes
        gap = (1-dashed_ratio)/(self.num_dashes-1)
        for index in range(self.num_dashes):
            a = index*(dash+gap)
            b = 1 if index == self.num_dashes-1 else a+dash
            child = Line(start+(end-start)*a,start+(end-start)*b,**kwargs)
            child._dash_interval = [a,b]
            self.children.append(child)

    def get_start(self):
        return self._point_to_world(self.children[0].get_start()) if self.children else Line.get_start(self)

    def get_end(self):
        return self._point_to_world(self.children[-1].get_end()) if self.children else Line.get_end(self)

    def get_first_handle(self):
        child = self.children[0]
        return self._point_to_world(child.get_start()+child.get_vector()*(1/3))

    def get_last_handle(self):
        child = self.children[-1]
        return self._point_to_world(child.get_end()-child.get_vector()*(1/3))

    def _calculate_num_dashes(self):
        count = self.get_length()/self.dash_length*self.dashed_ratio
        if not math.isfinite(count) or count > 1000:
            raise ValueError('DashedLine supports at most 1000 dashes')
        return max(2,math.ceil(count))

    def put_start_and_end_on(self, start, end):
        # Stretch the existing family; redraw is needed to recompute the count.
        start,end = Line._endpoints(start,end)
        old_start,old_end = self.get_start_and_end()
        old_length,new_length = math.dist(old_start,old_end),math.dist(start,end)
        if not all(math.isfinite(value) for value in (old_length,new_length)):
            raise ValueError('DashedLine endpoint spans must be finite')
        if any(not isinstance(child,Line) for child in self.children):
            raise TypeError('DashedLine endpoint changes require Line children')
        if old_length:
            old_unit = Vector(value/old_length for value in old_end-old_start)
            new_unit = Vector(value/new_length for value in end-start) if new_length else ORIGIN
            old_normal = Vector((-old_unit[1],old_unit[0],0))
            new_normal = Vector((-new_unit[1],new_unit[0],0))
            ratio = new_length/old_length
            def mapped(point):
                delta = self._point_to_world(point)-old_start
                along = sum(a*b for a,b in zip(delta,old_unit))*ratio
                across = sum(a*b for a,b in zip(delta,old_normal))*ratio
                return start+new_unit*along+new_normal*across
            endpoints = [(mapped(child.get_start()),mapped(child.get_end())) for child in self.children]
        else:
            endpoints = [(start+(end-start)*child._dash_interval[0],
                          start+(end-start)*child._dash_interval[1]) for child in self.children]
        center,scale = (start+end)*.5,self.geometry_scale or 1
        def local(point):
            dx,dy,_ = point-center
            return Vector(((dx*math.cos(self.angle)+dy*math.sin(self.angle))/scale,
                           (-dx*math.sin(self.angle)+dy*math.cos(self.angle))/scale,0))
        endpoints = [Line._endpoints(local(a),local(b)) for a,b in endpoints]
        for child,(a,b) in zip(self.children,endpoints):
            child.put_start_and_end_on(a,b)
        self.start,self.end = list(local(start)),list(local(end))
        self.geometry_scale = scale
        pivot = self._geometry_center()
        rotated = Vector((pivot[0]*math.cos(self.angle)-pivot[1]*math.sin(self.angle),
                          pivot[0]*math.sin(self.angle)+pivot[1]*math.cos(self.angle),0))*scale
        self.position = list(center-pivot+rotated)
        return self


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
                 numbers_to_include=None, label_constructor=None, **kwargs):
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
        self.label_constructor = MathTex if label_constructor is None else label_constructor
        self.numbers_with_elongated_ticks = self._numbers(numbers_with_elongated_ticks or [])
        self.numbers_to_exclude = self._numbers(numbers_to_exclude or [])
        self.numbers_to_include = None if numbers_to_include is None else self._numbers(numbers_to_include)
        # Community counts the digits after the step's printed decimal point (1.0 -> one place);
        # exponent notation keeps the significant fixed-point digits instead of collapsing to zero.
        step_text = str(values[2])
        decimals = (len(step_text.split('.')[-1]) if '.' in step_text and 'e' not in step_text.lower()
                    else len(format(values[2],'.12f').rstrip('0').split('.')[-1]))
        decimals = min(12, decimals)
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
        if (isinstance(value,bool) or not isinstance(value,_REAL) or not math.isfinite(value)
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
    get_slope = Line.get_slope
    set_angle = Line.set_angle

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

    get_projection = Line.get_projection

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
        # then let common family insertion preserve its bounding-box pivot.
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

    def polar_to_point(self, radius, azimuth):
        return self.coords_to_point(radius * math.cos(azimuth), radius * math.sin(azimuth))

    def pr2pt(self, radius, azimuth):
        return self.polar_to_point(radius, azimuth)

    def point_to_polar(self, point):
        x, y = self.point_to_coords(point)[:2]
        return math.hypot(x, y), math.atan2(y, x)

    def pt2pr(self, point):
        return self.point_to_polar(point)

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
        self._geometry_center()
        return self

    def get_x_axis_label(self, label, direction=UR, buff=.1, **kwargs):
        label = label if isinstance(label,Mobject) else MathTex(str(label))
        return label.next_to(self._point_to_world(self.x_axis.get_end()),direction,buff,**kwargs)

    def get_y_axis_label(self, label, direction=UR, buff=.1, **kwargs):
        label = label if isinstance(label,Mobject) else MathTex(str(label))
        return label.next_to(self._point_to_world(self.y_axis.get_end()),direction,buff,**kwargs)

    def get_axis_labels(self, x_label='x', y_label='y'):
        return VGroup(self.get_x_axis_label(x_label),self.get_y_axis_label(y_label))

    def get_line_from_axis_to_point(self, index, point, line_func=DashedLine,
                                    line_config=None, color=None, stroke_width=2):
        if isinstance(index,bool) or not isinstance(index, numbers.Integral) or index not in (0,1):
            raise ValueError('Axis index must be 0 or 1')
        point,_ = Line._endpoints(point,point)
        if not callable(line_func):
            raise TypeError('Guide line_func must be callable')
        if line_config is not None and not isinstance(line_config,dict):
            raise TypeError('Guide line_config must be a dictionary')
        options = dict(line_config or {})
        options.update(color=WHITE if color is None else color,stroke_width=stroke_width)
        Mobject._validate_width(stroke_width)
        axis = self.get_axis(index)
        world_axis = Line(self._point_to_world(axis.get_start()),self._point_to_world(axis.get_end()))
        line = line_func(world_axis.get_projection(point),point,**options)
        if not isinstance(line,Line):
            raise TypeError('Guide line_func must return a Line')
        return line

    def get_vertical_line(self, point, **kwargs):
        return self.get_line_from_axis_to_point(0,point,**kwargs)

    def get_horizontal_line(self, point, **kwargs):
        return self.get_line_from_axis_to_point(1,point,**kwargs)

    def get_lines_to_point(self, point, **kwargs):
        return VGroup(self.get_horizontal_line(point,**kwargs),self.get_vertical_line(point,**kwargs))

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
        if isinstance(samples,bool) or not isinstance(samples, numbers.Integral) or not 2 <= samples <= 10000:
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
            if isinstance(value,_REAL) and not isinstance(value,bool):
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
            return label._bounds()
        labels = [label for label in (dx_mob,df_mob) if label is not None]
        if labels:
            corners = [label_bounds(label) for label in labels]
            left,bottom = min(c[0] for c in corners),min(c[1] for c in corners)
            right,top = max(c[2] for c in corners),max(c[3] for c in corners)
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
                # Community leaves half the label height between label and line.
                label.next_to(line,direction,buff=(top-bottom)/2).set_color(line.color)
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


class BarChart(Axes):
    """Community's BarChart: bars on Axes with names, labels and value changes."""
    def __init__(self, values, bar_names=None, y_range=None, x_length=None, y_length=None,
                 bar_colors=('#003f5c', '#58508d', '#bc5090', '#ff6361', '#ffa600'), bar_width=0.6,
                 bar_fill_opacity=0.7, bar_stroke_width=3, **kwargs):
        values = list(values)
        if not values:
            raise ValueError('BarChart needs at least one value')
        for value in values:
            NumberLine._real(value, 'Bar value')
        y_length = config.frame_height - 4 if y_length is None else y_length
        self.values, self.bar_names, self.bar_colors = values, bar_names, list(bar_colors)
        self.bar_width, self.bar_fill_opacity, self.bar_stroke_width = bar_width, bar_fill_opacity, bar_stroke_width
        if y_range is None:
            y_range = [min(0, min(values)), max(0, max(values)), round(max(values) / y_length, 2)]
        elif len(y_range) == 2:
            y_range = [*y_range, round(max(values) / y_length, 2)]
        x_length = min(len(values), config.frame_width - 2) if x_length is None else x_length
        x_axis_config = {'font_size': 24, 'label_constructor': Tex} | dict(kwargs.pop('x_axis_config', None) or {})
        y_axis_config = {'include_numbers': True} | dict(kwargs.pop('y_axis_config', None) or {})
        super().__init__(x_range=[0, len(values), 1], y_range=y_range, x_length=x_length, y_length=y_length,
                         x_axis_config=x_axis_config, y_axis_config=y_axis_config, tips=kwargs.pop('tips', False),
                         **kwargs)
        self.bars = VGroup(*(self._create_bar(i, value) for i, value in enumerate(values)))
        self._update_colors()
        self.add_to_back(self.bars)
        self.x_labels = self.bar_labels = None
        if bar_names is not None:
            self._add_x_axis_labels()

    def _update_colors(self):
        self.bars.set_color_by_gradient(*self.bar_colors)

    def _add_x_axis_labels(self):
        labels = VGroup()
        axis = self.x_axis
        for i, name in enumerate(self.bar_names):
            label = axis.label_constructor(name, font_size=axis.font_size)
            label.next_to(axis.n2p(i + 0.5), UP if self.values[i] < 0 else DOWN, buff=axis.line_to_number_buff)
            labels.add(label)
        axis.labels = labels
        axis.add(labels)

    def _create_bar(self, bar_number, value):
        height = abs(self.c2p(0, value)[1] - self.c2p(0, 0)[1])
        width = self.c2p(self.bar_width, 0)[0] - self.c2p(0, 0)[0]
        bar = Rectangle(height=height, width=width, stroke_width=self.bar_stroke_width,
                        fill_opacity=self.bar_fill_opacity)
        return bar.next_to(self.c2p(bar_number + 0.5, 0), UP if value >= 0 else DOWN, buff=0)

    def get_bar_labels(self, color=None, font_size=24, buff=MED_SMALL_BUFF, label_constructor=None):
        make = Tex if label_constructor is None else label_constructor
        labels = VGroup()
        for bar, value in zip(self.bars, self.values):
            label = make(str(value), font_size=font_size)
            label.set_color(bar.get_fill_color() if color is None else color)
            labels.add(label.next_to(bar, UP if value >= 0 else DOWN, buff=buff))
        return labels

    def change_bar_values(self, values, update_colors=True):
        values = list(values)
        for i, (bar, value) in enumerate(zip(list(self.bars), values)):
            current = self.values[i]
            limit, edge = (bar.get_bottom(), DOWN) if current > 0 else (bar.get_top(), UP)
            if current != 0:
                quotient = value / current
                if quotient < 0:
                    edge = UP if current > 0 else DOWN
                bar.stretch_to_fit_height(abs(quotient) * bar.get_height())
            else:
                replacement = self._create_bar(i, value)
                bar.become(replacement)
            bar.move_to(limit, edge)
        if update_colors:
            self._update_colors()
        self.values[:len(values)] = values
        return self


class PolarPlane(Axes):
    """Community's PolarPlane: rings and spokes over radial axes, with azimuth labels."""
    def __init__(self, radius_max=None, size=None, radius_step=1, azimuth_step=None, azimuth_units='PI radians',
                 azimuth_compact_fraction=True, azimuth_offset=0, azimuth_direction='CCW',
                 azimuth_label_buff=SMALL_BUFF, azimuth_label_font_size=24, radius_config=None,
                 background_line_style=None, faded_line_style=None, faded_line_ratio=1,
                 make_smooth_after_applying_functions=True, **kwargs):
        if azimuth_units not in ('PI radians', 'TAU radians', 'degrees', 'gradians', None):
            raise ValueError('Invalid azimuth units. Expected one of: PI radians, TAU radians, degrees, gradians or None.')
        if azimuth_direction not in ('CW', 'CCW'):
            raise ValueError('Invalid azimuth direction. Expected one of: CW, CCW.')
        radius_max = config.frame_height / 2 if radius_max is None else radius_max
        NumberLine._real(radius_max, 'radius_max', positive=True)
        self.azimuth_units, self.azimuth_direction = azimuth_units, azimuth_direction
        self.azimuth_step = ({'PI radians': 20, 'TAU radians': 20, 'degrees': 36, 'gradians': 40, None: 1}[azimuth_units]
                             if azimuth_step is None else azimuth_step)
        NumberLine._real(self.azimuth_step, 'azimuth_step', positive=True)
        if self.azimuth_step * max(1, faded_line_ratio) > 720:
            raise ValueError('PolarPlane is limited to 720 azimuth lines')
        self.radius_config = {'stroke_width': 2, 'include_ticks': False, 'include_tip': False,
                              'line_to_number_buff': SMALL_BUFF, 'label_direction': DL, 'font_size': 24} | dict(radius_config or {})
        self.background_line_style = {'stroke_color': BLUE_D, 'stroke_width': 2, 'stroke_opacity': 1} | dict(background_line_style or {})
        self.faded_line_style, self.faded_line_ratio = faded_line_style, faded_line_ratio
        self.make_smooth_after_applying_functions = make_smooth_after_applying_functions
        self.azimuth_offset, self.azimuth_label_buff = azimuth_offset, azimuth_label_buff
        self.azimuth_label_font_size, self.azimuth_compact_fraction = azimuth_label_font_size, azimuth_compact_fraction
        # Community passes size=None through to unit-length radial axes.
        size = 2 * radius_max if size is None else size
        # Community builds a NumPy range, promoting every bound to float when any bound is a float.
        bounds = [-radius_max, radius_max, radius_step]
        if any(isinstance(value, float) for value in bounds):
            bounds = [float(value) for value in bounds]
        super().__init__(x_range=bounds, y_range=bounds[:],
                         x_length=size, y_length=size, axis_config=self.radius_config, **kwargs)
        if self.faded_line_style is None:
            self.faded_line_style = {key: value * .5 if isinstance(value, _REAL) and not isinstance(value, bool) else value
                                     for key, value in self.background_line_style.items()}
        background, faded = self._get_lines()
        background.set_style(**self.background_line_style)
        faded.set_style(**self.faded_line_style)
        background._plane_role, faded._plane_role = 'background', 'faded'
        self.add_to_back(faded, background)

    def _get_lines(self):
        center = self.get_origin()
        ratio = self.faded_line_ratio or 1
        rstep = self.x_axis.x_range[2] / ratio
        astep = TAU / self.azimuth_step / ratio
        rings, faded_rings, spokes, faded_spokes = VGroup(), VGroup(), VGroup(), VGroup()
        count = int(math.floor(self.x_axis.x_range[1] / rstep + 1e-9)) + 1
        for k in range(count):
            circle = Circle(radius=k * rstep * self.x_axis.get_unit_size()).move_to(center)
            (rings if k % ratio == 0 else faded_rings).add(circle)
        spoke = Line(center, self.get_x_axis().get_end())
        for k in range(int(math.ceil(TAU / astep - 1e-9))):
            line = spoke.copy().rotate(k * astep + self.azimuth_offset, about_point=center)
            (spokes if k % ratio == 0 else faded_spokes).add(line)
        return VGroup(*spokes, *rings), VGroup(*faded_spokes, *faded_rings)

    def _plane_group(self, role):
        for child in self.children:
            if child.__dict__.get('_plane_role') == role:
                return child
        raise ValueError('PolarPlane has no ' + role + ' lines')

    @property
    def background_lines(self):
        return self._plane_group('background')

    @property
    def faded_lines(self):
        return self._plane_group('faded')

    def get_vector(self, coords, **kwargs):
        kwargs['buff'] = 0
        return Arrow(self.coords_to_point(0, 0), self.coords_to_point(*coords), **kwargs)

    def get_radian_label(self, number, font_size=24, **kwargs):
        from fractions import Fraction
        constant = {'PI radians': '\\pi', 'TAU radians': '\\tau'}[self.azimuth_units]
        frac = Fraction(number * {'PI radians': 2, 'TAU radians': 1}[self.azimuth_units]).limit_denominator(100)
        if frac.numerator == 0:
            string = '0'
        elif frac.numerator == 1 and frac.denominator == 1:
            string = constant
        elif frac.numerator == 1:
            string = ('\\tfrac{' + constant + '}{' + str(frac.denominator) + '}' if self.azimuth_compact_fraction
                      else '\\tfrac{1}{' + str(frac.denominator) + '}' + constant)
        elif frac.denominator == 1:
            string = str(frac.numerator) + constant
        elif self.azimuth_compact_fraction:
            string = '\\tfrac{' + str(frac.numerator) + constant + '}{' + str(frac.denominator) + '}'
        else:
            string = '\\tfrac{' + str(frac.numerator) + '}{' + str(frac.denominator) + '}' + constant
        return MathTex(string, font_size=font_size, **kwargs)

    def get_coordinate_labels(self, r_values=None, a_values=None, **kwargs):
        if r_values is None:
            r_values = [r for r in self.get_x_axis().get_tick_range() if r >= 0]
        if a_values is None:
            a_values = [i / self.azimuth_step for i in range(int(math.ceil(self.azimuth_step - 1e-9)))]
        r_mobs = self.get_x_axis().add_numbers(r_values)
        sign = 1 if self.azimuth_direction == 'CCW' else -1
        reach = self.get_right()[0]
        labels = []
        for value in a_values:
            angle = sign * value * TAU + self.azimuth_offset
            point = Vector((reach * math.cos(angle), reach * math.sin(angle), 0))
            if self.azimuth_units in ('PI radians', 'TAU radians'):
                label = self.get_radian_label(value, font_size=self.azimuth_label_font_size)
            else:
                factor, suffix = {'degrees': (360, '^{\\circ}'), 'gradians': (400, '^{g}'), None: (1, '')}[self.azimuth_units]
                label = MathTex(f'{factor * value:g}' + suffix, font_size=self.azimuth_label_font_size)
            labels.append(label.next_to(point, direction=point, aligned_edge=point, buff=self.azimuth_label_buff))
        self.coordinate_labels = VGroup(r_mobs, VGroup(*labels))
        return self.coordinate_labels

    def add_coordinates(self, r_values=None, a_values=None):
        # Community's label group repeats x_axis (add_numbers returns it), and its family
        # deduplication renders that axis once. Attach only the new azimuth labels here.
        return self.add(self.get_coordinate_labels(r_values, a_values)[1])


class NumberPlane(Axes):
    """A linear Cartesian grid using the same local coordinates as its axes."""
    def __init__(self, x_range=None, y_range=None, x_length=None, y_length=None,
                 background_line_style=None, faded_line_style=None, faded_line_ratio=1,
                 make_smooth_after_applying_functions=True, **kwargs):
        if isinstance(faded_line_ratio,bool) or not isinstance(faded_line_ratio, numbers.Integral) or faded_line_ratio < 0:
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
        faded = ({key: value*.5 if isinstance(value,_REAL) and not isinstance(value,bool) else value
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
        return Arrow(start,end,buff=0,**kwargs)


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
            offset = label._pivot_point()-Vector(self.position)-center
            local = center+Vector((offset[0]*math.cos(self.angle)+offset[1]*math.sin(self.angle),
                                   -offset[0]*math.sin(self.angle)+offset[1]*math.cos(self.angle),0))*(1/self.geometry_scale)
            label.shift(local-label._pivot_point())
            label.angle -= self.angle
            label.geometry_scale /= self.geometry_scale
        self.add(labels)
        del self._coordinate_labels
        self._geometry_center()
        return self


# Community rate functions (manim.utils.rate_functions), including clamping.
def _unit_interval(function):
    def wrapper(t, *args, **kwargs):
        return function(t, *args, **kwargs) if 0 <= t <= 1 else (0 if t < 0 else 1)
    wrapper.__name__ = function.__name__
    return wrapper


def _zero(function):
    def wrapper(t, *args, **kwargs):
        return function(t, *args, **kwargs) if 0 <= t <= 1 else 0
    wrapper.__name__ = function.__name__
    return wrapper


def sigmoid(x):
    return 1.0 / (1 + math.exp(-x))


@_unit_interval
def linear(t):
    return t


@_unit_interval
def smooth(t, inflection=10.0):
    error = sigmoid(-inflection / 2)
    return min(max((sigmoid(inflection * (t - 0.5)) - error) / (1 - 2 * error), 0), 1)


@_unit_interval
def smoothstep(t):
    return 3 * t ** 2 - 2 * t ** 3


@_unit_interval
def smootherstep(t):
    return 6 * t ** 5 - 15 * t ** 4 + 10 * t ** 3


@_unit_interval
def smoothererstep(t):
    return 35 * t ** 4 - 84 * t ** 5 + 70 * t ** 6 - 20 * t ** 7


@_unit_interval
def rush_into(t, inflection=10.0):
    return 2 * smooth(t / 2.0, inflection)


@_unit_interval
def rush_from(t, inflection=10.0):
    return 2 * smooth(t / 2.0 + 0.5, inflection) - 1


@_unit_interval
def slow_into(t):
    return math.sqrt(1 - (1 - t) * (1 - t))


@_unit_interval
def double_smooth(t):
    return 0.5 * smooth(2 * t) if t < 0.5 else 0.5 * (1 + smooth(2 * t - 1))


@_zero
def there_and_back(t, inflection=10.0):
    return smooth(2 * t if t < 0.5 else 2 * (1 - t), inflection)


@_zero
def there_and_back_with_pause(t, pause_ratio=1.0 / 3):
    a = 2.0 / (1.0 - pause_ratio)
    if t < 0.5 - pause_ratio / 2:
        return smooth(a * t)
    if t < 0.5 + pause_ratio / 2:
        return 1
    return smooth(a - a * t)


@_unit_interval
def running_start(t, pull_factor=-0.5):
    mt = 1 - t
    return (15 * t**2 * mt**4 * pull_factor + 20 * t**3 * mt**3 * pull_factor +
            15 * t**4 * mt**2 + 6 * t**5 * mt + t**6)


def not_quite_there(func=smooth, proportion=0.7):
    def result(t, *args, **kwargs):
        return proportion * func(t, *args, **kwargs)
    return result


@_zero
def wiggle(t, wiggles=2):
    return there_and_back(t) * math.sin(wiggles * math.pi * t)


def squish_rate_func(func, a=0.4, b=0.6):
    def result(t, *args, **kwargs):
        if a == b:
            return a
        new_t = 0.0 if t < a else 1.0 if t > b else (t - a) / (b - a)
        return func(new_t, *args, **kwargs)
    return result


@_unit_interval
def lingering(t):
    return squish_rate_func(lambda t: t, 0, 0.8)(t)


@_unit_interval
def exponential_decay(t, half_life=0.1):
    return 1 - math.exp(-t / half_life)


def _ease_functions():
    sqrt, c1 = math.sqrt, 1.70158
    def bounce_out(t):
        n1, d1 = 7.5625, 2.75
        if t < 1 / d1:
            return n1 * t * t
        if t < 2 / d1:
            return n1 * (t - 1.5 / d1) ** 2 + 0.75
        if t < 2.5 / d1:
            return n1 * (t - 2.25 / d1) ** 2 + 0.9375
        return n1 * (t - 2.625 / d1) ** 2 + 0.984375
    c4, c5 = 2 * math.pi / 3, 2 * math.pi / 4.5
    functions = {
        'ease_in_sine': lambda t: 1 - math.cos(t * math.pi / 2),
        'ease_out_sine': lambda t: math.sin(t * math.pi / 2),
        'ease_in_out_sine': lambda t: -(math.cos(math.pi * t) - 1) / 2,
        'ease_in_quad': lambda t: t * t,
        'ease_out_quad': lambda t: 1 - (1 - t) * (1 - t),
        'ease_in_out_quad': lambda t: 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2,
        'ease_in_cubic': lambda t: t ** 3,
        'ease_out_cubic': lambda t: 1 - (1 - t) ** 3,
        'ease_in_out_cubic': lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2,
        'ease_in_quart': lambda t: t ** 4,
        'ease_out_quart': lambda t: 1 - (1 - t) ** 4,
        'ease_in_out_quart': lambda t: 8 * t ** 4 if t < 0.5 else 1 - (-2 * t + 2) ** 4 / 2,
        'ease_in_quint': lambda t: t ** 5,
        'ease_out_quint': lambda t: 1 - (1 - t) ** 5,
        'ease_in_out_quint': lambda t: 16 * t ** 5 if t < 0.5 else 1 - (-2 * t + 2) ** 5 / 2,
        'ease_in_expo': lambda t: 0 if t == 0 else 2 ** (10 * t - 10),
        'ease_out_expo': lambda t: 1 if t == 1 else 1 - 2 ** (-10 * t),
        'ease_in_out_expo': lambda t: (0 if t == 0 else 1 if t == 1 else 2 ** (20 * t - 10) / 2
                                       if t < 0.5 else (2 - 2 ** (-20 * t + 10)) / 2),
        'ease_in_circ': lambda t: 1 - sqrt(1 - t ** 2),
        'ease_out_circ': lambda t: sqrt(1 - (t - 1) ** 2),
        'ease_in_out_circ': lambda t: ((1 - sqrt(1 - (2 * t) ** 2)) / 2 if t < 0.5
                                       else (sqrt(1 - (-2 * t + 2) ** 2) + 1) / 2),
        'ease_in_back': lambda t: (c1 + 1) * t ** 3 - c1 * t * t,
        'ease_out_back': lambda t: 1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2,
        'ease_in_out_back': lambda t: ((2 * t) ** 2 * ((c1 * 1.525 + 1) * 2 * t - c1 * 1.525) / 2 if t < 0.5 else
                                       ((2 * t - 2) ** 2 * ((c1 * 1.525 + 1) * (t * 2 - 2) + c1 * 1.525) + 2) / 2),
        'ease_in_elastic': lambda t: (0 if t == 0 else 1 if t == 1 else
                                      -2 ** (10 * t - 10) * math.sin((t * 10 - 10.75) * c4)),
        'ease_out_elastic': lambda t: (0 if t == 0 else 1 if t == 1 else
                                       2 ** (-10 * t) * math.sin((t * 10 - 0.75) * c4) + 1),
        'ease_in_out_elastic': lambda t: (0 if t == 0 else 1 if t == 1 else
                                          -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2 if t < 0.5 else
                                          2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c5) / 2 + 1),
        'ease_in_bounce': lambda t: 1 - bounce_out(1 - t),
        'ease_out_bounce': bounce_out,
        'ease_in_out_bounce': lambda t: ((1 - bounce_out(1 - 2 * t)) / 2 if t < 0.5
                                         else (1 + bounce_out(2 * t - 1)) / 2),
    }
    result = {}
    for name, function in functions.items():
        function.__name__ = name
        result[name] = _unit_interval(function)
    return result


globals().update(_ease_functions())
rate_functions = types.SimpleNamespace(**{name: globals()[name] for name in (
    'linear', 'smooth', 'smoothstep', 'smootherstep', 'smoothererstep', 'rush_into', 'rush_from',
    'slow_into', 'double_smooth', 'there_and_back', 'there_and_back_with_pause', 'running_start',
    'not_quite_there', 'wiggle', 'squish_rate_func', 'lingering', 'exponential_decay', 'sigmoid',
    *_ease_functions())})


def interpolate(start, end, alpha):
    if isinstance(start, _REAL) and isinstance(end, _REAL):
        return start + (end - start) * alpha
    if isinstance(start, list) and isinstance(end, list) and len(start) == len(end):
        return [interpolate(a, b, alpha) for a, b in zip(start, end)]
    if isinstance(start, dict) and isinstance(end, dict):
        result = {key: interpolate(value, end.get(key, value), alpha)
                  for key, value in start.items()}
        # Tip roles identify aligned child slots, rather than animated values.
        if '_tip_role' in end:
            result['_tip_role'] = end['_tip_role']
        for key in ('part', 'part_strings'):
            if key in start or key in end:
                result[key] = copy.deepcopy(end.get(key) if alpha >= 1 or key not in start else start[key])
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


def _refresh_tip_shafts(snapshot):
    for child in snapshot.get('children',[]):
        _refresh_tip_shafts(child)
    curved = snapshot.get('_curved_tip_path') and snapshot['type'] == 'bezierpath'
    if snapshot['type'] not in ('line','arrow') and not curved:
        return snapshot
    snapshot.pop('shaft_start',None)
    snapshot.pop('shaft_end',None)
    for child in snapshot.get('children',[]):
        role = child.get('_tip_role')
        if role not in ('start','end'):
            continue
        curves = _path_curves(child)
        if not curves:
            continue
        index = len(curves)/2
        point = VMobject._bezier_point(curves[min(int(index),len(curves)-1)],index-int(index))
        tip = Mobject()
        tip.__dict__.update(child)
        tip._type = child['type']
        tip._sampled_geometry_center = Vector(child['geometry_center'])
        tip.children = []
        snapshot['shaft_'+role] = list(tip._point_to_world(point))
    if curved:
        curves = snapshot['curves']
        snapshot['shaft_curves'] = (_fit_curve_endpoints(curves,
            snapshot.get('shaft_start',curves[0][0]),snapshot.get('shaft_end',curves[-1][-1]))
            if curves else [])
    return snapshot


def _fit_curve_endpoints(curves, start, end):
    first,last = Vector(curves[0][0]),Vector(curves[-1][-1])
    start,end = Vector(start),Vector(end)
    old,new = last-first,end-start
    length = math.hypot(*old)
    if not length:
        return copy.deepcopy(curves)
    unit = Vector(value/length for value in old)
    real = new[0]*unit[0]+new[1]*unit[1]
    imag = new[1]*unit[0]-new[0]*unit[1]
    def point(value):
        x,y,_ = Vector(value)-first
        x,y = x/length,y/length
        return list(start+Vector((real*x-imag*y,imag*x+real*y,0)))
    return [[point(value) for value in curve] for curve in curves]


def _path_curves(snapshot):
    kind = snapshot['type']
    if kind == 'bezierpath':
        return _snapshot_copy(snapshot.get('shaft_curves',snapshot['curves']))
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
    elif kind in ('line','arrow'):
        vertices = [snapshot.get('shaft_start',snapshot['start']), snapshot.get('shaft_end',snapshot['end'])]
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
                  'square', 'rectangle', 'triangle', 'line', 'arrow', 'annulus')
    if any(snapshot['type']=='arrow' and not snapshot.get('explicit_tips') for snapshot in (start,target)):
        return None
    if start['type'] not in path_types or target['type'] not in path_types:
        return None
    if start['type'] == target['type'] and start['type'] not in ('polyline', 'polygon', 'bezierpath'):
        return None  # Matching primitives retain their analytical interpolation.
    # Align untrimmed curved-arrow geometry; capture fits it to sampled tips.
    start,target = copy.deepcopy(start),copy.deepcopy(target)
    for snapshot in (start,target):
        if snapshot.get('_curved_tip_path'):
            snapshot.pop('shaft_curves',None)
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
    if start.get('children') or target.get('children'):
        own_start,own_target = copy.deepcopy(start),copy.deepcopy(target)
        own_start['children'],own_target['children'] = [],[]
        first,last = VGroup().to_dict(),VGroup().to_dict()
        first['children'],last['children'] = start['children'],target['children']
        if start.get('_arc_polygon_outline') or target.get('_arc_polygon_outline'):
            def outline(snapshot):
                source = Mobject()
                source.__dict__.update(copy.deepcopy(snapshot))
                source._type = snapshot['type']
                source.children = []
                source._sampled_geometry_center = Vector(snapshot['geometry_center'])
                points = source.get_points()
                result = copy.deepcopy(snapshot)
                result.update(type='bezierpath',curves=[points[i:i+4] for i in range(0,len(points),4)],
                              vertices=[],position=list(ORIGIN),angle=0,geometry_scale=1,
                              geometry_center=list(ORIGIN))
                return result
            first['children'] = [outline(child) for child in first['children']]
            last['children'] = [outline(child) for child in last['children']]
        return ('family' ,start,target,[_transform_plan(own_start,own_target),
                                      _transform_plan(first,last)])
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
    if kind == 'family':
        own = _sample_transform(children[0],alpha)
        members = _sample_transform(children[1],alpha)[0]['children']
        own[0]['children'] = members
        return own
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


def _painted_paths(data, path=(), nested=True):
    """Preorder paths of drawable family members (Community's family_members_with_points)."""
    painted = data['type'] not in ('vgroup', 'mobject', 'valuetracker')
    result = [path] if painted else []
    if nested or not painted:
        for index, child in enumerate(data.get('children', [])):
            result += _painted_paths(child, path + (index,), nested)
    return result


class Animation:
    def __init__(self, mobject, run_time=1, rate_func=smooth, lag_ratio=0, remover=False,
                 introducer=False, name=None, suspend_mobject_updating=True, reverse_rate_function=False):
        if isinstance(lag_ratio, bool) or not isinstance(lag_ratio, _REAL) or not math.isfinite(lag_ratio) or lag_ratio < 0:
            raise ValueError('lag_ratio must be nonnegative and finite')
        if not callable(rate_func):
            raise TypeError('rate_func must be callable')
        self.reverse_rate_function = bool(reverse_rate_function)
        self.mobject, self.run_time, self.rate_func = mobject, run_time, rate_func
        self.lag_ratio, self.remover, self.introducer, self.name = lag_ratio, bool(remover), introducer, name

    def _member_states(self, data, alpha, rate_func, member, nested=True):
        """Apply member(node, sub_alpha) to drawable members with Community's lag timing."""
        paths = _painted_paths(data, nested=nested)
        full = (len(paths) - 1) * self.lag_ratio + 1 if paths else 1
        order = {path: index for index, path in enumerate(paths)}
        def visit(node, path):
            if path in order:
                local = max(0, min(1, alpha * full - order[path] * self.lag_ratio))
                member(node, rate_func(local), path)
                if not nested:
                    return
            for index, child in enumerate(node.get('children', [])):
                visit(child, path + (index,))
        visit(data, ())
        return data

    def _complete(self, scene):
        self.finish(scene)
        if self.remover:
            scene.remove(self.mobject)

    def begin(self, scene):
        scene._introduce(self.mobject)
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
        terminal._complete(staging)
        self._terminal = [m.to_dict() for m in staging.mobjects]

    def states(self, alpha, rate_func=None):
        rate = rate_func or self.rate_func
        if self.reverse_rate_function:
            # Like Community, reversal also applies to a play() rate override.
            forward = rate
            rate = lambda t: forward(1 - t)
        if alpha >= 1:
            result = self._terminal
        elif getattr(self, '_lagged', False):
            # Lagged members apply the rate function to their own sub-alphas.
            result = self.sample_members(max(0, alpha), rate)
        else:
            result = self.sample(rate(max(0, alpha)))
        return {self.mobject: result}


def _faded_group(mobjects, name):
    if not mobjects:
        raise ValueError('At least one mobject must be passed to ' + name)
    if any(not isinstance(m, Mobject) for m in mobjects):
        raise TypeError(name + ' expects Mobjects')
    return mobjects[0] if len(mobjects) == 1 else Group(*mobjects)


class FadeIn(Animation):
    """Fade in, optionally from a shift, a starting position and a scale."""
    _fading_in = True

    def __init__(self, *mobjects, shift=None, target_position=None, scale=1, **kwargs):
        super().__init__(_faded_group(mobjects, type(self).__name__), **kwargs)
        if shift is not None:
            shift = Mobject._xy_vector(shift, 'Fade shift')
        if target_position is not None and not isinstance(target_position, Mobject):
            target_position = Mobject._xy_vector(target_position, 'Fade target position')
        NumberLine._real(scale, 'Fade scale')
        self.shift_vector, self.target_position, self.scale_factor = shift, target_position, scale
        self._lagged = self.lag_ratio > 0

    def _faded(self):
        # Community's _Fade: a target position is where a fade-in starts and a
        # fade-out ends; a shift is applied backwards for fade-ins.
        moved = self.mobject.copy()
        if self.shift_vector is None and self.target_position is not None:
            point = (self.target_position.get_center() if isinstance(self.target_position, Mobject)
                     else self.target_position)
            moved.shift(point - self.mobject.get_center())
        elif self.shift_vector is not None:
            moved.shift(self.shift_vector * (-1 if self._fading_in else 1))
        if self.scale_factor != 1:
            moved.scale(self.scale_factor)
        return moved.to_dict()

    def begin(self, scene):
        super().begin(scene)
        self.moved = (self.shift_vector is not None or self.target_position is not None
                      or self.scale_factor != 1)
        away = self._faded() if self.moved else self.start
        self.first, self.last = (away, self.start) if self._fading_in else (self.start, away)

    def _visibility(self, opacity, alpha):
        return opacity * (alpha if self._fading_in else 1 - alpha)

    def sample(self, alpha):
        result = interpolate(self.first, self.last, alpha) if self.moved else _snapshot_copy(self.start)
        result['opacity'] = self._visibility(self.start['opacity'], alpha)
        return [result]

    def sample_members(self, alpha, rate_func):
        def member(node, a, path):
            start, end = _lookup(self.first, path), _lookup(self.last, path)
            node.update(interpolate(_strip_children(start), _strip_children(end), a))
            node['opacity'] = self._visibility(_lookup(self.start, path)['opacity'], a)
        result = _snapshot_copy(self.start)
        # Whole drawable subtrees fade together so nested opacity never compounds.
        return [self._member_states(result, alpha, rate_func, member, nested=False)]


def _lookup(data, path):
    for index in path:
        data = data['children'][index]
    return data


def _strip_children(data):
    return {key: value for key, value in data.items() if key != 'children'}


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
    """Trace outlines; Community's default lag_ratio=1 draws members in sequence."""
    _lagged = True

    def __init__(self, mobject, lag_ratio=1.0, introducer=True, **kwargs):
        super().__init__(mobject, lag_ratio=lag_ratio, introducer=introducer, **kwargs)

    @staticmethod
    def _reveal(node, progress):
        if node['type'] in ('text', 'mathtex'):
            node['opacity'] *= progress
        else:
            node['draw_progress'] = progress
            node['fill_opacity'] *= progress

    def sample(self, alpha):
        return self.sample_members(alpha, linear)

    def sample_members(self, alpha, rate_func):
        return [self._member_states(_snapshot_copy(self.start), alpha, rate_func,
                                    lambda node, a, path: self._reveal(node, a))]


class ShowPassingFlash(Animation):
    """Move a temporary cubic-parameter window over supported vector outlines."""
    def __init__(self, mobject, time_width=.1, **kwargs):
        super().__init__(mobject, **kwargs)
        if (isinstance(time_width, bool) or not isinstance(time_width, _REAL)
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
    def __init__(self, mobject, reverse_rate_function=True, remover=True, **kwargs):
        super().__init__(mobject, reverse_rate_function=reverse_rate_function, remover=remover, **kwargs)


class DrawBorderThenFill(Animation):
    """Draw each member's outline, then interpolate to its fill and stroke."""
    _lagged = True

    def __init__(self, vmobject, run_time=2, rate_func=double_smooth, stroke_width=2,
                 stroke_color=None, introducer=True, **kwargs):
        super().__init__(vmobject, run_time=run_time, rate_func=rate_func, introducer=introducer, **kwargs)
        Mobject._validate_width(stroke_width)
        self.outline_width, self.outline_color = stroke_width, stroke_color

    def _member(self, node, alpha, path):
        # Community's integer_interpolate(0, 2, alpha): outline, then style.
        phase = min(1, int(2 * alpha))
        sub = 2 * alpha - phase
        color = self.outline_color or (node.get('stroke_color') if node.get('stroke_width') else node.get('color'))
        width, fill = node.get('stroke_width', 0), node.get('fill_opacity', 1)
        stroke = node.get('stroke_color', node.get('color'))
        glyph = node['type'] in ('text', 'mathtex')
        if phase == 0:
            node['fill_opacity'] = 0
            node['stroke_width'] = self.outline_width
            node['stroke_color'] = color
            if glyph:
                node['opacity'] *= sub
            else:
                node['draw_progress'] = sub
        else:
            node['fill_opacity'] = fill * sub
            node['stroke_width'] = interpolate(self.outline_width, width, sub)
            node['stroke_color'] = interpolate(color, stroke, sub) if isinstance(color, str) else stroke

    def sample(self, alpha):
        return self.sample_members(alpha, linear)

    def sample_members(self, alpha, rate_func):
        return [self._member_states(_snapshot_copy(self.start), alpha, rate_func, self._member)]


class Write(DrawBorderThenFill):
    """Community's Write: lagged border-then-fill with length-based defaults.

    Text and formulas have no glyph outlines in this preview; they show a stroked
    outline fading in, then their fill."""
    def __init__(self, vmobject, rate_func=linear, reverse=False, **kwargs):
        length = len(vmobject._painted_members()) if isinstance(vmobject, Mobject) else 0
        kwargs.setdefault('run_time', 1 if length < 15 else 2)
        kwargs.setdefault('lag_ratio', min(4.0 / max(1.0, length), 0.2))
        kwargs.setdefault('remover', reverse)
        self.reverse = reverse
        super().__init__(vmobject, rate_func=rate_func, introducer=not reverse,
                         reverse_rate_function=reverse, **kwargs)


class Unwrite(Write):
    def __init__(self, vmobject, rate_func=linear, reverse=True, **kwargs):
        super().__init__(vmobject, rate_func=rate_func, reverse=reverse, **kwargs)


class FadeOut(FadeIn):
    _fading_in = False

    def __init__(self, *mobjects, **kwargs):
        kwargs.setdefault('remover', True)
        super().__init__(*mobjects, **kwargs)

    def finish(self, scene):
        scene.remove(self.mobject)


def _arc_factor(alpha, path_arc):
    """Community's path_along_arc as a complex factor on each point's displacement."""
    if abs(path_arc) < 1e-6:
        return complex(alpha, 0)
    scale = math.sin(alpha * path_arc / 2) / math.sin(path_arc / 2)
    angle = (alpha - 1) * path_arc / 2
    return complex(scale * math.cos(angle), scale * math.sin(angle))


def _apply_path_arc(sampled, start, end, alpha, path_arc):
    # Each drawable member's center follows the arc; shapes keep their morph.
    if (sampled['type'] in ('vgroup', 'mobject') and len(sampled.get('children', [])) ==
            len(start.get('children', [])) == len(end.get('children', [])) and sampled['children']):
        for node, a, b in zip(sampled['children'], start['children'], end['children']):
            _apply_path_arc(node, a, b, alpha, path_arc)
        return
    centers = [Vector(data['position']) + Vector(data.get('geometry_center', ORIGIN)) for data in (start, end)]
    delta = centers[1] - centers[0]
    factor = _arc_factor(alpha, path_arc) - alpha
    offset = (delta[0] * factor.real - delta[1] * factor.imag, delta[0] * factor.imag + delta[1] * factor.real, 0)
    sampled['position'] = list(Vector(sampled['position']) + offset)


class Transform(Animation):
    def __init__(self, mobject, target_mobject, path_arc=0, path_arc_axis=OUT, **kwargs):
        super().__init__(mobject, **kwargs)
        if not isinstance(target_mobject, Mobject):
            raise TypeError('Transform expects a target Mobject')
        NumberLine._real(path_arc, 'path_arc')
        if Vector(path_arc_axis) not in (OUT, IN):
            raise NotImplementedError('Transform paths support only OUT/IN arcs')
        self.path_arc = path_arc if Vector(path_arc_axis) == OUT else -path_arc
        self.target = target_mobject.copy()

    def begin(self, scene):
        super().begin(scene)
        self._transform_plan = None
        self._path_target = None
        if self.mobject.__dict__.get('_stretch_baked') or self.target.__dict__.get('_stretch_baked'):
            try:
                start = self.mobject.copy().stretch(1,0).to_dict()
                target = self.target.copy().stretch(1,0).to_dict()
            except NotImplementedError:
                pass  # Unsupported target types keep the existing fade/morph plan.
            else:
                self.start,self._path_target = start,target

    def sample(self, alpha):
        end = self._path_target or self.target.to_dict()
        if self._transform_plan is None:
            self._transform_plan = _transform_plan(self.start, end)
        result = _sample_transform(self._transform_plan, alpha)
        if self.path_arc and len(result) == 1 and 0 < alpha < 1:
            _apply_path_arc(result[0], self.start, end, alpha, self.path_arc)
        return result

    def finish(self, scene):
        if abs(self.rate_func(1)) < 1e-9 and not self.reverse_rate_function:
            # Like Community's final interpolate(rate_func(1)): a there-and-back
            # transform ends where it started.
            return
        # Preserve source and ordered child identities, callbacks and checkpoints.
        self.mobject.become(self.target)


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
            return [_snapshot_copy(self.start)]
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
            return [_snapshot_copy(self.start)]
        return [interpolate(self.start, self.highlight, alpha)]


class Rotate(Animation):
    """Sample a rigid rotation from the original object rather than its endpoints."""
    def __init__(self, mobject, angle=PI, axis=OUT, about_point=None, about_edge=None, **kwargs):
        super().__init__(mobject, **kwargs)
        if not math.isfinite(angle):
            raise ValueError('Rotation angle must be finite')
        axis = Vector(axis)
        if axis not in (OUT, IN):
            raise NotImplementedError('Only 2D rotation about OUT or IN is supported')
        if about_point is not None and about_edge is not None:
            raise ValueError('Pass about_point or about_edge, not both')
        self.angle = angle if axis == OUT else -angle
        self.about_point = Vector(about_point) if about_point is not None else None
        self.about_edge = None if about_edge is None else Mobject._xy_vector(about_edge, 'Pivot edge')

    def begin(self, scene):
        super().begin(scene)
        self.original = self.mobject.copy()
        if self.about_edge is not None:
            # The edge is resolved once, at the stage start, like Community's pivot.
            self.about_point = self.original.get_critical_point(self.about_edge)

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


class _TransformMatching(Animation):
    """Morph parts with matching keys; fade the rest (Community's matching rules)."""
    def __init__(self, mobject, target_mobject, transform_mismatches=False, fade_transform_mismatches=False,
                 key_map=None, **kwargs):
        if not isinstance(mobject, Mobject) or not isinstance(target_mobject, Mobject):
            raise TypeError(type(self).__name__ + ' expects two mobjects')
        if mobject is target_mobject:
            raise ValueError('Source and target must be different mobjects')
        super().__init__(mobject, **kwargs)
        self.target_mobject, self.key_map = target_mobject, dict(key_map or {})
        self.transform_mismatches = transform_mismatches or fade_transform_mismatches

    def _keyed(self, mobject):
        result = {}
        for part in self.get_mobject_parts(mobject):
            result.setdefault(self.get_mobject_key(part), []).append(part)
        return result

    def begin(self, scene):
        super().begin(scene)
        source, target = self._keyed(self.mobject), self._keyed(self.target_mobject)
        pairs = []
        for key in [k for k in source if k in target]:
            pairs.extend(zip(source[key], target[key]))
        for key1, key2 in self.key_map.items():
            if key1 in source and key2 in target:
                pairs.extend(zip(source.pop(key1), target.pop(key2)))
        lost = [part for key in source if key not in target for part in source[key]]
        new = [part for key in target if key not in source for part in target[key]]
        if self.transform_mismatches and lost and new:
            pairs.append((VGroup(*lost).copy(), VGroup(*new).copy()))
            lost, new = [], []
        self.plans, self.sliding = [], []
        for a, b in pairs:
            if {a._type, b._type} & {'text', 'mathtex'} or a._painted_members() != [a] or b._painted_members() != [b]:
                # Glyphs from different formulas: slide both and cross-fade, so
                # identical parts appear to move into place.
                self.sliding.append((a.to_dict(), self._posed(a, b).to_dict(), self._posed(b, a).to_dict(), b.to_dict()))
            else:
                self.plans.append(_transform_plan(a.to_dict(), b.to_dict()))
        # Unmatched sources fade toward the unmatched targets' center (origin if none).
        goal = VGroup(*[part.copy() for part in new]).get_center() if new else Vector(ORIGIN)
        self.leaving = [(part.to_dict(), part.copy().shift(goal - part.get_center()).to_dict()) for part in lost]
        self.arriving = [part.to_dict() for part in new]

    @staticmethod
    def _posed(mobject, reference):
        moved = mobject.copy()
        if mobject.get_height() and reference.get_height():
            moved.scale(reference.get_height() / mobject.get_height())
        return moved.shift(reference.get_center() - moved.get_center())

    def sample(self, alpha):
        states = [state for plan in self.plans for state in _sample_transform(plan, alpha)]
        for source, source_end, target_start, target in self.sliding:
            leaving, arriving = interpolate(source, source_end, alpha), interpolate(target_start, target, alpha)
            leaving['opacity'] = source['opacity'] * (1 - alpha)
            arriving['opacity'] = target['opacity'] * alpha
            states += [leaving, arriving]
        for start, end in self.leaving:
            state = interpolate(start, end, alpha)
            state['opacity'] = start['opacity'] * (1 - alpha)
            states.append(state)
        for start in self.arriving:
            state = copy.deepcopy(start)
            state['opacity'] *= alpha
            states.append(state)
        return states

    def finish(self, scene):
        scene.remove(self.mobject)
        scene.add(self.target_mobject)

    def objects(self):
        return [self.mobject, self.target_mobject]


class TransformMatchingTex(_TransformMatching):
    @staticmethod
    def get_mobject_parts(mobject):
        if isinstance(mobject, MathTex):
            return mobject._parts()
        if mobject._type in ('vgroup', 'mobject') or isinstance(mobject, Group):
            return [p for child in mobject.children for p in TransformMatchingTex.get_mobject_parts(child)]
        if not hasattr(mobject, 'tex_string'):
            raise TypeError('TransformMatchingTex expects MathTex/Tex mobjects or groups of them')
        return [mobject]

    @staticmethod
    def get_mobject_key(mobject):
        return mobject.tex_string


class TransformMatchingShapes(_TransformMatching):
    @staticmethod
    def get_mobject_parts(mobject):
        return mobject._painted_members()

    @staticmethod
    def get_mobject_key(mobject):
        # Shape identity up to position and size, like Community's normalized point hash.
        if mobject._type in ('text', 'mathtex'):
            return (mobject._type, mobject.text, getattr(mobject, 'part', None))
        probe = mobject.copy()
        probe.children = []
        probe.center()
        if probe.get_height():
            probe.scale_to_fit_height(1)
        return tuple(tuple(round(v, 3) + 0.0 for v in point[:2]) for point in probe.get_points())


class ClockwiseTransform(Transform):
    def __init__(self, mobject, target_mobject, path_arc=-PI, **kwargs):
        super().__init__(mobject, target_mobject, path_arc=path_arc, **kwargs)


class CounterclockwiseTransform(Transform):
    def __init__(self, mobject, target_mobject, path_arc=PI, **kwargs):
        super().__init__(mobject, target_mobject, path_arc=path_arc, **kwargs)


class MoveToTarget(Transform):
    def __init__(self, mobject, **kwargs):
        if not isinstance(getattr(mobject, 'target', None), Mobject):
            raise ValueError('MoveToTarget called on mobject without attribute \'target\'')
        super().__init__(mobject, mobject.target, **kwargs)


class CyclicReplace(Transform):
    """Move each mobject to the next one's position along an arc."""
    def __init__(self, *mobjects, path_arc=90 * DEGREES, **kwargs):
        if len(mobjects) < 1 or any(not isinstance(m, Mobject) for m in mobjects):
            raise TypeError('CyclicReplace expects mobjects')
        self.group = Group(*mobjects)
        super().__init__(self.group, self.group, path_arc=path_arc, **kwargs)

    def begin(self, scene):
        self.target = self.group.copy()
        cycled = self.target.children[-1:] + self.target.children[:-1]
        for moved, place in zip(cycled, self.group.children):
            moved.move_to(place)
        super().begin(scene)


class Swap(CyclicReplace):
    pass


class FadeTransform(Transform):
    """Crossfade while the source moves onto the target and the target grows from the source."""
    def __init__(self, mobject, target_mobject, stretch=True, dim_to_match=1, **kwargs):
        super().__init__(mobject, target_mobject, **kwargs)
        if not isinstance(stretch, bool):
            raise ValueError('stretch must be a boolean')
        self.replacement, self.stretch, self.dim_to_match = target_mobject, stretch, dim_to_match

    def _fit(self, mobject, reference):
        try:
            return mobject.replace(reference, self.dim_to_match, self.stretch)
        except NotImplementedError:
            # Glyphs cannot be stretched yet; fit one dimension instead.
            return mobject.replace(reference, self.dim_to_match)

    def begin(self, scene):
        Animation.begin(self, scene)
        self.source_end = self._fit(self.mobject.copy(), self.replacement).to_dict()
        self.target_start = self._fit(self.replacement.copy(), self.mobject).to_dict()
        self.target_end = self.replacement.to_dict()

    def sample(self, alpha):
        source = interpolate(self.start, self.source_end, alpha)
        target = interpolate(self.target_start, self.target_end, alpha)
        source['opacity'] *= 1 - alpha
        target['opacity'] *= alpha
        return [source, target]

    def finish(self, scene):
        scene.remove(self.mobject)
        scene.add(self.replacement)

    def objects(self):
        return [self.mobject, self.replacement]


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
        if name.startswith('_'):
            raise AttributeError(name)
        override = type(self.mobject).__dict__.get('_animate_overrides', None) or getattr(type(self.mobject), '_animate_overrides', {})
        if name in override and not self.operations:
            # Community's @override_animate: the method builds its own animation.
            return getattr(self.mobject, override[name])
        # Community animates any method applied to a copy; updater and checkpoint
        # bookkeeping is not geometry and stays unsupported here.
        if (name in ('add_updater', 'remove_updater', 'clear_updaters', 'suspend_updating', 'resume_updating',
                     'save_state', 'generate_target', 'copy', 'update') or
                not callable(getattr(self.mobject, name, None))):
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
            animation._complete(scene)

    def _complete(self, scene):
        self.finish(scene)


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
            # Update-function stages act on a live object; sample them from a copy of
            # the stage's starting state instead.
            source = animation.mobject.copy() if isinstance(animation, UpdateFromFunc) else None
            animation.prepare(staging)
            baseline = {originals[id(m)]: [m.to_dict()] for m in staging.mobjects
                        if originals[id(m)] in owned}
            # Remap only identity keys; start/terminal geometry stays snapshotted.
            prepared = copy.deepcopy(animation, originals.copy())
            self._stages.append((baseline, prepared, source))
            animation._complete(staging)
        # Placeholder roots allow capture() to include later introductions. Their
        # states remain empty until the relevant stage; geometry stays untouched.
        for mobject in owned:
            scene._introduce(mobject)

    def states(self, alpha, rate_func=None):
        time = self.natural_duration if alpha >= 1 else (rate_func or self.rate_func)(max(0, alpha)) * self.natural_duration
        stage = 0
        for index, (start, _) in enumerate(self.timings):
            if start <= time:
                stage = index
        start, duration = self.timings[stage]
        baseline, animation, source = self._stages[stage]
        result = {m: [] for m in self.objects()}
        result.update(baseline)
        result.update(animation.states((time - start) / duration))
        if source is not None:
            probe = source.copy()
            animation._call(probe)
            result[animation.mobject] = [probe.to_dict()]
        return result

    def finish(self, scene):
        scene.remove(*(m for m in self.objects() if m not in self._initial))
        for animation in self.animations:
            animation.prepare(scene)
            animation._complete(scene)


class ApplyMethod(Animate):
    """Animate a bound Mobject method, applied to a copy when the stage begins."""
    def __init__(self, method, *args, **kwargs):
        mobject = getattr(method, '__self__', None)
        if not isinstance(mobject, Mobject) or not callable(method):
            raise TypeError('ApplyMethod expects a method bound to a Mobject')
        options = {key: kwargs.pop(key) for key in list(kwargs)
                   if key in ('run_time', 'rate_func', 'lag_ratio', 'remover', 'name', 'path_arc')}
        super().__init__(mobject)
        for key, value in options.items():
            setattr(self, key, value)
        self.operations.append((method.__name__, args, kwargs))


class ScaleInPlace(ApplyMethod):
    def __init__(self, mobject, scale_factor, **kwargs):
        super().__init__(mobject.scale, scale_factor, **kwargs)


class FadeToColor(ApplyMethod):
    def __init__(self, mobject, color, **kwargs):
        super().__init__(mobject.set_color, color, **kwargs)


class ApplyPointwiseFunction(ApplyMethod):
    def __init__(self, function, mobject, run_time=3.0, **kwargs):
        if not callable(function):
            raise TypeError('ApplyPointwiseFunction expects a point function')
        super().__init__(mobject.apply_function, function, run_time=run_time, **kwargs)


class ApplyPointwiseFunctionToCenter(Animate):
    def __init__(self, function, mobject, run_time=3.0, **kwargs):
        if not callable(function):
            raise TypeError('ApplyPointwiseFunctionToCenter expects a point function')
        super().__init__(mobject)
        self.function, self.run_time = function, run_time
        for key, value in kwargs.items():
            setattr(self, key, value)

    def begin(self, scene):
        self.operations = [('move_to', (Vector(self.function(self.mobject.get_center())),), {})]
        super().begin(scene)


class ApplyMatrix(ApplyPointwiseFunction):
    def __init__(self, matrix, mobject, about_point=ORIGIN, **kwargs):
        rows = [list(row) for row in matrix]
        if [len(row) for row in rows] not in ([2, 2], [3, 3, 3]):
            raise ValueError('Matrix has bad dimensions')
        if len(rows) == 2:
            rows = [rows[0] + [0], rows[1] + [0], [0, 0, 1]]
        pivot = Vector(about_point)
        def function(point):
            p = Vector(point) - pivot
            return Vector(sum(a * b for a, b in zip(row, p)) for row in rows) + pivot
        super().__init__(function, mobject, **kwargs)


class ApplyComplexFunction(ApplyMethod):
    def __init__(self, function, mobject, **kwargs):
        if not callable(function):
            raise TypeError('ApplyComplexFunction expects a complex function')
        value = complex(function(complex(1)))
        kwargs.setdefault('path_arc', math.atan2(value.imag, value.real) if value else 0)
        super().__init__(mobject.apply_complex_function, function, **kwargs)


class ApplyFunction(Transform):
    def __init__(self, function, mobject, **kwargs):
        if not callable(function):
            raise TypeError('ApplyFunction expects a function returning a Mobject')
        super().__init__(mobject, mobject, **kwargs)
        self.function = function

    def begin(self, scene):
        target = self.function(self.mobject.copy())
        if not isinstance(target, Mobject):
            raise TypeError('Functions passed to ApplyFunction must return object of type Mobject')
        self.target = target
        super().begin(scene)


class Homotopy(Animation):
    """Apply homotopy(x, y, z, t) to the starting points at each sampled time."""
    def __init__(self, homotopy, mobject, run_time=3, apply_function_kwargs=None, **kwargs):
        if not callable(homotopy):
            raise TypeError('Homotopy expects a function of (x, y, z, t)')
        super().__init__(mobject, run_time=run_time, **kwargs)
        self.homotopy, self.apply_function_kwargs = homotopy, dict(apply_function_kwargs or {})

    def begin(self, scene):
        super().begin(scene)
        self.original = self.mobject.copy()

    def _at(self, t):
        current = self.original.copy()
        current.apply_function(lambda p: Vector(self.homotopy(p[0], p[1], p[2], t)), **self.apply_function_kwargs)
        return current

    def sample(self, alpha):
        return [self._at(alpha).to_dict()]

    def finish(self, scene):
        rate = self.rate_func(1 if not self.reverse_rate_function else 0)
        self.mobject.become(self._at(rate))


class SmoothedVectorizedHomotopy(Homotopy):
    def _at(self, t):
        return super()._at(t).make_smooth()


class ComplexHomotopy(Homotopy):
    def __init__(self, complex_homotopy, mobject, **kwargs):
        if not callable(complex_homotopy):
            raise TypeError('ComplexHomotopy expects a function of (z, t)')
        def homotopy(x, y, z, t):
            value = complex(complex_homotopy(complex(x, y), t))
            return (value.real, value.imag, z)
        super().__init__(homotopy, mobject, **kwargs)


class ApplyWave(Homotopy):
    """Community's travelling wave nudge along a direction."""
    def __init__(self, mobject, direction=UP, amplitude=0.2, wave_func=smooth, time_width=1, ripples=1,
                 run_time=2, **kwargs):
        x_min, x_max = mobject.get_left()[0], mobject.get_right()[0]
        direction = Mobject._xy_vector(direction, 'Wave direction')
        length = math.hypot(direction[0], direction[1])
        vect = direction * (amplitude / length) if length else Vector(ORIGIN)
        def wave(t):
            t = 1 - t
            if t >= 1 or t <= 0:
                return 0
            phases = ripples * 2
            phase = int(t * phases)
            if phase == 0:
                return wave_func(t * phases)
            if phase == phases - 1:
                t -= phase / phases
                return (1 - wave_func(t * phases)) * (2 * (ripples % 2) - 1)
            phase = int((phase - 1) / 2)
            t -= (2 * phase + 1) / phases
            return (1 - 2 * wave_func(t * ripples)) * (1 - 2 * (phase % 2))
        def homotopy(x, y, z, t):
            upper = t * (1 + time_width)
            lower = upper - time_width
            relative = (x - x_min) / (x_max - x_min) if x_max != x_min else 0
            phase = (relative - lower) / (upper - lower) if upper != lower else 0
            nudge = vect * wave(phase)
            return (x + nudge[0], y + nudge[1], z)
        super().__init__(homotopy, mobject, run_time=run_time, **kwargs)


class PhaseFlow(Animation):
    """Euler-integrate points along a vector field over virtual time."""
    def __init__(self, function, mobject, virtual_time=1, suspend_mobject_updating=False, rate_func=linear, **kwargs):
        if not callable(function):
            raise TypeError('PhaseFlow expects a vector field function')
        super().__init__(mobject, rate_func=rate_func, **kwargs)
        self.function, self.virtual_time = function, virtual_time

    def begin(self, scene):
        super().begin(scene)
        self.current, self.last = self.mobject.copy(), 0

    def _advance(self, alpha):
        if alpha < self.last:
            self.current, self.last = Mobject.copy(self.mobject), 0  # restart for out-of-order samples
        dt = self.virtual_time * (alpha - self.last)
        if dt:
            self.current.apply_function(lambda p: Vector(p) + Vector(self.function(p)) * dt)
        self.last = alpha
        return self.current

    def sample(self, alpha):
        return [self._advance(alpha).to_dict()]

    def finish(self, scene):
        self.mobject.become(self._advance(1))


class ChangingDecimal(Animation):
    def __init__(self, decimal_mob, number_update_func, suspend_mobject_updating=False, **kwargs):
        if not isinstance(decimal_mob, DecimalNumber):
            raise TypeError('ChangingDecimal can only take in a DecimalNumber')
        if not callable(number_update_func):
            raise TypeError('number_update_func must be callable')
        super().__init__(decimal_mob, **kwargs)
        self.number_update_func = number_update_func

    def sample(self, alpha):
        return [self.mobject.copy().set_value(self.number_update_func(alpha)).to_dict()]

    def finish(self, scene):
        self.mobject.set_value(self.number_update_func(self.rate_func(1)))


class ChangeDecimalToValue(ChangingDecimal):
    def __init__(self, decimal_mob, target_number, **kwargs):
        start = decimal_mob.number if isinstance(decimal_mob, DecimalNumber) else 0
        super().__init__(decimal_mob, lambda a: start + (target_number - start) * a, **kwargs)


class Wait(Animation):
    """A pause inside play(), AnimationGroup or Succession."""
    def __init__(self, run_time=1, stop_condition=None, frozen_frame=None, rate_func=linear, **kwargs):
        if stop_condition is not None:
            raise NotImplementedError('Wait stop conditions are not supported')
        NumberLine._real(run_time, 'Wait run_time', positive=True)
        super().__init__(None, run_time=run_time, rate_func=rate_func, **kwargs)

    def objects(self):
        return []

    def prepare(self, scene):
        pass

    def states(self, alpha, rate_func=None):
        return {}

    def _complete(self, scene):
        pass


class GrowFromEdge(GrowFromPoint):
    def __init__(self, mobject, edge, **kwargs):
        super().__init__(mobject, ORIGIN, **kwargs)
        self.edge = Mobject._xy_vector(edge, 'Growth edge')

    def begin(self, scene):
        self.point = self.mobject.get_critical_point(self.edge)
        super().begin(scene)


class GrowArrow(GrowFromPoint):
    def __init__(self, arrow, **kwargs):
        super().__init__(arrow, ORIGIN, **kwargs)

    def begin(self, scene):
        self.point = Vector(self.mobject.get_start())
        super().begin(scene)


class SpinInFromNothing(GrowFromCenter):
    """Grow from the center along Community's arc path (path_arc = angle)."""
    def __init__(self, mobject, angle=PI / 2, **kwargs):
        super().__init__(mobject, **kwargs)
        self.angle = NumberLine._real(angle, 'Spin angle')

    def sample(self, alpha):
        factor = _arc_factor(alpha, self.angle)
        current = self.original.copy().scale(abs(factor), about_point=self.point)
        current.rotate(math.atan2(factor.imag, factor.real), about_point=self.point)
        return [current.to_dict()]


class Wiggle(Animation):
    def __init__(self, mobject, scale_value=1.1, rotation_angle=0.01 * TAU, n_wiggles=6,
                 scale_about_point=None, rotate_about_point=None, run_time=2, **kwargs):
        super().__init__(mobject, run_time=run_time, **kwargs)
        for value, name in ((scale_value, 'scale_value'), (rotation_angle, 'rotation_angle'), (n_wiggles, 'n_wiggles')):
            NumberLine._real(value, name)
        self.scale_value, self.rotation_angle, self.n_wiggles = scale_value, rotation_angle, n_wiggles
        self.scale_about_point, self.rotate_about_point = scale_about_point, rotate_about_point

    def begin(self, scene):
        super().begin(scene)
        self.original = self.mobject.copy()
        center = self.original.get_center()
        self.pivots = [center if p is None else Mobject._xy_vector(p, 'Wiggle point')
                       for p in (self.scale_about_point, self.rotate_about_point)]

    def sample(self, alpha):
        current = self.original.copy()
        current.scale(interpolate(1, self.scale_value, there_and_back(alpha)), about_point=self.pivots[0])
        current.rotate(wiggle(alpha, self.n_wiggles) * self.rotation_angle, about_point=self.pivots[1])
        return [current.to_dict()]

    def finish(self, scene):
        pass


class FocusOn(Transform):
    """A large transparent dot shrinking onto a point."""
    def __init__(self, focus_point, opacity=0.2, color=GREY, run_time=2, **kwargs):
        point = focus_point.get_center() if isinstance(focus_point, Mobject) else Mobject._xy_vector(focus_point, 'Focus point')
        start = Dot(radius=config.frame_width / 2 + config.frame_height / 2, stroke_width=0,
                    fill_color=color, fill_opacity=0)
        target = Dot(radius=0, stroke_width=0).set_fill(color, opacity=opacity).move_to(point)
        kwargs.setdefault('remover', True)
        super().__init__(start, target, run_time=run_time, **kwargs)


class UpdateFromFunc(Animation):
    """Call update_function(mobject) on every frame of the stage."""
    def __init__(self, mobject, update_function, suspend_mobject_updating=False, **kwargs):
        if not callable(update_function):
            raise TypeError('update_function must be callable')
        super().__init__(mobject, **kwargs)
        self.update_function = update_function

    def _call(self, mobject):
        self.update_function(mobject)

    def prepare(self, scene):
        scene._introduce(self.mobject)
        self._alpha = 0
        self._updater = lambda mobject: self._call(mobject)
        self.mobject.add_updater(self._updater)

    def states(self, alpha, rate_func=None):
        # The live mobject is captured after updaters run with sampled neighbors.
        self._alpha = (rate_func or self.rate_func)(max(0, min(1, alpha)))
        return {}

    def _complete(self, scene):
        self._alpha = 1
        self.mobject.remove_updater(self._updater)
        self._call(self.mobject)
        if self.remover:
            scene.remove(self.mobject)


class UpdateFromAlphaFunc(UpdateFromFunc):
    """Call update_function(mobject, alpha) with the stage's eased progress."""
    def _call(self, mobject):
        self.update_function(mobject, self._alpha)


class ShowIncreasingSubsets(Animation):
    def __init__(self, group, suspend_mobject_updating=False, int_func=math.floor, **kwargs):
        super().__init__(group, **kwargs)
        self.int_func = int_func

    def sample(self, alpha):
        result = _snapshot_copy(self.start)
        count = max(0, min(len(result['children']), int(self.int_func(alpha * len(result['children'])))))
        result['children'] = result['children'][:count]
        return [result]


class ShowSubmobjectsOneByOne(ShowIncreasingSubsets):
    def __init__(self, group, int_func=math.ceil, **kwargs):
        super().__init__(group, int_func=int_func, **kwargs)

    def sample(self, alpha):
        result = _snapshot_copy(self.start)
        index = int(self.int_func(alpha * len(result['children']))) - 1
        result['children'] = result['children'][index:index + 1] if 0 <= index < len(result['children']) else []
        return [result]

    def finish(self, scene):
        pass


class AddTextLetterByLetter(Animation):
    """Reveal a Text's characters in order, keeping its final layout fixed."""
    _removing = False

    def __init__(self, text, suspend_mobject_updating=False, int_func=math.ceil, rate_func=linear,
                 time_per_char=0.1, run_time=None, **kwargs):
        if (not isinstance(text, Text) or isinstance(text, MathTex) or text._type not in ('text', 'vgroup')
                or '_number_format' in text.__dict__):
            raise TypeError('Letter-by-letter animations expect Text')
        glyphs = sum(1 for char in text.text if not char.isspace())
        if run_time is None:
            run_time = max(0.06, time_per_char * glyphs)
        super().__init__(text, run_time=run_time, rate_func=rate_func, **kwargs)
        self.int_func = int_func

    def sample(self, alpha):
        result = _snapshot_copy(self.start)
        progress = 1 - alpha if self._removing else alpha
        if result['type'] == 'vgroup':
            # Glyph children (Community's structure): reveal them in order.
            result['children'] = result['children'][:self._shown(progress, len(result['children']))]
            return [result]
        layout = _text_layout(result)
        shown = self._shown(progress, sum(1 for char in result['text'] if not char.isspace()))
        em = layout['em'] / 1000
        for line in layout['lines']:
            kept = ''
            for char in line['text']:
                if not char.isspace():
                    if shown == 0:
                        break
                    shown -= 1
                kept += char
            line['text'] = kept
            line['length'] = sum(_glyph_box(char, _glyph_table(result.get('font')))[0] for char in kept) * em
        result['layout'] = layout
        return [result]


    def _shown(self, alpha, count):
        """How many non-space glyphs are visible at this progress."""
        return max(0, min(count, int(self.int_func(alpha * count))))


class RemoveTextLetterByLetter(AddTextLetterByLetter):
    _removing = True

    def __init__(self, text, remover=True, **kwargs):
        super().__init__(text, remover=remover, **kwargs)


class Circumscribe(Succession):
    """Draw a temporary surrounding rectangle or circle around a mobject."""
    def __init__(self, mobject, shape=None, fade_in=False, fade_out=False, time_width=0.3,
                 buff=SMALL_BUFF, color=YELLOW, run_time=1, stroke_width=DEFAULT_STROKE_WIDTH, **kwargs):
        shape = Rectangle if shape is None else shape
        if shape is Rectangle:
            frame = SurroundingRectangle(mobject, color=color, buff=buff, stroke_width=stroke_width)
        elif shape is Circle:
            frame = Circle(color=color, stroke_width=stroke_width).surround(mobject, buffer_factor=1)
            radius = frame.get_width() / 2
            if radius:
                frame.scale((radius + buff) / radius)
        else:
            raise ValueError('shape should be either Rectangle or Circle.')
        if fade_in and fade_out:
            stages = (FadeIn(frame, run_time=run_time / 2), FadeOut(frame, run_time=run_time / 2))
        elif fade_in:
            frame.reverse_direction()
            stages = (FadeIn(frame, run_time=run_time / 2), Uncreate(frame, run_time=run_time / 2))
        elif fade_out:
            stages = (Create(frame, run_time=run_time / 2), FadeOut(frame, run_time=run_time / 2))
        else:
            stages = (ShowPassingFlash(frame, time_width, run_time=run_time),)
        super().__init__(*stages, **kwargs)


class Flash(AnimationGroup):
    """Short lines flashing outward from a point."""
    def __init__(self, point, line_length=0.2, num_lines=12, flash_radius=0.1, line_stroke_width=3,
                 color=YELLOW, time_width=1, run_time=1.0, **kwargs):
        center = point.get_center() if isinstance(point, Mobject) else Mobject._xy_vector(point, 'Flash point')
        if isinstance(num_lines, bool) or not isinstance(num_lines, numbers.Integral) or not 1 <= num_lines <= 360:
            raise ValueError('num_lines must be an integer from 1 to 360')
        lines = VGroup()
        for index in range(num_lines):
            line = Line(center, center + RIGHT * line_length).shift(RIGHT * flash_radius)
            lines.add(line.rotate(index * TAU / num_lines, about_point=center))
        lines.set_color(color).set_stroke(width=line_stroke_width)
        self.lines = lines
        flash_options = {key: kwargs.pop(key) for key in list(kwargs) if key in ('rate_func',)}
        super().__init__(*(ShowPassingFlash(line, time_width=time_width, run_time=run_time, **flash_options)
                           for line in lines), **kwargs)


class Scene:
    camera_class = PreviewConfig

    def __init__(self, camera_config=None):
        self.camera = self.camera_class(**{k: v for k, v in config.to_dict().items() if k != 'reference_frame_width'})
        for name, value in (camera_config or {}).items():
            setattr(self.camera, name, value)
        self.mobjects, self.frames = [], []
        self.foreground_mobjects = []
        self._elapsed_frames = 0

    @property
    def time(self):
        return self._elapsed_frames / FPS

    @staticmethod
    def _restructured(roots, removing):
        """Community's restructuring: drop members and split groups that contain them."""
        result = []
        def visit(items, removing):
            for mobject in items:
                if mobject in removing:
                    continue
                hit = [m for m in removing if m in mobject.get_family()]
                if not hit:
                    result.append(mobject)
                    continue
                if mobject.angle or mobject.geometry_scale != 1 or any(mobject.position):
                    raise NotImplementedError('Cannot split a rotated or transformed group; '
                                              'add or remove the whole group')
                visit(mobject.children, hit)
        visit(roots, list(removing))
        return result

    def get_mobject_family_members(self):
        return [m for root in self.mobjects for m in root.get_family()]

    def add(self, *mobjects):
        if any(not isinstance(m, Mobject) for m in mobjects):
            raise TypeError('Scene.add expects Mobjects')
        new = list(dict.fromkeys(mobjects))
        moving = [m for m in new if m not in self.foreground_mobjects] + self.foreground_mobjects
        family = [member for m in moving for member in m.get_family()]
        # Re-adding moves a mobject to the front; adding a group absorbs children
        # that were added on their own, and adding a child splits its group.
        self.mobjects = self._restructured(self.mobjects, family) + moving
        return self

    def _introduce(self, mobject):
        # Like Scene.add_mobjects_from_animations: on-screen members stay in place.
        if mobject not in self.get_mobject_family_members():
            self.add(mobject)

    def remove(self, *mobjects):
        self.mobjects = self._restructured(self.mobjects, mobjects)
        self.foreground_mobjects = self._restructured(self.foreground_mobjects, mobjects)
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
        def states(mobject):
            if overrides and mobject in overrides:
                return [_refresh_tip_shafts(state) for state in overrides[mobject]]
            if not overrides or not any(member in overrides for member in mobject.get_family()[1:]):
                return [mobject.to_dict()]
            # An animated member is drawn inside its on-screen group.
            data = mobject.to_dict()
            data['children'] = [state for child in mobject.children for state in states(child)]
            return [_refresh_tip_shafts(data)]
        for mobject in self.mobjects:
            if isinstance(mobject, (CameraFrame, ValueTracker)):
                continue
            objects.extend(states(mobject))
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
        if rate_func is not None:
            # play() options override each animation, as in Community.
            for animation in animations:
                animation.rate_func = rate_func
        for animation in animations:
            animation.prepare(self)
        for frame in range(count):
            time = frame / FPS
            overrides = {}
            for animation, duration in zip(animations, durations):
                overrides.update(animation.states(time / duration))
            self._update_mobjects(0 if frame == 0 else 1 / FPS, overrides)
            self.capture(overrides)
        # Update-function animations finish last, seeing their neighbors' final states as
        # Community's last frame does (e.g. MaintainPositionRelativeTo a moving object).
        for animation in sorted(animations, key=lambda a: isinstance(a, UpdateFromFunc)):
            animation._complete(self)
        self._update_mobjects(1 / FPS, {m: [m.to_dict()] for a in animations for m in a.objects()})
        # Community resumes the animated objects' updaters and runs update_mobjects(0),
        # so dependents such as Graph edges catch up with the committed state.
        self._update_mobjects(0)

    def validate(self, *animations):
        objects = [m for a in animations for m in a.objects()]
        def family(mobject):
            return [mobject] + [m for child in mobject.children for m in family(child)]
        members = [m for obj in objects for m in family(obj)]
        if len({id(m) for m in members}) != len(members):
            raise ValueError('Use one animation per object in each play() call')
        def ancestors(root, target, path=()):
            if root is target:
                return path
            for child in root.children:
                found = ancestors(child, target, path + (root,))
                if found is not None:
                    return found
            return None
        for root in self.mobjects:
            for obj in objects:
                chain = ancestors(root, obj) if obj is not root else None
                # Animated members are drawn inside their group, so their parents
                # must not add another pose to the animation's world coordinates.
                if chain and any(m.angle or m.geometry_scale != 1 or any(m.position) for m in chain):
                    raise NotImplementedError('Animate members of rotated or transformed groups '
                                              'by animating the whole group')

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
        def lay_out(node):
            if node.get('type') == 'text' and 'layout' not in node:
                node['layout'] = _text_layout(node)
            for child in node.get('children', []):
                lay_out(child)
        for frame in self.frames:
            for node in frame['mobjects']:
                lay_out(node)
        return {'frames': self.frames, 'fps': FPS, 'duration': (len(self.frames)-1)/FPS,
                'math_estimated': sorted(_MATH_ESTIMATED)}


class MovingCameraScene(Scene):
    camera_class = MovingCamera


DEFAULT_LAGGED_START_LAG_RATIO = 0.05


def line_intersection(line1, line2):
    """Community's XY intersection of two infinite lines, each given by two points."""
    (a, b), (c, d) = [[Vector(p) for p in line] for line in (line1, line2)]
    denominator = (a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0])
    if abs(denominator) < 1e-12:
        raise ValueError('The lines are parallel, there is no unique intersection point.')
    first, second = a[0] * b[1] - a[1] * b[0], c[0] * d[1] - c[1] * d[0]
    return Vector(((first * (c[0] - d[0]) - (a[0] - b[0]) * second) / denominator,
                   (first * (c[1] - d[1]) - (a[1] - b[1]) * second) / denominator, 0))


def angle_between_vectors(v1, v2):
    """Unsigned angle between two vectors, in [0, pi]."""
    v1, v2 = Vector(v1), Vector(v2)
    cross = (v1[1] * v2[2] - v1[2] * v2[1], v1[2] * v2[0] - v1[0] * v2[2], v1[0] * v2[1] - v1[1] * v2[0])
    return 2 * math.atan2(math.hypot(*cross), sum(a * b for a, b in zip(v1, v2)) +
                          math.sqrt(sum(a * a for a in v1) * sum(b * b for b in v2)))


class ScreenRectangle(Rectangle):
    def __init__(self, aspect_ratio=16.0 / 9.0, height=4, **kwargs):
        super().__init__(width=aspect_ratio * height, height=height, **kwargs)

    @property
    def aspect_ratio(self):
        return self.get_width() / self.get_height()

    @aspect_ratio.setter
    def aspect_ratio(self, value):
        self.stretch_to_fit_width(value * self.get_height())


class FullScreenRectangle(ScreenRectangle):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scale_to_fit_height(config.frame_height)


class VectorizedPoint(VMobject):
    """An invisible point with Community's artificial 0.01 width and height."""
    def __init__(self, location=ORIGIN, color=BLACK, fill_opacity=0, stroke_width=0,
                 artificial_width=0.01, artificial_height=0.01, **kwargs):
        super().__init__(color=color, fill_opacity=fill_opacity, stroke_width=stroke_width, **kwargs)
        self.artificial_width, self.artificial_height = artificial_width, artificial_height
        self.set_location(location)

    def get_width(self):
        return self.artificial_width

    def get_height(self):
        return self.artificial_height

    def get_location(self):
        return self.get_center()

    def set_location(self, new_loc):
        self.set_points_as_corners([new_loc, new_loc])
        return self


class ComplexValueTracker(ValueTracker):
    """A tracker for a complex number, stored as the x and y coordinates."""
    def get_value(self):
        return complex(self.position[0], self.position[1])

    def set_value(self, value):
        try:
            z = complex(value)
        except (TypeError, ValueError):
            raise ValueError('ComplexValueTracker requires a complex number') from None
        if not (math.isfinite(z.real) and math.isfinite(z.imag)):
            raise ValueError('ComplexValueTracker requires a finite complex number')
        self.position[0], self.position[1] = float(z.real), float(z.imag)
        return self

    def increment_value(self, d_value):
        return self.set_value(self.get_value() + complex(d_value))


class UnitInterval(NumberLine):
    def __init__(self, unit_size=10, numbers_with_elongated_ticks=None, decimal_number_config=None, **kwargs):
        super().__init__(x_range=(0, 1, 0.1), unit_size=unit_size,
                         numbers_with_elongated_ticks=[0, 1] if numbers_with_elongated_ticks is None
                         else numbers_with_elongated_ticks,
                         decimal_number_config={'num_decimal_places': 1} if decimal_number_config is None
                         else decimal_number_config, **kwargs)


class TangentialArc(ArcBetweenPoints):
    """An arc of the given radius tangent to two lines, in the corner chosen by signs."""
    def __init__(self, line1, line2, radius, corner=(1, 1), **kwargs):
        NumberLine._real(radius, 'TangentialArc radius', positive=True)
        intersection = line_intersection([line1.get_start(), line1.get_end()],
                                         [line2.get_start(), line2.get_end()])
        s1, s2 = corner
        unit1, unit2 = line1.get_unit_vector() * s1, line2.get_unit_vector() * s2
        corner_angle = angle_between_vectors(unit1, unit2)
        distance = radius / math.tan(corner_angle / 2)
        point1, point2 = intersection + unit1 * distance, intersection + unit2 * distance
        cross = unit1[0] * unit2[1] - unit1[1] * unit2[0]
        start, end = (point1, point2) if cross < 0 else (point2, point1)
        super().__init__(start=start, end=end, radius=radius, **kwargs)


class CurvesAsSubmobjects(VGroup):
    """Each cubic curve of a path as its own child, styled like the source."""
    def __init__(self, vmobject, **kwargs):
        super().__init__(**kwargs)
        parts = []
        for curve in vmobject.get_cubic_bezier_tuples():
            part = VMobject().set_points(list(curve))
            part.match_style(vmobject, family=False)
            parts.append(part)
        self.add(*parts)

    def point_from_proportion(self, alpha):
        if alpha < 0 or alpha > 1:
            raise ValueError(f'Alpha {alpha} not between 0 and 1.')
        parts = [part for part in self.children if not part.has_no_points()]
        if not parts:
            raise ValueError('CurvesAsSubmobjects has no submobjects with points')
        if alpha == 1:
            return Vector(parts[-1].get_points()[-1])
        lengths = [part.get_arc_length() for part in parts]
        target, current = alpha * sum(lengths), 0
        for part, length in zip(parts, lengths):
            if current + length >= target:
                return part.point_from_proportion((target - current) / length if length else 0)
            current += length
        return Vector(parts[-1].get_points()[-1])


class VDict(VGroup):
    """A VGroup addressed by keys; show_keys labels each value with a Tex key."""
    def __init__(self, mapping_or_iterable=None, show_keys=False, **kwargs):
        super().__init__(**kwargs)
        self.show_keys = show_keys
        self.submob_dict = {}
        self.add(mapping_or_iterable or {})

    def __repr__(self):
        return f'{type(self).__name__}({self.submob_dict!r})'

    def add(self, *mappings):
        # Group internals may still add plain children; keyed additions use mappings.
        if all(isinstance(m, Mobject) for m in mappings):
            return super().add(*mappings) if mappings else self
        if len(mappings) != 1:
            raise TypeError('VDict.add expects one mapping or iterable of (key, value) pairs')
        for key, value in dict(mappings[0]).items():
            self.add_key_value_pair(key, value)
        return self

    def remove(self, *keys):
        if keys and all(isinstance(k, Mobject) for k in keys):
            for mobject in keys:
                for key in [k for k, v in self.submob_dict.items() if v is mobject]:
                    del self.submob_dict[key]
            return super().remove(*keys)
        for key in keys:
            if key not in self.submob_dict:
                raise KeyError(f"The given key '{key!s}' is not present in the VDict")
            super().remove(self.submob_dict.pop(key))
        return self

    def __getitem__(self, key):
        if key in self.submob_dict:
            return self.submob_dict[key]
        if isinstance(key, (int, slice)) and not isinstance(key, bool):
            return super().__getitem__(key)
        raise KeyError(key)

    def __setitem__(self, key, value):
        if key in self.submob_dict:
            self.remove(key)
        self.add([(key, value)])

    def __delitem__(self, key):
        del self.submob_dict[key]

    def __contains__(self, key):
        return key in self.submob_dict

    def get_all_submobjects(self):
        return self.submob_dict.values()

    def add_key_value_pair(self, key, value):
        if not isinstance(value, Mobject):
            raise TypeError('VDict values must be Mobjects')
        if self.show_keys:
            value.add(Tex(str(key)).next_to(value, LEFT))
        self.submob_dict[key] = value
        super().add(value)
        return self


class Cutout(VMobject):
    """A main outline with holes: each cut is forced to the opposite winding."""
    def __init__(self, main_shape, *mobjects, **kwargs):
        super().__init__(**kwargs)
        self.append_points(main_shape.get_points())
        direction = 'CCW' if main_shape.get_direction() == 'CW' else 'CW'
        for mobject in mobjects:
            # Each hole is a separate, oppositely wound contour (nonzero fill leaves it empty).
            self.append_points(mobject.copy().force_direction(direction).get_points())


def _convex_hull(points):
    """Monotone-chain XY hull, counterclockwise from the lowest-leftmost vertex."""
    unique = sorted({(float(p[0]), float(p[1])) for p in points})
    if len(unique) < 3:
        raise ValueError('Not enough points supplied to build Convex Hull!')
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        raise ValueError('The points do not span the full coordinate dimension.')
    start = min(range(len(hull)), key=lambda i: (hull[i][1], hull[i][0]))
    return [Vector(point) for point in hull[start:] + hull[:start]]


class ConvexHull(Polygram):
    """The convex hull of XY points. Community's QuickHull vertex order depends on set
    hashing; this one is counterclockwise from the lowest-leftmost vertex."""
    def __init__(self, *points, tolerance=1e-5, **kwargs):
        for point in points:
            Mobject._xy_vector(point, 'ConvexHull point')
        super().__init__(_convex_hull(points), **kwargs)


class ArcBrace(Brace):
    """Community's brace bent around an Arc through the complex exponential map."""
    def __init__(self, arc=None, direction=RIGHT, **kwargs):
        if arc is None:
            arc = Arc(start_angle=-1, angle=2, radius=1)
        end_angle = arc.start_angle + arc.arc_angle
        line = Line(UP * arc.start_angle, UP * end_angle)
        radius = arc.radius * arc.geometry_scale
        if radius >= 1:
            line.scale(radius, about_point=ORIGIN)
            super().__init__(line, direction=direction, **kwargs)
            self.scale(1 / radius, about_point=ORIGIN)
        else:
            super().__init__(line, direction=direction, **kwargs)
        self.shift(RIGHT * math.log(radius if radius >= .3 else .3))
        self.apply_complex_function(cmath.exp)
        self.shift(arc.get_arc_center())


class LaggedStartMap(LaggedStart):
    def __init__(self, animation_class, mobject, arg_creator=None, run_time=2,
                 lag_ratio=DEFAULT_LAGGED_START_LAG_RATIO, **kwargs):
        arg_creator = arg_creator or (lambda mob: (mob,))
        kwargs.pop('lag_ratio', None)
        animations = [animation_class(*arg_creator(submob), **kwargs) for submob in mobject]
        super().__init__(*animations, run_time=run_time, lag_ratio=lag_ratio)


class MaintainPositionRelativeTo(UpdateFromFunc):
    """Keep a mobject's offset from a tracked mobject (which may be animated alongside)."""
    def __init__(self, mobject, tracked_mobject, **kwargs):
        self.tracked_mobject = tracked_mobject
        self.diff = mobject.get_center() - tracked_mobject.get_center()
        super().__init__(mobject, self._follow, **kwargs)

    def _follow(self, mobject):
        mobject.shift(self.tracked_mobject.get_center() - mobject.get_center() + self.diff)


class Blink(Succession):
    def __init__(self, mobject, time_on=0.5, time_off=0.5, blinks=1, hide_at_end=False, **kwargs):
        if isinstance(blinks, bool) or not isinstance(blinks, numbers.Integral) or not 1 <= blinks <= 100:
            raise ValueError('blinks must be an integer from 1 to 100')
        show = lambda: UpdateFromFunc(mobject, lambda mob: mob.set_opacity(1.0), run_time=time_on)
        hide = lambda: UpdateFromFunc(mobject, lambda mob: mob.set_opacity(0.0), run_time=time_off)
        animations = [anim for _ in range(blinks) for anim in (show(), hide())]
        if not hide_at_end:
            animations.append(show())
        super().__init__(*animations, **kwargs)


class Broadcast(LaggedStart):
    """Copies grow from a focal point while fading, like ripples."""
    def __init__(self, mobject, focal_point=ORIGIN, n_mobs=5, initial_opacity=1, final_opacity=0,
                 initial_width=0.0, remover=True, lag_ratio=0.2, run_time=3, **kwargs):
        if isinstance(n_mobs, bool) or not isinstance(n_mobs, numbers.Integral) or not 1 <= n_mobs <= 100:
            raise ValueError('n_mobs must be an integer from 1 to 100')
        self.focal_point, self.n_mobs = focal_point, n_mobs
        self.initial_opacity, self.final_opacity, self.initial_width = initial_opacity, final_opacity, initial_width
        filled = bool(mobject.fill_opacity)
        animations = []
        for _ in range(n_mobs):
            mob = mobject.copy()
            if filled:
                mob.set_opacity(final_opacity)
            else:
                mob.set_stroke(opacity=final_opacity)
            mob.move_to(focal_point)
            mob.save_state()
            mob.set(width=initial_width)
            if filled:
                mob.set_opacity(initial_opacity)
            else:
                mob.set_stroke(opacity=initial_opacity)
            animations.append(Restore(mob, remover=remover))
        super().__init__(*animations, run_time=run_time, lag_ratio=lag_ratio, **kwargs)


class SpiralIn(Animation):
    """Shapes spiral in from scaled-out positions, fading in over the first fraction."""
    def __init__(self, shapes, scale_factor=8, fade_in_fraction=0.3, **kwargs):
        NumberLine._real(fade_in_fraction, 'fade_in_fraction', positive=True)
        self.shapes = shapes.copy()
        self.scale_factor, self.fade_in_fraction = scale_factor, fade_in_fraction
        self.shape_center = shapes.get_center()
        self.moves = []
        for shape in shapes:
            final = shape.get_center()
            initial = final + (final - self.shape_center) * scale_factor
            shape.move_to(initial)
            self.moves.append((final, initial))
        super().__init__(shapes, introducer=True, **kwargs)

    def _place(self, group, alpha):
        for original, shape, (final, initial) in zip(self.shapes, group, self.moves):
            shape.move_to(initial)
            fill, stroke = original.fill_opacity, original.stroke_opacity
            shape.shift((final - initial) * alpha)
            shape.rotate(TAU * alpha, about_point=self.shape_center)
            shape.rotate(-TAU * alpha, about_point=shape.get_center_of_mass())
            shape.set_fill(opacity=min(fill, alpha * fill / self.fade_in_fraction))
            shape.set_stroke(opacity=min(stroke, alpha * stroke / self.fade_in_fraction))
        return group

    def sample(self, alpha):
        return [self._place(self.mobject.copy(), alpha).to_dict()]

    def finish(self, scene):
        self._place(self.mobject, 1)
        for shape, (final, _) in zip(self.mobject, self.moves):
            shape.move_to(final)  # A full turn returns each shape exactly home.


class AddTextWordByWord(AddTextLetterByLetter):
    """Reveal whole words of a Text in order (Community's version reveals characters)."""
    def __init__(self, text_mobject, run_time=None, time_per_char=0.06, **kwargs):
        super().__init__(text_mobject, run_time=run_time, time_per_char=time_per_char, **kwargs)
        self.word_ends = []
        count = 0
        for word in text_mobject.text.split():
            count += len(word)
            self.word_ends.append(count)

    def _shown(self, alpha, count):
        words = max(0, min(len(self.word_ends), int(self.int_func(alpha * len(self.word_ends)))))
        return min(count, self.word_ends[words - 1]) if words else 0


class _MT19937:
    """NumPy's legacy RandomState(seed) stream, as networkx layouts use for integer seeds."""
    def __init__(self, seed=0):
        if isinstance(seed, bool) or not isinstance(seed, numbers.Integral) or not 0 <= seed < 2 ** 32:
            raise ValueError('Layout seeds must be integers from 0 to 2**32 - 1')
        state = [int(seed)]
        for index in range(1, 624):
            previous = state[-1]
            state.append((1812433253 * (previous ^ (previous >> 30)) + index) & 0xFFFFFFFF)
        self._state, self._index = state, 624

    def _next32(self):
        if self._index >= 624:
            state = self._state
            for i in range(624):
                y = (state[i] & 0x80000000) | (state[(i + 1) % 624] & 0x7FFFFFFF)
                state[i] = state[(i + 397) % 624] ^ (y >> 1) ^ (0x9908B0DF if y & 1 else 0)
            self._index = 0
        y = self._state[self._index]
        self._index += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        return y ^ (y >> 18)

    def random_sample(self, count):
        return [((self._next32() >> 5) * 67108864.0 + (self._next32() >> 6)) / 9007199254740992.0
                for _ in range(count)]


def _float32(value):
    """Round to the nearest float32, as NumPy does for float32 arrays."""
    return struct.unpack('f', struct.pack('f', value))[0]


class _GraphData:
    """The networkx structure Community layouts consume: ordered nodes and adjacency."""
    def __init__(self, directed=False):
        self.directed, self._adj = directed, {}

    def __len__(self):
        return len(self._adj)

    def __iter__(self):
        return iter(self._adj)

    def __contains__(self, node):
        return node in self._adj

    @property
    def nodes(self):
        return list(self._adj)

    @property
    def edges(self):
        seen, result = set(), []
        for u, neighbors in self._adj.items():
            for v in neighbors:
                if self.directed or (v, u) not in seen:
                    seen.add((u, v))
                    result.append((u, v))
        return result

    def add_node(self, node):
        try:
            hash(node)
        except TypeError:
            raise TypeError('Graph vertices must be hashable') from None
        self._adj.setdefault(node, {})

    def add_edge(self, u, v):
        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = True
        if not self.directed:
            self._adj[v][u] = True

    def remove_node(self, node):
        del self._adj[node]
        for neighbors in self._adj.values():
            neighbors.pop(node, None)

    def remove_edge(self, u, v):
        self._adj[u].pop(v, None)
        if not self.directed:
            self._adj[v].pop(u, None)

    def neighbors(self, node):
        return list(self._adj[node])

    def is_tree(self):
        if not self._adj:
            return False
        undirected = {node: set() for node in self._adj}
        count = 0
        for u, v in self.edges:
            undirected[u].add(v)
            undirected[v].add(u)
            count += 1
        start = next(iter(undirected))
        seen, stack = {start}, [start]
        while stack:
            for other in undirected[stack.pop()]:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        return len(seen) == len(undirected) and count == len(undirected) - 1


def _rescale_layout(points, scale):
    """networkx rescale_layout: center on the mean, then fit the largest coordinate to scale."""
    count = len(points)
    means = [sum(p[i] for p in points) / count for i in range(2)]
    points = [[p[0] - means[0], p[1] - means[1]] for p in points]
    limit = max(abs(value) for p in points for value in p)
    if limit > 0:
        points = [[value * (scale / limit) for value in p] for p in points]
    return points


def _layout_scale(scale):
    if isinstance(scale, (tuple, list)):
        raise NotImplementedError('Per-axis layout scales are supported only by the tree layout')
    NumberLine._real(scale, 'layout_scale', nonnegative=True)
    return scale


def _circular_layout(graph, scale=2, center=None, dim=2):
    scale, nodes = _layout_scale(scale), graph.nodes
    if len(nodes) < 2:
        return {node: [0, 0] for node in nodes}
    # NumPy computes linspace(0, 1, n + 1) * 2pi, then rounds the angles to float32.
    angles = [_float32((i / len(nodes)) * 2 * math.pi) for i in range(len(nodes))]
    return dict(zip(nodes, _rescale_layout([[math.cos(a), math.sin(a)] for a in angles], scale)))


def _shell_layout(graph, nlist=None, rotate=None, scale=2, center=None, dim=2):
    scale, nodes = _layout_scale(scale), graph.nodes
    if len(nodes) < 2:
        return {node: [0, 0] for node in nodes}
    nlist = [list(nodes)] if nlist is None else [list(shell) for shell in nlist]
    bump = scale / len(nlist)
    radius = 0.0 if len(nlist[0]) == 1 else bump
    rotate = math.pi / len(nlist) if rotate is None else rotate
    first, result = rotate, {}
    for shell in nlist:
        for index, node in enumerate(shell):
            theta = _float32(2 * math.pi * index / len(shell)) + first
            result[node] = [radius * math.cos(theta), radius * math.sin(theta)]
        radius += bump
        first += rotate
    return result


def _spiral_layout(graph, scale=2, center=None, dim=2, resolution=0.35, equidistant=False):
    scale, nodes = _layout_scale(scale), graph.nodes
    if len(nodes) < 2:
        return {node: [0, 0] for node in nodes}
    points = []
    if equidistant:
        chord, step, theta = 1, 0.5, resolution
        theta += chord / (step * theta)
        for _ in nodes:
            r = step * theta
            theta += chord / r
            points.append([math.cos(theta) * r, math.sin(theta) * r])
    else:
        points = [[d * math.cos(resolution * d), d * math.sin(resolution * d)] for d in map(float, range(len(nodes)))]
    return dict(zip(nodes, _rescale_layout(points, scale)))


def _partite_layout(graph, scale=2, partitions=None, align='vertical', **kwargs):
    if not partitions:
        raise ValueError('The partite layout requires partitions parameter to contain the partition of the vertices')
    if kwargs:
        raise NotImplementedError('Unsupported partite layout options: ' + ', '.join(kwargs))
    scale, subset = _layout_scale(scale), {}
    for index, part in enumerate(partitions):
        for node in part:
            if node not in graph:
                raise ValueError('The partition must contain arrays of vertices in the graph')
            subset[node] = index
    layers = {}
    for node in graph:
        layers.setdefault(subset.get(node, len(partitions)), []).append(node)
    layers = dict(sorted(layers.items()))
    points, order = [], []
    for i, layer in enumerate(layers.values()):
        offset = ((len(layers) - 1) / 2, (len(layer) - 1) / 2)
        points += [[i - offset[0], y - offset[1]] for y in range(len(layer))]
        order += layer
    points = _rescale_layout(points, scale)
    if align == 'horizontal':
        points = [p[::-1] for p in points]
    return dict(zip(order, points))


def _random_layout(graph, scale=2, seed=None, center=None, dim=2):
    scale = _layout_scale(scale)
    # Community leaves the seed to NumPy's global generator; previews default to 0.
    values = _MT19937(0 if seed is None else seed).random_sample(2 * len(graph))
    return {node: [2 * scale * (_float32(values[2 * i]) - .5), 2 * scale * (_float32(values[2 * i + 1]) - .5)]
            for i, node in enumerate(graph)}


def _spring_layout(graph, k=None, pos=None, fixed=None, iterations=50, threshold=1e-4, weight='weight',
                   scale=2, center=None, dim=2, seed=None, method='auto', gravity=1.0):
    """networkx's dense Fruchterman-Reingold spring layout with a RandomState seed."""
    if pos is not None or fixed is not None or method == 'energy':
        raise NotImplementedError('Spring layouts support seed, k, iterations and threshold options')
    scale, nodes = _layout_scale(scale), graph.nodes
    n = len(nodes)
    if n > 500:
        raise ValueError('Spring layouts are limited to 500 vertices')
    if n < 2:
        return {node: [0, 0] for node in nodes}
    if isinstance(iterations, bool) or not isinstance(iterations, numbers.Integral) or not 0 <= iterations <= 1000:
        raise ValueError('Spring layout iterations must be an integer from 0 to 1000')
    index = {node: i for i, node in enumerate(nodes)}
    adjacency = [[0.0] * n for _ in range(n)]
    for u, v in graph.edges:
        adjacency[index[u]][index[v]] = 1.0
        if not graph.directed:
            adjacency[index[v]][index[u]] = 1.0
    # Community leaves the seed to NumPy's global generator; previews default to 0.
    values = _MT19937(0 if seed is None else seed).random_sample(2 * n)
    pos = [[values[2 * i], values[2 * i + 1]] for i in range(n)]
    k = math.sqrt(1.0 / n) if k is None else k
    t = max(max(p[0] for p in pos) - min(p[0] for p in pos), max(p[1] for p in pos) - min(p[1] for p in pos)) * .1
    dt = t / (iterations + 1)
    for _ in range(iterations):
        moves = []
        for i in range(n):
            dx = dy = 0.0
            xi, yi, row = pos[i][0], pos[i][1], adjacency[i]
            for j in range(n):
                ex, ey = xi - pos[j][0], yi - pos[j][1]
                distance = max(.01, math.hypot(ex, ey))
                force = k * k / distance ** 2 - row[j] * distance / k
                dx += ex * force
                dy += ey * force
            length = max(.01, math.hypot(dx, dy))
            moves.append((dx * t / length, dy * t / length))
        for p, (mx, my) in zip(pos, moves):
            p[0] += mx
            p[1] += my
        t -= dt
        if math.sqrt(sum(mx * mx + my * my for mx, my in moves)) / n < threshold:
            break
    return dict(zip(nodes, _rescale_layout(pos, scale)))


def _tree_layout(tree, root_vertex=None, scale=2, vertex_spacing=None, orientation='down'):
    """Community's port of SageMath's tree layout."""
    if root_vertex is None:
        raise ValueError('The tree layout requires the root_vertex parameter')
    if not tree.is_tree():
        raise ValueError('The tree layout must be used with trees')
    children = {root_vertex: tree.neighbors(root_vertex)}
    stack, stick = [list(children[root_vertex])], [root_vertex]
    parent = dict.fromkeys(children[root_vertex], root_vertex)
    pos, obstruction = {}, [0.0] * len(tree)
    o = -1 if orientation == 'down' else 1
    def slide(v, dx):
        level = [v]
        while level:
            following = []
            for u in level:
                x, y = pos[u]
                x += dx
                obstruction[y] = max(x + 1, obstruction[y])
                pos[u] = x, y
                following += children[u]
            level = following
    while stack:
        current = stack[-1]
        if not current:
            p = stick.pop()
            stack.pop()
            cp = children[p]
            y = o * len(stack)
            if not cp:
                x = obstruction[y]
                pos[p] = x, y
            else:
                x = sum(pos[c][0] for c in cp) / float(len(cp))
                pos[p] = x, y
                ox = obstruction[y]
                if x < ox:
                    slide(p, ox - x)
                    x = ox
            obstruction[y] = x + 1
            continue
        t = current.pop()
        pt = parent[t]
        ct = [u for u in tree.neighbors(t) if u != pt]
        for c in ct:
            parent[c] = t
        children[t] = list(ct)
        stack.append(ct)
        stick.append(t)
    xs, ys = [p[0] for p in pos.values()], [p[1] for p in pos.values()]
    center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    if vertex_spacing is None:
        if isinstance(scale, _REAL) and (width > 0 or height > 0):
            sx = sy = 2 * scale / max(width, height)
        elif isinstance(scale, (tuple, list)):
            sx = 2 * scale[0] / width if scale[0] is not None and width > 0 else 1
            sy = 2 * scale[1] / height if scale[1] is not None and height > 0 else 1
        else:
            sx = sy = 1
    else:
        sx, sy = vertex_spacing
    return {v: [(x - center[0]) * sx, (y - center[1]) * sy] for v, (x, y) in pos.items()}


_GRAPH_LAYOUTS = {'circular': _circular_layout, 'shell': _shell_layout, 'spiral': _spiral_layout,
                  'partite': _partite_layout, 'random': _random_layout, 'spring': _spring_layout,
                  'tree': _tree_layout}


def _determine_graph_layout(graph, layout='spring', layout_scale=2, layout_config=None):
    layout_config = {} if layout_config is None else dict(layout_config)
    if isinstance(layout, dict):
        return {node: Vector(point) for node, point in layout.items()}
    if isinstance(layout, str):
        if layout in ('kamada_kawai', 'planar', 'spectral'):
            raise NotImplementedError(f"The '{layout}' layout needs NumPy/SciPy solvers; "
                                      'use circular, shell, spiral, spring, random, partite, tree or a dict')
        if layout not in _GRAPH_LAYOUTS:
            raise ValueError(f"The layout '{layout}' is neither a recognized layout, a layout function,"
                             'nor a vertex placement dictionary.')
        if layout_config.pop('dim', 2) != 2:
            raise NotImplementedError('Graph layouts are two-dimensional in the browser preview')
        result = _GRAPH_LAYOUTS[layout](graph, scale=layout_scale, **layout_config)
        return {node: Vector((point[0], point[1], 0)) for node, point in result.items()}
    if callable(layout):
        # Custom layouts receive the browser graph structure (nodes, edges, neighbors), not networkx.
        result = layout(graph, scale=layout_scale, **layout_config)
        return {node: Vector(point) for node, point in result.items()}
    raise ValueError(f"The layout '{layout}' is neither a recognized layout, a layout function,"
                     'nor a vertex placement dictionary.')


class _GraphAnimationGroup(AnimationGroup):
    """An AnimationGroup that runs a callback after its stages finish (Community's _on_finish)."""
    def __init__(self, *animations, on_finish=None, **kwargs):
        super().__init__(*animations, **kwargs)
        self._on_finish = on_finish

    def finish(self, scene):
        super().finish(scene)
        if self._on_finish is not None:
            self._on_finish(scene)


class GenericGraph(VGroup):
    """Community's Graph base: vertex and edge mobjects kept attached by an updater."""
    _frame_excluded = ('_graph', '_layout', '_labels', '_vertex_config', '_edge_config', '_tip_config',
                       'default_vertex_config', 'default_edge_config')
    _animate_overrides = {'add_vertices': '_add_vertices_animation', 'remove_vertices': '_remove_vertices_animation',
                          'add_edges': '_add_edges_animation', 'remove_edges': '_remove_edges_animation'}
    _directed = False

    def __init__(self, vertices, edges, labels=False, label_fill_color=BLACK, layout='spring', layout_scale=2,
                 layout_config=None, vertex_type=Dot, vertex_config=None, vertex_mobjects=None, edge_type=Line,
                 partitions=None, root_vertex=None, edge_config=None):
        super().__init__()
        vertices, edges = list(vertices), [tuple(e) for e in edges]
        if len(vertices) > 500 or len(edges) > 5000:
            raise ValueError('Graphs are limited to 500 vertices and 5000 edges')
        graph = _GraphData(self._directed)
        for vertex in vertices:
            graph.add_node(vertex)
        for edge in edges:
            if len(edge) != 2:
                raise ValueError('Graph edges must be pairs of vertices')
            graph.add_edge(*edge)
        self._graph = graph
        if isinstance(labels, dict):
            self._labels = labels
        elif isinstance(labels, bool):
            self._labels = {v: MathTex(str(v), color=label_fill_color) for v in vertices} if labels else {}
        else:
            raise TypeError('Graph labels must be a boolean or a dictionary')
        if self._labels and vertex_type is Dot:
            vertex_type = LabeledDot
        vertex_mobjects = vertex_mobjects or {}
        vertex_config = vertex_config or {}
        default_vertex_config = {k: v for k, v in vertex_config.items() if k not in vertices}
        self._vertex_config = {v: vertex_config.get(v, dict(default_vertex_config)) for v in vertices}
        self.default_vertex_config = default_vertex_config
        for v, label in self._labels.items():
            self._vertex_config[v]['label'] = label
        self.vertices = {v: vertex_type(**self._vertex_config[v]) for v in vertices}
        self.vertices.update(vertex_mobjects)
        self.change_layout(layout=layout, layout_scale=layout_scale, layout_config=layout_config,
                           partitions=partitions, root_vertex=root_vertex)
        edge_config = dict(edge_config or {})
        default_tip_config = edge_config.pop('tip_config', {})
        default_edge_config = {k: v for k, v in edge_config.items() if not isinstance(k, tuple)}
        self._edge_config, self._tip_config = {}, {}
        for e in edges:
            if e in edge_config:
                config = dict(edge_config[e])
                self._tip_config[e] = config.pop('tip_config', dict(default_tip_config))
                self._edge_config[e] = config
            else:
                self._tip_config[e] = dict(default_tip_config)
                self._edge_config[e] = dict(default_edge_config)
        self.default_edge_config = default_edge_config
        self._populate_edge_dict(edges, edge_type)
        self.add(*self.vertices.values())
        self.add(*self.edges.values())
        self.add_updater(self.update_edges)

    def __getitem__(self, k):
        try:
            if k in self.vertices:
                return self.vertices[k]
            if k in self.edges:
                return self.edges[k]
        except TypeError:
            pass
        if isinstance(k, (int, slice)) and not isinstance(k, bool):
            return super().__getitem__(k)  # Positional access for group internals.
        raise ValueError(f'Could not find {k} in vertices or edges')

    def _make_edge(self, u, v, edge_type, config, tip_config=None):
        raise NotImplementedError('To be implemented in concrete subclasses')

    def _populate_edge_dict(self, edges, edge_type):
        self.edges = {(u, v): self._make_edge(u, v, edge_type, self._edge_config[(u, v)], self._tip_config[(u, v)])
                      for u, v in edges}

    def _create_vertex(self, vertex, position=None, label=False, label_fill_color=BLACK, vertex_type=Dot,
                       vertex_config=None, vertex_mobject=None):
        position = self.get_center() if position is None else Vector(position)
        if vertex in self.vertices:
            raise ValueError(f"Vertex identifier '{vertex}' is already used for a vertex in this graph.")
        if label is True:
            label = MathTex(str(vertex), color=label_fill_color)
        elif vertex in self._labels:
            label = self._labels[vertex]
        elif not isinstance(label, Mobject):
            label = None
        config = dict(self.default_vertex_config)
        config.update(vertex_config or {})
        if label is not None:
            config['label'] = label
            if vertex_type is Dot:
                vertex_type = LabeledDot
        if vertex_mobject is None:
            vertex_mobject = vertex_type(**config)
        vertex_mobject.move_to(position)
        return vertex, position, config, vertex_mobject

    def _add_created_vertex(self, vertex, position, vertex_config, vertex_mobject):
        if vertex in self.vertices:
            raise ValueError(f"Vertex identifier '{vertex}' is already used for a vertex in this graph.")
        self._graph.add_node(vertex)
        self._layout[vertex] = position
        if 'label' in vertex_config:
            self._labels[vertex] = vertex_config['label']
        self._vertex_config[vertex] = vertex_config
        self.vertices[vertex] = vertex_mobject
        vertex_mobject.move_to(position)
        self.add(vertex_mobject)
        return vertex_mobject

    def _add_vertex(self, vertex, position=None, **kwargs):
        return self._add_created_vertex(*self._create_vertex(vertex, position=position, **kwargs))

    def _create_vertices(self, *vertices, positions=None, labels=False, label_fill_color=BLACK, vertex_type=Dot,
                         vertex_config=None, vertex_mobjects=None):
        base_positions = dict.fromkeys(vertices, self.get_center())
        base_positions.update(positions or {})
        positions = base_positions
        vertex_mobjects = vertex_mobjects or {}
        if isinstance(labels, bool):
            labels = dict.fromkeys(vertices, labels)
        else:
            base_labels = dict.fromkeys(vertices, False)
            base_labels.update(labels)
            labels = base_labels
        vertex_config = dict(self.default_vertex_config) if vertex_config is None else vertex_config
        base = dict(self.default_vertex_config)
        base.update({key: val for key, val in vertex_config.items() if key not in vertices})
        configs = {v: vertex_config[v] if v in vertex_config else dict(base) for v in vertices}
        return [self._create_vertex(v, position=positions[v], label=labels[v], label_fill_color=label_fill_color,
                                    vertex_type=vertex_type, vertex_config=configs[v],
                                    vertex_mobject=vertex_mobjects.get(v)) for v in vertices]

    def add_vertices(self, *vertices, **kwargs):
        return [self._add_created_vertex(*v) for v in self._create_vertices(*vertices, **kwargs)]

    def _add_vertices_animation(self, *args, anim_args=None, **kwargs):
        anim_args = dict(anim_args or {})
        animation = anim_args.pop('animation', Create)
        created = self._create_vertices(*args, **kwargs)
        def on_finish(scene):
            for entry in created:
                scene.remove(entry[-1])
                self._add_created_vertex(*entry)
        return _GraphAnimationGroup(*(animation(entry[-1], **anim_args) for entry in created), on_finish=on_finish)

    def _remove_vertex(self, vertex):
        if vertex not in self.vertices:
            raise ValueError(f"The graph does not contain a vertex with identifier '{vertex}'")
        self._graph.remove_node(vertex)
        self._layout.pop(vertex)
        self._labels.pop(vertex, None)
        self._vertex_config.pop(vertex)
        edge_tuples = [e for e in self.edges if vertex in e]
        for e in edge_tuples:
            self._edge_config.pop(e)
        removed = [self.edges.pop(e) for e in edge_tuples]
        removed.append(self.vertices.pop(vertex))
        self.remove(*removed)
        return removed

    def remove_vertices(self, *vertices):
        return self.get_group_class()(*(m for v in vertices for m in self._remove_vertex(v)))

    def _remove_vertices_animation(self, *vertices, anim_args=None):
        anim_args = dict(anim_args or {})
        animation = anim_args.pop('animation', Uncreate)
        return AnimationGroup(*(animation(m, **anim_args) for m in self.remove_vertices(*vertices)))

    def _add_edge(self, edge, edge_type=Line, edge_config=None):
        edge_config = dict(self.default_edge_config) if edge_config is None else edge_config
        added = [self._add_vertex(v) for v in edge if v not in self.vertices]
        u, v = edge
        self._graph.add_edge(u, v)
        config = dict(self.default_edge_config)
        config.update(edge_config)
        tip_config = config.pop('tip_config', {})
        self._edge_config[(u, v)], self._tip_config[(u, v)] = config, tip_config
        mobject = self._make_edge(u, v, edge_type, config, tip_config)
        self.edges[(u, v)] = mobject
        self.add(mobject)
        return added + [mobject]

    def add_edges(self, *edges, edge_type=Line, edge_config=None, **kwargs):
        edges = [tuple(e) for e in edges]
        edge_config = edge_config or {}
        base = dict(self.default_edge_config)
        base.update({k: v for k, v in edge_config.items() if k not in edges})
        configs = {}
        for e in edges:
            configs[e] = dict(base)
            configs[e].update(edge_config.get(e, {}))
        new_vertices = [v for v in dict.fromkeys(v for e in edges for v in e) if v not in self.vertices]
        added = self.add_vertices(*new_vertices, **kwargs)
        for edge in edges:
            added += self._add_edge(edge, edge_type=edge_type, edge_config=configs[edge])[-1:]
        return self.get_group_class()(*added)

    def _add_edges_animation(self, *args, anim_args=None, **kwargs):
        anim_args = dict(anim_args or {})
        animation = anim_args.pop('animation', Create)
        return AnimationGroup(*(animation(m, **anim_args) for m in self.add_edges(*args, **kwargs)))

    def _remove_edge(self, edge):
        if edge not in self.edges:
            raise ValueError(f"The graph does not contain a edge '{edge}'")
        mobject = self.edges.pop(edge)
        self._graph.remove_edge(*edge)
        self._edge_config.pop(edge, None)
        self.remove(mobject)
        return mobject

    def remove_edges(self, *edges):
        return self.get_group_class()(*(self._remove_edge(tuple(e)) for e in edges))

    def _remove_edges_animation(self, *edges, anim_args=None):
        anim_args = dict(anim_args or {})
        animation = anim_args.pop('animation', Uncreate)
        return AnimationGroup(*(animation(m, **anim_args) for m in self.remove_edges(*edges)))

    @classmethod
    def from_networkx(cls, nxgraph, **kwargs):
        return cls(list(nxgraph.nodes), list(nxgraph.edges), **kwargs)

    def change_layout(self, layout='spring', layout_scale=2, layout_config=None, partitions=None, root_vertex=None):
        layout_config = {} if layout_config is None else dict(layout_config)
        if partitions is not None and 'partitions' not in layout_config:
            layout_config['partitions'] = partitions
        if root_vertex is not None and 'root_vertex' not in layout_config:
            layout_config['root_vertex'] = root_vertex
        self._layout = _determine_graph_layout(self._graph, layout=layout, layout_scale=layout_scale,
                                               layout_config=layout_config)
        for v in self.vertices:
            self[v].move_to(self._layout[v])
        return self


class Graph(GenericGraph):
    """An undirected graph whose Line edges follow their vertices' centers."""
    def _make_edge(self, u, v, edge_type, config, tip_config=None):
        return edge_type(start=self[u].get_center(), end=self[v].get_center(), z_index=-1, **config)

    def update_edges(self, graph):
        for (u, v), edge in graph.edges.items():
            # Community looks up "buff"/"path_arc" in the per-edge table, so both stay 0.
            edge.set_points_by_ends(graph[u].get_center(), graph[v].get_center(), buff=0, path_arc=0)
        return self

    def __repr__(self):
        return f'Undirected graph on {len(self.vertices)} vertices and {len(self.edges)} edges'


class DiGraph(GenericGraph):
    """A directed graph: arrow tips stop at the target vertex's boundary."""
    _directed = True

    def _make_edge(self, u, v, edge_type, config, tip_config=None):
        edge = edge_type(start=self[u], end=self[v], z_index=-1, **config)
        edge.add_tip(**(tip_config or {}))
        return edge

    def update_edges(self, graph):
        for (u, v), edge in graph.edges.items():
            tip = edge.pop_tips()[0]
            edge.set_points_by_ends(graph[u], graph[v], buff=0, path_arc=0)
            edge.add_tip(tip)
        return self

    def __repr__(self):
        return f'Directed graph on {len(self.vertices)} vertices and {len(self.edges)} edges'


def _bez(c, t):
    s = 1 - t
    return (s * s * s * c[0][0] + 3 * s * s * t * c[1][0] + 3 * s * t * t * c[2][0] + t * t * t * c[3][0],
            s * s * s * c[0][1] + 3 * s * s * t * c[1][1] + 3 * s * t * t * c[2][1] + t * t * t * c[3][1])


def _bez_tangent(c, t):
    s = 1 - t
    return (3 * s * s * (c[1][0] - c[0][0]) + 6 * s * t * (c[2][0] - c[1][0]) + 3 * t * t * (c[3][0] - c[2][0]),
            3 * s * s * (c[1][1] - c[0][1]) + 6 * s * t * (c[2][1] - c[1][1]) + 3 * t * t * (c[3][1] - c[2][1]))


def _bez_split(c, t):
    lerp = lambda p, q: (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    a, b, e = lerp(c[0], c[1]), lerp(c[1], c[2]), lerp(c[2], c[3])
    d, f = lerp(a, b), lerp(b, e)
    m = lerp(d, f)
    return (c[0], a, d, m), (m, f, e, c[3])


def _bez_box(c):
    xs, ys = [p[0] for p in c], [p[1] for p in c]
    return min(xs), min(ys), max(xs), max(ys)


def _bez_flat(c, tol):
    """True when both handles lie within tol of the chord (a straight segment)."""
    (x0, y0), (x3, y3) = c[0], c[3]
    dx, dy = x3 - x0, y3 - y0
    length = math.hypot(dx, dy)
    if length < tol:
        return all(math.hypot(p[0] - x0, p[1] - y0) < tol for p in c)
    return all(abs((p[0] - x0) * dy - (p[1] - y0) * dx) / length < tol for p in (c[1], c[2]))


def _segment_hits(p0, p1, q0, q1, tol):
    """Parameters (s, u) where segments p and q meet, including collinear overlap ends."""
    rx, ry = p1[0] - p0[0], p1[1] - p0[1]
    sx, sy = q1[0] - q0[0], q1[1] - q0[1]
    denom = rx * sy - ry * sx
    qpx, qpy = q0[0] - p0[0], q0[1] - p0[1]
    rr, ss = rx * rx + ry * ry, sx * sx + sy * sy
    if rr < tol * tol or ss < tol * tol:
        return []
    if abs(denom) <= 1e-12 * math.sqrt(rr * ss):
        # Parallel: only collinear overlaps meet; report the overlap's ends on both.
        if abs(qpx * ry - qpy * rx) / math.sqrt(rr) > tol:
            return []
        hits = []
        for point in (q0, q1):
            s = ((point[0] - p0[0]) * rx + (point[1] - p0[1]) * ry) / rr
            if -1e-9 <= s <= 1 + 1e-9:
                hits.append((min(1, max(0, s)), 0.0 if point is q0 else 1.0))
        for point in (p0, p1):
            u = ((point[0] - q0[0]) * sx + (point[1] - q0[1]) * sy) / ss
            if -1e-9 <= u <= 1 + 1e-9:
                hits.append((0.0 if point is p0 else 1.0, min(1, max(0, u))))
        return hits
    s = (qpx * sy - qpy * sx) / denom
    u = (qpx * ry - qpy * rx) / denom
    if -1e-9 <= s <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return [(min(1, max(0, s)), min(1, max(0, u)))]
    return []


def _cubic_hits(a, b, tol, ta=(0.0, 1.0), tb=(0.0, 1.0), depth=0, out=None):
    """Intersection parameter pairs of two cubics, by recursive subdivision."""
    out = [] if out is None else out
    ax0, ay0, ax1, ay1 = _bez_box(a)
    bx0, by0, bx1, by1 = _bez_box(b)
    if ax0 > bx1 + tol or bx0 > ax1 + tol or ay0 > by1 + tol or by0 > ay1 + tol or len(out) > 64:
        return out
    if (_bez_flat(a, tol) and _bez_flat(b, tol)) or depth > 48:
        for s, u in _segment_hits(a[0], a[3], b[0], b[3], tol):
            out.append((ta[0] + s * (ta[1] - ta[0]), tb[0] + u * (tb[1] - tb[0])))
        return out
    asize, bsize = max(ax1 - ax0, ay1 - ay0), max(bx1 - bx0, by1 - by0)
    if asize >= bsize and not _bez_flat(a, tol):
        mid = (ta[0] + ta[1]) / 2
        left, right = _bez_split(a, .5)
        _cubic_hits(left, b, tol, (ta[0], mid), tb, depth + 1, out)
        _cubic_hits(right, b, tol, (mid, ta[1]), tb, depth + 1, out)
    else:
        mid = (tb[0] + tb[1]) / 2
        left, right = _bez_split(b, .5)
        _cubic_hits(a, left, tol, ta, (tb[0], mid), depth + 1, out)
        _cubic_hits(a, right, tol, ta, (mid, tb[1]), depth + 1, out)
    return out


def _boolean_contours(mobject):
    """Closed XY cubic contours of a VMobject's own outline (Community ignores its family)."""
    if not isinstance(mobject, Mobject):
        raise TypeError('Boolean operations expect VMobjects')
    contours = []
    for path in mobject.get_subpaths():
        curves = [tuple((float(p[0]), float(p[1])) for p in path[i:i + 4]) for i in range(0, len(path) - 3, 4)]
        if not curves:
            continue
        if math.dist(curves[-1][3], curves[0][0]) > 1e-9:
            start, end = curves[-1][3], curves[0][0]
            curves.append((start, tuple(start[i] + (end[i] - start[i]) / 3 for i in range(2)),
                           tuple(start[i] + (end[i] - start[i]) * 2 / 3 for i in range(2)), end))
        contours.append(curves)
    # Orient so the shape's total signed area is positive (outer contours counterclockwise).
    area = sum(_contour_area(c) for c in contours)
    if area < 0:
        contours = [[tuple(reversed(curve)) for curve in reversed(c)] for c in contours]
    return contours


def _contour_area(curves):
    total = 0.0
    for curve in curves:
        points = [_bez(curve, i / 8) for i in range(9)]
        total += sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(points, points[1:])) / 2
    return total


def _flatten(contours, steps=32):
    return [[_bez(curve, i / steps) for curve in contour for i in range(steps)] for contour in contours]


def _winding(point, polygons):
    x, y, winding = point[0], point[1], 0
    for polygon in polygons:
        for (x0, y0), (x1, y1) in zip(polygon, polygon[1:] + polygon[:1]):
            if y0 <= y < y1 and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) > 0:
                winding += 1
            elif y1 <= y < y0 and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) < 0:
                winding -= 1
    return winding


def _nearest_on(point, contours):
    """Distance from point to the nearest contour curve, and that curve's tangent there."""
    best = (math.inf, None, None)
    for contour in contours:
        for curve in contour:
            x0, y0, x1, y1 = _bez_box(curve)
            if point[0] < x0 - best[0] or point[0] > x1 + best[0] or point[1] < y0 - best[0] or point[1] > y1 + best[0]:
                continue
            t = min((i / 16 for i in range(17)), key=lambda s: math.dist(_bez(curve, s), point))
            for _ in range(6):
                # Newton steps on the squared distance.
                p, d = _bez(curve, t), _bez_tangent(curve, t)
                h = 1e-6
                d2 = _bez_tangent(curve, min(1, t + h))
                dd = ((d2[0] - d[0]) / h, (d2[1] - d[1]) / h)
                f = (p[0] - point[0]) * d[0] + (p[1] - point[1]) * d[1]
                g = d[0] * d[0] + d[1] * d[1] + (p[0] - point[0]) * dd[0] + (p[1] - point[1]) * dd[1]
                if not g:
                    break
                t = min(1, max(0, t - f / g))
            distance = math.dist(_bez(curve, t), point)
            if distance < best[0]:
                best = (distance, _bez_tangent(curve, t), curve)
    return best


def _boolean_pieces(contours, others, tol):
    """Split contours at every crossing with the other shape's contours."""
    cuts = {}
    for ci, contour in enumerate(contours):
        for ki, curve in enumerate(contour):
            for other in others:
                for curve_b in other:
                    for ta, _ in _cubic_hits(curve, curve_b, tol):
                        cuts.setdefault((ci, ki), []).append(ta)
    result = []
    for ci, contour in enumerate(contours):
        pieces = []
        for ki, curve in enumerate(contour):
            ts = sorted(t for t in cuts.get((ci, ki), []) if 1e-9 < t < 1 - 1e-9)
            last, rest = 0.0, curve
            for t in ts:
                if t - last < 1e-9:
                    continue
                left, rest = _bez_split(rest, (t - last) / (1 - last))
                pieces.append(left)
                last = t
            pieces.append(rest)
        result.append(pieces)
    return result


def _classify(pieces, other_contours, tol):
    polygons = _flatten(other_contours)
    labels = []
    for contour in pieces:
        for piece in contour:
            mid = _bez(piece, .5)
            distance, tangent, _ = _nearest_on(mid, other_contours)
            if distance < tol * 100 and tangent is not None:
                own = _bez_tangent(piece, .5)
                labels.append((piece, 'same' if own[0] * tangent[0] + own[1] * tangent[1] > 0 else 'opposite'))
            else:
                labels.append((piece, 'inside' if _winding(mid, polygons) else 'outside'))
    return labels


def _link_contours(pieces, tol):
    """Chain kept pieces end-to-start into closed contours."""
    key = lambda p: (round(p[0] / (tol * 1000)), round(p[1] / (tol * 1000)))
    starts = {}
    for index, piece in enumerate(pieces):
        starts.setdefault(key(piece[0]), []).append(index)
    used, loops = set(), []
    def nearby(point):
        kx, ky = key(point)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for index in starts.get((kx + dx, ky + dy), []):
                    if index not in used and math.dist(pieces[index][0], point) < tol * 1000:
                        yield index
    for first in range(len(pieces)):
        if first in used:
            continue
        loop, current = [], first
        while current is not None:
            used.add(current)
            loop.append(pieces[current])
            if math.dist(loop[-1][3], loop[0][0]) < tol * 1000 and len(loop) > 1:
                break
            current = next(nearby(loop[-1][3]), None)
        # Close exactly: snap every join (and the seam) to a shared point.
        for i in range(len(loop)):
            following = loop[(i + 1) % len(loop)]
            joint = loop[i][3] if i + 1 < len(loop) or math.dist(loop[i][3], following[0]) < tol * 1000 else None
            if joint is not None:
                loop[(i + 1) % len(loop)] = (joint,) + tuple(following[1:])
        if sum(math.dist(c[0], c[3]) for c in loop) > tol:
            loops.append(loop)
    return loops


def _boolean(subject, clip, keep):
    """keep maps (own 'A'/'B', label) to None (drop), 1 (keep) or -1 (keep reversed)."""
    scale = max([1.0] + [abs(v) for c in subject + clip for curve in c for p in curve for v in p])
    tol = 1e-9 * scale
    kept = []
    for own, contours, others in (('A', subject, clip), ('B', clip, subject)):
        for piece, label in _classify(_boolean_pieces(contours, others, tol), others, tol):
            action = keep.get((own, label))
            if action:
                kept.append(piece if action > 0 else tuple(reversed(piece)))
    return _link_contours(kept, tol)


_BOOLEAN_RULES = {
    'union': {('A', 'outside'): 1, ('B', 'outside'): 1, ('A', 'same'): 1},
    'intersection': {('A', 'inside'): 1, ('B', 'inside'): 1, ('A', 'same'): 1},
    'difference': {('A', 'outside'): 1, ('B', 'inside'): -1, ('A', 'opposite'): 1},
    'exclusion': {('A', 'outside'): 1, ('B', 'outside'): 1, ('A', 'inside'): -1, ('B', 'inside'): -1},
}


class _BooleanOps(VMobject):
    """Shared construction: run the operation, then store cubic contours."""
    def _set_contours(self, contours):
        points = [list(p) + [0] for contour in contours for curve in contour for p in curve]
        VMobject.set_points(self, points)
        self.__dict__.pop('subpath_lengths', None)
        if len(contours) > 1:
            self.subpath_lengths = [len(contour) for contour in contours]
        return self

    @staticmethod
    def _operate(name, first, second):
        if isinstance(first, list):
            subject = first
        else:
            subject = _boolean_contours(first)
        return _boolean(subject, _boolean_contours(second), _BOOLEAN_RULES[name])


class Union(_BooleanOps):
    """The region covered by any of the given outlines (sequential pairwise union)."""
    def __init__(self, *vmobjects, **kwargs):
        if len(vmobjects) < 2:
            raise ValueError('At least 2 mobjects needed for Union.')
        super().__init__(**kwargs)
        contours = _boolean_contours(vmobjects[0])
        for vmobject in vmobjects[1:]:
            contours = self._operate('union', contours, vmobject)
        self._set_contours(contours)


class Intersection(_BooleanOps):
    """The region covered by every given outline."""
    def __init__(self, *vmobjects, **kwargs):
        if len(vmobjects) < 2:
            raise ValueError('At least 2 mobjects needed for Intersection.')
        super().__init__(**kwargs)
        contours = _boolean_contours(vmobjects[0])
        for vmobject in vmobjects[1:]:
            contours = self._operate('intersection', contours, vmobject)
        self._set_contours(contours)


class Difference(_BooleanOps):
    """The subject's region outside the clip outline."""
    def __init__(self, subject, clip, **kwargs):
        super().__init__(**kwargs)
        self._set_contours(self._operate('difference', subject, clip))


class Exclusion(_BooleanOps):
    """The region covered by exactly one of the two outlines."""
    def __init__(self, subject, clip, **kwargs):
        super().__init__(**kwargs)
        self._set_contours(self._operate('exclusion', subject, clip))


def _code_tokens(code_string, language, formatter_style):
    """(lines, per-character colors, foreground, line-number color, background) via Pygments.

    The worker loads Pygments for sources that use Code; without it the listing is
    drawn in the style's plain foreground on a black background."""
    lines = code_string.strip('\n').split('\n')  # Pygments lexers strip outer newlines.
    try:
        from pygments import lex
        from pygments.lexers import get_lexer_by_name, guess_lexer
        from pygments.styles import get_style_by_name
        from pygments.token import Text as TextToken
        from pygments.util import ClassNotFound
    except ImportError:
        return lines, [[None] * len(line) for line in lines], '#CCCCCC', '#CCCCCC', '#000000'
    try:
        style = get_style_by_name(formatter_style) if isinstance(formatter_style, str) else formatter_style
        lexer = get_lexer_by_name(language) if language is not None else guess_lexer(code_string)
    except ClassNotFound as error:
        raise ValueError(str(error)) from None
    default = style.style_for_token(TextToken).get('color')
    foreground = BLACK if default is None else '#' + default.upper()
    number = style.line_number_color
    number = foreground if number == 'inherit' else _hex_color(number)
    colors, row = [[]], 0
    for token, value in lex(code_string, lexer):
        color = style.style_for_token(token).get('color')
        color = '#' + color.upper() if color else None
        for char in value:
            if char == '\n':
                colors.append([])
            else:
                colors[-1].append(color)
    # Lexers strip outer newlines too, so colors follow the stripped lines.
    while len(colors) < len(lines):
        colors.append([])
    colors = [row[:len(line)] + [None] * (len(line) - len(row)) for row, line in zip(colors, lines)]
    return lines, colors, foreground, number, _hex_color(style.background_color)


def _hex_color(value):
    value = str(value or '#000000').strip()
    if not value.startswith('#'):
        value = '#' + value
    if len(value) == 4:
        value = '#' + ''.join(c * 2 for c in value[1:])
    return value.upper()


class Code(VGroup):
    """Community's syntax-highlighted listing: monospace Paragraph lines, line numbers
    and a rectangle or window background. Pygments colors each character."""
    default_background_config = {'buff': 0.3, 'fill_color': None, 'stroke_color': WHITE, 'corner_radius': 0.2,
                                 'stroke_width': 1, 'fill_opacity': 1}
    default_paragraph_config = {'font': 'Monospace', 'font_size': 24, 'line_spacing': 0.5, 'disable_ligatures': True}

    def __init__(self, code_file=None, code_string=None, language=None, formatter_style='vim', tab_width=4,
                 add_line_numbers=True, line_numbers_from=1, background='rectangle', background_config=None,
                 paragraph_config=None):
        super().__init__()
        if code_file is not None:
            raise NotImplementedError('The browser preview has no file system; pass code_string instead of code_file.')
        if not isinstance(code_string, str):
            raise ValueError('Either a code file or a code string must be specified.')
        if len(code_string) > 20000 or code_string.count('\n') > 400:
            raise ValueError('Code listings are limited to 400 lines and 20000 characters')
        if background not in ('rectangle', 'window'):
            raise ValueError(f'Unknown background type: {background}')
        code_string = code_string.expandtabs(tab_width)
        lines, colors, foreground, number_color, background_color = _code_tokens(code_string, language, formatter_style)
        config = dict(self.default_paragraph_config)
        config.update(paragraph_config or {})
        config.pop('color', None)
        rendered = lines if any(line.strip() for line in lines) else [''] * len(lines)
        # Community appends ascender/descender glyphs to the first and last lines so
        # listings get content-independent vertical bounds, then hides them.
        suffix = ' pA' + str(line_numbers_from)
        boundary = sorted({0, len(rendered) - 1})
        aligned = [line + suffix if index in boundary else line for index, line in enumerate(rendered)]
        self.code_lines = Paragraph(*aligned, color=foreground, **config)
        alignment = []
        for index, (line, line_colors) in enumerate(zip(self.code_lines, colors)):
            line._explode()
            text_length = len(rendered[index])
            kept = []
            for glyph in line.children:
                if glyph._char_index < text_length:
                    color = line_colors[glyph._char_index] if glyph._char_index < len(line_colors) else None
                    if color:
                        glyph.set_color(color)
                    kept.append(glyph)
                else:
                    # Keep only each hidden glyph's vertical extent, at its left edge.
                    left = glyph.get_left()[0]
                    alignment.append(Line((left, glyph.get_bottom()[1], 0), (left, glyph.get_top()[1], 0), stroke_width=0))
            reference = [g for g in line.children if g._char_index >= len(rendered[index]) + 3]
            if index == 0:
                self._number_reference = VGroup(*(g.copy() for g in reference))
            line._replace_children(kept)
        alignment = VGroup(*alignment)
        if add_line_numbers:
            numbers = [str(n) for n in range(line_numbers_from, line_numbers_from + len(self.code_lines))]
            number_config = dict(config, alignment='right')
            self.line_numbers = Paragraph(*numbers, color=number_color, **number_config)
            self.line_numbers.next_to(VGroup(self.code_lines, alignment), direction=LEFT)
            if len(self._number_reference):
                self.line_numbers.shift(UP * (self._number_reference.get_y() - self.line_numbers[0].get_y()))
            self.add(self.line_numbers)
        del self._number_reference
        self.add(self.code_lines)
        style = dict(self.default_background_config)
        style.update(background_config or {})
        if style['fill_color'] is None:
            style['fill_color'] = background_color
        if background == 'rectangle':
            self.background = SurroundingRectangle(self, alignment, **style)
        else:
            buttons = VGroup(*(Dot(radius=0.1, stroke_width=0, color=c) for c in ('#FF5F56', '#FFBD2E', '#27C93F')))
            buttons.arrange(RIGHT, buff=0.1)
            listing = VGroup(self.copy(), alignment)
            buttons.next_to(listing, UP, buff=0.1).align_to(listing, LEFT).shift(LEFT * 0.1)
            self.background = SurroundingRectangle(listing, buttons, **style)
            buttons.shift(UP * 0.1 + LEFT * 0.1)
            self.background.add(buttons)
        self.add_to_back(self.background)

    @classmethod
    def get_styles_list(cls):
        try:
            from pygments.styles import get_all_styles
        except ImportError:
            return ['vim']
        return list(get_all_styles())


_SVG_NAMED_COLORS = {
    'black': '#000000', 'white': '#FFFFFF', 'red': '#FF0000', 'green': '#008000', 'lime': '#00FF00',
    'blue': '#0000FF', 'yellow': '#FFFF00', 'cyan': '#00FFFF', 'aqua': '#00FFFF', 'magenta': '#FF00FF',
    'fuchsia': '#FF00FF', 'gray': '#808080', 'grey': '#808080', 'silver': '#C0C0C0', 'maroon': '#800000',
    'olive': '#808000', 'purple': '#800080', 'teal': '#008080', 'navy': '#000080', 'orange': '#FFA500',
    'pink': '#FFC0CB', 'brown': '#A52A2A', 'gold': '#FFD700', 'indigo': '#4B0082', 'violet': '#EE82EE',
    'darkgray': '#A9A9A9', 'darkgrey': '#A9A9A9', 'lightgray': '#D3D3D3', 'lightgrey': '#D3D3D3',
    'darkblue': '#00008B', 'darkred': '#8B0000', 'darkgreen': '#006400', 'lightblue': '#ADD8E6',
    'lightgreen': '#90EE90', 'skyblue': '#87CEEB', 'steelblue': '#4682B4', 'tomato': '#FF6347',
    'coral': '#FF7F50', 'salmon': '#FA8072', 'crimson': '#DC143C', 'turquoise': '#40E0D0',
    'tan': '#D2B48C', 'beige': '#F5F5DC', 'khaki': '#F0E68C', 'orchid': '#DA70D6', 'plum': '#DDA0DD',
    'chocolate': '#D2691E', 'firebrick': '#B22222', 'forestgreen': '#228B22', 'seagreen': '#2E8B57',
    'royalblue': '#4169E1', 'slategray': '#708090', 'dimgray': '#696969', 'whitesmoke': '#F5F5F5',
}
_SVG_STYLE_KEYS = ('fill', 'fill-opacity', 'stroke', 'stroke-opacity', 'stroke-width', 'opacity', 'color')


def _svg_color(value, current='#000000'):
    """(hex, alpha) for an SVG paint, or (None, 0) for none."""
    import re
    value = (value or '').strip()
    lower = value.lower()
    if lower in ('', 'none', 'transparent'):
        return None, 0.0
    if lower == 'currentcolor':
        return _svg_color(current)
    if lower in _SVG_NAMED_COLORS:
        return _SVG_NAMED_COLORS[lower], 1.0
    if re.fullmatch(r'#[0-9a-fA-F]{3,4}', value):
        value = '#' + ''.join(c * 2 for c in value[1:])
    if re.fullmatch(r'#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?', value):
        return value[:7].upper(), int(value[7:9], 16) / 255 if len(value) == 9 else 1.0
    match = re.fullmatch(r'rgba?\(([^)]*)\)', lower)
    if match:
        parts = [p.strip() for p in re.split(r'[,\s/]+', match.group(1)) if p.strip()]
        if len(parts) in (3, 4):
            channels = [round(float(p[:-1]) * 2.55) if p.endswith('%') else round(float(p)) for p in parts[:3]]
            alpha = 1.0
            if len(parts) == 4:
                alpha = float(parts[3][:-1]) / 100 if parts[3].endswith('%') else float(parts[3])
            return '#' + ''.join('%02X' % max(0, min(255, c)) for c in channels), max(0.0, min(1.0, alpha))
    raise ValueError(f'Unsupported SVG color: {value[:40]}')


def _svg_number(value, default=0.0):
    import re
    if value is None:
        return default
    match = re.match(r'\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)', str(value))
    if not match:
        raise ValueError(f'Invalid SVG number: {str(value)[:40]}')
    number = float(match.group(1))
    if not math.isfinite(number):
        raise ValueError('SVG numbers must be finite')
    return number


def _svg_numbers(text):
    import re
    return [float(n) for n in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', text or '')]


def _svg_transform(text):
    """Affine (a, b, c, d, e, f) for an SVG transform list (x' = a x + c y + e)."""
    import re
    result = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r'(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)', text or ''):
        v = _svg_numbers(args)
        if name == 'matrix' and len(v) == 6:
            m = tuple(v)
        elif name == 'translate' and v:
            m = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == 'scale' and v:
            m = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == 'rotate' and v:
            a = math.radians(v[0])
            cx, cy = (v[1], v[2]) if len(v) == 3 else (0, 0)
            cos, sin = math.cos(a), math.sin(a)
            m = (cos, sin, -sin, cos, cx - cos * cx + sin * cy, cy - sin * cx - cos * cy)
        elif name == 'skewX' and v:
            m = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == 'skewY' and v:
            m = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            raise ValueError(f'Invalid SVG transform: {name}({args[:40]})')
        result = _svg_compose(result, m)
    return result


def _svg_compose(m, n):
    """m applied after n."""
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (a * a2 + c * b2, b * a2 + d * b2, a * c2 + c * d2, b * c2 + d * d2,
            a * e2 + c * f2 + e, b * e2 + d * f2 + f)


def _svg_arc_cubics(start, rx, ry, phi, large, sweep, end):
    """Cubic approximations (at most 90 degrees each) of an SVG elliptical arc."""
    (x1, y1), (x2, y2) = start, end
    if (x1, y1) == (x2, y2):
        return []
    rx, ry = abs(rx), abs(ry)
    if not rx or not ry:
        return [((x1, y1), (x1 + (x2 - x1) / 3, y1 + (y2 - y1) / 3), (x1 + 2 * (x2 - x1) / 3, y1 + 2 * (y2 - y1) / 3), (x2, y2))]
    phi = math.radians(phi)
    cos, sin = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    xp, yp = cos * dx + sin * dy, -sin * dx + cos * dy
    scale = xp * xp / (rx * rx) + yp * yp / (ry * ry)
    if scale > 1:
        rx, ry = rx * math.sqrt(scale), ry * math.sqrt(scale)
    numerator = rx * rx * ry * ry - rx * rx * yp * yp - ry * ry * xp * xp
    factor = math.sqrt(max(0, numerator / (rx * rx * yp * yp + ry * ry * xp * xp)))
    if large == sweep:
        factor = -factor
    cxp, cyp = factor * rx * yp / ry, -factor * ry * xp / rx
    cx, cy = cos * cxp - sin * cyp + (x1 + x2) / 2, sin * cxp + cos * cyp + (y1 + y2) / 2
    angle = lambda ux, uy: math.atan2(uy, ux)
    theta = angle((xp - cxp) / rx, (yp - cyp) / ry)
    delta = angle((-xp - cxp) / rx, (-yp - cyp) / ry) - theta
    if sweep and delta < 0:
        delta += TAU
    elif not sweep and delta > 0:
        delta -= TAU
    count = max(1, math.ceil(abs(delta) / (PI / 2) - 1e-9))
    step = delta / count
    k = 4 / 3 * math.tan(step / 4)
    point = lambda t: (cx + rx * math.cos(t) * cos - ry * math.sin(t) * sin, cy + rx * math.cos(t) * sin + ry * math.sin(t) * cos)
    deriv = lambda t: (-rx * math.sin(t) * cos - ry * math.cos(t) * sin, -rx * math.sin(t) * sin + ry * math.cos(t) * cos)
    curves = []
    for i in range(count):
        t0, t1 = theta + i * step, theta + (i + 1) * step
        p0, p3 = point(t0), point(t1)
        d0, d1 = deriv(t0), deriv(t1)
        curves.append((p0, (p0[0] + k * d0[0], p0[1] + k * d0[1]), (p3[0] - k * d1[0], p3[1] - k * d1[1]), p3))
    curves[-1] = curves[-1][:3] + ((x2, y2),)
    return curves


def _svg_path_points(data):
    """Community's VMobjectFromSVGPath point list (cubics, lines/quads raised) for path data."""
    import re
    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', data or '')
    if len(tokens) > 200000:
        raise ValueError('SVG path data is too long')
    points, index = [], 0
    current = start = None
    last_control, last_command = None, ''
    def number():
        nonlocal index
        if index >= len(tokens) or tokens[index].isalpha():
            raise ValueError('Malformed SVG path data')
        index += 1
        return float(tokens[index - 1])
    def cubic(p1, p2, p3):
        nonlocal current
        points.extend([current, p1, p2, p3])
        current = p3
    def line(end):
        cubic(((2 * current[0] + end[0]) / 3, (2 * current[1] + end[1]) / 3),
              ((current[0] + 2 * end[0]) / 3, (current[1] + 2 * end[1]) / 3), end)
    command = None
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        elif command is None:
            raise ValueError('SVG path data must start with a command')
        relative = command.islower()
        kind = command.upper()
        base = current if relative and current is not None else (0.0, 0.0)
        offset = lambda x, y: (base[0] + x, base[1] + y)
        if kind == 'Z':
            if current is not None and start is not None and math.dist(current, start) > 0.0001:
                line(start)
            current, last_control, last_command = start, None, 'Z'
            continue
        if kind == 'M':
            current = start = offset(number(), number())
            command = 'l' if relative else 'L'  # Further pairs are implicit lines.
            last_control = None
            continue
        if current is None:
            raise ValueError('SVG path data must start with a move command')
        if kind == 'L':
            line(offset(number(), number()))
            last_control = None
        elif kind == 'H':
            x = number()
            line((current[0] + x if relative else x, current[1]))
            last_control = None
        elif kind == 'V':
            y = number()
            line((current[0], current[1] + y if relative else y))
            last_control = None
        elif kind == 'C':
            p1, p2, p3 = offset(number(), number()), offset(number(), number()), offset(number(), number())
            cubic(p1, p2, p3)
            last_control = p2
        elif kind == 'S':
            reflected = (2 * current[0] - last_control[0], 2 * current[1] - last_control[1]) \
                if last_control is not None and last_command in 'CS' else current
            p2, p3 = offset(number(), number()), offset(number(), number())
            cubic(reflected, p2, p3)
            last_control = p2
        elif kind in ('Q', 'T'):
            if kind == 'Q':
                control = offset(number(), number())
            else:
                control = (2 * current[0] - last_control[0], 2 * current[1] - last_control[1]) \
                    if last_control is not None and last_command in 'QT' else current
            end = offset(number(), number())
            cubic(((current[0] + 2 * control[0]) / 3, (current[1] + 2 * control[1]) / 3),
                  ((2 * control[0] + end[0]) / 3, (2 * control[1] + end[1]) / 3), end)
            last_control = control
        elif kind == 'A':
            rx, ry, phi = number(), number(), number()
            large, sweep = number() != 0, number() != 0
            end = offset(number(), number())
            for curve in _svg_arc_cubics(current, rx, ry, phi, large, sweep, end):
                cubic(*curve[1:])
            current = end
            last_control = None
        else:
            raise ValueError(f'Unsupported SVG path command: {command}')
        last_command = kind
    return [(p[0], p[1], 0.0) for p in points]


class VMobjectFromSVGPath(VMobject):
    """A VMobject from SVG path data (a string here; Community takes an svgelements Path)."""
    def __init__(self, path_obj, long_lines=False, should_subdivide_sharp_curves=False,
                 should_remove_null_curves=False, **kwargs):
        super().__init__(**kwargs)
        data = path_obj if isinstance(path_obj, str) else getattr(path_obj, 'd', lambda: None)()
        if not isinstance(data, str):
            raise TypeError('VMobjectFromSVGPath expects SVG path data')
        self.path_string = data
        points = _svg_path_points(data)
        if points:
            self.set_points(points)


class SVGMobject(VGroup):
    """Community's SVGMobject: one VMobject per SVG shape, y flipped, centered and fit
    to height 2. The browser has no file system, so pass SVG markup as file_name."""
    def __init__(self, file_name=None, should_center=True, height=2, width=None, color=None, opacity=None,
                 fill_color=None, fill_opacity=None, stroke_color=None, stroke_opacity=None, stroke_width=None,
                 svg_default=None, path_string_config=None, use_svg_cache=True, **kwargs):
        super().__init__(**kwargs)
        if not isinstance(file_name, str):
            raise ValueError('Must specify file for SVGMobject')
        markup = file_name.strip()
        if not markup.startswith('<'):
            raise NotImplementedError('The browser preview has no file system; pass SVG markup '
                                      '(a string starting with "<svg") instead of a file name.')
        if len(markup) > 2000000:
            raise ValueError('SVG markup is limited to 2 MB')
        self.should_center, self.svg_height, self.svg_width = should_center, height, width
        self.svg_default = dict({'color': None, 'opacity': None, 'fill_color': None, 'fill_opacity': None,
                                 'stroke_width': 0, 'stroke_color': None, 'stroke_opacity': None}, **(svg_default or {}))
        self.path_string_config = dict(path_string_config or {})
        self.id_to_vgroup_dict = {}
        self._svg_shapes = 0
        shapes = self._parse(markup)
        if shapes:
            # SVG y points down: mirror each shape about the drawing's center (Community's flip).
            left, bottom, right, top = _union_bounds(shapes)
            center = Vector(((left + right) / 2, (bottom + top) / 2, 0))
            for shape in shapes:
                shape.apply_matrix([[1, 0], [0, -1]], about_point=center)
        self.add(*shapes)
        self.set_style(fill_color=fill_color, fill_opacity=fill_opacity, stroke_color=stroke_color,
                       stroke_opacity=stroke_opacity, stroke_width=stroke_width)
        self.move_into_position()

    def move_into_position(self):
        if self.should_center:
            self.center()
        if self.svg_height is not None:
            self.set(height=self.svg_height)
        if self.svg_width is not None:
            self.set(width=self.svg_width)
        return self

    def _parse(self, markup):
        from xml.etree import ElementTree
        if '<!ENTITY' in markup or '<!DOCTYPE' in markup:
            raise ValueError('SVG markup with DTDs or entities is not supported')
        try:
            root = ElementTree.fromstring(markup)
        except ElementTree.ParseError as error:
            raise ValueError(f'Invalid SVG markup: {error}') from None
        local = lambda tag: tag.rsplit('}', 1)[-1]
        if local(root.tag) != 'svg':
            raise ValueError('SVG markup must have an <svg> root element')
        ids = {element.get('id'): element for element in root.iter() if element.get('id')}
        defaults = {key: self.svg_default[name] for key, name in
                    (('fill', 'fill_color'), ('fill-opacity', 'fill_opacity'), ('stroke', 'stroke_color'),
                     ('stroke-opacity', 'stroke_opacity'), ('stroke-width', 'stroke_width')) if self.svg_default.get(name) is not None}
        if self.svg_default.get('color') is not None:
            defaults.setdefault('fill', self.svg_default['color'])
            defaults.setdefault('stroke', self.svg_default['color'])
        style = {'fill': '#000000', 'stroke': 'none', 'stroke-width': '1', 'color': '#000000'}
        style.update({k: str(v) for k, v in defaults.items()})
        matrix = self._viewbox(root)
        result, groups = [], {}
        def styles(element, inherited):
            current = dict(inherited)
            current.pop('opacity', None)
            for key in _SVG_STYLE_KEYS:
                if element.get(key) is not None:
                    current[key] = element.get(key)
            for declaration in (element.get('style') or '').split(';'):
                if ':' in declaration:
                    key, value = (part.strip() for part in declaration.split(':', 1))
                    if key in _SVG_STYLE_KEYS:
                        current[key] = value
            opacity = _svg_number(current.get('opacity'), 1.0)
            current['_opacity'] = inherited.get('_opacity', 1.0) * opacity
            return current
        def visit(element, inherited, transform, group_names, depth):
            if depth > 64:
                raise ValueError('SVG nesting is too deep')
            tag = local(element.tag)
            if tag in ('defs', 'clipPath', 'mask', 'style', 'title', 'desc', 'metadata', 'symbol', 'linearGradient', 'radialGradient', 'pattern', 'marker'):
                return
            current = styles(element, inherited)
            transform = _svg_compose(transform, _svg_transform(element.get('transform')))
            name = element.get('id')
            names = group_names + [name] if name else group_names
            if tag in ('svg', 'g', 'a', 'switch') or (tag == 'svg' and element is root):
                for child in element:
                    visit(child, current, transform, names, depth + 1)
                return
            if tag == 'use':
                href = element.get('href') or element.get('{http://www.w3.org/1999/xlink}href') or ''
                target = ids.get(href[1:]) if href.startswith('#') else None
                if target is not None and depth < 32:
                    shifted = _svg_compose(transform, (1, 0, 0, 1, _svg_number(element.get('x')), _svg_number(element.get('y'))))
                    if local(target.tag) == 'symbol':
                        for child in target:
                            visit(child, current, shifted, names, depth + 1)
                    else:
                        visit(target, current, shifted, names, depth + 1)
                return
            mobject = self._shape(tag, element)
            if mobject is None or mobject.has_no_points():
                return
            self._svg_shapes += 1
            if self._svg_shapes > 5000:
                raise ValueError('SVGMobject is limited to 5000 shapes')
            self._apply_style(mobject, current)
            a, b, c, d, e, f = transform
            if (a, b, c, d) != (1, 0, 0, 1):
                mobject.apply_matrix([[a, c], [b, d]], about_point=ORIGIN)
            mobject.shift(Vector((e, f, 0)))
            result.append(mobject)
            for group_name in ['root'] + names:
                groups.setdefault(group_name, []).append(mobject)
        visit(root, style, matrix, [], 0)
        self.id_to_vgroup_dict = {name: VGroup(*members) for name, members in groups.items()}
        return result

    @staticmethod
    def _viewbox(root):
        box = _svg_numbers(root.get('viewBox'))
        if len(box) != 4 or box[2] <= 0 or box[3] <= 0:
            return (1, 0, 0, 1, 0, 0)
        width, height = _svg_number(root.get('width'), box[2]), _svg_number(root.get('height'), box[3])
        scale = min(width / box[2], height / box[3])
        return (scale, 0, 0, scale, (width - box[2] * scale) / 2 - box[0] * scale, (height - box[3] * scale) / 2 - box[1] * scale)

    def _shape(self, tag, element):
        number = lambda key, default=0.0: _svg_number(element.get(key), default)
        point = lambda x, y: Vector((x, y, 0))
        if tag == 'path':
            return VMobjectFromSVGPath(element.get('d') or '', **self.path_string_config)
        if tag == 'line':
            return Line(point(number('x1'), number('y1')), point(number('x2'), number('y2')))
        if tag == 'rect':
            width, height = number('width'), number('height')
            if width <= 0 or height <= 0:
                return None
            rx, ry = element.get('rx'), element.get('ry')
            rx = _svg_number(rx if rx is not None else ry)
            ry = _svg_number(ry if ry is not None else rx)
            rx, ry = min(rx, width / 2), min(ry, height / 2)
            if rx == 0 or ry == 0:
                mobject = Rectangle(width=width, height=height)
            else:
                mobject = RoundedRectangle(width=width, height=height * rx / ry, corner_radius=rx)
                mobject.stretch_to_fit_height(height)
            return mobject.shift(point(number('x') + width / 2, number('y') + height / 2))
        if tag in ('circle', 'ellipse'):
            rx = number('r') if tag == 'circle' else number('rx')
            ry = rx if tag == 'circle' else number('ry')
            if rx <= 0 or ry <= 0:
                return None
            mobject = Circle(radius=rx)
            if rx != ry:
                mobject.stretch_to_fit_height(2 * ry)
            return mobject.shift(point(number('cx'), number('cy')))
        if tag in ('polygon', 'polyline'):
            values = _svg_numbers(element.get('points'))
            points = [point(x, y) for x, y in zip(values[::2], values[1::2])]
            if len(points) < 2:
                return None
            return Polygon(*points) if tag == 'polygon' else VMobject().set_points_as_corners(points)
        return None  # Text and other elements are unsupported, as in Community.

    @staticmethod
    def _apply_style(mobject, style):
        fill, fill_alpha = _svg_color(style.get('fill'), style.get('color'))
        stroke, stroke_alpha = _svg_color(style.get('stroke'), style.get('color'))
        opacity = style.get('_opacity', 1.0)
        # svgelements folds fill-opacity into the paint's alpha byte.
        alpha = lambda paint, key: round(255 * paint * max(0, min(1, _svg_number(style.get(key), 1.0)))) / 255
        mobject.set_style(stroke_width=_svg_number(style.get('stroke-width'), 1.0) if stroke else 0,
                          stroke_color=stroke, stroke_opacity=alpha(stroke_alpha, 'stroke-opacity') * opacity if stroke else None,
                          fill_color=fill, fill_opacity=alpha(fill_alpha, 'fill-opacity') * opacity if fill else 0)


_IMAGE_PIXEL_LIMIT = 4000000
# Community maps these names to Pillow's resampling filters (NEAREST=0 ... HAMMING=5).
RESAMPLING_ALGORITHMS = {'nearest': 0, 'none': 0, 'lanczos': 1, 'antialias': 1, 'bilinear': 2, 'linear': 2,
                         'bicubic': 3, 'cubic': 3, 'box': 4, 'hamming': 5}


def _rgba_rows(pixels):
    """Rows of RGBA byte tuples from a NumPy array or nested lists (2D gray, RGB or RGBA)."""
    if hasattr(pixels, 'tolist'):
        pixels = pixels.tolist()
    rows = [list(row) for row in pixels]
    if not rows or not rows[0]:
        raise ValueError('ImageMobject arrays need at least one pixel')
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError('ImageMobject arrays must be rectangular')
    if len(rows) * width > _IMAGE_PIXEL_LIMIT:
        raise ValueError('ImageMobject is limited to 4 million pixels')
    def channel(value):
        if isinstance(value, bool) or not isinstance(value, _REAL) or not math.isfinite(value):
            raise ValueError('Image pixel values must be finite numbers')
        return max(0, min(255, int(value)))
    result = []
    for row in rows:
        out = []
        for pixel in row:
            if isinstance(pixel, _REAL):
                gray = channel(pixel)
                out.append((gray, gray, gray, 255))
            else:
                values = [channel(v) for v in pixel]
                if len(values) == 1:
                    values = values * 3 + [255]
                elif len(values) == 3:
                    values.append(255)
                elif len(values) != 4:
                    raise ValueError('Image pixels need 1, 3 or 4 channels')
                out.append(tuple(values))
        result.append(out)
    return result


def _png_data_uri(rows):
    import base64, zlib
    height, width = len(rows), len(rows[0])
    raw = b''.join(b'\x00' + bytes(v for pixel in row for v in pixel) for row in rows)
    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data +
                struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) +
           chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
    return 'data:image/png;base64,' + base64.b64encode(png).decode('ascii')


def _data_uri_size(uri):
    """Pixel (width, height) of a base64 PNG, GIF or JPEG data URI."""
    import base64, re
    match = re.fullmatch(r'data:image/(png|gif|jpeg|jpg|webp);base64,([A-Za-z0-9+/=\s]+)', uri)
    if not match:
        raise NotImplementedError('The browser preview has no file system; pass a pixel array or a '
                                  'base64 PNG/JPEG/GIF data URI to ImageMobject.')
    if len(uri) > 8000000:
        raise ValueError('Image data URIs are limited to 8 MB')
    data = base64.b64decode(re.sub(r'\s', '', match.group(2)))
    kind = match.group(1)
    if kind == 'png' and data[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', data[16:24])
    if kind == 'gif' and data[:3] == b'GIF':
        return struct.unpack('<HH', data[6:10])
    if kind in ('jpeg', 'jpg') and data[:2] == b'\xff\xd8':
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                break
            marker, length = data[index + 1], struct.unpack('>H', data[index + 2:index + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                height, width = struct.unpack('>HH', data[index + 5:index + 9])
                return width, height
            index += 2 + length
    raise ValueError('Could not read the image size from the data URI')


class ImageMobject(Mobject):
    """Community's raster image: height = rows / scale_to_resolution * frame height.
    Arrays are encoded as PNG; files are unavailable, but image data URIs work."""
    def __init__(self, filename_or_array, scale_to_resolution=1080, invert=False, image_mode='RGBA', **kwargs):
        kwargs.setdefault('fill_opacity', 1)
        kwargs.setdefault('stroke_width', 0)
        super().__init__(**kwargs)
        self._type = 'image'
        if isinstance(filename_or_array, str):
            if invert:
                raise NotImplementedError('invert needs a pixel array in the browser preview')
            self.pixel_width, self.pixel_height = _data_uri_size(filename_or_array.strip())
            self.href = filename_or_array.strip()
            self._pixels = None
        else:
            rows = _rgba_rows(filename_or_array)
            if invert:
                rows = [[(255 - r, 255 - g, 255 - b, a) for r, g, b, a in row] for row in rows]
            self._pixels = rows
            self.pixel_height, self.pixel_width = len(rows), len(rows[0])
            self.href = _png_data_uri(rows)
        if not self.pixel_width or not self.pixel_height:
            raise ValueError('ImageMobject needs a nonempty image')
        NumberLine._real(scale_to_resolution, 'scale_to_resolution', positive=True)
        self.scale_to_resolution, self.invert, self.image_mode = scale_to_resolution, invert, image_mode
        self.height = self.pixel_height / scale_to_resolution * config.frame_height
        self.width = self.height * self.pixel_width / self.pixel_height
        self.resampling_algorithm = 'bicubic'

    def get_pixel_array(self):
        if self._pixels is None:
            raise NotImplementedError('Pixel arrays of data URI images are not decoded in the browser preview')
        try:
            import numpy
        except ImportError:
            return [[list(pixel) for pixel in row] for row in self._pixels]
        return numpy.array(self._pixels, dtype=numpy.uint8)

    def set_resampling_algorithm(self, resampling_algorithm):
        names = {0: 'nearest', 1: 'lanczos', 2: 'bilinear', 3: 'bicubic', 4: 'box', 5: 'hamming'}
        value = names.get(resampling_algorithm, resampling_algorithm)
        if value not in ('nearest', 'lanczos', 'bilinear', 'bicubic', 'box', 'hamming'):
            raise ValueError('Unknown resampling algorithm')
        self.resampling_algorithm = value
        return self

    def set_opacity(self, alpha, family=True):
        self._validate_opacity(alpha)
        self.opacity = alpha
        return self

    def fade(self, darkness=0.5, family=True):
        return self.set_opacity(1 - darkness)

    def get_points(self):
        # Community stores the four corners: UL, UR, DL, DR.
        w, h = self.width / 2, self.height / 2
        return [list(self._point_to_world(Vector(p))) for p in ((-w, h, 0), (w, h, 0), (-w, -h, 0), (w, -h, 0))]


class _PCG64:
    """NumPy's default_rng(seed) stream (SeedSequence + PCG64), for exact Community noise."""
    _MULT = 0x2360ED051FC65DA44385DF649FCCF645

    def __init__(self, seed=0):
        m32, m128 = 0xFFFFFFFF, (1 << 128) - 1
        if isinstance(seed, bool) or not isinstance(seed, numbers.Integral) or seed < 0:
            raise ValueError('Random seeds must be nonnegative integers')
        entropy, n = ([0] if seed == 0 else []), int(seed)
        while n:
            entropy.append(n & m32)
            n >>= 32
        hash_const = [0x43b0d7e5]
        def hashmix(value):
            value = (value ^ hash_const[0]) & m32
            hash_const[0] = (hash_const[0] * 0x931e8875) & m32
            value = (value * hash_const[0]) & m32
            return value ^ (value >> 16)
        def mix(x, y):
            result = (0xca01f9dd * x - 0x4973f715 * y) & m32
            return result ^ (result >> 16)
        pool = [hashmix(entropy[i] if i < len(entropy) else 0) for i in range(4)]
        for source in range(4):
            for target in range(4):
                if source != target:
                    pool[target] = mix(pool[target], hashmix(pool[source]))
        for source in range(4, len(entropy)):
            for target in range(4):
                pool[target] = mix(pool[target], hashmix(entropy[source]))
        words, hash_b = [], 0x8b51f9dd
        for index in range(8):
            value = (pool[index % 4] ^ hash_b) & m32
            hash_b = (hash_b * 0x58f38ded) & m32
            value = (value * hash_b) & m32
            words.append(value ^ (value >> 16))
        state = [words[2 * i] | (words[2 * i + 1] << 32) for i in range(4)]
        self._inc = ((((state[2] << 64) | state[3]) << 1) | 1) & m128
        self._state = 0
        self._step()
        self._state = (self._state + ((state[0] << 64) | state[1])) & m128
        self._step()

    def _step(self):
        self._state = (self._state * self._MULT + self._inc) & ((1 << 128) - 1)

    def _next64(self):
        self._step()
        mask = (1 << 64) - 1
        value, rotation = ((self._state >> 64) ^ self._state) & mask, self._state >> 122
        return ((value >> rotation) | (value << ((64 - rotation) & 63))) & mask

    def random(self, size=None):
        draw = lambda: (self._next64() >> 11) * (1.0 / 9007199254740992.0)
        return draw() if size is None else [draw() for _ in range(size)]


DEFAULT_SCALAR_FIELD_COLORS = [_PALETTE[name] for name in ('BLUE_E', 'GREEN_C', 'YELLOW_C', 'RED_C')]
_FIELD_POINT_LIMIT = 5000


def _field_vector(value, name='Vector field output'):
    try:
        values = [_plain_number(v) for v in list(value)[:3]]
    except TypeError:
        raise TypeError(name + ' must be a coordinate sequence') from None
    if len(values) < 2 or any(isinstance(v, bool) or not isinstance(v, _REAL) or not math.isfinite(v) for v in values):
        raise ValueError(name + ' must contain finite real coordinates')
    return Vector(values)


def _field_ranges(x_range, y_range, z_range, three_dimensions):
    """Community's [start, stop, step] lists, with the stop extended by one step (np.arange is exclusive)."""
    if three_dimensions or z_range:
        raise NotImplementedError('3D vector fields are not supported in the browser preview')
    ranges = []
    for values, default, name in ((x_range, config.frame_width / 2, 'x_range'),
                                  (y_range, config.frame_height / 2, 'y_range')):
        values = [math.floor(-default), math.ceil(default)] if not values else list(values)
        if len(values) == 2:
            values.append(.5)
        if len(values) != 3 or any(isinstance(v, bool) or not isinstance(v, _REAL) or not math.isfinite(v) for v in values):
            raise ValueError('Vector field ' + name + ' needs finite [start, stop] or [start, stop, step]')
        if values[2] <= 0:
            raise ValueError('Vector field ' + name + ' step must be positive')
        values[1] += values[2]
        ranges.append(values)
    ranges.append([0, .5, .5])
    counts = [max(0, math.ceil((stop - start) / step)) for start, stop, step in ranges]
    if counts[0] * counts[1] > _FIELD_POINT_LIMIT:
        raise ValueError('Vector fields are limited to %d sample points' % _FIELD_POINT_LIMIT)
    axes = [[start + index * step for index in range(count)] for (start, stop, step), count in zip(ranges, counts)]
    return ranges, axes


class VectorField(VGroup):
    """Community's VectorField base: a function sampled with magnitude color schemes and RK4 nudging."""
    def __init__(self, func, color=None, color_scheme=None, min_color_scheme_value=0,
                 max_color_scheme_value=2, colors=DEFAULT_SCALAR_FIELD_COLORS, **kwargs):
        if not callable(func):
            raise TypeError('VectorField func must be callable')
        super().__init__(**kwargs)
        self.func = func
        self.submob_movement_updater = None
        if color is None:
            if color_scheme is not None and not callable(color_scheme):
                raise TypeError('color_scheme must be callable')
            for value in (min_color_scheme_value, max_color_scheme_value):
                if isinstance(value, bool) or not isinstance(value, _REAL) or not math.isfinite(value):
                    raise ValueError('Color scheme bounds must be finite real numbers')
            if min_color_scheme_value == max_color_scheme_value:
                raise ValueError('Color scheme bounds must differ')
            colors = list(colors)
            if not colors:
                raise ValueError('Vector field colors must not be empty')
            self.single_color = False
            self.color_scheme = color_scheme or (lambda vec: math.sqrt(sum(v * v for v in _field_vector(vec))))
            self.rgbs = [color_to_rgb(c) for c in colors]
            self.min_color_scheme_value, self.max_color_scheme_value = min_color_scheme_value, max_color_scheme_value
        else:
            self.single_color = True
            self.color = color

    def pos_to_rgb(self, pos):
        if self.single_color:
            raise ValueError('A single-color vector field has no color scheme')
        low, high = self.min_color_scheme_value, self.max_color_scheme_value
        value = _plain_number(self.color_scheme(self.func(Vector(pos))))
        if isinstance(value, bool) or not isinstance(value, _REAL) or not math.isfinite(value):
            raise ValueError('color_scheme must return a finite real number')
        value = max(min(low, high), min(max(low, high), value))
        alpha = (value - low) / (high - low) * (len(self.rgbs) - 1)
        first = self.rgbs[int(alpha)]
        second = self.rgbs[min(int(alpha + 1), len(self.rgbs) - 1)]
        alpha %= 1
        return [a + (b - a) * alpha for a, b in zip(first, second)]

    def pos_to_color(self, pos):
        return _rgb_color(self.pos_to_rgb(pos))

    @staticmethod
    def shift_func(func, shift_vector):
        shift_vector = Vector(shift_vector)
        return lambda p: func(Vector(p) - shift_vector)

    @staticmethod
    def scale_func(func, scalar):
        return lambda p: func(Vector(p) * scalar)

    def fit_to_coordinate_system(self, coordinate_system):
        return self.apply_function(lambda pos: coordinate_system.coords_to_point(*pos))

    def _runge_kutta(self, point, step):
        point = Vector(point)
        k1 = _field_vector(self.func(point))
        k2 = _field_vector(self.func(point + k1 * (step * .5)))
        k3 = _field_vector(self.func(point + k2 * (step * .5)))
        k4 = _field_vector(self.func(point + k3 * step))
        return (k1 + k2 * 2 + k3 * 2 + k4) * (step / 6)

    def nudge(self, mob, dt=1, substeps=1, pointwise=False):
        if isinstance(substeps, bool) or not isinstance(substeps, numbers.Integral) or not 1 <= substeps <= 1000:
            raise ValueError('nudge substeps must be an integer from 1 to 1000')
        step = dt / substeps
        for _ in range(substeps):
            if pointwise:
                mob.apply_function(lambda p: Vector(p) + self._runge_kutta(p, step))
            else:
                mob.shift(self._runge_kutta(mob.get_center(), step))
        return self

    def nudge_submobjects(self, dt=1, substeps=1, pointwise=False):
        for mob in self.children:
            self.nudge(mob, dt, substeps, pointwise)
        return self

    def get_nudge_updater(self, speed=1, pointwise=False):
        return lambda mob, dt: self.nudge(mob, dt * speed, pointwise=pointwise)

    def start_submobject_movement(self, speed=1, pointwise=False):
        self.stop_submobject_movement()
        self.submob_movement_updater = lambda mob, dt: mob.nudge_submobjects(dt * speed, pointwise=pointwise)
        self.add_updater(self.submob_movement_updater)
        return self

    def stop_submobject_movement(self):
        if self.submob_movement_updater is not None:
            self.remove_updater(self.submob_movement_updater)
        self.submob_movement_updater = None
        return self

    def get_colored_background_image(self, sampling_rate=5):
        raise NotImplementedError('Raster background images are not supported in the browser preview')

    def get_vectorized_rgba_gradient_function(self, start, end, colors):
        rgbs = [color_to_rgb(c) for c in colors]
        if not rgbs or start == end:
            raise ValueError('Gradient functions need colors and distinct bounds')
        def func(values, opacity=1.0):
            result = []
            for value in values:
                alpha = max(0, min(1, (value - start) / (end - start))) * (len(rgbs) - 1)
                index = int(alpha)
                following = min(index + 1, len(rgbs) - 1)
                result.append([a + (b - a) * (alpha % 1) for a, b in zip(rgbs[index], rgbs[following])] + [opacity])
            return result
        return func


class ArrowVectorField(VectorField):
    """Community's grid of Vectors, displayed at length_func(norm) and colored by magnitude."""
    def __init__(self, func, color=None, color_scheme=None, min_color_scheme_value=0, max_color_scheme_value=2,
                 colors=DEFAULT_SCALAR_FIELD_COLORS, x_range=None, y_range=None, z_range=None,
                 three_dimensions=False, length_func=lambda norm: .45 * sigmoid(norm), opacity=1.0,
                 vector_config=None, **kwargs):
        ranges, axes = _field_ranges(x_range, y_range, z_range, three_dimensions)
        self.x_range, self.y_range, self.z_range = ranges
        super().__init__(func, color, color_scheme, min_color_scheme_value, max_color_scheme_value, colors, **kwargs)
        if not callable(length_func):
            raise TypeError('length_func must be callable')
        self.length_func, self.opacity = length_func, opacity
        self.vector_config = dict(vector_config or {})
        self.add(*(self.get_vector(Vector((x, y, z))) for x in axes[0] for y in axes[1] for z in axes[2]))
        self.set_opacity(opacity)

    def get_vector(self, point):
        point = Vector(point)
        output = _field_vector(self.func(point))
        norm = math.sqrt(sum(v * v for v in output))
        if norm != 0:
            output = output * (_plain_number(self.length_func(norm)) / norm)
        vector = VectorArrow(Vector((output[0], output[1], 0)), **self.vector_config)
        vector.shift(Vector((point[0], point[1], 0)))
        vector.set_color(self.color if self.single_color else self.pos_to_color(point))
        return vector


class StreamLine(VMobject):
    """A traced field line, with the simulated duration Community uses for flow timing."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.duration = 0
        self.time = 0


class StreamLines(VectorField):
    """Community's Euler-traced stream lines from noisy grid starts (NumPy default_rng(0) noise)."""
    def __init__(self, func, color=None, color_scheme=None, min_color_scheme_value=0, max_color_scheme_value=2,
                 colors=DEFAULT_SCALAR_FIELD_COLORS, x_range=None, y_range=None, z_range=None,
                 three_dimensions=False, noise_factor=None, n_repeats=1, dt=.05, virtual_time=3,
                 max_anchors_per_line=100, padding=3, stroke_width=1, opacity=1, **kwargs):
        ranges, axes = _field_ranges(x_range, y_range, z_range, three_dimensions)
        self.x_range, self.y_range, self.z_range = ranges
        super().__init__(func, color, color_scheme, min_color_scheme_value, max_color_scheme_value, colors, **kwargs)
        for value, name in ((dt, 'dt'), (virtual_time, 'virtual_time')):
            NumberLine._real(value, name, positive=True)
        NumberLine._real(padding, 'padding', nonnegative=True)
        for value, name in ((n_repeats, 'n_repeats'), (max_anchors_per_line, 'max_anchors_per_line')):
            if isinstance(value, bool) or not isinstance(value, numbers.Integral) or value < 1:
                raise ValueError(name + ' must be a positive integer')
        max_steps = math.ceil(virtual_time / dt) + 1
        lines = n_repeats * len(axes[0]) * len(axes[1])
        if lines > _FIELD_POINT_LIMIT or lines * max_steps > 200000:
            raise ValueError('StreamLines is limited to %d lines and 200000 traced steps' % _FIELD_POINT_LIMIT)
        self.noise_factor = self.y_range[2] / 2 if noise_factor is None else noise_factor
        self.n_repeats, self.virtual_time = n_repeats, virtual_time
        self.max_anchors_per_line, self.padding, self.stroke_width = max_anchors_per_line, padding, stroke_width
        self.flow_animation = None
        half, rng = self.noise_factor / 2, _PCG64(0)
        starts = []
        for _ in range(n_repeats):
            for x in axes[0]:
                for y in axes[1]:
                    for z in axes[2]:
                        noise = rng.random(3)
                        starts.append(Vector((x - half + self.noise_factor * noise[0],
                                              y - half + self.noise_factor * noise[1],
                                              z - half + self.noise_factor * noise[2])))
        (x0, x1, xs), (y0, y1, ys), (z0, z1, zs) = ranges
        def outside(p):
            return (p[0] < x0 - padding or p[0] > x1 + padding - xs or p[1] < y0 - padding
                    or p[1] > y1 + padding - ys or p[2] < z0 - padding or p[2] > z1 + padding - zs)
        lines = []
        for start in starts:
            points = [start]
            for _ in range(max_steps):
                following = points[-1] + _field_vector(self.func(points[-1])) * dt
                if outside(following):
                    break
                points.append(following)
            line = StreamLine()
            line.duration = max_steps * dt  # Community records the full step budget.
            step = max(1, int(len(points) / max_anchors_per_line))
            plane = [Vector((p[0], p[1], 0)) for p in points[::step]]
            # A fresh line has no callbacks to preserve, so skip set_points_smoothly's copy/become.
            line.set_points_as_corners(plane if len(plane) > 1 else plane * 2).make_smooth()
            if self.single_color:
                line.set_stroke(color=self.color, width=stroke_width, opacity=opacity)
            else:
                # Community samples a raster of field colors under each stroke; approximate it
                # with a gradient along the line's chord, sampled at evenly spaced anchors.
                samples = [points[min(len(points) - 1, round(i * (len(points) - 1) / 7))] for i in range(8)]
                line.set_stroke(color=[self.pos_to_color(p) for p in samples], width=stroke_width, opacity=opacity)
                line.gradient_points = [[points[0][0], points[0][1]], [points[-1][0], points[-1][1]]]
            lines.append(line)
        self.add(*lines)  # One family update; adding lines one at a time is quadratic.

    @property
    def stream_lines(self):
        return [line for line in self.children if isinstance(line, StreamLine)]

    def create(self, lag_ratio=None, run_time=None, **kwargs):
        if run_time is None:
            run_time = self.virtual_time
        run_time = float(run_time(self.virtual_time) if callable(run_time) else run_time)
        lines = self.stream_lines
        if not lines:
            raise ValueError('StreamLines has no lines to create')
        if lag_ratio is None:
            lag_ratio = run_time / 2 / len(self.children)
        animations = [Create(line, run_time=run_time, **kwargs) for line in lines]
        # Community shuffles with the global generator; a fixed seed keeps previews reproducible.
        random.Random(0).shuffle(animations)
        return AnimationGroup(*animations, lag_ratio=lag_ratio)

    def start_animation(self, warm_up=True, flow_speed=1, time_width=.3, rate_func=linear,
                        line_animation_class=None, **kwargs):
        if line_animation_class not in (None, ShowPassingFlash):
            raise NotImplementedError('StreamLines flow supports ShowPassingFlash only')
        if kwargs:
            raise NotImplementedError('Unsupported options: ' + ', '.join(kwargs))
        NumberLine._real(flow_speed, 'flow_speed', positive=True)
        NumberLine._real(time_width, 'time_width', nonnegative=True)
        if not callable(rate_func):
            raise TypeError('rate_func must be callable')
        if self.flow_animation is not None:
            self.remove_updater(self.flow_animation)
        generator = random.Random(1)
        for line in self.stream_lines:
            if getattr(line, '_flow_source', None) is None:
                line._flow_source = line.copy()
            line.time = generator.random() * self.virtual_time * (-1 if warm_up else 1)
            self._flash(line, line.time, flow_speed, time_width, rate_func)
        def updater(mob, dt):
            for line in mob.stream_lines:
                line.time += dt * flow_speed
                if line.time >= mob.virtual_time:
                    line.time -= mob.virtual_time
                mob._flash(line, line.time, flow_speed, time_width, rate_func)
        self.add_updater(updater)
        self.flow_animation, self.flow_speed, self.time_width = updater, flow_speed, time_width
        self._flow_rate_func = rate_func
        return self

    @staticmethod
    def _flash(line, time, flow_speed, time_width, rate_func=linear):
        """Show ShowPassingFlash's window of the full line, from cached source points."""
        run_time = line.duration / flow_speed
        alpha = rate_func(max(0, min(1, time / run_time)))
        upper = (1 + time_width) * alpha
        lower, upper = max(0, upper - time_width), max(0, min(1, upper))
        source = line._flow_source
        points = source.__dict__.get('_flow_points')
        if points is None:
            points = source._flow_points = source.get_points()
        curves = _partial_cubics(points, min(lower, upper), upper)[0] if len(points) >= 4 else []
        VMobject.set_points(line, [point for curve in curves for point in curve])

    def end_animation(self):
        if self.flow_animation is None:
            raise ValueError('You have to start the animation before fading it out.')
        self.remove_updater(self.flow_animation)
        self.flow_animation = None
        return _StreamLinesEnd(self)


class _StreamLinesEnd(Animation):
    """Finish each flash cycle (or wait out warm-up), then redraw every full line, as in Community."""
    def __init__(self, field):
        self.field = field
        speed, width = field.flow_speed, field.time_width
        self.max_run_time = field.virtual_time / speed
        # Community starts creation at the flash speed and eases out (ease_out_sine).
        self.creation = self.max_run_time / (1 + width) * (math.sin(.001 * math.pi / 2) * 1000)
        self.plans = []
        for index, line in enumerate(field.children):
            if isinstance(line, StreamLine):
                delay = -line.time / speed if line.time <= 0 else self.max_run_time - line.time / speed
                self.plans.append((index, line, line.time, delay))
        run_time = max([delay for *_, delay in self.plans] + [0]) + self.creation
        super().__init__(field, run_time=run_time, rate_func=linear)

    def begin(self, scene):
        super().begin(scene)
        # Full-line snapshots and flash probes are reused on every sampled frame.
        self.full = {index: line._flow_source.to_dict() for index, line, _, _ in self.plans}
        self.probes = {}
        for index, line, _, _ in self.plans:
            probe = StreamLine()
            probe.__dict__.update({key: value for key, value in line.__dict__.items() if key != 'children'})
            probe.children = []
            self.probes[index] = probe

    def sample(self, alpha):
        now = alpha * self.run_time
        result = dict(self.start)
        children = result['children'] = list(self.start['children'])
        field = self.field
        for index, line, start_time, delay in self.plans:
            if now >= delay:
                progress = math.sin(min(1, (now - delay) / self.creation) * math.pi / 2)
                children[index] = dict(self.full[index], draw_progress=progress)
            elif start_time <= 0:
                children[index] = dict(children[index], stroke_opacity=0)
            else:
                probe = self.probes[index]
                field._flash(probe, start_time + now * field.flow_speed, field.flow_speed,
                             field.time_width, field._flow_rate_func)
                children[index] = probe.to_dict()
        return [result]

    def finish(self, scene):
        for _, line, _, _ in self.plans:
            line.pointwise_become_partial(line._flow_source, 0, 1)
            line.time = 0


EXPORTS = ['config', 'Scene', 'MovingCameraScene', 'Mobject', 'ValueTracker', 'always_redraw', 'VMobject', 'TipableVMobject', 'TracedPath', 'ParametricFunction', 'FunctionGraph', 'CubicBezier', 'Circle', 'Ellipse', 'Arc', 'ArcBetweenPoints', 'ArcPolygon', 'ArcPolygonFromArcs', 'AnnularSector', 'Sector', 'Annulus', 'Dot', 'Square', 'Rectangle', 'RoundedRectangle', 'Line', 'DashedLine', 'DashedVMobject', 'TangentLine', 'Elbow', 'Angle', 'RightAngle', 'ArrowTip', 'ArrowTriangleTip', 'ArrowTriangleFilledTip', 'ArrowCircleTip', 'ArrowCircleFilledTip', 'ArrowSquareTip', 'ArrowSquareFilledTip', 'StealthTip', 'Arrow', 'DoubleArrow', 'CurvedArrow', 'CurvedDoubleArrow',
           'Triangle', 'Polygon', 'Polygram', 'RegularPolygram', 'RegularPolygon', 'Star', 'Brace', 'BraceBetweenPoints', 'BraceLabel', 'BraceText',
           'Title', 'BulletedList', 'Tex', 'SingleStringMathTex', 'MarkupText', 'LabeledDot', 'Variable', 'always', 'f_always', 'always_shift', 'always_rotate',
           'SurroundingRectangle', 'BackgroundRectangle', 'Cross', 'Underline', 'Text', 'DecimalNumber', 'Integer', 'MathTex', 'Group', 'VGroup', 'NumberLine', 'Axes', 'BarChart', 'PolarPlane', 'NumberPlane', 'ComplexPlane', 'VectorField', 'ArrowVectorField', 'StreamLines', 'sigmoid', 'ScreenRectangle', 'FullScreenRectangle', 'VectorizedPoint', 'ComplexValueTracker', 'UnitInterval', 'TangentialArc', 'CurvesAsSubmobjects', 'VDict', 'Cutout', 'ConvexHull', 'ArcBrace', 'LaggedStartMap', 'MaintainPositionRelativeTo', 'Blink', 'Broadcast', 'SpiralIn', 'AddTextWordByWord', 'Animation', 'line_intersection', 'angle_between_vectors', 'DEFAULT_LAGGED_START_LAG_RATIO', 'Graph', 'DiGraph', 'Union', 'Intersection', 'Difference', 'Exclusion', 'Code', 'SVGMobject', 'VMobjectFromSVGPath', 'ImageMobject', 'RESAMPLING_ALGORITHMS', 'Create', 'Write', 'Unwrite', 'DrawBorderThenFill', 'FadeIn',
           'AnimationGroup', 'LaggedStart', 'Succession', 'MoveAlongPath',
           'GrowFromCenter', 'GrowFromPoint', 'ShrinkToCenter', 'Restore', 'Indicate', 'ShowPassingFlash', 'TransformFromCopy',
           'FadeOut', 'Uncreate', 'Rotate', 'Rotating', 'Transform', 'ReplacementTransform',
           'ClockwiseTransform', 'CounterclockwiseTransform', 'MoveToTarget', 'CyclicReplace', 'Swap',
           'FadeTransform', 'ApplyPointwiseFunction', 'ApplyPointwiseFunctionToCenter', 'ApplyMatrix',
           'ApplyComplexFunction', 'ApplyFunction', 'Homotopy', 'SmoothedVectorizedHomotopy', 'ComplexHomotopy',
           'ApplyWave', 'PhaseFlow', 'ChangingDecimal', 'ChangeDecimalToValue', 'AnnotationDot', 'Label', 'Matrix', 'DecimalMatrix', 'IntegerMatrix', 'MobjectMatrix',
           'get_det_text', 'matrix_to_tex_string', 'matrix_to_mobject', 'Paragraph', 'Table', 'MathTable',
           'MobjectTable', 'IntegerTable', 'DecimalTable',
           'LabeledLine', 'LabeledArrow', 'TransformMatchingTex', 'TransformMatchingShapes', 'ApplyMethod', 'ScaleInPlace', 'FadeToColor', 'Wait', 'GrowFromEdge', 'GrowArrow',
           'SpinInFromNothing', 'Wiggle', 'FocusOn', 'UpdateFromFunc', 'UpdateFromAlphaFunc',
           'ShowIncreasingSubsets', 'ShowSubmobjectsOneByOne', 'AddTextLetterByLetter',
           'RemoveTextLetterByLetter', 'Circumscribe', 'Flash', 'UP', 'DOWN', 'LEFT',
           'RIGHT', 'ORIGIN', 'OUT', 'IN', 'UL', 'UR', 'DL', 'DR', 'BLUE', 'BLUE_D', 'RED', 'GREEN',
           'YELLOW', 'PURPLE', 'ORANGE', 'WHITE', 'BLACK', 'GRAY', 'GREY', 'PINK',
           'linear', 'smooth', 'there_and_back', 'PI', 'TAU', 'DEGREES',
           'SMALL_BUFF', 'MED_SMALL_BUFF', 'MED_LARGE_BUFF', 'LARGE_BUFF',
           'DEFAULT_MOBJECT_TO_EDGE_BUFFER', 'DEFAULT_MOBJECT_TO_MOBJECT_BUFFER',
           'DEFAULT_STROKE_WIDTH', 'DEFAULT_FONT_SIZE', 'DEFAULT_DOT_RADIUS',
           'DEFAULT_SMALL_DOT_RADIUS', 'DEFAULT_ARROW_TIP_LENGTH', 'color_to_rgb', 'rgb_to_color',
           'rgb_to_hex', 'hex_to_rgb', 'interpolate_color', 'color_gradient', 'average_color',
           'invert_color', 'rate_functions', 'smoothstep', 'smootherstep', 'smoothererstep', 'rush_into',
           'rush_from', 'slow_into', 'double_smooth', 'there_and_back_with_pause', 'running_start',
           'not_quite_there', 'wiggle', 'squish_rate_func', 'lingering', 'exponential_decay', 'NORMAL', 'ITALIC', 'OBLIQUE', 'BOLD', 'THIN', 'ULTRALIGHT', 'LIGHT',
           'SEMILIGHT', 'BOOK', 'MEDIUM', 'SEMIBOLD', 'ULTRABOLD', 'HEAVY', 'ULTRAHEAVY']
EXPORTS += [name for name in _PALETTE if name not in EXPORTS]


def _pooled_json(result, default):
    """Encode frames with each distinct mobject snapshot stored once in a shared pool.

    Nodes are pooled bottom-up: a pooled node's children are pool indices, and large
    arrays become {"$pool": index} references, always lower than the node's own index. Static objects and unchanged group members repeat across frames; the
    worker swaps indices for shared objects, so the page sees the ordinary frame format."""
    dumps = json.JSONEncoder(allow_nan=False, default=default).encode
    pool, index = [], {}
    def store(text):
        key = index.get(text)
        if key is None:
            key = index[text] = len(pool)
            pool.append(text)
        return key
    def intern(node):
        node = dict(node)
        for name, value in node.items():
            # Large arrays (curves, vertices) often outlive style-only changes such as
            # draw_progress or opacity, so they are pooled as {"$pool": index} too.
            if name != 'children' and type(value) is list and len(value) >= 8:
                text = dumps(value)
                if len(text) > 400:
                    node[name] = {'$pool': store(text)}
        children = node.get('children')
        if isinstance(children, list) and children:
            node['children'] = [intern(child) for child in children]
        return store(dumps(node))
    frames = [dumps(dict(frame, mobjects=[intern(m) for m in frame['mobjects']])) for frame in result['frames']]
    head = dumps({key: value for key, value in result.items() if key != 'frames'})
    return head[:-1] + ', "pool": [' + ', '.join(pool) + '], "frames": [' + ', '.join(frames) + ']}'


def _render_scene(source, scene_name=None, compact=False):
    module = types.ModuleType('manim')
    module.__all__ = list(EXPORTS)
    for name in EXPORTS:
        setattr(module, name, globals()[name])
    # Internally Vector is the coordinate tuple; scenes get Community's arrow.
    module.Vector = VectorArrow
    module.__all__.append('Vector')
    try:
        import numpy  # Loaded by the worker only when the source mentions it.
    except ImportError:
        pass
    else:
        module.np = numpy
        module.__all__.append('np')
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
    def plain(value):
        if hasattr(value, 'tolist'):
            return value.tolist()
        if isinstance(value, numbers.Real):
            return _plain_number(value)
        raise TypeError(f'Object of type {type(value).__name__} is not part of a preview frame')
    if compact:
        return _pooled_json(result, plain)
    return json.dumps(result, allow_nan=False, default=plain)


def _set_math_metrics(math_metrics):
    metrics = {}
    if math_metrics is not None:
        items = math_metrics.items() if hasattr(math_metrics, 'items') else None
        if items is None:
            raise TypeError('Math metrics must map expressions to [width, height] in em')
        def finite(values, low=-1000):
            return all(not isinstance(v, bool) and isinstance(v, _REAL) and math.isfinite(v) and low <= v <= 1000
                       for v in values)
        for text, size in items:
            size = list(size)
            parts = [list(part) for part in size[2]] if len(size) == 3 and isinstance(size[2], (list, tuple)) else None
            if (not isinstance(text, str) or len(text) > 4096 or len(size) not in (2, 3) or
                    not finite(size[:2], 0) or (len(size) == 3 and (parts is None or len(parts) > 256 or
                    any(len(part) != 4 or not finite(part) or not finite(part[2:], 0) for part in parts)))):
                raise ValueError('Math metrics must map expressions to finite [width, height(, parts)] in em')
            metrics[text] = ((float(size[0]), float(size[1])) if parts is None else
                             (float(size[0]), float(size[1]), [tuple(float(v) for v in part) for part in parts]))
            if len(metrics) > 1024:
                raise ValueError('At most 1024 math metrics may be supplied')
    _MATH_METRICS.clear()
    _MATH_METRICS.update(metrics)
    _MATH_ESTIMATED.clear()


def render_scene(source, scene_name=None, math_metrics=None, compact=False):
    """Render frames; math_metrics holds browser-measured MathTex ink sizes in em.

    compact=True pools repeated top-level snapshots (decoded by the worker)."""
    global config
    previous = config
    config = PreviewConfig()
    try:
        _set_math_metrics(math_metrics)
        return _render_scene(source, scene_name, compact)
    finally:
        config = previous
