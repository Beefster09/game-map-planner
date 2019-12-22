"""Data specifically relevant to the app
"""

import json
import uuid
from collections import deque

from PySide2.QtCore import QPoint, QPointF
from PySide2.QtGui import QColor

from core.geometry import Path, Point, Orientation


class Item:
    def __init__(self, position, label, label_pos_hint=None, icon=None):
        self.position = position
        self.label = label
        self.icon = icon
        if label_pos_hint is None:
            self.label_pos_hint = position
        else:
            self.label_pos_hint = label_pos_hint

    def to_json(self):
        return {
            'label': self.label,
            'icon': self.icon,
            'position': self.position,
            'label_pos_hint': self.label_pos_hint
        }

    @classmethod
    def from_json(cls, data):
        return cls(
            Point(*data['position']),
            data['label'],
            Point(*data['label_pos_hint']) if 'label_pos_hint' in data else None,
            data.get('icon')
        )


class Door:
    def __init__(self, position, orientation, rooms, type=None, notes=None):
        self._rooms = rooms
        self.position = position
        self.orientation = orientation
        self.type = type
        self.notes = notes

    @property
    def colors(self):
        return tuple(room.color for room in self._rooms)

    def to_json(self):
        return {
            'position': self.position,
            'orientation': self.orientation.name,
            'rooms': [r.id for r in self._rooms],
            'type': self.type,
            'notes': self.notes,
        }

    @classmethod
    def from_json(cls, data, rooms_on_floor):
        def get_room_by_id(id):
            for room in rooms_on_floor:
                if room.id == id:
                    return room
        return cls(
            Point(*data['position']),
            Orientation[data['orientation']],
            tuple(get_room_by_id(id) for id in data['rooms']),
            data.get('type'),
            data.get('notes'),
        )

class Room:
    def __init__(self, shape, name=None, color=None, items=()):
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
        self._items = list(items)

        # For internal use (e.g. undo/redo, room links)
        self._undo_history = []
        self._rewind = 0

        self._door_links = []

    def __repr__(self):
        return f"<Room {self.id[:8]}>"

    def __str__(self):
        if self._name:
            return f"'{self._name}' ({self.id[:8]})"
        else:
            return repr(self).strip('<>')

    def get_path(self):
        return self._shape.qpath

    def add_item(self, item):
        self._items.append(item)

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

    @property
    def items(self):
        return self._items

    # -- conversions --

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'shape': self.shape.to_json(),
            'color': self.color.name(),
            'items': [item.to_json() for item in self._items]
        }

    @classmethod
    def from_json(cls, data):
        room = cls(
            Path.from_json(data['shape']),
            data['name'],
            QColor(data.get('color', 'white')),
            [Item.from_json(obj) for obj in data.get('items', [])]
        )
        room._id = data['id']
        return room


class Floor:
    def __init__(self, rooms=(), doors=(), name=None):
        self.name = name
        self._rooms = list(rooms)
        self._doors = list(doors)

    def rooms(self):
        yield from self._rooms

    def doors(self):
        yield from self._doors

    def room_at(self, point):
        if isinstance(point, (QPoint, QPointF)):
            point = Point(point.x(), point.y())
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
        to_combine = [
            room for room in self._rooms
            if room.shape.intersects(shape)
        ]
        if to_combine:
            for room in to_combine:
                shape |= room.shape
            to_combine[0].shape = shape
            for room in to_combine[1:]:
                room.shape = None
            self._remove_shapeless_rooms()
        else:
            self._rooms.append(Room(shape))

    def add_door(self, position, orientation, rooms, type=None):
        room_a, room_b = rooms
        if room_a is None or room_b is None or room_a is room_b:
            raise ValueError(rooms)
        offset = orientation.value.transposed * 0.2
        if (position - offset) in room_a.shape and (position + offset) in room_b.shape:
            self._doors.append(Door(position, orientation, rooms, type))
        else:
            raise ValueError("Inconsistency between rooms and door position")

    def _remove_shapeless_rooms(self):
        self._rooms = [room for room in self._rooms if room.shape is not None]
        # TODO: rooms with two parts should be split into two rooms

    def to_json(self):
        return {
            'name': self.name,
            'rooms': [room.to_json() for room in self._rooms],
            'doors': [door.to_json() for door in self._doors],
        }

    @classmethod
    def from_json(cls, data):
        rooms = [Room.from_json(r) for r in data['rooms']]
        return cls(
            rooms,
            [Door.from_json(d, rooms) for d in data['doors']],
            name=data['name']
        )

class Map:
    def __init__(self, floors=None, **settings):
        if floors:
            self._floors = list(floors)
        else:
            self._floors = [Floor()]
        self._settings = settings

    def __getitem__(self, index):
        return self._floors[index]

    def save(self, file):
        with open(file, 'w') as f:  # TODO: Should probably be atomic
            json.dump(self.to_json(), f, indent=2)

    @classmethod
    def load(cls, file):
        with open(file, 'r') as f:
            return cls.from_json(json.load(f))

    def to_json(self):
        return {
            'floors': [floor.to_json() for floor in self._floors],
            **self._settings
        }

    @classmethod
    def from_json(cls, data):
        data_copy = dict(data)
        floors = [Floor.from_json(f) for f in data_copy.pop('floors')]
        return cls(floors, **data_copy)
