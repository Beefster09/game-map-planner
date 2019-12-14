"""Data specifically relevant to the app
"""

import json
from collections import deque

from PySide2.QtGui import QColor

from .geometry import Path, Point

class Room:
    def __init__(self, shape, name=None, color=None):
        if isinstance(shape, Path):
            self._shape = shape
        elif isinstance(shape, list):
            if isinstance(shape[0], tuple):
                self._shape = Path(shape)
            else:
                self._shape = Path(*shape)
        else:
            raise TypeError(shape)
        self._name = name
        self._color = color or QColor('white')

        # For internal use (e.g. optimizations, undo/redo)
        self._path_cached = None
        self._dirty = True
        self._undo_history = []
        self._rewind = 0

    def get_path(self):
        if self._path_cached:
            if self._dirty:
                self._dirty = False
                return self._shape.to_qpath(self._path_cached)
            else:
                return self._path_cached
        else:
            self._path_cached = self._shape.to_qpath()
            return self._path_cached

    # -- undo/redo --

    def undo(self):
        self._rewind -= 1
        prev_values = self._undo_history[self._rewind]
        old_values = {
            attr: getattr(self, '_' + attr)
            for attr in old_values
        }
        self._undo_history[self._rewind] = old_values
        for attr, value in prev_values.items():
            setattr(self, '_' + attr, value)
        self._dirty = True

    def redo(self):
        if self._rewind >= 0:
            return  # raise error?
        next_values = self._undo_history[self._rewind]
        old_values = {
            attr: getattr(self, '_' + attr)
            for attr in old_values
        }
        self._undo_history[self._rewind] = old_values
        for attr, value in next_values.items():
            setattr(self, '_' + attr, value)
        self._rewind += 1
        self._dirty = True

    def update(self, **new_values):
        if self._rewind:
            del self._undo_history[self._rewind:]
            self._rewind = 0
        old_values = {
            attr: getattr(self, '_' + attr)
            for attr in new_values
        }
        self._undo_history.append(old_values)
        for attr, value in new_values.items():
            setattr(self, '_' + attr, value)
        self._dirty = True

    # -- properties --

    @property
    def shape(self):
        return self._shape

    @shape.setter
    def shape(self, value):
        self.update('shape', value)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self.update('name', value)

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self.update('color', value)


class Door:
    pass

class Item:
    pass

class Floor:
    def __init__(self, rooms=(), doors=(), items=()):
        self._rooms = list(rooms)
        self._doors = list(doors)
        self._items = list(items)

    def rooms(self):
        yield from self._rooms

    def add_room(self, room):
        self._rooms.append(room)

class Map:
    def __init__(self, floors, **settings):
        self._floors = floors

    def __getitem__(self, index):
        return self._floors[index]
