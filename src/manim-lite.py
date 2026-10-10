"""Small, explicit Manim subset for SVG frame playback (not full Manim)."""
import bisect
import cmath
import contextlib
import copy
import enum
import functools
import inspect
import itertools
import json
import logging
import math
import numbers
import operator
import random
import re
import struct
import sys
import types
import typing

FPS = 15
MAX_FRAMES = 901  # 900 timed samples plus a final seekable state.


_REAL = numbers.Real  # Includes NumPy scalars; bool is excluded where it matters.


_PLAIN_VALUE_TYPES = frozenset((int, float, str, bool, type(None)))  # ManimColor is added below


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


_BOUNDS_MEMO = None  # Per-serialization cache of local bounds (see Mobject.to_dict).


def _bounds_query(method):
    """Cache bounds for the outermost geometry query, as serialization does.

    Nothing moves while a query runs (pivot compensation only shifts a posed
    parent's own position before its parent-frame bounds are first computed),
    so repeated child-bound evaluations inside one query are shared."""
    def query(self, *args, **kwargs):
        global _BOUNDS_MEMO
        if _BOUNDS_MEMO is not None:
            return method(self, *args, **kwargs)
        _BOUNDS_MEMO = {}
        try:
            return method(self, *args, **kwargs)
        finally:
            _BOUNDS_MEMO = None
    query.__name__, query.__doc__ = method.__name__, method.__doc__
    return query
# Attributes that only ever hold coordinates: serialization skips the mobject scan.
_POINT_KEYS = frozenset(('curves', 'vertices', 'position', 'start', 'end', 'shaft_start',
                         'shaft_end', 'shaft_curves', 'cloud'))


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
        if len(values) == 1 and hasattr(values[0], '__len__'):
            values = list(values[0])  # A single-row (1, 3) point array, as NumPy broadcasting allows.
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

    def __radd__(self, other):
        return Vector(a + b for a, b in zip(Vector(other), self))

    def __rsub__(self, other):
        return Vector(a - b for a, b in zip(Vector(other), self))


UP, DOWN = Vector((0, 1, 0)), Vector((0, -1, 0))
LEFT, RIGHT = Vector((-1, 0, 0)), Vector((1, 0, 0))
ORIGIN = Vector((0, 0, 0))
OUT, IN = Vector((0, 0, 1)), Vector((0, 0, -1))
UL, UR, DL, DR = UP + LEFT, UP + RIGHT, DOWN + LEFT, DOWN + RIGHT


_GRADIENT_TYPES = frozenset(('circle', 'arc', 'ellipse', 'square', 'rectangle', 'triangle', 'polygon',
                             'polyline', 'bezierpath', 'annulus', 'line', 'arrow'))


def _glyph_matrix(state):
    """A text/formula leaf's local linear glyph map [[a, b], [c, d]] (y up)."""
    matrix = state.get('glyph_matrix')
    if matrix is not None:
        return [[matrix[0], matrix[1]], [matrix[2], matrix[3]]]
    sx, sy = state.get('glyph_stretch', (1, 1))
    return [[sx, 0], [0, sy]]


class LineJointType(enum.IntEnum):
    """Stroke joins; AUTO is Cairo's (and SVG's) default miter join."""
    AUTO = 0
    ROUND = 1
    BEVEL = 2
    MITER = 3


class CapStyleType(enum.IntEnum):
    """Stroke end caps; AUTO is Cairo's (and SVG's) default butt cap."""
    AUTO = 0
    ROUND = 1
    BUTT = 2
    SQUARE = 3
class ManimColor(str):
    """Community's ManimColor as a hex string ('#RRGGBB') that also carries RGBA floats.

    Being a str keeps every existing hex-string color path working; the methods
    follow Community (truncating to_hex, interpolate, lighter/darker, ...)."""
    def __new__(cls, value=None, alpha=1.0):
        rgba = cls._parse(value, alpha)
        text = '#' + ''.join('%02X' % int(min(1, max(0, v)) * 255) for v in rgba[:3])
        color = str.__new__(cls, text)
        color._rgba = rgba
        return color

    @staticmethod
    def _parse(value, alpha=1.0):
        import re
        if value is None:
            return (0.0, 0.0, 0.0, alpha)
        if isinstance(value, ManimColor):
            return value._rgba
        if isinstance(value, str):
            text = value.strip()
            if text.upper() in _PALETTE and not text.startswith('#'):
                return _PALETTE[text.upper()]._rgba
            digits = text[1:] if text.startswith('#') else text[2:] if text.lower().startswith('0x') else None
            if digits is not None and re.fullmatch(r'[0-9a-fA-F]+', digits) and len(digits) in (3, 4, 6, 8):
                if len(digits) in (3, 4):
                    digits = ''.join(c * 2 for c in digits)
                values = [int(digits[i:i + 2], 16) / 255 for i in range(0, len(digits), 2)]
                return tuple(values) if len(values) == 4 else tuple(values) + (alpha,)
            raise ValueError(f'Unsupported color: {text[:40]}')
        if isinstance(value, bool):
            raise ValueError('Colors cannot be booleans')
        if isinstance(value, numbers.Integral):
            value = int(value)
            if not 0 <= value <= 0xFFFFFF:
                raise ValueError('Integer colors must be 0x000000 to 0xFFFFFF')
            return ((value >> 16 & 255) / 255, (value >> 8 & 255) / 255, (value & 255) / 255, alpha)
        try:
            values = [_plain_number(v) for v in value]
        except TypeError:
            raise ValueError(f'Unsupported color: {value!r}') from None
        if len(values) not in (3, 4) or any(isinstance(v, bool) or not isinstance(v, _REAL) or not math.isfinite(v) for v in values):
            raise ValueError('Color tuples need three or four finite components')
        if isinstance(values[0], numbers.Integral):
            # Community reads integer tuples as 0-255 channels (truncating any floats).
            values = [int(v) / 255 for v in values]
        values = [float(v) for v in values]
        return tuple(values) if len(values) == 4 else tuple(values) + (alpha,)

    @classmethod
    def parse(cls, color, alpha=1.0):
        if isinstance(color, (list, tuple)) and color and not isinstance(color[0], _REAL):
            return [cls(c, alpha) for c in color]
        return cls(color, alpha)

    def __repr__(self):
        return f"ManimColor('{self.to_hex(self._rgba[3] != 1)}')"

    def __reduce__(self):
        return (ManimColor, (self.to_hex(True),))

    def __deepcopy__(self, memo):
        return self  # Immutable.

    def to_hex(self, with_alpha=False):
        values = self._rgba if with_alpha else self._rgba[:3]
        return '#' + ''.join('%02X' % int(min(1, max(0, v)) * 255) for v in values)

    def to_rgb(self):
        return list(self._rgba[:3])

    def to_rgba(self):
        return list(self._rgba)

    def to_int_rgb(self):
        return [int(v * 255) for v in self._rgba[:3]]

    def to_int_rgba(self):
        return [int(v * 255) for v in self._rgba]

    def to_rgba_with_alpha(self, alpha):
        return list(self._rgba[:3]) + [alpha]

    def to_int_rgba_with_alpha(self, alpha):
        return [int(v * 255) for v in self._rgba[:3]] + [int(alpha * 255)]

    def to_integer(self):
        r, g, b = self.to_int_rgb()
        return r << 16 | g << 8 | b

    def to_hsv(self):
        import colorsys
        return list(colorsys.rgb_to_hsv(*self._rgba[:3]))

    def to_hsl(self):
        import colorsys
        h, l, s = colorsys.rgb_to_hls(*self._rgba[:3])
        return [h, s, l]

    @classmethod
    def from_rgb(cls, rgb, alpha=1.0):
        return cls(tuple(rgb), alpha)

    @classmethod
    def from_rgba(cls, rgba):
        return cls(tuple(rgba))

    @classmethod
    def from_hex(cls, hex_str, alpha=1.0):
        return cls(hex_str, alpha)

    @classmethod
    def from_hsv(cls, hsv, alpha=1.0):
        import colorsys
        return cls(tuple(float(v) for v in colorsys.hsv_to_rgb(*hsv)), alpha)

    @classmethod
    def from_hsl(cls, hsl, alpha=1.0):
        import colorsys
        h, s, l = hsl
        return cls(tuple(float(v) for v in colorsys.hls_to_rgb(h, l, s)), alpha)

    def interpolate(self, other, alpha):
        other = ManimColor(other)
        return ManimColor(tuple(float(a * (1 - alpha) + b * alpha) for a, b in zip(self._rgba, other._rgba)))

    def lighter(self, blend=0.2):
        return self.interpolate(ManimColor('#FFFFFF'), blend).opacity(self._rgba[3])

    def darker(self, blend=0.2):
        return self.interpolate(ManimColor('#000000'), blend).opacity(self._rgba[3])

    def opacity(self, opacity):
        return ManimColor(tuple(float(v) for v in self._rgba[:3]) + (float(opacity),))

    def invert(self, with_alpha=False):
        r, g, b, a = self._rgba
        return ManimColor((1.0 - r, 1.0 - g, 1.0 - b, 1.0 - a if with_alpha else a))

    def contrasting(self, threshold=0.5, light=None, dark=None):
        import colorsys
        luminance = colorsys.rgb_to_yiq(*self._rgba[:3])[0]
        if luminance < threshold:
            return ManimColor('#FFFFFF') if light is None else ManimColor(light)
        return ManimColor('#000000') if dark is None else ManimColor(dark)

    def into(self, class_type):
        return class_type(self) if class_type is not ManimColor else self

    @staticmethod
    def gradient(colors, length):
        return color_gradient(colors, length)


RGBA = ManimColor


class HSV(ManimColor):
    """A color built from (hue, saturation, value) components in [0, 1]."""
    def __new__(cls, hsv, alpha=1.0):
        import colorsys
        if isinstance(hsv, str):
            return ManimColor.__new__(cls, hsv, alpha)
        values = list(hsv)
        if len(values) not in (3, 4):
            raise ValueError('HSV Color must be an array of 3 values')
        rgb = tuple(float(v) for v in colorsys.hsv_to_rgb(*values[:3]))
        return ManimColor.__new__(cls, rgb + (values[3] if len(values) == 4 else alpha,))

    @property
    def hue(self):
        return self.to_hsv()[0]

    @property
    def saturation(self):
        return self.to_hsv()[1]

    @property
    def value(self):
        return self.to_hsv()[2]


ManimColorDType = float
ParsableManimColor = (str, tuple, list, int)


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
_PALETTE = {name: ManimColor(value) for name, value in _PALETTE.items()}
globals().update(_PALETTE)
_PLAIN_VALUE_TYPES = _PLAIN_VALUE_TYPES | {ManimColor}
# Community's _all_manim_colors, in order, so seeded RandomColorGenerator sequences match.
_ALL_MANIM_COLORS = [ManimColor(value) for value in ['#FFFFFF', '#DDDDDD', '#DDDDDD', '#BBBBBB', '#BBBBBB', '#888888', '#888888', '#444444', '#444444', '#222222', '#222222', '#000000', '#DDDDDD', '#DDDDDD', '#BBBBBB', '#BBBBBB', '#888888', '#888888', '#444444', '#444444', '#222222', '#222222', '#FF0000', '#00FF00', '#0000FF', '#00FFFF', '#FF00FF', '#FFFF00', '#C7E9F1', '#9CDCEB', '#58C4DD', '#29ABCA', '#236B8E', '#58C4DD', '#236B8E', '#ACEAD7', '#76DDC0', '#5CD0B3', '#55C1A7', '#49A88F', '#5CD0B3', '#C9E2AE', '#A6CF8C', '#83C167', '#77B05D', '#699C52', '#83C167', '#FFF1B6', '#FFEA94', '#F7D96F', '#F4D345', '#E8C11C', '#F7D96F', '#F7C797', '#F9B775', '#F0AC5F', '#E1A158', '#C78D46', '#F0AC5F', '#F7A1A3', '#FF8080', '#FC6255', '#E65A4C', '#CF5044', '#FC6255', '#ECABC1', '#EC92AB', '#C55F73', '#A24D61', '#94424F', '#C55F73', '#CAA3E8', '#B189C6', '#9A72AC', '#715582', '#644172', '#9A72AC', '#D147BD', '#DC75CD', '#FF862F', '#CD853F', '#8B4513', '#736357', '#736357', '#ECE7E2', '#87C2A5', '#525893', '#E07A5F', '#343434']]


class RandomColorGenerator:
    """Random Manim palette colors; a seed gives Community's reproducible sequence."""
    _singleton = None

    def __init__(self, seed=None, sample_colors=None):
        self.choice = random.choice if seed is None else random.Random(seed).choice
        self.colors = _ALL_MANIM_COLORS if sample_colors is None else list(sample_colors)

    def next(self):
        return ManimColor(self.choice(self.colors))

    @classmethod
    def _random_color(cls):
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton.next()


def random_color():
    return RandomColorGenerator._random_color()


def random_bright_color():
    return ManimColor(tuple(.5 + v / 2 for v in random_color().to_rgb()))


def _paint(value):
    """Community parses colors into ManimColor; gradient lists keep each stop."""
    if value is None or isinstance(value, ManimColor):
        return value
    if isinstance(value, (list, tuple)) and value and not isinstance(value[0], numbers.Real):
        return [_paint(v) for v in value]
    return ManimColor(value)
PI, TAU, DEGREES = math.pi, math.tau, math.pi / 180
SMALL_BUFF, MED_SMALL_BUFF, MED_LARGE_BUFF, LARGE_BUFF = 0.1, 0.25, 0.5, 1
DEFAULT_MOBJECT_TO_EDGE_BUFFER, DEFAULT_MOBJECT_TO_MOBJECT_BUFFER = MED_LARGE_BUFF, MED_SMALL_BUFF
DEFAULT_STROKE_WIDTH, DEFAULT_FONT_SIZE = 4, 48
DEFAULT_DOT_RADIUS, DEFAULT_SMALL_DOT_RADIUS = 0.08, 0.04
DEFAULT_ARROW_TIP_LENGTH = 0.35


def _color_rgb(color):
    if isinstance(color, ManimColor):
        return list(color._rgba[:3])
    if isinstance(color, (tuple, list)) or (isinstance(color, str) and color.upper() in _PALETTE):
        return list(ManimColor(color)._rgba[:3])
    if (not isinstance(color, str) or len(color) != 7 or color[0] != '#' or
            any(c not in '0123456789abcdefABCDEF' for c in color[1:])):
        raise ValueError('Colors must be six-digit hex strings such as #58C4DD')
    return [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]


def _rgb_color(rgb):
    # Community's ManimColor.to_hex truncates each channel (int(value * 255)).
    return ManimColor(tuple(float(min(1, max(0, v))) for v in rgb))


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

    @property
    def frame_x_radius(self):
        return self.frame_width / 2

    @frame_x_radius.setter
    def frame_x_radius(self, value):
        self.frame_width = 2 * value

    @property
    def frame_y_radius(self):
        return self.frame_height / 2

    @property
    def top(self):
        return Vector((0, self.frame_height / 2, 0))

    @property
    def bottom(self):
        return Vector((0, -self.frame_height / 2, 0))

    @property
    def left_side(self):
        return Vector((-self.frame_width / 2, 0, 0))

    @property
    def right_side(self):
        return Vector((self.frame_width / 2, 0, 0))

    @property
    def aspect_ratio(self):
        return self.pixel_width / self.pixel_height

    @property
    def frame_size(self):
        return (self.pixel_width, self.pixel_height)

    @property
    def frame_rate(self):
        return FPS

    @property
    def renderer(self):
        # Community code checks config.renderer; the preview draws like the Cairo renderer.
        return RendererType.CAIRO

    @frame_y_radius.setter
    def frame_y_radius(self, value):
        self.frame_height = 2 * value

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
        elif name not in ('frame_x_radius', 'frame_y_radius'):
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


# Classes whose __init__ defaults were changed by set_default, with their own original
# __init__ (None when inherited); render_scene restores them after every render.
_DEFAULT_OVERRIDES = {}
_NO_INIT = object()


def _set_default(cls, **kwargs):
    """Community's set_default: change (or, without arguments, reset) constructor defaults."""
    if cls not in _DEFAULT_OVERRIDES:
        _DEFAULT_OVERRIDES[cls] = cls.__dict__.get('__init__', _NO_INIT)
    original = _DEFAULT_OVERRIDES[cls]
    if kwargs:
        init = original if original is not _NO_INIT else super(cls, cls).__init__
        cls.__init__ = functools.partialmethod(init, **kwargs)
    else:
        _restore_default(cls)


def _restore_default(cls):
    original = _DEFAULT_OVERRIDES.pop(cls, None)
    if original is _NO_INIT:
        cls.__dict__.get('__init__') is not None and delattr(cls, '__init__')
    elif original is not None:
        cls.__init__ = original


class _UpdaterBuilder:
    """mobject.always.method(...) adds an updater calling that method every frame."""
    def __init__(self, mobject):
        self._mobject = mobject

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        def add_updater(*args, **kwargs):
            self._mobject.add_updater(lambda m: getattr(m, name)(*args, **kwargs), call_updater=True)
            return self
        return add_updater


class Mobject:
    # Subclass bookkeeping (e.g. Graph adjacency) that frames never store.
    _frame_excluded = ()
    # Stroke caps/joins and sheen are stored per instance only when changed.
    joint_type = LineJointType.AUTO
    cap_style = CapStyleType.AUTO
    sheen_factor = 0
    sheen_direction = UL

    def __init__(self, color=WHITE, fill_opacity=0, stroke_width=2,
                 fill_color=None, stroke_color=None, stroke_opacity=1, z_index=0,
                 shade_in_3d=False, joint_type=None, cap_style=None, sheen_factor=0,
                 sheen_direction=None, **kwargs):
        if kwargs:
            raise NotImplementedError('Unsupported options: ' + ', '.join(kwargs))
        if joint_type is not None:
            self.joint_type = LineJointType(joint_type)
        if cap_style is not None:
            self.cap_style = CapStyleType(cap_style)
        if sheen_factor or sheen_direction is not None:
            self.set_sheen(sheen_factor, sheen_direction, family=False)
        self.position = list(ORIGIN)
        self.shade_in_3d = bool(shade_in_3d)
        color, fill_color, stroke_color = _paint(color), _paint(fill_color), _paint(stroke_color)
        self.color = color
        self.fill_color = color if fill_color is None else fill_color
        self.stroke_color = color if stroke_color is None else stroke_color
        fill_opacity = self._opacity_channel('fill', fill_opacity)
        stroke_opacity = self._opacity_channel('stroke', stroke_opacity)
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
        unique = list(dict.fromkeys(mobjects))
        self._release([m for m in self.children if m not in unique])
        self._adopt(unique)
        self._replace_children(unique)

    def _release(self, mobjects):
        # A member leaving a posed parent keeps its world placement, as in Community.
        if self.angle == 0 and self.geometry_scale == 1 and not any(self.position):
            return
        for mobject in mobjects:
            if mobject in self.children:
                self._place_in_world(mobject)

    def _place_in_world(self, mobject):
        pivot = Vector(mobject._pivot_point())
        world = self._point_to_world(pivot)
        mobject.scale(self.geometry_scale, about_point=pivot).rotate(self.angle, about_point=pivot)
        return mobject.shift(world - pivot)

    def _world_member(self, child):
        """A world-placed copy of a direct child (child queries are parent-local)."""
        return self._place_in_world(child.copy())

    def _adopt(self, mobjects):
        # Community children live in world coordinates; a posed parent stores them
        # locally, so newly added world-placed members are re-posed to stay in place.
        if not self.geometry_scale:
            return  # A collapsed parent has no inverse; members keep their own pose.
        for mobject in mobjects:
            if mobject not in self.children:
                self._to_local_pose(mobject)

    def add(self, *mobjects):
        self._validate_children(mobjects)
        unique = list(dict.fromkeys(mobjects))
        self._adopt(unique)
        self._replace_children([m for m in self.children if m not in unique] + unique)
        return self

    def add_to_back(self, *mobjects):
        self._validate_children(mobjects)
        unique = list(dict.fromkeys(mobjects))
        self._adopt(unique)
        self._replace_children(unique + [m for m in self.children if m not in unique])
        if self._type in ('text', 'mathtex'):
            # Community glyphs are submobjects, so these paint behind the text.
            for mobject in unique:
                mobject.behind_parent = True
        return self

    def remove(self, *mobjects):
        if any(not isinstance(m, Mobject) for m in mobjects):
            raise TypeError('Mobject removal expects Mobjects')
        self._release([m for m in self.children if m in mobjects])
        self._replace_children([m for m in self.children if m not in mobjects])
        return self

    def _tip_shaft_curves(self, skip_role=None):
        """Community's reset_endpoints_based_on_tip: a curved path with tips keeps its shape
        but is moved by the similarity taking its ends onto the tip bases."""
        curves = self.__dict__.get('curves', [])
        if not self.__dict__.get('_curved_tip_path') or not curves:
            return curves
        ends = {}
        for child in self.children:
            role = child.__dict__.get('_tip_role')
            if role in ('start', 'end') and role != skip_role:
                tip_curves = _path_curves(child.to_dict())
                if tip_curves:
                    index = len(tip_curves) / 2
                    point = VMobject._bezier_point(tip_curves[min(int(index), len(tip_curves) - 1)], index - int(index))
                    ends[role] = child._point_to_world(point)
        if not ends:
            return curves
        return _fit_curve_endpoints(curves, ends.get('start', curves[0][0]), ends.get('end', curves[-1][-1]))

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

    # Community's width/height: world extents, and assigning one rescales uniformly.
    # Analytical shapes keep their local dimensions in __dict__ under the same names.
    @property
    def width(self):
        return self.__dict__['width'] if 'width' in self.__dict__ else self.get_width()

    @width.setter
    def width(self, value):
        self.rescale_to_fit(value, 0)

    @width.deleter
    def width(self):
        self.__dict__.pop('width', None)

    @property
    def height(self):
        return self.__dict__['height'] if 'height' in self.__dict__ else self.get_height()

    @height.setter
    def height(self, value):
        self.rescale_to_fit(value, 1)

    @height.deleter
    def height(self):
        self.__dict__.pop('height', None)

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

    @_bounds_query
    def _z_extent(self):
        memo = _BOUNDS_MEMO
        key = ('z', id(self))
        if key not in memo:
            memo[key] = self._compute_z_extent()
        return memo[key]

    def _compute_z_extent(self):
        """(min, max) of this mobject's z coordinates in its parent frame.

        Own geometry contributes the pose-mapped z of its bound points (the
        same pz + cz + (z - cz) * scale formula as _points_to_world). Child
        extents, expressed in this node's frame, are mapped through this pose
        again. A point-free leaf yields only its position's z, and a pure
        container contributes nothing of its own."""
        center_z = self._geometry_center()[2]
        pivot_z = self.position[2] + center_z
        scale = self.geometry_scale
        zs = []
        own = self._own_bound_points()
        if own:
            zs.extend(pivot_z + ((point[2] if len(point) > 2 else 0) - center_z) * scale
                      for point in own)
        for child in self.children:
            low, high = child._z_extent()
            zs.extend(pivot_z + (z - center_z) * scale for z in (low, high))
        depth = self.__dict__.get('glyph_depth') if self._type in ('text', 'mathtex') else None
        if depth:
            # A text plane turned out of XY spans the z of its mapped ink box.
            width, height = self._glyph_size()
            half = (abs(depth[0]) * width + abs(depth[1]) * height) / 2 * scale
            zs.extend((pivot_z - half, pivot_z + half))
        if not zs:
            return self.position[2], self.position[2]
        return min(zs), max(zs)

    def _critical_point(self, direction):
        left, bottom, right, top = self._bounds()
        low, high = self._z_extent()
        x, y, z = direction
        return Vector((right if x > 0 else left if x < 0 else (left + right) / 2,
                       top if y > 0 else bottom if y < 0 else (bottom + top) / 2,
                       high if z > 0 else low if z < 0 else (low + high) / 2))

    @_bounds_query
    def get_critical_point(self, direction):
        direction = Vector(direction)
        if not all(math.isfinite(value) for value in direction):
            raise ValueError('Boundary direction must be finite')
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

    def get_zenith(self):
        """Community's name for the critical point along OUT."""
        return self.get_critical_point(OUT)

    def get_nadir(self):
        """Community's name for the critical point along IN."""
        return self.get_critical_point(IN)

    def get_depth(self):
        low, high = self._z_extent()
        return high - low

    @_bounds_query
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
        if isinstance(dim,bool) or not isinstance(dim, numbers.Integral) or dim not in (0,1,2):
            raise ValueError('Size fitting dimension must be 0 (width), 1 (height) or 2 (depth)')
        return dim

    def length_over_dim(self, dim):
        self._fit_dimension(dim)
        return self.get_width() if dim == 0 else self.get_height() if dim == 1 else self.get_depth()

    def stretch(self, factor, dim, *, about_point=None, about_edge=None):
        NumberLine._real(factor,'Stretch factor')
        self._fit_dimension(dim)
        def function(point):
            values = list(point)
            values[dim] *= factor
            return values
        if dim == 2 or self._is_3d():
            # Scaling z (or stretching a 3D family at all) bakes the points.
            return self._map_points_3d(function, about_point, about_edge)
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
        if about_point is None and about_edge is None:
            about_point = ORIGIN
        if full[2] != [0, 0, 1] or self._is_3d():
            pivot = self._pivot_3d(about_point, about_edge)
            return self._map_points_3d(lambda point: _apply_rows(full, point), pivot)
        return self._apply_xy_map(lambda point:[sum(a*b for a,b in zip(row,point)) for row in full],
                                  about_point,about_edge,linear=True)

    def apply_function(self, function, *, about_point=None, about_edge=None):
        if not callable(function):
            raise TypeError('apply_function expects a callable point map')
        if about_point is None and about_edge is None:
            about_point = ORIGIN
        if self._is_3d():
            return self._map_points_3d(function, about_point, about_edge)
        try:
            return self._apply_xy_map(function,about_point,about_edge)
        except NotImplementedError as error:
            if 'preserve the XY plane' not in str(error):
                raise
            return self._map_points_3d(function, about_point, about_edge)

    def apply_points_function(self, func, about_point=None, about_edge=None, works_on_bounding_box=False):
        return self.apply_function(func, about_point=about_point, about_edge=about_edge)

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
            if (not linear and old._type == 'text' and not old.children and isinstance(old, Text)
                    and not isinstance(old, MathTex) and '_number_format' not in old.__dict__
                    and sum(not ch.isspace() for ch in old.text) > 1):
                # Nonlinear maps move each glyph with its own local linear map.
                old._explode()
                new._explode()
            old._geometry_center()
            def world(point):
                return parent_world(old._point_to_world(Vector(point)))
            if old._type in ('vgroup','mobject'):
                # Pure containers stay at their parent's origin, so their children keep
                # world-space coordinates (and no synthetic origin is ever mapped).
                origin = Vector(parent_origin)
            else:
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
            elif kind in ('text','mathtex'):
                # Glyphs have no outline points here: the leaf keeps its center's image and
                # a local linear glyph map (the map's derivative there; exact for linear maps).
                center = world(ORIGIN)
                image = mapped(center)
                if linear:
                    jacobian = [mapped(pivot+direction)-mapped(pivot) for direction in (RIGHT,UP)]
                else:
                    step = 1e-4
                    jacobian = [(mapped(center+direction*step)-mapped(center-direction*step))*(1/(2*step))
                                for direction in (RIGHT,UP)]
                frame = [world(RIGHT)-center, world(UP)-center]
                (ga,gb),(gc,gd) = _glyph_matrix(old.__dict__)
                # total = J . L . G, with L the leaf's current local-to-world linear part.
                la,lb,lc,ld = frame[0][0],frame[1][0],frame[0][1],frame[1][1]
                ja,jb,jc,jd = jacobian[0][0],jacobian[1][0],jacobian[0][1],jacobian[1][1]
                ma,mb,mc,md = ja*la+jb*lc, ja*lb+jb*ld, jc*la+jd*lc, jc*lb+jd*ld
                matrix = [ma*ga+mb*gc, ma*gb+mb*gd, mc*ga+md*gc, mc*gb+md*gd]
                new.__dict__.pop('glyph_stretch',None)
                new.__dict__.pop('glyph_matrix',None)
                if abs(matrix[1]) <= 1e-12 and abs(matrix[2]) <= 1e-12:
                    new.glyph_stretch = [matrix[0], matrix[3]]  # Axis-aligned stretching.
                else:
                    new.glyph_matrix = matrix
                new.position,new.angle,new.geometry_scale = list(image-parent_origin),0,1
                for key in ('_family_pivot_cache','_sampled_geometry_center'):
                    new.__dict__.pop(key,None)
                for old_child,new_child in zip(old.children,new.children):
                    visit(old_child,new_child,world,image)
                return
            elif kind == 'pointcloud':
                # Point clouds map point by point (stored in the local frame).
                new.cloud = [list(mapped(world((p[0],p[1],0))) - origin)[:2] for p in old.cloud]
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

    def _glyph_size(self):
        """The unmapped ink box (width, height) of a text or formula leaf."""
        if self._type == 'mathtex' and 'glyph' in self.__dict__:
            glyphs = _math_glyphs(self.text, self.font_size, self.__dict__.get('part_strings'))
            return glyphs[self.glyph][2:4] if self.glyph < len(glyphs) else (0, 0)
        if self._type == 'mathtex' and 'part' in self.__dict__:
            return _math_parts(self.text, self.part_strings, self.font_size)[self.part][2:]
        return _math_box(self.text, self.font_size) if self._type == 'mathtex' else _text_extent(self.__dict__)

    def _is_3d(self):
        """True when any family member holds geometry outside the XY plane."""
        for member in self.get_family():
            if member.position[2] or member.__dict__.get('glyph_depth'):
                return True
            state = member.__dict__
            vertices = state.get('vertices')
            # Graph keeps a vertex dict under the same name; only point lists count.
            points = list(vertices) if isinstance(vertices, list) else []
            for key in ('start', 'end', 'shaft_start', 'shaft_end'):
                if state.get(key) is not None:
                    points.append(state[key])
            for curve in state.get('curves') or ():
                points.extend(curve)
            if any(len(point) > 2 and point[2] for point in points):
                return True
        return False

    def _map_points_3d(self, function, about_point=None, about_edge=None):
        """Apply an arbitrary 3D point map, baking geometry into world points.

        Path leaves become 'bezierpath' curves with an identity pose; other
        leaves move their anchor. All results are validated before the family
        is mutated (the work happens on a copy committed through become)."""
        if isinstance(self, CameraFrame):
            raise NotImplementedError('Camera point mapping is not implemented')
        pivot = self._pivot_3d(about_point, about_edge)
        if pivot is None:
            pivot = Vector(ORIGIN)
        def mapped(point):
            values = list(function(Vector(point) - pivot))
            if len(values) not in (2, 3):
                raise ValueError('Point maps must return two or three coordinates')
            for value in values:
                NumberLine._real(value, 'Mapped coordinate')
            result = Vector(values) + pivot
            if not all(math.isfinite(value) for value in result):
                raise ValueError('Mapped geometry must be finite')
            return list(result)
        target = self.copy()
        target._bake_3d_map(mapped)
        return self.become(target)

    def _bake_3d_map(self, mapped):
        # Children of a posed parent are stored parent-locally; release them into
        # world coordinates first, so each member's own pose spans its geometry.
        if self.children and (self.angle or self.geometry_scale != 1 or any(self.position)):
            for child in list(self.children):
                self._place_in_world(child)
            if self._type in ('vgroup', 'mobject', 'valuetracker'):
                self.position, self.angle, self.geometry_scale = [0, 0, 0], 0, 1
        for child in list(self.children):
            child._bake_3d_map(mapped)
        kind = self._type
        if kind in _PATH_TYPES:
            snapshot = _snapshot_copy(self.__dict__)
            snapshot['type'] = kind
            paths = _path_subpaths(snapshot, include_pending=False)
            # Community's apply_function pulls handles to a small fraction of
            # their anchor distance, maps, then scales back up.
            eps = getattr(self, 'pre_function_handle_to_anchor_scale_factor', 0.01)
            def mapped_curve(curve):
                a0, h1, h2, a1 = (Vector(p) for p in curve)
                m0 = mapped(self._point_to_world(a0))
                m1 = mapped(self._point_to_world(a1))
                near1 = mapped(self._point_to_world(a0 + (h1 - a0) * eps))
                near2 = mapped(self._point_to_world(a1 + (h2 - a1) * eps))
                return [m0, [m0[i] + (near1[i] - m0[i]) / eps for i in range(3)],
                        [m1[i] + (near2[i] - m1[i]) / eps for i in range(3)], m1]
            self.curves = [mapped_curve(curve) for path in paths for curve in path]
            pending = (self.vertices if kind == 'bezierpath' else
                       self.vertices if kind == 'polyline' and len(self.vertices) == 1 else [])
            self.vertices = [mapped(self._point_to_world(Vector(p))) for p in pending]
            if kind in ('line', 'arrow'):
                self.start = mapped(self._point_to_world(Vector(self.start)))
                self.end = mapped(self._point_to_world(Vector(self.end)))
            self._type = 'bezierpath'
            self.position, self.angle, self.geometry_scale = [0, 0, 0], 0, 1
            self.__dict__.pop('subpath_lengths', None)
            if len(paths) > 1:
                self.subpath_lengths = [len(path) for path in paths]
            # The displayed shaft is baked before the tip family is deformed,
            # exactly as _apply_xy_map handles curved-arrow shafts.
            for key in ('_curved_tip_path', '_curve_arc_center', '_family_pivot_cache',
                        '_sampled_geometry_center', 'shaft_curves', 'shaft_start', 'shaft_end'):
                self.__dict__.pop(key, None)
            if '_curve_arc_center' in snapshot:
                self._curve_arc_center = mapped(self._point_to_world(Vector(snapshot['_curve_arc_center'])))
        elif kind in ('text', 'mathtex'):
            # Community maps the glyph outlines: keep the anchor's image and the map's
            # derivative there as a 3x2 local glyph map (rows x, y in glyph_matrix and
            # z in glyph_depth), exact for rotations and other linear maps.
            center = self._geometry_center()
            anchor = self._point_to_world(center)
            image = Vector(mapped(anchor))
            (ga, gb), (gc, gd) = _glyph_matrix(self.__dict__)
            ge, gf = self.__dict__.get('glyph_depth') or (0, 0)
            c, s_, k = math.cos(self.angle), math.sin(self.angle), self.geometry_scale
            local = [[k * (c * ga - s_ * gc), k * (c * gb - s_ * gd)],
                     [k * (s_ * ga + c * gc), k * (s_ * gb + c * gd)], [k * ge, k * gf]]
            step = 1e-4
            jacobian = [[(mapped(anchor + Vector(axis) * step)[row] - mapped(anchor - Vector(axis) * step)[row])
                         / (2 * step) for axis in (RIGHT, UP, OUT)] for row in range(3)]
            total = [[sum(jacobian[r][m] * local[m][col] for m in range(3)) for col in range(2)] for r in range(3)]
            for key in ('glyph_stretch', 'glyph_matrix', 'glyph_depth', '_family_pivot_cache', '_sampled_geometry_center'):
                self.__dict__.pop(key, None)
            self.glyph_matrix = [total[0][0], total[0][1], total[1][0], total[1][1]]
            if abs(total[2][0]) > 1e-12 or abs(total[2][1]) > 1e-12:
                self.glyph_depth = [total[2][0], total[2][1]]
            self.angle, self.geometry_scale = 0, 1
            self.position = list(image - center)
        elif kind not in ('vgroup', 'mobject', 'valuetracker'):
            # Images and other non-path leaves: only the anchor is mapped (they stay
            # upright facing the camera).
            center = self._geometry_center()
            anchor = self._point_to_world(center)
            self.position = list(Vector(mapped(anchor)) - (anchor - Vector(self.position)))

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

    def shift_onto_screen(self, buff=DEFAULT_MOBJECT_TO_EDGE_BUFFER):
        """Community's shift_onto_screen: pull any edge past the frame back inside."""
        for vect in (UP, DOWN, LEFT, RIGHT):
            dim = 0 if vect[0] else 1
            limit = (config.frame_width if dim == 0 else config.frame_height) / 2 - buff
            if sum(a * b for a, b in zip(self.get_edge_center(vect), vect)) > limit:
                self.to_edge(vect, buff=buff)
        return self

    def is_off_screen(self):
        return (self.get_left()[0] > config.frame_width / 2 or
                self.get_right()[0] < -config.frame_width / 2 or
                self.get_bottom()[1] > config.frame_height / 2 or
                self.get_top()[1] < -config.frame_height / 2)

    def center(self):
        return self.shift(Vector(ORIGIN) - self.get_center())

    @staticmethod
    def _coordinate_dim(dim):
        if isinstance(dim, bool) or not isinstance(dim, numbers.Integral) or dim not in (0, 1, 2):
            raise ValueError('Coordinate dimension must be 0, 1 or 2')
        return dim

    def get_coord(self, dim, direction=ORIGIN):
        self._coordinate_dim(dim)
        direction = Vector(direction)
        if not all(math.isfinite(v) for v in direction):
            raise ValueError('Coordinate direction must be finite')
        return self.get_critical_point(direction)[dim]

    def get_x(self, direction=ORIGIN):
        return self.get_coord(0, direction)

    def get_y(self, direction=ORIGIN):
        return self.get_coord(1, direction)

    def get_z(self, direction=ORIGIN):
        return self.get_coord(2, direction)

    def set_coord(self, value, dim, direction=ORIGIN):
        NumberLine._real(value, 'Coordinate')
        self._coordinate_dim(dim)
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
        direction = Vector(direction)
        if not all(math.isfinite(v) for v in direction):
            raise ValueError('Alignment direction must be finite')
        point = (mobject_or_point.get_critical_point(direction) if isinstance(mobject_or_point, Mobject)
                 else self._xy_vector(mobject_or_point, 'Alignment point'))
        offset = [point[dim] - self.get_coord(dim, direction) if direction[dim] else 0
                  for dim in (0, 1, 2)]
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

    def _pivot_3d(self, about_point, about_edge):
        """Like _pivot, but allows a pivot outside the XY plane."""
        if about_point is not None and about_edge is not None:
            raise ValueError('Pass about_point or about_edge, not both')
        if about_edge is not None:
            edge = Vector(about_edge)
            if not all(math.isfinite(v) for v in edge):
                raise ValueError('Pivot edge must be finite')
            return self.get_critical_point(edge)
        if about_point is None:
            return None
        point = Vector(about_point)
        if not all(math.isfinite(v) for v in point):
            raise ValueError('Pivot point must be finite')
        return point

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
        if self._type == 'pointcloud':
            if not self.cloud:
                return (0, 0, 0, 0)
            xs, ys = [p[0] for p in self.cloud], [p[1] for p in self.cloud]
            return (min(xs), min(ys), max(xs), max(ys))
        if self._type in ('line', 'arrow'):
            points = [self.start, self.end]
        elif self._type in ('polygon', 'polyline'):
            points = self.vertices
        elif self._type == 'bezierpath':
            # Community edges use anchors (get_points_defining_boundary); sizes include handles.
            # A tipped curve's own points are its shaft, refit between the tip bases.
            curves = self._tip_shaft_curves()
            points = ([point for curve in curves for point in curve] if _BOUNDS_WITH_HANDLES else
                      [point for curve in curves for point in (curve[0], curve[-1])]) + getattr(self, 'vertices', [])
        elif self._type == 'triangle':
            height = math.sqrt(3) / 2
            points = [(0, height * 2 / 3), (-0.5, -height / 3), (0.5, -height / 3)]
        elif self._type in ('text', 'mathtex'):
            # Text is centered on its estimated (Text) or measured (MathTex) ink box.
            width, height = self._glyph_size()
            (a, b), (c, d) = _glyph_matrix(self.__dict__)
            # The glyph map's image of the centered ink box.
            half_w, half_h = (abs(a) * width + abs(b) * height) / 2, (abs(c) * width + abs(d) * height) / 2
            return (-half_w, -half_h, half_w, half_h)
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
        memo = _BOUNDS_MEMO
        if memo is None:
            return self._compute_local_bounds()
        key = (id(self), _BOUNDS_WITH_HANDLES)
        result = memo.get(key)
        if result is None:
            result = memo[key] = self._compute_local_bounds()
        return result

    def _compute_local_bounds(self):
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
        memo = _BOUNDS_MEMO
        if memo is not None:
            # Within one serialization the first call already applied any pivot
            # compensation below, so later calls would return the same center.
            key = ('center', id(self))
            result = memo.get(key)
            if result is None:
                result = memo[key] = self._compute_anchor_center()
            return Vector(result)
        return self._compute_anchor_center()

    def _compute_anchor_center(self):
        left, bottom, right, top = self._local_bounds()
        center = Vector(((left + right) / 2, (bottom + top) / 2, 0))
        if self.children:
            # A tipped curve's refit shaft moves with its tips: key its own geometry by the raw curves.
            own = (tuple(map(tuple, (p for curve in self.curves for p in curve)))
                   if self.__dict__.get('_curved_tip_path') else self._own_local_bounds())
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

    @_bounds_query
    def get_center(self):
        # Community's center is the bounds center; it differs from the pivot only
        # for rotated point-based outlines, whose bounds use rotated points.
        z = sum(self._z_extent()) / 2
        if (math.sin(2 * self.angle) and not self.children and
                (self._own_bound_points() or self._type in ('arc', 'ellipse'))) or (self.children and self._rotated_family()):
            left, bottom, right, top = self._bounds()
            return Vector(((left + right) / 2, (bottom + top) / 2, z))
        pivot = self._pivot_point()
        return Vector((pivot[0], pivot[1], z))

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
        return self._points_to_world(points)

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

    def get_midpoint(self):
        """Community's get_midpoint: the point halfway along the path."""
        return self.point_from_proportion(0.5) if self.has_points() else self.get_center()

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

    def insert_n_curves(self, n):
        """Community's bezier_remap: split curves into equal-parameter pieces."""
        if isinstance(n, bool) or not isinstance(n, numbers.Integral) or not 0 <= n <= 10000:
            raise ValueError('insert_n_curves expects an integer from 0 to 10000')
        points = self.get_points()
        count = len(points) // 4
        if not n or not count:
            return self
        lengths = list(self.__dict__.get('subpath_lengths') or [count])
        total = count + n
        splits = [0] * count
        for index in range(total):
            splits[index * count // total] += 1
        curves = []
        for index in range(count):
            remaining, parts = points[4 * index:4 * index + 4], splits[index]
            for part in range(parts - 1):
                left, remaining = _split_cubic(remaining, 1 / (parts - part))
                curves.append(left)
            curves.append(remaining)
        new_lengths, offset = [], 0
        for length in lengths:
            new_lengths.append(sum(splits[offset:offset + length]))
            offset += length
        VMobject.set_points(self, [list(p) for curve in curves for p in curve] + list(points[4 * count:]))
        if len(new_lengths) > 1:
            self.subpath_lengths = new_lengths
        return self

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

    def match_points(self, mobject, copy_submobjects=True):
        """Community's match_points: each family member takes its partner's points."""
        if not isinstance(mobject, Mobject):
            raise TypeError('match_points expects a Mobject')
        for member, source in zip(self.get_family(), mobject.get_family()):
            if isinstance(member, VMobject) and source._type in _PATH_TYPES:
                VMobject.set_points(member, source.get_points())
        return self

    def get_pieces(self, n_pieces):
        """Community's get_pieces: n equal-parameter partial copies, no children."""
        if isinstance(n_pieces, bool) or not isinstance(n_pieces, numbers.Integral) or n_pieces < 1:
            raise ValueError('Piece count must be a positive integer')
        if n_pieces > 1000:
            raise ValueError('Piece count is limited to 1000')
        template = self.copy()
        template._replace_children([])
        alphas = _linspace(0, 1, int(n_pieces) + 1)
        return Group(*(template.copy().pointwise_become_partial(self, a1, a2)
                       for a1, a2 in zip(alphas[:-1], alphas[1:])))

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
            # Baked 3D paths keep z; flat paths use the faster XY sampler.
            bez = _bez3 if any(len(p) > 2 and p[2] for curve in self.curves for p in curve) else _bez
            for curve in self.curves:
                # Plain-tuple sampling (_bez); Vector arithmetic here dominated MoveAlongPath.
                samples = [bez(curve, i / 20) for i in range(21)]
                lengths.append(sum(math.dist(a, b) for a, b in zip(samples, samples[1:])))
            total = sum(lengths)
            if not math.isfinite(total):
                raise ValueError('Path length must be finite')
            remaining = alpha * total
            for curve, length in zip(self.curves, lengths):
                if remaining <= length:
                    point = bez(curve, remaining / length if length else 0)
                    return self._point_to_world(Vector((*point, 0)[:3]))
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
        if self.angle == 0 and self.geometry_scale == 1:
            point = Vector(self.position) + point
        else:
            center = self._geometry_center()
            offset = (point - center) * self.geometry_scale
            point = Vector(self.position) + center + Vector((
                offset[0] * math.cos(self.angle) - offset[1] * math.sin(self.angle),
                offset[0] * math.sin(self.angle) + offset[1] * math.cos(self.angle),
                offset[2]))
        if not all(math.isfinite(v) for v in point):
            raise ValueError('Path coordinates must be finite')
        return point

    def _points_to_world(self, points):
        """_point_to_world for many points, computing the pivot once."""
        px, py, pz = self.position
        if self.angle == 0 and self.geometry_scale == 1:
            result = [[px + p[0], py + p[1], pz + (p[2] if len(p) > 2 else 0)] for p in points]
        else:
            cx, cy, cz = self._geometry_center()
            scale, cos, sin = self.geometry_scale, math.cos(self.angle), math.sin(self.angle)
            result = []
            for p in points:
                ox, oy, oz = (p[0] - cx) * scale, (p[1] - cy) * scale, ((p[2] if len(p) > 2 else 0) - cz) * scale
                result.append([px + cx + ox * cos - oy * sin, py + cy + ox * sin + oy * cos, pz + cz + oz])
        if not all(math.isfinite(v) for point in result for v in point):
            raise ValueError('Path coordinates must be finite')
        return result

    def _own_bound_points(self):
        """Local points that define a point-based outline's bounds, or None."""
        if self._type in ('polygon', 'polyline'):
            return self.vertices
        if self._type in ('line', 'arrow'):
            return [self.start, self.end]
        if self._type == 'bezierpath':
            curves = self._tip_shaft_curves()
            return ([p for curve in curves for p in curve] if _BOUNDS_WITH_HANDLES else
                    [p for curve in curves for p in (curve[0], curve[-1])]) + getattr(self, 'vertices', [])
        if self._type in ('square', 'rectangle', 'triangle'):
            return [curve[0] for curve in _path_curves(self.to_dict() if self._type == 'triangle' else
                    {'type': self._type, 'side_length': getattr(self, 'side_length', 0),
                     'width': self.__dict__.get('width', 0), 'height': self.__dict__.get('height', 0)})]
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
                                                  'inner_radius', 'outer_radius', 'num_components')}
                                      | {'type': self._type})
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
        memo = _BOUNDS_MEMO
        if memo is not None:
            key = ('bounds', id(self), _BOUNDS_WITH_HANDLES)
            result = memo.get(key)
            if result is None:
                result = memo[key] = self._compute_bounds()
            return result
        return self._compute_bounds()

    def _compute_bounds(self):
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

    def scale(self, scale_factor, *, about_point=None, about_edge=None, scale_stroke=False):
        self._scale(scale_factor, about_point=about_point, about_edge=about_edge)
        if scale_stroke:
            # Community multiplies each member's stroke width by the scale factor.
            for member in self.get_family():
                member.stroke_width = abs(scale_factor) * member.stroke_width
        return self

    def _scale(self, scale_factor, *, about_point=None, about_edge=None):
        if not isinstance(scale_factor, _REAL) and (isinstance(scale_factor, (list, tuple)) or
                                                   hasattr(scale_factor, 'tolist')):
            # Community multiplies points by a per-axis vector (NumPy broadcasting).
            factors = list(scale_factor.tolist() if hasattr(scale_factor, 'tolist') else scale_factor)
            if not 1 <= len(factors) <= 3:
                raise ValueError('A per-axis scale factor needs one to three values')
            for value in factors:
                NumberLine._real(value, 'Scale factor')
            fx, fy = (factors * 2)[:2] if len(factors) == 1 else factors[:2]
            fz = factors[2] if len(factors) == 3 else 1
            pivot = self._pivot_3d(about_point, about_edge)
            if fz != 1 or self._is_3d():
                pivot = self.get_center() if pivot is None else pivot
                return self._map_points_3d(lambda p: [p[0] * fx, p[1] * fy, p[2] * fz], pivot)
            return self.apply_matrix([[fx, 0], [0, fy]],
                                     about_point=self.get_center() if pivot is None else pivot)
        if not math.isfinite(scale_factor):
            raise ValueError('Scale factor must be finite')
        about_point = self._pivot_3d(about_point, about_edge)
        if self._is_3d():
            # Baked 3D points cannot use the XY pose path; scale about the 3D pivot.
            pivot = self.get_center() if about_point is None else about_point
            return self._map_points_3d(lambda p: Vector(p) * scale_factor, pivot)
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

    def rotate_about_origin(self, angle, axis=OUT, **kwargs):
        return self.rotate(angle, axis=axis, about_point=ORIGIN, **kwargs)

    def rotate(self, angle, axis=OUT, *, about_point=None, about_edge=None):
        if not math.isfinite(angle):
            raise ValueError('Rotation angle must be finite')
        axis = Vector(axis)
        if not all(math.isfinite(v) for v in axis) or not any(axis):
            raise ValueError('Rotation axis must be finite and nonzero')
        if axis[0] or axis[1]:
            if (not axis[2] and abs(math.sin(angle)) < 1e-12 and math.cos(angle) < 0
                    and not self._is_3d()):
                # A half turn about an in-plane axis is the XY reflection across it.
                about_point = self._pivot(about_point, about_edge)
                length = math.hypot(axis[0], axis[1])
                ux, uy = axis[0] / length, axis[1] / length
                return self.apply_matrix([[2*ux*ux-1, 2*ux*uy], [2*ux*uy, 2*uy*uy-1]],
                                         about_point=self.get_center() if about_point is None else about_point)
            # A general 3D rotation: bake Rodrigues' formula into the points.
            if not angle % TAU:
                return self
            pivot = self._pivot_3d(about_point, about_edge)
            pivot = self.get_center() if pivot is None else pivot
            matrix = rotation_matrix(angle, axis)
            return self._map_points_3d(lambda p: _apply_rows(matrix, p), pivot)
        angle = angle if axis[2] > 0 else -angle
        if self._is_3d():
            # Pose rotation ignores z of children and cannot mix with baked 3D
            # points, so bake the rotation about z into the geometry.
            if not angle % TAU:
                return self
            pivot = self._pivot_3d(about_point, about_edge)
            pivot = self.get_center() if pivot is None else pivot
            matrix = rotation_about_z(angle)
            return self._map_points_3d(lambda p: _apply_rows(matrix, p), pivot)
        about_point = self._pivot(about_point, about_edge)
        if type(self) in (Group, VGroup, Mobject) and self._world_container():
            # Like shift and scale, a pure container turns its members about one pivot,
            # keeping their (Community) world coordinates.
            pivot = self.get_center() if about_point is None else Vector(about_point)
            for child in self.children:
                Mobject.rotate(child, angle, about_point=pivot)
            self.__dict__.pop('_family_pivot_cache', None)
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
        color = _paint(color)
        self.color = color
        self.fill_color = self.stroke_color = color
        if family:
            for child in self.children:
                child.set_color(color)
        return self

    def _opacity_channel(self, channel, opacity):
        """A scalar opacity, or a list drawn as Community's gradient of opacities. A list is
        kept as relative stop opacities (``<channel>_opacities``) under a scalar of 1."""
        if isinstance(opacity, (list, tuple)) or hasattr(opacity, 'tolist'):
            values = [float(v) for v in (opacity.tolist() if hasattr(opacity, 'tolist') else opacity)]
            if not values or len(values) > 64:
                raise ValueError('Opacity lists need 1 to 64 values')
            for value in values:
                self._validate_opacity(value)
            if len(values) == 1:
                self.__dict__.pop(channel + '_opacities', None)
                return values[0]
            self.__dict__[channel + '_opacities'] = values
            return 1
        self._validate_opacity(opacity)
        self.__dict__.pop(channel + '_opacities', None)
        return opacity

    def set_fill(self, color=None, opacity=None, family=True):
        raw = opacity
        if opacity is not None:
            opacity = self._opacity_channel('fill', opacity)
        color = _paint(color)
        if color is not None:
            self.fill_color = color
        if opacity is not None:
            self.fill_opacity = opacity
        if family:
            for child in self.children:
                child.set_fill(color, raw)
        return self

    def set_stroke(self, color=None, width=None, opacity=None, background=False, family=True):
        if background:
            return self.set_background_stroke(color, width, opacity, family=family)
        if width is not None:
            self._validate_width(width)
        raw = opacity
        if opacity is not None:
            opacity = self._opacity_channel('stroke', opacity)
        color = _paint(color)
        if color is not None:
            self.stroke_color = color
        if width is not None:
            self.stroke_width = width
        if opacity is not None:
            self.stroke_opacity = opacity
        if family:
            for child in self.children:
                child.set_stroke(color, width, raw)
        return self

    def set_opacity(self, opacity, family=True):
        self._validate_opacity(opacity)
        self.set_fill(opacity=opacity, family=family)
        self.set_stroke(opacity=opacity, family=family)
        return self

    def set_cap_style(self, cap_style):
        for member in self.get_family():
            member.cap_style = CapStyleType(cap_style)
        return self

    def set_joint_type(self, joint_type, family=True):
        for member in (self.get_family() if family else [self]):
            member.joint_type = LineJointType(joint_type)
        return self

    def get_cap_style(self):
        return self.cap_style

    def get_joint_type(self):
        return self.joint_type

    def set_sheen(self, factor, direction=None, family=True):
        """Community's sheen: each color gains a copy lightened by factor, as a gradient."""
        NumberLine._real(factor, 'Sheen factor')
        if direction is not None:
            direction = self._xy_vector(direction, 'Sheen direction')
        for member in (self.get_family() if family else [self]):
            member.sheen_factor = factor
            if direction is not None:
                member.sheen_direction = direction
        return self

    def get_sheen_factor(self):
        return self.sheen_factor

    def get_sheen_direction(self):
        return Vector(self.sheen_direction)

    def set_sheen_direction(self, direction, family=True):
        direction = self._xy_vector(direction, 'Sheen direction')
        for member in (self.get_family() if family else [self]):
            member.sheen_direction = direction
        return self

    def rotate_sheen_direction(self, angle, axis=OUT, family=True):
        if Vector(axis) not in (OUT, IN):
            raise NotImplementedError('Sheen directions rotate about OUT/IN only')
        angle = angle if Vector(axis) == OUT else -angle
        for member in (self.get_family() if family else [self]):
            x, y = member.sheen_direction[0], member.sheen_direction[1]
            member.sheen_direction = Vector((x * math.cos(angle) - y * math.sin(angle),
                                             x * math.sin(angle) + y * math.cos(angle), 0))
        return self

    def set_z_index(self, z_index_value, family=True):
        if not isinstance(z_index_value, _REAL) or not math.isfinite(z_index_value):
            raise ValueError('z_index must be a finite number')
        self.z_index = z_index_value
        if family:
            for child in self.children:
                child.set_z_index(z_index_value, family=True)
        return self

    def set_shade_in_3d(self, value=True, z_index_as_group=False):
        for member in self.get_family():
            member.shade_in_3d = value
            # Community stores the family root as z_index_group; the preview
            # records a flag and uses the root snapshot's center at capture.
            member._z_index_as_group = bool(z_index_as_group)
        return self

    def set_style(self, fill_color=None, fill_opacity=None, stroke_color=None, stroke_width=None,
                  stroke_opacity=None, family=True, **kwargs):
        unsupported = [key for key in kwargs if not key.startswith('background_stroke') and key not in ('sheen_factor', 'sheen_direction')]
        if unsupported:
            raise NotImplementedError('Unsupported style options: ' + ', '.join(unsupported))
        if kwargs.get('sheen_factor') is not None or kwargs.get('sheen_direction') is not None:
            self.set_sheen(self.sheen_factor if kwargs.get('sheen_factor') is None else kwargs['sheen_factor'],
                           kwargs.get('sheen_direction'), family=family)
        if any(kwargs.get(key) is not None for key in
               ('background_stroke_color', 'background_stroke_width', 'background_stroke_opacity')):
            self.set_background_stroke(kwargs.get('background_stroke_color'), kwargs.get('background_stroke_width'),
                                       kwargs.get('background_stroke_opacity'), family=family)
        self.set_fill(fill_color, fill_opacity, family=family)
        return self.set_stroke(stroke_color, stroke_width, stroke_opacity, family=family)

    def set_background_stroke(self, color=None, width=None, opacity=None, family=True, **kwargs):
        """Community's background stroke: drawn behind the fill (e.g. index labels, braces)."""
        color = kwargs.pop('stroke_color', color)
        width = kwargs.pop('stroke_width', width)
        opacity = kwargs.pop('stroke_opacity', opacity)
        if kwargs:
            raise NotImplementedError('Unsupported background stroke options: ' + ', '.join(kwargs))
        if width is not None:
            self._validate_width(width)
        if opacity is not None:
            self._validate_opacity(opacity)
        color = _paint(color)
        for member in (self.get_family() if family else [self]):
            if color is not None:
                member.background_stroke_color = color
            if width is not None:
                member.background_stroke_width = width
            if opacity is not None:
                member.background_stroke_opacity = opacity
        return self

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
        pivot = mobject._pivot_point()
        offset = pivot - Vector(self.position) - center
        c, s = math.cos(-self.angle), math.sin(-self.angle)
        local = center + Vector((offset[0]*c - offset[1]*s, offset[0]*s + offset[1]*c, 0)) * (1 / self.geometry_scale)
        # Turn about the pivot itself: a pure container's bounds center is not covariant.
        mobject.rotate(-self.angle, about_point=pivot).scale(1 / self.geometry_scale, about_point=pivot)
        return mobject.shift(local - pivot)

    def generate_target(self, use_deepcopy=False):
        self.target = None  # Do not copy an earlier target into the new one.
        self.target = self.copy()
        return self.target

    def add_background_rectangle(self, color=None, opacity=0.75, **kwargs):
        rectangle = BackgroundRectangle(self, color=color, fill_opacity=opacity, **kwargs)
        self.background_rectangle = rectangle
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

    @property
    def saved_state(self):
        """Community's saved_state: a copy of the checkpoint (None before save_state)."""
        if '_saved_state' not in self.__dict__:
            return None
        state = object.__new__(type(self))
        state.__dict__ = copy.deepcopy(self._saved_state)
        return state

    def restore(self):
        if '_saved_state' not in self.__dict__:
            raise ValueError('Call save_state() before restoring an object')
        # Community's become(saved_state): members keep their identities. Unlike
        # become, a checkpoint also restores a traced path's clock.
        self.become(self.saved_state)
        for key in ('dissipating_time', 'time'):
            if key in self._saved_state and 'traced_point_func' in self.__dict__:
                self.__dict__[key] = copy.deepcopy(self._saved_state[key])
        return self

    @property
    def animate(self):
        return Animate(self)

    @property
    def always(self):
        return _UpdaterBuilder(self)

    @property
    def points(self):
        """World-space points as an (n, 3) array (a NumPy array when NumPy is loaded).

        This is a copy: write back with ``mobject.points = array`` or set_points."""
        return _point_array(self._point_rows())

    @points.setter
    def points(self, value):
        self.set_points(value)

    def _point_rows(self):
        return [list(Vector(p)) for p in self.get_points()]

    set_default = classmethod(_set_default)

    def shuffle(self, recursive=False):
        if recursive:
            for child in self.children:
                child.shuffle(recursive=True)
        children = list(self.children)
        random.shuffle(children)
        self._replace_children(children)
        return self

    def shuffle_submobjects(self, *args, **kwargs):
        return self.shuffle(*args, **kwargs)

    def to_dict(self):
        global _BOUNDS_MEMO
        if _BOUNDS_MEMO is not None:
            return self._to_dict()
        # Nothing moves while a family serializes, so local bounds are computed once.
        _BOUNDS_MEMO = {}
        try:
            return self._to_dict()
        finally:
            _BOUNDS_MEMO = None

    def _to_dict(self):
        center = self._geometry_center()
        result = _snapshot_copy({key: value for key, value in self.__dict__.items()
                                if (key in _POINT_KEYS and type(value) is list or not _holds_mobject(value) and not callable(value)) and
                                key not in ('_saved_state', 'children', 'updaters', 'updating_suspended', '_sampled_geometry_center', 'traced_point_func', '_parametric_function', 'underlying_function', '_coordinate_labels', '_angle_lines', '_family_pivot_cache', '_flow_points') and
                                key not in self._frame_excluded})
        result['type'] = result.pop('_type')
        result['geometry_center'] = list(center)
        result['children'] = [child.to_dict() for child in self.children]
        if result['type'] in _GRADIENT_TYPES and (self.sheen_factor or isinstance(self.fill_color, list) or
                                                  isinstance(self.stroke_color, list) or 'fill_opacities' in result
                                                  or 'stroke_opacities' in result):
            self._gradient_paint(result)
        return _refresh_tip_shafts(result)

    def _gradient_paint(self, result):
        """Community's Cairo gradients: colors (plus their sheen-lightened copies) run
        from center - offset to center + offset, offset = half extents times the sheen direction."""
        if self.sheen_factor:
            def sheen(colors):
                colors = colors if isinstance(colors, list) else [colors]
                lit = [_rgb_color([min(1, max(0, v + self.sheen_factor)) for v in _color_rgb(c)]) for c in colors]
                return list(colors) + lit
            result['fill_color'], result['stroke_color'] = sheen(self.fill_color), sheen(self.stroke_color)
        if 'gradient_points' in result:
            return
        left, bottom, right, top = self._own_local_bounds()
        dx, dy = self.sheen_direction[0], self.sheen_direction[1]
        # The direction is a world direction; the gradient lives in the local frame.
        cos, sin = math.cos(-self.angle), math.sin(-self.angle)
        dx, dy = dx * cos - dy * sin, dx * sin + dy * cos
        if self.geometry_scale < 0:
            dx, dy = -dx, -dy
        ox, oy = (right - left) / 2 * dx, (top - bottom) / 2 * dy
        if ox or oy:
            cx, cy = (left + right) / 2, (bottom + top) / 2
            result['gradient_points'] = [[cx - ox, cy - oy], [cx + ox, cy + oy]]


def _point_array(rows):
    try:
        import numpy
    except ImportError:
        return rows
    return numpy.array(rows, dtype=float).reshape(len(rows), 3)


def _point_rows_of(points):
    rows = points.tolist() if hasattr(points, 'tolist') else [list(p) for p in points]
    if rows and isinstance(rows[0], _REAL):
        rows = [rows]
    return rows


class ValueTracker(Mobject):
    """An invisible finite real parameter, encoded in its x coordinate."""
    def _point_rows(self):
        return [[float(self.position[0]), 0.0, 0.0]]

    def set_points(self, points):
        return self.set_value(_point_rows_of(points)[0][0])

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

    @staticmethod
    def _aligned_point_lists(first, second):
        """World cubic points of two paths, the shorter subdivided to the longer's curve count."""
        a, b = [Vector(p) for p in first.get_points()], [Vector(p) for p in second.get_points()]
        if not a or not b:
            # Community grows an empty path from the other path's center.
            if not a and not b:
                return [], []
            if not a:
                a = [Vector(first.get_center())] * len(b)
            else:
                b = [Vector(second.get_center())] * len(a)
            return a, b
        def curves(points):
            whole = len(points) - len(points) % 4
            return [points[i:i + 4] for i in range(0, whole, 4)] or [[points[0]] * 4]
        ca, cb = curves(a), curves(b)
        if len(ca) < len(cb):
            ca = _subdivide_curves(ca, len(cb))
        elif len(cb) < len(ca):
            cb = _subdivide_curves(cb, len(ca))
        return [p for c in ca for p in c], [p for c in cb for p in c]

    def align_points(self, mobject):
        """Give both paths the same number of cubic curves (Community's align_points)."""
        if not isinstance(mobject, VMobject):
            raise TypeError('align_points expects a VMobject')
        a, b = self._aligned_point_lists(self, mobject)
        if a and len(a) != len(self.get_points()):
            self.set_points(a)
        if b and len(b) != len(mobject.get_points()):
            mobject.set_points(b)
        return self

    def interpolate(self, mobject1, mobject2, alpha, path_func=None):
        """Become the alpha-interpolation of two paths' points and styles."""
        if not isinstance(mobject1, Mobject) or not isinstance(mobject2, Mobject):
            raise TypeError('interpolate expects two mobjects')
        NumberLine._real(alpha, 'Interpolation alpha')
        a, b = self._aligned_point_lists(mobject1, mobject2)
        if path_func is None:
            points = [p + (q - p) * alpha for p, q in zip(a, b)]
        else:
            points = [Vector(p) for p in path_func(a, b, alpha)]
        self.set_points(points)
        self.interpolate_color(mobject1, mobject2, alpha)
        return self

    def interpolate_color(self, mobject1, mobject2, alpha):
        def first(color):
            return color[0] if isinstance(color, list) else color
        def mix(name):
            return interpolate_color(first(getattr(mobject1, name)), first(getattr(mobject2, name)), alpha)
        self.color, self.fill_color, self.stroke_color = mix('color'), mix('fill_color'), mix('stroke_color')
        for name in ('fill_opacity', 'stroke_opacity', 'stroke_width'):
            setattr(self, name, getattr(mobject1, name) * (1 - alpha) + getattr(mobject2, name) * alpha)
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
        discontinuities = sorted(set(NumberLine._numbers([] if discontinuities is None else discontinuities)))
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
            # np.arange fills start + i * ((start + step) - start), as Community samples.
            delta = (start+self.t_step)-start
            times = [start+i*delta for i in range(count) if start+i*delta < end]+[end]
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
        # Community orients each new tip along the path as already refit for the other tip.
        curves = (self._tip_shaft_curves('start' if at_start else 'end') if self.__dict__.get('_curved_tip_path')
                  else self._raw_curves())
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
        other = self._tip(not at_start)
        if other is not None and self.__dict__.get('_curved_tip_path'):
            # Community's reset_endpoints_based_on_tip runs put_start_and_end_on on the whole
            # family: the existing tip turns and scales about its own point with the path.
            fixed = Vector(other.tip_point)
            shaft = self._tip_shaft_curves(role)
            moving = Vector(shaft[0][0] if at_start else shaft[-1][-1])
            base = Vector(tip.base)
            current, target = complex(*(moving - fixed)[:2]), complex(*(base - fixed)[:2])
            if current and target:
                factor = target / current
                other.scale(abs(factor), about_point=fixed)
                other.rotate(cmath.phase(factor), about_point=fixed)
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
    def __init__(self, radius=1, start_angle=0, angle=PI / 2, arc_center=ORIGIN, num_components=9, **kwargs):
        if isinstance(num_components, bool) or not isinstance(num_components, numbers.Integral) or not 2 <= num_components <= 1000:
            raise ValueError('num_components must be an integer from 2 to 1000')
        center = Vector(arc_center)
        if not all(math.isfinite(v) for v in (radius, start_angle, angle, *center)) or radius < 0:
            raise ValueError('Arc geometry must be finite with a nonnegative radius')
        if abs(angle) > TAU:
            raise NotImplementedError('Arcs support at most one full turn')
        kwargs.setdefault('stroke_width',2)
        super().__init__(**kwargs)
        self._type, self.radius = 'arc', radius
        self.start_angle, self.arc_angle = start_angle % TAU, angle
        if num_components != 9:
            self.num_components = int(num_components)
        self.position = list(center)

    def get_arc_center(self):
        return self._point_to_world(ORIGIN)

    def move_arc_center_to(self, point):
        point = Vector(point)
        if not all(math.isfinite(v) for v in point):
            raise ValueError('Arc center must be finite')
        return self.shift(point - self.get_arc_center())


class Circle(Arc):
    def __init__(self, radius=1, color=RED, **kwargs):
        # Community's Circle (and Ellipse) default to RED.
        super().__init__(radius=1 if radius is None else radius, start_angle=0, angle=TAU, color=color, **kwargs)
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
        self._type = 'ellipse'
        self.__dict__.update(width=width, height=height)


class ArcBetweenPoints(Arc):
    """A circular XY arc spanning two endpoints, or a straight zero-angle path."""
    def __init__(self, start, end, angle=PI/2, radius=None, **kwargs):
        kwargs.setdefault('stroke_width',4)
        start,end = Line._endpoints(start,end)
        if start[2] or end[2]:
            raise NotImplementedError('Endpoint arcs support only the XY plane')
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
    def __init__(self, color=WHITE, height=2, width=4, grid_xstep=None, grid_ystep=None,
                 mark_paths_closed=True, close_new_points=True, **kwargs):
        super().__init__(color=color, **kwargs)
        self._type = 'rectangle'
        self.__dict__.update(width=width, height=height)
        # Community's optional internal grid: lines from the upper-left corner.
        self.grid_lines = VGroup()
        corner = Vector((-width / 2, height / 2, 0))
        for step, along, across, extent, span in ((grid_xstep, RIGHT, DOWN, width, height),
                                                  (grid_ystep, DOWN, RIGHT, height, width)):
            if step:
                NumberLine._real(step, 'Grid step')
                step = abs(step)
                count = int(extent / step)
                if count > 1001:
                    raise ValueError('A rectangle grid is limited to 1000 lines per direction')
                self.grid_lines.add(VGroup(*(Line(corner + along * (i * step), corner + along * (i * step) + across * span,
                                                  color=color) for i in range(1, count))))
        if self.grid_lines.children:
            self.add(self.grid_lines)


class Square(Rectangle):
    def __init__(self, side_length=2, **kwargs):
        super().__init__(width=side_length, height=side_length, **kwargs)
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
            # Community's round_corners: one cubic (components_per_rounded_corner=2) per corner.
            curves = _path_curves({'type':'arc', 'radius':cut, 'start_angle':angle, 'num_components':2,
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
            self.frame.__dict__['width'] = self.frame.height * self.pixel_width / self.pixel_height

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
    def __init__(self, start=LEFT, end=RIGHT, buff=0, path_arc=0, tip_length=.35, tip_style=None, **kwargs):
        NumberLine._real(path_arc, 'path_arc')
        start,end = self._endpoints(*self._resolve_ends(start,end))
        if path_arc:
            # Community: the points of ArcBetweenPoints, trimmed by buff along the arc.
            kwargs.setdefault('stroke_width',2)
            super().__init__(tip_length=tip_length,tip_style=tip_style,**kwargs)
            self._type = 'line'
            self.start, self.end, self.buff, self.path_arc = list(start), list(end), buff, path_arc
            self.set_points(ArcBetweenPoints(start, end, angle=path_arc).get_points())
            length = self.get_arc_length()
            if buff > 0 and length >= 2 * buff:
                self.pointwise_become_partial(self, buff / length, 1 - buff / length)
            return
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
            dx, dy, dz = point - center
            return [(dx * math.cos(self.angle) + dy * math.sin(self.angle)) / scale,
                    (-dx * math.sin(self.angle) + dy * math.cos(self.angle)) / scale, dz / scale]
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
_MATH_ESTIMATE_CACHE = {}


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


def _text_layout_key(snapshot):
    return (snapshot['text'], snapshot['font_size'], snapshot.get('line_spacing', .3), '_number_format' in snapshot,
            _is_mono(snapshot.get('font')), snapshot.get('_wrap_width'), bool(snapshot.get('justify')))


def _text_layout(snapshot):
    """Ink-centered line layout for a Text/DecimalNumber snapshot, in scene units."""
    key = _text_layout_key(snapshot)
    if key not in _TEXT_LAYOUTS:
        if len(_TEXT_LAYOUTS) > 4096:
            _TEXT_LAYOUTS.clear()
        _TEXT_LAYOUTS[key] = _compute_text_layout(*key)
    return copy.deepcopy(_TEXT_LAYOUTS[key])


def _text_extent(snapshot):
    layout = _TEXT_LAYOUTS.get(_text_layout_key(snapshot))
    if layout is None:
        layout = _text_layout(snapshot)
    return layout['width'], layout['height']


def _wrap_paragraph(paragraph, width, measure):
    """Pango's word wrapping: greedy lines broken after runs of spaces; a word wider
    than the layout stays whole. Returns (start, end) spans including trailing spaces."""
    spans, start, n = [], 0, len(paragraph)
    while True:
        end = None
        position = start
        while True:
            k = position
            while k < n and paragraph[k] != ' ':
                k += 1
            while k < n and paragraph[k] == ' ':
                k += 1
            if end is not None and measure(paragraph[start:k].rstrip(' ')) > width:
                break
            end = k
            if k >= n or measure(paragraph[start:k].rstrip(' ')) > width:
                break
            position = k
        spans.append((start, end))
        start = end
        if start >= n:
            return spans


def _compute_text_layout(text, font_size, line_spacing, numeric, mono=False, wrap=None, justify=False):
    import re
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
        table = _MONO_GLYPHS if mono else _SANS_GLYPHS
        def measure(chunk):
            return sum(_glyph_box(char, table)[0] for char in chunk) * em
        row, offset = 0, 0
        for paragraph in snapshot['text'].split('\n'):
            # MarkupText wraps at Community's Pango layout width; justify stretches the
            # spaces of every wrapped line but a paragraph's last to that width.
            spans = _wrap_paragraph(paragraph, wrap, measure) if wrap and paragraph else [(0, len(paragraph))]
            for number, (start, end) in enumerate(spans):
                line = paragraph[start:end].rstrip(' ') if wrap else paragraph[start:end]
                baseline = -row * pitch
                spaces = line.count(' ')
                extra = ((wrap - measure(line)) / spaces if justify and wrap and spaces and number < len(spans) - 1
                         else 0)
                words = [(0, line)] if not extra else [(m.start(), m.group()) for m in re.finditer(r'[^ ]+', line)]
                for at, word in words:
                    x = measure(line[:at]) / em + extra * line[:at].count(' ') / em
                    left = x
                    for char in word:
                        advance, x0, x1, y0, y1 = _glyph_box(char, table)
                        if x1 > x0 or y1 > y0:
                            merge(((x + x0) * em, baseline + y0 * em, (x + x1) * em, baseline + y1 * em))
                        x += advance
                    lines.append({'text': word, 'x': left * em, 'y': baseline, 'length': (x - left) * em,
                                  'start': offset + start + at})
                row += 1
            offset += len(paragraph) + 1
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
    body = re.sub(r'\\class\{manim-(?:part|sub)-\d+\}|\\kern\{[^}]*\}', '', text)
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
    key = (text, font_size)
    if key not in _MATH_ESTIMATE_CACHE:
        if len(_MATH_ESTIMATE_CACHE) > 4096:
            _MATH_ESTIMATE_CACHE.clear()
        _MATH_ESTIMATE_CACHE[key] = _math_estimate(text, font_size)
    return _MATH_ESTIMATE_CACHE[key]


def _math_parts(text, parts, font_size):
    """Centers and sizes of each \\class part relative to the formula's ink center."""
    em = font_size * TEX_EM_PER_POINT
    metric = _MATH_METRICS.get(text)
    if metric is not None and len(metric) >= 3 and metric[2] is not None and len(metric[2]) == len(parts):
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


_TEX_ZERO_GLYPH = {'left', 'right', 'displaystyle', 'textstyle', 'scriptstyle', 'scriptscriptstyle', 'quad',
                   'qquad', 'mathrm', 'mathbf', 'mathit', 'mathsf', 'mathtt', 'mathcal', 'mathbb', 'mathfrak',
                   'boldsymbol', 'operatorname', 'begin', 'end', 'limits', 'nolimits', 'class', 'color',
                   'hspace', 'vspace', 'phantom', 'hphantom', 'vphantom', 'text', 'textbf', 'textit', 'texttt',
                   'textrm', 'textsf', 'mbox', 'big', 'Big', 'bigg', 'Bigg', 'nonumber', 'notag', 'tag'}
_TEX_NAMED_FUNCTIONS = {'sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'log', 'ln', 'exp', 'lim', 'max', 'min',
                        'det', 'sinh', 'cosh', 'tanh', 'arcsin', 'arccos', 'arctan', 'gcd', 'deg', 'dim',
                        'ker', 'arg', 'sup', 'inf', 'Pr', 'hom', 'lg', 'liminf', 'limsup'}


def _estimate_glyph_count(tex, minimum=1):
    """How many glyph submobjects TeX would produce, until the browser counts MathJax's."""
    import re
    count = 0
    tex = re.sub(r'\\(?:begin|end)\{[^}]*\}(?:\{[^}]*\})?|\\class\{[^}]*\}|\\kern\{[^}]*\}', '', tex)
    for match in re.finditer(r'\\([A-Za-z]+)|\\(.)|([^\s{}^_&\\])', tex):
        name, symbol, char = match.groups()
        if name is not None:
            if name in _TEX_NAMED_FUNCTIONS:
                count += len(name)
            elif name in ('sqrt',):
                count += 2
            elif name in ('frac', 'dfrac', 'tfrac', 'overline', 'underline', 'cfrac'):
                count += 1
            elif name not in _TEX_ZERO_GLYPH:
                count += 1
        elif symbol is not None:
            if symbol not in ',;:! \\':
                count += 1
        else:
            count += 1
    # Delimiters after \left/\right were counted; a '.' there draws nothing.
    count -= len(re.findall(r'\\(?:left|right)\.', tex))
    return max(minimum, count)


def _math_glyphs(text, font_size, part_strings=None):
    """(cx, cy, w, h, part, sub) of every glyph relative to the formula's ink center, in scene
    units; sub is the isolated substring (\\class{manim-sub-k}) holding the glyph, or -1."""
    em = font_size * TEX_EM_PER_POINT
    metric = _MATH_METRICS.get(text)
    if metric is not None and len(metric) >= 4 and metric[3] is not None:
        return [(cx * em, cy * em, w * em, h * em, part, sub) for cx, cy, w, h, part, sub in metric[3]]
    _MATH_ESTIMATED.add(text)
    multi = bool(part_strings and len(part_strings) > 1)
    if multi:
        boxes = list(enumerate(_math_parts(text, part_strings, font_size)))
    else:
        width, height = _math_box(text, font_size)
        boxes = [(-1, (0, 0, width, height))]
    runs = _classed_runs(text)
    result = []
    for index, (cx, cy, width, height) in boxes:
        subs = [sub for part, sub, fragment in runs if part == index or not multi
                for _ in range(_estimate_glyph_count(fragment, 0))] or [-1]
        step = width / len(subs)
        for k, sub in enumerate(subs):
            result.append((cx - width / 2 + step * (k + .5), cy, step, height, index, sub))
    return result


class Text(Mobject):
    def __init__(self, text, font_size=48, line_spacing=-1, font='', slant=NORMAL, weight=NORMAL,
                 t2c=None, t2f=None, t2g=None, t2s=None, t2w=None, gradient=None, disable_ligatures=False,
                 height=None, width=None, **kwargs):
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
        if type(self) in (Text, MarkupText):
            self._fit_svg_size(height, width)

    def _fit_svg_size(self, height, width):
        """Community's SVGMobject sizing: scale to height, then to width (both uniform)."""
        if height is not None:
            self.scale_to_fit_height(NumberLine._real(height, 'height', positive=True))
        if width is not None:
            self.scale_to_fit_width(NumberLine._real(width, 'width', positive=True))
        return self

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
            index = line.get('start', index)
            for char in line['text']:
                advance, x0, x1, y0, y1 = _glyph_box(char, _glyph_table(self.__dict__.get('font')))
                if not char.isspace() and (x1 > x0 or y1 > y0):
                    glyph = Text(char, font_size=self.font_size, **options, **style)
                    (a, b), (c, d) = _glyph_matrix(self.__dict__)
                    cx, cy = x + (x0 + x1) / 2 * em, line['y'] + (y0 + y1) / 2 * em
                    center = Vector((a * cx + b * cy, c * cx + d * cy, 0))
                    glyph.position = list(self._point_to_world(center))
                    glyph.angle, glyph.geometry_scale, glyph.opacity = self.angle, self.geometry_scale, self.opacity
                    for key in ('glyph_stretch', 'glyph_matrix'):
                        if key in self.__dict__:
                            glyph.__dict__[key] = list(self.__dict__[key])
                    glyph._char_index = index
                    glyphs.append(glyph)
                x += advance * em
                index += 1
            index += 1  # the newline
        self.position, self.angle, self.geometry_scale, self.opacity = [0, 0, 0], 0, 1, 1
        self.__dict__.pop('glyph_stretch', None)
        self.__dict__.pop('glyph_matrix', None)
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
    """Pango-style markup for <b>, <i>, <span> colors/weights/styles and entities, plus
    Manim's <gradient> and <color> tags."""
    @staticmethod
    def _count_real_chars(text):
        """Community's count of displayed characters (no tags, spaces or tabs)."""
        import re
        count, level = 0, 0
        for char in re.sub('&[^;]+;', 'x', text):
            if char == '<':
                level += 1
            if char == '>' and level > 0:
                level -= 1
            elif char not in ' \t' and level == 0:
                count += 1
        return count

    @classmethod
    def _extract_manim_tags(cls, markup, tag, attributes):
        import re
        pattern = '<' + tag + ''.join(r'\s+' + name + '="([^"]+)"' for name in attributes) + \
                  r'(\s+offset="([^"]+)")?>(.+?)</' + tag + '>'
        found = []
        for match in re.finditer(pattern, markup, re.S):
            start = cls._count_real_chars(markup[:match.start(0)])
            end = start + cls._count_real_chars(match.group(len(attributes) + 3))
            offsets = match.group(len(attributes) + 2).split(',') if match.group(len(attributes) + 2) else ['0']
            start_offset = int(offsets[0]) if offsets[0] else 0
            end_offset = int(offsets[1]) if len(offsets) == 2 and offsets[1] else 0
            found.append((start - start_offset, end - start_offset - end_offset,
                          [match.group(i + 1) for i in range(len(attributes))]))
        markup = re.sub('<' + tag + '[^>]+>(.+?)</' + tag + '>', r'\1', markup, flags=re.S)
        return markup, found

    @staticmethod
    def _parse_color(value):
        if value.startswith('#'):
            return ManimColor(value)
        return ManimColor(_PALETTE.get(value.upper(), value))

    def __init__(self, text, justify=False, **kwargs):
        import re, html
        text, gradients = self._extract_manim_tags(str(text), 'gradient', ('from', 'to'))
        text, colors = self._extract_manim_tags(text, 'color', ('col',))
        self.justify = bool(justify)
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
        # Community lays markup out in a Pango box 500 px wide: 25 scene units at any size.
        self._wrap_width = 25.0
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
        if colors or gradients:
            # Community slices the displayed characters (spaces excluded).
            self._explode()
            chars = [glyph for glyph in self.children if glyph.text.strip()]
            for start, end, (color,) in colors:
                for glyph in chars[start:end]:
                    glyph.set_color(self._parse_color(color))
            for start, end, (first, last) in gradients:
                selected = chars[start:end]
                if selected:
                    VGroup(*selected).set_color_by_gradient(self._parse_color(first), self._parse_color(last))


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
    _frame_excluded = ('edge_to_fix',)

    def __init__(self, number=0, num_decimal_places=2, include_sign=False,
                 group_with_commas=True, show_ellipsis=False, unit=None, font_size=48,
                 digit_buff_per_font_unit=0.001, unit_buff_per_font_unit=0, edge_to_fix=LEFT, **kwargs):
        if (isinstance(num_decimal_places, bool) or not isinstance(num_decimal_places, numbers.Integral) or
                not 0 <= num_decimal_places <= 12):
            raise ValueError('num_decimal_places must be an integer from 0 to 12')
        if not all(isinstance(v, bool) for v in (include_sign, group_with_commas, show_ellipsis)):
            raise ValueError('Numeric formatting flags must be booleans')
        if unit is not None and (not isinstance(unit, str) or len(unit) > 256):
            raise ValueError('Numeric unit must be a string of at most 256 characters')
        if not isinstance(font_size, _REAL) or not math.isfinite(font_size) or font_size <= 0:
            raise ValueError('Numeric font size must be positive and finite')
        # Community typesets the unit as a separate TeX part after the digits.
        options = dict(num_decimal_places=num_decimal_places, include_sign=include_sign,
                       group_with_commas=group_with_commas, show_ellipsis=show_ellipsis, unit=None)
        super().__init__(_number_text(number, options), font_size=font_size, **kwargs)
        self.number, self._number_format, self.unit = number, options, unit
        self.edge_to_fix = Vector(edge_to_fix)
        self.digit_buff_per_font_unit = NumberLine._real(digit_buff_per_font_unit, 'digit_buff_per_font_unit')
        self.unit_buff_per_font_unit = NumberLine._real(unit_buff_per_font_unit, 'unit_buff_per_font_unit')
        if unit:
            sign = MathTex(unit, font_size=font_size, color=self.fill_color)
            sign._number_role = 'unit'
            self.add(sign)
            self._place_unit()
            # Community arranges digits and unit as one row centered where the number was.
            self.shift(Vector(self.position) - self.get_center())

    @property
    def unit_sign(self):
        return next((c for c in self.children if c.__dict__.get('_number_role') == 'unit'), None)

    def _place_unit(self):
        sign = self.unit_sign
        if sign is None:
            return
        width, height = _text_extent(self.__dict__)
        # Community's next_to buff: (unit_buff_per_font_unit + digit_buff_per_font_unit) * font_size.
        buff = (self.__dict__.get('unit_buff_per_font_unit', 0) +
                self.__dict__.get('digit_buff_per_font_unit', 0.001)) * self.font_size
        # Children of a shape live in its local frame, where the digits' ink is centered on 0.
        x = width / 2 + buff + sign.get_width() / 2
        y = (height - sign.get_height()) / 2 * (1 if self.unit.startswith('^') else -1)
        sign.move_to(Vector((x, y, 0)))

    def get_value(self):
        return self.number

    def set_value(self, number):
        # Community re-typesets the number and keeps its edge_to_fix (LEFT) in place.
        edge = self.__dict__.get('edge_to_fix', LEFT)
        anchor = self.get_edge_center(edge)
        text = _number_text(number, self._number_format)
        self.number, self.text = number, text
        self._place_unit()
        self.move_to(anchor, aligned_edge=edge)
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
_SUB_CLASS = '\\class{manim-sub-%d}{%s}'


def _split_double_braces(tex_string):
    """Community 0.22's {{ ... }} split: a group opens at the start or after whitespace and
    closes at a }} outside inner braces; \\, \\{ and \\} are atomic."""
    segments, current, i, inside, depth = [], '', 0, False, 0
    while i < len(tex_string):
        if tex_string[i] == '\\' and i + 1 < len(tex_string) and (tex_string[i + 1] == '\\' or tex_string[i + 1] in '{}'):
            current += tex_string[i:i + 2]
            i += 2
            continue
        if not inside:
            if tex_string[i:i + 2] == '{{' and (i == 0 or tex_string[i - 1].isspace()):
                segments.append(current)
                current, inside, depth = '', True, 0
                i += 2
            else:
                current += tex_string[i]
                i += 1
        elif tex_string[i] == '{':
            depth += 1
            current += '{'
            i += 1
        elif tex_string[i] == '}' and depth == 0 and tex_string[i:i + 2] == '}}':
            segments.append(current)
            current, inside = '', False
            i += 2
        else:
            depth -= tex_string[i] == '}'
            current += tex_string[i]
            i += 1
    segments.append(current)
    return segments


def _isolate_segments(string, isolate):
    """Community's _locate_first_match loop: the earliest match (longest on ties) is
    isolated, then matching continues on the rest. Returns (text, matched) pieces."""
    segments, rest = [], string
    while rest:
        best = None
        for sub in isolate:
            at = rest.find(sub)
            if at >= 0 and (best is None or at < best[0] or (at == best[0] and len(sub) > len(best[1]))):
                best = (at, sub)
        if best is None:
            segments.append((rest, False))
            break
        at, sub = best
        if at:
            segments.append((rest[:at], False))
        segments.append((sub, True))
        rest = rest[at + len(sub):]
    return segments


def _isolated_tex(pre, match, post, index):
    """Tag an isolated math substring with its class, or None where a TeX group there would
    change the formula (a split control word, unbalanced braces, alignment)."""
    import re
    depth, i = 0, 0
    while i < len(match):
        if match[i] == '\\':
            i += 2
            continue
        depth += {'{': 1, '}': -1}.get(match[i], 0)
        if depth < 0:
            return None
        i += 1
    if depth or '&' in match or not match.strip():
        return None
    if re.search(r'\\[A-Za-z]*$', pre) and (match[0].isalpha() or not re.search(r'\\[A-Za-z]+\s*$', pre)):
        return None
    if re.search(r'(?<!\\)(\\\\)*\\[A-Za-z]*$', match) and (post[:1].isalpha() or match.endswith('\\')):
        return None
    wrapped = _class_wrap(match, index, _SUB_CLASS)
    # A superscript, subscript or command argument takes a single token: brace the group.
    return '{' + wrapped + '}' if re.search(r'(?:[\^_]|\\[A-Za-z]+)\s*$', pre) else wrapped


def _classed_runs(text):
    """(part, sub, fragment) runs of a class-tagged expression, in source order."""
    import re
    runs, stack, depth, i, current = [], [], 0, 0, ''
    def state():
        part = next((n for kind, n, _ in reversed(stack) if kind == 'part'), -1)
        sub = next((n for kind, n, _ in reversed(stack) if kind == 'sub'), -1)
        return part, sub
    def flush():
        nonlocal current
        if current:
            runs.append(state() + (current,))
        current = ''
    while i < len(text):
        match = re.match(r'\\class\{manim-(part|sub)-(\d+)\}\{', text[i:])
        if match:
            flush()
            depth += 1
            stack.append((match.group(1), int(match.group(2)), depth))
            i += match.end()
            continue
        char = text[i]
        if char == '\\':
            current += text[i:i + 2]
            i += 2
            continue
        if char == '{':
            depth += 1
        elif char == '}':
            if stack and stack[-1][2] == depth:
                flush()
                stack.pop()
                depth -= 1
                i += 1
                continue
            depth -= 1
        current += char
        i += 1
    flush()
    return runs


def _reject_tex(value):
    raise TypeError('MathTex expects TeX strings or numbers')


def _class_wrap(piece, index, form=_PART_CLASS):
    """Tag a tex piece in place: braces and ^/_ stay structural, balanced runs get the class."""
    out, buffer, i = [], '', 0
    def flush():
        nonlocal buffer
        if buffer.strip():
            out.append(form % (index, buffer))
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
        if char == '&' or piece.startswith('\\\\', i):
            # Alignment points and row breaks belong to align*, outside any \class group.
            flush()
            step = 1 if char == '&' else 2
            out.append(piece[i:i + step])
            i += step
            continue
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
            out.append('{' + _class_wrap(inner, index, form) + '}')
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
    """One tex string of a multi-part MathTex (or, with index None, the only string of a
    single-string MathTex), drawn from the shared typeset formula. Indexing or iterating
    splits it into glyph submobjects, as Community's SingleStringMathTex."""
    def __init__(self, text, index, part_strings, font_size, **kwargs):
        super().__init__(text, font_size=font_size, **kwargs)
        self._type = 'mathtex'
        if index is not None:
            self.part, self.part_strings = index, list(part_strings)
            self.tex_string = part_strings[index]
        else:
            self.tex_string = text

    def get_tex_string(self):
        return self.tex_string

    def _explode(self):
        _explode_math(self)

    def __getitem__(self, value):
        self._explode()
        if isinstance(value, slice):
            return VGroup(*self.children[value])
        if (isinstance(value, numbers.Integral) and not -len(self.children) <= value < len(self.children)
                and self.text in _MATH_ESTIMATED):
            # Glyphs are counted once the browser has typeset the formula (second pass).
            return VMobject()
        return self.children[value]

    def __iter__(self):
        self._explode()
        return iter(list(self.children))

    def __len__(self):
        self._explode()
        return len(self.children)


class _MathTexGlyph(Text):
    """One glyph (or rule) of a typeset formula, Community's path submobject."""
    _frame_excluded = ('sub',)

    def __init__(self, text, glyph, font_size, part_strings=None, **kwargs):
        super().__init__(text, font_size=font_size, **kwargs)
        self._type, self.glyph = 'mathtex', glyph
        if part_strings:
            self.part_strings = list(part_strings)

    def _explode(self):
        pass


def _glyph_family(mobject):
    """Give text and formula leaves their glyph submobjects, as Community's families have:
    creation animations count and lag over glyphs."""
    if not isinstance(mobject, Mobject):
        return
    for member in list(mobject.get_family()):
        if (member._type == 'text' and isinstance(member, Text) and not isinstance(member, MathTex)
                and '_char_index' not in member.__dict__):
            member._explode()  # Glyphs themselves (with _char_index) stay leaves.
        elif member._type == 'mathtex' and 'glyph' not in member.__dict__:
            if isinstance(member, MathTex) and not isinstance(member, SingleStringMathTex):
                member._split_single()
                for part in member.children:
                    _explode_math(part)
            else:
                _explode_math(member)


def _explode_math(leaf):
    """Split a formula leaf (a whole single-string formula or one part) into glyph leaves
    placed by the browser-measured (or, before measurement, estimated) glyph boxes."""
    if leaf._type != 'mathtex' or 'glyph' in leaf.__dict__:
        return
    part_strings = leaf.__dict__.get('part_strings')
    glyphs = _math_glyphs(leaf.text, leaf.font_size, part_strings)
    if 'part' in leaf.__dict__:
        px, py = _math_parts(leaf.text, part_strings, leaf.font_size)[leaf.part][:2]
        members = [(i, g) for i, g in enumerate(glyphs) if g[4] == leaf.part]
    else:
        px = py = 0
        members = list(enumerate(glyphs))
    style = {key: leaf.__dict__[key] for key in ('color', 'fill_color', 'stroke_color', 'fill_opacity',
                                                'stroke_opacity', 'stroke_width', 'z_index')}
    (a, b), (c, d) = _glyph_matrix(leaf.__dict__)
    children = []
    for index, (cx, cy, _, _, _, sub) in members:
        x, y = cx - px, cy - py
        glyph = _MathTexGlyph(leaf.text, index, leaf.font_size, part_strings, **style)
        if sub >= 0:
            glyph.sub = sub
        glyph.position = list(leaf._point_to_world(Vector((a * x + b * y, c * x + d * y, 0))))
        glyph.angle, glyph.geometry_scale, glyph.opacity = leaf.angle, leaf.geometry_scale, leaf.opacity
        for key in ('glyph_stretch', 'glyph_matrix'):
            if key in leaf.__dict__:
                glyph.__dict__[key] = list(leaf.__dict__[key])
        children.append(glyph)
    # Existing members (e.g. background rectangles) keep their world placement.
    others = [leaf._world_member(child) for child in leaf.children]
    leaf.position, leaf.angle, leaf.geometry_scale, leaf.opacity = [0, 0, 0], 0, 1, 1
    for key in ('glyph_stretch', 'glyph_matrix', '_family_pivot_cache', '_sampled_geometry_center'):
        leaf.__dict__.pop(key, None)
    leaf.children, leaf._type = others + children, 'vgroup'


class TexTemplate:
    """Community's LaTeX template. The preview typesets with MathJax, so preambles,
    compilers and font packages are recorded but do not change the output."""
    def __init__(self, tex_compiler='latex', description='', output_format='.dvi', documentclass=None,
                 preamble=None, placeholder_text='YourTextHere', post_doc_commands='', **kwargs):
        self.tex_compiler, self.description, self.output_format = tex_compiler, description, output_format
        self.documentclass = documentclass or r'\documentclass[preview]{standalone}'
        self.preamble = preamble if preamble is not None else (
            '\\usepackage[english]{babel}\n\\usepackage{amsmath}\n\\usepackage{amssymb}')
        self.placeholder_text, self.post_doc_commands = placeholder_text, post_doc_commands
        for key, value in kwargs.items():
            setattr(self, key, value)

    def add_to_preamble(self, txt, prepend=False):
        self.preamble = (txt + '\n' + self.preamble) if prepend else (self.preamble + '\n' + txt)
        return self

    def add_to_document(self, txt):
        self.post_doc_commands += txt
        return self

    @property
    def body(self):
        return '\n'.join((self.documentclass, self.preamble, '\\begin{document}',
                           self.post_doc_commands, self.placeholder_text, '\\end{document}'))

    def get_texcode_for_expression(self, expression):
        return self.body.replace(self.placeholder_text, expression)

    def get_texcode_for_expression_in_env(self, expression, environment):
        begin, end = f'\\begin{{{environment}}}', f'\\end{{{environment}}}'
        return self.body.replace(self.placeholder_text, f'{begin}\n{expression}\n{end}')

    def copy(self):
        return copy.deepcopy(self)


class _TemplateNamespace:
    """Named templates (TexTemplateLibrary, TexFontTemplates); each is a plain TexTemplate."""
    def __init__(self, names):
        self._names = names

    def __getattr__(self, name):
        if name.startswith('_') or (self._names and name not in self._names):
            raise AttributeError(name)
        return TexTemplate(description=name)


TexTemplateLibrary = _TemplateNamespace(('default', 'threeb1b', 'ctex'))
TexFontTemplates = _TemplateNamespace(())


class MathTex(Text):
    """Formulas rendered as SVG paths by MathJax; several strings become parts."""
    def get_tex_string(self):
        return self.tex_string

    def __init__(self, *tex_strings, arg_separator=' ', substrings_to_isolate=None, tex_to_color_map=None,
                 font_size=48, tex_environment='align*', tex_template=None, height=None, width=None, **kwargs):
        # MathJax typesets in the browser; LaTeX templates (preamble, fonts) cannot apply.
        if tex_template is not None and not isinstance(tex_template, TexTemplate):
            raise TypeError('tex_template must be a TexTemplate')
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
        isolate = [s for s in list([] if substrings_to_isolate is None else substrings_to_isolate) + list(color_map) if s]
        # Community 0.22: parts are the strings (split at {{ }}); isolated substrings only
        # tag glyph groups for get_part_by_tex/set_color_by_tex, they never split parts.
        parts = [piece for string in tex_strings for piece in _split_double_braces(string) if piece] or ['']
        typeset, self._matched, sub = [], [], 0
        for index, part in enumerate(parts):
            self._matched.append((part, index, None))
            segments = _isolate_segments(part, isolate)
            for string, matched in segments:
                if matched:
                    self._matched.append((string, index, sub))
                    sub += 1
            typeset.append(self._typeset_part(segments, sub - sum(m for _, m in segments)))
        text = self._environment(arg_separator.join(typeset))
        if len(text) > 4096:
            raise ValueError('MathTex expressions are limited to 4096 characters')
        if len(parts) <= 1:
            super().__init__(text, font_size=font_size, **kwargs)
            self._type = 'mathtex'
            self.tex_string, self.tex_strings = arg_separator.join(parts), parts
        else:
            # Each part is tagged with \class so MathJax keeps TeX spacing while
            # the browser measures and draws every part separately.
            classed = self._environment(arg_separator.join(_class_wrap(piece, i) for i, piece in enumerate(typeset)))
            super().__init__(classed, font_size=font_size, **kwargs)
            self._type = 'vgroup'
            self.tex_string, self.tex_strings = arg_separator.join(parts), parts
            style = {key: kwargs[key] for key in kwargs
                     if key in ('color', 'fill_color', 'stroke_color', 'fill_opacity', 'stroke_width', 'stroke_opacity', 'z_index')}
            members = []
            for index, (cx, cy, _, _) in enumerate(_math_parts(classed, typeset, font_size)):
                member = _MathTexPart(classed, index, typeset, font_size, **style)
                member.tex_string = parts[index]
                members.append(member.move_to((cx, cy, 0)))
            self.add(*members)
        self.set_color_by_tex_to_color_map(color_map)
        self._fit_svg_size(height, width)

    def _typeset(self, string):
        return string

    # Community typesets MathTex in align*: LaTeX puts rows 1.5em apart (baselineskip plus
    # \jot), MathJax 1.3em.
    _ROWS = ('align*', '0.2em')

    def _environment(self, text):
        """Wrap rows (\\\\) and alignment points (&) outside other environments in this
        class's LaTeX environment, with LaTeX's row spacing."""
        out, depth, i, rows, align = [], 0, 0, False, False
        while i < len(text):
            if text.startswith('\\begin{', i):
                depth += 1
            elif text.startswith('\\end{', i):
                depth -= 1
            if text.startswith('\\\\', i):
                out.append(text[i:i + 2])
                i += 2
                if not depth:
                    rows = True
                    if not text.startswith('[', i):
                        out.append('[%s]' % self._ROWS[1])
                continue
            if text[i] == '\\':
                out.append(text[i:i + 2])
                i += 2
                continue
            if text[i] == '&' and not depth:
                align = True
            out.append(text[i])
            i += 1
        if not (rows or align):
            return text
        environment = 'align*' if align else self._ROWS[0]
        return '\\begin{%s}%s\\end{%s}' % (environment, ''.join(out), environment)

    def _typeset_part(self, segments, first_sub):
        """A part's TeX with each isolated substring tagged by \\class{manim-sub-k}."""
        try:
            out, sub = [], first_sub
            for i, (string, matched) in enumerate(segments):
                piece = self._typeset(string)
                if matched:
                    pre = ''.join(self._typeset(s) for s, _ in segments[:i])
                    post = ''.join(self._typeset(s) for s, _ in segments[i + 1:])
                    piece = _isolated_tex(pre, piece, post, sub) or piece
                    sub += 1
                out.append(piece)
            return ''.join(out)
        except (ValueError, NotImplementedError):
            # A substring that cannot be typeset on its own stays untagged.
            return self._typeset(''.join(string for string, _ in segments))

    def _parts(self):
        return list(self.children) if self._type == 'vgroup' else [self]

    def _split_single(self):
        """Community's MathTex holds its string as a part: give the formula that part."""
        if self._type != 'mathtex':
            return
        style = {key: self.__dict__[key] for key in ('color', 'fill_color', 'stroke_color', 'fill_opacity',
                                                    'stroke_opacity', 'stroke_width', 'z_index')}
        part = _MathTexPart(self.text, None, None, self.font_size, **style)
        part.tex_string = self.tex_string
        for key in ('position', 'angle', 'geometry_scale', 'opacity', 'glyph_stretch', 'glyph_matrix'):
            if key in self.__dict__:
                part.__dict__[key] = copy.deepcopy(self.__dict__[key])
        others = [self._world_member(child) for child in self.children]
        self.position, self.angle, self.geometry_scale, self.opacity = [0, 0, 0], 0, 1, 1
        for key in ('glyph_stretch', 'glyph_matrix', '_family_pivot_cache', '_sampled_geometry_center'):
            self.__dict__.pop(key, None)
        self.children, self._type = others + [part], 'vgroup'

    def __getitem__(self, value):
        self._split_single()
        return super().__getitem__(value)

    def __iter__(self):
        self._split_single()
        return iter(self._parts())

    def __len__(self):
        return len(self._parts())

    def get_parts_by_tex(self, tex, substring=True, case_sensitive=True):
        def matches(part):
            a, b = (tex, part.tex_string) if case_sensitive else (tex.lower(), part.tex_string.lower())
            return a in b if substring else a == b
        return VGroup(*[part for part in self._parts() if matches(part)]) if self._type == 'vgroup' else (
            [self] if matches(self) else [])

    def _matches(self, tex):
        """Community 0.22's id groups whose string equals tex exactly: whole parts and
        isolated substrings (the glyphs tagged with that substring)."""
        groups = []
        for string, index, sub in self.__dict__.get('_matched', ()):
            if string != tex:
                continue
            self._split_single()
            parts = [child for child in self.children if isinstance(child, _MathTexPart)]
            if index >= len(parts):
                continue
            if sub is None:
                groups.append(parts[index])
            else:
                _explode_math(parts[index])
                groups.append(VGroup(*[glyph for glyph in parts[index].children
                                       if glyph.__dict__.get('sub') == sub]))
        return groups

    def get_part_by_tex(self, tex, **kwargs):
        groups = self._matches(tex)
        return groups[0] if groups else None

    def index_of_part_by_tex(self, tex, **kwargs):
        part = self.get_part_by_tex(tex, **kwargs)
        return self._parts().index(part) if part in self._parts() else -1

    def set_color_by_tex(self, tex, color, **kwargs):
        for group in self._matches(tex):
            group.set_color(color)
        return self

    def set_color_by_tex_to_color_map(self, texs_to_color_map, **kwargs):
        for tex, color in texs_to_color_map.items():
            self.set_color_by_tex(tex, color, **kwargs)
        return self

    def set_opacity_by_tex(self, tex, opacity=0.5, remaining_opacity=None, **kwargs):
        if remaining_opacity is not None:
            self.set_opacity(remaining_opacity)
        for group in self._matches(tex):
            group.set_opacity(opacity)
        return self


class SingleStringMathTex(MathTex):
    """Community's single tex string: its submobjects are glyphs directly."""
    def __getitem__(self, value):
        if self._type == 'mathtex':
            _explode_math(self)
        return Group.__getitem__(self, value)

    def __iter__(self):
        if self._type == 'mathtex':
            _explode_math(self)
        return iter(list(self.children))

    def __len__(self):
        if self._type == 'mathtex':
            _explode_math(self)
        return len(self.children)


_TEX_FONT_COMMANDS = {'textbf': 'textbf', 'textit': 'textit', 'emph': 'textit', 'textsl': 'textit',
                      'texttt': 'texttt', 'textrm': 'textrm', 'textup': 'textrm', 'textnormal': 'text',
                      'textsf': 'textsf', 'text': 'text', 'mbox': 'text'}
_TEX_TEXT_SPACES = {' ', ',', ';', ':', '!', 'quad', 'qquad', 'enspace', 'thinspace', 'hfill', 'newline', '\\'}
_TEX_TEXT_SYMBOLS = {'_': '_', 'ldots': '\u2026', 'dots': '\u2026', 'textendash': '\u2013', 'textemdash': '\u2014',
                     'textquoteleft': '\u2018', 'textquoteright': '\u2019', 'textbullet': '\u2022',
                     'copyright': '\u00a9', 'S': '\u00a7', 'P': '\u00b6', 'textdegree': '\u00b0',
                     'LaTeX': 'LaTeX', 'TeX': 'TeX'}
_TEX_MATH_ESCAPES = {'%': '\\%', '&': '\\&', '#': '\\#', '$': '\\$', '{': '\\{', '}': '\\}'}


# Computer Modern text kerns and ligatures (OT1 codes) from the cmr10/cmbx10/cmti10/cmtt10/cmss10
# TFM files, so Tex text runs space like LaTeX: {font: (kerns "a,b:v ...", ligatures "a,b:c ...", widths)}.
_CM_TEXT_FONTS = {
    'cmr10': ('11,39:0.077779 11,63:0.077779 11,33:0.077779 11,41:0.077779 11,93:0.077779 32,108:-0.277779 32,76:-0.319446 39,63:0.111112 39,33:0.111112 65,116:-0.027779 65,67:-0.027779 65,79:-0.027779 65,71:-0.027779 65,85:-0.027779 65,81:-0.027779 65,84:-0.083334 65,89:-0.083334 65,86:-0.111112 65,87:-0.111112 68,88:-0.027779 68,87:-0.027779 68,65:-0.027779 68,86:-0.027779 68,89:-0.027779 70,111:-0.083334 70,101:-0.083334 70,117:-0.083334 70,114:-0.083334 70,97:-0.083334 70,65:-0.111112 70,79:-0.027779 70,67:-0.027779 70,71:-0.027779 70,81:-0.027779 73,73:0.027779 75,79:-0.027779 75,67:-0.027779 75,71:-0.027779 75,81:-0.027779 76,84:-0.083334 76,89:-0.083334 76,86:-0.111112 76,87:-0.111112 79,88:-0.027779 79,87:-0.027779 79,65:-0.027779 79,86:-0.027779 79,89:-0.027779 80,65:-0.083334 80,111:-0.027779 80,101:-0.027779 80,97:-0.027779 80,46:-0.083334 80,44:-0.083334 82,116:-0.027779 82,67:-0.027779 82,79:-0.027779 82,71:-0.027779 82,85:-0.027779 82,81:-0.027779 82,84:-0.083334 82,89:-0.083334 82,86:-0.111112 82,87:-0.111112 84,121:-0.027779 84,101:-0.083334 84,111:-0.083334 84,114:-0.083334 84,97:-0.083334 84,65:-0.083334 84,117:-0.083334 86,111:-0.083334 86,101:-0.083334 86,117:-0.083334 86,114:-0.083334 86,97:-0.083334 86,65:-0.111112 86,79:-0.027779 86,67:-0.027779 86,71:-0.027779 86,81:-0.027779 87,111:-0.083334 87,101:-0.083334 87,117:-0.083334 87,114:-0.083334 87,97:-0.083334 87,65:-0.111112 87,79:-0.027779 87,67:-0.027779 87,71:-0.027779 87,81:-0.027779 88,79:-0.027779 88,67:-0.027779 88,71:-0.027779 88,81:-0.027779 89,101:-0.083334 89,111:-0.083334 89,114:-0.083334 89,97:-0.083334 89,65:-0.083334 89,117:-0.083334 97,118:-0.027779 97,106:0.055555 97,121:-0.027779 97,119:-0.027779 98,101:0.027779 98,111:0.027779 98,120:-0.027779 98,100:0.027779 98,99:0.027779 98,113:0.027779 98,118:-0.027779 98,106:0.055555 98,121:-0.027779 98,119:-0.027779 99,104:-0.027779 99,107:-0.027779 102,39:0.077779 102,63:0.077779 102,33:0.077779 102,41:0.077779 102,93:0.077779 103,106:0.027779 104,116:-0.027779 104,117:-0.027779 104,98:-0.027779 104,121:-0.027779 104,118:-0.027779 104,119:-0.027779 107,97:-0.027779 107,101:-0.027779 107,111:-0.027779 107,99:-0.027779 109,116:-0.027779 109,117:-0.027779 109,98:-0.027779 109,121:-0.027779 109,118:-0.027779 109,119:-0.027779 110,116:-0.027779 110,117:-0.027779 110,98:-0.027779 110,121:-0.027779 110,118:-0.027779 110,119:-0.027779 111,101:0.027779 111,111:0.027779 111,120:-0.027779 111,100:0.027779 111,99:0.027779 111,113:0.027779 111,118:-0.027779 111,106:0.055555 111,121:-0.027779 111,119:-0.027779 112,101:0.027779 112,111:0.027779 112,120:-0.027779 112,100:0.027779 112,99:0.027779 112,113:0.027779 112,118:-0.027779 112,106:0.055555 112,121:-0.027779 112,119:-0.027779 116,121:-0.027779 116,119:-0.027779 117,119:-0.027779 118,97:-0.027779 118,101:-0.027779 118,111:-0.027779 118,99:-0.027779 119,101:-0.027779 119,97:-0.027779 119,111:-0.027779 119,99:-0.027779 121,111:-0.027779 121,101:-0.027779 121,97:-0.027779 121,46:-0.083334 121,44:-0.083334',
              '11,105:14 11,108:15 33,96:60 39,39:34 45,45:123 63,96:62 96,96:92 102,105:12 102,102:11 102,108:13 123,45:124',
              {11: 0.583336, 12: 0.555557, 13: 0.555557, 14: 0.833336, 15: 0.833336, 102: 0.305557, 105: 0.277779, 108: 0.277779}),
    'cmbx10': ('11,39:0.109027 11,63:0.109027 11,33:0.109027 11,41:0.109027 11,93:0.109027 32,108:-0.319443 32,76:-0.377777 39,63:0.127777 39,33:0.127777 65,116:-0.031944 65,67:-0.031944 65,79:-0.031944 65,71:-0.031944 65,85:-0.031944 65,81:-0.031944 65,84:-0.095833 65,89:-0.095833 65,86:-0.127777 65,87:-0.127777 68,88:-0.031944 68,87:-0.031944 68,65:-0.031944 68,86:-0.031944 68,89:-0.031944 70,111:-0.095833 70,101:-0.095833 70,117:-0.095833 70,114:-0.095833 70,97:-0.095833 70,65:-0.127777 70,79:-0.031944 70,67:-0.031944 70,71:-0.031944 70,81:-0.031944 73,73:0.031944 75,79:-0.031944 75,67:-0.031944 75,71:-0.031944 75,81:-0.031944 76,84:-0.095833 76,89:-0.095833 76,86:-0.127777 76,87:-0.127777 79,88:-0.031944 79,87:-0.031944 79,65:-0.031944 79,86:-0.031944 79,89:-0.031944 80,65:-0.095833 80,111:-0.031944 80,101:-0.031944 80,97:-0.031944 80,46:-0.095833 80,44:-0.095833 82,116:-0.031944 82,67:-0.031944 82,79:-0.031944 82,71:-0.031944 82,85:-0.031944 82,81:-0.031944 82,84:-0.095833 82,89:-0.095833 82,86:-0.127777 82,87:-0.127777 84,121:-0.031944 84,101:-0.095833 84,111:-0.095833 84,114:-0.095833 84,97:-0.095833 84,65:-0.095833 84,117:-0.095833 86,111:-0.095833 86,101:-0.095833 86,117:-0.095833 86,114:-0.095833 86,97:-0.095833 86,65:-0.127777 86,79:-0.031944 86,67:-0.031944 86,71:-0.031944 86,81:-0.031944 87,111:-0.095833 87,101:-0.095833 87,117:-0.095833 87,114:-0.095833 87,97:-0.095833 87,65:-0.127777 87,79:-0.031944 87,67:-0.031944 87,71:-0.031944 87,81:-0.031944 88,79:-0.031944 88,67:-0.031944 88,71:-0.031944 88,81:-0.031944 89,101:-0.095833 89,111:-0.095833 89,114:-0.095833 89,97:-0.095833 89,65:-0.095833 89,117:-0.095833 97,118:-0.031944 97,106:0.063889 97,121:-0.031944 97,119:-0.031944 98,101:0.031944 98,111:0.031944 98,120:-0.031944 98,100:0.031944 98,99:0.031944 98,113:0.031944 98,118:-0.031944 98,106:0.063889 98,121:-0.031944 98,119:-0.031944 99,104:-0.031944 99,107:-0.031944 102,39:0.109027 102,63:0.109027 102,33:0.109027 102,41:0.109027 102,93:0.109027 103,106:0.031944 104,116:-0.031944 104,117:-0.031944 104,98:-0.031944 104,121:-0.031944 104,118:-0.031944 104,119:-0.031944 107,97:-0.031944 107,101:-0.031944 107,111:-0.031944 107,99:-0.031944 109,116:-0.031944 109,117:-0.031944 109,98:-0.031944 109,121:-0.031944 109,118:-0.031944 109,119:-0.031944 110,116:-0.031944 110,117:-0.031944 110,98:-0.031944 110,121:-0.031944 110,118:-0.031944 110,119:-0.031944 111,101:0.031944 111,111:0.031944 111,120:-0.031944 111,100:0.031944 111,99:0.031944 111,113:0.031944 111,118:-0.031944 111,106:0.063889 111,121:-0.031944 111,119:-0.031944 112,101:0.031944 112,111:0.031944 112,120:-0.031944 112,100:0.031944 112,99:0.031944 112,113:0.031944 112,118:-0.031944 112,106:0.063889 112,121:-0.031944 112,119:-0.031944 116,121:-0.031944 116,119:-0.031944 117,119:-0.031944 118,97:-0.031944 118,101:-0.031944 118,111:-0.031944 118,99:-0.031944 119,101:-0.031944 119,97:-0.031944 119,111:-0.031944 119,99:-0.031944 121,111:-0.031944 121,101:-0.031944 121,97:-0.031944 121,46:-0.095833 121,44:-0.095833',
              '11,105:14 11,108:15 33,96:60 39,39:34 45,45:123 63,96:62 96,96:92 102,105:12 102,102:11 102,108:13 123,45:124',
              {11: 0.67083, 12: 0.638885, 13: 0.638885, 14: 0.958328, 15: 0.958328, 102: 0.351387, 105: 0.319443, 108: 0.319443}),
    'cmti10': ('11,39:0.104306 11,63:0.104306 11,33:0.104306 11,41:0.104306 11,93:0.104306 32,108:-0.255554 32,76:-0.320554 39,63:0.102221 39,33:0.102221 65,110:-0.025556 65,108:-0.025556 65,114:-0.025556 65,117:-0.025556 65,109:-0.025556 65,116:-0.025556 65,105:-0.025556 65,67:-0.025556 65,79:-0.025556 65,71:-0.025556 65,104:-0.025556 65,98:-0.025556 65,85:-0.025556 65,107:-0.025556 65,118:-0.025556 65,119:-0.025556 65,81:-0.025556 65,84:-0.076666 65,89:-0.076666 65,86:-0.102221 65,87:-0.102221 65,101:-0.051111 65,97:-0.051111 65,111:-0.051111 65,100:-0.051111 65,99:-0.051111 65,103:-0.051111 65,113:-0.051111 68,88:-0.025556 68,87:-0.025556 68,65:-0.025556 68,86:-0.025556 68,89:-0.025556 70,111:-0.076666 70,101:-0.076666 70,117:-0.076666 70,114:-0.076666 70,97:-0.076666 70,65:-0.102221 70,79:-0.025556 70,67:-0.025556 70,71:-0.025556 70,81:-0.025556 75,79:-0.025556 75,67:-0.025556 75,71:-0.025556 75,81:-0.025556 76,84:-0.076666 76,89:-0.076666 76,86:-0.102221 76,87:-0.102221 76,101:-0.051111 76,97:-0.051111 76,111:-0.051111 76,100:-0.051111 76,99:-0.051111 76,103:-0.051111 76,113:-0.051111 79,88:-0.025556 79,87:-0.025556 79,65:-0.025556 79,86:-0.025556 79,89:-0.025556 80,65:-0.076666 82,110:-0.025556 82,108:-0.025556 82,114:-0.025556 82,117:-0.025556 82,109:-0.025556 82,116:-0.025556 82,105:-0.025556 82,67:-0.025556 82,79:-0.025556 82,71:-0.025556 82,104:-0.025556 82,98:-0.025556 82,85:-0.025556 82,107:-0.025556 82,118:-0.025556 82,119:-0.025556 82,81:-0.025556 82,84:-0.076666 82,89:-0.076666 82,86:-0.102221 82,87:-0.102221 82,101:-0.051111 82,97:-0.051111 82,111:-0.051111 82,100:-0.051111 82,99:-0.051111 82,103:-0.051111 82,113:-0.051111 84,121:-0.076666 84,101:-0.076666 84,111:-0.076666 84,114:-0.076666 84,97:-0.076666 84,117:-0.076666 84,65:-0.076666 86,111:-0.076666 86,101:-0.076666 86,117:-0.076666 86,114:-0.076666 86,97:-0.076666 86,65:-0.102221 86,79:-0.025556 86,67:-0.025556 86,71:-0.025556 86,81:-0.025556 87,65:-0.076666 88,79:-0.025556 88,67:-0.025556 88,71:-0.025556 88,81:-0.025556 89,101:-0.076666 89,111:-0.076666 89,114:-0.076666 89,97:-0.076666 89,117:-0.076666 89,65:-0.076666 98,101:-0.051111 98,97:-0.051111 98,111:-0.051111 98,100:-0.051111 98,99:-0.051111 98,103:-0.051111 98,113:-0.051111 99,101:-0.051111 99,97:-0.051111 99,111:-0.051111 99,100:-0.051111 99,99:-0.051111 99,103:-0.051111 99,113:-0.051111 100,108:0.051111 101,101:-0.051111 101,97:-0.051111 101,111:-0.051111 101,100:-0.051111 101,99:-0.051111 101,103:-0.051111 101,113:-0.051111 102,39:0.104306 102,63:0.104306 102,33:0.104306 102,41:0.104306 102,93:0.104306 108,108:0.051111 110,39:-0.102221 111,101:-0.051111 111,97:-0.051111 111,111:-0.051111 111,100:-0.051111 111,99:-0.051111 111,103:-0.051111 111,113:-0.051111 112,101:-0.051111 112,97:-0.051111 112,111:-0.051111 112,100:-0.051111 112,99:-0.051111 112,103:-0.051111 112,113:-0.051111 114,101:-0.051111 114,97:-0.051111 114,111:-0.051111 114,100:-0.051111 114,99:-0.051111 114,103:-0.051111 114,113:-0.051111 119,108:0.051111',
              '11,105:14 11,108:15 33,96:60 39,39:34 45,45:123 63,96:62 96,96:92 102,105:12 102,102:11 102,108:13 123,45:124',
              {11: 0.61333, 12: 0.56222, 13: 0.587774, 14: 0.881662, 15: 0.89444, 102: 0.306665, 105: 0.306665, 108: 0.255554}),
    'cmtt10': ('',
              '33,96:14 63,96:15',
              {11: 0.524996, 12: 0.524996, 13: 0.524996, 14: 0.524996, 15: 0.524996, 102: 0.524996, 105: 0.524996, 108: 0.524996}),
    'cmss10': ('11,39:0.069445 11,63:0.069445 11,33:0.069445 11,41:0.069445 11,93:0.069445 32,108:-0.23889 32,76:-0.258336 39,63:0.111112 39,33:0.111112 65,116:-0.027779 65,67:-0.027779 65,79:-0.027779 65,71:-0.027779 65,85:-0.027779 65,81:-0.027779 65,84:-0.083334 65,89:-0.083334 65,86:-0.111112 65,87:-0.111112 68,88:-0.027779 68,87:-0.027779 68,65:-0.027779 68,86:-0.027779 68,89:-0.027779 70,111:-0.027779 70,101:-0.027779 70,117:-0.027779 70,114:-0.027779 70,97:-0.027779 70,65:-0.083334 70,79:-0.027779 70,67:-0.027779 70,71:-0.027779 70,81:-0.027779 73,73:0.027779 75,79:-0.027779 75,67:-0.027779 75,71:-0.027779 75,81:-0.027779 76,84:-0.083334 76,89:-0.083334 76,86:-0.111112 76,87:-0.111112 79,88:-0.027779 79,87:-0.027779 79,65:-0.027779 79,86:-0.027779 79,89:-0.027779 80,65:-0.083334 80,111:-0.027779 80,101:-0.027779 80,97:-0.027779 80,46:-0.083334 80,44:-0.083334 84,121:-0.083334 84,101:-0.083334 84,111:-0.083334 84,114:-0.083334 84,97:-0.083334 84,65:-0.083334 84,117:-0.083334 86,111:-0.027779 86,101:-0.027779 86,117:-0.027779 86,114:-0.027779 86,97:-0.027779 86,65:-0.083334 86,79:-0.027779 86,67:-0.027779 86,71:-0.027779 86,81:-0.027779 87,111:-0.027779 87,101:-0.027779 87,117:-0.027779 87,114:-0.027779 87,97:-0.027779 87,65:-0.083334 87,79:-0.027779 87,67:-0.027779 87,71:-0.027779 87,81:-0.027779 88,79:-0.027779 88,67:-0.027779 88,71:-0.027779 88,81:-0.027779 89,101:-0.083334 89,111:-0.083334 89,114:-0.083334 89,97:-0.083334 89,65:-0.083334 89,117:-0.083334 97,114:-0.027779 97,121:-0.027779 97,119:-0.027779 98,101:0.027779 98,111:0.027779 98,120:-0.027779 98,100:0.027779 98,99:0.027779 98,113:0.027779 98,114:-0.027779 98,121:-0.027779 98,119:-0.027779 102,39:0.069445 102,63:0.069445 102,33:0.069445 102,41:0.069445 102,93:0.069445 103,106:0.027779 107,101:-0.027779 107,97:-0.027779 107,111:-0.027779 107,99:-0.027779 111,101:0.027779 111,111:0.027779 111,120:-0.027779 111,100:0.027779 111,99:0.027779 111,113:0.027779 111,114:-0.027779 111,121:-0.027779 111,119:-0.027779 112,101:0.027779 112,111:0.027779 112,120:-0.027779 112,100:0.027779 112,99:0.027779 112,113:0.027779 112,114:-0.027779 112,121:-0.027779 112,119:-0.027779 116,121:-0.027779 116,119:-0.027779 117,119:-0.027779 119,101:-0.027779 119,97:-0.027779 119,111:-0.027779 119,99:-0.027779 121,111:-0.027779 121,101:-0.027779 121,97:-0.027779 121,46:-0.083334 121,44:-0.083334',
              '11,105:14 11,108:15 33,96:60 39,39:34 45,45:123 63,96:62 96,96:92 102,105:12 102,102:11 102,108:13 123,45:124',
              {11: 0.583336, 12: 0.536113, 13: 0.536113, 14: 0.813891, 15: 0.813891, 102: 0.305557, 105: 0.23889, 108: 0.23889}),
}
# Interword space and extra space after sentence punctuation (TFM params 2 and 7), in em.
_CM_TEXT_SPACE = {'cmr10': (0.333334, 0.111112), 'cmbx10': (0.383331, 0.127777), 'cmti10': (0.357776, 0.102221),
                  'cmtt10': (0.524996, 0.524996), 'cmss10': (0.333334, 0.111112)}
# LaTeX's \nonfrenchspacing space factors (uppercase letters are 999; ) ] ' keep the previous one).
_TEX_SPACE_FACTORS = {'.': 3000, '?': 3000, '!': 3000, ':': 2000, ';': 1500, ',': 1250, ')': 0, ']': 0, "'": 0}
_CM_FONT_FOR = {'text': 'cmr10', 'textrm': 'cmr10', 'textbf': 'cmbx10', 'textit': 'cmti10', 'texttt': 'cmtt10',
                'textsf': 'cmss10'}
# OT1 positions whose glyphs differ from ASCII (LaTeX prints these for the typed characters).
_OT1_OUTPUT = {34: '”', 39: '’', 96: '‘', 92: '“', 60: '¡', 62: '¿', 123: '–', 124: '—'}
_OT1_LIGATURE_PARTS = {11: (102, 102), 12: (102, 105), 13: (102, 108), 14: (102, 102, 105), 15: (102, 102, 108)}
_CM_TEXT_TABLES = {}


def _cm_text_table(font):
    if font not in _CM_TEXT_TABLES:
        kerns, ligs, widths = _CM_TEXT_FONTS[font]
        def pairs(spec, convert):
            return {tuple(int(v) for v in key.split(',')): convert(value)
                    for key, value in (item.split(':') for item in spec.split())}
        _CM_TEXT_TABLES[font] = (pairs(kerns, float), pairs(ligs, int), widths)
    return _CM_TEXT_TABLES[font]


def _kerned_text(font, value):
    """A text run as MathJax \\text pieces with LaTeX's Computer Modern kerns and ligatures.
    MathJax has no ligature glyphs, so a ligature keeps its letters, kerned to its width."""
    name = _CM_FONT_FOR.get(font)
    if name is None:
        return '\\' + font + '{' + value + '}'
    kerns, ligs, widths = _cm_text_table(name)
    space, extra = _CM_TEXT_SPACE[name]
    codes = [ord(c) if 33 <= ord(c) <= 126 else None for c in value]
    items, i, factor = [], 0, 1000
    while i < len(codes):
        code = codes[i]
        if value[i] == ' ':
            # TeX's interword glue (MathJax's \text space is narrower); runs of spaces are one.
            while i < len(codes) and value[i] == ' ':
                i += 1
            items.append(space + (extra if factor >= 2000 else 0))
            factor = 1000
            continue
        char = value[i]
        sf = 999 if char.isupper() else _TEX_SPACE_FACTORS.get(char, 1000)
        if sf:
            factor = 1000 if sf > 1000 and factor == 999 else sf
        if code is None:
            items.append(value[i])
            i += 1
            continue
        while i + 1 < len(codes) and codes[i + 1] is not None and (code, codes[i + 1]) in ligs:
            code = ligs[(code, codes[i + 1])]
            i += 1
        following = codes[i + 1] if i + 1 < len(codes) else None
        if code in _OT1_LIGATURE_PARTS:
            parts = _OT1_LIGATURE_PARTS[code]
            gap = (widths[code] - sum(widths[p] for p in parts)) / (len(parts) - 1)
            for k, part in enumerate(parts):
                items.append(chr(part))
                if k < len(parts) - 1:
                    items.append(gap)
        else:
            items.append(_OT1_OUTPUT.get(code, chr(code)))
        if following is not None and (code, following) in kerns:
            items.append(kerns[(code, following)])
        i += 1
    out, run, gap = [], '', 0
    for item in items + ['']:
        if not isinstance(item, str):
            gap += item
            continue
        if gap and not item:
            pass
        elif gap:
            if run:
                out.append('\\' + font + '{' + run + '}')
                run = ''
            out.append('\\kern{%gem}' % round(gap, 6))
            gap = 0
        run += item
    if gap:
        if run:
            out.append('\\' + font + '{' + run + '}')
            run = ''
        out.append('\\kern{%gem}' % round(gap, 6))
    if run:
        out.append('\\' + font + '{' + run + '}')
    return ''.join(out)


def _tex_text_to_math(text):
    """Typeset LaTeX text mode with MathJax: text runs become \\text{...} (or font commands),
    $math$ stays math, {groups} and Manim's {{ }} parts merge, and TeX specials are escaped."""
    import re
    segments, i, n = [], 0, len(text)

    def add_text(font, value):
        if segments and segments[-1][0] == 'text' and segments[-1][1] == font:
            segments[-1] = ('text', font, segments[-1][2] + value)
        else:
            segments.append(('text', font, value))

    def parse(font, closing):
        nonlocal i
        while i < n:
            char = text[i]
            if char == '}':
                i += 1
                if closing:
                    return
                raise NotImplementedError('Tex supports text, $math$ and basic font commands in this preview')
            if char == '{':
                i += 1
                parse(font, True)
                continue
            if char == '$':
                double = text.startswith('$$', i)
                i += 2 if double else 1
                start = i
                while i < n and not (text[i] == '$' and text[i - 1] != '\\'):
                    i += 1
                if i >= n:
                    raise ValueError('Unbalanced $ in Tex string')
                segments.append(('math', None, text[start:i]))
                i += 2 if double and text.startswith('$$', i) else 1
                continue
            if char == '\\':
                match = re.match(r'\\([A-Za-z]+)\s*|\\(.)', text[i:], re.S)
                if not match:
                    raise NotImplementedError('Tex supports text, $math$ and basic font commands in this preview')
                name = match.group(1) or match.group(2)
                i += match.end()
                if name in _TEX_FONT_COMMANDS:
                    if i < n and text[i] == '{':
                        i += 1
                        parse(_TEX_FONT_COMMANDS[name], True)
                    continue
                if name in ('\\', 'newline'):
                    segments.append(('math', None, '\\\\'))  # A line break: a row of the environment.
                    continue
                if name in _TEX_TEXT_SPACES:
                    add_text(font, ' ')
                    continue
                if name in _TEX_MATH_ESCAPES:
                    segments.append(('math', None, _TEX_MATH_ESCAPES[name]))
                    continue
                if name in ('LaTeX', 'TeX'):
                    # LaTeX's own logo definitions (MathJax's are wider): a 7pt A raised to the
                    # T's height (cmr7 is wider than scaled cmr10) and E lowered half an ex.
                    f = '\\' + font
                    logo = (f'{f}{{T}}\\kern{{-0.1667em}}\\lower{{0.2153em}}{{{f}{{E}}}}'
                            f'\\kern{{-0.125em}}{f}{{X}}')
                    if name == 'LaTeX':
                        logo = (f'{f}{{L}}\\kern{{-0.36em}}\\raise{{0.2049em}}{{\\scriptsize{f}{{A}}}}'
                                f'\\kern{{-0.0847em}}' + logo)
                    segments.append(('math', None, logo))
                    if i < n and text[i] == '{' and text.startswith('{}', i):
                        i += 2
                    continue
                if name in ('_', 'textunderscore'):
                    # LaTeX's OT1 underscore: a 0.06em kern and a 0.3em rule on the baseline.
                    segments.append(('math', None, '\\kern{0.06em}\\rule{0.3em}{0.04em}'))
                    continue
                if name in _TEX_TEXT_SYMBOLS:
                    add_text(font, _TEX_TEXT_SYMBOLS[name])
                    continue
                if name.isalpha() and not (i < n and text[i] == '{'):
                    # Argument-free commands (\LaTeX, \TeX, symbols) are typeset by MathJax.
                    segments.append(('math', None, '\\' + name + ' '))
                    continue
                raise NotImplementedError('Tex supports text, $math$ and basic font commands in this preview')
            if char == '~':
                add_text(font, ' ')
            elif char in _TEX_MATH_ESCAPES:
                segments.append(('math', None, _TEX_MATH_ESCAPES[char]))
            elif char != '%':
                add_text(font, char)
            else:
                # A TeX comment runs to the end of the line.
                while i < n and text[i] != '\n':
                    i += 1
                continue
            i += 1

    parse('text', False)
    # TeX drops spaces before a line break (\\unskip) and at the start of a line.
    for index, (kind, font, value) in enumerate(segments):
        if kind == 'math' and value == '\\\\':
            if index and segments[index - 1][0] == 'text':
                segments[index - 1] = ('text', segments[index - 1][1], segments[index - 1][2].rstrip(' '))
            if index + 1 < len(segments) and segments[index + 1][0] == 'text':
                segments[index + 1] = ('text', segments[index + 1][1], segments[index + 1][2].lstrip(' '))
    result = []
    for kind, font, value in segments:
        if kind == 'math':
            result.append(value)
        elif value:
            result.append(_kerned_text(font, value))
    return ''.join(result)


class Tex(MathTex):
    """LaTeX text mode (with $math$), typeset by MathJax as \\text runs."""
    def __init__(self, *tex_strings, arg_separator='', tex_environment='center', font_size=48, **kwargs):
        if tex_environment not in ('center', None):
            raise NotImplementedError('Tex environments other than center are not supported')
        if not all(isinstance(value, str) for value in (*tex_strings, arg_separator)):
            raise TypeError('Tex expects LaTeX strings')
        super().__init__(*tex_strings, arg_separator=arg_separator, font_size=font_size, **kwargs)

    # Text lines in Community's center environment are a baselineskip (1.2em) apart.
    _ROWS = ('gather*', '-0.1em')

    def _typeset(self, string):
        return _tex_text_to_math(string)



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
    def add(self, *mobjects):
        # Community unpacks non-Mobject iterables (lists, generators) of members.
        members = []
        for index, item in enumerate(mobjects):
            if isinstance(item, Mobject):
                members.append(item)
            elif isinstance(item, (str, bytes)) or not hasattr(item, '__iter__'):
                raise TypeError(f'Only Mobjects can be added to a VGroup, but the value {item!r} '
                                f'(at index {index}) is of type {type(item).__name__}.')
            else:
                for inner, member in enumerate(item):
                    if not isinstance(member, Mobject):
                        raise TypeError(f'Only Mobjects can be added to a VGroup, but the value {member!r} '
                                        f'(at index {inner} of parameter {index}) is of type {type(member).__name__}.')
                    members.append(member)
        return super().add(*members)

    def __add__(self, mobject):
        return VGroup(*self.children, mobject)

    def __iadd__(self, mobject):
        return self.add(mobject)

    def __sub__(self, mobject):
        result = VGroup(*self.children)
        result.remove(mobject)
        return result

    def __isub__(self, mobject):
        return self.remove(mobject)

    def __setitem__(self, key, value):
        children = list(self.children)
        children[key] = value
        self.submobjects = children


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
    def set_color_by_tex(self, tex, color, **kwargs):
        # Community's items are Tex parts that include their bullet.
        for row in self.children:
            if tex in row[1].tex_string:
                row.set_color(color)
        return self

    def __init__(self, *items, buff=MED_LARGE_BUFF, dot_scale_factor=2, tex_environment=None,
                 height=None, width=None, **kwargs):
        super().__init__()
        texts = [Tex(item, **kwargs) for item in items]
        if (height is not None or width is not None) and texts:
            # Community sizes the whole Tex (items stacked) before adding the bullets.
            stacked = VGroup(*(text.copy() for text in texts)).arrange(DOWN, aligned_edge=LEFT, buff=buff)
            factor = 1
            if height is not None:
                factor = NumberLine._real(height, 'height', positive=True) / stacked.get_height()
            if width is not None:
                factor = NumberLine._real(width, 'width', positive=True) / (stacked.get_width() * factor) * factor
            for text in texts:
                text.scale(factor)
        for text in texts:
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

    def coordinate_label(self, integer_labels=True, n_dim=2, color=None, **kwargs):
        """A column Matrix of the end coordinates beside the tip, as in Community."""
        end = list(self.get_end())
        values = [int(round(v)) if integer_labels else v for v in end][:n_dim]
        label = Matrix([[value] for value in values], **kwargs)
        label.scale(LARGE_BUFF - 0.2)
        if end[0] >= 0:
            shift = Vector(end) - (Vector(label.get_left()) + DEFAULT_MOBJECT_TO_MOBJECT_BUFFER * LEFT)
        else:
            shift = Vector(end) - (Vector(label.get_right()) + DEFAULT_MOBJECT_TO_MOBJECT_BUFFER * RIGHT)
        label.shift(shift)
        if color is not None:
            label.set_color(color)
        return label


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
        self.add(self.label)


class LabeledArrow(LabeledLine, Arrow):
    pass


class LabeledDot(Dot):
    """A dot sized to hold a MathTex (or given) label at its center."""
    def __init__(self, label, radius=None, buff=SMALL_BUFF, **kwargs):
        rendered = MathTex(label, color=BLACK) if isinstance(label, str) else label
        if not isinstance(rendered, Mobject):
            raise TypeError('LabeledDot label must be a string or Mobject')
        if radius is None:
            # Manim 0.22: the label's half diagonal plus buff.
            radius = buff + math.hypot(rendered.get_width(), rendered.get_height()) / 2
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


class _ScaleBase:
    def __init__(self, custom_labels=False):
        self.custom_labels = custom_labels

    def function(self, value):
        raise NotImplementedError

    def inverse_function(self, value):
        raise NotImplementedError

    def get_custom_labels(self, val_range, **kwargs):
        raise NotImplementedError


class LinearBase(_ScaleBase):
    """Linear axis scaling: displayed values are scale_factor times positions."""
    def __init__(self, scale_factor=1.0):
        super().__init__()
        self.scale_factor = scale_factor

    def function(self, value):
        return self.scale_factor * value

    def inverse_function(self, value):
        return value / self.scale_factor


class LogBase(_ScaleBase):
    """Logarithmic axis scaling: positions are exponents, labeled base^k by default."""
    def __init__(self, base=10, custom_labels=True):
        super().__init__()
        NumberLine._real(base, 'LogBase base', positive=True)
        self.base, self.custom_labels = base, custom_labels

    def function(self, value):
        return self.base ** value

    def inverse_function(self, value):
        if value <= 0:
            raise ValueError('log(0) is undefined. Make sure the value is in the domain of the function')
        return math.log(value, self.base)

    def get_custom_labels(self, val_range, unit_decimal_places=0, **base_config):
        return [Integer(self.base, unit='^{%s}' % f'{self.inverse_function(i):.{unit_decimal_places}f}', **base_config)
                for i in val_range]


class NumberLine(VGroup):
    """Linear XY coordinates, composed from a shaft, ticks and numeric labels."""
    def __init__(self, x_range=None, length=None, unit_size=1, include_ticks=True,
                 tick_size=.1, numbers_with_elongated_ticks=None, longer_tick_multiple=2,
                 exclude_origin_tick=False, rotation=0, include_tip=False,
                 tip_width=.35, tip_height=.35, include_numbers=False, font_size=36,
                 label_direction=DOWN, line_to_number_buff=.25,
                 decimal_number_config=None, numbers_to_exclude=None,
                 numbers_to_include=None, label_constructor=None, scaling=None, tip_shape=None, **kwargs):
        self.scaling = LinearBase() if scaling is None else scaling
        if not isinstance(self.scaling, _ScaleBase):
            raise TypeError('NumberLine scaling must be LinearBase, LogBase or another _ScaleBase')
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
        # NumPy arrays (np.arange) are common here, so test for None, not truthiness.
        self.numbers_with_elongated_ticks = self._numbers([] if numbers_with_elongated_ticks is None
                                                          else numbers_with_elongated_ticks)
        self.numbers_to_exclude = self._numbers([] if numbers_to_exclude is None else numbers_to_exclude)
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
        if include_tip and tip_shape is not None and tip_shape is not ArrowTriangleFilledTip:
            # Community's add_tip(tip_shape=...): the shape at the end, stroked like the line.
            if not (isinstance(tip_shape, type) and issubclass(tip_shape, ArrowTip)):
                raise TypeError('tip_shape must be an ArrowTip class')
            tip = tip_shape(length=tip_height, fill_color=self.stroke_color, stroke_color=self.stroke_color)
            tip.set_stroke(self.stroke_color, self.stroke_width)
            shaft._orient_tip(tip, False)
            tip._number_line_role = 'tip'
            self.add(tip)
        elif include_tip:
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
            if self.scaling.custom_labels:
                ticks = self.get_tick_range()
                labels = self.scaling.get_custom_labels(ticks, unit_decimal_places=self.decimal_number_config.get('num_decimal_places', 0))
                self.add_labels(dict(zip(ticks, labels)))
            else:
                self.add_numbers(self.numbers_to_include)

    _frame_excluded = ('scaling',)

    @staticmethod
    def _real(value, name, positive=False, nonnegative=False):
        if (isinstance(value,bool) or not isinstance(value,_REAL) or not math.isfinite(value)
                or positive and value <= 0 or nonnegative and value < 0):
            raise ValueError(name + ' must be a finite real value' + (' greater than zero' if positive else ''))
        return value

    @classmethod
    def _numbers(cls, values):
        result = values.tolist() if hasattr(values, 'tolist') else list(values)
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
        number = self._real(self.scaling.inverse_function(number),'NumberLine value')
        result = self.get_start()+self.get_vector()*((number-self.x_min)/(self.x_max-self.x_min))
        if not all(math.isfinite(v) for v in result):
            raise ValueError('NumberLine coordinates must be finite')
        return result

    n2p = number_to_point

    def rotate_about_number(self, number, angle, axis=OUT, **kwargs):
        return self.rotate(angle, axis, about_point=self.n2p(number), **kwargs)

    def rotate_about_zero(self, angle, axis=OUT, **kwargs):
        return self.rotate_about_number(0, angle, axis, **kwargs)

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
        return self._real(self.scaling.function(self.x_min+alpha*(self.x_max-self.x_min)),'NumberLine result')

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
        return [self.scaling.function(value) for value in values if
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
        # New geometry is positioned in world coordinates; add() re-poses it into this
        # parent's frame and common family insertion preserves the bounding-box pivot.
        if self.geometry_scale == 0:
            raise ValueError('Cannot add decorations to a collapsed NumberLine')
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
        size = self.font_size if font_size is None else font_size
        number = DecimalNumber(x,font_size=size,**options).next_to(self.n2p(x),direction=direction,buff=buff)
        if x < 0 and self.label_direction[0] == 0 and number.text.startswith('-'):
            # Community aligns negative labels without their minus sign.
            _, x0, x1, _, _ = _CM_GLYPHS['-']
            number.shift(LEFT*((x1-x0)/1000*size*TEX_EM_PER_POINT/2))
        return number

    def add_labels(self, dict_values, direction=None, buff=None, font_size=None, label_constructor=None):
        """Place given labels (strings or mobjects) at numbers, as Community's add_labels."""
        direction = self._direction(self.label_direction if direction is None else direction)
        buff = self.line_to_number_buff if buff is None else buff
        constructor = self.label_constructor if label_constructor is None else label_constructor
        labels = []
        for x, label in dict(dict_values).items():
            if isinstance(label, str):
                label = constructor(label, font_size=self.font_size if font_size is None else font_size)
            elif not isinstance(label, Mobject):
                raise TypeError('NumberLine labels must be strings or Mobjects')
            labels.append(label.next_to(self.n2p(x), direction=direction, buff=buff))
        return self._add_world_decoration(VGroup(*labels), 'labels')

    @property
    def labels(self):
        return self._part('labels')

    @labels.setter
    def labels(self, group):
        # Community stores the label group; lite tags it so the child lookup finds it.
        group._number_line_role = 'labels'

    def add_numbers(self, x_values=None, excluding=None, font_size=None, **kwargs):
        values = self.get_tick_range() if x_values is None else self._numbers(x_values)
        excluding = self.numbers_to_exclude if excluding is None else self._numbers(excluding)
        labels = VGroup(*(self.get_number_mobject(value,font_size=font_size,**kwargs)
                          for value in values if value not in excluding))
        return self._add_world_decoration(labels,'numbers')


class CoordinateSystem:
    """Marker base for Axes-like coordinate systems (Community's CoordinateSystem)."""


class Axes(VGroup, CoordinateSystem):
    """Two linear NumberLines with transform-aware XY coordinate conversion."""
    _frame_excluded = ('axis_config',)
    def __init__(self, x_range=None, y_range=None, x_length=None, y_length=None,
                 axis_config=None, x_axis_config=None, y_axis_config=None, tips=True, **kwargs):
        if not isinstance(tips,bool):
            raise ValueError('Axes tips must be a boolean')
        super().__init__(**kwargs)
        common = dict(color=self.color,stroke_color=self.stroke_color,
                      stroke_width=self.stroke_width,stroke_opacity=self.stroke_opacity,
                      include_tip=tips,numbers_to_exclude=[0],exclude_origin_tick=True)
        merge = self._merge_axis_options
        common = merge(common,axis_config)
        self.axis_config = common
        x_options = merge(common,x_axis_config)
        y_options = merge(merge(common,dict(rotation=PI/2,label_direction=LEFT)),y_axis_config)
        for options in (x_options, y_options):
            # Community keeps the origin tick on scaled (e.g. LogBase) axes.
            options['exclude_origin_tick'] = isinstance(options.get('scaling') or LinearBase(), LinearBase)
        if y_range is None:
            radius = max(1,round(config.frame_height/2))
            y_range = [-radius,radius,1]
        x_options['length'] = max(1,round(config.frame_width)-2) if x_length is None else x_length
        y_options['length'] = max(1,round(config.frame_height)-2) if y_length is None else y_length
        x_axis = NumberLine(x_range,**x_options)
        y_axis = NumberLine(y_range,**y_options)
        for axis, role in ((x_axis,'x'),(y_axis,'y')):
            # Community shifts by the scaled range (LogBase ranges are exponents).
            scaled = [axis.scaling.function(axis.x_min), axis.scaling.function(axis.x_max)]
            axis.shift(axis.n2p(self._origin_shift(scaled))*(-1))
            axis._axes_role = role
        self.add(x_axis,y_axis)
        self.x_range,self.y_range = x_axis.x_range[:],y_axis.x_range[:]
        self.num_sampled_graph_points_per_tick = 10
        # Center the coordinate rectangle, including ranges which exclude zero.
        middle = self.c2p(x_axis.scaling.function((x_axis.x_min+x_axis.x_max)/2),
                          y_axis.scaling.function((y_axis.x_min+y_axis.x_max)/2))
        self.shift(middle*(-1))

    @staticmethod
    def _merge_axis_options(base, options):
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

    _AXIS_ROLES = ('x', 'y')

    def _coordinate_axes(self):
        # During construction the later axes may not exist yet.
        result = []
        for role in self._AXIS_ROLES:
            axis = next((child for child in self.children
                         if child.__dict__.get('_axes_role') == role), None)
            if axis is None:
                break
            result.append(axis)
        if len(result) < 2:
            raise ValueError('Axes has no x and y axes')
        return result

    @property
    def axes(self):
        return VGroup(*self._coordinate_axes())

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
            raise ValueError('Axes coordinates need x, y and optionally z')
        sequences = [value for value in coords if isinstance(value,(list,tuple))]
        if sequences:
            count = len(sequences[0])
            if count > 1000 or any(len(value) != count for value in sequences):
                raise ValueError('Axes coordinate arrays need equal lengths of at most 1000')
            return [self.coords_to_point(*(value[i] if isinstance(value,(list,tuple)) else value
                                          for value in coords)) for i in range(count)]
        for value in coords:
            NumberLine._real(value,'Axes coordinate')
        # Community sums each axis's offset from the origin; coordinates beyond
        # the axis count (z on 2D Axes) are ignored.
        axes = self._coordinate_axes()
        origin = axes[0].n2p(self._axis_shift(axes[0]))
        point = axes[0].n2p(coords[0])
        for axis, value in zip(axes[1:], coords[1:]):
            point = point + axis.n2p(value) - origin
        return self._point_to_world(point)

    def _axis_shift(self, axis):
        """Community's origin shift, taken over the axis's scaled range."""
        return self._origin_shift([axis.scaling.function(axis.x_min), axis.scaling.function(axis.x_max)])

    c2p = coords_to_point

    def get_origin(self):
        return self.c2p(0,0)

    def _basis(self):
        # Query the nested NumberLines in Axes-local space, then apply this parent.
        origin = self.x_axis.n2p(self._axis_shift(self.x_axis))
        world = self._point_to_world(origin)
        vectors = [self._point_to_world(origin+axis.get_unit_vector())-world
                   for axis in self._coordinate_axes()]
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
        # Solve in the axes' raw (position) coordinates, then apply each axis scaling.
        shifts = [self._axis_shift(self.x_axis), self._axis_shift(self.y_axis)]
        raw = [axis.scaling.inverse_function(value) for axis, value in zip((self.x_axis, self.y_axis), shifts)]
        offset = point-self.c2p(*shifts)
        result = [raw[0]+(offset[0]*y[1]-offset[1]*y[0])/determinant/lx,
                  raw[1]+(x[0]*offset[1]-x[1]*offset[0])/determinant/ly]
        result = [axis.scaling.function(value) for axis, value in zip((self.x_axis, self.y_axis), result)]
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

    def _get_axis_label(self, label, axis, edge, direction, buff=SMALL_BUFF):
        """Community's _get_axis_label: next to the axis edge, then onto the screen."""
        label = label if isinstance(label,Mobject) else MathTex(str(label))
        label.next_to(self._point_to_world(axis.get_edge_center(edge)),direction,buff)
        label.shift_onto_screen(buff=MED_SMALL_BUFF)
        return label

    def get_x_axis_label(self, label, edge=UR, direction=UR, buff=SMALL_BUFF):
        return self._get_axis_label(label,self.x_axis,edge,direction,buff)

    def get_y_axis_label(self, label, edge=UR, direction=UP*.5+RIGHT, buff=SMALL_BUFF):
        return self._get_axis_label(label,self.y_axis,edge,direction,buff)

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

    def get_z_axis(self):
        return self.get_axis(2)

    @staticmethod
    def _create_label_tex(label, constructor=None, **kwargs):
        if isinstance(label, Mobject):
            return label
        return (MathTex if constructor is None else constructor)(str(label), **kwargs)

    def get_graph_label(self, graph, label='f(x)', x_val=None, direction=RIGHT, buff=MED_SMALL_BUFF,
                        color=None, dot=False, dot_config=None):
        """Community's graph label: beside the graph at x_val, or its last on-screen point."""
        color = graph.get_color() if color is None else color
        label_object = self._create_label_tex(label).set_color(color)
        if x_val is None:
            # Search from right to left, as Community does.
            low, high = self.x_range[0], self.x_range[1]
            for index in range(100):
                x = high + (low - high) * index / 99
                point = self.input_to_graph_point(x, graph)
                if point[1] < config.frame_y_radius:
                    break
        else:
            point = self.input_to_graph_point(x_val, graph)
        label_object.next_to(point, direction, buff=buff)
        label_object.shift_onto_screen()
        if dot:
            marker = Dot(point=point, **(dot_config or {}))
            label_object.add(marker)
            label_object.dot = marker
        return label_object

    def get_vertical_lines_to_graph(self, graph, x_range=None, num_lines=20, **kwargs):
        x_range = self.x_range if x_range is None else list(x_range)
        if isinstance(num_lines, bool) or not isinstance(num_lines, numbers.Integral) or not 0 <= num_lines <= 1000:
            raise ValueError('num_lines must be an integer from 0 to 1000')
        values = [x_range[0] + (x_range[1] - x_range[0]) * (i / (num_lines - 1) if num_lines > 1 else 0)
                  for i in range(num_lines)]
        return VGroup(*(self.get_vertical_line(self.i2gp(x, graph), **kwargs) for x in values))

    def get_T_label(self, x_val, graph, label=None, label_color=None, triangle_size=MED_SMALL_BUFF,
                    triangle_color=WHITE, line_func=Line, line_color=PURE_YELLOW):
        group = VGroup()
        triangle = RegularPolygon(n=3, start_angle=PI / 2, stroke_width=0).set_fill(color=triangle_color, opacity=1)
        triangle.height = triangle_size
        triangle.move_to(self.coords_to_point(x_val, 0), UP)
        if label is not None:
            options = {} if label_color is None else {'color': label_color}
            group.add(self._create_label_tex(label, **options).next_to(triangle, DOWN))
        line = self.get_vertical_line(self.i2gp(x_val, graph), color=line_color, line_func=line_func)
        return group.add(triangle, line)

    def plot_implicit_curve(self, func, min_depth=5, max_quads=1500, **kwargs):
        if not callable(func):
            raise TypeError('plot_implicit_curve expects func(x, y)')
        x_scale, y_scale = self.get_x_axis().scaling, self.get_y_axis().scaling
        graph = ImplicitFunction(lambda x, y: func(x_scale.function(x), y_scale.function(y)),
                                 x_range=self.x_range[:2], y_range=self.y_range[:2],
                                 min_depth=min_depth, max_quads=max_quads, **kwargs)
        graph.stretch(self.get_x_unit_size(), 0, about_point=ORIGIN).stretch(self.get_y_unit_size(), 1, about_point=ORIGIN)
        return graph.shift(self.get_origin())

    def plot_polar_graph(self, r_func, theta_range=None, **kwargs):
        if not callable(r_func):
            raise TypeError('plot_polar_graph expects r(theta)')
        theta_range = [0, TAU] if theta_range is None else theta_range
        graph = ParametricFunction(lambda theta: self.pr2pt(r_func(theta), theta), t_range=theta_range, **kwargs)
        graph.underlying_function = r_func
        return graph

    def plot_line_graph(self, x_values, y_values, z_values=None, line_color=PURE_YELLOW, add_vertex_dots=True,
                        vertex_dot_radius=DEFAULT_DOT_RADIUS, vertex_dot_style=None, **kwargs):
        xs = list(x_values.tolist() if hasattr(x_values, 'tolist') else x_values)
        ys = list(y_values.tolist() if hasattr(y_values, 'tolist') else y_values)
        zs = [0] * len(xs) if z_values is None else list(z_values.tolist() if hasattr(z_values, 'tolist') else z_values)
        if not len(xs) == len(ys) == len(zs):
            raise ValueError('plot_line_graph needs equally many x, y (and z) values')
        if len(xs) > 10000:
            raise ValueError('plot_line_graph is limited to 10000 vertices')
        vertices = [self.coords_to_point(x, y, z) if z else self.coords_to_point(x, y) for x, y, z in zip(xs, ys, zs)]
        line_graph = VDict()
        graph = VMobject(color=line_color, **kwargs)
        graph.set_points_as_corners(vertices)
        line_graph['line_graph'] = graph
        if add_vertex_dots:
            style = vertex_dot_style or {}
            line_graph['vertex_dots'] = VGroup(*(Dot(point=vertex, radius=vertex_dot_radius, **style) for vertex in vertices))
        return line_graph

    def plot(self, function, x_range=None, use_vectorized=False, **kwargs):
        if not callable(function):
            raise TypeError('Axes.plot expects a scalar function')
        values = self.x_range[:] if x_range is None else list(x_range)
        density = NumberLine._real(self.num_sampled_graph_points_per_tick,'Plot samples per tick',positive=True)
        step = self.x_range[2]/density
        if x_range is None:
            values[2] = step
        values = ParametricFunction._range(values,step)
        scale = self.x_axis.scaling
        if isinstance(scale,LinearBase):
            point = lambda t: self.c2p(t,function(t))
        else:
            # Community samples scaled plots at scaling.function(t) over the raw range.
            point = lambda t: self.c2p(scale.function(t),function(scale.function(t)))
        graph = ParametricFunction(point,t_range=values,use_vectorized=use_vectorized,**kwargs)
        graph.underlying_function = function
        return graph

    def plot_parametric_curve(self, function, **kwargs):
        if not callable(function):
            raise TypeError('Parametric plotting expects a callable returning XY coordinates')
        dim = len(self._AXIS_ROLES)
        return ParametricFunction(lambda t: self.c2p(*list(function(t))[:dim]),**kwargs)

    def plot_surface(self, function, u_range=None, v_range=None, colorscale=None,
                     colorscale_axis=2, **kwargs):
        """Community's plot_surface: a Surface over (u, v) with height function(u, v)."""
        if not callable(function):
            raise TypeError('plot_surface expects a callable height function')
        options = dict(kwargs)
        if u_range is not None:
            options['u_range'] = u_range
        if v_range is not None:
            options['v_range'] = v_range
        surface = Surface(lambda u, v: self.c2p(u, v, function(u, v)), **options)
        if colorscale:
            surface.set_fill_by_value(axes=self.copy(), colorscale=colorscale, axis=colorscale_axis)
        return surface

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

    def prepare_for_nonlinear_transform(self, num_inserted_curves=50):
        """Give every path at least num_inserted_curves cubic pieces before warping."""
        for mobject in self.family_members_with_points():
            count = mobject.get_num_curves()
            if num_inserted_curves > count:
                mobject.insert_n_curves(num_inserted_curves - count)
        return self

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

    def prepare_for_nonlinear_transform(self, num_inserted_curves=50):
        """Give every path at least num_inserted_curves cubic pieces before warping."""
        for mobject in self.family_members_with_points():
            count = mobject.get_num_curves()
            if num_inserted_curves > count:
                mobject.insert_n_curves(num_inserted_curves - count)
        return self

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
        # add() re-poses the world-placed labels into this plane's frame.
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
# In Community's module order (code that iterates rate_functions.__dict__ sees the same order).
rate_functions = types.SimpleNamespace(sigmoid=sigmoid, unit_interval=_unit_interval, zero=_zero,
                                       **{name: globals()[name] for name in (
    'linear', 'smooth', 'smoothstep', 'smootherstep', 'smoothererstep', 'rush_into', 'rush_from',
    'slow_into', 'double_smooth', 'there_and_back', 'there_and_back_with_pause', 'running_start',
    'not_quite_there', 'wiggle', 'squish_rate_func', 'lingering', 'exponential_decay',
    *_ease_functions())})


_FAST_NUMBERS = (int, float)


def interpolate(start, end, alpha):
    kind = type(start)
    if kind in _FAST_NUMBERS and type(end) in _FAST_NUMBERS:
        return start + (end - start) * alpha
    if kind is list and type(end) is list and len(start) == len(end):
        # Coordinate lists dominate morphs; keep their numbers on a fast path.
        return [a + (b - a) * alpha if type(a) in _FAST_NUMBERS and type(b) in _FAST_NUMBERS
                else interpolate(a, b, alpha) for a, b in zip(start, end)]
    if kind is str and type(end) is str and not (start.startswith('#') and end.startswith('#')):
        return end if alpha >= 1 else start
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
        # Community's Arc: num_components anchors (default 9, so 8 cubics) for any sweep.
        count = snapshot.get('num_components', 9) - 1
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
    start,target = _snapshot_copy(start),_snapshot_copy(target)
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
        aligned = _snapshot_copy(snapshot)
        aligned['type'] = 'bezierpath'
        aligned['curves'] = [curve for path, count in zip(paths, counts)
                             for curve in _subdivide_curves(path, count)]
        aligned['vertices'] = []
        aligned['subpath_lengths'] = counts[:]
        # Keep the original pivot. Subdivision changes control-point bounds but
        # must not move a previously scaled/rotated curve at either endpoint.
        result.append(aligned)
    return tuple(result)


def _pose_turns(start, target):
    """Whether two snapshots differ in rotation (or reflection), which Community
    interpolates point by point rather than as a rigid turn."""
    a, b = start.get('angle', 0), target.get('angle', 0)
    sa, sb = start.get('geometry_scale', 1), target.get('geometry_scale', 1)
    return abs(a - b) > 1e-9 or (sa < 0) != (sb < 0)


def _lerp_pose(result, start, target, alpha):
    """Community's straight_path moves every point linearly. Between two similarity
    poses of the same local geometry that is again a similarity: the complex factor
    scale * e^(i angle) and the image of the local origin interpolate linearly."""
    def factor(node):
        return cmath.rect(node.get('geometry_scale', 1), node.get('angle', 0))
    def origin(node, z):
        p, c = node['position'], node.get('geometry_center', ORIGIN)
        return complex(p[0] + c[0], p[1] + c[1]) - z * complex(c[0], c[1])
    z0, z1 = factor(start), factor(target)
    z = z0 + (z1 - z0) * alpha
    offset = origin(start, z0) + (origin(target, z1) - origin(start, z0)) * alpha
    c = result.get('geometry_center', ORIGIN)
    moved = offset - complex(c[0], c[1]) + z * complex(c[0], c[1])
    result['position'] = [moved.real, moved.imag, result['position'][2]]
    result['geometry_scale'], result['angle'] = abs(z), (cmath.phase(z) if z else 0.0)


def _transform_plan(start, target):
    """Align immutable family snapshots once, before sampling their timeline."""
    if start['type'] == 'vgroup' or target['type'] == 'vgroup':
        def as_group(snapshot):
            if snapshot['type'] == 'vgroup':
                return _snapshot_copy(snapshot)
            group = VGroup().to_dict()
            group['children'] = [_snapshot_copy(snapshot)]
            return group
        start, target = as_group(start), as_group(target)
        count = max(len(start['children']), len(target['children']))
        def expand(children, other):
            if not children:
                # An empty family grows/shrinks at each corresponding child's
                # own center, without moving the containing group's pivot.
                result = _snapshot_copy(other)
                for child in result:
                    child['opacity'] = 0
                    child['geometry_scale'] = 0
                return result
            result, seen = [], set()
            for index in range(count):
                source_index = index * len(children) // count
                child = _snapshot_copy(children[source_index])
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
        own_start,own_target = _snapshot_copy(start),_snapshot_copy(target)
        own_start['children'],own_target['children'] = [],[]
        first,last = VGroup().to_dict(),VGroup().to_dict()
        first['children'],last['children'] = start['children'],target['children']
        if start.get('_arc_polygon_outline') or target.get('_arc_polygon_outline'):
            def outline(snapshot):
                source = Mobject()
                source.__dict__.update(_snapshot_copy(snapshot))
                source._type = snapshot['type']
                source.children = []
                source._sampled_geometry_center = Vector(snapshot['geometry_center'])
                points = source.get_points()
                result = _snapshot_copy(snapshot)
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


def _plan_members(plan):
    """Painted members of an aligned plan, in Community's family order."""
    kind, _, _, children = plan
    if kind == 'family':
        return _plan_members(children[0]) + _plan_members(children[1])
    if kind == 'group':
        return sum((_plan_members(child) for child in children), 0)
    return 1


def _sample_transform(plan, alpha, path_arc=0, member_alpha=None):
    """Sample a plan; member_alpha() supplies successive lagged member alphas."""
    kind, start, target, children = plan
    if kind == 'family':
        own = _sample_transform(children[0],alpha,path_arc,member_alpha)
        members = _sample_transform(children[1],alpha,path_arc,member_alpha)[0]['children']
        own[0]['children'] = members
        return own
    if member_alpha is not None and kind != 'group':
        alpha = member_alpha()
    if kind == 'fade':
        first, last = _snapshot_copy(start), _snapshot_copy(target)
        first['opacity'] *= 1 - alpha
        last['opacity'] *= alpha
        return [first, last]
    result = interpolate(start, target, alpha)
    if _pose_turns(start, target) and 'position' in result:
        _lerp_pose(result, start, target, alpha)
    if kind == 'group':
        result['children'] = [snapshot for child in children
                              for snapshot in _sample_transform(child, alpha, path_arc, member_alpha)]
    elif (isinstance(path_arc, _PointPath) or abs(path_arc) >= STRAIGHT_PATH_THRESHOLD) and 0 < alpha < 1:
        _arc_geometry(result, start, target, alpha, path_arc)
    return [result]


STRAIGHT_PATH_THRESHOLD = 0.01


def _snapshot_pose(node):
    """Local-to-parent map of a snapshot's pose and, when invertible, its inverse."""
    px, py, pz = node['position']
    gx, gy, gz = node.get('geometry_center', ORIGIN)
    scale, angle = node['geometry_scale'], node['angle']
    c, s = scale * math.cos(angle), scale * math.sin(angle)
    forward = lambda p: [px + gx + c * (p[0] - gx) - s * (p[1] - gy),
                         py + gy + s * (p[0] - gx) + c * (p[1] - gy),
                         pz + gz + (p[2] - gz) * scale]
    if not scale:
        return forward, None
    d = scale * scale
    inverse = lambda p: [gx + (c * (p[0] - px - gx) + s * (p[1] - py - gy)) / d,
                         gy + (-s * (p[0] - px - gx) + c * (p[1] - py - gy)) / d,
                         gz + (p[2] - pz - gz) / scale]
    return forward, inverse


def _arc_geometry(result, start, target, alpha, path_arc):
    """Community's path functions: every point follows its path (an arc, or a _PointPath
    such as path_along_circles or a user function) in the parent frame."""
    if isinstance(path_arc, _PointPath):
        def move(p, q):
            return list(path_arc.point(p, q, alpha))
    else:
        factor = _arc_factor(alpha, path_arc)
        def move(p, q):
            dx, dy = q[0] - p[0], q[1] - p[1]
            dz = (q[2] - p[2]) if len(p) > 2 and len(q) > 2 else 0
            return [p[0] + factor.real * dx - factor.imag * dy, p[1] + factor.imag * dx + factor.real * dy,
                    p[2] + alpha * dz if len(p) > 2 else 0]
    kind = result['type']
    fields = {'bezierpath': ('curves', 'vertices'), 'polygon': ('vertices',), 'polyline': ('vertices',),
              'line': ('start', 'end'), 'arrow': ('start', 'end')}.get(kind)
    if fields is None or start['type'] != kind or target['type'] != kind:
        # Analytical shapes, text and images: the center follows the path.
        centers = [Vector(data['position']) + Vector(data.get('geometry_center', ORIGIN)) for data in (start, target)]
        offset = Vector(move(list(centers[0]), list(centers[1]))) - (centers[0] + (centers[1] - centers[0]) * alpha)
        result['position'] = list(Vector(result['position']) + offset)
        return
    first, last, (_, inverse) = _snapshot_pose(start)[0], _snapshot_pose(target)[0], _snapshot_pose(result)
    if inverse is None:
        return
    def arc(a, b):
        p, q = first(a), last(b)
        if len(p) < 3 or len(q) < 3:
            p, q = list(p) + [0] * (3 - len(p)), list(q) + [0] * (3 - len(q))
        return inverse(move(p, q))
    for field in fields:
        a, b = start.get(field), target.get(field)
        if a is None or b is None:
            continue
        if field == 'curves':
            if len(a) == len(b) and all(len(x) == len(y) for x, y in zip(a, b)):
                result[field] = [[arc(p, q) for p, q in zip(x, y)] for x, y in zip(a, b)]
        elif field == 'vertices':
            if len(a) == len(b):
                result[field] = [arc(p, q) for p, q in zip(a, b)]
        else:
            result[field] = arc(a, b)


_PATH_TYPES = ('polyline', 'polygon', 'bezierpath', 'circle', 'arc', 'ellipse',
               'square', 'rectangle', 'triangle', 'line', 'arrow', 'annulus')


def _bbox_center(points):
    """Center of the 3D bounding box of a point list (ORIGIN when empty)."""
    if not points:
        return Vector(ORIGIN)
    return Vector((min(p[i] for p in points) + max(p[i] for p in points)) / 2
                  for i in range(3))


def _painted_paths(data, path=(), nested=True):
    """Preorder paths of drawable family members (Community's family_members_with_points)."""
    painted = data['type'] not in ('vgroup', 'mobject', 'valuetracker')
    result = [path] if painted else []
    if nested or not painted:
        for index, child in enumerate(data.get('children', [])):
            result += _painted_paths(child, path + (index,), nested)
    return result


class Animation:
    _instant = False  # Only Add may have a zero run_time.
    set_default = classmethod(_set_default)

    def __new__(cls, *args, use_override=True, **kwargs):
        mobject = args[0] if args else kwargs.get('mobject')
        if use_override and isinstance(mobject, Mobject):
            # Community's @override_animation: a mobject method builds this animation.
            for klass in type(mobject).__mro__:
                for value in vars(klass).values():
                    if getattr(value, '_override_animation', None) is cls:
                        return value(mobject, *args[1:], **kwargs)
        return super().__new__(cls)

    def __init__(self, mobject, run_time=1, rate_func=smooth, lag_ratio=0, remover=False,
                 introducer=False, name=None, suspend_mobject_updating=True, reverse_rate_function=False,
                 use_override=True):
        if isinstance(lag_ratio, bool) or not isinstance(lag_ratio, _REAL) or not math.isfinite(lag_ratio) or lag_ratio < 0:
            raise ValueError('lag_ratio must be nonnegative and finite')
        if not callable(rate_func):
            raise TypeError('rate_func must be callable')
        self.reverse_rate_function = bool(reverse_rate_function)
        self.mobject, self.run_time, self.rate_func = mobject, run_time, rate_func
        self.lag_ratio, self.remover, self.introducer, self.name = lag_ratio, bool(remover), introducer, name
        self.suspend_mobject_updating = suspend_mobject_updating

    # Community's custom-animation protocol. A subclass overriding one of these hooks
    # runs live like Community: begin(), interpolate(alpha) on each frame, finish(),
    # then clean_up_from_scene(scene).
    _COMMUNITY_HOOKS = ('interpolate', 'interpolate_mobject', 'interpolate_submobject')

    @property
    def _community_style(self):
        cls = type(self)
        return any(getattr(cls, name) is not getattr(Animation, name) for name in self._COMMUNITY_HOOKS)

    def interpolate(self, alpha):
        self.interpolate_mobject(alpha)

    def interpolate_mobject(self, alpha):
        families = list(self.get_all_families_zipped())
        for index, mobjects in enumerate(families):
            self.interpolate_submobject(*mobjects, self.get_sub_alpha(alpha, index, len(families)))

    def interpolate_submobject(self, submobject, starting_submobject, alpha):
        pass  # Implemented by subclasses.

    def get_sub_alpha(self, alpha, index, num_submobjects):
        full = (num_submobjects - 1) * self.lag_ratio + 1
        return self.rate_func(max(0, min(1, alpha * full - index * self.lag_ratio)))

    def create_starting_mobject(self):
        return self.mobject.copy()

    def get_all_mobjects(self):
        return [self.mobject, self.starting_mobject]

    def get_all_families_zipped(self):
        return zip(*(mobject.family_members_with_points() for mobject in self.get_all_mobjects()))

    def get_all_mobjects_to_update(self):
        return [m for m in self.get_all_mobjects() if m is not self.mobject]

    def update_mobjects(self, dt):
        for mobject in self.get_all_mobjects_to_update():
            mobject.update(dt)

    def clean_up_from_scene(self, scene):
        if self.is_remover():
            scene.remove(self.mobject)

    def get_run_time(self):
        return self.run_time

    def set_run_time(self, run_time):
        self.run_time = run_time
        return self

    def get_rate_func(self):
        return self.rate_func

    def set_rate_func(self, rate_func):
        self.rate_func = rate_func
        return self

    def set_name(self, name):
        self.name = name
        return self

    def is_remover(self):
        return self.remover

    def is_introducer(self):
        return self.introducer

    def copy(self):
        return copy.deepcopy(self)

    def _community_begin(self):
        self.starting_mobject = self.create_starting_mobject()
        if self.suspend_mobject_updating:
            self.mobject.suspend_updating()
        self.interpolate(0)

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
        if self._community_style:
            self.finish()
            self.clean_up_from_scene(scene)
            return
        self.finish(scene)
        if self.remover:
            scene.remove(self.mobject)

    def _advance_copies(self, dt):
        """Community's Animation.update_mobjects: run updaters on internal copies."""
        if self._community_style:
            self.update_mobjects(dt)

    def begin(self, scene=None):
        if scene is None:
            return self._community_begin()
        scene._introduce(self.mobject)
        self.start = self.mobject.to_dict()

    def sample(self, alpha):
        return [self.start]

    def finish(self, scene=None):
        if scene is None:
            # Community's finish: the final frame, then resume the mobject's updaters.
            self.interpolate(1)
            if self.suspend_mobject_updating and self.mobject is not None:
                self.mobject.resume_updating()

    def objects(self):
        return [self.mobject]

    def prepare(self, scene):
        if self._community_style:
            if self.mobject is not None:
                scene._introduce(self.mobject)
            self.begin()
            return
        self.begin(scene)
        # Compute the held terminal frame without changing the live scene early.
        terminal = copy.deepcopy(self)
        staging = Scene().add(terminal.mobject)
        terminal._complete(staging)
        self._terminal = [m.to_dict() for m in staging.mobjects]

    def states(self, alpha, rate_func=None):
        if self._community_style:
            # Live like Community: the mobject is drawn as interpolate() leaves it.
            self.interpolate(max(0, min(1, alpha)))
            return {}
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
        if self._fading_in:
            kwargs.setdefault('introducer', True)
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
    def __init__(self, mobject, point, point_color=None, **kwargs):
        kwargs.setdefault('introducer', True)
        super().__init__(mobject, **kwargs)
        if isinstance(point, Mobject):
            point = point.get_center()
        self.point, self.point_color = Vector(point), point_color
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
        return [self._tint(current, alpha).to_dict()]

    def _tint(self, current, alpha):
        """Community starts from a copy recolored with point_color (set_color) and
        interpolates every family member's colors toward the original's."""
        if not self.point_color:
            return current
        start = self.original.copy().set_color(self.point_color)
        def first(color):
            return color[0] if isinstance(color, (list, tuple)) and color and not isinstance(color, str) else color
        for member, a, b in zip(current.get_family(), start.get_family(), self.original.get_family()):
            for name in ('color', 'fill_color', 'stroke_color'):
                ca, cb = first(a.__dict__.get(name)), first(b.__dict__.get(name))
                if isinstance(ca, str) and isinstance(cb, str):
                    member.__dict__[name] = _paint(interpolate_color(ca, cb, alpha))
        return current


class GrowFromCenter(GrowFromPoint):
    def __init__(self, mobject, point_color=None, **kwargs):
        super().__init__(mobject, ORIGIN, point_color=point_color, **kwargs)

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
        _glyph_family(mobject)
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
        kwargs.setdefault('introducer', True)
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
        _glyph_family(vmobject)
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
    if abs(path_arc) < STRAIGHT_PATH_THRESHOLD:
        return complex(alpha, 0)
    scale = math.sin(alpha * path_arc / 2) / math.sin(path_arc / 2)
    angle = (alpha - 1) * path_arc / 2
    return complex(scale * math.cos(angle), scale * math.sin(angle))


class Transform(Animation):
    def __init__(self, mobject, target_mobject, path_arc=0, path_arc_axis=OUT, path_func=None, **kwargs):
        super().__init__(mobject, **kwargs)
        point_path = None
        if path_func is not None:
            if isinstance(path_func, _PathFunction):
                path_arc, path_arc_axis = path_func.path_arc, OUT
            elif isinstance(path_func, _PointPath):
                point_path = path_func
            elif callable(path_func):
                point_path = _FunctionPath(path_func)
            else:
                raise TypeError('path_func must be a path function')
        if not isinstance(target_mobject, Mobject):
            raise TypeError('Transform expects a target Mobject')
        NumberLine._real(path_arc, 'path_arc')
        if point_path is None and Vector(path_arc_axis) not in (OUT, IN):
            # Community's path_along_arc about any axis moves every point on its own arc.
            point_path = _AxisArcPath(path_arc, path_arc_axis)
        self.path_arc = point_path or (path_arc if Vector(path_arc_axis) == OUT else -path_arc)
        self.target = target_mobject.copy()

    def begin(self, scene):
        super().begin(scene)
        self._transform_plan = None
        self._path_target = None
        # Community updates the starting and target copies (which keep the mobject's
        # updaters) every frame, so e.g. a rotating updater keeps turning the morph.
        self._live_start = (self.mobject.copy() if any(m.updaters for m in self.mobject.get_family())
                            else None)
        if self.mobject.__dict__.get('_stretch_baked') or self.target.__dict__.get('_stretch_baked'):
            def canonical(mobject):
                # Already-baked families are canonical; re-mapping them is costly.
                if all(member.__dict__.get('_stretch_baked') for member in mobject.get_family()):
                    return mobject.to_dict()
                return mobject.copy().stretch(1,0).to_dict()
            try:
                start, target = canonical(self.mobject), canonical(self.target)
            except NotImplementedError:
                pass  # Unsupported target types keep the existing fade/morph plan.
            else:
                self.start,self._path_target = start,target
                self._live_start = None

    def _advance_copies(self, dt):
        if self.__dict__.get('_live_start') is None:
            return
        self._live_start.update(dt)
        self.target.update(dt)
        self.start, self._transform_plan = self._live_start.to_dict(), None

    def sample(self, alpha):
        end = self._path_target or self.target.to_dict()
        if self._transform_plan is None:
            self._transform_plan = _transform_plan(self.start, end)
        return _sample_transform(self._transform_plan, alpha, self.path_arc)

    @property
    def _lagged(self):
        # Subclasses with their own sampling keep it; lag applies to the aligned plan.
        return self.lag_ratio > 0 and type(self).sample is Transform.sample

    def sample_members(self, alpha, rate_func):
        """Community's get_sub_alpha: each painted member runs its own lagged sub-alpha."""
        self.sample(0)
        plan = self._transform_plan
        count = _plan_members(plan)
        full = (count - 1) * self.lag_ratio + 1
        index = itertools.count()
        def member_alpha():
            return rate_func(max(0, min(1, alpha * full - next(index) * self.lag_ratio)))
        return _sample_transform(plan, rate_func(alpha), self.path_arc, member_alpha)

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
        if not all(math.isfinite(v) for v in axis) or not any(axis):
            raise ValueError('Rotation axis must be finite and nonzero')
        if about_point is not None and about_edge is not None:
            raise ValueError('Pass about_point or about_edge, not both')
        # In-plane axes rotate in 3D: each sample bakes the rigid rotation, which
        # is exactly Community's path_arc interpolation about that axis.
        self.axis = OUT if axis in (OUT, IN) else axis
        self.angle = angle if axis != IN else -angle
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
        angle = self.angle * alpha
        if angle % TAU and (self.axis != OUT or self.original._is_3d()):
            # Mobject.rotate would bake these points through a validated copy and
            # become(); the throwaway sample is baked in place instead.
            if self.__dict__.get('_pivot') is None:
                self._pivot = (Vector(self.about_point) if self.about_point is not None
                               else self.original.get_center())
            pivot, matrix = self._pivot, rotation_matrix(angle, self.axis)
            current._bake_3d_map(lambda point: list(pivot + _apply_rows(matrix, Vector(point) - pivot)))
        else:
            current.rotate(angle, self.axis, about_point=self.about_point)
        return [current.to_dict()]

    def finish(self, scene):
        final = self.original.copy().rotate(self.angle, self.axis, about_point=self.about_point)
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
                 key_map=None, path_arc=0, **kwargs):
        if not isinstance(mobject, Mobject) or not isinstance(target_mobject, Mobject):
            raise TypeError(type(self).__name__ + ' expects two mobjects')
        if mobject is target_mobject:
            raise ValueError('Source and target must be different mobjects')
        super().__init__(mobject, **kwargs)
        # Community passes transform options such as path_arc to the matched transforms.
        self.path_arc = NumberLine._real(path_arc, 'path_arc')
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
        arc = self.path_arc if abs(self.path_arc) >= STRAIGHT_PATH_THRESHOLD else 0
        states = [state for plan in self.plans for state in _sample_transform(plan, alpha, arc)]
        for source, source_end, target_start, target in self.sliding:
            leaving, arriving = interpolate(source, source_end, alpha), interpolate(target_start, target, alpha)
            if arc and 0 < alpha < 1:
                _arc_geometry(leaving, source, source_end, alpha, arc)
                _arc_geometry(arriving, target_start, target, alpha, arc)
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
        # Community: the mobject ends shaped like its target, which then takes its place
        # in the scene (inside its parent group when nested).
        super().finish(scene)
        if self.mobject in scene.get_mobject_family_members():
            scene.replace(self.mobject, self.replacement)
            if self.mobject in scene.foreground_mobjects:
                scene.add()  # Community keeps foreground mobjects drawn last.
        else:
            scene.add(self.replacement)

    def objects(self):
        return [self.mobject, self.replacement]


class ReplacementTransform(Transform):
    def __init__(self, mobject, target_mobject, **kwargs):
        super().__init__(mobject, target_mobject, **kwargs)
        self.replacement = target_mobject

    def finish(self, scene):
        # Community: the mobject ends shaped like its target, which then takes its place
        # in the scene (inside its parent group when nested).
        super().finish(scene)
        if self.mobject in scene.get_mobject_family_members():
            scene.replace(self.mobject, self.replacement)
            if self.mobject in scene.foreground_mobjects:
                scene.add()  # Community keeps foreground mobjects drawn last.
        else:
            scene.add(self.replacement)

    def objects(self):
        return [self.mobject, self.replacement]


class Animate(Transform):
    _ANIMATION_OPTIONS = ('run_time', 'rate_func', 'lag_ratio', 'remover', 'introducer', 'name', 'path_arc',
                          'reverse_rate_function', 'suspend_mobject_updating')

    def __init__(self, mobject):
        super().__init__(mobject, mobject)
        self.operations = []

    def __call__(self, **kwargs):
        """mobject.animate(run_time=..., lag_ratio=...): Community's animation arguments."""
        unsupported = [key for key in kwargs if key not in self._ANIMATION_OPTIONS]
        if unsupported:
            raise NotImplementedError('Unsupported animate options: ' + ', '.join(unsupported))
        if 'lag_ratio' in kwargs:
            NumberLine._real(kwargs['lag_ratio'], 'lag_ratio', nonnegative=True)
        if 'path_arc' in kwargs:
            NumberLine._real(kwargs['path_arc'], 'path_arc')
        if 'rate_func' in kwargs and not callable(kwargs['rate_func']):
            raise TypeError('rate_func must be callable')
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self

    def begin(self, scene):
        # Relative method chains resolve against the state at this stage's start.
        self.target = self.mobject.copy()
        for name, args, kwargs in self.operations:
            getattr(self.target, name)(*args, **kwargs)
        super().begin(scene)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        method = getattr(type(self.mobject), name, None)
        if hasattr(method, '_override_animate') and not self.operations:
            # Community's @override_animate(method) decorator.
            custom = method._override_animate
            return lambda *args, **kwargs: custom(self.mobject, *args, anim_args={}, **kwargs)
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
    introducer = False

    def __init__(self, *animations, lag_ratio=0, run_time=None, rate_func=linear, group=None, introducer=False):
        if not animations or any(not isinstance(a, (Animation, AnimationGroup)) for a in animations):
            raise TypeError('AnimationGroup expects at least one supported animation')
        if group is not None and not isinstance(group, Mobject):
            raise TypeError('AnimationGroup group must be a Mobject')
        self._group, self.introducer = group, bool(introducer)
        if not math.isfinite(lag_ratio) or lag_ratio < 0:
            raise ValueError('lag_ratio must be nonnegative and finite')
        self.animations, self.rate_func = animations, rate_func
        self.timings = []
        start = 0
        for animation in animations:
            if (not math.isfinite(animation.run_time) or animation.run_time < 0 or
                    (animation.run_time == 0 and not animation._instant)):
                raise ValueError('Animation run_time must be positive and finite')
            self.timings.append((start, animation.run_time))
            start += lag_ratio * animation.run_time
        self.natural_duration = max(start + duration for start, duration in self.timings)
        if not math.isfinite(self.natural_duration):
            raise ValueError('Animation timeline duration must be finite')
        self.run_time = self.natural_duration if run_time is None else run_time
        if not math.isfinite(self.run_time) or self.run_time < 0 or (self.run_time == 0 and not self._instant):
            raise ValueError('Animation run_time must be positive and finite')

    @property
    def _instant(self):
        return all(animation._instant for animation in self.animations)

    @property
    def mobject(self):
        return self.group

    @property
    def group(self):
        """Community's group of the non-introducer members' mobjects, built on first use."""
        if self._group is None:
            members = [a.mobject for a in self.animations if not a.introducer and a.mobject is not None]
            self._group = Group(*dict.fromkeys(members))
        return self._group

    def objects(self):
        return [m for animation in self.animations for m in animation.objects()]

    def prepare(self, scene):
        for animation in self.animations:
            animation.prepare(scene)

    def states(self, alpha, rate_func=None):
        time = self.natural_duration if alpha >= 1 else (rate_func or self.rate_func)(max(0, alpha)) * self.natural_duration
        result = {}
        for animation, (start, duration) in zip(self.animations, self.timings):
            result.update(animation.states((time - start) / duration if duration else (1 if time >= start else 0)))
        return result

    def finish(self, scene):
        for animation in self.animations:
            animation._complete(scene)

    def _complete(self, scene):
        self.finish(scene)

    def _advance_copies(self, dt):
        for animation in self.animations:
            animation._advance_copies(dt)


class LaggedStart(AnimationGroup):
    def __init__(self, *animations, lag_ratio=0.05, **kwargs):
        super().__init__(*animations, lag_ratio=lag_ratio, **kwargs)


class Succession(AnimationGroup):
    """Run consecutive stages live, as Community does: each stage begins on the live
    scene when the previous one finishes, so stage callbacks see real objects."""
    def __init__(self, *animations, lag_ratio=1, **kwargs):
        super().__init__(*animations, lag_ratio=lag_ratio, **kwargs)

    def objects(self):
        return list(dict.fromkeys(super().objects()))

    def prepare(self, scene):
        self._scene, self._active = scene, -1
        # Objects first introduced by a later stage stay hidden until it begins.
        self._hidden = {m for m in self.objects() if m not in scene.get_mobject_family_members()}
        self._advance(0)
        # Placeholder roots keep the capture order stable for later introductions.
        for mobject in self.objects():
            scene._introduce(mobject)

    def _advance(self, stage):
        while self._active < stage:
            if self._active >= 0:
                self.animations[self._active]._complete(self._scene)
            self._active += 1
            animation = self.animations[self._active]
            self._scene.validate(animation)
            animation.prepare(self._scene)
            self._hidden.difference_update(animation.objects())

    def states(self, alpha, rate_func=None):
        time = self.natural_duration if alpha >= 1 else (rate_func or self.rate_func)(max(0, alpha)) * self.natural_duration
        # Only one stage is active: the next begins when the active one ends, so with
        # lag_ratio < 1 a later stage starts partway through (Community's interpolate).
        stage = max(self._active, 0)
        while stage < len(self.animations) - 1 and time >= sum(self.timings[stage]):
            stage += 1
        self._advance(stage)
        start, duration = self.timings[self._active]
        result = {m: [] for m in self._hidden}
        result.update(self.animations[self._active].states(
            min(1, max(0, (time - start) / duration)) if duration else 1))
        return result

    def finish(self, scene):
        self._advance(len(self.animations) - 1)
        self.animations[-1]._complete(scene)
        self._active = len(self.animations)


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
        if rows[2] == [0, 0, 1] and rows[0][2] == rows[1][2] == 0:
            # An XY matrix: the linear map keeps text and formulas whole (same geometry).
            self.operations[-1] = ('apply_matrix', ([rows[0][:2], rows[1][:2]],), {'about_point': pivot})


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


def _frame_count(duration):
    """len(np.arange(0, duration, 1 / FPS)): Community's sampled animation frames."""
    return max(0, math.ceil(duration / (1 / FPS))) if duration > 0 else 0


class Wait(Animation):
    """A pause inside play(), AnimationGroup or Succession."""
    def __init__(self, run_time=1, stop_condition=None, frozen_frame=None, rate_func=linear, **kwargs):
        if stop_condition is not None and not callable(stop_condition):
            raise TypeError('stop_condition must be callable')
        NumberLine._real(run_time, 'Wait run_time', positive=True)
        super().__init__(None, run_time=run_time, rate_func=rate_func, **kwargs)
        # Only a lone Wait passed to play() honors these, as in Community.
        self.stop_condition, self.frozen_frame = stop_condition, frozen_frame

    def objects(self):
        return []

    def prepare(self, scene):
        pass

    def states(self, alpha, rate_func=None):
        return {}

    def _complete(self, scene):
        pass


class GrowFromEdge(GrowFromPoint):
    def __init__(self, mobject, edge, point_color=None, **kwargs):
        super().__init__(mobject, ORIGIN, point_color=point_color, **kwargs)
        self.edge = Mobject._xy_vector(edge, 'Growth edge')

    def begin(self, scene):
        self.point = self.mobject.get_critical_point(self.edge)
        super().begin(scene)


class GrowArrow(GrowFromPoint):
    def __init__(self, arrow, point_color=None, **kwargs):
        super().__init__(arrow, ORIGIN, point_color=point_color, **kwargs)

    def begin(self, scene):
        self.point = Vector(self.mobject.get_start())
        super().begin(scene)


class SpinInFromNothing(GrowFromCenter):
    """Grow from the center along Community's arc path (path_arc = angle)."""
    def __init__(self, mobject, angle=PI / 2, point_color=None, **kwargs):
        super().__init__(mobject, point_color=point_color, **kwargs)
        self.angle = NumberLine._real(angle, 'Spin angle')

    def sample(self, alpha):
        factor = _arc_factor(alpha, self.angle)
        current = self.original.copy().scale(abs(factor), about_point=self.point)
        current.rotate(math.atan2(factor.imag, factor.real), about_point=self.point)
        return [self._tint(current, alpha).to_dict()]


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
        kwargs.setdefault('introducer', True)
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


class DefaultSectionType:
    """Community's section type names (sections only mark frame ranges in the preview)."""
    NORMAL = 'default.normal'


class Scene:
    camera_class = PreviewConfig

    def __init__(self, camera_config=None, *, renderer=None, camera_class=None, always_update_mobjects=False,
                 random_seed=None, skip_animations=False):
        # Community's Scene arguments: a camera class, and a seed for random and NumPy's random.
        if camera_class is not None:
            self.camera_class = camera_class
        self.always_update_mobjects, self.random_seed = always_update_mobjects, random_seed
        if random_seed is not None:
            random.seed(random_seed)
            try:
                import numpy
            except ImportError:
                pass
            else:
                numpy.random.seed(random_seed)
        self.camera = self.camera_class(**config.to_dict())
        for name, value in (camera_config or {}).items():
            setattr(self.camera, name, value)
        self.mobjects, self.frames = [], []
        self.foreground_mobjects = []
        self._elapsed_frames = 0
        self.updaters, self.sounds, self.subcaptions = [], [], []
        self.sections = [{'name': 'autocreated', 'type': DefaultSectionType.NORMAL, 'skip_animations': False, 'frame': 0}]
        self._skipping = False
        self._camera_views = []
        # id(root) -> frame data, reused for unchanged roots inside one play/wait loop.
        self._static_frames = None

    @property
    def renderer(self):
        """Community's CairoRenderer view: its camera, scene time and frame count."""
        return types.SimpleNamespace(camera=self.camera, time=self.time, num_plays=len(self.sections),
                                     skip_animations=self._skipping)

    def _add_camera_view(self, display):
        """Community's MultiCamera.add_image_mobject_from_camera."""
        if not isinstance(display, ImageMobjectFromCamera):
            raise TypeError('Camera views must be ImageMobjectFromCamera displays')
        if all(display is not view for view, _ in self._camera_views):
            self._camera_views.append((display, display.camera))

    @staticmethod
    def _sampled_clone(mobject, overrides):
        """An independent family copy showing an object's sampled animation state."""
        clone = copy.deepcopy(mobject)
        states = overrides.get(mobject) if overrides else None
        if not states:
            return clone
        def apply(target, snapshot):
            for key, value in snapshot.items():
                if key not in ('type', 'children', 'geometry_center'):
                    target.__dict__[key] = copy.deepcopy(value)
            target._type = snapshot['type']
            target._sampled_geometry_center = snapshot['geometry_center']
            target.__dict__.pop('_family_pivot_cache', None)
            children = snapshot['children']
            target.children = target.children[:len(children)]
            for child, state in zip(target.children, children):
                apply(child, state)
        apply(clone, max(states, key=lambda state: state['opacity']))
        return clone

    def _camera_view_data(self, overrides, camera):
        """Community's MultiCamera.update_sub_cameras, then each view's frame and display box."""
        views = []
        for display, sub_camera in self._camera_views:
            box = self._sampled_clone(display, overrides)._bounds()
            if not all(math.isfinite(v) for v in box):
                raise ValueError('Zoomed displays must stay finite')
            # Sub-cameras take the display's whole-pixel shape, keeping the frame width.
            pixel_width = int(camera['pixel_width'] * (box[2] - box[0]) / camera['frame_width'])
            pixel_height = int(camera['pixel_height'] * (box[3] - box[1]) / camera['frame_height'])
            frame = sub_camera.frame
            states = overrides.get(frame) if overrides else None
            target = self._sampled_clone(frame, overrides) if states else frame
            if pixel_width > 0 and pixel_height > 0 and target.get_height() > 0:
                height = target.get_width() * pixel_height / pixel_width
                if math.isfinite(height) and height > 0 and abs(height - target.get_height()) > 1e-12:
                    target.stretch_to_fit_height(height)
                    if states and len(states) == 1:
                        sampled = target.to_dict()
                        sampled['children'] = states[0]['children']
                        overrides[frame] = [sampled]
            source = target._bounds()
            if not all(math.isfinite(v) for v in source):
                raise ValueError('Zoomed camera frames must stay finite')
            if source[2] - source[0] <= 1e-9 or source[3] - source[1] <= 1e-9:
                continue  # A collapsed camera frame shows nothing.
            views.append({'id': display.camera_view, 'source': list(source), 'display': list(box),
                          'background': sub_camera.background_color,
                          'background_opacity': sub_camera.background_opacity})
        return views

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
                # A camera display's screen is the display itself in Community, not a member.
                visit([child for child in mobject.children if 'camera_screen' not in child.__dict__], hit)
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
        # A group and one of its own members cannot both move.
        for root in roots:
            for obj in roots:
                if obj is not root and obj in family(root):
                    raise NotImplementedError('Reorder a group or its members, not both')
        return roots

    def bring_to_front(self, *mobjects):
        # Community re-adds them: group members split out of their scene group.
        return self.add(*self._ordered_roots(mobjects))

    def bring_to_back(self, *mobjects):
        roots = self._ordered_roots(mobjects)
        self.remove(*roots)
        self.mobjects = roots + self.mobjects
        return self

    def clear(self):
        self.mobjects = []
        self.foreground_mobjects = []
        return self

    def _update_mobjects(self, dt, overrides=None, scene_updaters=True):
        """Expose sampled geometry to dependent callbacks without committing animations."""
        roots = list(self.mobjects)
        if isinstance(self.camera, MovingCamera) and self.camera.frame not in roots:
            roots.append(self.camera.frame)
        scene_updaters = list(getattr(self, 'updaters', [])) if scene_updaters else []
        if not scene_updaters and not any(m.get_family_updaters() for m in roots):
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
            # Community's update_self: scene-level updaters run last and see
            # the interpolated mobjects.
            for func in scene_updaters:
                func(dt)
        finally:
            for mobject, state in saved.items():
                mobject.__dict__ = state

    def capture(self, overrides=None, *, advance_time=True):
        if self._skipping and advance_time:
            # next_section(skip_animations=True): time passes but no frames are kept.
            self._elapsed_frames += 1
            return
        if len(self.frames) >= MAX_FRAMES:
            raise ValueError('Preview exceeds 60 seconds / 900 frames. Shorten the scene.')
        if isinstance(self.camera, MovingCamera):
            frame_states = overrides.get(self.camera.frame) if overrides else None
            if frame_states is not None and len(frame_states) != 1:
                raise ValueError('Camera animation must produce one frame rectangle')
            camera = self.camera.to_dict(frame_states[0] if frame_states else None)
        else:
            camera = self.camera.to_dict()
        if self._camera_views:
            overrides = dict(overrides or {})
            camera['views'] = self._camera_view_data(overrides, camera)
        # VectorScene.lock_in_faded_grid bakes a background into later frames.
        objects = list(getattr(self, '_background_snapshots', ()))
        objects.extend(self._frame_objects(overrides))
        self.frames.append({'mobjects': objects, 'camera': camera})
        if advance_time:
            self._elapsed_frames += 1

    def _static_frames_safe(self, animations=()):
        """Whether roots untouched by these animations stay fixed for the whole loop.

        Only built-in camera updaters may run, there must be no scene updaters, and no
        animation may call user code that could edit other mobjects each frame."""
        if self.updaters:
            return False
        pending = list(animations)
        while pending:
            animation = pending.pop()
            if isinstance(animation, UpdateFromFunc) or getattr(animation, '_community_style', False):
                return False
            if isinstance(animation, AnimationGroup):
                pending.extend(animation.animations)
            elif isinstance(animation, TransformAnimations):
                pending.extend((animation.start_anim, animation.end_anim))
        for root in self.mobjects:
            for member in root.get_family():
                if any(not getattr(f, '_camera_updater', False) for f in member.updaters):
                    return False
        return True

    def _root_frame_data(self, mobject, overrides):
        """One root's frame entries; ThreeDScene flattens them to world leaves."""
        return self._root_states(mobject, overrides)

    def _frame_objects(self, overrides):
        """The scene's roots as frame entries, reusing unchanged roots within a loop."""
        frame_center = getattr(self.camera, '_frame_center', None)
        cache = self._static_frames
        objects = []
        for mobject in self.mobjects:
            if isinstance(mobject, (CameraFrame, ValueTracker)) or mobject is frame_center:
                continue
            static = cache is not None and not (overrides and any(
                member in overrides for member in mobject.get_family()))
            if static and id(mobject) in cache:
                objects.extend(cache[id(mobject)])
                continue
            data = self._root_frame_data(mobject, overrides)
            if static:
                cache[id(mobject)] = data
            objects.extend(data)
        return objects

    def _root_states(self, root, overrides):
        def states(mobject):
            if overrides and mobject in overrides:
                return [_refresh_tip_shafts(state) for state in overrides[mobject]]
            if not overrides or not any(member in overrides for member in mobject.get_family()[1:]):
                return [mobject.to_dict()]
            # An animated member is drawn inside its on-screen group.
            data = mobject.to_dict()
            data['children'] = [state for child in mobject.children for state in states(child)]
            return [_refresh_tip_shafts(data)]
        return states(root)

    _PLAY_OPTIONS = ('path_arc', 'lag_ratio', 'remover', 'introducer', 'name',
                     'suspend_mobject_updating', 'reverse_rate_function')

    def play(self, *animations, run_time=None, rate_func=None, **kwargs):
        unsupported = [key for key in kwargs if key not in self._PLAY_OPTIONS]
        if unsupported:
            raise NotImplementedError('Unsupported play options: ' + ', '.join(unsupported))
        if len(animations) == 1 and type(animations[0]) is Wait:
            # A lone Wait follows Community's static/updating wait logic.
            wait = animations[0]
            return self.wait(wait.run_time if run_time is None else run_time, wait.stop_condition, wait.frozen_frame)
        if not animations or any(not isinstance(a, (Animation, AnimationGroup)) for a in animations):
            raise TypeError('play() expects supported animations such as Create or Transform')
        if 'path_arc' in kwargs:
            NumberLine._real(kwargs['path_arc'], 'path_arc')
        if 'lag_ratio' in kwargs:
            NumberLine._real(kwargs['lag_ratio'], 'lag_ratio', nonnegative=True)
        # Community's compile_animations sets play() options on every animation.
        for animation in animations:
            for key, value in kwargs.items():
                setattr(animation, key, value)
        self.validate(*animations)
        durations = [a.run_time if run_time is None else run_time for a in animations]
        if any(not math.isfinite(d) or d < 0 or (d == 0 and not a._instant) for d, a in zip(durations, animations)):
            raise ValueError('Animation run_time must be positive and finite')
        # Instant animations (Add) take no frames, as Community's zero run_time;
        # other totals are at least one frame (validate_run_time).
        count = max(1, _frame_count(max(durations))) if max(durations) else 0
        if count + len(self.frames) >= MAX_FRAMES:
            raise ValueError('Preview exceeds 60 seconds / 900 frames. Shorten the scene.')
        if rate_func is not None:
            # play() options override each animation, as in Community.
            for animation in animations:
                animation.rate_func = rate_func
        for animation in animations:
            animation.prepare(self)
        self._static_frames = {} if self._static_frames_safe(animations) else None
        try:
            for frame in range(count):
                time = frame / FPS
                overrides = {}
                for animation in animations:
                    animation._advance_copies(0 if frame == 0 else 1 / FPS)
                for animation, duration in zip(animations, durations):
                    overrides.update(animation.states(time / duration if duration else 1))
                self._update_mobjects(0 if frame == 0 else 1 / FPS, overrides)
                self.capture(overrides)
        finally:
            self._static_frames = None
        # Update-function animations finish last, seeing their neighbors' final states as
        # Community's last frame does (e.g. MaintainPositionRelativeTo a moving object).
        for animation in sorted(animations, key=lambda a: isinstance(a, UpdateFromFunc)):
            animation._complete(self)
        # Community resumes the animated objects' updaters and runs update_mobjects(0)
        # (not scene updaters), so dependents such as Graph edges catch up.
        self._update_mobjects(0, scene_updaters=False)

    def validate(self, *animations):
        objects = [m for a in animations for m in a.objects()]
        def family(mobject):
            return [mobject] + [m for child in mobject.children for m in family(child)]
        # A member shared inside one family is allowed (Community de-duplicates
        # families); separately animated objects must not share members.
        seen = set()
        for obj in objects:
            members = {id(m) for m in family(obj)}
            if members & seen:
                raise ValueError('Use one animation per object in each play() call')
            seen |= members
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

    def wait(self, duration=1, stop_condition=None, frozen_frame=None):
        if not math.isfinite(duration) or duration < 0:
            raise ValueError('Wait duration must be nonnegative and finite')
        if stop_condition is not None and not callable(stop_condition):
            raise TypeError('stop_condition must be callable')
        if 0 < duration < 1 / FPS:
            duration = 1 / FPS  # Community's validate_run_time: at least one frame.
        static = self._wait_is_static(stop_condition, frozen_frame)
        # Community freezes a static wait for int(duration * fps) frames without running
        # updaters; other waits sample np.arange(0, duration, 1 / fps).
        count = int(duration / (1 / FPS)) if static else _frame_count(duration)
        if count + len(self.frames) >= MAX_FRAMES and stop_condition is None and not self._skipping:
            raise ValueError('Preview exceeds 60 seconds / 900 frames. Shorten the scene.')
        if static:
            self._static_frames = {}
            try:
                for frame in range(count):
                    self.capture()
            finally:
                self._static_frames = None
            return
        safe = stop_condition is None and self._static_frames_safe()
        self._static_frames = {} if safe else None
        self._update_mobjects(0, scene_updaters=False)  # Community's compile_animation_data.
        try:
            for frame in range(count):
                self._update_mobjects(0 if frame == 0 else 1 / FPS)
                if stop_condition is not None and stop_condition():
                    break
                if len(self.frames) >= MAX_FRAMES - 1:
                    raise ValueError('Preview exceeds 60 seconds / 900 frames. Shorten the scene.')
                self.capture()
        finally:
            self._static_frames = None
        if count:
            # Like Community's play_internal: no time passes after the last frame.
            self._update_mobjects(0, scene_updaters=False)

    always_update_mobjects = False

    def _wait_is_static(self, stop_condition, frozen_frame):
        """Community's should_update_mobjects for a lone Wait."""
        if frozen_frame is not None:
            return bool(frozen_frame)
        if stop_condition is not None or self.always_update_mobjects or getattr(self, 'updaters', None):
            return False
        roots = list(self.mobjects)
        if isinstance(self.camera, MovingCamera) and self.camera.frame not in roots:
            roots.append(self.camera.frame)
        return not any(member.has_time_based_updater() for root in roots for member in root.get_family())

    def wait_until(self, stop_condition, max_time=60):
        return self.wait(max_time, stop_condition=stop_condition)

    def pause(self, duration=1.0):
        return self.wait(duration, frozen_frame=True)

    def next_section(self, name='unnamed', section_type=None, skip_animations=False):
        """Start a section; skip_animations keeps time and state but drops its frames."""
        if not isinstance(name, str):
            raise TypeError('Section names must be strings')
        self._skipping = bool(skip_animations)
        self.sections.append({'name': name, 'type': section_type or DefaultSectionType.NORMAL,
                              'skip_animations': self._skipping, 'frame': len(self.frames)})

    def add_sound(self, sound_file, time_offset=0, gain=None, **kwargs):
        # The browser preview has no audio track; sounds are recorded but not played.
        self.sounds.append({'file': str(sound_file), 'time': self.time + time_offset, 'gain': gain})

    def add_subcaption(self, content, duration=1, offset=0):
        NumberLine._real(duration, 'Subcaption duration', nonnegative=True)
        self.subcaptions.append({'content': str(content), 'start': self.time + offset,
                                 'end': self.time + offset + duration})

    def add_updater(self, func):
        if not callable(func):
            raise TypeError('Scene updaters must be callable')
        self.updaters.append(func)

    def remove_updater(self, func):
        self.updaters = [f for f in self.updaters if f is not func]

    def update_self(self, dt):
        for func in list(self.updaters):
            func(dt)

    def update_mobjects(self, dt):
        self._update_mobjects(dt)

    def should_update_mobjects(self):
        return bool(self.updaters) or any(m.get_family_updaters() for m in self.mobjects)

    def get_top_level_mobjects(self):
        families = [m.get_family()[1:] for m in self.mobjects]
        return [m for m in self.mobjects if not any(m in family for family in families)]

    def get_mobject_family_members(self):
        return [member for m in self.mobjects for member in m.get_family()]

    def get_moving_mobjects(self, *animations):
        moving = [member for a in animations for m in a.objects() for member in m.get_family()]
        return list(dict.fromkeys(moving + [m for m in self.get_mobject_family_members() if m.updaters]))

    def get_run_time(self, animations):
        return max(a.run_time for a in animations)

    def get_attrs(self, *keys):
        return [getattr(self, key) for key in keys]

    def replace(self, old_mobject, new_mobject):
        """Swap a mobject in the scene (or inside a scene group) without changing order."""
        if not isinstance(new_mobject, Mobject) or not isinstance(old_mobject, Mobject):
            raise TypeError('replace expects Mobjects')
        def swap(items, owner=None):
            # Community 0.22: drop new_mobject from each searched list (no duplicates), check
            # the whole level first, then descend breadth-first into each member.
            items = list(items)
            changed = False
            if any(item is new_mobject for item in items):
                if old_mobject is new_mobject:
                    return True
                items = [item for item in items if item is not new_mobject]
                changed = True
            found = False
            for index, item in enumerate(items):
                if item is old_mobject:
                    items[index], found, changed = new_mobject, True, True
                    break
            if changed:
                if owner is None:
                    self.mobjects[:] = items
                else:
                    owner._replace_children(items)
            if found:
                return True
            return any(swap(item.children, item) for item in items)
        if not swap(self.mobjects):
            raise ValueError('The mobject to replace is not in the scene')

    def embed(self):
        raise NotImplementedError('Interactive embedding is not available in the browser preview')

    interactive_embed = embed

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
        self._update_mobjects(0, scene_updaters=False)
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
                'math_estimated': sorted(_MATH_ESTIMATED), 'typst_pending': sorted(_TYPST_PENDING)}


Camera = PreviewConfig


class MultiCamera(MovingCamera):
    """Community's camera that also draws image mobjects of other cameras (ZoomedScene's
    displays draw their views as vector insets here)."""
    def __init__(self, image_mobjects_from_cameras=None, allow_cameras_to_capture_their_own_display=False,
                 **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'image_mobjects_from_cameras', list(image_mobjects_from_cameras or []))
        object.__setattr__(self, 'allow_cameras_to_capture_their_own_display',
                           allow_cameras_to_capture_their_own_display)

    def add_image_mobject_from_camera(self, imfc):
        self.image_mobjects_from_cameras.append(imfc)


class MovingCameraScene(Scene):
    camera_class = MovingCamera


class _ZoomedCamera:
    """A sub-camera: a visible ScreenRectangle frame whose view a display shows."""
    def __init__(self, frame=None, fixed_dimension=0, default_frame_stroke_color=WHITE,
                 default_frame_stroke_width=0, background_color=None, background_opacity=1, **kwargs):
        if kwargs:
            raise NotImplementedError('Unsupported zoomed camera options: ' + ', '.join(kwargs))
        NumberLine._real(background_opacity, 'Camera background opacity')
        if frame is None:
            frame = ScreenRectangle(height=config.frame_height)
            frame.set_stroke(default_frame_stroke_color, default_frame_stroke_width)
        elif not isinstance(frame, Mobject):
            raise TypeError('A camera frame must be a Mobject')
        self.frame, self.fixed_dimension = frame, fixed_dimension
        self.default_frame_stroke_color = default_frame_stroke_color
        self.default_frame_stroke_width = default_frame_stroke_width
        self.background_color = _paint(config.background_color if background_color is None else background_color)
        self.background_opacity = min(1, max(0, background_opacity))

    def __deepcopy__(self, memo):
        return self  # Copies of a display keep showing the same camera.

    @property
    def frame_width(self):
        return self.frame.get_width()

    @property
    def frame_height(self):
        return self.frame.get_height()

    @property
    def frame_center(self):
        return self.frame.get_center()


class ImageMobjectFromCamera(Mobject):
    """A display that shows its camera's frame stretched to fit (vector, not pixels).

    A pure container keeps Community's world-space children: an invisible screen
    rectangle marks the view and add_display_frame adds the border.
    """
    _frame_excluded = ('camera', 'default_display_frame_config')
    _view_ids = itertools.count(1)

    def __init__(self, camera, default_display_frame_config=None, **kwargs):
        if not isinstance(camera, (_ZoomedCamera, MovingCamera)):
            raise TypeError('ImageMobjectFromCamera needs a moving camera')
        super().__init__(**kwargs)
        self.camera = camera
        self.default_display_frame_config = ({'stroke_width': 3, 'stroke_color': WHITE, 'buff': 0}
                                             if default_display_frame_config is None
                                             else dict(default_display_frame_config))
        self.camera_view = next(self._view_ids)
        # Community's camera images start 3 units tall at the pixel aspect ratio.
        screen = Rectangle(width=3 * config.pixel_width / config.pixel_height, height=3,
                           stroke_width=0, fill_opacity=0)
        screen.camera_screen = self.camera_view
        self.add(screen)

    @property
    def display_frame(self):
        for child in self.children:
            if getattr(child, '_display_frame', False):
                return child
        raise AttributeError('This display has no display frame; call add_display_frame()')

    def add_display_frame(self, **kwargs):
        options = dict(self.default_display_frame_config)
        options.update(kwargs)
        frame = SurroundingRectangle(self, **options)
        frame._display_frame = True
        return self.add(frame)


class ZoomedScene(MovingCameraScene):
    """A scene with a magnified inset: zoomed_camera.frame is shown in zoomed_display."""
    def __init__(self, camera_class=None, zoomed_display_height=3, zoomed_display_width=3,
                 zoomed_display_center=None, zoomed_display_corner=UP + RIGHT,
                 zoomed_display_corner_buff=DEFAULT_MOBJECT_TO_EDGE_BUFFER,
                 zoomed_camera_config=None, zoomed_camera_image_mobject_config=None,
                 zoomed_camera_frame_starting_position=ORIGIN, zoom_factor=0.15,
                 image_frame_stroke_width=3, zoom_activated=False, **kwargs):
        self.zoomed_display_height, self.zoomed_display_width = zoomed_display_height, zoomed_display_width
        self.zoomed_display_center, self.zoomed_display_corner = zoomed_display_center, zoomed_display_corner
        self.zoomed_display_corner_buff = zoomed_display_corner_buff
        self.zoomed_camera_config = ({'default_frame_stroke_width': 2, 'background_opacity': 1}
                                     if zoomed_camera_config is None else dict(zoomed_camera_config))
        self.zoomed_camera_image_mobject_config = dict(zoomed_camera_image_mobject_config or {})
        self.zoomed_camera_frame_starting_position = zoomed_camera_frame_starting_position
        self.zoom_factor, self.image_frame_stroke_width = zoom_factor, image_frame_stroke_width
        self.zoom_activated = zoom_activated
        super().__init__(**kwargs)

    def setup(self):
        super().setup()
        zoomed_camera = _ZoomedCamera(**self.zoomed_camera_config)
        zoomed_display = ImageMobjectFromCamera(zoomed_camera, **self.zoomed_camera_image_mobject_config)
        zoomed_display.add_display_frame()
        for mobject in (zoomed_camera.frame, zoomed_display):
            mobject.stretch_to_fit_height(self.zoomed_display_height)
            mobject.stretch_to_fit_width(self.zoomed_display_width)
        zoomed_camera.frame.scale(self.zoom_factor)
        zoomed_camera.frame.move_to(self.zoomed_camera_frame_starting_position)
        if self.zoomed_display_center is not None:
            zoomed_display.move_to(self.zoomed_display_center)
        else:
            zoomed_display.to_corner(self.zoomed_display_corner, buff=self.zoomed_display_corner_buff)
        self.zoomed_camera, self.zoomed_display = zoomed_camera, zoomed_display

    def activate_zooming(self, animate=False):
        self.zoom_activated = True
        self._add_camera_view(self.zoomed_display)
        if animate:
            self.play(self.get_zoom_in_animation())
            self.play(self.get_zoomed_display_pop_out_animation())
        self.add_foreground_mobjects(self.zoomed_camera.frame, self.zoomed_display)

    def get_zoom_in_animation(self, run_time=2, **kwargs):
        frame = self.zoomed_camera.frame
        frame.save_state()
        frame.stretch_to_fit_width(self.camera.frame_width)
        frame.stretch_to_fit_height(self.camera.frame_height)
        frame.center()
        frame.set_stroke(width=0)
        return ApplyMethod(frame.restore, run_time=run_time, **kwargs)

    def get_zoomed_display_pop_out_animation(self, **kwargs):
        display = self.zoomed_display
        display.save_state()
        display.replace(self.zoomed_camera.frame, stretch=True)
        return ApplyMethod(display.restore, **kwargs)

    def get_zoom_factor(self):
        return self.zoomed_camera.frame.get_height() / self.zoomed_display.get_height()


def angle_of_vector(vector):
    """The XY angle of a vector, as Community's np.angle(complex(x, y))."""
    vector = list(vector)
    return math.atan2(vector[1], vector[0])


def _matrix_rows(matrix, name='Matrix'):
    rows = [list(row.tolist() if hasattr(row, 'tolist') else row) for row in
            (matrix.tolist() if hasattr(matrix, 'tolist') else matrix)]
    if len(rows) not in (2, 3) or any(len(row) != len(rows) for row in rows):
        raise ValueError(name + ' has bad dimensions')
    for row in rows:
        for value in row:
            NumberLine._real(value, name + ' entry')
    return [[float(v) for v in row] for row in rows]


def _matrix_inverse(matrix):
    rows = _matrix_rows(matrix)
    n = len(rows)
    work = [row + [float(i == j) for j in range(n)] for i, row in enumerate(rows)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda r: abs(work[r][column]))
        if abs(work[pivot][column]) < 1e-12:
            raise ValueError('Singular matrix')
        work[column], work[pivot] = work[pivot], work[column]
        scale = work[column][column]
        work[column] = [v / scale for v in work[column]]
        for r in range(n):
            if r != column and work[r][column]:
                factor = work[r][column]
                work[r] = [a - factor * b for a, b in zip(work[r], work[column])]
    return [row[n:] for row in work]


def _transpose(rows):
    return [list(column) for column in zip(*rows)]


def _update_dict_recursively(current, *others):
    for other in others:
        for key, value in other.items():
            if isinstance(value, dict) and isinstance(current.get(key), dict):
                _update_dict_recursively(current[key], value)
            else:
                current[key] = value


X_COLOR, Y_COLOR, Z_COLOR = GREEN_C, RED_C, BLUE_D


class VectorScene(Scene):
    """Community's VectorScene helpers for planes, vectors, labels and coordinates."""
    def __init__(self, basis_vector_stroke_width=6.0, **kwargs):
        super().__init__(**kwargs)
        self.basis_vector_stroke_width = basis_vector_stroke_width

    def add_plane(self, animate=False, **kwargs):
        plane = NumberPlane(**kwargs)
        if animate:
            self.play(Create(plane, lag_ratio=0.5))
        self.add(plane)
        return plane

    def add_axes(self, animate=False, color=WHITE):
        axes = Axes(color=color, axis_config={'unit_size': 1})
        if animate:
            self.play(Create(axes))
        self.add(axes)
        return axes

    def lock_in_faded_grid(self, dimness=0.7, axes_dimness=0.5):
        """Bake a faded plane into the background of every later frame, then clear."""
        plane = self.add_plane()
        axes = plane.get_axes()
        plane.fade(dimness)
        axes.set_color(WHITE)
        axes.fade(axes_dimness)
        self.add(axes)
        self._background_snapshots = [node for mobject in self.mobjects
                                      if not isinstance(mobject, (CameraFrame, ValueTracker))
                                      for node in [mobject.to_dict()]]
        self.clear()

    def get_vector(self, numerical_vector, **kwargs):
        numerical_vector = list(numerical_vector)
        return Arrow(self.plane.coords_to_point(0, 0), self.plane.coords_to_point(*numerical_vector[:2]),
                     buff=0, **kwargs)

    def add_vector(self, vector, color=PURE_YELLOW, animate=True, **kwargs):
        if not isinstance(vector, Arrow):
            vector = VectorArrow(vector, color=color, **kwargs)
        if animate:
            self.play(GrowArrow(vector))
        self.add(vector)
        return vector

    def write_vector_coordinates(self, vector, **kwargs):
        coords = vector.coordinate_label(**kwargs)
        self.play(Write(coords))
        return coords

    def get_basis_vectors(self, i_hat_color=X_COLOR, j_hat_color=Y_COLOR):
        return VGroup(*(VectorArrow(vect, color=color, stroke_width=self.basis_vector_stroke_width)
                        for vect, color in (([1, 0], i_hat_color), ([0, 1], j_hat_color))))

    def get_basis_vector_labels(self, **kwargs):
        i_hat, j_hat = self.get_basis_vectors()
        return VGroup(*(self.get_vector_label(vect, label, color=color, label_scale_factor=1, **kwargs)
                        for vect, label, color in ((i_hat, '\\hat{\\imath}', X_COLOR),
                                                   (j_hat, '\\hat{\\jmath}', Y_COLOR))))

    def get_vector_label(self, vector, label, at_tip=False, direction='left', rotate=False, color=None,
                         label_scale_factor=LARGE_BUFF - 0.2):
        if isinstance(label, str):
            if len(label) == 1:
                label = '\\vec{\\textbf{' + label + '}}'
            label = MathTex(label)
            label.set_color(vector.get_color() if color is None else color)
        label.scale(label_scale_factor)
        label.add_background_rectangle()
        if at_tip:
            vect = Vector(vector.get_vector())
            length = math.hypot(*vect)
            label.next_to(vector.get_end(), vect / length if length else RIGHT, buff=SMALL_BUFF)
        else:
            angle = vector.get_angle()
            if not rotate:
                label.rotate(-angle, about_point=ORIGIN)
            if direction == 'left':
                label.shift(-Vector(label.get_bottom()) + 0.1 * UP)
            else:
                label.shift(-Vector(label.get_top()) + 0.1 * DOWN)
            label.rotate(angle, about_point=ORIGIN)
            label.shift((Vector(vector.get_end()) - Vector(vector.get_start())) / 2)
        return label

    def label_vector(self, vector, label, animate=True, **kwargs):
        label = self.get_vector_label(vector, label, **kwargs)
        if animate:
            self.play(Write(label, run_time=1))
        self.add(label)
        return label

    def position_x_coordinate(self, x_coord, x_line, vector):
        x_coord.next_to(x_line, -_sign(list(vector)[1]) * UP)
        x_coord.set_color(X_COLOR)
        return x_coord

    def position_y_coordinate(self, y_coord, y_line, vector):
        y_coord.next_to(y_line, _sign(list(vector)[0]) * RIGHT)
        y_coord.set_color(Y_COLOR)
        return y_coord

    def coords_to_vector(self, vector, coords_start=2 * RIGHT + 2 * UP, clean_up=True):
        starting_mobjects = list(self.mobjects)
        vector = list(vector)
        array = Matrix([[value] for value in vector])
        array.shift(coords_start)
        arrow = VectorArrow(vector)
        x_line = Line(ORIGIN, vector[0] * RIGHT)
        y_line = Line(x_line.get_end(), arrow.get_end())
        x_line.set_color(X_COLOR)
        y_line.set_color(Y_COLOR)
        mob_matrix = array.get_mob_matrix()
        x_coord, y_coord = mob_matrix[0][0], mob_matrix[1][0]
        self.play(Write(array, run_time=1))
        self.wait()
        self.play(ApplyFunction(lambda x: self.position_x_coordinate(x, x_line, vector), x_coord))
        self.play(Create(x_line))
        self.play(ApplyFunction(lambda y: self.position_y_coordinate(y, y_line, vector), y_coord),
                  FadeOut(array.get_brackets()))
        self.play(Create(y_line))
        self.play(Create(arrow))
        self.wait()
        if clean_up:
            self.clear()
            self.add(*starting_mobjects)

    def vector_to_coords(self, vector, integer_labels=True, clean_up=True):
        starting_mobjects = list(self.mobjects)
        show_creation = False
        if isinstance(vector, Arrow):
            arrow = vector
            vector = list(arrow.get_end())[:2]
        else:
            vector = list(vector)
            arrow = VectorArrow(vector)
            show_creation = True
        array = arrow.coordinate_label(integer_labels=integer_labels)
        x_line = Line(ORIGIN, vector[0] * RIGHT)
        y_line = Line(x_line.get_end(), arrow.get_end())
        x_line.set_color(X_COLOR)
        y_line.set_color(Y_COLOR)
        x_coord, y_coord = array.get_entries()[0], array.get_entries()[1]
        x_coord_start = self.position_x_coordinate(x_coord.copy(), x_line, vector)
        y_coord_start = self.position_y_coordinate(y_coord.copy(), y_line, vector)
        brackets = array.get_brackets()
        if show_creation:
            self.play(Create(arrow))
        self.play(Create(x_line), Write(x_coord_start), run_time=1)
        self.play(Create(y_line), Write(y_coord_start), run_time=1)
        self.wait()
        self.play(Transform(x_coord_start, x_coord, lag_ratio=0), Transform(y_coord_start, y_coord, lag_ratio=0),
                  Write(brackets, run_time=1))
        self.wait()
        self.remove(x_coord_start, y_coord_start, brackets)
        self.add(array)
        if clean_up:
            self.clear()
            self.add(*starting_mobjects)
        return array, x_line, y_line

    def show_ghost_movement(self, vector):
        if isinstance(vector, Arrow):
            vector = Vector(vector.get_end()) - Vector(vector.get_start())
        else:
            vector = Vector((list(vector) + [0])[:3])
        x_max = int(config.frame_x_radius + abs(vector[0]))
        y_max = int(config.frame_y_radius + abs(vector[1]))
        dots = VGroup(*(Dot(x * RIGHT + y * UP) for x in range(-x_max, x_max) for y in range(-y_max, y_max)))
        dots.set_fill(BLACK, opacity=0)
        dots_halfway = dots.copy().shift(vector / 2).set_fill(WHITE, 1)
        dots_end = dots.copy().shift(vector)
        self.play(Transform(dots, dots_halfway, rate_func=rush_into))
        self.play(Transform(dots, dots_end, rate_func=rush_from))
        self.remove(dots)


def _sign(value):
    return (value > 0) - (value < 0)


class LinearTransformationScene(VectorScene):
    """Community's LinearTransformationScene: planes, basis vectors and matrix animations."""
    def __init__(self, include_background_plane=True, include_foreground_plane=True,
                 background_plane_kwargs=None, foreground_plane_kwargs=None, show_coordinates=False,
                 show_basis_vectors=True, basis_vector_stroke_width=6, i_hat_color=X_COLOR,
                 j_hat_color=Y_COLOR, leave_ghost_vectors=False, **kwargs):
        super().__init__(**kwargs)
        self.include_background_plane = include_background_plane
        self.include_foreground_plane = include_foreground_plane
        self.show_coordinates = show_coordinates
        self.show_basis_vectors = show_basis_vectors
        self.basis_vector_stroke_width = basis_vector_stroke_width
        self.i_hat_color, self.j_hat_color = ManimColor(i_hat_color), ManimColor(j_hat_color)
        self.leave_ghost_vectors = leave_ghost_vectors
        self.background_plane_kwargs = {'color': GREY, 'axis_config': {'color': GREY},
                                        'background_line_style': {'stroke_color': GREY, 'stroke_width': 1}}
        self.ghost_vectors = VGroup()
        self.foreground_plane_kwargs = {'x_range': [-config.frame_width, config.frame_width, 1.0],
                                        'y_range': [-config.frame_width, config.frame_width, 1.0],
                                        'faded_line_ratio': 1}
        self.update_default_configs((self.foreground_plane_kwargs, self.background_plane_kwargs),
                                    (foreground_plane_kwargs, background_plane_kwargs))

    @staticmethod
    def update_default_configs(default_configs, passed_configs):
        for default_config, passed_config in zip(default_configs, passed_configs):
            if passed_config is not None:
                _update_dict_recursively(default_config, passed_config)

    def setup(self):
        if hasattr(self, 'has_already_setup'):
            return
        self.has_already_setup = True
        self.background_mobjects, self.foreground_mobjects = [], []
        self.transformable_mobjects, self.moving_vectors = [], []
        self.transformable_labels, self.moving_mobjects = [], []
        self.background_plane = NumberPlane(**self.background_plane_kwargs)
        if self.show_coordinates:
            self.background_plane.add_coordinates()
        if self.include_background_plane:
            self.add_background_mobject(self.background_plane)
        if self.include_foreground_plane:
            self.plane = NumberPlane(**self.foreground_plane_kwargs)
            self.add_transformable_mobject(self.plane)
        if self.show_basis_vectors:
            self.basis_vectors = self.get_basis_vectors(i_hat_color=self.i_hat_color, j_hat_color=self.j_hat_color)
            self.moving_vectors += list(self.basis_vectors)
            self.i_hat, self.j_hat = self.basis_vectors
            self.add(self.basis_vectors)

    def add_special_mobjects(self, mob_list, *mobs_to_add):
        for mobject in mobs_to_add:
            if mobject not in mob_list:
                mob_list.append(mobject)
                self.add(mobject)

    def add_background_mobject(self, *mobjects):
        self.add_special_mobjects(self.background_mobjects, *mobjects)

    def add_foreground_mobject(self, *mobjects):
        self.add_special_mobjects(self.foreground_mobjects, *mobjects)

    def add_transformable_mobject(self, *mobjects):
        self.add_special_mobjects(self.transformable_mobjects, *mobjects)

    def add_moving_mobject(self, mobject, target_mobject=None):
        mobject.target = target_mobject
        self.add_special_mobjects(self.moving_mobjects, mobject)

    def get_ghost_vectors(self):
        return self.ghost_vectors

    def get_unit_square(self, color=PURE_YELLOW, opacity=0.3, stroke_width=3):
        square = self.square = Rectangle(color=color, width=self.plane.get_x_unit_size(),
                                         height=self.plane.get_y_unit_size(), stroke_color=color,
                                         stroke_width=stroke_width, fill_color=color, fill_opacity=opacity)
        square.move_to(self.plane.coords_to_point(0, 0), DL)
        return square

    def add_unit_square(self, animate=False, **kwargs):
        square = self.get_unit_square(**kwargs)
        if animate:
            self.play(DrawBorderThenFill(square), Animation(Group(*self.moving_vectors)))
        self.add_transformable_mobject(square)
        self.bring_to_front(*self.moving_vectors)
        self.square = square
        return self

    def add_vector(self, vector, color=PURE_YELLOW, animate=False, **kwargs):
        vector = super().add_vector(vector, color=color, animate=animate, **kwargs)
        self.moving_vectors.append(vector)
        return vector

    def write_vector_coordinates(self, vector, **kwargs):
        coords = super().write_vector_coordinates(vector, **kwargs)
        self.add_foreground_mobject(coords)
        return coords

    def add_transformable_label(self, vector, label, transformation_name='L', new_label=None, **kwargs):
        label_mob = self.label_vector(vector, label, **kwargs)
        label_mob.target_text = new_label if new_label else f'{transformation_name}({label_mob.get_tex_string()})'
        label_mob.vector = vector
        label_mob.kwargs = {key: value for key, value in kwargs.items() if key != 'animate'}
        self.transformable_labels.append(label_mob)
        return label_mob

    def add_title(self, title, scale_factor=1.5, animate=False):
        if not isinstance(title, Mobject):
            title = Tex(title).scale(scale_factor)
        title.to_edge(UP)
        title.add_background_rectangle()
        if animate:
            self.play(Write(title))
        self.add_foreground_mobject(title)
        self.title = title
        return self

    def get_matrix_transformation(self, matrix):
        return self.get_transposed_matrix_transformation(_transpose(_matrix_rows(matrix)))

    def get_transposed_matrix_transformation(self, transposed_matrix):
        rows = _matrix_rows(transposed_matrix)
        if len(rows) == 2:
            rows = [rows[0] + [0.0], rows[1] + [0.0], [0.0, 0.0, 1.0]]
        def transform(point):
            point = (list(point) + [0, 0, 0])[:3]
            return Vector([sum(point[i] * rows[i][j] for i in range(3)) for j in range(3)])
        return transform

    def get_piece_movement(self, pieces):
        v_pieces = [piece for piece in pieces if isinstance(piece, VMobject)]
        start = VGroup(*v_pieces)
        target = VGroup(*(mob.target for mob in v_pieces))
        if self.leave_ghost_vectors and start.children:
            self.ghost_vectors.add(start.copy().fade(0.7))
            self.add(self.ghost_vectors[-1])
        return Transform(start, target, lag_ratio=0)

    def get_moving_mobject_movement(self, func):
        for m in self.moving_mobjects:
            if m.target is None:
                m.target = m.copy()
            m.target.move_to(func(m.get_center()))
        return self.get_piece_movement(self.moving_mobjects)

    def get_vector_movement(self, func):
        for v in self.moving_vectors:
            v.target = VectorArrow(func(v.get_end()), color=v.get_color())
            norm = math.hypot(*list(v.target.get_end())[:2])
            if norm < 0.1:
                v.target.get_tip().scale(norm)
        return self.get_piece_movement(self.moving_vectors)

    def get_transformable_label_movement(self):
        for label in self.transformable_labels:
            label.target = self.get_vector_label(label.vector.target, label.target_text, **label.kwargs)
        return self.get_piece_movement(self.transformable_labels)

    def apply_matrix(self, matrix, **kwargs):
        self.apply_transposed_matrix(_transpose(_matrix_rows(matrix)), **kwargs)

    def apply_inverse(self, matrix, **kwargs):
        self.apply_matrix(_matrix_inverse(matrix), **kwargs)

    def apply_transposed_matrix(self, transposed_matrix, **kwargs):
        func = self.get_transposed_matrix_transformation(transposed_matrix)
        if 'path_arc' not in kwargs:
            kwargs['path_arc'] = (angle_of_vector(func(RIGHT)) + angle_of_vector(func(UP)) - PI / 2) / 2
        self.apply_function(func, **kwargs)

    def apply_inverse_transpose(self, t_matrix, **kwargs):
        t_inv = _transpose(_matrix_inverse(_transpose(_matrix_rows(t_matrix))))
        self.apply_transposed_matrix(t_inv, **kwargs)

    def apply_nonlinear_transformation(self, function, **kwargs):
        self.plane.prepare_for_nonlinear_transform()
        self.apply_function(function, **kwargs)

    def apply_function(self, function, added_anims=(), **kwargs):
        kwargs.setdefault('run_time', 3)
        anims = ([ApplyPointwiseFunction(function, t_mob) for t_mob in self.transformable_mobjects] +
                 [self.get_vector_movement(function), self.get_transformable_label_movement(),
                  self.get_moving_mobject_movement(function)] +
                 [Animation(f_mob) for f_mob in self.foreground_mobjects] + list(added_anims))
        self.play(*anims, **kwargs)


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
    def _point_rows(self):
        return [[float(self.position[0]), float(self.position[1]), 0.0]]

    def set_points(self, points):
        row = list(_point_rows_of(points)[0])
        return self.set_value(complex(row[0], row[1]))

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


def _mat_mul3(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _camera_rotation_matrix(phi, theta, gamma):
    """Community's ThreeDCamera.generate_rotation_matrix for sampled values."""
    result = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    for matrix in (rotation_about_z(-theta - 90 * DEGREES),
                   rotation_matrix(-phi, RIGHT),
                   rotation_about_z(gamma)):
        result = _mat_mul3(matrix, result)
    return result


class ThreeDCamera(PreviewConfig):
    """Community's ThreeDCamera: orientation trackers and perspective projection.

    The frame dict stays the plain PreviewConfig shape; phi/theta/gamma/zoom/
    focal_distance live in ValueTrackers so move_camera animates them."""

    _EXTRA_ATTRS = {'phi', 'theta', 'gamma', 'zoom', 'focal_distance', 'shading_factor',
                    'default_distance', 'light_source_start_point', 'light_source',
                    'should_apply_shading', 'exponential_projection', 'max_allowable_norm',
                    'phi_tracker', 'theta_tracker', 'gamma_tracker', 'zoom_tracker',
                    'focal_distance_tracker', 'rotation_matrix', 'fixed_orientation_mobjects',
                    'fixed_in_frame_mobjects', '_frame_center', '_orientation_key_count',
                    '_custom_orientation_centers'}

    def __init__(self, focal_distance=20.0, shading_factor=0.2, default_distance=5.0,
                 light_source_start_point=9 * DOWN + 7 * LEFT + 10 * OUT,
                 should_apply_shading=True, exponential_projection=False,
                 phi=0, theta=-90 * DEGREES, gamma=0, zoom=1, frame_center=ORIGIN, **kwargs):
        super().__init__(**kwargs)
        for name, value in dict(focal_distance=focal_distance, shading_factor=shading_factor,
                                default_distance=default_distance, phi=phi, theta=theta,
                                gamma=gamma, zoom=zoom).items():
            NumberLine._real(value, 'Camera ' + name)
            object.__setattr__(self, name, float(value))
        light = Vector(light_source_start_point)
        if not all(math.isfinite(v) for v in light):
            raise ValueError('Camera light source must be finite')
        object.__setattr__(self, 'light_source_start_point', list(light))
        object.__setattr__(self, 'light_source', VectorizedPoint(light))
        object.__setattr__(self, '_frame_center', VectorizedPoint(frame_center))
        object.__setattr__(self, 'should_apply_shading', bool(should_apply_shading))
        object.__setattr__(self, 'exponential_projection', bool(exponential_projection))
        object.__setattr__(self, 'max_allowable_norm', 3 * self.frame_width)
        for name, value in dict(phi_tracker=self.phi, theta_tracker=self.theta,
                                focal_distance_tracker=self.focal_distance,
                                gamma_tracker=self.gamma, zoom_tracker=self.zoom).items():
            object.__setattr__(self, name, ValueTracker(value))
        # id(member) -> callable returning the orientation reference center.
        object.__setattr__(self, 'fixed_orientation_mobjects', {})
        object.__setattr__(self, 'fixed_in_frame_mobjects', set())
        self.reset_rotation_matrix()

    def __setattr__(self, name, value):
        if name == 'frame_center':
            self._frame_center.move_to(value)
            return
        if name in self._EXTRA_ATTRS:
            object.__setattr__(self, name, value)
            return
        super().__setattr__(name, value)

    @property
    def frame_center(self):
        return self._frame_center.get_center()

    @frame_center.setter
    def frame_center(self, point):
        self._frame_center.move_to(point)

    def get_value_trackers(self):
        return [self.phi_tracker, self.theta_tracker, self.focal_distance_tracker,
                self.gamma_tracker, self.zoom_tracker]

    def get_phi(self):
        return self.phi_tracker.get_value()

    def get_theta(self):
        return self.theta_tracker.get_value()

    def get_focal_distance(self):
        return self.focal_distance_tracker.get_value()

    def get_gamma(self):
        return self.gamma_tracker.get_value()

    def get_zoom(self):
        return self.zoom_tracker.get_value()

    def set_phi(self, value):
        self.phi_tracker.set_value(value)

    def set_theta(self, value):
        self.theta_tracker.set_value(value)

    def set_focal_distance(self, value):
        self.focal_distance_tracker.set_value(value)

    def set_gamma(self, value):
        self.gamma_tracker.set_value(value)

    def set_zoom(self, value):
        self.zoom_tracker.set_value(value)

    def reset_rotation_matrix(self):
        self.rotation_matrix = self.generate_rotation_matrix()

    def get_rotation_matrix(self):
        return self.rotation_matrix

    def generate_rotation_matrix(self):
        return _camera_rotation_matrix(self.get_phi(), self.get_theta(), self.get_gamma())

    def project_points(self, points):
        """Community's rotate-then-perspective project; returns plain lists."""
        frame_center = Vector(self.frame_center)
        focal_distance, zoom = self.get_focal_distance(), self.get_zoom()
        rot = self.get_rotation_matrix()
        result = []
        for point in points:
            rotated = _apply_rows(rot, Vector(point) - frame_center)
            if self.exponential_projection:
                factor = (math.exp(rotated[2] / focal_distance) if rotated[2] >= 0
                          else focal_distance / (focal_distance - rotated[2]))
            else:
                factor = (1e6 if focal_distance - rotated[2] < 0
                          else focal_distance / (focal_distance - rotated[2]))
            result.append([rotated[0] * factor * zoom, rotated[1] * factor * zoom, rotated[2]])
        return result

    def project_point(self, point):
        return self.project_points([point])[0]

    def add_fixed_orientation_mobjects(self, *mobjects, use_static_center_func=False, center_func=None):
        if center_func is not None and not callable(center_func):
            raise TypeError('center_func must be callable')
        for mobject in mobjects:
            if not isinstance(mobject, Mobject):
                raise TypeError('Fixed-orientation registration expects Mobjects')
            if center_func is not None:
                func = center_func
                # User centers may follow other mobjects, so frames are never reused.
                object.__setattr__(self, '_custom_orientation_centers', True)
            elif use_static_center_func:
                point = list(mobject.get_center())
                func = lambda point=point: point
            else:
                func = mobject.get_center
            for member in mobject.get_family():
                self.fixed_orientation_mobjects[id(member)] = func
                member._fixed_orientation = True
                member._fixed_orientation_key = id(member)

    def remove_fixed_orientation_mobjects(self, *mobjects):
        for mobject in mobjects:
            for member in mobject.get_family():
                self.fixed_orientation_mobjects.pop(id(member), None)
                member.__dict__.pop('_fixed_orientation', None)
                member.__dict__.pop('_fixed_orientation_key', None)

    def add_fixed_in_frame_mobjects(self, *mobjects):
        for mobject in mobjects:
            if not isinstance(mobject, Mobject):
                raise TypeError('Fixed-in-frame registration expects Mobjects')
            for member in mobject.get_family():
                self.fixed_in_frame_mobjects.add(id(member))
                member._fixed_in_frame = True

    def remove_fixed_in_frame_mobjects(self, *mobjects):
        for mobject in mobjects:
            for member in mobject.get_family():
                self.fixed_in_frame_mobjects.discard(id(member))
                member.__dict__.pop('_fixed_in_frame', None)


class ThreeDScene(Scene):
    """Community's ThreeDScene: roots are projected to 2D bezier snapshots."""
    camera_class = ThreeDCamera

    def __init__(self, camera_class=None, ambient_camera_rotation=None,
                 default_angled_camera_orientation_kwargs=None, **kwargs):
        self.ambient_camera_rotation = ambient_camera_rotation
        self.default_angled_camera_orientation_kwargs = (
            {'phi': 70 * DEGREES, 'theta': -135 * DEGREES}
            if default_angled_camera_orientation_kwargs is None
            else dict(default_angled_camera_orientation_kwargs))
        if camera_class is not None:
            self.camera_class = camera_class
        super().__init__(**kwargs)

    def set_camera_orientation(self, phi=None, theta=None, gamma=None, zoom=None,
                               focal_distance=None, frame_center=None, **kwargs):
        if phi is not None:
            self.camera.set_phi(phi)
        if theta is not None:
            self.camera.set_theta(theta)
        if focal_distance is not None:
            self.camera.set_focal_distance(focal_distance)
        if gamma is not None:
            self.camera.set_gamma(gamma)
        if zoom is not None:
            self.camera.set_zoom(zoom)
        if frame_center is not None:
            self.camera.frame_center = frame_center

    def move_camera(self, phi=None, theta=None, gamma=None, zoom=None, focal_distance=None,
                    frame_center=None, added_anims=(), **kwargs):
        anims = []
        for value, tracker in ((phi, self.camera.phi_tracker), (theta, self.camera.theta_tracker),
                               (focal_distance, self.camera.focal_distance_tracker),
                               (gamma, self.camera.gamma_tracker), (zoom, self.camera.zoom_tracker)):
            if value is not None:
                anims.append(tracker.animate.set_value(value))
        if frame_center is not None:
            anims.append(self.camera._frame_center.animate.move_to(frame_center))
        if anims or added_anims:
            self.play(*anims, *added_anims, **kwargs)
        # Community drops the frame center afterwards; it is never drawn.
        if frame_center is not None:
            self.remove(self.camera._frame_center)

    def _camera_tracker(self, about):
        trackers = {'theta': self.camera.theta_tracker, 'phi': self.camera.phi_tracker,
                    'gamma': self.camera.gamma_tracker}
        tracker = trackers.get(str(about).lower())
        if tracker is None:
            raise ValueError('Invalid ambient rotation angle.')
        return tracker

    def begin_ambient_camera_rotation(self, rate=0.02, about='theta'):
        NumberLine._real(rate, 'Camera rotation rate')
        tracker = self._camera_tracker(about)
        def rotate(m, dt):
            return tracker.increment_value(rate * dt)
        rotate._camera_updater = True  # Edits only the tracker (see _static_frames_safe).
        tracker.add_updater(rotate)
        self.add(tracker)

    def stop_ambient_camera_rotation(self, about='theta'):
        tracker = self._camera_tracker(about)
        tracker.clear_updaters()
        self.remove(tracker)

    def begin_3dillusion_camera_rotation(self, rate=1, origin_phi=None, origin_theta=None):
        NumberLine._real(rate, 'Camera rotation rate')
        if origin_theta is None:
            origin_theta = self.camera.theta_tracker.get_value()
        if origin_phi is None:
            origin_phi = self.camera.phi_tracker.get_value()
        theta_progress = ValueTracker(0)

        def update_theta(m, dt):
            theta_progress.increment_value(dt * rate)
            return m.set_value(origin_theta + 0.2 * math.sin(theta_progress.get_value()))

        update_theta._camera_updater = True
        self.camera.theta_tracker.add_updater(update_theta)
        self.add(self.camera.theta_tracker)
        phi_progress = ValueTracker(0)

        def update_phi(m, dt):
            phi_progress.increment_value(dt * rate)
            return m.set_value(origin_phi + 0.1 * math.cos(phi_progress.get_value()) - 0.1)

        update_phi._camera_updater = True
        self.camera.phi_tracker.add_updater(update_phi)
        self.add(self.camera.phi_tracker)

    def stop_3dillusion_camera_rotation(self):
        self.camera.theta_tracker.clear_updaters()
        self.remove(self.camera.theta_tracker)
        self.camera.phi_tracker.clear_updaters()
        self.remove(self.camera.phi_tracker)

    def add_fixed_orientation_mobjects(self, *mobjects, **kwargs):
        self.add(*mobjects)
        self.camera.add_fixed_orientation_mobjects(*mobjects, **kwargs)

    def remove_fixed_orientation_mobjects(self, *mobjects):
        self.camera.remove_fixed_orientation_mobjects(*mobjects)

    def add_fixed_in_frame_mobjects(self, *mobjects):
        self.add(*mobjects)
        self.camera.add_fixed_in_frame_mobjects(*mobjects)

    def remove_fixed_in_frame_mobjects(self, *mobjects):
        self.camera.remove_fixed_in_frame_mobjects(*mobjects)

    def set_to_default_angled_camera_orientation(self, **kwargs):
        config_ = dict(self.default_angled_camera_orientation_kwargs)
        config_.update(kwargs)
        self.set_camera_orientation(**config_)

    def get_moving_mobjects(self, *animations):
        moving = super().get_moving_mobjects(*animations)
        camera_mobjects = self.camera.get_value_trackers() + [self.camera._frame_center]
        if any(member in moving for member in camera_mobjects):
            return self.mobjects
        return moving

    def _static_frames_safe(self, animations=()):
        return (not getattr(self.camera, '_custom_orientation_centers', False) and
                super()._static_frames_safe(animations))

    def capture(self, overrides=None, *, advance_time=True):
        count = len(self.frames)
        super().capture(overrides, advance_time=advance_time)
        if len(self.frames) > count:
            self.frames[-1]['camera']['three_d'] = self._three_d_camera(overrides)

    def _three_d_camera(self, overrides):
        """The sampled camera the renderer projects this frame's world leaves with."""
        camera = self.camera
        def tracked(tracker):
            states = overrides.get(tracker) if overrides else None
            return float(states[0]['position'][0] if states else tracker.get_value())
        states = overrides.get(camera._frame_center) if overrides else None
        if states:
            frame_center = Vector(states[0]['position']) + Vector(states[0]['geometry_center'])
        else:
            frame_center = Vector(camera.frame_center)
        return {'phi': tracked(camera.phi_tracker), 'theta': tracked(camera.theta_tracker),
                'gamma': tracked(camera.gamma_tracker), 'zoom': tracked(camera.zoom_tracker),
                'focal_distance': tracked(camera.focal_distance_tracker),
                'frame_center': [float(v) for v in frame_center],
                'light_source': [float(v) for v in camera.light_source.get_center()],
                'shading': bool(camera.should_apply_shading),
                'exponential': bool(camera.exponential_projection)}

    def _root_frame_data(self, root, overrides):
        """Flatten a root into world-space leaves; the renderer projects them.

        Path leaves become identity-pose bezierpaths (line/arrow keep their type
        and endpoints); text, formulas and images keep their glyphs and gain an
        ``anchor3d`` world point. Static geometry is therefore identical across
        camera moves and pools. Fixed-orientation leaves carry their reference
        ``orient_center`` and z_index_as_group leaves their root's
        ``depth_center``; the renderer sorts, shades and projects (Community's
        ThreeDCamera)."""
        roots = self._root_states(root, overrides)
        camera = self.camera
        leaves = []

        def orientation_center(node, points):
            if node.get('_fixed_center') is not None:
                return [float(v) for v in node['_fixed_center']]
            func = camera.fixed_orientation_mobjects.get(node.get('_fixed_orientation_key'))
            if func is not None:
                return [float(v) for v in func()]
            return list(_bbox_center(points)) if points else [0.0, 0.0, 0.0]

        def emit_path(node, world_map, opacity, group):
            kind = node['type']
            out = dict(node)
            out['children'] = []
            out['opacity'] = opacity
            if world_map is None and kind == 'bezierpath':
                # Identity pose: the stored curves already are world points.
                world = None
            else:
                paths = _path_subpaths(node, include_pending=False)
                pending = (node.get('vertices') or []) if (kind == 'bezierpath' or
                           (kind == 'polyline' and len(node.get('vertices') or []) == 1)) else []
                mapping = world_map or (lambda point: [point[0], point[1], point[2] if len(point) > 2 else 0])
                out['curves'] = [[mapping(point) for point in curve] for path in paths for curve in path]
                out['vertices'] = [mapping(point) for point in pending]
                out.pop('subpath_lengths', None)
                if len(paths) > 1:
                    out['subpath_lengths'] = [len(path) for path in paths]
                if kind in ('line', 'arrow'):
                    for key in ('start', 'end', 'shaft_start', 'shaft_end'):
                        if node.get(key) is not None:
                            out[key] = mapping(node[key])
                world = True
            if kind not in ('line', 'arrow'):
                out['type'] = 'bezierpath'
            out['position'], out['angle'], out['geometry_scale'] = [0, 0, 0], 0, 1
            out['geometry_center'] = [0, 0, 0]
            if node.get('_fixed_orientation'):
                points = [point for curve in out.get('curves') or () for point in curve]
                out['orient_center'] = orientation_center(node, points + list(out.get('vertices') or ()))
            # The lookup key is an object id: meaningless (and unstable) in frames.
            out.pop('_fixed_orientation_key', None)
            leaves.append(out)
            group.append(out)

        def emit_leaf(node, world_map, opacity, group):
            out = dict(node)
            out['opacity'] = opacity
            gc = node.get('geometry_center') or [0, 0, 0]
            anchor = list(world_map(gc)) if world_map else [gc[0], gc[1], gc[2] if len(gc) > 2 else 0]
            out['anchor3d'] = anchor
            out['position'] = [anchor[i] - (gc[i] if i < len(gc) else 0) for i in range(3)]
            if node['type'] in ('text', 'mathtex') and not node.get('_fixed_orientation'):
                # Community's text is a planar object: export the world images of the glyph
                # map's x and y directions, which the renderer projects like any geometry.
                (ga, gb), (gc_, gd) = _glyph_matrix(node)
                ge, gf = node.get('glyph_depth') or (0, 0)
                base = [gc[0], gc[1], gc[2] if len(gc) > 2 else 0]
                image = world_map or (lambda point: list(point))
                origin = list(image(base))
                out['plane3d'] = [[a - b for a, b in zip(image([base[0] + x, base[1] + y, base[2] + z]), origin)]
                                  for x, y, z in ((ga, gc_, ge), (gb, gd, gf))]
            if node.get('_fixed_orientation'):
                out['orient_center'] = orientation_center(node, [anchor])
            out.pop('_fixed_orientation_key', None)
            leaves.append(out)
            group.append(out)

        def identity(node):
            return (not node.get('angle') and node.get('geometry_scale', 1) == 1 and
                    not any(node.get('position') or ()))

        def walk(node, parent_map, opacity, group):
            if identity(node):
                world_map = parent_map
            else:
                pose, _ = _snapshot_pose(node)
                world_map = pose if parent_map is None else (lambda point, pose=pose: parent_map(pose(point)))
            node_opacity = opacity * node.get('opacity', 1)
            kind = node['type']
            if kind in _PATH_TYPES:
                emit_path(node, world_map, node_opacity, group)
                for child in node.get('children', []):
                    walk(child, world_map, node_opacity, group)
            elif kind in ('vgroup', 'mobject', 'valuetracker'):
                for child in node.get('children', []):
                    walk(child, world_map, node_opacity, group)
            else:
                emit_leaf(node, world_map, node_opacity, group)

        for root in roots:
            group = []
            walk(root, None, 1, group)
            if any(leaf.get('_z_index_as_group') for leaf in group):
                # Community's z_index_group reference: the root's world bounds center.
                points = [point for leaf in group for point in
                          ([leaf['anchor3d']] if 'anchor3d' in leaf else
                           [p for curve in leaf.get('curves') or () for p in curve] +
                           list(leaf.get('vertices') or ()))]
                center = list(_bbox_center(points)) if points else [0, 0, 0]
                for leaf in group:
                    if leaf.get('_z_index_as_group'):
                        leaf['depth_center'] = center
        return leaves


def _linspace(start, stop, count):
    """np.linspace equivalent: count samples inclusive of both endpoints."""
    if count == 1:
        return [float(start)]
    step = (stop - start) / (count - 1)
    return [start + i * step for i in range(count)]


class ThreeDVMobject(VMobject):
    """Community's ThreeDVMobject: a VMobject shaded by the 3D camera."""
    def __init__(self, shade_in_3d=True, **kwargs):
        super().__init__(shade_in_3d=shade_in_3d, **kwargs)


class Surface(VGroup):
    """Community's parametric Surface: a checkerboard grid of face cells.

    Faces are built flat in (u, v) space then mapped through ``func`` with
    apply_function, exactly like Community; ``func`` returns a 3-vector and is
    excluded from frame serialization."""
    _frame_excluded = ('_func',)

    MAX_SURFACE_FACES = 10000

    def __init__(self, func, u_range=(0, 1), v_range=(0, 1), resolution=32,
                 surface_piece_config=None, fill_color=BLUE_D, fill_opacity=1.0,
                 checkerboard_colors=(BLUE_D, BLUE_E), stroke_color=LIGHT_GREY,
                 stroke_width=0.5, should_make_jagged=False,
                 pre_function_handle_to_anchor_scale_factor=0.00001, **kwargs):
        if not callable(func):
            raise TypeError('Surface func must be callable')
        for name, values in (('u_range', u_range), ('v_range', v_range)):
            if (len(values) != 2 or
                    not all(isinstance(v, _REAL) and not isinstance(v, bool) and math.isfinite(v)
                            for v in values)):
                raise ValueError(name + ' must be two finite numbers')
        self.u_range, self.v_range = list(u_range), list(v_range)
        super().__init__(fill_color=fill_color, fill_opacity=fill_opacity,
                         stroke_color=stroke_color, stroke_width=stroke_width, **kwargs)
        if isinstance(resolution, bool):
            raise ValueError('Surface resolution must be positive integers')
        if isinstance(resolution, numbers.Integral):
            u_res = v_res = int(resolution)
        else:
            try:
                u_res, v_res = resolution
            except (TypeError, ValueError):
                raise ValueError('Surface resolution must be an integer or a pair') from None
        if (u_res < 1 or v_res < 1 or not isinstance(u_res, numbers.Integral)
                or not isinstance(v_res, numbers.Integral)):
            raise ValueError('Surface resolution must be positive integers')
        if u_res * v_res > self.MAX_SURFACE_FACES:
            raise ValueError('Surface resolution exceeds 10000 faces')
        self.resolution = resolution
        self.surface_piece_config = dict(surface_piece_config or {})
        self.checkerboard_colors = (checkerboard_colors if checkerboard_colors is False
                                    else [_paint(color) for color in checkerboard_colors])
        self.should_make_jagged = bool(should_make_jagged)
        self.pre_function_handle_to_anchor_scale_factor = pre_function_handle_to_anchor_scale_factor
        self.list_of_faces = []
        self._func = func
        self._setup_in_uv_space()
        self.apply_function(lambda p: func(p[0], p[1]))
        if self.should_make_jagged:
            self.make_jagged()

    def func(self, u, v):
        return self._func(u, v)

    def _get_u_values_and_v_values(self):
        if isinstance(self.resolution, numbers.Integral) and not isinstance(self.resolution, bool):
            u_res = v_res = int(self.resolution)
        else:
            u_res, v_res = self.resolution
        return (_linspace(self.u_range[0], self.u_range[1], int(u_res) + 1),
                _linspace(self.v_range[0], self.v_range[1], int(v_res) + 1))

    def _setup_in_uv_space(self):
        u_values, v_values = self._get_u_values_and_v_values()
        faces = VGroup()
        self.list_of_faces = []
        for i in range(len(u_values) - 1):
            for j in range(len(v_values) - 1):
                u1, u2 = u_values[i:i + 2]
                v1, v2 = v_values[j:j + 2]
                face = ThreeDVMobject(**self.surface_piece_config)
                face.set_points_as_corners(
                    [[u1, v1, 0], [u2, v1, 0], [u2, v2, 0], [u1, v2, 0], [u1, v1, 0]])
                face.u_index, face.v_index = i, j
                face.u1, face.u2, face.v1, face.v2 = u1, u2, v1, v2
                self.list_of_faces.append(face)
        # One bulk add: per-face adds recompute family bounds quadratically.
        faces.add(*self.list_of_faces)
        faces.set_fill(color=self.fill_color, opacity=self.fill_opacity)
        faces.set_stroke(color=self.stroke_color, width=self.stroke_width,
                         opacity=self.stroke_opacity)
        self.add(*faces)
        if self.checkerboard_colors:
            self.set_fill_by_checkerboard(*self.checkerboard_colors)

    def set_fill_by_checkerboard(self, *colors, opacity=None):
        """Alternate face fills by (u_index + v_index) % len(colors)."""
        n_colors = len(colors)
        if n_colors == 0:
            raise ValueError('set_fill_by_checkerboard needs at least one color')
        for face in self.list_of_faces:
            face.set_fill(colors[(face.u_index + face.v_index) % n_colors], opacity=opacity)
        return self

    def set_fill_by_value(self, axes=None, colorscale=None, axis=2, **kwargs):
        """Community's value-gradient fill: pivot interpolation along an axis.

        Without an axes (or one without point_to_coords) the raw coordinate of
        each face's midpoint is used and the pivots span the surface's own
        extent along ``axis``."""
        if 'colors' in kwargs and colorscale is None:
            colorscale = kwargs.pop('colors')
            if kwargs:
                raise ValueError('Unsupported keyword argument(s): ' + ', '.join(map(str, kwargs)))
        if kwargs:
            raise ValueError('Unsupported keyword argument(s): ' + ', '.join(map(str, kwargs)))
        if colorscale is None:
            return self
        colorscale_list = list(colorscale)
        if not colorscale_list:
            raise ValueError('colorscale needs at least one color')
        if isinstance(colorscale_list[0], tuple) and len(colorscale_list[0]) == 2:
            new_colors = [_paint(color) for color, _ in colorscale_list]
            pivots = [float(pivot) for _, pivot in colorscale_list]
        else:
            new_colors = [_paint(color) for color in colorscale_list]
            ranges = [getattr(axes, name, None) for name in ('x_range', 'y_range', 'z_range')]
            current_range = ranges[axis]
            if current_range is not None:
                pivot_min, pivot_max = current_range[0], current_range[1]
            else:
                points = [mob.get_midpoint()[axis]
                          for mob in self.family_members_with_points()]
                pivot_min, pivot_max = (min(points), max(points)) if points else (0, 0)
            pivots = _linspace(pivot_min, pivot_max, len(new_colors))
        for mob in self.family_members_with_points():
            point = mob.get_midpoint()
            axis_value = (axes.point_to_coords(point)[axis]
                          if axes is not None and hasattr(axes, 'point_to_coords')
                          else point[axis])
            if axis_value <= pivots[0]:
                mob.set_color(new_colors[0], family=False)
            elif axis_value >= pivots[-1]:
                mob.set_color(new_colors[-1], family=False)
            else:
                for i, pivot in enumerate(pivots):
                    if pivot > axis_value:
                        alpha = min((axis_value - pivots[i - 1]) / (pivots[i] - pivots[i - 1]), 1)
                        mob.set_color(interpolate_color(new_colors[i - 1], new_colors[i], alpha),
                                      family=False)
                        break
        return self


class Sphere(Surface):
    """Community's parametric sphere (u: azimuth, v: polar angle)."""
    def __init__(self, center=ORIGIN, radius=1, resolution=None,
                 u_range=(0, TAU), v_range=(0, PI), **kwargs):
        NumberLine._real(radius, 'Sphere radius', positive=True)
        self.radius = radius
        super().__init__(self.func, resolution=(24, 12) if resolution is None else resolution,
                         u_range=u_range, v_range=v_range, **kwargs)
        self.shift(center)

    def func(self, u, v):
        return [self.radius * math.cos(u) * math.sin(v),
                self.radius * math.sin(u) * math.sin(v),
                -self.radius * math.cos(v)]


class Dot3D(Sphere):
    """A small sphere used as a 3D marker, like Community's Dot3D."""
    def __init__(self, point=ORIGIN, radius=DEFAULT_DOT_RADIUS, color=WHITE,
                 resolution=(8, 8), **kwargs):
        super().__init__(center=point, radius=radius, resolution=resolution, **kwargs)
        self.set_color(color)


class Cube(VGroup):
    """Community's cube: six flipped/shifted/reoriented Square faces."""
    def __init__(self, side_length=2, fill_opacity=0.75, fill_color=BLUE,
                 stroke_width=0, **kwargs):
        NumberLine._real(side_length, 'Cube side length', positive=True)
        self.side_length = side_length
        super().__init__(fill_color=fill_color, fill_opacity=fill_opacity,
                         stroke_width=stroke_width, **kwargs)
        self.generate_points()

    def generate_points(self):
        # Community's init_colors applies the cube's fill/stroke to the faces.
        for vect in IN, OUT, LEFT, RIGHT, UP, DOWN:
            face = Square(side_length=self.side_length, fill_color=self.fill_color,
                          fill_opacity=self.fill_opacity, stroke_color=self.stroke_color,
                          stroke_width=self.stroke_width, shade_in_3d=True)
            face.flip()
            face.shift(self.side_length * OUT / 2.0)
            face.apply_matrix(z_to_vector(vect))
            self.add(face)
        return self


class Prism(Cube):
    """A rectangular cuboid: a cube rescaled per axis, like Community."""
    def __init__(self, dimensions=(3, 2, 1), **kwargs):
        dims = list(dimensions)
        if len(dims) != 3 or not all(isinstance(v, _REAL) and not isinstance(v, bool)
                                     and math.isfinite(v) and v > 0 for v in dims):
            raise ValueError('Prism dimensions must be three positive finite numbers')
        self.dimensions = dims
        super().__init__(**kwargs)
        for dim, value in enumerate(dims):
            self.rescale_to_fit(value, dim, stretch=True)


class Cone(Surface):
    """Community's cone; direction rotates via theta about Y then phi about Z."""
    def __init__(self, base_radius=1, height=1, direction=OUT, show_base=False,
                 v_range=(0, TAU), u_min=0, checkerboard_colors=False, **kwargs):
        NumberLine._real(base_radius, 'Cone base radius', positive=True)
        NumberLine._real(height, 'Cone height', positive=True)
        self.direction = Vector(direction)
        if not all(math.isfinite(v) for v in self.direction) or _norm(self.direction) == 0:
            raise ValueError('Cone direction must be finite and nonzero')
        self.theta = PI - math.atan(base_radius / height)
        super().__init__(self.func, v_range=v_range,
                         u_range=(u_min, math.hypot(base_radius, height)),
                         checkerboard_colors=checkerboard_colors, **kwargs)
        self.new_height = height
        self._current_theta = 0
        self._current_phi = 0
        self.base_circle = Circle(radius=base_radius, color=self.fill_color,
                                  fill_opacity=self.fill_opacity, stroke_width=0)
        self.base_circle.shift(height * IN)
        self._set_start_and_end_attributes(self.direction)
        if show_base:
            self.add(self.base_circle)
        self._rotate_to_direction()

    def func(self, u, v):
        r, phi = u, v
        return [r * math.sin(self.theta) * math.cos(phi),
                r * math.sin(self.theta) * math.sin(phi),
                r * math.cos(self.theta)]

    def get_start(self):
        return self.start_point.get_center()

    def get_end(self):
        return self.end_point.get_center()

    def _rotate_to_direction(self):
        x, y, z = self.direction
        r = math.sqrt(x * x + y * y + z * z)
        theta = math.acos(z / r) if r > 0 else 0
        if x == 0:
            if y == 0:
                phi = 0
            else:
                phi = math.atan(math.inf)
                if y < 0:
                    phi += PI
        else:
            phi = math.atan(y / x)
        if x < 0:
            phi += PI
        self.rotate(-self._current_phi, Z_AXIS, about_point=ORIGIN)
        self.rotate(-self._current_theta, Y_AXIS, about_point=ORIGIN)
        self.rotate(theta, Y_AXIS, about_point=ORIGIN)
        self.rotate(phi, Z_AXIS, about_point=ORIGIN)
        self._current_theta = theta
        self._current_phi = phi

    def set_direction(self, direction):
        self.direction = Vector(direction)
        self._rotate_to_direction()
        return self

    def get_direction(self):
        return self.direction

    def _set_start_and_end_attributes(self, direction):
        # Community multiplies the direction by its own norm here (sic).
        normalized_direction = Vector(direction) * _norm(direction)
        start = self.base_circle.get_center()
        end = start + normalized_direction * self.new_height
        self.start_point = VectorizedPoint(start)
        self.end_point = VectorizedPoint(end)
        self.add(self.start_point, self.end_point)


class Cylinder(Surface):
    """Community's cylinder with optional end-cap circles."""
    def __init__(self, radius=1, height=2, direction=OUT, v_range=(0, TAU),
                 show_ends=True, resolution=(24, 24), **kwargs):
        NumberLine._real(radius, 'Cylinder radius', positive=True)
        NumberLine._real(height, 'Cylinder height', positive=True)
        self._height = height
        self.radius = radius
        super().__init__(self.func, resolution=resolution,
                         u_range=(-self._height / 2, self._height / 2),
                         v_range=v_range, **kwargs)
        if show_ends:
            self.add_bases()
        self._current_phi = 0
        self._current_theta = 0
        self.set_direction(direction)

    def func(self, u, v):
        return [self.radius * math.cos(v), self.radius * math.sin(v), u]

    def add_bases(self):
        color, opacity = self.fill_color, self.fill_opacity
        self.base_top = Circle(radius=self.radius, color=color, fill_opacity=opacity,
                               shade_in_3d=True, stroke_width=0)
        self.base_top.shift(self.u_range[1] * IN)
        self.base_bottom = Circle(radius=self.radius, color=color, fill_opacity=opacity,
                                  shade_in_3d=True, stroke_width=0)
        self.base_bottom.shift(self.u_range[0] * IN)
        self.add(self.base_top, self.base_bottom)
        return self

    _rotate_to_direction = Cone._rotate_to_direction

    def set_direction(self, direction):
        self.direction = Vector(direction)
        self._rotate_to_direction()
        return self

    def get_direction(self):
        return self.direction


class Line3D(Cylinder):
    """A cylindrical line segment, like Community's Line3D."""
    def __init__(self, start=LEFT, end=RIGHT, thickness=0.02, color=None,
                 resolution=24, **kwargs):
        NumberLine._real(thickness, 'Line3D thickness', positive=True)
        self.thickness = thickness
        self.resolution = ((2, resolution) if isinstance(resolution, numbers.Integral)
                           and not isinstance(resolution, bool) else resolution)
        self.set_start_and_end_attrs(start, end, **kwargs)
        if color is not None:
            self.set_color(color)

    def set_start_and_end_attrs(self, start, end, **kwargs):
        rough_start = self.pointify(start)
        rough_end = self.pointify(end)
        self.vect = rough_end - rough_start
        self.length = _norm(self.vect)
        if self.length == 0:
            raise ValueError('Line3D start and end must differ')
        self.direction = normalize(self.vect)
        self.start = self.pointify(start, self.direction)
        self.end = self.pointify(end, -self.direction)
        super().__init__(height=_norm(self.vect), radius=self.thickness,
                         direction=self.direction, resolution=self.resolution, **kwargs)
        self.shift((self.start + self.end) / 2)
        return self

    def pointify(self, mob_or_point, direction=None):
        if isinstance(mob_or_point, Mobject):
            return (mob_or_point.get_center() if direction is None
                    else mob_or_point.get_boundary_point(direction))
        return Vector(mob_or_point)

    def get_start(self):
        return self.start

    def get_end(self):
        return self.end

    @classmethod
    def parallel_to(cls, line, point=ORIGIN, length=5, **kwargs):
        point = Vector(point)
        vect = normalize(line.vect)
        return cls(point + vect * length / 2, point - vect * length / 2, **kwargs)

    @classmethod
    def perpendicular_to(cls, line, point=ORIGIN, length=5, **kwargs):
        point = Vector(point)
        norm = _cross(line.vect, point - Vector(line.start))
        if _norm(norm) == 0:
            raise ValueError('Could not find the perpendicular.')
        start, end = perpendicular_bisector([line.start, line.end], norm)
        vect = normalize(Vector(end) - Vector(start))
        return cls(point + vect * length / 2, point - vect * length / 2, **kwargs)


class Arrow3D(Line3D):
    """A Line3D shaft shortened for a conical tip, like Community's Arrow3D."""
    def __init__(self, start=LEFT, end=RIGHT, thickness=0.02, height=0.3,
                 base_radius=0.08, color=WHITE, resolution=24, **kwargs):
        super().__init__(start=start, end=end, thickness=thickness, color=color,
                         resolution=resolution, **kwargs)
        self.length = _norm(self.vect)
        # Community re-runs the cylinder build with the shaft end pulled back.
        self.set_start_and_end_attrs(self.start, self.end - height * self.direction, **kwargs)
        self.cone = Cone(direction=self.direction, base_radius=base_radius,
                         height=height, **kwargs)
        self.cone.shift(Vector(end))
        self.end_point = VectorizedPoint(end)
        self.add(self.end_point, self.cone)
        self.set_color(color)

    def get_end(self):
        return self.end_point.get_center()


class Torus(Surface):
    """Community's torus: (R - r cos v)[cos u, sin u, 0] - r sin v OUT."""
    def __init__(self, major_radius=3, minor_radius=1, u_range=(0, TAU),
                 v_range=(0, TAU), resolution=None, **kwargs):
        NumberLine._real(major_radius, 'Torus major radius', positive=True)
        NumberLine._real(minor_radius, 'Torus minor radius', positive=True)
        self.R, self.r = major_radius, minor_radius
        super().__init__(self.func, u_range=u_range, v_range=v_range,
                         resolution=(24, 24) if resolution is None else resolution, **kwargs)

    def func(self, u, v):
        scale = self.R - self.r * math.cos(v)
        return [scale * math.cos(u), scale * math.sin(u), -self.r * math.sin(v)]


class Polyhedron(VGroup):
    """Community's Polyhedron: shaded polygon faces plus a Graph of Dot3D vertices.

    An updater rebuilds the faces from the current vertex centers, so moving a
    vertex (``polyhedron.graph[i]``) deforms the attached faces."""
    _frame_excluded = ('faces_config', 'graph_config', 'vertex_coords', 'vertex_indices',
                       'layout', 'faces_list', 'face_coords', 'edges')

    def __init__(self, vertex_coords, faces_list, faces_config=None, graph_config=None):
        super().__init__()
        coords = [list(_point(point, 'Polyhedron vertex')) for point in vertex_coords]
        if len(coords) > 1000:
            raise ValueError('Polyhedra are limited to 1000 vertices')
        faces = [list(face) for face in faces_list]
        for face in faces:
            if len(face) < 3 or any(isinstance(i, bool) or not isinstance(i, numbers.Integral)
                                    or not 0 <= i < len(coords) for i in face):
                raise ValueError('Polyhedron faces need three or more valid vertex indices')
        self.faces_config = dict({'fill_opacity': 0.5, 'shade_in_3d': True}, **(faces_config or {}))
        self.graph_config = dict({'vertex_type': Dot3D, 'edge_config': {'stroke_opacity': 0}},
                                 **(graph_config or {}))
        self.vertex_coords = coords
        self.vertex_indices = list(range(len(coords)))
        self.layout = dict(enumerate(coords))
        self.faces_list = faces
        self.face_coords = [[self.layout[j] for j in face] for face in faces]
        self.edges = self.get_edges(faces)
        self.faces = self.create_faces(self.face_coords)
        self.graph = Graph(self.vertex_indices, self.edges, layout=self.layout, **self.graph_config)
        self.add(self.faces, self.graph)
        self.add_updater(self.update_faces)

    def get_edges(self, faces_list):
        edges = []
        for face in faces_list:
            edges += zip(face, face[1:] + face[:1])
        return edges

    def create_faces(self, face_coords):
        return VGroup(*(Polygon(*face, **self.faces_config) for face in face_coords))

    def update_faces(self, m):
        self.faces.match_points(self.create_faces(self.extract_face_coords()))
        return self

    def extract_face_coords(self):
        layout = dict(enumerate(list(self.graph[v].get_center()) for v in self.graph.vertices))
        return [[layout[j] for j in face] for face in self.faces_list]


class Tetrahedron(Polyhedron):
    def __init__(self, edge_length=1, **kwargs):
        NumberLine._real(edge_length, 'Edge length', positive=True)
        unit = edge_length * math.sqrt(2) / 4
        super().__init__(vertex_coords=[[unit, unit, unit], [unit, -unit, -unit],
                                        [-unit, unit, -unit], [-unit, -unit, unit]],
                         faces_list=[[0, 1, 2], [3, 0, 2], [0, 1, 3], [3, 1, 2]], **kwargs)


class Octahedron(Polyhedron):
    def __init__(self, edge_length=1, **kwargs):
        NumberLine._real(edge_length, 'Edge length', positive=True)
        unit = edge_length * math.sqrt(2) / 2
        super().__init__(vertex_coords=[[unit, 0, 0], [-unit, 0, 0], [0, unit, 0],
                                        [0, -unit, 0], [0, 0, unit], [0, 0, -unit]],
                         faces_list=[[2, 4, 1], [0, 4, 2], [4, 3, 0], [1, 3, 4],
                                     [3, 5, 0], [1, 5, 3], [2, 5, 1], [0, 5, 2]], **kwargs)


class Icosahedron(Polyhedron):
    def __init__(self, edge_length=1, **kwargs):
        NumberLine._real(edge_length, 'Edge length', positive=True)
        a, b = edge_length * (1 + math.sqrt(5)) / 4, edge_length / 2
        super().__init__(
            vertex_coords=[[0, b, a], [0, -b, a], [0, b, -a], [0, -b, -a], [b, a, 0], [b, -a, 0],
                           [-b, a, 0], [-b, -a, 0], [a, 0, b], [a, 0, -b], [-a, 0, b], [-a, 0, -b]],
            faces_list=[[1, 8, 0], [1, 5, 7], [8, 5, 1], [7, 3, 5], [5, 9, 3], [8, 9, 5],
                        [3, 2, 9], [9, 4, 2], [8, 4, 9], [0, 4, 8], [6, 4, 0], [6, 2, 4],
                        [11, 2, 6], [3, 11, 2], [0, 6, 10], [10, 1, 0], [10, 7, 1],
                        [11, 7, 3], [10, 11, 7], [10, 11, 6]], **kwargs)


class Dodecahedron(Polyhedron):
    def __init__(self, edge_length=1, **kwargs):
        NumberLine._real(edge_length, 'Edge length', positive=True)
        a = edge_length * (1 + math.sqrt(5)) / 4
        b = edge_length * (3 + math.sqrt(5)) / 4
        c = edge_length / 2
        super().__init__(
            vertex_coords=[[a, a, a], [a, a, -a], [a, -a, a], [a, -a, -a], [-a, a, a], [-a, a, -a],
                           [-a, -a, a], [-a, -a, -a], [0, c, b], [0, c, -b], [0, -c, -b], [0, -c, b],
                           [c, b, 0], [-c, b, 0], [c, -b, 0], [-c, -b, 0], [b, 0, c], [-b, 0, c],
                           [b, 0, -c], [-b, 0, -c]],
            faces_list=[[18, 16, 0, 12, 1], [3, 18, 16, 2, 14], [3, 10, 9, 1, 18],
                        [1, 9, 5, 13, 12], [0, 8, 4, 13, 12], [2, 16, 0, 8, 11],
                        [4, 17, 6, 11, 8], [17, 19, 5, 13, 4], [19, 7, 15, 6, 17],
                        [6, 15, 14, 2, 11], [19, 5, 9, 10, 7], [7, 10, 3, 14, 15]], **kwargs)


def _convex_hull_3d(points, tolerance):
    """Outward triangles of the 3D convex hull (incremental; deterministic order)."""
    def sub(a, b):
        return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
    def cross(a, b):
        return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    count = len(points)
    if count < 4:
        raise ValueError('ConvexHull3D needs at least four points')
    # Initial tetrahedron: two far points, the farthest from their line, then the plane.
    i0 = 0
    i1 = max(range(count), key=lambda i: dot(sub(points[i], points[i0]), sub(points[i], points[i0])))
    line = sub(points[i1], points[i0])
    i2 = max(range(count), key=lambda i: dot(cross(line, sub(points[i], points[i0])),
                                            cross(line, sub(points[i], points[i0]))))
    normal = cross(line, sub(points[i2], points[i0]))
    i3 = max(range(count), key=lambda i: abs(dot(normal, sub(points[i], points[i0]))))
    scale = max(1.0, max(abs(v) for p in points for v in p))
    if (dot(line, line) <= (tolerance * scale) ** 2 or dot(normal, normal) <= (tolerance * scale) ** 4
            or abs(dot(normal, sub(points[i3], points[i0]))) <= tolerance * scale * math.sqrt(dot(normal, normal))):
        raise ValueError('ConvexHull3D points must not be coplanar')
    interior = [sum(points[i][k] for i in (i0, i1, i2, i3)) / 4 for k in range(3)]

    def oriented(a, b, c):
        n = cross(sub(points[b], points[a]), sub(points[c], points[a]))
        return (a, b, c) if dot(n, sub(points[a], interior)) > 0 else (a, c, b)

    def plane(face):
        a, b, c = face
        n = cross(sub(points[b], points[a]), sub(points[c], points[a]))
        length = math.sqrt(dot(n, n))
        return n, length

    faces = [oriented(*f) for f in ((i0, i1, i2), (i0, i1, i3), (i0, i2, i3), (i1, i2, i3))]
    used = {i0, i1, i2, i3}
    for index in range(count):
        if index in used:
            continue
        p = points[index]
        visible = []
        for face in faces:
            n, length = plane(face)
            if length and dot(n, sub(p, points[face[0]])) > tolerance * length * scale:
                visible.append(face)
        if not visible:
            continue
        edges = {}
        for a, b, c in visible:
            for edge in ((a, b), (b, c), (c, a)):
                edges[edge] = True
        horizon = [edge for edge in edges if (edge[1], edge[0]) not in edges]
        hidden = set(visible)
        faces = [face for face in faces if face not in hidden] + [(a, b, index) for a, b in horizon]
        used.add(index)
    return faces


class ConvexHull3D(Polyhedron):
    """The convex hull of 3D points as a Polyhedron of triangular faces."""
    def __init__(self, *points, tolerance=1e-5, **kwargs):
        NumberLine._real(tolerance, 'Hull tolerance', nonnegative=True)
        coords = [list(_point(point, 'Hull point')) for point in points]
        if len(coords) > 1000:
            raise ValueError('ConvexHull3D is limited to 1000 points')
        faces = _convex_hull_3d(coords, tolerance)
        order = {}
        for face in faces:
            for index in face:
                order.setdefault(index, len(order))
        super().__init__(vertex_coords=[coords[i] for i in order],
                         faces_list=[[order[i] for i in face] for face in faces], **kwargs)


class ThreeDAxes(Axes):
    """Community's ThreeDAxes: Axes plus a z NumberLine rotated out of the plane.

    Each axis also carries ``num_axis_pieces`` shaded shaft pieces (the shaft
    itself gets zero stroke) so the 3D camera can depth-sort them against
    surfaces, as Community's Cairo renderer does. Sheen is not modelled."""
    _AXIS_ROLES = ('x', 'y', 'z')
    _frame_excluded = ('axis_config', 'axis_labels')

    def __init__(self, x_range=(-6, 6, 1), y_range=(-5, 5, 1), z_range=(-4, 4, 1),
                 x_length=8 + 2.5, y_length=8 + 2.5, z_length=8 - 1.5,
                 z_axis_config=None, z_normal=DOWN, num_axis_pieces=20,
                 light_source=9 * DOWN + 7 * LEFT + 10 * OUT, depth=None, gloss=0.5, **kwargs):
        if (isinstance(num_axis_pieces, bool) or not isinstance(num_axis_pieces, numbers.Integral)
                or not 1 <= num_axis_pieces <= 1000):
            raise ValueError('num_axis_pieces must be an integer from 1 to 1000')
        normal, light = Vector(z_normal), Vector(light_source)
        if not all(math.isfinite(v) for v in (*normal, *light)):
            raise ValueError('ThreeDAxes z_normal and light_source must be finite')
        super().__init__(x_range=x_range, x_length=x_length, y_range=y_range,
                         y_length=y_length, **kwargs)
        self.z_range, self.z_length = z_range, z_length
        self.z_normal, self.num_axis_pieces = list(normal), int(num_axis_pieces)
        self.light_source, self.dimension = list(light), 3
        self.depth, self.gloss = depth, gloss
        z_options = self._merge_axis_options(self.axis_config, z_axis_config)
        z_options['exclude_origin_tick'] = isinstance(z_options.get('scaling') or LinearBase(), LinearBase)
        z_options['length'] = z_length
        z_axis = NumberLine(z_range, **z_options)
        z_origin = self._origin_shift([z_axis.x_min, z_axis.x_max])
        z_axis.shift(z_axis.n2p(z_origin) * -1)
        z_axis.rotate_about_number(z_origin, -PI / 2, UP)
        z_axis.rotate_about_number(z_origin, angle_of_vector(normal))
        z_axis.shift(z_axis.n2p(z_origin) * -1)
        z_axis.shift(self.x_axis.n2p(self._origin_shift([self.x_axis.x_min, self.x_axis.x_max])))
        z_axis._axes_role = 'z'
        self.add(z_axis)
        self._add_3d_pieces()

    def _add_3d_pieces(self):
        for axis in self._coordinate_axes():
            shaft = axis._part('shaft')
            pieces = VGroup(*shaft.get_pieces(self.num_axis_pieces))
            for piece in pieces:
                piece.__dict__.pop('_number_line_role', None)
            pieces._number_line_role = 'pieces'
            axis.add(pieces)
            shaft.set_stroke(width=0)
            axis.set_shade_in_3d(True)

    @property
    def z_axis(self):
        return self._axis('z')

    def get_z_axis(self):
        return self.z_axis

    def point_to_coords(self, point):
        if isinstance(point, (list, tuple)) and point and isinstance(point[0], (list, tuple)):
            if len(point) > 1000:
                raise ValueError('Axes coordinate batches are limited to 1000 points')
            return [self.point_to_coords(value) for value in point]
        point = Vector(point)
        if not all(math.isfinite(v) for v in point):
            raise ValueError('Axes point must be finite')
        axes = self._coordinate_axes()
        basis = self._basis()
        determinant = _det3(basis)
        if abs(determinant) < 1e-12:
            raise ValueError('Cannot invert collapsed or coplanar ThreeDAxes')
        shifts = [self._axis_shift(axis) for axis in axes]
        raw = [axis.scaling.inverse_function(value) for axis, value in zip(axes, shifts)]
        offset = point - self.c2p(*shifts)
        result = []
        for index in range(3):
            columns = [list(vector) for vector in basis]
            columns[index] = list(offset)
            result.append(raw[index] + _det3(columns) / determinant)
        result = [axis.scaling.function(value) for axis, value in zip(axes, result)]
        for value in result:
            NumberLine._real(value, 'Axes result')
        return result

    p2c = point_to_coords

    def get_y_axis_label(self, label, edge=UR, direction=UR, buff=SMALL_BUFF,
                         rotation=PI / 2, rotation_axis=OUT):
        return self._get_axis_label(label, self.y_axis, edge, direction, buff).rotate(
            rotation, axis=rotation_axis)

    def get_z_axis_label(self, label, edge=OUT, direction=RIGHT, buff=SMALL_BUFF,
                         rotation=PI / 2, rotation_axis=RIGHT):
        return self._get_axis_label(label, self.z_axis, edge, direction, buff).rotate(
            rotation, axis=rotation_axis)

    def get_axis_labels(self, x_label='x', y_label='y', z_label='z'):
        self.axis_labels = VGroup(self.get_x_axis_label(x_label), self.get_y_axis_label(y_label),
                                  self.get_z_axis_label(z_label))
        return self.axis_labels


def _solve3(rows, rhs):
    """Cramer's rule for a 3x3 linear system."""
    det = _det3(rows)
    result = []
    for column in range(3):
        replaced = [[rhs[r] if c == column else rows[r][c] for c in range(3)] for r in range(3)]
        result.append(_det3(replaced) / det)
    return result


def _det3(rows):
    (a, b, c), (d, e, f), (g, h, i) = (list(row)[:3] for row in rows)
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


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
        # A leaf (e.g. a whole Tex without glyph members here) maps as one member.
        members = list(mobject) or [mobject]
        animations = [animation_class(*arg_creator(submob), **kwargs) for submob in members]
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


def _graph_matrix(graph):
    """networkx.to_numpy_array (unweighted), symmetrized for directed graphs."""
    nodes = graph.nodes
    index = {node: i for i, node in enumerate(nodes)}
    matrix = [[0.0] * len(nodes) for _ in nodes]
    for u, v in graph.edges:
        matrix[index[u]][index[v]] += 1.0
        if not graph.directed and u != v:
            matrix[index[v]][index[u]] += 1.0
    if graph.directed:
        matrix = [[matrix[i][j] + matrix[j][i] for j in range(len(nodes))] for i in range(len(nodes))]
    return matrix


def _symmetric_eigen(matrix):
    """Eigenvalues and column eigenvectors of a symmetric matrix (NumPy when loaded, else Jacobi)."""
    try:
        import numpy
    except ImportError:
        numpy = None
    if numpy is not None:
        values, vectors = numpy.linalg.eig(numpy.array(matrix, dtype=float))
        return [float(v) for v in numpy.real(values)], numpy.real(vectors).tolist()
    n = len(matrix)
    a = [row[:] for row in matrix]
    v = [[float(i == j) for j in range(n)] for i in range(n)]
    for _ in range(100):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off < 1e-22:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-300:
                    continue
                theta = (a[q][q] - a[p][p]) / (2 * a[p][q])
                t = (1 if theta >= 0 else -1) / (abs(theta) + math.sqrt(theta * theta + 1))
                c = 1 / math.sqrt(t * t + 1)
                s_ = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p], a[k][q] = c * akp - s_ * akq, s_ * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k], a[q][k] = c * apk - s_ * aqk, s_ * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p], v[k][q] = c * vkp - s_ * vkq, s_ * vkp + c * vkq
    return [a[i][i] for i in range(n)], v


def _spectral_layout(graph, weight='weight', scale=2, center=None, dim=2):
    """networkx spectral_layout: the Laplacian's smallest nonzero eigenvectors."""
    scale, nodes = _layout_scale(scale), graph.nodes
    if len(nodes) > 500:
        raise ValueError('The spectral layout is limited to 500 vertices')
    if len(nodes) <= 2:
        return {node: [0.0, 0.0] for node in nodes}
    matrix = _graph_matrix(graph)
    laplacian = [[(sum(row) if i == j else 0.0) - row[j] for j in range(len(row))] for i, row in enumerate(matrix)]
    values, vectors = _symmetric_eigen(laplacian)
    order = sorted(range(len(values)), key=lambda i: values[i])[1:3]
    points = [[vectors[row][order[0]], vectors[row][order[1]]] for row in range(len(nodes))]
    return dict(zip(nodes, _rescale_layout(points, scale)))


def _dcstep(stx, fx, dx, sty, fy, dy, stp, fp, dp, brackt, stpmin, stpmax):
    """MINPACK-2 dcstep (as ported in SciPy): a safeguarded cubic/quadratic step."""
    sgnd = math.copysign(1, dp) * math.copysign(1, dx) if dp and dx else 0.0
    if fp > fx:
        theta = 3.0 * (fx - fp) / (stp - stx) + dx + dp
        s = max(abs(theta), abs(dx), abs(dp))
        gamma = s * math.sqrt((theta / s) ** 2 - (dx / s) * (dp / s))
        if stp < stx:
            gamma = -gamma
        p = (gamma - dx) + theta
        q = ((gamma - dx) + gamma) + dp
        stpc = stx + p / q * (stp - stx)
        stpq = stx + ((dx / ((fx - fp) / (stp - stx) + dx)) / 2.0) * (stp - stx)
        stpf = stpc if abs(stpc - stx) <= abs(stpq - stx) else stpc + (stpq - stpc) / 2.0
        brackt = True
    elif sgnd < 0.0:
        theta = 3 * (fx - fp) / (stp - stx) + dx + dp
        s = max(abs(theta), abs(dx), abs(dp))
        gamma = s * math.sqrt((theta / s) ** 2 - (dx / s) * (dp / s))
        if stp > stx:
            gamma = -gamma
        p = (gamma - dp) + theta
        q = ((gamma - dp) + gamma) + dx
        stpc = stp + p / q * (stx - stp)
        stpq = stp + (dp / (dp - dx)) * (stx - stp)
        stpf = stpc if abs(stpc - stp) > abs(stpq - stp) else stpq
        brackt = True
    elif abs(dp) < abs(dx):
        theta = 3 * (fx - fp) / (stp - stx) + dx + dp
        s = max(abs(theta), abs(dx), abs(dp))
        gamma = s * math.sqrt(max(0, (theta / s) ** 2 - (dx / s) * (dp / s)))
        if stp > stx:
            gamma = -gamma
        p = (gamma - dp) + theta
        q = (gamma + (dx - dp)) + gamma
        r = p / q
        if r < 0 and gamma != 0:
            stpc = stp + r * (stx - stp)
        elif stp > stx:
            stpc = stpmax
        else:
            stpc = stpmin
        stpq = stp + (dp / (dp - dx)) * (stx - stp)
        if brackt:
            stpf = stpc if abs(stpc - stp) < abs(stpq - stp) else stpq
            stpf = min(stp + 0.66 * (sty - stp), stpf) if stp > stx else max(stp + 0.66 * (sty - stp), stpf)
        else:
            stpf = stpc if abs(stpc - stp) > abs(stpq - stp) else stpq
            stpf = min(max(stpf, stpmin), stpmax)
    else:
        if brackt:
            theta = 3.0 * (fp - fy) / (sty - stp) + dy + dp
            s = max(abs(theta), abs(dy), abs(dp))
            gamma = s * math.sqrt((theta / s) ** 2 - (dy / s) * (dp / s))
            if stp > sty:
                gamma = -gamma
            p = (gamma - dp) + theta
            q = ((gamma - dp) + gamma) + dy
            stpf = stp + p / q * (sty - stp)
        elif stp > stx:
            stpf = stpmax
        else:
            stpf = stpmin
    if fp > fx:
        sty, fy, dy = stp, fp, dp
    else:
        if sgnd < 0:
            sty, fy, dy = stx, fx, dx
        stx, fx, dx = stp, fp, dp
    return stx, fx, dx, sty, fy, dy, stpf, brackt


def _dcsrch(phi, stp, f, g, ftol=1e-3, gtol=0.9, xtol=0.1, stpmin=0.0, stpmax=1e10, maxls=20):
    """MINPACK-2 dcsrch line search, as L-BFGS-B calls it. phi(stp) -> (f, g).

    Returns (stp, f, g, evaluations, ok) for the last evaluated step."""
    finit, ginit = f, g
    gtest = ftol * ginit
    width, width1 = stpmax - stpmin, (stpmax - stpmin) / 0.5
    stx, fx, gx, sty, fy, gy = 0.0, finit, ginit, 0.0, finit, ginit
    stmin, stmax = 0.0, stp + 4.0 * stp
    brackt, stage = False, 1
    for evaluations in range(1, maxls + 1):
        f, g = phi(stp)
        ftest = finit + stp * gtest
        if stage == 1 and f <= ftest and g >= 0:
            stage = 2
        if ((brackt and (stp <= stmin or stp >= stmax)) or (brackt and stmax - stmin <= xtol * stmax)
                or (stp == stpmax and f <= ftest and g <= gtest) or (stp == stpmin and (f > ftest or g >= gtest))
                or (f <= ftest and abs(g) <= gtol * -ginit)):
            return stp, f, g, evaluations, True
        if stage == 1 and f <= fx and f > ftest:
            fm, fxm, fym = f - stp * gtest, fx - stx * gtest, fy - sty * gtest
            gm, gxm, gym = g - gtest, gx - gtest, gy - gtest
            stx, fxm, gxm, sty, fym, gym, stp, brackt = _dcstep(stx, fxm, gxm, sty, fym, gym, stp, fm, gm,
                                                                brackt, stmin, stmax)
            fx, fy, gx, gy = fxm + stx * gtest, fym + sty * gtest, gxm + gtest, gym + gtest
        else:
            stx, fx, gx, sty, fy, gy, stp, brackt = _dcstep(stx, fx, gx, sty, fy, gy, stp, f, g,
                                                            brackt, stmin, stmax)
        if brackt:
            if abs(sty - stx) >= 0.66 * width1:
                stp = stx + 0.5 * (sty - stx)
            width1, width = width, abs(sty - stx)
            stmin, stmax = min(stx, sty), max(stx, sty)
        else:
            stmin, stmax = stp + 1.1 * (stp - stx), stp + 4.0 * (stp - stx)
        stp = min(max(stp, stpmin), stpmax)
        if (brackt and (stp <= stmin or stp >= stmax)) or (brackt and stmax - stmin <= xtol * stmax):
            stp = stx
        if not math.isfinite(stp):
            break
    return stp, f, g, maxls, False


def _lbfgs(function, x, history=10, pgtol=1e-5, factr=1e7, max_iterations=15000):
    """SciPy's L-BFGS-B without bounds: quasi-Newton directions from the last ten pairs,
    a first step of 1/|g|, the dcsrch line search and SciPy's stopping tests."""
    eps = 2.220446049250313e-16
    f, g = function(x)
    pairs = []
    for iteration in range(max_iterations):
        if max(abs(v) for v in g) <= pgtol:
            break
        q = g[:]
        alphas = []
        for s_, y, rho in reversed(pairs):
            a = rho * sum(si * qi for si, qi in zip(s_, q))
            alphas.append(a)
            q = [qi - a * yi for qi, yi in zip(q, y)]
        if pairs:
            s_, y, rho = pairs[-1]
            gamma = (1 / rho) / sum(yi * yi for yi in y)
            q = [gamma * qi for qi in q]
        for (s_, y, rho), a in zip(pairs, reversed(alphas)):
            b = rho * sum(yi * ri for yi, ri in zip(y, q))
            q = [ri + si * (a - b) for ri, si in zip(q, s_)]
        d = [-qi for qi in q]
        gd = sum(gi * di for gi, di in zip(g, d))
        if gd >= 0:
            pairs, d = [], [-gi for gi in g]
            gd = -sum(gi * gi for gi in g)
        dnorm = math.sqrt(sum(di * di for di in d))
        stp = min(1 / dnorm, 1e10) if iteration == 0 else 1.0
        state = {}
        def phi(step):
            trial = [xi + step * di for xi, di in zip(x, d)]
            value, gradient = function(trial)
            state.update(x=trial, f=value, g=gradient)
            return value, sum(gi * di for gi, di in zip(gradient, d))
        stp, _, _, _, ok = _dcsrch(phi, stp, f, gd)
        if not ok and not pairs:
            break
        fold, gold = f, g
        x, f, g = state['x'], state['f'], state['g']
        if max(abs(v) for v in g) <= pgtol:
            break
        if fold - f <= factr * eps * max(abs(fold), abs(f), 1):
            break
        s_ = [stp * di for di in d]
        y = [gn - go for gn, go in zip(g, gold)]
        dr = sum(yi * si for yi, si in zip(y, s_))
        if dr > eps * (-gd * stp):
            pairs.append((s_, y, 1 / dr))
            if len(pairs) > history:
                pairs.pop(0)
    return x


def _kamada_kawai_layout(graph, dist=None, pos=None, weight='weight', scale=2, center=None, dim=2):
    """networkx kamada_kawai_layout: shortest-path spring energy from a circular start."""
    scale, nodes = _layout_scale(scale), graph.nodes
    count = len(nodes)
    if count == 0:
        return {}
    if count > 300:
        raise ValueError('The Kamada-Kawai layout is limited to 300 vertices')
    if dist is None:
        neighbors = {node: [] for node in nodes}
        for u, v in graph.edges:
            neighbors[u].append(v)
            if not graph.directed:
                neighbors[v].append(u)
        dist = {}
        for source in nodes:
            lengths, frontier = {source: 0}, [source]
            while frontier:
                following = []
                for node in frontier:
                    for other in neighbors[node]:
                        if other not in lengths:
                            lengths[other] = lengths[node] + 1
                            following.append(other)
                frontier = following
            dist[source] = lengths
    matrix = [[float(dist.get(a, {}).get(b, 1e6)) for b in nodes] for a in nodes]
    start = _circular_layout(graph, scale=1) if pos is None else {n: list(pos[n])[:2] for n in nodes}
    invdist = [[1 / (matrix[i][j] + (1e-3 if i == j else 0)) for j in range(count)] for i in range(count)]
    meanweight = 1e-3
    def cost(vector):
        points = [(vector[2 * i], vector[2 * i + 1]) for i in range(count)]
        total, grad = 0.0, [0.0] * (2 * count)
        for i in range(count):
            for j in range(count):
                if i == j:
                    continue
                dx, dy = points[i][0] - points[j][0], points[i][1] - points[j][1]
                separation = math.hypot(dx, dy)
                offset = separation * invdist[i][j] - 1.0
                total += 0.5 * offset * offset
                factor = invdist[i][j] * offset / separation if separation else 0.0
                grad[2 * i] += factor * dx
                grad[2 * i + 1] += factor * dy
                grad[2 * j] -= factor * dx
                grad[2 * j + 1] -= factor * dy
        sx, sy = sum(p[0] for p in points), sum(p[1] for p in points)
        total += 0.5 * meanweight * (sx * sx + sy * sy)
        for i in range(count):
            grad[2 * i] += meanweight * sx
            grad[2 * i + 1] += meanweight * sy
        return total, grad
    solution = _lbfgs(cost, [value for node in nodes for value in start[node][:2]])
    points = [[solution[2 * i], solution[2 * i + 1]] for i in range(count)]
    return dict(zip(nodes, _rescale_layout(points, scale)))


class _PlanarEmbedding:
    """networkx's PlanarEmbedding half-edge structure: succ[v][w] = {'cw': .., 'ccw': ..},
    kept in networkx's insertion order (the last successor is the leftmost neighbor)."""
    def __init__(self, nodes=()):
        self.succ = {v: {} for v in nodes}

    def copy(self):
        result = _PlanarEmbedding()
        result.succ = {v: {w: dict(data) for w, data in nbrs.items()} for v, nbrs in self.succ.items()}
        return result

    def nodes(self):
        return list(self.succ)

    def __getitem__(self, v):
        return self.succ[v]

    def has_edge(self, u, v):
        return u in self.succ and v in self.succ[u]

    def neighbors_cw_order(self, v):
        succs = self.succ[v]
        if not succs:
            return
        start = next(reversed(succs))
        yield start
        current = succs[start]['cw']
        while start != current:
            yield current
            current = succs[current]['cw']

    def _add(self, u, v, data):
        self.succ.setdefault(u, {})
        self.succ.setdefault(v, {})
        if v in self.succ[u]:
            self.succ[u][v].update(data)
        else:
            self.succ[u][v] = data

    def add_half_edge(self, start, end, cw=None, ccw=None):
        succs = self.succ.get(start)
        if succs:
            leftmost = next(reversed(succs))
            if cw is not None:
                ref_ccw = succs[cw]['ccw']
                self._add(start, end, {'cw': cw, 'ccw': ref_ccw})
                succs[ref_ccw]['cw'] = end
                succs[cw]['ccw'] = end
                move = cw != leftmost
            elif ccw is not None:
                ref_cw = succs[ccw]['cw']
                self._add(start, end, {'cw': ref_cw, 'ccw': ccw})
                succs[ref_cw]['ccw'] = end
                succs[ccw]['cw'] = end
                move = True
            else:
                raise ValueError('A reference neighbor is required')
            if move:
                succs[leftmost] = succs.pop(leftmost)
        else:
            self._add(start, end, {'ccw': end, 'cw': end})

    def add_half_edge_first(self, start, end):
        succs = self.succ.get(start)
        self.add_half_edge(start, end, cw=next(reversed(succs)) if succs else None)

    def connect_components(self, v, w):
        self.add_half_edge(v, w, cw=next(reversed(self.succ[v])) if self.succ.get(v) else None)
        self.add_half_edge(w, v, cw=next(reversed(self.succ[w])) if self.succ.get(w) else None)

    def next_face_half_edge(self, v, w):
        return w, self.succ[w][v]['ccw']

    def connected_components(self):
        """networkx's connected_components (BFS sets, in their own iteration order)."""
        def bfs(source, n):
            seen, following = {source}, [source]
            while following:
                level, following = following, []
                for v in level:
                    for w in self.succ[v]:
                        if w not in seen:
                            seen.add(w)
                            following.append(w)
                    if len(seen) == n:
                        return seen
            return seen
        seen = set()
        for v in self.succ:
            if v not in seen:
                component = bfs(v, len(self.succ) - len(seen))
                seen.update(component)
                yield component


def _lr_planarity(graph):
    """networkx's check_planarity (left-right planarity test with embedding), ported
    step for step so the embedding, and so planar_layout, match networkx exactly."""
    from collections import defaultdict
    adj = {v: {} for v in graph.nodes}
    for u, v in graph.edges:
        if u != v:
            adj[u][v] = True
            adj[v][u] = True
    order = len(adj)
    size = sum(len(n) for n in adj.values()) // 2
    if order > 2 and size > 3 * order - 6:
        return None
    height, parent_edge = defaultdict(lambda: None), defaultdict(lambda: None)
    lowpt, lowpt2, nesting = {}, {}, {}
    dg = {v: {} for v in graph.nodes}
    roots, ref, side = [], defaultdict(lambda: None), defaultdict(lambda: 1)
    stack, stack_bottom, lowpt_edge, left_ref, right_ref = [], {}, {}, {}, {}
    adjs = {v: list(adj[v]) for v in adj}

    class Interval:
        __slots__ = ('low', 'high')
        def __init__(self, low=None, high=None):
            self.low, self.high = low, high
        def empty(self):
            return self.low is None and self.high is None
        def copy(self):
            return Interval(self.low, self.high)
        def conflicting(self, b):
            return not self.empty() and lowpt[self.high] > lowpt[b]

    class Pair:
        __slots__ = ('left', 'right')
        def __init__(self, left=None, right=None):
            self.left = left if left is not None else Interval()
            self.right = right if right is not None else Interval()
        def swap(self):
            self.left, self.right = self.right, self.left
        def lowest(self):
            if self.left.empty():
                return lowpt[self.right.low]
            if self.right.empty():
                return lowpt[self.left.low]
            return min(lowpt[self.left.low], lowpt[self.right.low])

    def top():
        return stack[-1] if stack else None

    def orientation(v):
        dfs, ind, skip = [v], defaultdict(int), defaultdict(bool)
        while dfs:
            v = dfs.pop()
            e = parent_edge[v]
            for w in adjs[v][ind[v]:]:
                vw = (v, w)
                if not skip[vw]:
                    if w in dg[v] or v in dg[w]:
                        ind[v] += 1
                        continue
                    dg[v][w] = True
                    lowpt[vw] = lowpt2[vw] = height[v]
                    if height[w] is None:
                        parent_edge[w] = vw
                        height[w] = height[v] + 1
                        dfs.append(v)
                        dfs.append(w)
                        skip[vw] = True
                        break
                    lowpt[vw] = height[w]
                nesting[vw] = 2 * lowpt[vw]
                if lowpt2[vw] < height[v]:
                    nesting[vw] += 1
                if e is not None:
                    if lowpt[vw] < lowpt[e]:
                        lowpt2[e] = min(lowpt[e], lowpt2[vw])
                        lowpt[e] = lowpt[vw]
                    elif lowpt[vw] > lowpt[e]:
                        lowpt2[e] = min(lowpt2[e], lowpt[vw])
                    else:
                        lowpt2[e] = min(lowpt2[e], lowpt2[vw])
                ind[v] += 1

    def add_constraints(ei, e):
        P = Pair()
        while True:
            Q = stack.pop()
            if not Q.left.empty():
                Q.swap()
            if not Q.left.empty():
                return False
            if lowpt[Q.right.low] > lowpt[e]:
                if P.right.empty():
                    P.right = Q.right.copy()
                else:
                    ref[P.right.low] = Q.right.high
                P.right.low = Q.right.low
            else:
                ref[Q.right.low] = lowpt_edge[e]
            if top() == stack_bottom[ei]:
                break
        while top().left.conflicting(ei) or top().right.conflicting(ei):
            Q = stack.pop()
            if Q.right.conflicting(ei):
                Q.swap()
            if Q.right.conflicting(ei):
                return False
            ref[P.right.low] = Q.right.high
            if Q.right.low is not None:
                P.right.low = Q.right.low
            if P.left.empty():
                P.left = Q.left.copy()
            else:
                ref[P.left.low] = Q.left.high
            P.left.low = Q.left.low
        if not (P.left.empty() and P.right.empty()):
            stack.append(P)
        return True

    def remove_back_edges(e):
        u = e[0]
        while stack and top().lowest() == height[u]:
            P = stack.pop()
            if P.left.low is not None:
                side[P.left.low] = -1
        if stack:
            P = stack.pop()
            while P.left.high is not None and P.left.high[1] == u:
                P.left.high = ref[P.left.high]
            if P.left.high is None and P.left.low is not None:
                ref[P.left.low] = P.right.low
                side[P.left.low] = -1
                P.left.low = None
            while P.right.high is not None and P.right.high[1] == u:
                P.right.high = ref[P.right.high]
            if P.right.high is None and P.right.low is not None:
                ref[P.right.low] = P.left.low
                side[P.right.low] = -1
                P.right.low = None
            stack.append(P)
        if lowpt[e] < height[u]:
            hl, hr = top().left.high, top().right.high
            ref[e] = hl if hl is not None and (hr is None or lowpt[hl] > lowpt[hr]) else hr

    def testing(v):
        dfs, ind, skip = [v], defaultdict(int), defaultdict(bool)
        while dfs:
            v = dfs.pop()
            e, skip_final = parent_edge[v], False
            for w in ordered[v][ind[v]:]:
                ei = (v, w)
                if not skip[ei]:
                    stack_bottom[ei] = top()
                    if ei == parent_edge[w]:
                        dfs.append(v)
                        dfs.append(w)
                        skip[ei] = skip_final = True
                        break
                    lowpt_edge[ei] = ei
                    stack.append(Pair(right=Interval(ei, ei)))
                if lowpt[ei] < height[v]:
                    if w == ordered[v][0]:
                        lowpt_edge[e] = lowpt_edge[ei]
                    elif not add_constraints(ei, e):
                        return False
                ind[v] += 1
            if not skip_final and e is not None:
                remove_back_edges(e)
        return True

    def sign(e):
        dfs, old = [e], defaultdict(lambda: None)
        while dfs:
            e = dfs.pop()
            if ref[e] is not None:
                dfs.append(e)
                dfs.append(ref[e])
                old[e] = ref[e]
                ref[e] = None
            else:
                side[e] *= side[old[e]]
        return side[e]

    for v in adj:
        if height[v] is None:
            height[v] = 0
            roots.append(v)
            orientation(v)
    ordered = {v: sorted(dg[v], key=lambda x, v=v: nesting[v, x]) for v in dg}
    for v in roots:
        if not testing(v):
            return None
    for u in dg:
        for w in dg[u]:
            nesting[u, w] = sign((u, w)) * nesting[u, w]
    embedding = _PlanarEmbedding(dg)
    for v in dg:
        ordered[v] = sorted(dg[v], key=lambda x, v=v: nesting[v, x])
        previous = None
        for w in ordered[v]:
            embedding.add_half_edge(v, w, ccw=previous)
            previous = w
    for root in roots:
        dfs, ind = [root], defaultdict(int)
        while dfs:
            v = dfs.pop()
            for w in ordered[v][ind[v]:]:
                ind[v] += 1
                ei = (v, w)
                if ei == parent_edge[w]:
                    embedding.add_half_edge_first(w, v)
                    left_ref[v] = right_ref[v] = w
                    dfs.append(v)
                    dfs.append(w)
                    break
                elif side[ei] == 1:
                    embedding.add_half_edge(w, v, ccw=right_ref[w])
                else:
                    embedding.add_half_edge(w, v, cw=left_ref[w])
                    left_ref[w] = v
    return embedding


def _make_bi_connected(embedding, start, out, counted):
    if (start, out) in counted:
        return []
    counted.add((start, out))
    v1, v2, face, face_set = start, out, [start], {start}
    _, v3 = embedding.next_face_half_edge(v1, v2)
    while v2 != start or v3 != out:
        if v2 in face_set:
            embedding.add_half_edge(v1, v3, ccw=v2)
            embedding.add_half_edge(v3, v1, cw=v2)
            counted.add((v2, v3))
            counted.add((v3, v1))
            v2 = v1
        else:
            face_set.add(v2)
            face.append(v2)
        v1 = v2
        v2, v3 = embedding.next_face_half_edge(v2, v3)
        counted.add((v1, v2))
    return face


def _triangulate_face(embedding, v1, v2):
    _, v3 = embedding.next_face_half_edge(v1, v2)
    _, v4 = embedding.next_face_half_edge(v2, v3)
    if v1 in (v2, v3):
        return
    while v1 != v4:
        if embedding.has_edge(v1, v3):
            v1, v2, v3 = v2, v3, v4
        else:
            embedding.add_half_edge(v1, v3, ccw=v2)
            embedding.add_half_edge(v3, v1, cw=v2)
            v1, v2, v3 = v1, v3, v4
        _, v4 = embedding.next_face_half_edge(v2, v3)


def _canonical_ordering(embedding, outer):
    from collections import defaultdict
    v1, v2 = outer[0], outer[1]
    chords, marked, ready = defaultdict(int), set(), set(outer)
    ccw_nbr, cw_nbr = {}, {}
    previous = v2
    for index in range(2, len(outer)):
        ccw_nbr[previous] = outer[index]
        previous = outer[index]
    ccw_nbr[previous] = v1
    previous = v1
    for index in range(len(outer) - 1, 0, -1):
        cw_nbr[previous] = outer[index]
        previous = outer[index]
    def outer_nbr(x, y):
        if x not in ccw_nbr:
            return cw_nbr[x] == y
        if x not in cw_nbr:
            return ccw_nbr[x] == y
        return ccw_nbr[x] == y or cw_nbr[x] == y
    def on_outer(x):
        return x not in marked and (x in ccw_nbr or x == v1)
    for v in outer:
        for nbr in embedding.neighbors_cw_order(v):
            if on_outer(nbr) and not outer_nbr(v, nbr):
                chords[v] += 1
                ready.discard(v)
    count = len(embedding.nodes())
    ordering = [None] * count
    ordering[0], ordering[1] = (v1, []), (v2, [])
    ready.discard(v1)
    ready.discard(v2)
    for k in range(count - 1, 1, -1):
        v = ready.pop()
        marked.add(v)
        wp = wq = None
        neighbors = iter(embedding.neighbors_cw_order(v))
        while True:
            nbr = next(neighbors)
            if nbr in marked:
                continue
            if on_outer(nbr):
                if nbr == v1:
                    wp = v1
                elif nbr == v2:
                    wq = v2
                elif cw_nbr[nbr] == v:
                    wp = nbr
                else:
                    wq = nbr
            if wp is not None and wq is not None:
                break
        path, nbr = [wp], wp
        while nbr != wq:
            following = embedding[v][nbr]['ccw']
            path.append(following)
            cw_nbr[nbr] = following
            ccw_nbr[following] = nbr
            nbr = following
        if len(path) == 2:
            for end in (wp, wq):
                chords[end] -= 1
                if chords[end] == 0:
                    ready.add(end)
        else:
            new_face = set(path[1:-1])
            for w in new_face:
                ready.add(w)
                for nbr in embedding.neighbors_cw_order(w):
                    if on_outer(nbr) and not outer_nbr(w, nbr):
                        chords[w] += 1
                        ready.discard(w)
                        if nbr not in new_face:
                            chords[nbr] += 1
                            ready.discard(nbr)
        ordering[k] = (v, path)
    return ordering


def _combinatorial_embedding_to_pos(embedding):
    """networkx's Chrobak-Payne straight-line drawing on an integer grid."""
    nodes = embedding.nodes()
    if len(nodes) < 4:
        return dict(zip(nodes, [(0, 0), (2, 0), (1, 1)]))
    embedding = embedding.copy()
    components = [next(iter(c)) for c in embedding.connected_components()]
    for a, b in zip(components, components[1:]):
        embedding.connect_components(a, b)
    outer, faces, visited = [], [], set()
    for v in embedding.nodes():
        for w in embedding.neighbors_cw_order(v):
            face = _make_bi_connected(embedding, v, w, visited)
            if face:
                faces.append(face)
                if len(face) > len(outer):
                    outer = face
    for face in faces:
        if face is not outer:
            _triangulate_face(embedding, face[0], face[1])
    ordering = _canonical_ordering(embedding, outer)
    (v1, _), (v2, _), (v3, _) = ordering[:3]
    dx, y = {v1: 0, v2: 1, v3: 1}, {v1: 0, v2: 0, v3: 1}
    right, left = {v1: v3, v2: None, v3: v2}, {v1: None, v2: None, v3: None}
    for k in range(3, len(ordering)):
        vk, contour = ordering[k]
        wp, wp1, wq, wq1 = contour[0], contour[1], contour[-1], contour[-2]
        multi = len(contour) > 2
        dx[wp1] += 1
        dx[wq] += 1
        span = sum(dx[x] for x in contour[1:])
        dx[vk] = (-y[wp] + span + y[wq]) // 2
        y[vk] = (y[wp] + span + y[wq]) // 2
        dx[wq] = span - dx[vk]
        if multi:
            dx[wp1] -= dx[vk]
        right[wp], right[vk] = vk, wq
        if multi:
            left[vk] = wp1
            right[wq1] = None
        else:
            left[vk] = None
    pos, remaining = {v1: (0, y[v1])}, [v1]
    while remaining:
        parent = remaining.pop()
        for tree in (left, right):
            child = tree[parent]
            if child is not None:
                pos[child] = (pos[parent][0] + dx[child], y[child])
                remaining.append(child)
    return pos


def _planar_layout(graph, scale=2, center=None, dim=2):
    scale = _layout_scale(scale)
    if not len(graph):
        return {}
    embedding = _lr_planarity(graph)
    if embedding is None:
        raise ValueError('G is not planar.')
    pos = _combinatorial_embedding_to_pos(embedding)
    nodes = embedding.nodes()
    return dict(zip(nodes, _rescale_layout([[float(c) for c in pos[v]] for v in nodes], scale)))


_GRAPH_LAYOUTS = {'circular': _circular_layout, 'shell': _shell_layout, 'spiral': _spiral_layout,
                  'partite': _partite_layout, 'random': _random_layout, 'spring': _spring_layout,
                  'tree': _tree_layout, 'spectral': _spectral_layout, 'kamada_kawai': _kamada_kawai_layout,
                  'planar': _planar_layout}


def _determine_graph_layout(graph, layout='spring', layout_scale=2, layout_config=None):
    layout_config = {} if layout_config is None else dict(layout_config)
    if isinstance(layout, dict):
        return {node: Vector(point) for node, point in layout.items()}
    if isinstance(layout, str):
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
        centers = {}  # Edges never move vertices, so each center is measured once.
        def center(vertex):
            if vertex not in centers:
                centers[vertex] = graph[vertex].get_center()
            return centers[vertex]
        for (u, v), edge in graph.edges.items():
            # Community looks up "buff"/"path_arc" in the per-edge table, so both stay 0.
            edge.set_points_by_ends(center(u), center(v), buff=0, path_arc=0)
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


def _bez3(c, t):
    s = 1 - t
    a, b, d = s * s * s, 3 * s * s * t, 3 * s * t * t
    e = t * t * t
    return tuple(a * c[0][i] + b * c[1][i] + d * c[2][i] + e * c[3][i] for i in range(3))


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
    _frame_excluded = ('_svg_shape_sources',)
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
        self._svg_shape_sources = []
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
            # The SVG transform and stroke width each shape was drawn with (Typst uses them).
            stroke = current.get('stroke')
            self._svg_shape_sources.append((mobject, transform, _svg_number(current.get('stroke-width'), 1.0)
                                            if stroke and stroke != 'none' else 0))
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


# Community 0.22's Typst: compiled by the typst package, here by typst.ts in the page. Python
# records each document it needs (typst_pending); the page compiles them and renders again.
TYPST_COMPILATION_FONT_SIZE = 10
_TYPST_TEMPLATE = ('#set page(width: auto, height: auto, margin: 0pt, fill: none)\n'
                   '#set text(size: {text_size}pt)\n{preamble}\n{body}\n')
_TYPST_SVGS = {}
_TYPST_PENDING = set()
_TYPST_LABEL = re.compile(r'^(.*)\s*:\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*$', re.DOTALL)
_TYPST_INTERNAL_ID = re.compile(r'g[0-9A-Fa-f]+')
_TYPST_DUPLICATE = '__manim_typst_dup_'
_TYPST_STROKE_SCALE = 0.5
_TYPST_LEAF_TAGS = {'circle', 'ellipse', 'image', 'line', 'path', 'polygon', 'polyline', 'rect', 'text', 'use'}


def _typst_document(code, preamble=''):
    """The compiled SVG of a Typst body, or None (requested from the page) until compiled."""
    source = _TYPST_TEMPLATE.format(text_size=TYPST_COMPILATION_FONT_SIZE, preamble=preamble, body=code)
    if len(source) > 100000:
        raise ValueError('Typst sources are limited to 100000 characters')
    svg = _TYPST_SVGS.get(source)
    if svg is None:
        if len(_TYPST_PENDING) >= 64:
            raise ValueError('Preview is limited to 64 distinct Typst documents.')
        _TYPST_PENDING.add(source)
    return svg


def _typst_placeholder(code, font_size):
    """An invisible box roughly the size of the text, until the page has compiled it."""
    width = max(1, len(re.sub(r'\s+', ' ', code).strip())) * 5
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 10"><path d="M0 0H{width}V10H0Z" '
            f'fill="#000000" fill-opacity="0"/></svg>')


def _manimgrp_preamble(target):
    target_value = 'none' if target is None else f'"{target}"'
    return f'#let manimgrp(lbl, body) = if lbl == {target_value} {{ hide(body) }} else {{ body }}'


def _svg_local_tag(element):
    return element.tag.rsplit('}', 1)[-1] if isinstance(element.tag, str) else ''


def _iter_svg_leaves(parent, transform=(1, 0, 0, 1, 0, 0), inside_defs=False):
    """Rendered SVG leaves (parent, index, element, effective transform) in drawing order."""
    for index, element in enumerate(list(parent)):
        tag = _svg_local_tag(element)
        hidden = inside_defs or tag == 'defs'
        effective = _svg_compose(transform, _svg_transform(element.get('transform')))
        if not hidden and tag in _TYPST_LEAF_TAGS:
            yield parent, index, element, effective
        yield from _iter_svg_leaves(element, effective, hidden)


def _svg_leaf_signatures(markup):
    from xml.etree import ElementTree
    root = ElementTree.fromstring(markup)
    result = []
    for _, _, element, transform in _iter_svg_leaves(root):
        attributes = tuple(sorted((k, v) for k, v in element.attrib.items() if k != 'transform'))
        result.append((_svg_local_tag(element), attributes, tuple(element.itertext()),
                       tuple(round(v, 12) for v in transform)))
    return result


def _hidden_leaf_indices(visible, probe):
    hidden, at = set(), 0
    for index, signature in enumerate(visible):
        if at < len(probe) and signature == probe[at]:
            at += 1
        else:
            hidden.add(index)
    if at != len(probe):
        raise ValueError('The MathTypst grouping probe changed visible SVG geometry instead of only hiding '
                         'captured leaves. A custom Typst show rule for `hide` may be interfering with '
                         'subexpression selection.')
    return hidden


class Typst(SVGMobject):
    """Typst markup compiled to SVG (by typst.ts in the page) and imported like Community."""
    _frame_excluded = ('_svg_shape_sources', '_label_aliases', '_svg_leaf_labels', '_typst_tracked')

    def __init__(self, typst_code, *, font_size=DEFAULT_FONT_SIZE, typst_preamble='', color=None,
                 stroke_width=None, font_paths=None, track_baselines=False, should_center=True,
                 height=None, **kwargs):
        if not isinstance(typst_code, str) or not isinstance(typst_preamble, str):
            raise TypeError('Typst expects Typst source strings')
        NumberLine._real(font_size, 'Typst font_size', positive=True)
        if font_paths:
            raise NotImplementedError('The browser preview compiles Typst with its bundled fonts only')
        self.typst_code, self.typst_preamble, self.track_baselines = typst_code, typst_preamble, bool(track_baselines)
        self._preserve_svg_stroke_widths = stroke_width is None
        labels = self.__dict__.get('_svg_leaf_labels', {})
        svg = _typst_document(typst_code, typst_preamble)
        # Until the page has compiled the document, a placeholder keeps layout going.
        self._typst_waiting = svg is None
        markup = self._labelled(svg, labels) if svg is not None else _typst_placeholder(typst_code, font_size)
        super().__init__(markup, should_center=should_center, height=height, stroke_width=stroke_width, **kwargs)
        self._svg_leaf_labels = labels
        sources = self.__dict__.pop('_svg_shape_sources', [])
        # Per shape: (index, reference size, source stroke width, reference points, baseline frame).
        self._typst_tracked = []
        for index, (mobject, transform, width) in enumerate(sources):
            if mobject not in self.children:
                continue
            a, b, c, d, e, f = transform
            frame = [[e, -f, 0], [a + e, -(b + f), 0], [c + e, -(d + f), 0]]
            self._typst_tracked.append([self.children.index(mobject), max(mobject.get_width(), mobject.get_height()),
                                        width, [list(p) for p in mobject.get_points()], frame])
        self._rebuild_label_aliases()
        color = VMobject().color if color is None else color
        # Community's init_colors: members drawn in Typst's default black (filled glyphs or
        # stroked rules) take the mobject's color; explicitly colored Typst content keeps its own.
        black = ('#000000', '#000')
        for child in self.children:
            filled = child.get_fill_opacity() > 0
            paint = child.get_fill_color() if filled else child.get_stroke_color()
            if str(paint).upper() in black:
                child.set_color(color)
        self.initial_height = self.get_height()
        self._refresh_svg_stroke_widths()
        if height is None and self.initial_height > 0:
            self.font_size = font_size

    @staticmethod
    def _labelled(markup, leaf_labels):
        """Wrap labelled leaves (MathTypst groups) and data-typst-label elements in id groups."""
        from xml.etree import ElementTree
        if not leaf_labels and 'data-typst-label' not in markup:
            return markup
        root = ElementTree.fromstring(markup)
        counts = {}
        def next_id(label):
            count = counts.get(label, 0)
            counts[label] = count + 1
            return label if count == 0 else f'{label}{_TYPST_DUPLICATE}{count}'
        if leaf_labels:
            for leaf_index, (parent, index, element, _) in enumerate(list(_iter_svg_leaves(root))):
                wrapped = element
                for label in reversed(leaf_labels.get(leaf_index, [])):
                    namespace = wrapped.tag.partition('}')[0] + '}' if '}' in wrapped.tag else ''
                    group = ElementTree.Element(f'{namespace}g', {'id': next_id(label)})
                    group.append(wrapped)
                    wrapped = group
                parent[index] = wrapped
        for element in root.iter():
            label = element.get('data-typst-label')
            if label is not None:
                element.set('id', next_id(label))
                del element.attrib['data-typst-label']
        return ElementTree.tostring(root, encoding='unicode')

    def __repr__(self):
        return f'{type(self).__name__}({self.typst_code!r})'

    @property
    def font_size(self):
        return self.get_height() / self.initial_height / SCALE_FACTOR_PER_FONT_POINT

    @font_size.setter
    def font_size(self, value):
        NumberLine._real(value, 'Typst font_size', positive=True)
        if self.get_height() > 0:
            self.scale(value / self.font_size)

    def scale(self, scale_factor, scale_stroke=False, **kwargs):
        result = super().scale(scale_factor, scale_stroke=scale_stroke, **kwargs) if scale_stroke else \
            super().scale(scale_factor, **kwargs)
        if '_typst_tracked' in self.__dict__:
            self._refresh_svg_stroke_widths()
        return result

    def _refresh_svg_stroke_widths(self):
        """Community keeps Typst's own stroke weights (fraction bars, rules) proportional to size."""
        if not self._preserve_svg_stroke_widths:
            return
        pixels_per_unit = config.pixel_width / config.frame_width
        for index, reference, width, _, _ in self._typst_tracked:
            if not width or reference <= 0 or index >= len(self.children):
                continue
            child = self.children[index]
            size = max(child.get_width(), child.get_height())
            child.set_stroke(width=width * size / reference * pixels_per_unit * _TYPST_STROKE_SCALE, family=False)

    def get_baseline_frame(self, submobject):
        """Community's (origin, right, up) of a glyph's Typst baseline frame, following the
        submobject's current placement (a least-squares affine fit of its points)."""
        entry = next((t for t in self.__dict__.get('_typst_tracked', ())
                      if t[0] < len(self.children) and self.children[t[0]] is submobject), None)
        if not self.track_baselines or entry is None:
            raise ValueError('No tracked Typst baseline frame is available for this submobject. '
                             'Construct the Typst mobject with track_baselines=True.')
        reference, current = entry[3], submobject.get_points()
        if len(reference) != len(current) or len(reference) < 3:
            raise ValueError('The stored Typst reference geometry is degenerate, so its baseline frame '
                             'cannot be recovered.')
        rows = [[p[0], p[1], 1.0] for p in reference]
        normal = [[sum(r[i] * r[j] for r in rows) for j in range(3)] for i in range(3)]
        if abs(_det3(normal)) < 1e-12:
            raise ValueError('The stored Typst reference geometry is degenerate, so its baseline frame '
                             'cannot be recovered.')
        solution = []
        for axis in range(3):
            rhs = [sum(r[i] * q[axis] for r, q in zip(rows, current)) for i in range(3)]
            solution.append(_solve3(normal, rhs))
        result = []
        for x, y, _ in entry[4]:
            result.append(Vector(sum(c * v for c, v in zip(column, (x, y, 1.0))) for column in solution))
        return tuple(result)

    @property
    def baseline_frames(self):
        if not self.track_baselines:
            return []
        return [self.get_baseline_frame(self.children[t[0]]) for t in self._typst_tracked
                if t[0] < len(self.children)]

    def _rebuild_label_aliases(self):
        aliases = {}
        for key in self.id_to_vgroup_dict:
            if key == 'root' or key.startswith('numbered_group_') or _TYPST_INTERNAL_ID.fullmatch(key):
                continue
            base = key.partition(_TYPST_DUPLICATE)[0] if _TYPST_DUPLICATE in key else key
            aliases.setdefault(base, []).append(key)
        self._label_aliases = aliases

    def _user_label_keys(self):
        return list(self._label_aliases)

    def _select_label(self, label):
        if self.__dict__.get('_typst_waiting') and label not in self._label_aliases:
            return VGroup()
        if label not in self._label_aliases:
            raise KeyError(f'No group with label {label!r} found. Available labels: {self._user_label_keys()}')
        result, seen = VGroup(), set()
        for group_id in self._label_aliases[label]:
            for member in self.id_to_vgroup_dict.get(group_id, ()):
                if id(member) not in seen:
                    seen.add(id(member))
                    result.add(member)
        return result

    def select(self, key):
        if isinstance(key, int):
            label = f'_grp-{key}'
            if label not in self._label_aliases and not self.__dict__.get('_typst_waiting'):
                raise IndexError(f'Group index {key} out of range. Available labels: {self._user_label_keys()}')
            return self._select_label(label)
        return self._select_label(key)


class MathTypst(Typst):
    """A Typst math expression ($ ... $) whose {{ body : label }} groups can be selected."""
    def __init__(self, math_expression, **kwargs):
        processed, labels = self._preprocess_groups(math_expression)
        self._group_labels = labels
        typst_code = f'$ {processed} $'
        distinct = list(dict.fromkeys(labels))
        if distinct:
            user_preamble = kwargs.get('typst_preamble', '')
            final_preamble = _manimgrp_preamble(None) + (f'\n{user_preamble}' if user_preamble else '')
            final_svg = _typst_document(typst_code, final_preamble)
            probes = {label: _typst_document(typst_code, _manimgrp_preamble(label) +
                                             (f'\n{user_preamble}' if user_preamble else ''))
                      for label in distinct}
            leaf_labels = {}
            if final_svg is not None and all(svg is not None for svg in probes.values()):
                visible = _svg_leaf_signatures(final_svg)
                for label in distinct:
                    try:
                        hidden = _hidden_leaf_indices(visible, _svg_leaf_signatures(probes[label]))
                    except ValueError as error:
                        raise ValueError(f'Could not map MathTypst group {label!r} to SVG leaves. {error}') from error
                    for index in sorted(hidden):
                        leaf_labels.setdefault(index, []).append(label)
            self._svg_leaf_labels = leaf_labels
            kwargs['typst_preamble'] = final_preamble
        super().__init__(typst_code, **kwargs)
        for label in distinct:
            self._label_aliases.setdefault(label, [])

    @staticmethod
    def _preprocess_groups(math_expr):
        """Community's {{ body : label }} rewriting into manimgrp("label", body) calls."""
        labels, auto = [], 0
        def process(expression):
            nonlocal auto
            result, i, n, in_string, depth_bracket = [], 0, len(expression), False, 0
            while i < n:
                ch = expression[i]
                if in_string:
                    result.append(ch)
                    if ch == '\\' and i + 1 < n:
                        result.append(expression[i + 1])
                        i += 2
                        continue
                    if ch == '"':
                        in_string = False
                    i += 1
                    continue
                if ch == '"':
                    in_string = True
                    result.append(ch)
                    i += 1
                    continue
                if ch == '[':
                    depth_bracket += 1
                    result.append(ch)
                    i += 1
                    continue
                if ch == ']' and depth_bracket > 0:
                    depth_bracket -= 1
                    result.append(ch)
                    i += 1
                    continue
                if depth_bracket > 0 or i + 1 >= n or ch != '{' or expression[i + 1] != '{':
                    result.append(ch)
                    i += 1
                    continue
                start = i
                i += 2
                content_start, depth, group_string, group_bracket = i, 1, False, 0
                content = None
                while i < n and depth > 0:
                    ch = expression[i]
                    if group_string:
                        if ch == '\\' and i + 1 < n:
                            i += 2
                            continue
                        if ch == '"':
                            group_string = False
                        i += 1
                        continue
                    if ch == '"':
                        group_string = True
                        i += 1
                        continue
                    if ch == '[':
                        group_bracket += 1
                        i += 1
                        continue
                    if ch == ']' and group_bracket > 0:
                        group_bracket -= 1
                        i += 1
                        continue
                    if group_bracket > 0:
                        i += 1
                        continue
                    if ch == '{' and i + 1 < n and expression[i + 1] == '{':
                        depth += 1
                        i += 2
                        continue
                    if ch == '}' and i + 1 < n and expression[i + 1] == '}':
                        depth -= 1
                        if depth == 0:
                            content = expression[content_start:i]
                            i += 2
                            break
                        i += 2
                        continue
                    i += 1
                if content is None:
                    result.append(expression[start:])
                    return ''.join(result)
                match = _TYPST_LABEL.match(content)
                if match is not None:
                    body, label = match.group(1).strip(), match.group(2)
                else:
                    body, label = content.strip(), f'_grp-{auto}'
                    auto += 1
                labels.append(label)
                result.append(f'manimgrp("{label}", {process(body)})')
            return ''.join(result)
        return process(math_expr), labels


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
        height = self.pixel_height / scale_to_resolution * config.frame_height
        self.__dict__.update(height=height, width=height * self.pixel_width / self.pixel_height)
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


class Add(Animation):
    """Add mobjects instantly; useful inside Succession (Community's zero run_time)."""
    _instant = True

    def __init__(self, *mobjects, run_time=0.0, **kwargs):
        if not mobjects or any(not isinstance(m, Mobject) for m in mobjects):
            raise TypeError('Add expects Mobjects')
        mobject = mobjects[0] if len(mobjects) == 1 else Group(*mobjects)
        super().__init__(mobject, run_time=run_time, introducer=True, **kwargs)


class ShowPartial(Animation):
    """Abstract base of partial-drawing animations, as in Community."""
    def __init__(self, mobject, **kwargs):
        if not callable(getattr(mobject, 'pointwise_become_partial', None)):
            raise TypeError(f'{type(self).__name__} only works for VMobjects.')
        super().__init__(mobject, **kwargs)

    def _get_bounds(self, alpha):
        raise NotImplementedError('Please use Create or ShowPassingFlash')


class TypeWithCursor(AddTextLetterByLetter):
    """Type a Text glyph by glyph with a cursor that follows the last shown glyph."""
    def __init__(self, text, cursor, buff=0.1, keep_cursor_y=True, leave_cursor_on=True, time_per_char=0.1,
                 reverse_rate_function=False, introducer=True, **kwargs):
        if not isinstance(cursor, Mobject):
            raise TypeError('TypeWithCursor needs a cursor Mobject')
        self.cursor, self.buff = cursor, buff
        self.keep_cursor_y, self.leave_cursor_on = keep_cursor_y, leave_cursor_on
        super().__init__(text, time_per_char=time_per_char, reverse_rate_function=reverse_rate_function,
                         introducer=introducer, **kwargs)
        text._explode()

    def begin(self, scene):
        text = self.mobject
        self.y_cursor = self.cursor.get_y()
        self.initial_y = text.get_center()[1]
        if self.keep_cursor_y:
            self.cursor.set_y(self.y_cursor)
        self.cursor.set_opacity(0)
        if self.cursor in text.children:
            text.remove(self.cursor)
        text.add(self.cursor)  # Community adds the cursor as the text's last member.
        super().begin(scene)

    def _place(self, group, index):
        *glyphs, cursor = group.children  # The cursor is the text's last member.
        for position, glyph in enumerate(glyphs):
            glyph.opacity = 1 if position < index else 0
        if index != 0:
            cursor.next_to(glyphs[index - 1], RIGHT, buff=self.buff).set_y(self.initial_y)
        else:
            cursor.move_to(glyphs[0]).set_y(self.initial_y)
        if self.keep_cursor_y:
            cursor.set_y(self.y_cursor)
        cursor.set_opacity(1)
        return group

    def sample(self, alpha):
        group = self.mobject.copy()
        # Community lists the glyphs before the cursor joins the text.
        count = len(group.children) - 1
        return [self._place(group, max(0, min(count, int(self.int_func(alpha * count))))).to_dict()]

    def sample_members(self, alpha, rate_func):
        return self.sample(rate_func(alpha))

    def finish(self, scene):
        # Community's finish interpolates to the end: the cursor follows the final glyph.
        count = len(self.mobject.children) - 1
        final = 0 if self.reverse_rate_function else count
        self._place(self.mobject, max(0, min(count, int(self.int_func(final)))))
        for glyph in self.mobject.children:
            glyph.opacity = 1
        if self.leave_cursor_on:
            self.cursor.set_opacity(1)
        else:
            self.cursor.set_opacity(0)
            self.mobject.remove(self.cursor)


class UntypeWithCursor(TypeWithCursor):
    def __init__(self, text, cursor=None, time_per_char=0.1, reverse_rate_function=True, introducer=False,
                 remover=True, **kwargs):
        super().__init__(text, cursor=cursor if cursor is not None else VectorizedPoint(),
                         time_per_char=time_per_char, reverse_rate_function=reverse_rate_function,
                         introducer=introducer, remover=remover, **kwargs)


class AnimatedBoundary(VGroup):
    """Two outline copies that redraw and fade in cycling colors, driven by an updater."""
    def __init__(self, vmobject, colors=None, max_stroke_width=3, cycle_rate=0.5, back_and_forth=True,
                 draw_rate_func=smooth, fade_rate_func=smooth, **kwargs):
        super().__init__(**kwargs)
        self.colors = list(colors) if colors is not None else [BLUE_D, BLUE_B, BLUE_E, GREY_BROWN]
        if not self.colors:
            raise ValueError('AnimatedBoundary needs at least one color')
        self.max_stroke_width, self.cycle_rate, self.back_and_forth = max_stroke_width, cycle_rate, back_and_forth
        self.draw_rate_func, self.fade_rate_func = draw_rate_func, fade_rate_func
        self.vmobject = vmobject
        self.boundary_copies = [vmobject.copy().set_style(stroke_width=0, fill_opacity=0) for _ in range(2)]
        self.add(*self.boundary_copies)
        self.total_time = 0.0
        self.add_updater(lambda m, dt: m.update_boundary_copies(dt))

    def update_boundary_copies(self, dt):
        time = self.total_time * self.cycle_rate
        growing, fading = self.children[:2]
        colors, width = self.colors, self.max_stroke_width
        index = int(time % len(colors))
        alpha = time % 1
        draw, fade = self.draw_rate_func(alpha), self.fade_rate_func(alpha)
        bounds = (1.0 - draw, 1.0) if self.back_and_forth and int(time) % 2 == 1 else (0.0, draw)
        self.full_family_become_partial(growing, self.vmobject, *bounds)
        growing.set_stroke(colors[index], width=width)
        if time >= 1:
            self.full_family_become_partial(fading, self.vmobject, 0, 1)
            fading.set_stroke(color=colors[index - 1], width=(1 - fade) * width)
        self.total_time += dt

    def full_family_become_partial(self, mob1, mob2, a, b):
        for sm1, sm2 in zip(mob1.family_members_with_points(), mob2.family_members_with_points()):
            sm1.pointwise_become_partial(sm2, a, b)
        return self


class ShowPassingFlashWithThinningStrokeWidth(AnimationGroup):
    """Stacked passing flashes whose widths thin toward the leading edge."""
    def __init__(self, vmobject, n_segments=10, time_width=0.1, remover=True, **kwargs):
        if isinstance(n_segments, bool) or not isinstance(n_segments, numbers.Integral) or not 1 <= n_segments <= 100:
            raise ValueError('n_segments must be an integer from 1 to 100')
        self.n_segments, self.time_width, self.remover = n_segments, time_width, remover
        width = vmobject.get_stroke_width()
        space = lambda a, b: [a + (b - a) * i / (n_segments - 1) for i in range(n_segments)] if n_segments > 1 else [a]
        group_options = {key: kwargs.pop(key) for key in ('run_time', 'lag_ratio') if key in kwargs}
        super().__init__(*(ShowPassingFlash(vmobject.copy().set_stroke(width=w), time_width=t, **kwargs)
                           for w, t in zip(space(0, width), space(time_width, 0))), **group_options)


class FadeTransformPieces(FadeTransform):
    """FadeTransform piece by piece: each source member ghosts onto its matching target member."""
    @staticmethod
    def _pieces(mobject, count):
        group = mobject.copy()
        pieces = list(group.children) or [group]
        if len(pieces) < count:
            # Community's add_n_more_submobjects: repeated members become faded copies.
            current = len(pieces)
            repeats = [(i * current) // count for i in range(count)]
            padded = []
            for index, piece in enumerate(pieces):
                padded.append(piece)
                padded += [piece.copy().fade(1) for _ in range(1, repeats.count(index))]
            pieces = padded
        return pieces

    def begin(self, scene):
        Animation.begin(self, scene)
        count = max(len(self.mobject.children) or 1, len(self.replacement.children) or 1)
        sources, targets = self._pieces(self.mobject, count), self._pieces(self.replacement, count)
        snapshot = lambda pieces: Group(*pieces).to_dict()
        self.start = snapshot([p.copy() for p in sources])
        self.source_end = snapshot([self._fit(s.copy(), t) for s, t in zip(sources, targets)])
        self.target_start = snapshot([self._fit(t.copy(), s) for s, t in zip(sources, targets)])
        self.target_end = snapshot([t.copy() for t in targets])


class _IsoPoint:
    __slots__ = ('pos', 'val')

    def __init__(self, pos, val):
        self.pos, self.val = pos, val


class _IsoCell:
    __slots__ = ('vertices', 'depth', 'children', 'parent', 'child_direction')

    def __init__(self, vertices, depth, parent, child_direction):
        self.vertices, self.depth, self.children = vertices, depth, []
        self.parent, self.child_direction = parent, child_direction


class _IsoTriangle:
    __slots__ = ('vertices', 'next', 'next_bisect_point', 'prev', 'visited')

    def __init__(self, vertices):
        self.vertices, self.next, self.next_bisect_point, self.prev, self.visited = vertices, None, None, None, False


def _plot_isoline(fn, pmin, pmax, min_depth=5, max_quads=10000):
    """The isosurfaces package's plot_isoline, which Community's ImplicitFunction uses: an
    adaptive quadtree, its dual triangulation and the traced zero crossings, in its order."""
    def value(pos):
        try:
            result = float(fn(pos))
        except (ZeroDivisionError, OverflowError, ValueError):
            return math.nan  # NumPy gives inf/nan here instead of raising.
        return result
    def sign(v):
        return math.nan if math.isnan(v) else (v > 0) - (v < 0)
    def point(pos):
        return _IsoPoint(pos, value(pos))
    def midpoint(a, b):
        return point(((a.pos[0] + b.pos[0]) / 2, (a.pos[1] + b.pos[1]) / 2))
    def intersect_zero(a, b):
        denom = a.val - b.val
        k1, k2 = -b.val / denom, a.val / denom
        return point((k1 * a.pos[0] + k2 * b.pos[0], k1 * a.pos[1] + k2 * b.pos[1]))
    tol = ((pmax[0] - pmin[0]) / 1000, (pmax[1] - pmin[1]) / 1000)
    def extremes(lo, hi):
        w = (hi[0] - lo[0], hi[1] - lo[1])
        return [point((lo[0] + (i & 1) * w[0], lo[1] + (i >> 1 & 1) * w[1])) for i in range(4)]
    def should_descend(cell):
        a, b = cell.vertices[0].pos, cell.vertices[-1].pos
        if b[0] - a[0] < 10 * tol[0] and b[1] - a[1] < 10 * tol[1]:
            return False
        if all(math.isnan(v.val) for v in cell.vertices):
            return False
        if any(math.isnan(v.val) for v in cell.vertices):
            return True
        first = sign(cell.vertices[0].val)
        return any(sign(v.val) != first for v in cell.vertices[1:])
    import collections
    max_cells = max(4 ** min_depth, max_quads)
    root = _IsoCell(extremes(pmin, pmax), 0, None, 0)
    queue, leaves = collections.deque([root]), 1
    while queue and leaves < max_cells:
        cell = queue.popleft()
        if cell.depth < min_depth or should_descend(cell):
            for i, vertex in enumerate(cell.vertices):
                lo = ((cell.vertices[0].pos[0] + vertex.pos[0]) / 2, (cell.vertices[0].pos[1] + vertex.pos[1]) / 2)
                hi = ((cell.vertices[-1].pos[0] + vertex.pos[0]) / 2, (cell.vertices[-1].pos[1] + vertex.pos[1]) / 2)
                cell.children.append(_IsoCell(extremes(lo, hi), cell.depth + 1, cell, i))
            queue.extend(cell.children)
            leaves += 3

    def binary_search_zero(a, b):
        while not (abs(b.pos[0] - a.pos[0]) < tol[0] and abs(b.pos[1] - a.pos[1]) < tol[1]):
            mid = midpoint(a, b)
            if mid.val == 0:
                return mid, True
            if (mid.val > 0) == (a.val > 0):
                a = mid
            else:
                b = mid
        pt = intersect_zero(a, b)
        return pt, pt.val == 0 or (sign(pt.val - a.val) == sign(b.val - pt.val) and pt.val < 1e200)

    triangles, hanging = [], {}
    def set_next(t1, t2, vpos, vneg):
        if not vpos.val > 0 >= vneg.val:
            return
        intersection, is_zero = binary_search_zero(vpos, vneg)
        if is_zero:
            t1.next_bisect_point, t1.next, t2.prev = intersection, t2, t1
    def sandwich(a, b, c):
        center, x, y = b.vertices[2], b.vertices[0], b.vertices[1]
        if center.val > 0 >= y.val:
            set_next(b, c, center, y)
        if x.val > 0 >= center.val:
            set_next(b, a, x, center)
        key = struct.pack('dd', x.pos[0] + y.pos[0], x.pos[1] + y.pos[1])
        if y.val > 0 >= x.val:
            if key in hanging:
                set_next(b, hanging.pop(key), y, x)
            else:
                hanging[key] = b
        elif y.val <= 0 < x.val:
            if key in hanging:
                set_next(hanging.pop(key), b, x, y)
            else:
                hanging[key] = b
    def add_four(a, b, c, d, center):
        four = (_IsoTriangle([a, b, center]), _IsoTriangle([b, c, center]),
                _IsoTriangle([c, d, center]), _IsoTriangle([d, a, center]))
        for i in range(4):
            sandwich(four[i], four[(i + 1) % 4], four[(i + 2) % 4])
        triangles.extend(four)
    def edge_dual(p1, p2):
        if (p1.val > 0) != (p2.val > 0):
            return midpoint(p1, p2)
        dt = 0.01
        df1 = value((p1.pos[0] * (1 - dt) + p2.pos[0] * dt, p1.pos[1] * (1 - dt) + p2.pos[1] * dt))
        df2 = value((p1.pos[0] * dt + p2.pos[0] * (1 - dt), p1.pos[1] * dt + p2.pos[1] * (1 - dt)))
        if (df1 > 0) == (df2 > 0):
            return midpoint(p1, p2)
        return intersect_zero(_IsoPoint(p1.pos, df1), _IsoPoint(p2.pos, df2))
    def face_dual(cell):
        return midpoint(cell.vertices[0], cell.vertices[-1])
    def crossing(a, b, row):
        first, second = ((1, 0), (3, 2)) if row else ((2, 0), (3, 1))
        if a.children and b.children:
            crossing(a.children[first[0]], b.children[first[1]], row)
            crossing(a.children[second[0]], b.children[second[1]], row)
        elif a.children:
            crossing(a.children[first[0]], b, row)
            crossing(a.children[second[0]], b, row)
        elif b.children:
            crossing(a, b.children[first[1]], row)
            crossing(a, b.children[second[1]], row)
        else:
            fa, fb = face_dual(a), face_dual(b)
            i, j = (2, 0) if row else (0, 1)
            k, l = (3, 1) if row else (2, 3)
            if a.depth < b.depth:
                add_four(b.vertices[i], fb, b.vertices[j], fa, edge_dual(b.vertices[i], b.vertices[j]))
            else:
                add_four(a.vertices[k], fb, a.vertices[l], fa, edge_dual(a.vertices[k], a.vertices[l]))
    def inside(cell):
        if cell.children:
            for child in cell.children:
                inside(child)
            crossing(cell.children[0], cell.children[1], True)
            crossing(cell.children[2], cell.children[3], True)
            crossing(cell.children[0], cell.children[2], False)
            crossing(cell.children[1], cell.children[3], False)
    inside(root)
    curves = []
    for triangle in triangles:
        if not triangle.visited and triangle.next is not None:
            curve, start, closed = [], triangle, False
            while triangle.prev is not None:
                triangle = triangle.prev
                if triangle is start:
                    closed = True
                    break
            while triangle is not None and not triangle.visited:
                if triangle.next_bisect_point is not None:
                    curve.append(triangle.next_bisect_point)
                triangle.visited = True
                triangle = triangle.next
            if closed:
                curve.append(curve[0])
            curves.append([v.pos for v in curve])
    return curves


class ImplicitFunction(VMobject):
    """The curve func(x, y) = 0, traced by the isosurfaces quadtree (as Community) and smoothed."""
    def __init__(self, func, x_range=None, y_range=None, min_depth=5, max_quads=1500, use_smoothing=True, **kwargs):
        if not callable(func):
            raise TypeError('ImplicitFunction needs a callable func(x, y)')
        super().__init__(**kwargs)
        self.function, self.min_depth, self.max_quads, self.use_smoothing = func, min_depth, max_quads, use_smoothing
        self.x_range = list(x_range or [-config.frame_width / 2, config.frame_width / 2])
        self.y_range = list(y_range or [-config.frame_height / 2, config.frame_height / 2])
        if isinstance(min_depth, bool) or not isinstance(min_depth, numbers.Integral) or not 0 <= min_depth <= 7:
            raise ValueError('min_depth must be an integer from 0 to 7 in the browser preview')
        if isinstance(max_quads, bool) or not isinstance(max_quads, numbers.Integral) or not 1 <= max_quads <= 20000:
            raise ValueError('max_quads must be an integer from 1 to 20000 in the browser preview')
        curves = [c for c in _plot_isoline(lambda u: func(u[0], u[1]), (self.x_range[0], self.y_range[0]),
                                           (self.x_range[1], self.y_range[1]), min_depth, max_quads) if c]
        for curve in curves:
            self.start_new_path((curve[0][0], curve[0][1], 0))
            self.add_points_as_corners([(x, y, 0) for x, y in curve[1:]])
        if curves and use_smoothing:
            self.make_smooth()

    @property
    def underlying_function(self):
        return self.function


class _LabelCell:
    """A polylabel search cell, ordered by distance like Community's Cell."""
    def __init__(self, x, y, h, distance):
        self.x, self.y, self.h, self.d = x, y, h, distance(x, y)
        self.p = self.d + h * math.sqrt(2)

    def __lt__(self, other):
        return self.d < other.d


def _polylabel(rings, precision=0.01):
    """Community's polylabel (manim.utils.polylabel): a pole of inaccessibility and its distance."""
    import heapq
    segments = [(a, b) for ring in rings for a, b in zip(ring, ring[1:])]
    def inside(x, y):
        for (x0, y0), (x1, y1) in segments:
            if min(x0, x1) <= x <= max(x0, x1) and min(y0, y1) <= y <= max(y0, y1) and \
                    abs((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)) <= 1e-8:
                return True
        crossings = 0
        for (x0, y0), (x1, y1) in segments:
            if (y0 > y) != (y1 > y) and x < (x1 - x0) / (y1 - y0) * (y - y0) + x0:
                crossings += 1
        return crossings % 2 == 1
    def distance(x, y):
        best = math.inf
        for (ax, ay), (bx, by) in segments:
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy))) if dx or dy else 0
            best = min(best, math.hypot(ax + dx * t - x, ay + dy * t - y))
        return best if inside(x, y) else -best
    points = [p for ring in rings for p in ring]
    min_x, min_y = min(p[0] for p in points), min(p[1] for p in points)
    width, height = max(p[0] for p in points) - min_x, max(p[1] for p in points) - min_y
    size = min(width, height)
    if size <= 0:
        return (min_x, min_y), 0.0
    h = size / 2.0
    queue = []
    ys = [min_y + i * size for i in range(math.ceil(height / size - 1e-12))]
    xs = [min_x + i * size for i in range(math.ceil(width / size - 1e-12))]
    for y in ys:
        for x in xs:
            heapq.heappush(queue, _LabelCell(x + h, y + h, h, distance))
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in segments:
        factor = x0 * y1 - x1 * y0
        area += factor / 2
        cx, cy = cx + (x0 + x1) * factor, cy + (y0 + y1) * factor
    best = _LabelCell(cx / (6 * area), cy / (6 * area), 0, distance) if area else _LabelCell(min_x, min_y, 0, distance)
    box = _LabelCell(min_x + width / 2, min_y + height / 2, 0, distance)
    if box.d > best.d:
        best = box
    steps = 0
    while queue and steps < 200000:
        cell = heapq.heappop(queue)
        steps += 1
        if cell.d > best.d:
            best = cell
        if cell.p - best.d > precision:
            half = cell.h / 2.0
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                heapq.heappush(queue, _LabelCell(cell.x + dx * half, cell.y + dy * half, half, distance))
    return (best.x, best.y), best.d


class LabeledPolygram(Polygram):
    """A polygram with a Label at its pole of inaccessibility."""
    def __init__(self, *vertex_groups, label, precision=0.01, label_config=None, box_config=None,
                 frame_config=None, **kwargs):
        super().__init__(*vertex_groups, **kwargs)
        self.label = Label(label=label, label_config=label_config, box_config=box_config, frame_config=frame_config)
        rings = []
        for group in vertex_groups:
            ring = [(float(p[0]), float(p[1])) for p in group]
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            rings.append(ring)
        center, self.radius = _polylabel(rings, precision)
        self.pole = Vector((center[0], center[1], 0))
        self.label.move_to(self.pole)
        self.add(self.label)


class ChangeSpeed(AnimationGroup):
    """Re-time an animation with speed factors at chosen progress nodes (Community's ChangeSpeed)."""
    dt, is_changing_dt = 0, False

    def __init__(self, anim, speedinfo, rate_func=None, affects_speed_updaters=True, **kwargs):
        if not isinstance(anim, (Animation, AnimationGroup)):
            raise TypeError('ChangeSpeed expects an animation')
        speedinfo = dict(speedinfo)
        if any(isinstance(v, bool) or not isinstance(v, _REAL) or not v >= 0 for v in speedinfo.values()):
            raise ValueError('ChangeSpeed speed factors must be nonnegative')
        if any(not 0 <= k <= 1 for k in speedinfo):
            raise ValueError('ChangeSpeed nodes must lie between 0 and 1')
        speedinfo.setdefault(0, 1)
        if 1 not in speedinfo:
            speedinfo[1] = sorted(speedinfo.items())[-1][1]
        self.speedinfo = dict(sorted(speedinfo.items()))
        self.anim, self.affects_speed_updaters = anim, affects_speed_updaters
        self.rate_func_inner = anim.rate_func if rate_func is None else rate_func
        self.segments, current, previous, init = [], 0.0, 0.0, self.speedinfo[0]
        for node, final in list(self.speedinfo.items())[1:]:
            if init + final <= 0:
                raise ValueError('ChangeSpeed cannot stay at zero speed between two nodes')
            duration = node - previous
            length = 2 / (init + final) * duration
            self.segments.append((current, length, duration, previous, init, final))
            current += length
            previous, init = node, final
        self.scaled_total_time = current
        super().__init__(anim, run_time=self.scaled_total_time * anim.run_time, **kwargs)
        self._progress = 0.0

    def _remap(self, t):
        x = self.rate_func_inner(t) * self.scaled_total_time
        for start, length, duration, node, init, final in self.segments:
            if x <= start + length or (start, length) == self.segments[-1][:2]:
                u = (x - start) / duration if duration else 0
                return ((final ** 2 - init ** 2) * u * u / 4 + init * u) * duration + node
        return 1.0

    def prepare(self, scene):
        if self.affects_speed_updaters:
            ChangeSpeed.is_changing_dt = True
        self._progress = 0.0
        super().prepare(scene)

    def states(self, alpha, rate_func=None):
        progress = 1.0 if alpha >= 1 else min(1.0, self._remap(max(0.0, alpha)))
        if self.affects_speed_updaters:
            ChangeSpeed.dt = (progress - self._progress) * self.anim.run_time
        self._progress = progress
        return self.anim.states(progress, lambda t: t) if isinstance(self.anim, Animation) else \
            self.anim.states(progress, lambda t: t)

    def finish(self, scene):
        ChangeSpeed.is_changing_dt = False
        super().finish(scene)

    @classmethod
    def add_updater(cls, mobject, update_function, index=None, call_updater=False):
        if 'dt' in inspect.signature(update_function).parameters:
            return mobject.add_updater(lambda mob, dt: update_function(mob, cls.dt if cls.is_changing_dt else dt),
                                       index=index, call_updater=call_updater)
        return mobject.add_updater(update_function, index=index, call_updater=call_updater)


DEFAULT_POINT_DENSITY_1D, DEFAULT_POINT_DENSITY_2D = 10, 25
_POINT_CLOUD_LIMIT = 100000


class PMobject(Mobject):
    """Community's point cloud: colored points drawn as squares of stroke_width pixels
    (at Community's 1920-pixel default width), unaffected by scaling like the Cairo camera."""
    def __init__(self, stroke_width=DEFAULT_STROKE_WIDTH, **kwargs):
        super().__init__(stroke_width=stroke_width, **kwargs)
        self._type = 'pointcloud'
        self.cloud, self.cloud_colors, self.cloud_opacities = [], [], []

    def reset_points(self):
        self.cloud, self.cloud_colors, self.cloud_opacities = [], [], []
        return self

    def add_points(self, points, rgbas=None, color=None, alpha=1.0):
        points = [Vector(p) for p in points]
        if len(self.cloud) + len(points) > _POINT_CLOUD_LIMIT:
            raise ValueError('Point clouds are limited to 100000 points')
        if any(not all(math.isfinite(v) for v in p) or p[2] for p in points):
            raise ValueError('Point cloud points must be finite XY coordinates')
        if rgbas is None:
            colors = [ManimColor(color) if color else ManimColor(self.color)] * len(points)
            alphas = [alpha] * len(points)
        else:
            rgbas = [list(r) for r in rgbas]
            if len(rgbas) != len(points):
                raise ValueError('points and rgbas must have same length')
            colors, alphas = [ManimColor(tuple(float(v) for v in r[:3])) for r in rgbas], [float(r[3]) for r in rgbas]
        # Points are stored in this object's local frame.
        local = self._world_to_local([list(p) for p in points])
        self.cloud += [[p[0], p[1]] for p in local]
        self.cloud_colors += colors
        self.cloud_opacities += alphas
        return self

    def _world_to_local(self, points):
        if not self.cloud and not self.children:
            self.position = [0, 0, 0]
            self.angle, self.geometry_scale = 0, 1
            return points
        center = self._geometry_center()
        cos, sin = math.cos(-self.angle), math.sin(-self.angle)
        scale = self.geometry_scale or 1
        result = []
        for x, y, _ in points:
            dx, dy = x - self.position[0] - center[0], y - self.position[1] - center[1]
            result.append([center[0] + (dx * cos - dy * sin) / scale, center[1] + (dx * sin + dy * cos) / scale, 0])
        return result

    def get_points(self):
        return self._points_to_world([[x, y, 0] for x, y in self.cloud])

    def get_num_points(self):
        return len(self.cloud)

    def set_points(self, points):
        return self.reset_points().add_points(points)

    def set_color(self, color=PURE_YELLOW, family=True):
        color = ManimColor(color)
        self.cloud_colors = [color] * len(self.cloud)
        super().set_color(color, family)
        if family:
            for child in self.children:
                child.set_color(color)
        return self

    def get_color(self):
        return self.cloud_colors[0] if self.cloud_colors else self.color

    def get_stroke_width(self):
        return self.stroke_width

    def set_stroke_width(self, width, family=True):
        self._validate_width(width)
        self.stroke_width = width
        if family:
            for child in self.children:
                if isinstance(child, PMobject):
                    child.set_stroke_width(width)
        return self

    def set_color_by_gradient(self, *colors):
        self.cloud_colors = list(color_gradient(colors, len(self.cloud)))
        return self

    def set_colors_by_radial_gradient(self, center=None, radius=1, inner_color=WHITE, outer_color=BLACK):
        center = self.get_center() if center is None else Vector(center)
        self.cloud_colors = [interpolate_color(inner_color, outer_color, math.dist(p[:2], center[:2]) / radius)
                             for p in self.get_points()]
        return self

    def set_opacity(self, opacity, family=True):
        self._validate_opacity(opacity)
        self.cloud_opacities = [opacity] * len(self.cloud)
        return super().set_opacity(opacity, family)

    def _keep(self, indices):
        self.cloud = [self.cloud[i] for i in indices]
        self.cloud_colors = [self.cloud_colors[i] for i in indices]
        self.cloud_opacities = [self.cloud_opacities[i] for i in indices]

    def filter_out(self, condition):
        points = self.get_points()
        self._keep([i for i, p in enumerate(points) if not condition(Vector(p))])
        return self

    def thin_out(self, factor=5):
        self._keep(range(0, len(self.cloud), max(1, int(factor))))
        return self

    def sort_points(self, function=lambda p: p[0]):
        points = self.get_points()
        self._keep(sorted(range(len(points)), key=lambda i: function(Vector(points[i]))))
        return self

    def fade_to(self, color, alpha, family=True):
        self.cloud_colors = [interpolate_color(c, color, alpha) for c in self.cloud_colors]
        for child in self.children:
            child.fade_to(color, alpha, family)
        return self

    def point_from_proportion(self, alpha):
        if not self.cloud:
            raise ValueError('The point cloud has no points')
        return Vector(self.get_points()[int(alpha * (len(self.cloud) - 1))])

    def pointwise_become_partial(self, mobject, a, b):
        count = len(mobject.cloud)
        lower, upper = int(a * count), int(b * count)
        self.cloud = [p[:] for p in mobject.cloud[lower:upper]]
        self.cloud_colors = mobject.cloud_colors[lower:upper]
        self.cloud_opacities = mobject.cloud_opacities[lower:upper]
        return self

    def get_point_mobject(self, center=None):
        return Point(self.get_center() if center is None else center)

    def to_dict(self):
        result = super().to_dict()
        if result['type'] == 'pointcloud':
            # Community's camera thickens each point by stroke_width pixels at 1920 wide.
            result['point_size'] = self.stroke_width * config.frame_width / 1920
        return result


class Mobject1D(PMobject):
    def __init__(self, density=DEFAULT_POINT_DENSITY_1D, **kwargs):
        NumberLine._real(density, 'Point density', positive=True)
        self.density, self.epsilon = density, 1.0 / density
        super().__init__(**kwargs)

    def add_line(self, start, end, color=None):
        start, end = Vector(start), Vector(end)
        length = math.dist(start, end)
        if length == 0:
            points = [start]
        else:
            step = self.epsilon / length
            points = [start + (end - start) * (i * step) for i in range(math.ceil(1 / step - 1e-12))]
        return self.add_points(points, color=color)


class Mobject2D(PMobject):
    def __init__(self, density=DEFAULT_POINT_DENSITY_2D, **kwargs):
        NumberLine._real(density, 'Point density', positive=True)
        self.density, self.epsilon = density, 1.0 / density
        super().__init__(**kwargs)


class PGroup(PMobject):
    def __init__(self, *pmobs, **kwargs):
        if not all(isinstance(m, PMobject) for m in pmobs):
            raise ValueError('All submobjects must be of type PMobject')
        super().__init__(**kwargs)
        self.add(*pmobs)

    def fade_to(self, color, alpha, family=True):
        if family:
            for child in self.children:
                child.fade_to(color, alpha, family)
        return self


class PointCloudDot(Mobject1D):
    """A disk of points on concentric rings, as Community's PointCloudDot."""
    def __init__(self, center=ORIGIN, radius=2.0, stroke_width=2, density=DEFAULT_POINT_DENSITY_1D,
                 color=PURE_YELLOW, **kwargs):
        NumberLine._real(radius, 'PointCloudDot radius', positive=True)
        super().__init__(stroke_width=stroke_width, density=density, color=color, **kwargs)
        self.radius = radius
        points, r = [], self.epsilon
        while r < radius - 1e-12:
            count = int(2 * math.pi * (r + self.epsilon) / self.epsilon)
            # np.linspace(0, 2pi, count) includes both ends.
            points += [(r * math.cos(2 * math.pi * k / (count - 1)), r * math.sin(2 * math.pi * k / (count - 1)), 0)
                       for k in range(count)] if count > 1 else [(r, 0, 0)] * count
            r += self.epsilon
        self.add_points(points)
        self.shift(Vector(center))


class Point(PMobject):
    def __init__(self, location=ORIGIN, color=BLACK, **kwargs):
        super().__init__(color=color, **kwargs)
        self.location = list(Vector(location))
        self.add_points([location])


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


# Community utility functions (manim.utils.*). Vectors are lite Vectors (tuples with
# arithmetic) and arrays are lists, which NumPy accepts wherever arrays are expected.
X_AXIS, Y_AXIS, Z_AXIS = RIGHT, UP, OUT
DEFAULT_DASH_LENGTH = 0.05
DEFAULT_POINTWISE_FUNCTION_RUN_TIME = 3.0
DEFAULT_WAIT_TIME = 1.0
SCALE_FACTOR_PER_FONT_POINT = 1 / 960
START_X, START_Y = 30, 20


def _point(value, name='Point'):
    vector = Vector(value.tolist() if hasattr(value, 'tolist') else value)
    for v in vector:
        NumberLine._real(v, name + ' coordinate')
    return vector


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _cross(a, b):
    return Vector((a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]))


def _user_interpolate(start, end, alpha):
    """Community's interpolate: (1 - alpha) * start + alpha * end, for numbers or points."""
    if isinstance(start, _REAL) and isinstance(end, _REAL):
        return (1 - alpha) * start + alpha * end
    if hasattr(start, '__array__') or hasattr(end, '__array__'):
        return (1 - alpha) * start + alpha * end
    a, b = list(start), list(end)
    if len(a) == 3 and len(b) == 3:
        return Vector((1 - alpha) * x + alpha * y for x, y in zip(a, b))
    return [_user_interpolate(x, y, alpha) for x, y in zip(a, b)]


def integer_interpolate(start, end, alpha):
    if alpha >= 1:
        return (int(end - 1), 1.0)
    if alpha <= 0:
        return (int(start), 0)
    value = int(_user_interpolate(start, end, alpha))
    residue = ((end - start) * alpha) % 1
    return (value, residue)


def mid(start, end):
    return _user_interpolate(start, end, 0.5)


def inverse_interpolate(start, end, value):
    return (value - start) / (end - start)


def match_interpolate(new_start, new_end, old_start, old_end, old_value):
    return _user_interpolate(new_start, new_end, inverse_interpolate(old_start, old_end, old_value))


def midpoint(point1, point2):
    return _user_interpolate(point1, point2, 0.5)


def normalize(vect, fall_back=None):
    vector = _point(vect, 'Vector')
    norm = _norm(vector)
    if norm > 0:
        return vector / norm
    return fall_back if fall_back is not None else Vector(ORIGIN)


def rotation_about_z(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def rotation_matrix(angle, axis, homogeneous=False):
    """Rodrigues' rotation matrix about an axis (3x3, or 4x4 when homogeneous)."""
    x, y, z = normalize(axis)
    c, s, t = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    matrix = [[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
              [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
              [t * x * z - s * y, t * y * z + s * x, t * z * z + c]]
    if homogeneous:
        return [row + [0] for row in matrix] + [[0, 0, 0, 1]]
    return matrix


def _apply_rows(matrix, vector):
    return Vector(sum(row[i] * vector[i] for i in range(3)) for row in matrix)


def rotate_vector(vector, angle, axis=OUT):
    """Rotate a 2D or 3D vector by angle about axis (Community returns the same length)."""
    values = list(vector.tolist() if hasattr(vector, 'tolist') else vector)
    if len(values) == 2:
        c, s = math.cos(angle), math.sin(angle)
        return Vector((values[0] * c - values[1] * s, values[0] * s + values[1] * c, 0))
    if len(values) != 3:
        raise ValueError('Vector must have the correct dimensions.')
    return _apply_rows(rotation_matrix(angle, axis), Vector(values))


def z_to_vector(vector):
    axis_z = normalize(vector)
    axis_y = normalize(_cross(axis_z, RIGHT))
    axis_x = _cross(axis_y, axis_z)
    if _norm(axis_y) == 0:
        axis_x = normalize(_cross(UP, axis_z))
        axis_y = -_cross(axis_x, axis_z)
    return [list(row) for row in zip(axis_x, axis_y, axis_z)]


def get_unit_normal(v1, v2, tol=1e-6):
    v1, v2 = _point(v1, 'Vector'), _point(v2, 'Vector')
    div1, div2 = max(abs(v) for v in v1), max(abs(v) for v in v2)
    if div1 == 0:
        if div2 == 0:
            return DOWN
        u = v2 / div2
    elif div2 == 0:
        u = v1 / div1
    else:
        u1, u2 = v1 / div1, v2 / div2
        cp = _cross(u1, u2)
        cp_norm = _norm(cp)
        if cp_norm > tol:
            return cp / cp_norm
        u = u1
    if abs(u[0]) < tol and abs(u[1]) < tol:
        return DOWN
    cp = Vector((-u[0] * u[2], -u[1] * u[2], u[0] * u[0] + u[1] * u[1]))
    return cp / _norm(cp)


def get_shaded_rgb(rgb, point, unit_normal_vect, light_source):
    """Community's shading: 0.5*cos^3 toward the light, halved when facing away.

    The result is deliberately unclipped, matching Community; callers that
    serialize colors must clamp to [0, 1] themselves."""
    to_sun = normalize(Vector(light_source) - Vector(point))
    light = 0.5 * sum(a * b for a, b in zip(normalize(unit_normal_vect), to_sun)) ** 3
    if light < 0:
        light *= 0.5
    return [value + light for value in rgb]


def compass_directions(n=4, start_vect=RIGHT):
    return [rotate_vector(_point(start_vect), k * TAU / n) for k in range(n)]


def regular_vertices(n, *, radius=1, start_angle=None):
    if start_angle is None:
        start_angle = 0 if n % 2 == 0 else TAU / 4
    return compass_directions(n, rotate_vector(RIGHT * radius, start_angle)), start_angle


def complex_to_R3(complex_num):
    return Vector((complex_num.real, complex_num.imag, 0))


def R3_to_complex(point):
    return complex(*list(point)[:2])


def complex_func_to_R3_func(complex_func):
    return lambda p: complex_to_R3(complex_func(R3_to_complex(p)))


def center_of_mass(points):
    points = [list(p) for p in points]
    return [sum(values) / len(points) for values in zip(*points)]


def cross2d(a, b):
    a, b = list(a.tolist() if hasattr(a, 'tolist') else a), list(b.tolist() if hasattr(b, 'tolist') else b)
    if a and isinstance(a[0], (list, tuple)):
        return [p[0] * q[1] - q[0] * p[1] for p, q in zip(a, b)]
    return a[0] * b[1] - b[0] * a[1]


def shoelace(x_y):
    points = [list(p) for p in x_y]
    return sum(points[i - 1][0] * points[i][1] - points[i][0] * points[i - 1][1]
               for i in range(len(points))) / -2 if points else 0.0


def shoelace_direction(x_y):
    return 'CW' if shoelace(x_y) > 0 else 'CCW'


def perpendicular_bisector(line, norm_vector=OUT):
    p1, p2 = _point(line[0]), _point(line[1])
    direction = _cross(p1 - p2, _point(norm_vector))
    middle = midpoint(p1, p2)
    return [middle + direction, middle - direction]


def cartesian_to_spherical(vec):
    vec = _point(vec)
    r = _norm(vec)
    if r == 0:
        return Vector(ORIGIN)
    return Vector((r, math.atan2(vec[1], vec[0]), math.acos(vec[2] / r)))


def spherical_to_cartesian(spherical):
    r, theta, phi = list(spherical)
    return Vector((r * math.cos(theta) * math.sin(phi), r * math.sin(theta) * math.sin(phi), r * math.cos(phi)))


def find_intersection(p0s, v0s, p1s, v1s, threshold=1e-5):
    result = []
    for p0, v0, p1, v1 in zip(p0s, v0s, p1s, v1s):
        p0, v0, p1, v1 = (_point(v) for v in (p0, v0, p1, v1))
        normal = _cross(v1, _cross(v0, v1))
        denom = max(sum(a * b for a, b in zip(v0, normal)), threshold)
        result.append(p0 + v0 * (sum(a * b for a, b in zip(p1 - p0, normal)) / denom))
    return result


def get_winding_number(points):
    total = 0
    points = [list(p) for p in points]
    for p1, p2 in adjacent_pairs(points):
        d_angle = math.atan2(p2[1], p2[0]) - math.atan2(p1[1], p1[0])
        d_angle = ((d_angle + PI) % TAU) - PI
        total += d_angle
    return total / TAU


def thick_diagonal(dim, thickness=2):
    return [[int(abs(i - j) < thickness) for j in range(dim)] for i in range(dim)]


def bezier(points):
    """Community's Bézier evaluator for any number of control points."""
    points = [_point(p) for p in (points.tolist() if hasattr(points, 'tolist') else points)]
    n = len(points) - 1
    def evaluate(t):
        return Vector(sum(math.comb(n, k) * (1 - t) ** (n - k) * t ** k * p[i] for k, p in enumerate(points))
                      for i in range(3))
    return evaluate


def _de_casteljau(points, t):
    points = [_point(p) for p in points]
    left, right = [points[0]], [points[-1]]
    while len(points) > 1:
        points = [a + (b - a) * t for a, b in zip(points, points[1:])]
        left.append(points[0])
        right.append(points[-1])
    return left, right[::-1]


def split_bezier(points, t):
    left, right = _de_casteljau(list(points), t)
    return left + right


def partial_bezier_points(points, a, b):
    points = list(points)
    if a == 1:
        return [_point(points[-1])] * len(points)
    if b == 0:
        return [_point(points[0])] * len(points)
    _, upper = _de_casteljau(points, a)
    if a == b:
        return [upper[0]] * len(points)
    lower, _ = _de_casteljau(upper, (b - a) / (1 - a))
    return lower


def subdivide_bezier(points, n_divisions):
    points = list(points)
    if n_divisions == 1:
        return [_point(p) for p in points]
    result, remaining = [], points
    for i in range(n_divisions - 1):
        left, remaining = _de_casteljau(remaining, 1 / (n_divisions - i))
        result += left
    return result + remaining


def bezier_remap(bezier_tuples, new_number_of_curves):
    tuples = [list(t) for t in bezier_tuples]
    count = len(tuples)
    splits = [0] * count
    for index in range(new_number_of_curves):
        splits[index * count // new_number_of_curves] += 1
    result = []
    for curve, parts in zip(tuples, splits):
        pieces = subdivide_bezier(curve, parts) if parts else []
        degree = len(curve)
        result += [pieces[i:i + degree] for i in range(0, len(pieces), degree)]
    return result


def point_lies_on_bezier(point, control_points, round_to=1e-6):
    return bool(proportions_along_bezier_curve_for_point(point, control_points, round_to))


def proportions_along_bezier_curve_for_point(point, control_points, round_to=1e-6):
    """Parameters where a Bézier curve passes through point (sampled, then refined)."""
    curve, target = bezier(control_points), _point(point)
    def distance(t):
        return _norm(curve(t) - target)
    found = []
    samples = 400
    for i in range(samples + 1):
        lo, hi = max(0, (i - 1) / samples), min(1, (i + 1) / samples)
        for _ in range(60):
            m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
            if distance(m1) < distance(m2):
                hi = m2
            else:
                lo = m1
        t = (lo + hi) / 2
        if distance(t) <= max(round_to, 1e-9) * 10 and all(abs(t - u) > 1e-4 for u in found):
            found.append(t)
    return sorted(found)


def get_smooth_cubic_bezier_handle_points(anchors):
    """Community's smooth handles: natural splines (open) or periodic (closed) anchors."""
    anchors = [_point(p) for p in anchors]
    if len(anchors) < 2:
        return [], []
    path = VMobject().set_points_smoothly(anchors)
    points = path.get_points()
    return [Vector(points[i + 1]) for i in range(0, len(points), 4)], [Vector(points[i + 2]) for i in range(0, len(points), 4)]


def is_closed(points):
    points = list(points)
    return bool(points) and all(abs(a - b) < 1e-6 for a, b in zip(_point(points[0]), _point(points[-1])))


def straight_path():
    return _PathFunction(0)


def path_along_arc(arc_angle, axis=OUT):
    axis = _point(axis)
    if axis[0] or axis[1] or not axis[2]:
        raise NotImplementedError('Path arcs support only the OUT/IN axes')
    return _PathFunction(arc_angle if axis[2] > 0 else -arc_angle)


def clockwise_path():
    return _PathFunction(-PI)


def counterclockwise_path():
    return _PathFunction(PI)


def path_along_circles(arc_angle, circles_centers, axis=OUT):
    return _CirclesPath(arc_angle, circles_centers, axis)


def spiral_path(angle, axis=OUT):
    if abs(angle) < STRAIGHT_PATH_THRESHOLD:
        return straight_path()
    return _SpiralPath(angle, axis)


def _rotation_rows(angle, axis):
    x, y, z = _point(axis)
    norm = math.sqrt(x * x + y * y + z * z)
    x, y, z = (x / norm, y / norm, z / norm) if norm else (0, 0, 1)
    c, s, t = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return ((t * x * x + c, t * x * y - s * z, t * x * z + s * y),
            (t * x * y + s * z, t * y * y + c, t * y * z - s * x),
            (t * x * z - s * y, t * y * z + s * x, t * z * z + c))


def _apply_rows(rows, v):
    return Vector(sum(a * b for a, b in zip(row, v)) for row in rows)


class _PointPath:
    """A path function moving each point independently: point(p, q, alpha), and callable
    on point lists (Community's PathFuncType)."""
    def __call__(self, start_points, end_points, alpha):
        starts = start_points.tolist() if hasattr(start_points, 'tolist') else start_points
        ends = end_points.tolist() if hasattr(end_points, 'tolist') else end_points
        if starts is not None and len(starts) and isinstance(list(starts)[0], _REAL):
            return self.point(starts, ends, alpha)
        return [self.point(p, q, alpha) for p, q in zip(starts, ends)]


class _CirclesPath(_PointPath):
    """Community's path_along_circles: orbit each point's own center while blending."""
    def __init__(self, arc_angle, circles_centers, axis=OUT):
        self.arc_angle, self.axis = NumberLine._real(arc_angle, 'arc_angle'), axis
        centers = circles_centers.tolist() if hasattr(circles_centers, 'tolist') else circles_centers
        self.centers = (_point(centers) if len(centers) and isinstance(list(centers)[0], _REAL)
                        else [_point(c) for c in centers])
        self._index = 0

    def _center(self):
        if isinstance(self.centers, list):
            center = self.centers[self._index % len(self.centers)]
            self._index += 1
            return center
        return self.centers

    def __call__(self, start_points, end_points, alpha):
        self._index = 0
        return super().__call__(start_points, end_points, alpha)

    def point(self, p, q, alpha):
        c = self._center()
        back = _apply_rows(_rotation_rows(-self.arc_angle, self.axis), _point(q) - c) + c
        p = _point(p)
        return _apply_rows(_rotation_rows(alpha * self.arc_angle, self.axis), p + (back - p) * alpha - c) + c


class _AxisArcPath(_PointPath):
    """Community's path_along_arc about an arbitrary axis."""
    def __init__(self, arc_angle, axis):
        self.arc_angle, self.axis = arc_angle, axis
        x, y, z = _point(axis)
        norm = math.sqrt(x * x + y * y + z * z) or 1
        self.unit = Vector((x / norm, y / norm, z / norm)) if (x or y or z) else Vector(OUT)

    def point(self, p, q, alpha):
        p, q = _point(p), _point(q)
        if abs(self.arc_angle) < STRAIGHT_PATH_THRESHOLD:
            return p + (q - p) * alpha
        half = (q - p) * 0.5
        center = p + half
        if self.arc_angle != PI:
            u = self.unit
            cross = Vector((u[1] * half[2] - u[2] * half[1], u[2] * half[0] - u[0] * half[2],
                            u[0] * half[1] - u[1] * half[0]))
            center = center + cross * (1 / math.tan(self.arc_angle / 2))
        return _apply_rows(_rotation_rows(alpha * self.arc_angle, self.unit), p - center) + center


class _SpiralPath(_PointPath):
    """Community's spiral_path: the offset to the target turns as it grows."""
    def __init__(self, angle, axis=OUT):
        self.angle, self.axis = NumberLine._real(angle, 'spiral angle'), axis

    def point(self, p, q, alpha):
        p = _point(p)
        return p + _apply_rows(_rotation_rows((alpha - 1) * self.angle, self.axis), _point(q) - p) * alpha


class _FunctionPath(_PointPath):
    """A user path function, applied to one start/end point pair at a time."""
    def __init__(self, function):
        self.function = function

    def point(self, p, q, alpha):
        try:
            import numpy
        except ImportError:
            value = self.function([list(p)], [list(q)], alpha)
        else:
            value = self.function(numpy.array([list(p)], dtype=float), numpy.array([list(q)], dtype=float), alpha)
        value = value.tolist() if hasattr(value, 'tolist') else value
        return _point(value[0])


class _PathFunction(_PointPath):
    """Community's arc path functions: callable on point lists, and usable as path_func."""
    def __init__(self, arc):
        self.path_arc = arc if abs(arc) >= STRAIGHT_PATH_THRESHOLD else 0

    def point(self, p, q, alpha):
        return self([p], [q], alpha)[0]

    def __call__(self, start_points, end_points, alpha):
        factor = _arc_factor(alpha, self.path_arc)
        def move(p, q):
            p, q = _point(p), _point(q)
            d = q - p
            return Vector((p[0] + factor.real * d[0] - factor.imag * d[1],
                           p[1] + factor.imag * d[0] + factor.real * d[1], p[2] + alpha * d[2]))
        starts = start_points.tolist() if hasattr(start_points, 'tolist') else start_points
        ends = end_points.tolist() if hasattr(end_points, 'tolist') else end_points
        if starts and isinstance(list(starts)[0], _REAL):
            return move(starts, ends)
        return [move(p, q) for p, q in zip(starts, ends)]


def adjacent_n_tuples(objects, n):
    objects = list(objects)
    return list(zip(*[objects[k:] + objects[:k] for k in range(n)]))


def adjacent_pairs(objects):
    return adjacent_n_tuples(objects, 2)


def all_elements_are_instances(iterable, Class):
    return all(isinstance(e, Class) for e in iterable)


def concatenate_lists(*list_of_lists):
    return [item for items in list_of_lists for item in items]


def list_update(l1, l2):
    return [e for e in l1 if e not in l2] + list(l2)


def list_difference_update(l1, l2):
    return [e for e in l1 if e not in l2]


def listify(obj):
    if isinstance(obj, str):
        return [obj]
    try:
        return list(obj)
    except TypeError:
        return [obj]


def make_even(iterable_1, iterable_2):
    list_1, list_2 = list(iterable_1), list(iterable_2)
    length = max(len(list_1), len(list_2))
    return ([list_1[(n * len(list_1)) // length] for n in range(length)],
            [list_2[(n * len(list_2)) // length] for n in range(length)])


def make_even_by_cycling(iterable_1, iterable_2):
    list_1, list_2 = list(iterable_1), list(iterable_2)
    length = max(len(list_1), len(list_2))
    return [list_1[i % len(list_1)] for i in range(length)], [list_2[i % len(list_2)] for i in range(length)]


def remove_list_redundancies(lst):
    seen, result = set(), []
    for item in reversed(list(lst)):
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result[::-1]


def remove_nones(sequence):
    return [x for x in sequence if x]


def stretch_array_to_length(nparray, length):
    items = list(nparray)
    curr_len = len(items)
    if curr_len > length:
        raise Warning('Trying to stretch array to a length shorter than its own')
    return [items[int(i * curr_len / length)] for i in range(length)]


def tuplify(obj):
    if isinstance(obj, str):
        return (obj,)
    try:
        return tuple(obj)
    except TypeError:
        return (obj,)


def choose(n, k):
    return math.comb(n, k)


def clip(a, min_a, max_a):
    return min_a if a < min_a else max_a if a > max_a else a


def binary_search(function, target, lower_bound, upper_bound, tolerance=1e-4):
    lh, rh = lower_bound, upper_bound
    mh = (lh + rh) / 2
    while abs(rh - lh) > tolerance:
        mh = (lh + rh) / 2
        lx, mx, rx = (function(h) for h in (lh, mh, rh))
        if lx == target:
            return lh
        if rx == target:
            return rh
        if lx <= target <= rx:
            if mx > target:
                rh = mh
            else:
                lh = mh
        elif lx > target > rx:
            lh, rh = rh, lh
        else:
            return None
    return mh


def color_to_rgba(color, alpha=1):
    return list(ManimColor(color, alpha)._rgba[:3]) + [alpha]


def rgba_to_color(rgba):
    rgba = list(rgba)
    return ManimColor(rgba[:3], rgba[3] if len(rgba) > 3 else 1.0)


def color_to_int_rgb(color):
    return [int(v * 255) for v in ManimColor(color)._rgba[:3]]


def color_to_int_rgba(color, opacity=1.0):
    return color_to_int_rgb(color) + [int(opacity * 255)]


def merge_dicts_recursively(*dicts):
    result = {}
    _update_dict_recursively(result, *[copy.deepcopy(d) for d in dicts])
    return result


def update_dict_recursively(current_dict, *others):
    _update_dict_recursively(current_dict, *others)


class tempconfig:
    """Community's tempconfig: temporarily override preview configuration values."""
    def __init__(self, temp_config):
        self.changes = dict(temp_config.items() if hasattr(temp_config, 'items') else temp_config)

    def __enter__(self):
        self.saved = {name: getattr(config, name) for name in self.changes}
        for name, value in self.changes.items():
            setattr(config, name, value)
        return config

    def __exit__(self, *exc):
        for name, value in self.saved.items():
            setattr(config, name, value)
        return False


def override_animate(method):
    """Decorator: make mobject.animate.method(...) build this custom animation."""
    def decorator(animation_method):
        method._override_animate = animation_method
        return animation_method
    return decorator


def override_animation(animation_class):
    """Decorator: make animation_class(mobject, ...) build this method's animation."""
    def decorator(func):
        func._override_animation = animation_class
        return func
    return decorator


def index_labels(mobject, label_height=0.15, background_stroke_width=5, **kwargs):
    """Integer labels at each submobject center (Community's debugging helper)."""
    labels = VGroup()
    for n, submob in enumerate(mobject):
        label = Integer(n, **kwargs)
        label.set_stroke(BLACK, width=background_stroke_width, background=True)
        label.scale_to_fit_height(label_height)
        label.move_to(submob)
        labels.add(label)
    return labels


def print_family(mobject, n_tabs=0):
    print('\t' * n_tabs, mobject, id(mobject))
    for submob in mobject.children:
        print_family(submob, n_tabs + 1)


def assert_is_mobject_method(method):
    if not inspect.ismethod(method) or not isinstance(method.__self__, Mobject):
        raise AssertionError('Expected a Mobject method')


def turn_animation_into_updater(animation, cycle=False, delay=0, **kwargs):
    """Drive an animation from an updater instead of Scene.play (Community)."""
    mobject = animation.mobject
    animation.suspend_mobject_updating = False
    elapsed = [-delay]
    starting = mobject.copy()
    animation_copy = [None]
    def update(m, dt):
        if elapsed[0] < 0:
            elapsed[0] += dt
            return
        if animation_copy[0] is None:
            m.become(starting)
            animation_copy[0] = True
        run_time = animation.run_time
        time_ratio = elapsed[0] / run_time if run_time else 1
        if cycle:
            alpha = time_ratio % 1
        else:
            alpha = min(1, max(0, time_ratio))
            if alpha >= 1:
                m.become(_animation_end_state(animation, starting))
                m.remove_updater(update)
                return
        m.become(_animation_state(animation, starting, alpha))
        elapsed[0] += dt
    mobject.add_updater(update)
    return mobject


def cycle_animation(animation, **kwargs):
    return turn_animation_into_updater(animation, cycle=True, **kwargs)


def _animation_state(animation, starting, alpha):
    """A live Mobject showing an animation at alpha (for animation-driven updaters)."""
    if not getattr(animation, '_updater_ready', False):
        animation.mobject.become(starting)
        animation.prepare(Scene())
        animation._updater_ready = True
    states = animation.states(alpha)[animation.mobject]
    snapshot = max(states, key=lambda state: state['opacity'])
    result = starting.copy()
    def apply(target, node):
        for child, state in zip(target.children, node.get('children', [])):
            apply(child, state)
        for key, value in node.items():
            if key not in ('type', 'children', 'geometry_center'):
                target.__dict__[key] = _snapshot_copy(value)
        target._type = node['type']
        target.__dict__.pop('_family_pivot_cache', None)
        # Keep the sampled pose exactly although the pivot is recomputed:
        # P' = P + (I - sR)(G - G').
        sampled, current = Vector(node['geometry_center']), target._geometry_center()
        delta = sampled - current
        c, s = target.geometry_scale * math.cos(target.angle), target.geometry_scale * math.sin(target.angle)
        target.position = list(Vector(target.position) + Vector((delta[0] - (c * delta[0] - s * delta[1]),
                                                                 delta[1] - (s * delta[0] + c * delta[1]), 0)))
    apply(result, snapshot)
    return result


def _animation_end_state(animation, starting):
    return _animation_state(animation, starting, 1)


class SampleSpace(Rectangle):
    """Community's probability sample space: a rectangle divided by probabilities."""
    def __init__(self, height=3, width=3, fill_color=DARK_GREY, fill_opacity=1, stroke_width=0.5,
                 stroke_color=LIGHT_GREY, default_label_scale_val=1):
        super().__init__(height=height, width=width, fill_color=fill_color, fill_opacity=fill_opacity,
                         stroke_width=stroke_width, stroke_color=stroke_color)
        self.default_label_scale_val = default_label_scale_val

    def add_title(self, title='Sample space', buff=MED_SMALL_BUFF):
        title_mob = Tex(title)
        if title_mob.get_width() > self.get_width():
            title_mob.width = self.get_width()
        title_mob.next_to(self, UP, buff=buff)
        self.title = title_mob
        self.add(title_mob)
        return self

    def add_label(self, label):
        self.label = label
        return self

    def complete_p_list(self, p_list):
        new_p_list = list(tuplify(p_list))
        remainder = 1.0 - sum(new_p_list)
        if abs(remainder) > 1e-8:
            new_p_list.append(remainder)
        return new_p_list

    def get_division_along_dimension(self, p_list, dim, colors, vect):
        p_list = self.complete_p_list(p_list)
        colors = color_gradient(colors, len(p_list))
        last_point = self.get_edge_center(-Vector(vect))
        parts = VGroup()
        for factor, color in zip(p_list, colors):
            part = SampleSpace()
            part.set_fill(color, 1)
            part.replace(self, stretch=True)
            part.stretch(factor, dim)
            part.move_to(last_point, -Vector(vect))
            last_point = part.get_edge_center(vect)
            parts.add(part)
        return parts

    def get_horizontal_division(self, p_list, colors=(GREEN_E, BLUE_E), vect=DOWN):
        return self.get_division_along_dimension(p_list, 1, colors, vect)

    def get_vertical_division(self, p_list, colors=(MAROON_B, YELLOW), vect=RIGHT):
        return self.get_division_along_dimension(p_list, 0, colors, vect)

    def divide_horizontally(self, *args, **kwargs):
        self.horizontal_parts = self.get_horizontal_division(*args, **kwargs)
        self.add(self.horizontal_parts)
        return self

    def divide_vertically(self, *args, **kwargs):
        self.vertical_parts = self.get_vertical_division(*args, **kwargs)
        self.add(self.vertical_parts)
        return self

    def get_subdivision_braces_and_labels(self, parts, labels, direction, buff=SMALL_BUFF, min_num_quads=1):
        # min_num_quads is accepted for compatibility; Community's Brace rejects it.
        label_mobs, braces = VGroup(), VGroup()
        # Parts are children of this shape; measure them where they appear.
        owner = self._world_member(parts) if parts in self.children else parts
        for label, part in zip(labels, owner):
            brace = Brace(part, direction, buff=buff)
            if isinstance(label, VMobject):
                label_mob = label
            else:
                label_mob = MathTex(label)
                label_mob.scale(self.default_label_scale_val)
            label_mob.next_to(brace, direction, buff)
            braces.add(brace)
            label_mobs.add(label_mob)
        parts.braces, parts.labels = braces, label_mobs
        parts.label_kwargs = {'labels': label_mobs.copy(), 'direction': direction, 'buff': buff}
        return VGroup(parts.braces, parts.labels)

    def get_side_braces_and_labels(self, labels, direction=LEFT, **kwargs):
        return self.get_subdivision_braces_and_labels(self.horizontal_parts, labels, direction, **kwargs)

    def get_top_braces_and_labels(self, labels, **kwargs):
        return self.get_subdivision_braces_and_labels(self.vertical_parts, labels, UP, **kwargs)

    def get_bottom_braces_and_labels(self, labels, **kwargs):
        return self.get_subdivision_braces_and_labels(self.vertical_parts, labels, DOWN, **kwargs)

    def add_braces_and_labels(self):
        for attr in ('horizontal_parts', 'vertical_parts'):
            parts = self.__dict__.get(attr)
            if parts is None:
                continue
            for subattr in ('braces', 'labels'):
                if subattr in parts.__dict__:
                    self.add(parts.__dict__[subattr])
        return self

    def __getitem__(self, index):
        if 'horizontal_parts' in self.__dict__:
            return self.horizontal_parts[index]
        if 'vertical_parts' in self.__dict__:
            return self.vertical_parts[index]
        return super().__getitem__(index)


class TransformAnimations(Animation):
    """Morph between what two animations show, frame by frame (Community)."""
    def __init__(self, start_anim, end_anim, rate_func=squish_rate_func(smooth), **kwargs):
        if not isinstance(start_anim, Animation) or not isinstance(end_anim, Animation):
            raise TypeError('TransformAnimations expects two animations')
        run_time = kwargs.pop('run_time', max(start_anim.run_time, end_anim.run_time))
        super().__init__(start_anim.mobject, rate_func=rate_func, run_time=run_time, **kwargs)
        self.start_anim, self.end_anim = start_anim, end_anim
        for anim in (start_anim, end_anim):
            anim.run_time = run_time

    def prepare(self, scene):
        for anim in (self.start_anim, self.end_anim):
            anim.prepare(Scene())
        super().prepare(scene)

    @staticmethod
    def _shown(anim, alpha):
        states = anim.states(alpha)[anim.mobject]
        return max(states, key=lambda state: state['opacity'])

    def states(self, alpha, rate_func=None):
        alpha = max(0, min(1, alpha))
        start, end = self._shown(self.start_anim, alpha), self._shown(self.end_anim, alpha)
        rate = rate_func or self.rate_func
        return {self.mobject: _sample_transform(_transform_plan(start, end), rate(alpha))}

    def finish(self, scene):
        terminal = copy.deepcopy(self.end_anim)
        staging = Scene().add(terminal.mobject)
        terminal._complete(staging)
        self.mobject.become(terminal.mobject)


# Community's logo glyph outlines (manim/mobject/logo.py): the double-struck M, then "anim".
MANIM_SVG_PATHS = [
    'M 4.64259,-2.092154 L 2.739726,-6.625156 C 2.660025,-6.824408 2.650062,-6.824408 2.381071,-6.824408 L 0.52802,-6.824408 C 0.348692,-6.824408 0.199253,-6.824408 0.199253,-6.645081 C 0.199253,-6.475716 0.37858,-6.475716 0.428394,-6.475716 C 0.547945,-6.475716 0.816936,-6.455791 1.036115,-6.37609 L 1.036115,-1.05604 C 1.036115,-0.846824 1.036115,-0.408468 0.358655,-0.348692 C 0.169365,-0.328767 0.169365,-0.18929 0.169365,-0.179328 C 0.169365,0 0.328767,0 0.508095,0 L 2.052304,0 C 2.231631,0 2.381071,0 2.381071,-0.179328 C 2.381071,-0.268991 2.30137,-0.33873 2.221669,-0.348692 C 1.454545,-0.408468 1.454545,-0.826899 1.454545,-1.05604 L 1.454545,-6.017435 L 1.464508,-6.027397 L 3.895392,-0.209215 C 3.975093,-0.029888 4.044832,0 4.104608,0 C 4.224159,0 4.254047,-0.079701 4.303861,-0.199253 L 6.744707,-6.027397 L 6.75467,-6.017435 L 6.75467,-1.05604 C 6.75467,-0.846824 6.75467,-0.408468 6.07721,-0.348692 C 5.88792,-0.328767 5.88792,-0.18929 5.88792,-0.179328 C 5.88792,0 6.047323,0 6.22665,0 L 8.886675,0 C 9.066002,0 9.215442,0 9.215442,-0.179328 C 9.215442,-0.268991 9.135741,-0.33873 9.05604,-0.348692 C 8.288917,-0.408468 8.288917,-0.826899 8.288917,-1.05604 L 8.288917,-5.768369 C 8.288917,-5.977584 8.288917,-6.41594 8.966376,-6.475716 C 9.066002,-6.485679 9.155666,-6.535492 9.155666,-6.645081 C 9.155666,-6.824408 9.006227,-6.824408 8.826899,-6.824408 L 6.90411,-6.824408 C 6.645081,-6.824408 6.625156,-6.824408 6.535492,-6.615193 L 4.64259,-2.092154 Z M 4.343711,-1.912827 C 4.423412,-1.743462 4.433375,-1.733499 4.552927,-1.693649 L 4.11457,-0.637609 L 4.094645,-0.637609 L 1.823163,-6.057285 C 1.77335,-6.1868 1.693649,-6.356164 1.554172,-6.475716 L 2.420922,-6.475716 L 4.343711,-1.912827 Z M 1.334994,-0.348692 L 1.165629,-0.348692 C 1.185554,-0.37858 1.205479,-0.408468 1.225405,-0.428394 C 1.235367,-0.438356 1.235367,-0.448319 1.24533,-0.458281 L 1.334994,-0.348692 Z M 7.103362,-6.475716 L 8.159402,-6.475716 C 7.940224,-6.22665 7.940224,-5.967621 7.940224,-5.788294 L 7.940224,-1.036115 C 7.940224,-0.856787 7.940224,-0.597758 8.169365,-0.348692 L 6.884184,-0.348692 C 7.103362,-0.597758 7.103362,-0.856787 7.103362,-1.036115 L 7.103362,-6.475716 Z',
    'M 1.464508,-4.024907 C 1.464508,-4.234122 1.743462,-4.393524 2.092154,-4.393524 C 2.669988,-4.393524 2.929016,-4.124533 2.929016,-3.516812 L 2.929016,-2.789539 C 1.77335,-2.440847 0.249066,-2.042341 0.249066,-0.916563 C 0.249066,-0.308842 0.71731,0.139477 1.354919,0.139477 C 1.92279,0.139477 2.381071,-0.059776 2.929016,-0.557908 C 3.038605,-0.049813 3.257783,0.139477 3.745953,0.139477 C 4.174346,0.139477 4.483188,-0.019925 4.861768,-0.428394 L 4.712329,-0.637609 L 4.612702,-0.537983 C 4.582814,-0.508095 4.552927,-0.498132 4.503113,-0.498132 C 4.363636,-0.498132 4.293898,-0.587796 4.293898,-0.747198 L 4.293898,-3.347447 C 4.293898,-4.184309 3.536737,-4.712329 2.321295,-4.712329 C 1.195517,-4.712329 0.438356,-4.204234 0.438356,-3.457036 C 0.438356,-3.048568 0.67746,-2.799502 1.085928,-2.799502 C 1.484433,-2.799502 1.763387,-3.038605 1.763387,-3.377335 C 1.763387,-3.676214 1.464508,-3.88543 1.464508,-4.024907 Z M 2.919054,-0.996264 C 2.650062,-0.687422 2.450809,-0.56787 2.211706,-0.56787 C 1.912827,-0.56787 1.703611,-0.836862 1.703611,-1.235367 C 1.703611,-1.8132 2.122042,-2.231631 2.919054,-2.440847 L 2.919054,-0.996264 Z',
    'M 2.948941,-4.044832 C 3.297634,-4.044832 3.466999,-3.775841 3.466999,-3.217933 L 3.466999,-0.806974 C 3.466999,-0.438356 3.337484,-0.278954 2.998755,-0.239103 L 2.998755,0 L 5.339975,0 L 5.339975,-0.239103 C 4.951432,-0.268991 4.851806,-0.388543 4.851806,-0.806974 L 4.851806,-3.307597 C 4.851806,-4.164384 4.323786,-4.712329 3.506849,-4.712329 C 2.909091,-4.712329 2.450809,-4.433375 2.082192,-3.845579 L 2.082192,-4.592777 L 0.179328,-4.592777 L 0.179328,-4.353674 C 0.617684,-4.283935 0.707347,-4.184309 0.707347,-3.765878 L 0.707347,-0.836862 C 0.707347,-0.418431 0.627646,-0.328767 0.179328,-0.239103 L 0.179328,0 L 2.580324,0 L 2.580324,-0.239103 C 2.211706,-0.288917 2.092154,-0.438356 2.092154,-0.806974 L 2.092154,-3.466999 C 2.092154,-3.576588 2.530511,-4.044832 2.948941,-4.044832 Z',
    'M 2.15193,-4.592777 L 0.239103,-4.592777 L 0.239103,-4.353674 C 0.67746,-4.26401 0.767123,-4.174346 0.767123,-3.765878 L 0.767123,-0.836862 C 0.767123,-0.428394 0.697385,-0.348692 0.239103,-0.239103 L 0.239103,0 L 2.6401,0 L 2.6401,-0.239103 C 2.291407,-0.288917 2.15193,-0.428394 2.15193,-0.806974 L 2.15193,-4.592777 Z M 1.454545,-6.884184 C 1.026152,-6.884184 0.67746,-6.535492 0.67746,-6.117061 C 0.67746,-5.668742 1.006227,-5.339975 1.444583,-5.339975 S 2.221669,-5.668742 2.221669,-6.107098 C 2.221669,-6.535492 1.882939,-6.884184 1.454545,-6.884184 Z',
    'M 2.929016,-4.044832 C 3.317559,-4.044832 3.466999,-3.815691 3.466999,-3.217933 L 3.466999,-0.806974 C 3.466999,-0.398506 3.35741,-0.268991 2.988792,-0.239103 L 2.988792,0 L 5.32005,0 L 5.32005,-0.239103 C 4.971357,-0.278954 4.851806,-0.428394 4.851806,-0.806974 L 4.851806,-3.466999 C 4.851806,-3.576588 5.310087,-4.044832 5.69863,-4.044832 C 6.07721,-4.044832 6.22665,-3.805729 6.22665,-3.217933 L 6.22665,-0.806974 C 6.22665,-0.388543 6.117061,-0.268991 5.738481,-0.239103 L 5.738481,0 L 8.109589,0 L 8.109589,-0.239103 C 7.721046,-0.259029 7.611457,-0.37858 7.611457,-0.806974 L 7.611457,-3.307597 C 7.611457,-4.164384 7.083437,-4.712329 6.266501,-4.712329 C 5.69863,-4.712329 5.32005,-4.483188 4.801993,-3.845579 C 4.503113,-4.473225 4.154421,-4.712329 3.526775,-4.712329 S 2.440847,-4.443337 2.062267,-3.845579 L 2.062267,-4.592777 L 0.179328,-4.592777 L 0.179328,-4.353674 C 0.617684,-4.293898 0.707347,-4.174346 0.707347,-3.765878 L 0.707347,-0.836862 C 0.707347,-0.428394 0.617684,-0.318804 0.179328,-0.239103 L 0.179328,0 L 2.550436,0 L 2.550436,-0.239103 C 2.201743,-0.288917 2.092154,-0.428394 2.092154,-0.806974 L 2.092154,-3.466999 C 2.092154,-3.58655 2.530511,-4.044832 2.929016,-4.044832 Z'
]


class ManimBanner(VGroup):
    """Community's Manim logo banner: Create draws it, expand() slides out "anim"."""
    def __init__(self, dark_theme=True):
        super().__init__()
        logo_green, logo_blue, logo_red = '#81b29a', '#454866', '#e07a5f'
        m_height_over_anim_height = 0.75748
        self.font_color = '#ece6e2' if dark_theme else '#343434'
        self.scale_factor = 1.0
        self.M = VMobjectFromSVGPath(MANIM_SVG_PATHS[0]).flip(RIGHT).center()
        self.M.set(stroke_width=0).scale(7 * DEFAULT_FONT_SIZE * SCALE_FACTOR_PER_FONT_POINT)
        self.M.set_fill(color=self.font_color, opacity=1).shift(2.25 * LEFT + 1.5 * UP)
        self.circle = Circle(color=logo_green, fill_opacity=1).shift(LEFT)
        self.square = Square(color=logo_blue, fill_opacity=1).shift(UP)
        self.triangle = Triangle(color=logo_red, fill_opacity=1).shift(RIGHT)
        self.shapes = VGroup(self.triangle, self.square, self.circle)
        self.add(self.shapes, self.M)
        self.move_to(ORIGIN)
        anim = VGroup()
        for index, path in enumerate(MANIM_SVG_PATHS[1:]):
            tex = VMobjectFromSVGPath(path).flip(RIGHT).center()
            tex.set(stroke_width=0).scale(DEFAULT_FONT_SIZE * SCALE_FACTOR_PER_FONT_POINT)
            if index > 0:
                tex.next_to(anim, buff=0.01)
            tex.align_to(self.M, DOWN)
            anim.add(tex)
        anim.set_fill(color=self.font_color, opacity=1)
        anim.height = m_height_over_anim_height * self.M.get_height()
        # "anim" joins the banner only when it expands.
        self.anim = anim

    def scale(self, scale_factor, **kwargs):
        self.scale_factor *= scale_factor
        if self.anim not in self.children:
            self.anim.scale(scale_factor, **kwargs)
        return super().scale(scale_factor, **kwargs)

    @override_animation(Create)
    def create(self, run_time=2):
        return AnimationGroup(SpiralIn(self.shapes, run_time=run_time), FadeIn(self.M, run_time=run_time / 2),
                              lag_ratio=0.1)

    def expand(self, run_time=1.5, direction='center'):
        if direction not in ('left', 'right', 'center'):
            raise ValueError("direction must be 'left', 'right' or 'center'.")
        m_shape_offset = 6.25 * self.scale_factor
        shape_sliding_overshoot = self.scale_factor * 0.8
        self.anim.next_to(self.M, buff=0.06).align_to(self.M, DOWN)
        self.anim.set_opacity(0)
        self.shapes.save_state()
        m_clone = self.anim[-1].copy()
        self.add(m_clone)
        m_clone.move_to(self.shapes)
        self.M.save_state()
        left_group = VGroup(self.M, self.anim, m_clone)
        def shift(vector):
            self.shapes.restore()
            left_group.align_to(self.M.saved_state, LEFT)
            if direction == 'right':
                self.shapes.shift(vector)
            elif direction == 'center':
                self.shapes.shift(vector / 2)
                left_group.shift(-vector / 2)
            elif direction == 'left':
                left_group.shift(-vector)
        def slide_and_uncover(mob, alpha):
            shift(alpha * (m_shape_offset + shape_sliding_overshoot) * RIGHT)
            for letter in mob.anim:
                if mob.square.get_center()[0] > letter.get_center()[0]:
                    letter.set_opacity(1)
                    self.add_to_back(letter)
            if alpha == 1:
                self.remove(*[self.anim])
                self.add_to_back(self.anim)
                mob.shapes.set_z_index(0)
                mob.shapes.save_state()
                mob.M.save_state()
        def slide_back(mob, alpha):
            if alpha == 0:
                m_clone.set_opacity(1)
                m_clone.move_to(mob.anim[-1])
                mob.anim.set_opacity(1)
            shift(alpha * shape_sliding_overshoot * LEFT)
            if alpha == 1:
                mob.remove(m_clone)
                mob.add_to_back(mob.shapes)
        return Succession(UpdateFromAlphaFunc(self, slide_and_uncover, run_time=run_time * 2 / 3,
                                              rate_func=ease_in_out_cubic),
                          UpdateFromAlphaFunc(self, slide_back, run_time=run_time / 3, rate_func=smooth))


EXPORTS = ['config', 'Scene', 'MovingCameraScene', 'ZoomedScene', 'VectorScene', 'LinearTransformationScene', 'ThreeDCamera', 'ThreeDScene', 'ThreeDVMobject', 'Surface', 'Sphere', 'Dot3D', 'Cube', 'Prism', 'Cone', 'Cylinder', 'Line3D', 'Arrow3D', 'Torus', 'ThreeDAxes', 'Polyhedron', 'Tetrahedron', 'Octahedron', 'Icosahedron', 'Dodecahedron', 'ConvexHull3D', 'angle_of_vector', 'ImageMobjectFromCamera', 'Mobject', 'ValueTracker', 'always_redraw', 'VMobject', 'TipableVMobject', 'TracedPath', 'ParametricFunction', 'FunctionGraph', 'CubicBezier', 'Circle', 'Ellipse', 'Arc', 'ArcBetweenPoints', 'ArcPolygon', 'ArcPolygonFromArcs', 'AnnularSector', 'Sector', 'Annulus', 'Dot', 'Square', 'Rectangle', 'RoundedRectangle', 'Line', 'DashedLine', 'DashedVMobject', 'TangentLine', 'Elbow', 'Angle', 'RightAngle', 'ArrowTip', 'ArrowTriangleTip', 'ArrowTriangleFilledTip', 'ArrowCircleTip', 'ArrowCircleFilledTip', 'ArrowSquareTip', 'ArrowSquareFilledTip', 'StealthTip', 'Arrow', 'DoubleArrow', 'CurvedArrow', 'CurvedDoubleArrow',
           'Triangle', 'Polygon', 'Polygram', 'RegularPolygram', 'RegularPolygon', 'Star', 'Brace', 'BraceBetweenPoints', 'BraceLabel', 'BraceText',
           'Title', 'BulletedList', 'Tex', 'SingleStringMathTex', 'MarkupText', 'LabeledDot', 'Variable', 'always', 'f_always', 'always_shift', 'always_rotate',
           'SurroundingRectangle', 'BackgroundRectangle', 'Cross', 'Underline', 'Text', 'DecimalNumber', 'Integer', 'MathTex', 'Group', 'VGroup', 'NumberLine', 'Axes', 'BarChart', 'PolarPlane', 'NumberPlane', 'ComplexPlane', 'VectorField', 'ArrowVectorField', 'StreamLines', 'sigmoid', 'ScreenRectangle', 'FullScreenRectangle', 'VectorizedPoint', 'ComplexValueTracker', 'UnitInterval', 'TangentialArc', 'CurvesAsSubmobjects', 'VDict', 'Cutout', 'ConvexHull', 'ArcBrace', 'LaggedStartMap', 'MaintainPositionRelativeTo', 'Blink', 'Broadcast', 'SpiralIn', 'AddTextWordByWord', 'Animation', 'line_intersection', 'angle_between_vectors', 'DEFAULT_LAGGED_START_LAG_RATIO', 'Graph', 'DiGraph', 'Union', 'Intersection', 'Difference', 'Exclusion', 'Code', 'SVGMobject', 'VMobjectFromSVGPath', 'ImageMobject', 'RESAMPLING_ALGORITHMS', 'ManimColor', 'HSV', 'RGBA', 'LinearBase', 'LogBase', 'DefaultSectionType', 'Add', 'ShowPartial', 'TexTemplate', 'TexTemplateLibrary', 'TexFontTemplates', 'CoordinateSystem', 'PMobject', 'Mobject1D', 'Mobject2D', 'PGroup', 'PointCloudDot', 'Point', 'DEFAULT_POINT_DENSITY_1D', 'DEFAULT_POINT_DENSITY_2D', 'RandomColorGenerator', 'random_color', 'random_bright_color', 'TypeWithCursor', 'UntypeWithCursor', 'AnimatedBoundary', 'ShowPassingFlashWithThinningStrokeWidth', 'FadeTransformPieces', 'ImplicitFunction', 'LabeledPolygram', 'ChangeSpeed', 'Create', 'Write', 'Unwrite', 'DrawBorderThenFill', 'FadeIn',
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
# Community utilities (manim.utils.*).
EXPORTS += ['ManimBanner', 'MANIM_SVG_PATHS', 'SampleSpace', 'TransformAnimations', 'X_AXIS', 'Y_AXIS', 'Z_AXIS', 'DEFAULT_DASH_LENGTH', 'DEFAULT_POINTWISE_FUNCTION_RUN_TIME', 'DEFAULT_WAIT_TIME', 'SCALE_FACTOR_PER_FONT_POINT', 'START_X', 'START_Y', 'integer_interpolate', 'mid', 'inverse_interpolate', 'match_interpolate', 'midpoint', 'normalize', 'rotation_about_z', 'rotation_matrix', 'rotate_vector', 'z_to_vector', 'get_unit_normal', 'get_shaded_rgb', 'compass_directions', 'regular_vertices', 'complex_to_R3', 'R3_to_complex', 'complex_func_to_R3_func', 'center_of_mass', 'cross2d', 'shoelace', 'shoelace_direction', 'perpendicular_bisector', 'cartesian_to_spherical', 'spherical_to_cartesian', 'find_intersection', 'get_winding_number', 'thick_diagonal', 'bezier', 'split_bezier', 'partial_bezier_points', 'subdivide_bezier', 'bezier_remap', 'point_lies_on_bezier', 'proportions_along_bezier_curve_for_point', 'get_smooth_cubic_bezier_handle_points', 'is_closed', 'straight_path', 'path_along_arc', 'clockwise_path', 'counterclockwise_path', 'adjacent_n_tuples', 'adjacent_pairs', 'all_elements_are_instances', 'concatenate_lists', 'list_update', 'list_difference_update', 'listify', 'make_even', 'make_even_by_cycling', 'remove_list_redundancies', 'remove_nones', 'stretch_array_to_length', 'tuplify', 'choose', 'clip', 'binary_search', 'color_to_rgba', 'rgba_to_color', 'color_to_int_rgb', 'color_to_int_rgba', 'merge_dicts_recursively', 'update_dict_recursively', 'tempconfig', 'override_animate', 'override_animation', 'index_labels', 'print_family', 'assert_is_mobject_method', 'turn_animation_into_updater', 'cycle_animation']
EXPORTS += ['LineJointType', 'CapStyleType', 'register_font', 'Typst', 'MathTypst',
            'AS2700', 'BS381', 'DVIPSNAMES', 'SVGNAMES', 'X11', 'XKCD', 'quaternion_mult',
            'quaternion_from_angle_axis', 'angle_axis_from_quaternion', 'quaternion_conjugate', 'RendererType',
            'QUALITIES', 'DEFAULT_QUALITY', 'ParsableManimColor', 'ManimColorDType', 'Section', 'console',
            'error_console', 'Camera', 'MovingCamera', 'MultiCamera']


def _rounded_array(value):
    if type(value) is float:
        return round(value, 5) if math.isfinite(value) else value
    if type(value) is list:
        return [_rounded_array(item) for item in value]
    return value


def _flat_xy(value):
    """{'$xy': [x0, y0, ...], 'k': k} for planar points, or k-point groups of them."""
    first = value[0]
    if type(first) is not list or not first:
        return None
    if type(first[0]) is list:
        k = len(first)
        if not 1 <= k <= 64 or any(type(item) is not list or len(item) != k for item in value):
            return None
        points = [p for item in value for p in item]
    else:
        points, k = value, 0
    flat = []
    append = flat.append
    for p in points:
        if type(p) is not list or len(p) != 3 or p[2] != 0:
            return None
        for v in (p[0], p[1]):
            kind = type(v)
            if kind is float:
                append(round(v, 5))
            elif kind is int:
                append(v)
            else:
                return None
    return {'$xy': flat, 'k': k} if k else {'$xy': flat}


def _pooled_json(result, default):
    """Encode frames with each distinct mobject snapshot stored once in a shared pool.

    Nodes are pooled bottom-up: a pooled node's children are pool indices, and large
    arrays become {"$pool": index} references, always lower than the node's own index. Static objects and unchanged group members repeat across frames; the
    worker swaps indices for shared objects, so the page sees the ordinary frame format."""
    dumps = json.JSONEncoder(allow_nan=False, default=default, separators=(',', ':')).encode
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
                # Geometry arrays travel at 1e-5 scene units (far below a pixel); planar
                # point lists as flat XY pairs, grouped k per item (curves), if possible.
                text = dumps(_flat_xy(value) or _rounded_array(value))
                if len(text) > 400:
                    node[name] = {'$pool': store(text)}
        children = node.get('children')
        if isinstance(children, list) and children:
            node['children'] = [intern(child) for child in children]
        return store(dumps(node))
    frames = [dumps(dict(frame, mobjects=[intern(m) for m in frame['mobjects']])) for frame in result['frames']]
    head = dumps({key: value for key, value in result.items() if key != 'frames'})
    return head[:-1] + ', "pool": [' + ', '.join(pool) + '], "frames": [' + ', '.join(frames) + ']}'


class _SubmoduleFinder:
    """Serve any manim.* submodule as a package sharing the preview namespace."""
    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith('manim.') or 'manim' not in sys.modules:
            return None
        import importlib.machinery
        return importlib.machinery.ModuleSpec(fullname, self, is_package=True)

    def create_module(self, spec):
        module = types.ModuleType(spec.name)
        root = sys.modules['manim']
        module.__dict__.update({name: getattr(root, name) for name in root.__all__})
        module.__dict__.update({name: globals()[name] for name in _SUBMODULE_ONLY})
        module.__all__ = list(root.__all__)
        module.__path__ = []
        return module

    def exec_module(self, module):
        pass


# Community's color libraries (manim.utils.color.AS2700, BS381, DVIPSNAMES, SVGNAMES, X11, XKCD),
# as "NAME:RRGGBB" lists parsed on first use.
_COLOR_LIBRARIES = {
    'AS2700': ('B11_RICH_BLUE:2B3770 B12_ROYAL_BLUE:2C3563 B13_NAVY_BLUE:28304D B14_SAPHHIRE:28426B B15_MID_BLUE:144'
        'B6F B21_ULTRAMARINE:2C5098 B22_HOMEBUSH_BLUE:215097 B23_BRIGHT_BLUE:174F90 B24_HARBOUR_BLUE:1C6293 B'
        '25_AQUA:5097AC B32_POWDER_BLUE:B7C8DB B33_MIST_BLUE:E0E6E2 B34_PARADISE_BLUE:3499BA B35_PALE_BLUE:CD'
        'E4E2 B41_BLUEBELL:5B94D1 B42_PURPLE_BLUE:5E7899 B43_GREY_BLUE:627C8D B44_LIGHT_GREY_BLUE:C0C0C1 B45_'
        'SKY_BLUE:7DB7C7 B51_PERIWINKLE:3871AC B53_DARK_GREY_BLUE:4F6572 B55_STORM_BLUE:3F7C94 B61_CORAL_SEA:'
        '2B3873 B62_MIDNIGHT_BLUE:292A34 B64_CHARCOAL:363E45 G11_BOTTLE_GREEN:253A32 G12_HOLLY:21432D G13_EME'
        'RALD:195F35 G14_MOSS_GREEN:33572D G15_RAINFOREST_GREEN:3D492D G16_TRAFFIC_GREEN:305442 G17_MINT_GREE'
        'N:006B45 G21_JADE:127453 G22_SERPENTINE:78A681 G23_SHAMROCK:336634 G24_FERN_TREE:477036 G25_OLIVE:59'
        '5B2A G26_APPLE_GREEN:4E9843 G27_HOMEBUSH_GREEN:017F4D G31_VERTIGRIS:468A65 G32_OPALINE:AFCBB8 G33_LE'
        'TTUCE:7B9954 G34_AVOCADO:757C4C G35_LIME_GREEN:89922E G36_KIKUYU:95B43B G37_BEANSTALK:45A56A G41_LAW'
        'N_GREEN:0D875D G42_GLACIER:D5E1D2 G43_SURF_GREEN:C8C8A7 G44_PALM_GREEN:99B179 G45_CHARTREUSE:C7C98D '
        'G46_CITRONELLA:BFC83E G47_CRYSTAL_GREEN:ADCCA8 G51_SPRUCE:05674F G52_EUCALYPTUS:66755B G53_BANKSIA:9'
        '29479 G54_MIST_GREEN:7A836D G55_LICHEN:A7A98C G56_SAGE_GREEN:677249 G61_DARK_GREEN:283533 G62_RIVERG'
        'UM:617061 G63_DEEP_BRONZE_GREEN:333334 G64_SLATE:5E6153 G65_TI_TREE:5D5F4E G66_ENVIRONMENT_GREEN:484'
        'C3F G67_ZUCCHINI:2E443A N11_PEARL_GREY:D8D3C7 N12_PASTEL_GREY:CCCCCC N14_WHITE:FFFFFF N15_HOMEBUSH_G'
        'REY:A29B93 N22_CLOUD_GREY:C4C1B9 N23_NEUTRAL_GREY:CCCCCC N24_SILVER_GREY:BDC7C5 N25_BIRCH_GREY:ABA49'
        '8 N32_GREEN_GREY:8E9282 N33_LIGHTBOX_GREY:ACADAD N35_LIGHT_GREY:A6A7A1 N41_OYSTER:998F78 N42_STORM_G'
        'REY:858F88 N43_PIPELINE_GREY:999999 N44_BRIDGE_GREY:767779 N45_KOALA_GREY:928F88 N52_MID_GREY:727A77'
        ' N53_BLUE_GREY:7C8588 N54_BASALT:585C63 N55_LEAD_GREY:5E5C58 N61_BLACK:2A2A2C N63_PEWTER:596064 N64_'
        'DARK_GREY:4B5259 N65_GRAPHITE_GREY:45474A P11_MAGENTA:7B2B48 P12_PURPLE:85467B P13_VIOLET:5D3A61 P14'
        '_BLUEBERRY:4C4176 P21_SUNSET_PINK:E3BBBD P22_CYCLAMEN:83597D P23_LILAC:A69FB1 P24_JACKARANDA:795F91 '
        'P31_DUSTY_PINK:DBBEBC P33_RIBBON_PINK:D1BCC9 P41_ERICA_PINK:C55A83 P42_MULBERRY:A06574 P43_WISTERIA:'
        '756D91 P52_PLUM:6E3D4B R11_INTERNATIONAL_ORANGE:CE482A R12_SCARLET:CD392A R13_SIGNAL_RED:BA312B R14_'
        'WARATAH:AA2429 R15_CRIMSON:9E2429 R21_TANGERINE:E96957 R22_HOMEBUSH_RED:D83A2D R23_LOLLIPOP:CC5058 R'
        '24_STRAWBERRY:B4292A R25_ROSE_PINK:E8919C R32_APPLE_BLOSSOM:F2E1D8 R33_GHOST_GUM:E8DAD4 R34_MUSHROOM'
        ':D7C0B6 R35_DEEP_ROSE:CD6D71 R41_SHELL_PINK:F9D9BB R42_SALMON_PINK:D99679 R43_RED_DUST:D0674F R44_PO'
        'SSUM:A18881 R45_RUBY:8F3E5C R51_BURNT_PINK:E19B8E R52_TERRACOTTA:A04C36 R53_RED_GUM:8D4338 R54_RASPB'
        'ERRY:852F31 R55_CLARET:67292D R62_VENETIAN_RED:77372B R63_RED_OXIDE:663334 R64_DEEP_INDIAN_RED:542E2'
        'B R65_MAROON:3F2B3C T11_TROPICAL_BLUE:006698 T12_DIAMANTIA:006C74 T14_MALACHITE:105154 T15_TURQUOISE'
        ':098587 T22_ORIENTAL_BLUE:358792 T24_BLUE_JADE:427F7E T32_HUON_GREEN:72B3B1 T33_SMOKE_BLUE:9EB6B2 T3'
        '5_GREEN_ICE:78AEA2 T44_BLUE_GUM:6A8A88 T45_COOTAMUNDRA:759E91 T51_MOUNTAIN_BLUE:295668 T53_PEACOCK_B'
        'LUE:245764 T63_TEAL:183F4E X11_BUTTERSCOTCH:D38F43 X12_PUMPKIN:DD7E1A X13_MARIGOLD:ED7F15 X14_MANDAR'
        'IN:E45427 X15_ORANGE:E36C2B X21_PALE_OCHRE:DAA45F X22_SAFFRON:F6AA51 X23_APRICOT:FEB56D X24_ROCKMELO'
        'N:F6894B X31_RAFFIA:EBC695 X32_MAGNOLIA:F1DEBE X33_WARM_WHITE:F3E7D4 X34_DRIFTWOOD:D5C4AE X41_BUFF:C'
        '28A44 X42_BISCUIT:DEBA92 X43_BEIGE:C9AA8C X45_CINNAMON:AC826D X51_TAN:8F5F32 X52_COFFEE:AD7948 X53_G'
        'OLDEN_TAN:925629 X54_BROWN:68452C X55_NUT_BROWN:764832 X61_WOMBAT:6E5D52 X62_DARK_EARTH:6E5D52 X63_I'
        'RONBARK:443B36 X64_CHOCOLATE:4A3B31 X65_DARK_BROWN:4F372D Y11_CANARY:E7BD11 Y12_WATTLE:E8AF01 Y13_VI'
        'VID_YELLOW:FCAE01 Y14_GOLDEN_YELLOW:F5A601 Y15_SUNFLOWER:FFA709 Y16_INCA_GOLD:DF8C19 Y21_PRIMROSE:F5'
        'CF5B Y22_CUSTARD:EFD25C Y23_BUTTERCUP:E0CD41 Y24_STRAW:E3C882 Y25_DEEP_CREAM:F3C968 Y26_HOMEBUSH_GOL'
        'D:FCC51A Y31_LILY_GREEN:E3E3CD Y32_FLUMMERY:E6DF9E Y33_PALE_PRIMROSE:F5F3CE Y34_CREAM:EFE3BE Y35_OFF'
        '_WHITE:F1E9D5 Y41_OLIVE_YELLOW:8E7426 Y42_MUSTARD:C4A32E Y43_PARCHMENT:D4C9A3 Y44_SAND:DCC18B Y45_MA'
        'NILLA:E5D0A7 Y51_BRONZE_OLIVE:695D3E Y52_CHAMOIS:BEA873 Y53_SANDSTONE:D5BF8E Y54_OATMEAL:CAAE82 Y55_'
        'DEEP_STONE:BC9969 Y56_MERINO:C9B79E Y61_BLACK_OLIVE:47473B Y62_SUGAR_CANE:BCA55C Y63_KHAKI:826843 Y6'
        '5_MUSHROOM:A39281 Y66_MUDSTONE:574E45'),
    'BS381': ('BS381_101:94BFAC SKY_BLUE:94BFAC BS381_102:5B9291 TURQUOISE_BLUE:5B9291 BS381_103:3B6879 PEACOCK_BLU'
        'E:3B6879 BS381_104:264D7E AZURE_BLUE:264D7E BS381_105:1F3057 OXFORD_BLUE:1F3057 BS381_106:2A283D ROY'
        'AL_BLUE:2A283D BS381_107:3A73A9 STRONG_BLUE:3A73A9 BS381_108:173679 AIRCRAFT_BLUE:173679 BS381_109:1'
        'C5680 MIDDLE_BLUE:1C5680 BS381_110:2C3E75 ROUNDEL_BLUE:2C3E75 BS381_111:8CC5BB PALE_BLUE:8CC5BB BS38'
        '1_112:78ADC2 ARCTIC_BLUE:78ADC2 FIESTA_BLUE:78ADC2 BS381_113:3F687D DEEP_SAXE_BLUE:3F687D BS381_114:'
        '1F4B61 RAIL_BLUE:1F4B61 BS381_115:5F88C1 COBALT_BLUE:5F88C1 BS381_166:2458AF FRENCH_BLUE:2458AF BS38'
        '1_169:135B75 TRAFFIC_BLUE:135B75 BS381_172:A7C6EB PALE_ROUNDEL_BLUE:A7C6EB BS381_174:64A0AA ORIENT_B'
        'LUE:64A0AA BS381_175:4F81C5 LIGHT_FRENCH_BLUE:4F81C5 BS381_210:BBC9A5 SKY:BBC9A5 BS381_216:BCD890 EA'
        'U_DE_NIL:BCD890 BS381_217:96BF65 SEA_GREEN:96BF65 BS381_218:698B47 GRASS_GREEN:698B47 BS381_219:7576'
        '39 SAGE_GREEN:757639 BS381_220:4B5729 OLIVE_GREEN:4B5729 BS381_221:507D3A BRILLIANT_GREEN:507D3A BS3'
        '81_222:6A7031 LIGHT_BRONZE_GREEN:6A7031 BS381_223:49523A MIDDLE_BRONZE_GREEN:49523A BS381_224:3E4630'
        ' DEEP_BRONZE_GREEN:3E4630 BS381_225:406A28 LIGHT_BRUNSWICK_GREEN:406A28 BS381_226:33533B MID_BRUNSWI'
        'CK_GREEN:33533B BS381_227:254432 DEEP_BRUNSWICK_GREEN:254432 BS381_228:428B64 EMERALD_GREEN:428B64 B'
        'S381_241:4F5241 DARK_GREEN:4F5241 BS381_262:44945E BOLD_GREEN:44945E BS381_267:476A4C DEEP_CHROME_GR'
        'EEN:476A4C TRAFFIC_GREEN:476A4C BS381_275:8FC693 OPALINE_GREEN:8FC693 BS381_276:2E4C1E LINCON_GREEN:'
        '2E4C1E BS381_277:364A20 CYPRESS_GREEN:364A20 BS381_278:87965A LIGHT_OLIVE_GREEN:87965A BS381_279:3B3'
        '629 STEEL_FURNITURE_GREEN:3B3629 BS381_280:68AB77 VERDIGRIS_GREEN:68AB77 BS381_282:506B52 FOREST_GRE'
        'EN:506B52 BS381_283:7E8F6E AIRCRAFT_GREY_GREEN:7E8F6E BS381_284:6B6F5A SPRUCE_GREEN:6B6F5A BS381_285'
        ':5F5C4B NATO_GREEN:5F5C4B BS381_298:4F5138 OLIVE_DRAB:4F5138 BS381_309:FEEC04 CANARY_YELLOW:FEEC04 B'
        'S381_310:FEF963 PRIMROSE:FEF963 BS381_315:FEF96A GRAPEFRUIT:FEF96A BS381_320:9E7339 LIGHT_BROWN:9E73'
        '39 BS381_337:4C4A3C VERY_DARK_DRAB:4C4A3C BS381_350:7B6B4F DARK_EARTH:7B6B4F BS381_352:FCED96 PALE_C'
        'REAM:FCED96 BS381_353:FDF07A DEEP_CREAM:FDF07A BS381_354:E9BB43 PRIMROSE_2:E9BB43 BS381_355:FDD906 L'
        'EMON:FDD906 BS381_356:FCC808 GOLDEN_YELLOW:FCC808 BS381_358:F6C870 LIGHT_BUFF:F6C870 BS381_359:DBAC5'
        '0 MIDDLE_BUFF:DBAC50 BS381_361:D4B97D LIGHT_STONE:D4B97D BS381_362:AC7C42 MIDDLE_STONE:AC7C42 BS381_'
        '363:FDE706 BOLD_YELLOW:FDE706 BS381_364:CEC093 PORTLAND_STONE:CEC093 BS381_365:F4F0BD VELLUM:F4F0BD '
        'BS381_366:F5E7A1 LIGHT_BEIGE:F5E7A1 BS381_367:FEF6BF MANILLA:FEF6BF BS381_368:DD7B00 TRAFFIC_YELLOW:'
        'DD7B00 BS381_369:FEEBA8 BISCUIT:FEEBA8 BS381_380:BBA38A CAMOUFLAGE_DESERT_SAND:BBA38A BS381_384:EEDF'
        'A5 LIGHT_STRAW:EEDFA5 BS381_385:E8C88F LIGHT_BISCUIT:E8C88F BS381_386:E6C18D CHAMPAGNE:E6C18D BS381_'
        '387:CFB48A SUNRISE:CFB48A SUNSHINE:CFB48A BS381_388:E4CF93 BEIGE:E4CF93 BS381_389:B2A788 CAMOUFLAGE_'
        'BEIGE:B2A788 BS381_397:F3D163 JASMINE_YELLOW:F3D163 BS381_411:74542F MIDDLE_BROWN:74542F BS381_412:5'
        'C422E DARK_BROWN:5C422E BS381_413:402D21 NUT_BROWN:402D21 BS381_414:A86C29 GOLDEN_BROWN:A86C29 BS381'
        '_415:61361E IMPERIAL_BROWN:61361E BS381_420:A89177 DARK_CAMOUFLAGE_DESERT_SAND:A89177 BS381_435:845B'
        '4D CAMOUFLAGE_RED:845B4D BS381_436:564B47 DARK_CAMOUFLAGE_BROWN:564B47 BS381_439:753B1E ORANGE_BROWN'
        ':753B1E BS381_443:C98A71 SALMON:C98A71 BS381_444:A65341 TERRACOTTA:A65341 BS381_445:83422B VENETIAN_'
        'RED:83422B BS381_446:774430 RED_OXIDE:774430 BS381_447:F3B28B SALMON_PINK:F3B28B BS381_448:67403A DE'
        'EP_INDIAN_RED:67403A BS381_449:693B3F LIGHT_PURPLE_BROWN:693B3F BS381_452:613339 DARK_CRIMSON:613339'
        ' BS381_453:FBDED6 SHELL_PINK:FBDED6 BS381_454:E8A1A2 PALE_ROUNDEL_RED:E8A1A2 BS381_460:BD8F56 DEEP_B'
        'UFF:BD8F56 BS381_473:793932 GULF_RED:793932 BS381_489:8D5B41 LEAF_BROWN:8D5B41 BS381_490:573320 BEEC'
        'H_BROWN:573320 BS381_499:59493E SERVICE_BROWN:59493E BS381_536:BB3016 POPPY:BB3016 BS381_537:DD3420 '
        'SIGNAL_RED:DD3420 BS381_538:C41C22 POST_OFFICE_RED:C41C22 CHERRY:C41C22 BS381_539:D21E2B CURRANT_RED'
        ':D21E2B BS381_540:8B1A32 CRIMSON:8B1A32 BS381_541:471B21 MAROON:471B21 BS381_542:982D57 RUBY:982D57 '
        'BS381_557:EF841E LIGHT_ORANGE:EF841E BS381_564:DD3524 BOLD_RED:DD3524 BS381_568:FB9C06 APRICOT:FB9C0'
        '6 BS381_570:A83C19 TRAFFIC_RED:A83C19 BS381_591:D04E09 DEEP_ORANGE:D04E09 BS381_592:E45523 INTERNATI'
        'ONAL_ORANGE:E45523 BS381_593:F24816 RAIL_RED:F24816 AZO_ORANGE:F24816 BS381_626:A0A9AA CAMOUFLAGE_GR'
        'EY:A0A9AA BS381_627:BEC0B8 LIGHT_AIRCRAFT_GREY:BEC0B8 BS381_628:9D9D7E SILVER_GREY:9D9D7E BS381_629:'
        '7A838B DARK_CAMOUFLAGE_GREY:7A838B BS381_630:A5AD98 FRENCH_GREY:A5AD98 BS381_631:9AAA9F LIGHT_GREY:9'
        'AAA9F BS381_632:6B7477 DARK_ADMIRALTY_GREY:6B7477 BS381_633:424C53 RAF_BLUE_GREY:424C53 BS381_634:6F'
        '7264 SLATE:6F7264 BS381_635:525B55 LEAD:525B55 BS381_636:5F7682 PRU_BLUE:5F7682 BS381_637:8E9B9C MED'
        'IUM_SEA_GREY:8E9B9C BS381_638:6C7377 DARK_SEA_GREY:6C7377 BS381_639:667563 LIGHT_SLATE_GREY:667563 B'
        'S381_640:566164 EXTRA_DARK_SEA_GREY:566164 BS381_642:282B2F NIGHT:282B2F BS381_671:4E5355 MIDDLE_GRA'
        'PHITE:4E5355 BS381_676:A9B7B9 LIGHT_WEATHERWORK_GREY:A9B7B9 BS381_677:676F76 DARK_WEATHERWORK_GREY:6'
        '76F76 BS381_692:7B93A3 SMOKE_GREY:7B93A3 BS381_693:88918D AIRCRAFT_GREY:88918D BS381_694:909A92 DOVE'
        '_GREY:909A92 BS381_697:B6D3CC LIGHT_ADMIRALTY_GREY:B6D3CC BS381_796:6E4A75 DARK_VIOLET:6E4A75 BS381_'
        '797:C9A8CE LIGHT_VIOLET:C9A8CE'),
    'DVIPSNAMES': ('AQUAMARINE:00B5BE BITTERSWEET:C04F17 APRICOT:FBB982 BLACK:221E1F BLUE:2D2F92 BLUEGREEN:00B3B8 BLUEVI'
        'OLET:473992 BRICKRED:B6321C BROWN:792500 BURNTORANGE:F7921D CADETBLUE:74729A CARNATIONPINK:F282B4 CE'
        'RULEAN:00A2E3 CORNFLOWERBLUE:41B0E4 CYAN:00AEEF DANDELION:FDBC42 DARKORCHID:A4538A EMERALD:00A99D FO'
        'RESTGREEN:009B55 FUCHSIA:8C368C GOLDENROD:FFDF42 GRAY:949698 GREEN:00A64F GREENYELLOW:DFE674 JUNGLEG'
        'REEN:00A99A LAVENDER:F49EC4 LIMEGREEN:8DC73E MAGENTA:EC008C MAHOGANY:A9341F MAROON:AF3235 MELON:F89E'
        '7B MIDNIGHTBLUE:006795 MULBERRY:A93C93 NAVYBLUE:006EB8 OLIVEGREEN:3C8031 ORANGE:F58137 ORANGERED:ED1'
        '35A ORCHID:AF72B0 PEACH:F7965A PERIWINKLE:7977B8 PINEGREEN:008B72 PLUM:92268F PROCESSBLUE:00B0F0 PUR'
        'PLE:99479B RAWSIENNA:974006 RED:ED1B23 REDORANGE:F26035 REDVIOLET:A1246B RHODAMINE:EF559F ROYALBLUE:'
        '0071BC ROYALPURPLE:613F99 RUBINERED:ED017D SALMON:F69289 SEAGREEN:3FBC9D SEPIA:671800 SKYBLUE:46C5DD'
        ' SPRINGGREEN:C6DC67 TAN:DA9D76 TEALBLUE:00AEB3 THISTLE:D883B7 TURQUOISE:00B4CE VIOLET:58429B VIOLETR'
        'ED:EF58A0 WHITE:FFFFFF WILDSTRAWBERRY:EE2967 YELLOW:FFF200 YELLOWGREEN:98CC70 YELLOWORANGE:FAA21A'),
    'SVGNAMES': ('ALICEBLUE:EFF7FF ANTIQUEWHITE:F9EAD7 AQUA:00FFFF AQUAMARINE:7EFFD3 AZURE:EFFFFF BEIGE:F4F4DC BISQUE:'
        'FFE3C4 BLACK:000000 BLANCHEDALMOND:FFEACD BLUE:0000FF BLUEVIOLET:892BE2 BROWN:A52A2A BURLYWOOD:DDB78'
        '7 CADETBLUE:5E9EA0 CHARTREUSE:7EFF00 CHOCOLATE:D2681D CORAL:FF7E4F CORNFLOWERBLUE:6395ED CORNSILK:FF'
        'F7DC CRIMSON:DC143B CYAN:00FFFF DARKBLUE:00008A DARKCYAN:008A8A DARKGOLDENROD:B7850B DARKGRAY:A9A9A9'
        ' DARKGREEN:006300 DARKGREY:A9A9A9 DARKKHAKI:BCB66B DARKMAGENTA:8A008A DARKOLIVEGREEN:546B2F DARKORAN'
        'GE:FF8C00 DARKORCHID:9931CC DARKRED:8A0000 DARKSALMON:E8967A DARKSEAGREEN:8EBB8E DARKSLATEBLUE:483D8'
        'A DARKSLATEGRAY:2F4F4F DARKSLATEGREY:2F4F4F DARKTURQUOISE:00CED1 DARKVIOLET:9300D3 DEEPPINK:FF1492 D'
        'EEPSKYBLUE:00BFFF DIMGRAY:686868 DIMGREY:686868 DODGERBLUE:1D90FF FIREBRICK:B12121 FLORALWHITE:FFF9E'
        'F FORESTGREEN:218A21 FUCHSIA:FF00FF GAINSBORO:DCDCDC GHOSTWHITE:F7F7FF GOLD:FFD700 GOLDENROD:DAA51F '
        'GRAY:7F7F7F GREEN:007F00 GREENYELLOW:ADFF2F GREY:7F7F7F HONEYDEW:EFFFEF HOTPINK:FF68B3 INDIANRED:CD5'
        'B5B INDIGO:4A0082 IVORY:FFFFEF KHAKI:EFE58C LAVENDER:E5E5F9 LAVENDERBLUSH:FFEFF4 LAWNGREEN:7CFC00 LE'
        'MONCHIFFON:FFF9CD LIGHTBLUE:ADD8E5 LIGHTCORAL:EF7F7F LIGHTCYAN:E0FFFF LIGHTGOLDENROD:EDDD82 LIGHTGOL'
        'DENRODYELLOW:F9F9D2 LIGHTGRAY:D3D3D3 LIGHTGREEN:90ED90 LIGHTGREY:D3D3D3 LIGHTPINK:FFB5C0 LIGHTSALMON'
        ':FFA07A LIGHTSEAGREEN:1FB1AA LIGHTSKYBLUE:87CEF9 LIGHTSLATEBLUE:8470FF LIGHTSLATEGRAY:778799 LIGHTSL'
        'ATEGREY:778799 LIGHTSTEELBLUE:AFC4DD LIGHTYELLOW:FFFFE0 LIME:00FF00 LIMEGREEN:31CD31 LINEN:F9EFE5 MA'
        'GENTA:FF00FF MAROON:7F0000 MEDIUMAQUAMARINE:66CDAA MEDIUMBLUE:0000CD MEDIUMORCHID:BA54D3 MEDIUMPURPL'
        'E:9270DB MEDIUMSEAGREEN:3BB271 MEDIUMSLATEBLUE:7B68ED MEDIUMSPRINGGREEN:00F99A MEDIUMTURQUOISE:48D1C'
        'C MEDIUMVIOLETRED:C61584 MIDNIGHTBLUE:181870 MINTCREAM:F4FFF9 MISTYROSE:FFE3E1 MOCCASIN:FFE3B5 NAVAJ'
        'OWHITE:FFDDAD NAVY:00007F NAVYBLUE:00007F OLDLACE:FCF4E5 OLIVE:7F7F00 OLIVEDRAB:6B8D22 ORANGE:FFA500'
        ' ORANGERED:FF4400 ORCHID:DA70D6 PALEGOLDENROD:EDE8AA PALEGREEN:97FB97 PALETURQUOISE:AFEDED PALEVIOLE'
        'TRED:DB7092 PAPAYAWHIP:FFEED4 PEACHPUFF:FFDAB8 PERU:CD843F PINK:FFBFCA PLUM:DDA0DD POWDERBLUE:AFE0E5'
        ' PURPLE:7F007F RED:FF0000 ROSYBROWN:BB8E8E ROYALBLUE:4168E1 SADDLEBROWN:8A4413 SALMON:F97F72 SANDYBR'
        'OWN:F3A45F SEAGREEN:2D8A56 SEASHELL:FFF4ED SIENNA:A0512C SILVER:BFBFBF SKYBLUE:87CEEA SLATEBLUE:6959'
        'CD SLATEGRAY:707F90 SLATEGREY:707F90 SNOW:FFF9F9 SPRINGGREEN:00FF7E STEELBLUE:4682B3 TAN:D2B38C TEAL'
        ':007F7F THISTLE:D8BFD8 TOMATO:FF6347 TURQUOISE:3FE0CF VIOLET:ED82ED VIOLETRED:D01F90 WHEAT:F4DDB2 WH'
        'ITE:FFFFFF WHITESMOKE:F4F4F4 YELLOW:FFFF00 YELLOWGREEN:9ACD30'),
    'X11': ('ALICEBLUE:F0F8FF ANTIQUEWHITE:FAEBD7 ANTIQUEWHITE1:FFEFDB ANTIQUEWHITE2:EEDFCC ANTIQUEWHITE3:CDC0B0 '
        'ANTIQUEWHITE4:8B8378 AQUAMARINE1:7FFFD4 AQUAMARINE2:76EEC6 AQUAMARINE4:458B74 AZURE1:F0FFFF AZURE2:E'
        '0EEEE AZURE3:C1CDCD AZURE4:838B8B BEIGE:F5F5DC BISQUE1:FFE4C4 BISQUE2:EED5B7 BISQUE3:CDB79E BISQUE4:'
        '8B7D6B BLACK:000000 BLANCHEDALMOND:FFEBCD BLUE1:0000FF BLUE2:0000EE BLUE4:00008B BLUEVIOLET:8A2BE2 B'
        'ROWN:A52A2A BROWN1:FF4040 BROWN2:EE3B3B BROWN3:CD3333 BROWN4:8B2323 BURLYWOOD:DEB887 BURLYWOOD1:FFD3'
        '9B BURLYWOOD2:EEC591 BURLYWOOD3:CDAA7D BURLYWOOD4:8B7355 CADETBLUE:5F9EA0 CADETBLUE1:98F5FF CADETBLU'
        'E2:8EE5EE CADETBLUE3:7AC5CD CADETBLUE4:53868B CHARTREUSE1:7FFF00 CHARTREUSE2:76EE00 CHARTREUSE3:66CD'
        '00 CHARTREUSE4:458B00 CHOCOLATE:D2691E CHOCOLATE1:FF7F24 CHOCOLATE2:EE7621 CHOCOLATE3:CD661D CORAL:F'
        'F7F50 CORAL1:FF7256 CORAL2:EE6A50 CORAL3:CD5B45 CORAL4:8B3E2F CORNFLOWERBLUE:6495ED CORNSILK1:FFF8DC'
        ' CORNSILK2:EEE8CD CORNSILK3:CDC8B1 CORNSILK4:8B8878 CYAN1:00FFFF CYAN2:00EEEE CYAN3:00CDCD CYAN4:008'
        'B8B DARKGOLDENROD:B8860B DARKGOLDENROD1:FFB90F DARKGOLDENROD2:EEAD0E DARKGOLDENROD3:CD950C DARKGOLDE'
        'NROD4:8B6508 DARKGREEN:006400 DARKKHAKI:BDB76B DARKOLIVEGREEN:556B2F DARKOLIVEGREEN1:CAFF70 DARKOLIV'
        'EGREEN2:BCEE68 DARKOLIVEGREEN3:A2CD5A DARKOLIVEGREEN4:6E8B3D DARKORANGE:FF8C00 DARKORANGE1:FF7F00 DA'
        'RKORANGE2:EE7600 DARKORANGE3:CD6600 DARKORANGE4:8B4500 DARKORCHID:9932CC DARKORCHID1:BF3EFF DARKORCH'
        'ID2:B23AEE DARKORCHID3:9A32CD DARKORCHID4:68228B DARKSALMON:E9967A DARKSEAGREEN:8FBC8F DARKSEAGREEN1'
        ':C1FFC1 DARKSEAGREEN2:B4EEB4 DARKSEAGREEN3:9BCD9B DARKSEAGREEN4:698B69 DARKSLATEBLUE:483D8B DARKSLAT'
        'EGRAY:2F4F4F DARKSLATEGRAY1:97FFFF DARKSLATEGRAY2:8DEEEE DARKSLATEGRAY3:79CDCD DARKSLATEGRAY4:528B8B'
        ' DARKTURQUOISE:00CED1 DARKVIOLET:9400D3 DEEPPINK1:FF1493 DEEPPINK2:EE1289 DEEPPINK3:CD1076 DEEPPINK4'
        ':8B0A50 DEEPSKYBLUE1:00BFFF DEEPSKYBLUE2:00B2EE DEEPSKYBLUE3:009ACD DEEPSKYBLUE4:00688B DIMGRAY:6969'
        '69 DODGERBLUE1:1E90FF DODGERBLUE2:1C86EE DODGERBLUE3:1874CD DODGERBLUE4:104E8B FIREBRICK:B22222 FIRE'
        'BRICK1:FF3030 FIREBRICK2:EE2C2C FIREBRICK3:CD2626 FIREBRICK4:8B1A1A FLORALWHITE:FFFAF0 FORESTGREEN:2'
        '28B22 GAINSBORO:DCDCDC GHOSTWHITE:F8F8FF GOLD1:FFD700 GOLD2:EEC900 GOLD3:CDAD00 GOLD4:8B7500 GOLDENR'
        'OD:DAA520 GOLDENROD1:FFC125 GOLDENROD2:EEB422 GOLDENROD3:CD9B1D GOLDENROD4:8B6914 GRAY:BEBEBE GRAY1:'
        '030303 GRAY2:050505 GRAY3:080808 GRAY4:0A0A0A GRAY5:0D0D0D GRAY6:0F0F0F GRAY7:121212 GRAY8:141414 GR'
        'AY9:171717 GRAY10:1A1A1A GRAY11:1C1C1C GRAY12:1F1F1F GRAY13:212121 GRAY14:242424 GRAY15:262626 GRAY1'
        '6:292929 GRAY17:2B2B2B GRAY18:2E2E2E GRAY19:303030 GRAY20:333333 GRAY21:363636 GRAY22:383838 GRAY23:'
        '3B3B3B GRAY24:3D3D3D GRAY25:404040 GRAY26:424242 GRAY27:454545 GRAY28:474747 GRAY29:4A4A4A GRAY30:4D'
        '4D4D GRAY31:4F4F4F GRAY32:525252 GRAY33:545454 GRAY34:575757 GRAY35:595959 GRAY36:5C5C5C GRAY37:5E5E'
        '5E GRAY38:616161 GRAY39:636363 GRAY40:666666 GRAY41:696969 GRAY42:6B6B6B GRAY43:6E6E6E GRAY44:707070'
        ' GRAY45:737373 GRAY46:757575 GRAY47:787878 GRAY48:7A7A7A GRAY49:7D7D7D GRAY50:7F7F7F GRAY51:828282 G'
        'RAY52:858585 GRAY53:878787 GRAY54:8A8A8A GRAY55:8C8C8C GRAY56:8F8F8F GRAY57:919191 GRAY58:949494 GRA'
        'Y59:969696 GRAY60:999999 GRAY61:9C9C9C GRAY62:9E9E9E GRAY63:A1A1A1 GRAY64:A3A3A3 GRAY65:A6A6A6 GRAY6'
        '6:A8A8A8 GRAY67:ABABAB GRAY68:ADADAD GRAY69:B0B0B0 GRAY70:B3B3B3 GRAY71:B5B5B5 GRAY72:B8B8B8 GRAY73:'
        'BABABA GRAY74:BDBDBD GRAY75:BFBFBF GRAY76:C2C2C2 GRAY77:C4C4C4 GRAY78:C7C7C7 GRAY79:C9C9C9 GRAY80:CC'
        'CCCC GRAY81:CFCFCF GRAY82:D1D1D1 GRAY83:D4D4D4 GRAY84:D6D6D6 GRAY85:D9D9D9 GRAY86:DBDBDB GRAY87:DEDE'
        'DE GRAY88:E0E0E0 GRAY89:E3E3E3 GRAY90:E5E5E5 GRAY91:E8E8E8 GRAY92:EBEBEB GRAY93:EDEDED GRAY94:F0F0F0'
        ' GRAY95:F2F2F2 GRAY97:F7F7F7 GRAY98:FAFAFA GRAY99:FCFCFC GREEN1:00FF00 GREEN2:00EE00 GREEN3:00CD00 G'
        'REEN4:008B00 GREENYELLOW:ADFF2F HONEYDEW1:F0FFF0 HONEYDEW2:E0EEE0 HONEYDEW3:C1CDC1 HONEYDEW4:838B83 '
        'HOTPINK:FF69B4 HOTPINK1:FF6EB4 HOTPINK2:EE6AA7 HOTPINK3:CD6090 HOTPINK4:8B3A62 INDIANRED:CD5C5C INDI'
        'ANRED1:FF6A6A INDIANRED2:EE6363 INDIANRED3:CD5555 INDIANRED4:8B3A3A IVORY1:FFFFF0 IVORY2:EEEEE0 IVOR'
        'Y3:CDCDC1 IVORY4:8B8B83 KHAKI:F0E68C KHAKI1:FFF68F KHAKI2:EEE685 KHAKI3:CDC673 KHAKI4:8B864E LAVENDE'
        'R:E6E6FA LAVENDERBLUSH1:FFF0F5 LAVENDERBLUSH2:EEE0E5 LAVENDERBLUSH3:CDC1C5 LAVENDERBLUSH4:8B8386 LAW'
        'NGREEN:7CFC00 LEMONCHIFFON1:FFFACD LEMONCHIFFON2:EEE9BF LEMONCHIFFON3:CDC9A5 LEMONCHIFFON4:8B8970 LI'
        'GHT:EEDD82 LIGHTBLUE:ADD8E6 LIGHTBLUE1:BFEFFF LIGHTBLUE2:B2DFEE LIGHTBLUE3:9AC0CD LIGHTBLUE4:68838B '
        'LIGHTCORAL:F08080 LIGHTCYAN1:E0FFFF LIGHTCYAN2:D1EEEE LIGHTCYAN3:B4CDCD LIGHTCYAN4:7A8B8B LIGHTGOLDE'
        'NROD1:FFEC8B LIGHTGOLDENROD2:EEDC82 LIGHTGOLDENROD3:CDBE70 LIGHTGOLDENROD4:8B814C LIGHTGOLDENRODYELL'
        'OW:FAFAD2 LIGHTGRAY:D3D3D3 LIGHTPINK:FFB6C1 LIGHTPINK1:FFAEB9 LIGHTPINK2:EEA2AD LIGHTPINK3:CD8C95 LI'
        'GHTPINK4:8B5F65 LIGHTSALMON1:FFA07A LIGHTSALMON2:EE9572 LIGHTSALMON3:CD8162 LIGHTSALMON4:8B5742 LIGH'
        'TSEAGREEN:20B2AA LIGHTSKYBLUE:87CEFA LIGHTSKYBLUE1:B0E2FF LIGHTSKYBLUE2:A4D3EE LIGHTSKYBLUE3:8DB6CD '
        'LIGHTSKYBLUE4:607B8B LIGHTSLATEBLUE:8470FF LIGHTSLATEGRAY:778899 LIGHTSTEELBLUE:B0C4DE LIGHTSTEELBLU'
        'E1:CAE1FF LIGHTSTEELBLUE2:BCD2EE LIGHTSTEELBLUE3:A2B5CD LIGHTSTEELBLUE4:6E7B8B LIGHTYELLOW1:FFFFE0 L'
        'IGHTYELLOW2:EEEED1 LIGHTYELLOW3:CDCDB4 LIGHTYELLOW4:8B8B7A LIMEGREEN:32CD32 LINEN:FAF0E6 MAGENTA:FF0'
        '0FF MAGENTA2:EE00EE MAGENTA3:CD00CD MAGENTA4:8B008B MAROON:B03060 MAROON1:FF34B3 MAROON2:EE30A7 MARO'
        'ON3:CD2990 MAROON4:8B1C62 MEDIUM:66CDAA MEDIUMAQUAMARINE:66CDAA MEDIUMBLUE:0000CD MEDIUMORCHID:BA55D'
        '3 MEDIUMORCHID1:E066FF MEDIUMORCHID2:D15FEE MEDIUMORCHID3:B452CD MEDIUMORCHID4:7A378B MEDIUMPURPLE:9'
        '370DB MEDIUMPURPLE1:AB82FF MEDIUMPURPLE2:9F79EE MEDIUMPURPLE3:8968CD MEDIUMPURPLE4:5D478B MEDIUMSEAG'
        'REEN:3CB371 MEDIUMSLATEBLUE:7B68EE MEDIUMSPRINGGREEN:00FA9A MEDIUMTURQUOISE:48D1CC MEDIUMVIOLETRED:C'
        '71585 MIDNIGHTBLUE:191970 MINTCREAM:F5FFFA MISTYROSE1:FFE4E1 MISTYROSE2:EED5D2 MISTYROSE3:CDB7B5 MIS'
        'TYROSE4:8B7D7B MOCCASIN:FFE4B5 NAVAJOWHITE1:FFDEAD NAVAJOWHITE2:EECFA1 NAVAJOWHITE3:CDB38B NAVAJOWHI'
        'TE4:8B795E NAVYBLUE:000080 OLDLACE:FDF5E6 OLIVEDRAB:6B8E23 OLIVEDRAB1:C0FF3E OLIVEDRAB2:B3EE3A OLIVE'
        'DRAB4:698B22 ORANGE1:FFA500 ORANGE2:EE9A00 ORANGE3:CD8500 ORANGE4:8B5A00 ORANGERED1:FF4500 ORANGERED'
        '2:EE4000 ORANGERED3:CD3700 ORANGERED4:8B2500 ORCHID:DA70D6 ORCHID1:FF83FA ORCHID2:EE7AE9 ORCHID3:CD6'
        '9C9 ORCHID4:8B4789 PALE:DB7093 PALEGOLDENROD:EEE8AA PALEGREEN:98FB98 PALEGREEN1:9AFF9A PALEGREEN2:90'
        'EE90 PALEGREEN3:7CCD7C PALEGREEN4:548B54 PALETURQUOISE:AFEEEE PALETURQUOISE1:BBFFFF PALETURQUOISE2:A'
        'EEEEE PALETURQUOISE3:96CDCD PALETURQUOISE4:668B8B PALEVIOLETRED:DB7093 PALEVIOLETRED1:FF82AB PALEVIO'
        'LETRED2:EE799F PALEVIOLETRED3:CD6889 PALEVIOLETRED4:8B475D PAPAYAWHIP:FFEFD5 PEACHPUFF1:FFDAB9 PEACH'
        'PUFF2:EECBAD PEACHPUFF3:CDAF95 PEACHPUFF4:8B7765 PINK:FFC0CB PINK1:FFB5C5 PINK2:EEA9B8 PINK3:CD919E '
        'PINK4:8B636C PLUM:DDA0DD PLUM1:FFBBFF PLUM2:EEAEEE PLUM3:CD96CD PLUM4:8B668B POWDERBLUE:B0E0E6 PURPL'
        'E:A020F0 PURPLE1:9B30FF PURPLE2:912CEE PURPLE3:7D26CD PURPLE4:551A8B RED1:FF0000 RED2:EE0000 RED3:CD'
        '0000 RED4:8B0000 ROSYBROWN:BC8F8F ROSYBROWN1:FFC1C1 ROSYBROWN2:EEB4B4 ROSYBROWN3:CD9B9B ROSYBROWN4:8'
        'B6969 ROYALBLUE:4169E1 ROYALBLUE1:4876FF ROYALBLUE2:436EEE ROYALBLUE3:3A5FCD ROYALBLUE4:27408B SADDL'
        'EBROWN:8B4513 SALMON:FA8072 SALMON1:FF8C69 SALMON2:EE8262 SALMON3:CD7054 SALMON4:8B4C39 SANDYBROWN:F'
        '4A460 SEAGREEN1:54FF9F SEAGREEN2:4EEE94 SEAGREEN3:43CD80 SEAGREEN4:2E8B57 SEASHELL1:FFF5EE SEASHELL2'
        ':EEE5DE SEASHELL3:CDC5BF SEASHELL4:8B8682 SIENNA:A0522D SIENNA1:FF8247 SIENNA2:EE7942 SIENNA3:CD6839'
        ' SIENNA4:8B4726 SKYBLUE:87CEEB SKYBLUE1:87CEFF SKYBLUE2:7EC0EE SKYBLUE3:6CA6CD SKYBLUE4:4A708B SLATE'
        'BLUE:6A5ACD SLATEBLUE1:836FFF SLATEBLUE2:7A67EE SLATEBLUE3:6959CD SLATEBLUE4:473C8B SLATEGRAY:708090'
        ' SLATEGRAY1:C6E2FF SLATEGRAY2:B9D3EE SLATEGRAY3:9FB6CD SLATEGRAY4:6C7B8B SNOW1:FFFAFA SNOW2:EEE9E9 S'
        'NOW3:CDC9C9 SNOW4:8B8989 SPRINGGREEN1:00FF7F SPRINGGREEN2:00EE76 SPRINGGREEN3:00CD66 SPRINGGREEN4:00'
        '8B45 STEELBLUE:4682B4 STEELBLUE1:63B8FF STEELBLUE2:5CACEE STEELBLUE3:4F94CD STEELBLUE4:36648B TAN:D2'
        'B48C TAN1:FFA54F TAN2:EE9A49 TAN3:CD853F TAN4:8B5A2B THISTLE:D8BFD8 THISTLE1:FFE1FF THISTLE2:EED2EE '
        'THISTLE3:CDB5CD THISTLE4:8B7B8B TOMATO1:FF6347 TOMATO2:EE5C42 TOMATO3:CD4F39 TOMATO4:8B3626 TURQUOIS'
        'E:40E0D0 TURQUOISE1:00F5FF TURQUOISE2:00E5EE TURQUOISE3:00C5CD TURQUOISE4:00868B VIOLET:EE82EE VIOLE'
        'TRED:D02090 VIOLETRED1:FF3E96 VIOLETRED2:EE3A8C VIOLETRED3:CD3278 VIOLETRED4:8B2252 WHEAT:F5DEB3 WHE'
        'AT1:FFE7BA WHEAT2:EED8AE WHEAT3:CDBA96 WHEAT4:8B7E66 WHITE:FFFFFF WHITESMOKE:F5F5F5 YELLOW1:FFFF00 Y'
        'ELLOW2:EEEE00 YELLOW3:CDCD00 YELLOW4:8B8B00 YELLOWGREEN:9ACD32'),
    'XKCD': ('ACIDGREEN:8FFE09 ADOBE:BD6C48 ALGAE:54AC68 ALGAEGREEN:21C36F ALMOSTBLACK:070D0D AMBER:FEB308 AMETHYS'
        'T:9B5FC0 APPLE:6ECB3C APPLEGREEN:76CD26 APRICOT:FFB16D AQUA:13EAC9 AQUABLUE:02D8E9 AQUAGREEN:12E193 '
        'AQUAMARINE:2EE8BB ARMYGREEN:4B5D16 ASPARAGUS:77AB56 AUBERGINE:3D0734 AUBURN:9A3001 AVOCADO:90B134 AV'
        'OCADOGREEN:87A922 AZUL:1D5DEC AZURE:069AF3 BABYBLUE:A2CFFE BABYGREEN:8CFF9E BABYPINK:FFB7CE BABYPOO:'
        'AB9004 BABYPOOP:937C00 BABYPOOPGREEN:8F9805 BABYPUKEGREEN:B6C406 BABYPURPLE:CA9BF7 BABYSHITBROWN:AD9'
        '00D BABYSHITGREEN:889717 BANANA:FFFF7E BANANAYELLOW:FAFE4B BARBIEPINK:FE46A5 BARFGREEN:94AC02 BARNEY'
        ':AC1DB8 BARNEYPURPLE:A00498 BATTLESHIPGREY:6B7C85 BEIGE:E6DAA6 BERRY:990F4B BILE:B5C306 BLACK:000000'
        ' BLAND:AFA88B BLOOD:770001 BLOODORANGE:FE4B03 BLOODRED:980002 BLUE:0343DF BLUEBERRY:464196 BLUEBLUE:'
        '2242C7 BLUEGREEN:0F9B8E BLUEGREY:85A3B2 BLUEPURPLE:5A06EF BLUEVIOLET:5D06E9 BLUEWITHAHINTOFPURPLE:53'
        '3CC6 BLUEYGREEN:2BB179 BLUEYGREY:89A0B0 BLUEYPURPLE:6241C7 BLUISH:2976BB BLUISHGREEN:10A674 BLUISHGR'
        'EY:748B97 BLUISHPURPLE:703BE7 BLURPLE:5539CC BLUSH:F29E8E BLUSHPINK:FE828C BOOGER:9BB53C BOOGERGREEN'
        ':96B403 BORDEAUX:7B002C BORINGGREEN:63B365 BOTTLEGREEN:044A05 BRICK:A03623 BRICKORANGE:C14A09 BRICKR'
        'ED:8F1402 BRIGHTAQUA:0BF9EA BRIGHTBLUE:0165FC BRIGHTCYAN:41FDFE BRIGHTGREEN:01FF07 BRIGHTLAVENDER:C7'
        '60FF BRIGHTLIGHTBLUE:26F7FD BRIGHTLIGHTGREEN:2DFE54 BRIGHTLILAC:C95EFB BRIGHTLIME:87FD05 BRIGHTLIMEG'
        'REEN:65FE08 BRIGHTMAGENTA:FF08E8 BRIGHTOLIVE:9CBB04 BRIGHTORANGE:FF5B00 BRIGHTPINK:FE01B1 BRIGHTPURP'
        'LE:BE03FD BRIGHTRED:FF000D BRIGHTSEAGREEN:05FFA6 BRIGHTSKYBLUE:02CCFE BRIGHTTEAL:01F9C6 BRIGHTTURQUO'
        'ISE:0FFEF9 BRIGHTVIOLET:AD0AFD BRIGHTYELLOW:FFFD01 BRIGHTYELLOWGREEN:9DFF00 BRITISHRACINGGREEN:05480'
        'D BRONZE:A87900 BROWN:653700 BROWNGREEN:706C11 BROWNGREY:8D8468 BROWNISH:9C6D57 BROWNISHGREEN:6A6E09'
        ' BROWNISHGREY:86775F BROWNISHORANGE:CB7723 BROWNISHPINK:C27E79 BROWNISHPURPLE:76424E BROWNISHRED:9E3'
        '623 BROWNISHYELLOW:C9B003 BROWNORANGE:B96902 BROWNRED:922B05 BROWNYELLOW:B29705 BROWNYGREEN:6F6C0A B'
        'ROWNYORANGE:CA6B02 BRUISE:7E4071 BUBBLEGUM:FF6CB5 BUBBLEGUMPINK:FF69AF BUFF:FEF69E BURGUNDY:610023 B'
        'URNTORANGE:C04E01 BURNTRED:9F2305 BURNTSIENA:B75203 BURNTSIENNA:B04E0F BURNTUMBER:A0450E BURNTYELLOW'
        ':D5AB09 BURPLE:6832E3 BUTTER:FFFF81 BUTTERSCOTCH:FDB147 BUTTERYELLOW:FFFD74 CADETBLUE:4E7496 CAMEL:C'
        '69F59 CAMO:7F8F4E CAMOGREEN:526525 CAMOUFLAGEGREEN:4B6113 CANARY:FDFF63 CANARYYELLOW:FFFE40 CANDYPIN'
        'K:FF63E9 CARAMEL:AF6F09 CARMINE:9D0216 CARNATION:FD798F CARNATIONPINK:FF7FA7 CAROLINABLUE:8AB8FE CEL'
        'ADON:BEFDB7 CELERY:C1FD95 CEMENT:A5A391 CERISE:DE0C62 CERULEAN:0485D1 CERULEANBLUE:056EEE CHARCOAL:3'
        '43837 CHARCOALGREY:3C4142 CHARTREUSE:C1F80A CHERRY:CF0234 CHERRYRED:F7022A CHESTNUT:742802 CHOCOLATE'
        ':3D1C02 CHOCOLATEBROWN:411900 CINNAMON:AC4F06 CLARET:680018 CLAY:B66A50 CLAYBROWN:B2713D CLEARBLUE:2'
        '47AFD COBALT:1E488F COBALTBLUE:030AA7 COCOA:875F42 COFFEE:A6814C COOLBLUE:4984B8 COOLGREEN:33B864 CO'
        'OLGREY:95A3A6 COPPER:B66325 CORAL:FC5A50 CORALPINK:FF6163 CORNFLOWER:6A79F7 CORNFLOWERBLUE:5170D7 CR'
        'ANBERRY:9E003A CREAM:FFFFC2 CREME:FFFFB6 CRIMSON:8C000F CUSTARD:FFFD78 CYAN:00FFFF DANDELION:FEDF08 '
        'DARK:1B2431 DARKAQUA:05696B DARKAQUAMARINE:017371 DARKBEIGE:AC9362 DARKBLUE:030764 DARKBLUEGREEN:005'
        '249 DARKBLUEGREY:1F3B4D DARKBROWN:341C02 DARKCORAL:CF524E DARKCREAM:FFF39A DARKCYAN:0A888A DARKFORES'
        'TGREEN:002D04 DARKFUCHSIA:9D0759 DARKGOLD:B59410 DARKGRASSGREEN:388004 DARKGREEN:054907 DARKGREENBLU'
        'E:1F6357 DARKGREY:363737 DARKGREYBLUE:29465B DARKHOTPINK:D90166 DARKINDIGO:1F0954 DARKISHBLUE:014182'
        ' DARKISHGREEN:287C37 DARKISHPINK:DA467D DARKISHPURPLE:751973 DARKISHRED:A90308 DARKKHAKI:9B8F55 DARK'
        'LAVENDER:856798 DARKLILAC:9C6DA5 DARKLIME:84B701 DARKLIMEGREEN:7EBD01 DARKMAGENTA:960056 DARKMAROON:'
        '3C0008 DARKMAUVE:874C62 DARKMINT:48C072 DARKMINTGREEN:20C073 DARKMUSTARD:A88905 DARKNAVY:000435 DARK'
        'NAVYBLUE:00022E DARKOLIVE:373E02 DARKOLIVEGREEN:3C4D03 DARKORANGE:C65102 DARKPASTELGREEN:56AE57 DARK'
        'PEACH:DE7E5D DARKPERIWINKLE:665FD1 DARKPINK:CB416B DARKPLUM:3F012C DARKPURPLE:35063E DARKRED:840000 '
        'DARKROSE:B5485D DARKROYALBLUE:02066F DARKSAGE:598556 DARKSALMON:C85A53 DARKSAND:A88F59 DARKSEAFOAM:1'
        'FB57A DARKSEAFOAMGREEN:3EAF76 DARKSEAGREEN:11875D DARKSKYBLUE:448EE4 DARKSLATEBLUE:214761 DARKTAN:AF'
        '884A DARKTAUPE:7F684E DARKTEAL:014D4E DARKTURQUOISE:045C5A DARKVIOLET:34013F DARKYELLOW:D5B60A DARKY'
        'ELLOWGREEN:728F02 DEEPAQUA:08787F DEEPBLUE:040273 DEEPBROWN:410200 DEEPGREEN:02590F DEEPLAVENDER:8D5'
        'EB7 DEEPLILAC:966EBD DEEPMAGENTA:A0025C DEEPORANGE:DC4D01 DEEPPINK:CB0162 DEEPPURPLE:36013F DEEPRED:'
        '9A0200 DEEPROSE:C74767 DEEPSEABLUE:015482 DEEPSKYBLUE:0D75F8 DEEPTEAL:00555A DEEPTURQUOISE:017374 DE'
        'EPVIOLET:490648 DENIM:3B638C DENIMBLUE:3B5B92 DESERT:CCAD60 DIARRHEA:9F8303 DIRT:8A6E45 DIRTBROWN:83'
        '6539 DIRTYBLUE:3F829D DIRTYGREEN:667E2C DIRTYORANGE:C87606 DIRTYPINK:CA7B80 DIRTYPURPLE:734A65 DIRTY'
        'YELLOW:CDC50A DODGERBLUE:3E82FC DRAB:828344 DRABGREEN:749551 DRIEDBLOOD:4B0101 DUCKEGGBLUE:C3FBF4 DU'
        'LLBLUE:49759C DULLBROWN:876E4B DULLGREEN:74A662 DULLORANGE:D8863B DULLPINK:D5869D DULLPURPLE:84597E '
        'DULLRED:BB3F3F DULLTEAL:5F9E8F DULLYELLOW:EEDC5B DUSK:4E5481 DUSKBLUE:26538D DUSKYBLUE:475F94 DUSKYP'
        'INK:CC7A8B DUSKYPURPLE:895B7B DUSKYROSE:BA6873 DUST:B2996E DUSTYBLUE:5A86AD DUSTYGREEN:76A973 DUSTYL'
        'AVENDER:AC86A8 DUSTYORANGE:F0833A DUSTYPINK:D58A94 DUSTYPURPLE:825F87 DUSTYRED:B9484E DUSTYROSE:C073'
        '7A DUSTYTEAL:4C9085 EARTH:A2653E EASTERGREEN:8CFD7E EASTERPURPLE:C071FE ECRU:FEFFCA EGGPLANT:380835 '
        'EGGPLANTPURPLE:430541 EGGSHELL:FFFCC4 EGGSHELLBLUE:C4FFF7 ELECTRICBLUE:0652FF ELECTRICGREEN:21FC0D E'
        'LECTRICLIME:A8FF04 ELECTRICPINK:FF0490 ELECTRICPURPLE:AA23FF EMERALD:01A049 EMERALDGREEN:028F1E EVER'
        'GREEN:05472A FADEDBLUE:658CBB FADEDGREEN:7BB274 FADEDORANGE:F0944D FADEDPINK:DE9DAC FADEDPURPLE:916E'
        '99 FADEDRED:D3494E FADEDYELLOW:FEFF7F FAWN:CFAF7B FERN:63A950 FERNGREEN:548D44 FIREENGINERED:FE0002 '
        'FLATBLUE:3C73A8 FLATGREEN:699D4C FLUORESCENTGREEN:08FF08 FLUROGREEN:0AFF02 FOAMGREEN:90FDA9 FOREST:0'
        'B5509 FORESTGREEN:06470C FORRESTGREEN:154406 FRENCHBLUE:436BAD FRESHGREEN:69D84F FROGGREEN:58BC08 FU'
        'CHSIA:ED0DD9 GOLD:DBB40C GOLDEN:F5BF03 GOLDENBROWN:B27A01 GOLDENROD:F9BC08 GOLDENYELLOW:FEC615 GRAPE'
        ':6C3461 GRAPEFRUIT:FD5956 GRAPEPURPLE:5D1451 GRASS:5CAC2D GRASSGREEN:3F9B0B GRASSYGREEN:419C03 GREEN'
        ':15B01A GREENAPPLE:5EDC1F GREENBLUE:01C08D GREENBROWN:544E03 GREENGREY:77926F GREENISH:40A368 GREENI'
        'SHBEIGE:C9D179 GREENISHBLUE:0B8B87 GREENISHBROWN:696112 GREENISHCYAN:2AFEB7 GREENISHGREY:96AE8D GREE'
        'NISHTAN:BCCB7A GREENISHTEAL:32BF84 GREENISHTURQUOISE:00FBB0 GREENISHYELLOW:CDFD02 GREENTEAL:0CB577 G'
        'REENYBLUE:42B395 GREENYBROWN:696006 GREENYELLOW:B5CE08 GREENYGREY:7EA07A GREENYYELLOW:C6F808 GREY:92'
        '9591 GREYBLUE:647D8E GREYBROWN:7F7053 GREYGREEN:86A17D GREYISH:A8A495 GREYISHBLUE:5E819D GREYISHBROW'
        'N:7A6A4F GREYISHGREEN:82A67D GREYISHPINK:C88D94 GREYISHPURPLE:887191 GREYISHTEAL:719F91 GREYPINK:C39'
        '09B GREYPURPLE:826D8C GREYTEAL:5E9B8A GROSSGREEN:A0BF16 GUNMETAL:536267 HAZEL:8E7618 HEATHER:A484AC '
        'HELIOTROPE:D94FF5 HIGHLIGHTERGREEN:1BFC06 HOSPITALGREEN:9BE5AA HOTGREEN:25FF29 HOTMAGENTA:F504C9 HOT'
        'PINK:FF028D HOTPURPLE:CB00F5 HUNTERGREEN:0B4008 ICE:D6FFFA ICEBLUE:D7FFFE ICKYGREEN:8FAE22 INDIANRED'
        ':850E04 INDIGO:380282 INDIGOBLUE:3A18B1 IRIS:6258C4 IRISHGREEN:019529 IVORY:FFFFCB JADE:1FA774 JADEG'
        'REEN:2BAF6A JUNGLEGREEN:048243 KELLEYGREEN:009337 KELLYGREEN:02AB2E KERMITGREEN:5CB200 KEYLIME:AEFF6'
        'E KHAKI:AAA662 KHAKIGREEN:728639 KIWI:9CEF43 KIWIGREEN:8EE53F LAVENDER:C79FEF LAVENDERBLUE:8B88F8 LA'
        'VENDERPINK:DD85D7 LAWNGREEN:4DA409 LEAF:71AA34 LEAFGREEN:5CA904 LEAFYGREEN:51B73B LEATHER:AC7434 LEM'
        'ON:FDFF52 LEMONGREEN:ADF802 LEMONLIME:BFFE28 LEMONYELLOW:FDFF38 LICHEN:8FB67B LIGHTAQUA:8CFFDB LIGHT'
        'AQUAMARINE:7BFDC7 LIGHTBEIGE:FFFEB6 LIGHTBLUE:7BC8F6 LIGHTBLUEGREEN:7EFBB3 LIGHTBLUEGREY:B7C9E2 LIGH'
        'TBLUISHGREEN:76FDA8 LIGHTBRIGHTGREEN:53FE5C LIGHTBROWN:AD8150 LIGHTBURGUNDY:A8415B LIGHTCYAN:ACFFFC '
        'LIGHTEGGPLANT:894585 LIGHTERGREEN:75FD63 LIGHTERPURPLE:A55AF4 LIGHTFORESTGREEN:4F9153 LIGHTGOLD:FDDC'
        '5C LIGHTGRASSGREEN:9AF764 LIGHTGREEN:76FF7B LIGHTGREENBLUE:56FCA2 LIGHTGREENISHBLUE:63F7B4 LIGHTGREY'
        ':D8DCD6 LIGHTGREYBLUE:9DBCD4 LIGHTGREYGREEN:B7E1A1 LIGHTINDIGO:6D5ACF LIGHTISHBLUE:3D7AFD LIGHTISHGR'
        'EEN:61E160 LIGHTISHPURPLE:A552E6 LIGHTISHRED:FE2F4A LIGHTKHAKI:E6F2A2 LIGHTLAVENDAR:EFC0FE LIGHTLAVE'
        'NDER:DFC5FE LIGHTLIGHTBLUE:CAFFFB LIGHTLIGHTGREEN:C8FFB0 LIGHTLILAC:EDC8FF LIGHTLIME:AEFD6C LIGHTLIM'
        'EGREEN:B9FF66 LIGHTMAGENTA:FA5FF7 LIGHTMAROON:A24857 LIGHTMAUVE:C292A1 LIGHTMINT:B6FFBB LIGHTMINTGRE'
        'EN:A6FBB2 LIGHTMOSSGREEN:A6C875 LIGHTMUSTARD:F7D560 LIGHTNAVY:155084 LIGHTNAVYBLUE:2E5A88 LIGHTNEONG'
        'REEN:4EFD54 LIGHTOLIVE:ACBF69 LIGHTOLIVEGREEN:A4BE5C LIGHTORANGE:FDAA48 LIGHTPASTELGREEN:B2FBA5 LIGH'
        'TPEACH:FFD8B1 LIGHTPEAGREEN:C4FE82 LIGHTPERIWINKLE:C1C6FC LIGHTPINK:FFD1DF LIGHTPLUM:9D5783 LIGHTPUR'
        'PLE:BF77F6 LIGHTRED:FF474C LIGHTROSE:FFC5CB LIGHTROYALBLUE:3A2EFE LIGHTSAGE:BCECAC LIGHTSALMON:FEA99'
        '3 LIGHTSEAFOAM:A0FEBF LIGHTSEAFOAMGREEN:A7FFB5 LIGHTSEAGREEN:98F6B0 LIGHTSKYBLUE:C6FCFF LIGHTTAN:FBE'
        'EAC LIGHTTEAL:90E4C1 LIGHTTURQUOISE:7EF4CC LIGHTURPLE:B36FF6 LIGHTVIOLET:D6B4FC LIGHTYELLOW:FFFE7A L'
        'IGHTYELLOWGREEN:CCFD7F LIGHTYELLOWISHGREEN:C2FF89 LILAC:CEA2FD LILIAC:C48EFD LIME:AAFF32 LIMEGREEN:8'
        '9FE05 LIMEYELLOW:D0FE1D LIPSTICK:D5174E LIPSTICKRED:C0022F MACARONIANDCHEESE:EFB435 MAGENTA:C20078 M'
        'AHOGANY:4A0100 MAIZE:F4D054 MANGO:FFA62B MANILLA:FFFA86 MARIGOLD:FCC006 MARINE:042E60 MARINEBLUE:013'
        '86A MAROON:650021 MAUVE:AE7181 MEDIUMBLUE:2C6FBB MEDIUMBROWN:7F5112 MEDIUMGREEN:39AD48 MEDIUMGREY:7D'
        '7F7C MEDIUMPINK:F36196 MEDIUMPURPLE:9E43A2 MELON:FF7855 MERLOT:730039 METALLICBLUE:4F738E MIDBLUE:27'
        '6AB3 MIDGREEN:50A747 MIDNIGHT:03012D MIDNIGHTBLUE:020035 MIDNIGHTPURPLE:280137 MILITARYGREEN:667C3E '
        'MILKCHOCOLATE:7F4E1E MINT:9FFEB0 MINTGREEN:8FFF9F MINTYGREEN:0BF77D MOCHA:9D7651 MOSS:769958 MOSSGRE'
        'EN:658B38 MOSSYGREEN:638B27 MUD:735C12 MUDBROWN:60460F MUDDYBROWN:886806 MUDDYGREEN:657432 MUDDYYELL'
        'OW:BFAC05 MUDGREEN:606602 MULBERRY:920A4E MURKYGREEN:6C7A0E MUSHROOM:BA9E88 MUSTARD:CEB301 MUSTARDBR'
        'OWN:AC7E04 MUSTARDGREEN:A8B504 MUSTARDYELLOW:D2BD0A MUTEDBLUE:3B719F MUTEDGREEN:5FA052 MUTEDPINK:D17'
        '68F MUTEDPURPLE:805B87 NASTYGREEN:70B23F NAVY:01153E NAVYBLUE:001146 NAVYGREEN:35530A NEONBLUE:04D9F'
        'F NEONGREEN:0CFF0C NEONPINK:FE019A NEONPURPLE:BC13FE NEONRED:FF073A NEONYELLOW:CFFF04 NICEBLUE:107AB'
        '0 NIGHTBLUE:040348 OCEAN:017B92 OCEANBLUE:03719C OCEANGREEN:3D9973 OCHER:BF9B0C OCHRE:BF9005 OCRE:C6'
        '9C04 OFFBLUE:5684AE OFFGREEN:6BA353 OFFWHITE:FFFFE4 OFFYELLOW:F1F33F OLDPINK:C77986 OLDROSE:C87F89 O'
        'LIVE:6E750E OLIVEBROWN:645403 OLIVEDRAB:6F7632 OLIVEGREEN:677A04 OLIVEYELLOW:C2B709 ORANGE:F97306 OR'
        'ANGEBROWN:BE6400 ORANGEISH:FD8D49 ORANGEPINK:FF6F52 ORANGERED:FE420F ORANGEYBROWN:B16002 ORANGEYELLO'
        'W:FFAD01 ORANGEYRED:FA4224 ORANGEYYELLOW:FDB915 ORANGISH:FC824A ORANGISHBROWN:B25F03 ORANGISHRED:F43'
        '605 ORCHID:C875C4 PALE:FFF9D0 PALEAQUA:B8FFEB PALEBLUE:D0FEFE PALEBROWN:B1916E PALECYAN:B7FFFA PALEG'
        'OLD:FDDE6C PALEGREEN:C7FDB5 PALEGREY:FDFDFE PALELAVENDER:EECFFE PALELIGHTGREEN:B1FC99 PALELILAC:E4CB'
        'FF PALELIME:BEFD73 PALELIMEGREEN:B1FF65 PALEMAGENTA:D767AD PALEMAUVE:FED0FC PALEOLIVE:B9CC81 PALEOLI'
        'VEGREEN:B1D27B PALEORANGE:FFA756 PALEPEACH:FFE5AD PALEPINK:FFCFDC PALEPURPLE:B790D4 PALERED:D9544D P'
        'ALEROSE:FDC1C5 PALESALMON:FFB19A PALESKYBLUE:BDF6FE PALETEAL:82CBB2 PALETURQUOISE:A5FBD5 PALEVIOLET:'
        'CEAEFA PALEYELLOW:FFFF84 PARCHMENT:FEFCAF PASTELBLUE:A2BFFE PASTELGREEN:B0FF9D PASTELORANGE:FF964F P'
        'ASTELPINK:FFBACD PASTELPURPLE:CAA0FF PASTELRED:DB5856 PASTELYELLOW:FFFE71 PEA:A4BF20 PEACH:FFB07C PE'
        'ACHYPINK:FF9A8A PEACOCKBLUE:016795 PEAGREEN:8EAB12 PEAR:CBF85F PEASOUP:929901 PEASOUPGREEN:94A617 PE'
        'RIWINKLE:8E82FE PERIWINKLEBLUE:8F99FB PERRYWINKLE:8F8CE7 PETROL:005F6A PIGPINK:E78EA5 PINE:2B5D34 PI'
        'NEGREEN:0A481E PINK:FF81C0 PINKISH:D46A7E PINKISHBROWN:B17261 PINKISHGREY:C8ACA9 PINKISHORANGE:FF724'
        'C PINKISHPURPLE:D648D7 PINKISHRED:F10C45 PINKISHTAN:D99B82 PINKPURPLE:EF1DE7 PINKRED:F5054F PINKY:FC'
        '86AA PINKYPURPLE:C94CBE PINKYRED:FC2647 PISSYELLOW:DDD618 PISTACHIO:C0FA8B PLUM:580F41 PLUMPURPLE:4E'
        '0550 POISONGREEN:40FD14 POO:8F7303 POOBROWN:885F01 POOP:7F5E00 POOPBROWN:7A5901 POOPGREEN:6F7C00 POW'
        'DERBLUE:B1D1FC POWDERPINK:FFB2D0 PRIMARYBLUE:0804F9 PRUSSIANBLUE:004577 PUCE:A57E52 PUKE:A5A502 PUKE'
        'BROWN:947706 PUKEGREEN:9AAE07 PUKEYELLOW:C2BE0E PUMPKIN:E17701 PUMPKINORANGE:FB7D07 PUREBLUE:0203E2 '
        'PURPLE:7E1E9C PURPLEBLUE:5D21D0 PURPLEBROWN:673A3F PURPLEGREY:866F85 PURPLEISH:98568D PURPLEISHBLUE:'
        '6140EF PURPLEISHPINK:DF4EC8 PURPLEPINK:D725DE PURPLERED:990147 PURPLEY:8756E4 PURPLEYBLUE:5F34E7 PUR'
        'PLEYGREY:947E94 PURPLEYPINK:C83CB9 PURPLISH:94568C PURPLISHBLUE:601EF9 PURPLISHBROWN:6B4247 PURPLISH'
        'GREY:7A687F PURPLISHPINK:CE5DAE PURPLISHRED:B0054B PURPLY:983FB2 PURPLYBLUE:661AEE PURPLYPINK:F075E6'
        ' PUTTY:BEAE8A RACINGGREEN:014600 RADIOACTIVEGREEN:2CFA1F RASPBERRY:B00149 RAWSIENNA:9A6200 RAWUMBER:'
        'A75E09 REALLYLIGHTBLUE:D4FFFF RED:E50000 REDBROWN:8B2E16 REDDISH:C44240 REDDISHBROWN:7F2B0A REDDISHG'
        'REY:997570 REDDISHORANGE:F8481C REDDISHPINK:FE2C54 REDDISHPURPLE:910951 REDDYBROWN:6E1005 REDORANGE:'
        'FD3C06 REDPINK:FA2A55 REDPURPLE:820747 REDVIOLET:9E0168 REDWINE:8C0034 RICHBLUE:021BF9 RICHPURPLE:72'
        '0058 ROBINEGGBLUE:8AF1FE ROBINSEGG:6DEDFD ROBINSEGGBLUE:98EFF9 ROSA:FE86A4 ROSE:CF6275 ROSEPINK:F787'
        '9A ROSERED:BE013C ROSYPINK:F6688E ROGUE:AB1239 ROYAL:0C1793 ROYALBLUE:0504AA ROYALPURPLE:4B006E RUBY'
        ':CA0147 RUSSET:A13905 RUST:A83C09 RUSTBROWN:8B3103 RUSTORANGE:C45508 RUSTRED:AA2704 RUSTYORANGE:CD59'
        '09 RUSTYRED:AF2F0D SAFFRON:FEB209 SAGE:87AE73 SAGEGREEN:88B378 SALMON:FF796C SALMONPINK:FE7B7C SAND:'
        'E2CA76 SANDBROWN:CBA560 SANDSTONE:C9AE74 SANDY:F1DA7A SANDYBROWN:C4A661 SANDYELLOW:FCE166 SANDYYELLO'
        'W:FDEE73 SAPGREEN:5C8B15 SAPPHIRE:2138AB SCARLET:BE0119 SEA:3C9992 SEABLUE:047495 SEAFOAM:80F9AD SEA'
        'FOAMBLUE:78D1B6 SEAFOAMGREEN:7AF9AB SEAGREEN:53FCA1 SEAWEED:18D17B SEAWEEDGREEN:35AD6B SEPIA:985E2B '
        'SHAMROCK:01B44C SHAMROCKGREEN:02C14D SHIT:7F5F00 SHITBROWN:7B5804 SHITGREEN:758000 SHOCKINGPINK:FE02'
        'A2 SICKGREEN:9DB92C SICKLYGREEN:94B21C SICKLYYELLOW:D0E429 SIENNA:A9561E SILVER:C5C9C7 SKY:82CAFC SK'
        'YBLUE:75BBFD SLATE:516572 SLATEBLUE:5B7C99 SLATEGREEN:658D6D SLATEGREY:59656D SLIMEGREEN:99CC04 SNOT'
        ':ACBB0D SNOTGREEN:9DC100 SOFTBLUE:6488EA SOFTGREEN:6FC276 SOFTPINK:FDB0C0 SOFTPURPLE:A66FB5 SPEARMIN'
        'T:1EF876 SPRINGGREEN:A9F971 SPRUCE:0A5F38 SQUASH:F2AB15 STEEL:738595 STEELBLUE:5A7D9A STEELGREY:6F82'
        '8A STONE:ADA587 STORMYBLUE:507B9C STRAW:FCF679 STRAWBERRY:FB2943 STRONGBLUE:0C06F7 STRONGPINK:FF0789'
        ' SUNFLOWER:FFC512 SUNFLOWERYELLOW:FFDA03 SUNNYYELLOW:FFF917 SUNSHINEYELLOW:FFFD37 SUNYELLOW:FFDF22 S'
        'WAMP:698339 SWAMPGREEN:748500 TAN:D1B26F TANBROWN:AB7E4C TANGERINE:FF9408 TANGREEN:A9BE70 TAUPE:B9A2'
        '81 TEA:65AB7C TEAGREEN:BDF8A3 TEAL:029386 TEALBLUE:01889F TEALGREEN:25A36F TEALISH:24BCA8 TEALISHGRE'
        'EN:0CDC73 TERRACOTA:CB6843 TERRACOTTA:C9643B TIFFANYBLUE:7BF2DA TOMATO:EF4026 TOMATORED:EC2D01 TOPAZ'
        ':13BBAF TOUPE:C7AC7D TOXICGREEN:61DE2A TREEGREEN:2A7E19 TRUEBLUE:010FCC TRUEGREEN:089404 TURQUOISE:0'
        '6C2AC TURQUOISEBLUE:06B1C4 TURQUOISEGREEN:04F489 TURTLEGREEN:75B84F TWILIGHT:4E518B TWILIGHTBLUE:0A4'
        '37A UGLYBLUE:31668A UGLYBROWN:7D7103 UGLYGREEN:7A9703 UGLYPINK:CD7584 UGLYPURPLE:A442A0 UGLYYELLOW:D'
        '0C101 ULTRAMARINE:2000B1 ULTRAMARINEBLUE:1805DB UMBER:B26400 VELVET:750851 VERMILION:F4320C VERYDARK'
        'BLUE:000133 VERYDARKBROWN:1D0200 VERYDARKGREEN:062E03 VERYDARKPURPLE:2A0134 VERYLIGHTBLUE:D5FFFF VER'
        'YLIGHTBROWN:D3B683 VERYLIGHTGREEN:D1FFBD VERYLIGHTPINK:FFF4F2 VERYLIGHTPURPLE:F6CEFC VERYPALEBLUE:D6'
        'FFFE VERYPALEGREEN:CFFDBC VIBRANTBLUE:0339F8 VIBRANTGREEN:0ADD08 VIBRANTPURPLE:AD03DE VIOLET:9A0EEA '
        'VIOLETBLUE:510AC9 VIOLETPINK:FB5FFC VIOLETRED:A50055 VIRIDIAN:1E9167 VIVIDBLUE:152EFF VIVIDGREEN:2FE'
        'F10 VIVIDPURPLE:9900FA VOMIT:A2A415 VOMITGREEN:89A203 VOMITYELLOW:C7C10C WARMBLUE:4B57DB WARMBROWN:9'
        '64E02 WARMGREY:978A84 WARMPINK:FB5581 WARMPURPLE:952E8F WASHEDOUTGREEN:BCF5A6 WATERBLUE:0E87CC WATER'
        'MELON:FD4659 WEIRDGREEN:3AE57F WHEAT:FBDD7E WHITE:FFFFFF WINDOWSBLUE:3778BF WINE:80013F WINERED:7B03'
        '23 WINTERGREEN:20F986 WISTERIA:A87DC2 YELLOW:FFFF14 YELLOWBROWN:B79400 YELLOWGREEN:BBF90F YELLOWISH:'
        'FAEE66 YELLOWISHBROWN:9B7A01 YELLOWISHGREEN:B0DD16 YELLOWISHORANGE:FFAB0F YELLOWISHTAN:FCFC81 YELLOW'
        'OCHRE:CB9D06 YELLOWORANGE:FCB001 YELLOWTAN:FFE36E YELLOWYBROWN:AE8B0C YELLOWYGREEN:BFF128'),
}


class _ColorLibrary(types.ModuleType):
    """A Community color module: attribute access to its ManimColor constants."""
    def __init__(self, name):
        super().__init__(f'manim.utils.color.{name}')
        self._library = name

    def _colors(self):
        if '_parsed' not in self.__dict__:
            self._parsed = {key: ManimColor('#' + value) for key, value in
                            (item.split(':') for item in _COLOR_LIBRARIES[self._library].split())}
        return self._parsed

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            return self._colors()[name]
        except KeyError:
            raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}") from None

    def __dir__(self):
        return list(self._colors())


AS2700, BS381, DVIPSNAMES, SVGNAMES, X11, XKCD = (_ColorLibrary(name) for name in
                                                  ('AS2700', 'BS381', 'DVIPSNAMES', 'SVGNAMES', 'X11', 'XKCD'))


def quaternion_mult(*quats):
    """Community's quaternion product of [w, x, y, z] lists."""
    if not quats:
        return [1, 0, 0, 0]
    result = list(quats[0])
    for following in quats[1:]:
        w1, x1, y1, z1 = result
        w2, x2, y2, z2 = following
        result = [w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                  w1 * y2 + y1 * w2 + z1 * x2 - x1 * z2, w1 * z2 + z1 * w2 + x1 * y2 - y1 * x2]
    return result


def quaternion_from_angle_axis(angle, axis, axis_normalized=False):
    axis = Vector(axis) if axis_normalized else normalize(axis)
    return [math.cos(angle / 2), *(math.sin(angle / 2) * value for value in axis)]


def angle_axis_from_quaternion(quaternion):
    axis = normalize(list(quaternion)[1:], fall_back=Vector((1, 0, 0)))
    angle = 2 * math.acos(quaternion[0])
    if angle > TAU / 2:
        angle, axis = TAU - angle, -Vector(axis)
    return angle, axis


def quaternion_conjugate(quaternion):
    w, *rest = list(quaternion)
    return [w] + [-value for value in rest]


class RendererType(str, enum.Enum):
    """Community's renderer choice; the preview always draws like the Cairo renderer."""
    CAIRO = 'cairo'
    OPENGL = 'opengl'


QUALITIES = {
    'fourk_quality': {'flag': 'k', 'pixel_height': 2160, 'pixel_width': 3840, 'frame_rate': 60},
    'production_quality': {'flag': 'p', 'pixel_height': 1440, 'pixel_width': 2560, 'frame_rate': 60},
    'high_quality': {'flag': 'h', 'pixel_height': 1080, 'pixel_width': 1920, 'frame_rate': 60},
    'medium_quality': {'flag': 'm', 'pixel_height': 720, 'pixel_width': 1280, 'frame_rate': 30},
    'low_quality': {'flag': 'l', 'pixel_height': 480, 'pixel_width': 854, 'frame_rate': 15},
    'example_quality': {'flag': None, 'pixel_height': 480, 'pixel_width': 854, 'frame_rate': 30},
}
DEFAULT_QUALITY = 'high_quality'
ParsableManimColor = typing.Union['ManimColor', str, int, tuple, list]
ManimColorDType = float


class Section:
    """Community's video section record (the preview records sections without video files)."""
    def __init__(self, type_, video, name, skip_animations):
        self.type_, self.video, self.name, self.skip_animations = type_, video, name, skip_animations
        self.partial_movie_files = []

    def is_empty(self):
        return not self.partial_movie_files

    def __repr__(self):
        return f"<Section '{self.name}' stored in '{self.video}'>"


class _Console:
    """Community's rich console: prints to the browser console."""
    def print(self, *objects, **kwargs):
        print(*objects)

    log = print


console = error_console = _Console()


_SUBMODULE_NAMES = frozenset((
    'animation', 'camera', 'mobject', 'scene', 'constants', 'typing', 'color', 'manim_colors', 'unit', 'core',
    'data_structures', 'opengl', 'renderer', 'utils', 'paths', 'rate_functions', 'space_ops', 'bezier',
    'iterables', 'simple_functions', 'config_ops', 'tex', 'tex_templates', 'images', 'family', 'geometry', 'line',
    'arc', 'polygram', 'boolean_ops', 'shape_matchers', 'labeled', 'tips', 'text', 'tex_mobject', 'numbers',
    'text_mobject', 'code_mobject', 'graphing', 'coordinate_systems', 'functions', 'number_line', 'probability',
    'scale', 'three_d', 'three_dimensions', 'three_d_utils', 'polyhedra', 'svg', 'svg_mobject', 'brace', 'table',
    'matrix', 'value_tracker', 'vector_field', 'graph', 'logo', 'types', 'vectorized_mobject',
    'point_cloud_mobject', 'image_mobject', 'creation', 'fading', 'growing', 'indication', 'movement', 'rotation',
    'specialized', 'speedmodifier', 'transform', 'transform_matching_parts', 'updaters', 'mobject_update_utils',
    'update', 'composition', 'changing', 'moving_camera_scene', 'zoomed_scene', 'vector_space_scene',
    'three_d_scene', 'section', 'moving_camera', 'multi_camera', 'mapping_camera', 'three_d_camera', 'frame',
    'unit', 'debug', 'file_ops', 'qhull', 'polylabel', 'deprecation'))


# Public in Community's submodules but not in its star import.
_SUBMODULE_ONLY = ('path_along_circles', 'spiral_path')


class _ModuleNamespace(types.ModuleType):
    """Community's submodules (manim.utils.paths, manim.utils.rate_functions, ...) as
    attribute chains over the flat preview namespace."""
    def __init__(self, name, root):
        super().__init__(name)
        self._root = root

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        if hasattr(self._root, name):
            return getattr(self._root, name)
        if name in _SUBMODULE_ONLY:
            return globals()[name]
        if name in _SUBMODULE_NAMES:
            return _ModuleNamespace(f'{self.__name__}.{name}', self._root)
        raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")


@contextlib.contextmanager
def register_font(font_file):
    """Community registers a font file for Pango; the preview draws with browser fonts."""
    yield


def _render_scene(source, scene_name=None, compact=False):
    module = types.ModuleType('manim')
    module.__all__ = list(EXPORTS)
    for name in EXPORTS:
        setattr(module, name, globals()[name])
    # Internally Vector is the coordinate tuple; scenes get Community's arrow.
    module.Vector = VectorArrow
    module.__all__.append('Vector')
    # Community's interpolate works on numbers and points; frames use their own.
    module.interpolate = _user_interpolate
    module.__all__.append('interpolate')
    try:
        import numpy  # Loaded by the worker only when the source mentions it.
    except ImportError:
        pass
    else:
        module.np = numpy
        module.__all__.append('np')
    module.__version__ = '0.22.0'
    # Community's star import also exposes its submodules (utils.paths.straight_path(), ...).
    for name in ('animation', 'camera', 'mobject', 'scene', 'constants', 'typing', 'color', 'manim_colors',
                 'unit', 'core', 'data_structures', 'opengl', 'renderer', 'utils'):
        setattr(module, name, _ModuleNamespace('manim.' + name, module))
        module.__all__.append(name)
    module.logger = logging.getLogger('manim')
    module.__all__.append('logger')
    # Submodule imports (manim.utils.color.manim_colors, manim.mobject.geometry.tips, ...)
    # resolve to the same flat namespace.
    module.__path__ = []
    sys.modules['manim'] = module
    for name in [name for name in sys.modules if name.startswith('manim.')]:
        del sys.modules[name]
    if not any(isinstance(finder, _SubmoduleFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _SubmoduleFinder())
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


def _set_typst_svgs(typst_svgs):
    svgs = {}
    if typst_svgs is not None:
        items = typst_svgs.items() if hasattr(typst_svgs, 'items') else None
        if items is None:
            raise TypeError('Typst SVGs must map Typst documents to SVG markup')
        for source, svg in items:
            if not isinstance(source, str) or not isinstance(svg, str) or len(svg) > 2000000:
                raise ValueError('Typst SVGs must map Typst documents to SVG markup of at most 2 MB')
            svgs[source] = svg
            if len(svgs) > 256:
                raise ValueError('At most 256 Typst documents may be supplied')
    _TYPST_SVGS.clear()
    _TYPST_SVGS.update(svgs)
    _TYPST_PENDING.clear()


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
            parts = ([list(part) for part in size[2]] if len(size) >= 3 and isinstance(size[2], (list, tuple))
                     else None)
            glyphs = ([list(glyph) for glyph in size[3]] if len(size) == 4 and isinstance(size[3], (list, tuple))
                      else None)
            if (not isinstance(text, str) or len(text) > 4096 or len(size) not in (2, 3, 4) or
                    not finite(size[:2], 0) or (len(size) >= 3 and parts is None and size[2] is not None) or
                    (len(size) == 3 and parts is None) or
                    (parts is not None and (len(parts) > 256 or
                     any(len(part) != 4 or not finite(part) or not finite(part[2:], 0) for part in parts))) or
                    (len(size) == 4 and (glyphs is None or len(glyphs) > 2000 or
                     any(len(glyph) not in (5, 6) or not finite(glyph[:4]) or not finite(glyph[2:4], 0) or
                         any(isinstance(v, bool) or not isinstance(v, _REAL) or v != int(v) or not -1 <= v <= 4096
                             for v in glyph[4:]) or glyph[4] > 256 for glyph in glyphs)))):
                raise ValueError('Math metrics must map expressions to finite [width, height(, parts(, glyphs))] in em')
            metrics[text] = (float(size[0]), float(size[1]),
                             None if parts is None else [tuple(float(v) for v in part) for part in parts],
                             None if glyphs is None else [tuple(float(v) for v in glyph[:4]) + (int(glyph[4]),)
                                                          + (int(glyph[5]) if len(glyph) > 5 else -1,)
                                                          for glyph in glyphs])
            if len(metrics) > 1024:
                raise ValueError('At most 1024 math metrics may be supplied')
    _MATH_METRICS.clear()
    _MATH_METRICS.update(metrics)
    _MATH_ESTIMATED.clear()


def render_scene(source, scene_name=None, math_metrics=None, compact=False, typst_svgs=None):
    """Render frames; math_metrics holds browser-measured MathTex ink sizes in em and
    typst_svgs maps Typst documents (as requested in typst_pending) to compiled SVG.

    compact=True pools repeated top-level snapshots (decoded by the worker)."""
    global config
    previous = config
    config = PreviewConfig()
    try:
        _set_math_metrics(math_metrics)
        _set_typst_svgs(typst_svgs)
        return _render_scene(source, scene_name, compact)
    finally:
        config = previous
        for cls in list(_DEFAULT_OVERRIDES):
            _restore_default(cls)
        for name in [name for name in sys.modules if name.startswith('manim.')]:
            del sys.modules[name]
