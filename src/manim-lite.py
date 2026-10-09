"""Small, explicit Manim subset for SVG frame playback (not full Manim)."""
import bisect
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
    return '#' + ''.join('%02X' % round(min(1, max(0, v)) * 255) for v in rgb)


def color_to_rgb(color):
    return _color_rgb(color)


def rgb_to_color(rgb):
    rgb = list(rgb)
    if len(rgb) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                            not math.isfinite(v) for v in rgb):
        raise ValueError('RGB colors need three finite components')
    if any(v > 1 for v in rgb):
        rgb = [v / 255 for v in rgb]
    return _rgb_color(rgb)


rgb_to_hex, hex_to_rgb = rgb_to_color, color_to_rgb


def interpolate_color(color1, color2, alpha):
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha):
        raise ValueError('Color interpolation alpha must be finite')
    a, b = _color_rgb(color1), _color_rgb(color2)
    return _rgb_color([x * (1 - alpha) + y * alpha for x, y in zip(a, b)])


def color_gradient(reference_colors, length_of_output):
    colors = list(reference_colors)
    if isinstance(length_of_output, bool) or not isinstance(length_of_output, int) or not 0 <= length_of_output <= 10000:
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
            center_point = self._point_to_world(child.get_center())
            target.position = list(center_point-pivot)
            target.angle += self.angle
            target.geometry_scale *= self.geometry_scale
            targets.append(target)
        return targets

    def _apply_layout_targets(self, targets):
        # Invert translations only; keep the parent pose for animated layouts.
        shifts = []
        for child,target in zip(self.children,targets):
            delta = target.get_center()-self._point_to_world(child.get_center())
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
        if len(gaps) != 2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in gaps):
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
            if dimensions[i] is not None and (isinstance(dimensions[i],bool) or not isinstance(dimensions[i],int) or not 1 <= dimensions[i] <= 1000):
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
            if size is not None and any(v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v < 0) for v in size):
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
                       self.get_center()[2]))

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

    def get_width(self):
        left,_,right,_ = self._bounds()
        return right-left

    def get_height(self):
        _,bottom,_,top = self._bounds()
        return top-bottom

    @staticmethod
    def _fit_dimension(dim):
        if isinstance(dim,bool) or not isinstance(dim,int) or dim not in (0,1):
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
                new.curves = [[local(point) for point in curve] for path in paths for curve in path]
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
        if not mobject.get_num_points() and not mobject.children:
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
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in value):
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
        if isinstance(dim, bool) or not isinstance(dim, int) or dim not in (0, 1, 2):
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
        elif self._type in ('text', 'mathtex'):
            # Text is centered on its estimated (Text) or measured (MathTex) ink box.
            width, height = (_math_box(self.text, self.font_size) if self._type == 'mathtex' else
                             (lambda layout: (layout['width'], layout['height']))(_text_layout(self.__dict__)))
            return (-width / 2, -height / 2, width / 2, height / 2)
        else:
            return (0, 0, 0, 0)
        if not points:
            return (0, 0, 0, 0)
        return (min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points))

    def _local_bounds(self):
        if not self.children:
            return self._own_local_bounds()
        bounds = [child._bounds() for child in self.children]
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

    def get_center(self):
        center = self._geometry_center()
        return Vector(self.position) + center

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
        if about_point is not None:
            pivot = Vector(about_point)
            center = self.get_center()
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
        offset = mobject.get_center() - Vector(self.position) - center
        c, s = math.cos(-self.angle), math.sin(-self.angle)
        local = center + Vector((offset[0]*c - offset[1]*s, offset[0]*s + offset[1]*c, 0)) * (1 / self.geometry_scale)
        mobject.rotate(-self.angle).scale(1 / self.geometry_scale)
        return mobject.move_to(local)

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
        center = self._geometry_center()
        result = copy.deepcopy({key: value for key, value in self.__dict__.items()
                                if key not in ('_saved_state', 'children', 'updaters', 'updating_suspended', '_sampled_geometry_center', 'traced_point_func', '_parametric_function', 'underlying_function', '_coordinate_labels', '_angle_lines', '_family_pivot_cache')})
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
    if isinstance(samples,bool) or not isinstance(samples,int) or not 2 <= samples <= 1000:
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
        super().__init__(radius=1 if radius is None else radius, start_angle=0, angle=TAU, **kwargs)
        self._type = 'circle'

    def surround(self, mobject, dim_to_match=0, stretch=False, buffer_factor=1.2):
        if not isinstance(mobject,Mobject):
            raise TypeError('surround expects a Mobject')
        self._fit_dimension(dim_to_match)
        if not isinstance(stretch,bool):
            raise ValueError('stretch must be a boolean')
        NumberLine._real(buffer_factor,'Circle buffer factor',nonnegative=True)
        if not mobject.get_num_points() and not mobject.children:
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
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
               not math.isfinite(v) or v < 0 for v in (width, height)):
            raise ValueError('Ellipse dimensions must be nonnegative and finite')
        super().__init__(**kwargs)
        self._type, self.width, self.height = 'ellipse', width, height


