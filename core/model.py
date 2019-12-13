"""Data specifically relevant to the app
"""

import json

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
        self._path_cached = None
        self._dirty = True

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

class Door:
    pass

class Item:
    pass

class Floor:
    def __init__(self, rooms, doors, items):
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
