"""All classes and utility functions for defining room geometry
"""

import math
import itertools
from collections import namedtuple
from enum import Enum

from PySide2.QtGui import QPainterPath


class Vector2(namedtuple('_Vector2', ['x', 'y'])):
    def cross(self, other):
        return self.x * other.y - self.y * other.x

    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, other):
        if isinstance(other, self.__class__):
            return Vector2(self.x * other.x, self.y * other.y)
        else:
            return Vector2(self.x * other, self.y * other)

    __rmul__ = __mul__

    @property
    def transposed(self):
        return Vector2(self.y, self.x)

    @property
    def length_squared(self):
        return self.x * self.x + self.y * self.y

    @property
    def length(self):
        return math.hypot(self.x, self.y)

    def distance(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)

    @property
    def rotated90cw(self):
        return Vector2(-self.y, self.x)

    @property
    def rotated90ccw(self):
        return Vector2(self.y, -self.x)

Point = Vector2
Vector2.Up = Vector2(0, -1)
Vector2.Down = Vector2(0, 1)
Vector2.Left = Vector2(-1, 0)
Vector2.Right = Vector2(1, 0)


class Orientation(namedtuple('_ORIENTATION', ['direction', 'index']), Enum):
    Horizontal = Vector2(1, 0), 0
    Vertical = Vector2(0, 1), 1

    @property
    def value(self):
        return self.direction

    @property
    def other_index(self):
        return 1 - self.index



def _rect_to_path_xywh(x, y, w, h):
    return [
        Point(x, y),
        Point(x + w, y),
        Point(x + w, y + h),
        Point(x, y + h),
    ]

def _rect_to_path_2p(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return [
        Point(x1, y1),
        Point(x2, y1),
        Point(x2, y2),
        Point(x1, y2),
    ]

def _lines_intersect(a, b, c, d):
    """Non-colinear line-line intersection test"""
    # test if c and d are on the same side of ab
    ab = b - a
    bc = c - b
    bd = d - b
    abc = ab.cross(bc)
    abd = ab.cross(bd)
    if abc == 0 or abd == 0 or (abc > 0) == (abd > 0):
        return False
    # test if a and b are on the same side of cd
    cd = d - c
    da = a - d
    db = b - d
    cda = cd.cross(da)
    cdb = cd.cross(db)
    if cda == 0 or cdb == 0:
        return False
    return (cda > 0) != (cdb > 0)

def _point_of_intersection(p11, p12, p21, p22):
    """Assuming two intersecting line segments, where is the intersection?"""
    # Calculate coefficients for two ax + by = c equations,
    # But combine the coefficients into vectors
    a = Vector2(p11.y - p12.y, p21.y - p22.y)
    b = Vector2(p12.x - p11.x, p22.x - p21.x)
    c = Vector2(p12.cross(p11), p22.cross(p21))
    # Use Cramer's Rule to find the point of intersection
    # (Cross products are equivalent to the determinant of 2 column vectors as a matrix)
    d = a.cross(b)
    if d:
        return Vector2(b.cross(c) / d, c.cross(a) / d)
    else:
        return None

class Path:
    """Representation of the shape of a room. Pseudo-immutable.
    """
    def __init__(self, *subpaths):
        self._subpaths = [
            [Point(*p) for p in subpath]
            for subpath in subpaths
        ]
        self._bounding_box = None
        self._qpath = None

    # -- Geometric operations --

    @property
    def bounding_box(self):
        if self._bounding_box is None:
            all_x, all_y = zip(*self.points())
            self._bounding_box = min(all_x), min(all_y), max(all_x), max(all_y)
        return self._bounding_box

    def segments(self, which=Ellipsis):
        if which is Ellipsis:
            for subpath in self._subpaths:
                l = len(subpath)
                for i in range(l):
                    yield (subpath[i], subpath[(i + 1) % l])
        else:
            subpath = self._subpaths[which]
            l = len(subpath)
            for i in range(l):
                yield (subpath[i], subpath[(i + 1) % l])

    def points(self):
        yield from itertools.chain.from_iterable(self._subpaths)

    def __contains__(self, point):
        """Exclusive point membership test - does not count colinear points or segments

        Uses odd-even rule with a horizontal raycast to the left
        """
        minx, miny, maxx, maxy = self.bounding_box
        if point.x < minx or point.x > maxx or point.y < miny or point.y > maxy:
            return False
        def _x_at_y(p1, p2, y):
            vec = p2 - p1
            dy = y - p1.y
            return p1.x + (dy / vec.y) * vec.x
        point_inside = False
        for segment in self.segments():
            p1, p2 = segment
            if p1.y == p2.y or point.x < p1.x and point.x < p2.x:
                continue # ignore horizontal lines and degenerate segments
            miny = min(p1.y, p2.y)
            maxy = max(p1.y, p2.y)
            if point.y < miny or point.y > maxy:
                continue
            maxx = max(p1.x, p2.x)
            if point.x > maxx or point.x > _x_at_y(p1, p2, point.y):
                point_inside = not point_inside
        return point_inside

    def union(self, other):
        return self.from_qpath(self.qpath | other.qpath)

    def intersection(self, other):
        return self.from_qpath(self.qpath & other.qpath)

    def difference(self, other):
        return self.from_qpath(self.qpath - other.qpath)

    def intersects(self, other):
        s_minx, s_miny, s_maxx, s_maxy = self.bounding_box
        o_minx, o_miny, o_maxx, o_maxy = other.bounding_box
        if s_minx >= o_maxx or s_miny >= o_maxy or s_maxx <= o_minx or s_maxy <= o_miny:
            return False
        else:
            return self.qpath.intersects(other.qpath)

    __or__ = __add__ = union
    __and__ = intersection
    __sub__ = difference

    # -- Conversions --

    @property
    def qpath(self):
        if self._qpath is None:
            self._qpath = QPainterPath()
            for subpath in self._subpaths:
                self._qpath.moveTo(*subpath[0])
                for point in subpath[1:]:
                    self._qpath.lineTo(*point)
                self._qpath.closeSubpath()
        return self._qpath

    @classmethod
    def from_qpath(cls, qpath):
        subpaths = []
        cur_subpath = []
        for i in range(qpath.elementCount()):
            element = qpath.elementAt(i)
            if element.isLineTo():
                cur_subpath.append(Point(element.x, element.y))
            elif element.isMoveTo():
                while cur_subpath and cur_subpath[0] == cur_subpath[-1]:
                    cur_subpath.pop()
                if len(cur_subpath) >= 3:
                    subpaths.append(cur_subpath)
                cur_subpath = [Point(element.x, element.y)]
        while cur_subpath and cur_subpath[0] == cur_subpath[-1]:
            cur_subpath.pop()
        if len(cur_subpath) >= 3:
            subpaths.append(cur_subpath)
        return cls(*subpaths) if subpaths else None

    @classmethod
    def from_rect(cls, *args):
        if len(args) == 2:
            return Path(_rect_to_path_2p(*args))
        elif len(args) == 4:
            return Path(_rect_to_path_xywh(*args))
        else:
            raise TypeError(
                f"'{cls.__name__}.from_rect' expects 2 or 4 arguments, but {len(args)} were given."
            )

    def to_json(self):
        return self._subpaths

    @classmethod
    def from_json(cls, data):
        return cls(*data)