class ArcBetweenPoints(Arc):
    """A circular XY arc spanning two endpoints, or a straight zero-angle path."""
    def __init__(self, start, end, angle=PI/2, radius=None, **kwargs):
        kwargs.setdefault('stroke_width',4)
        start,end = Line._endpoints(start,end)
        if isinstance(angle,bool) or not isinstance(angle,(int,float)) or not math.isfinite(angle):
            raise ValueError('Arc angle must be finite')
        if radius is not None and (isinstance(radius,bool) or not isinstance(radius,(int,float))
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
        if not radii or any(isinstance(r, bool) or not isinstance(r, (int, float)) or
                            not math.isfinite(r) for r in radii):
            raise ValueError('Corner radii must be finite real values in a nonempty sequence')
        if not isinstance(evenly_distribute_anchors, bool):
            raise ValueError('evenly_distribute_anchors must be a boolean')
        if (isinstance(components_per_rounded_corner, bool) or not isinstance(components_per_rounded_corner, int)
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


class Line(TipableVMobject):
    def __init__(self, start=LEFT, end=RIGHT, buff=0, tip_length=.35, tip_style=None, **kwargs):
        start,end = self._endpoints(start,end)
        ArrowTip._tip_dimension(tip_length,'length')
        if tip_style is not None and not isinstance(tip_style,dict):
            raise TypeError('tip_style must be a dictionary')
        if isinstance(buff,bool) or not isinstance(buff,(int,float)) or not math.isfinite(buff) or buff < 0:
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
        if isinstance(angle,bool) or not isinstance(angle,(int,float)) or not math.isfinite(angle):
            raise ValueError('Line angle must be finite')
        pivot = self.get_start() if about_point is None else about_point
        return self.rotate(angle-self.get_angle(),about_point=pivot)

    def set_length(self, length):
        if isinstance(length,bool) or not isinstance(length,(int,float)) or not math.isfinite(length) or length < 0:
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
        if isinstance(alpha,bool) or not isinstance(alpha,(int,float)) or not math.isfinite(alpha) or not 0 <= alpha <= 1:
            raise ValueError('Tangent proportion must be finite and between 0 and 1')
        if isinstance(length,bool) or not isinstance(length,(int,float)) or not math.isfinite(length) or length < 0:
            raise ValueError('Tangent length must be nonnegative and finite')
        if isinstance(d_alpha,bool) or not isinstance(d_alpha,(int,float)) or not math.isfinite(d_alpha) or d_alpha <= 0:
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
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0:
            raise ValueError('Tip '+name+' must be nonnegative and finite')


class ArrowTriangleTip(ArrowTip):
    def __init__(self, length=.35, width=.35, start_angle=PI,
                 fill_opacity=0, stroke_width=3, **kwargs):
        self._tip_dimension(length,'length')
        self._tip_dimension(width,'width')
        if isinstance(start_angle,bool) or not isinstance(start_angle,(int,float)) or not math.isfinite(start_angle):
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
        if isinstance(start_angle,bool) or not isinstance(start_angle,(int,float)) or not math.isfinite(start_angle):
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
        if isinstance(start_angle,bool) or not isinstance(start_angle,(int,float)) or not math.isfinite(start_angle):
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
        if isinstance(start_angle,bool) or not isinstance(start_angle,(int,float)) or not math.isfinite(start_angle):
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
        if isinstance(num_vertices, bool) or not isinstance(num_vertices, int) or not 1 <= num_vertices <= 10000:
            raise ValueError('num_vertices must be an integer from 1 to 10000')
        if isinstance(density, bool) or not isinstance(density, int) or density < 1:
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
        if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= 10000:
            raise ValueError('Star points must be an integer from 2 to 10000')
        NumberLine._real(outer_radius, 'Star outer radius')
        inner_angle = TAU / (2 * n)
        if inner_radius is None:
            if isinstance(density, bool) or not isinstance(density, (int, float)) or density <= 0 or density >= n / 2:
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
    import unicodedata
    if unicodedata.east_asian_width(char) in 'WF':
        return (1000, 50, 950, -120, 830)
    if unicodedata.category(char) in ('Mn', 'Me', 'Cf', 'Cc'):
        return (0, 0, 0, 0, 0)
    return (556, 50, 506, 0, 716)


def _text_layout(snapshot):
    """Ink-centered line layout for a Text/DecimalNumber snapshot, in scene units."""
    font_size = snapshot['font_size']
    numeric = '_number_format' in snapshot
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
                advance, x0, x1, y0, y1 = _glyph_box(char, _SANS_GLYPHS)
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
            'family': 'serif' if numeric else 'sans'}


def _math_box(text, font_size):
    em = font_size * TEX_EM_PER_POINT
    if text in _MATH_METRICS:
        width, height = _MATH_METRICS[text]
        return width * em, height * em
    _MATH_ESTIMATED.add(text)
    # Rough placeholder until the browser measures the typeset formula.
    import re
    body = re.sub(r'\\[a-zA-Z]+', 'x', text)
    body = re.sub(r'[{}^_\s\\]', '', body)
    tall = 2 if re.search(r'\\(frac|sum|int|prod|binom|dfrac)', text) else 1
    return max(1, len(body)) * .55 * em, .75 * tall * em


class Text(Mobject):
    def __init__(self, text, font_size=48, line_spacing=-1, font='', slant=NORMAL, weight=NORMAL, **kwargs):
        if isinstance(font_size, bool) or not isinstance(font_size, (int, float)) or not math.isfinite(font_size) or font_size <= 0:
            raise ValueError('font_size must be positive and finite')
        if isinstance(line_spacing, bool) or not isinstance(line_spacing, (int, float)) or not math.isfinite(line_spacing):
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
        if all(not isinstance(r, bool) and isinstance(r, (int, float)) and r == 0 for r in radii):
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
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
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
                isinstance(q,bool) or not isinstance(q,int) or q not in (-1,1) for q in quadrant):
            raise ValueError('Angle quadrant needs two signs, each -1 or 1')
        if not all(isinstance(value,bool) for value in (other_angle,dot,elbow)):
            raise ValueError('Angle flags must be booleans')
        for value in (radius,dot_radius,dot_distance):
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float))
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
        if isinstance(num_dashes,bool) or not isinstance(num_dashes,int) or not 0 <= num_dashes <= 1000:
            raise ValueError('Dash count must be an integer from 0 to 1000')
        if isinstance(dashed_ratio,bool) or not isinstance(dashed_ratio,(int,float)) or not math.isfinite(dashed_ratio) or not 0 <= dashed_ratio <= 1:
            raise ValueError('Dashed ratio must be finite and between 0 and 1')
        if isinstance(dash_offset,bool) or not isinstance(dash_offset,(int,float)) or not math.isfinite(dash_offset):
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
        if isinstance(dash_length,bool) or not isinstance(dash_length,(int,float)) or not math.isfinite(dash_length) or dash_length <= 0:
            raise ValueError('Dash length must be positive and finite')
        if isinstance(dashed_ratio,bool) or not isinstance(dashed_ratio,(int,float)) or not math.isfinite(dashed_ratio) or not 0 <= dashed_ratio <= 1:
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
        if isinstance(index,bool) or not isinstance(index,int) or index not in (0,1):
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
            offset = label.get_center()-Vector(self.position)-center
            local = center+Vector((offset[0]*math.cos(self.angle)+offset[1]*math.sin(self.angle),
                                   -offset[0]*math.sin(self.angle)+offset[1]*math.cos(self.angle),0))*(1/self.geometry_scale)
            label.move_to(local)
            label.angle -= self.angle
            label.geometry_scale /= self.geometry_scale
        self.add(labels)
        del self._coordinate_labels
        self._geometry_center()
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
        result = {key: interpolate(value, end.get(key, value), alpha)
                  for key, value in start.items()}
        # Tip roles identify aligned child slots, rather than animated values.
        if '_tip_role' in end:
            result['_tip_role'] = end['_tip_role']
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
        return copy.deepcopy(snapshot.get('shaft_curves',snapshot['curves']))
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
            if data['type'] != 'vgroup':
                for child in data.get('children',[]):
                    reveal(child)
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
        if self._transform_plan is None:
            self._transform_plan = _transform_plan(self.start, self._path_target or self.target.to_dict())
        return _sample_transform(self._transform_plan, alpha)

    def finish(self, scene):
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
        if name not in ('become', 'set_value', 'increment_value', 'shift', 'move_to', 'to_edge', 'to_corner',
                        'align_on_border', 'center', 'align_to', 'set_coord', 'set_x', 'set_y', 'match_x',
                        'match_y', 'match_coord', 'match_width', 'match_height', 'match_dim_size', 'flip',
                        'match_color', 'match_style', 'set_color_by_gradient', 'set_colors_by_radial_gradient',
                        'fade', 'fade_to', 'set_width', 'set_height', 'rescale_to_fit', 'scale_to_fit_width', 'scale_to_fit_height', 'stretch', 'apply_matrix', 'apply_function', 'apply_complex_function', 'stretch_to_fit_width', 'stretch_to_fit_height', 'replace', 'surround', 'set_length', 'move_arc_center_to', 'put_start_and_end_on', 'set_angle', 'next_to', 'arrange', 'arrange_submobjects', 'arrange_in_grid', 'set_color', 'set_fill', 'set_stroke', 'set_opacity', 'set_z_index', 'pointwise_become_partial', 'set_points', 'append_points', 'clear_points', 'add_subpath', 'append_vectorized_mobject', 'start_new_path', 'close_path', 'set_points_as_corners', 'set_points_smoothly', 'make_smooth', 'make_jagged', 'change_anchor_mode', 'add_points_as_corners', 'add_line_to', 'add_cubic_bezier_curve_to', 'reverse_direction', 'restore', 'scale', 'rotate'):
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
            objects.extend(_refresh_tip_shafts(state) for state in (overrides[mobject] if overrides and mobject in overrides else [mobject.to_dict()]))
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


