"""Data specifically relevant to the app
"""

import json
import uuid
from collections import deque

from PySide2.QtGui import QColor

from .geometry import Path, Point

class Room:
    def __init__(self, shape, name=None, color=None):
        self._id = str(uuid.uuid4())
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

        # For internal use (e.g. undo/redo)
        self._undo_history = []
        self._rewind = 0

    def get_path(self):
        return self._shape.qpath

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

    # -- properties --

    @property
    def shape(self):
        return self._shape

    @shape.setter
    def shape(self, value):
        self.update(shape=value)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self.update(name=value)

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self.update(color=value)

    @property
    def id(self):
        return self._id


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

    def room_at(self, point):
        for room in self._rooms:
            if point in room.shape:
                return room

    def new_room(self, shape, replace=True):
        for room in self._rooms:
            if room.shape.intersects(shape):
                if replace:
                    room.shape -= shape
                else:
                    shape -= room.shape
        self._rooms.append(Room(shape))
        self._remove_shapeless_rooms()

    def erase_rooms(self, shape):
        for room in self._rooms:
            if room.shape.intersects(shape):
                room.shape -= shape

        self._remove_shapeless_rooms()

    def expand_room(self, target, shape):
        for room in self._rooms:
            if room is target:
                room.shape |= shape
            elif room.shape.intersects(shape):
                room.shape -= shape
        self._remove_shapeless_rooms()

    def combine_rooms(self, shape):
        pass

    def _remove_shapeless_rooms(self):
        self._rooms = [room for room in self._rooms if room.shape is not None]
        # TODO: rooms with two parts should be split into two rooms

class Map:
    def __init__(self, floors, **settings):
        self._floors = floors

    def __getitem__(self, index):
        return self._floors[index]
