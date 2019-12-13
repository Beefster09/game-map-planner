"""All classes and utility functions for defining room geometry
"""

from collections import namedtuple

from PySide2.QtGui import QPainterPath

class Point(namedtuple('_Point', ['x', 'y'])):
    pass

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

class Path:
    def __init__(self, *subpaths):
        self.subpaths = [
            [Point(*p) for p in subpath]
            for subpath in subpaths
        ]

    def union(self, other):
        pass

    def difference(self, other):
        pass

    __or__ = union
    __sub__ = difference

    def to_qpath(self, path=None):
        if path is None:
            path = QPainterPath()
        else:
            path.clear()
        for subpath in self.subpaths:
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