EXPORTS = ['config', 'Scene', 'MovingCameraScene', 'Mobject', 'ValueTracker', 'always_redraw', 'VMobject', 'TipableVMobject', 'TracedPath', 'ParametricFunction', 'FunctionGraph', 'CubicBezier', 'Circle', 'Ellipse', 'Arc', 'ArcBetweenPoints', 'ArcPolygon', 'ArcPolygonFromArcs', 'AnnularSector', 'Sector', 'Annulus', 'Dot', 'Square', 'Rectangle', 'RoundedRectangle', 'Line', 'DashedLine', 'DashedVMobject', 'TangentLine', 'Elbow', 'Angle', 'RightAngle', 'ArrowTip', 'ArrowTriangleTip', 'ArrowTriangleFilledTip', 'ArrowCircleTip', 'ArrowCircleFilledTip', 'ArrowSquareTip', 'ArrowSquareFilledTip', 'StealthTip', 'Arrow', 'DoubleArrow', 'CurvedArrow', 'CurvedDoubleArrow',
           'Triangle', 'Polygon', 'Polygram', 'RegularPolygram', 'RegularPolygon', 'Star', 'SurroundingRectangle', 'BackgroundRectangle', 'Cross', 'Underline', 'Text', 'DecimalNumber', 'Integer', 'MathTex', 'Group', 'VGroup', 'NumberLine', 'Axes', 'NumberPlane', 'ComplexPlane', 'Create', 'Write', 'FadeIn',
           'AnimationGroup', 'LaggedStart', 'Succession', 'MoveAlongPath',
           'GrowFromCenter', 'GrowFromPoint', 'ShrinkToCenter', 'Restore', 'Indicate', 'ShowPassingFlash', 'TransformFromCopy',
           'FadeOut', 'Uncreate', 'Rotate', 'Rotating', 'Transform', 'ReplacementTransform', 'UP', 'DOWN', 'LEFT',
           'RIGHT', 'ORIGIN', 'OUT', 'IN', 'UL', 'UR', 'DL', 'DR', 'BLUE', 'BLUE_D', 'RED', 'GREEN',
           'YELLOW', 'PURPLE', 'ORANGE', 'WHITE', 'BLACK', 'GRAY', 'GREY', 'PINK',
           'linear', 'smooth', 'there_and_back', 'PI', 'TAU', 'DEGREES',
           'SMALL_BUFF', 'MED_SMALL_BUFF', 'MED_LARGE_BUFF', 'LARGE_BUFF',
           'DEFAULT_MOBJECT_TO_EDGE_BUFFER', 'DEFAULT_MOBJECT_TO_MOBJECT_BUFFER',
           'DEFAULT_STROKE_WIDTH', 'DEFAULT_FONT_SIZE', 'DEFAULT_DOT_RADIUS',
           'DEFAULT_SMALL_DOT_RADIUS', 'DEFAULT_ARROW_TIP_LENGTH', 'color_to_rgb', 'rgb_to_color',
           'rgb_to_hex', 'hex_to_rgb', 'interpolate_color', 'color_gradient', 'average_color',
           'invert_color', 'NORMAL', 'ITALIC', 'OBLIQUE', 'BOLD', 'THIN', 'ULTRALIGHT', 'LIGHT',
           'SEMILIGHT', 'BOOK', 'MEDIUM', 'SEMIBOLD', 'ULTRABOLD', 'HEAVY', 'ULTRAHEAVY']
EXPORTS += [name for name in _PALETTE if name not in EXPORTS]


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


def _set_math_metrics(math_metrics):
    metrics = {}
    if math_metrics is not None:
        items = math_metrics.items() if hasattr(math_metrics, 'items') else None
        if items is None:
            raise TypeError('Math metrics must map expressions to [width, height] in em')
        for text, size in items:
            size = list(size)
            if (not isinstance(text, str) or len(text) > 4096 or len(size) != 2 or
                    any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                        not math.isfinite(v) or not 0 <= v <= 1000 for v in size)):
                raise ValueError('Math metrics must map expressions to finite [width, height] in em')
            metrics[text] = (float(size[0]), float(size[1]))
            if len(metrics) > 1024:
                raise ValueError('At most 1024 math metrics may be supplied')
    _MATH_METRICS.clear()
    _MATH_METRICS.update(metrics)
    _MATH_ESTIMATED.clear()


def render_scene(source, scene_name=None, math_metrics=None):
    """Render frames; math_metrics holds browser-measured MathTex ink sizes in em."""
    global config
    previous = config
    config = PreviewConfig()
    try:
        _set_math_metrics(math_metrics)
        return _render_scene(source, scene_name)
    finally:
        config = previous
