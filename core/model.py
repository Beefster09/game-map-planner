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

    def get_path(self):
        return self._shape.to_qpath()

class Door:
    pass

class Item:
    pass

class Floor:
    def __init__(self, rooms, doors, items):
        self._rooms = rooms
        self._doors = doors
        self._items = items

    def rooms(self):
        yield from self._rooms

class Map:
    def __init__(self, floors, **settings):
        self._floors = floors

    def __getitem__(self, index):
        return self._floors[index]
