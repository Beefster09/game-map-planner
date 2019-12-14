"""All classes and utility functions for defining room geometry
"""

import math
import itertools
from collections import namedtuple

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

Point = Vector2

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
    s = math.copysign
    # test if c and d are on the same side of ab
    ab = b - a
    bc = c - b
    bd = d - b
    abc = s(1, ab.cross(bc))
    abd = s(1, ab.cross(bd))
    if abc == abd:
        return False
    # test if a and b are on the same side of cd
    cd = d - c
    db = b - d
    da = a - d
    cdb = s(1, cd.cross(db))
    cda = s(1, cd.cross(da))
    return cdb != cda

class Path:
    """Representation of the shape of a room. Pseudo-immutable
    """
    def __init__(self, *subpaths):
        self._subpaths = [
            [Point(*p) for p in subpath]
            for subpath in subpaths
        ]
        self._bounding_box = None

    # -- Geometric operations --

    @property
    def bounding_box(self):
        if self._bounding_box is None:
            all_x, all_y = zip(*self.points())
            self._bounding_box = min(all_x), min(all_y), max(all_x), max(all_y)
        return self._bounding_box

    def segments(self):
        for subpath in self._subpaths:
            l = len(subpath)
            for i in range(l):
                yield (subpath[i], subpath[(i + 1) % l])

    def points(self):
        yield from itertools.chain.from_iterable(self._subpaths)

    def __contains__(self, point):
        minx, miny, maxx, maxy = self.bounding_box
        if point.x < minx or point.x > maxx or point.y < miny or point.y > maxy:
            return False
        outside = Point(minx - 1, miny + 1)
        point_inside = False
        for segment in self.segments():
            if _lines_intersect(outside, point, *segment):
                point_inside = not point_inside
        return point_inside

    def union(self, other):
        return NotImplemented

    def difference(self, other):
        return NotImplemented

    def intersects(self, other):
        s_minx, s_miny, s_maxx, s_maxy = self.bounding_box
        o_minx, o_miny, o_maxx, o_maxy = other.bounding_box
        if s_minx > o_maxx or s_miny > o_maxy or s_maxx < o_minx or s_maxy < o_miny:
            return False
        else:
            return (
                any(
                    _lines_intersect(*l1, *l2)
                    for l1, l2 in itertools.product(self.segments(), other.segments())
                )
                or any(point in self for point in other.points())
                or any(point in other for point in self.points())
            )

    __or__ = union
    __sub__ = difference

    # -- Conversions --

    def to_qpath(self, path=None):
        if path is None:
            path = QPainterPath()
        else:
            path.clear()
        for subpath in self._subpaths:
            path.moveTo(*subpath[0])
            for point in subpath[1:]:
                path.lineTo(*point)
            path.closeSubpath()
        return path

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
