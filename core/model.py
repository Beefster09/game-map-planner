"""Data specifically relevant to the app
"""

import json
import uuid
from collections import deque

from PySide2.QtCore import QPoint, QPointF, Qt
from PySide2.QtGui import QColor

from core.geometry import Path, Point, Orientation, Vector2


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
    def __init__(self, position, normal, rooms, size=1, type=None, notes=None):
        self._rooms = a, b = rooms
        self.position = position
        self.normal = normal
        self.type = type
        self.notes = notes
        self.extent = size / 2
        self._deleteme = False

    @property
    def colors(self):
        return tuple(room.color for room in self._rooms)

    def remove(self):
        self._deleteme = True

    def hit_test(self, point, within=0.15):
        offset = self.position - point
        return (
            abs(self.normal.dot(offset)) < within
            and abs(self.normal.rotated90cw.dot(offset)) < self.extent
        )

    def to_json(self):
        return {
            'position': self.position,
            'normal': self.normal,
            'size': self.extent * 2,
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
        normal = (
            Vector2(*data['normal'])
            if 'normal' in data else
            Orientation[data['orientation']].value.transposed
        )
        return cls(
            Point(*data['position']),
            normal,
            tuple(get_room_by_id(id) for id in data['rooms']),
            data.get('size', 1),
            data.get('type'),
            data.get('notes'),
        )

    @property
    def is_consistent(self):
        if self._deleteme:
            return False
        offset = self.normal * 0.2
        return (
            (self.position - offset) in self._rooms[0].shape
            and (self.position + offset) in self._rooms[1].shape
        )

    def make_consistent(self):
        offset = self.normal * 0.2
        room_a, room_b = self._rooms
        back = (self.position - offset)
        front = (self.position + offset)
        if back not in room_a.shape:
            for room in room_a.derivatives:
                if back in room.shape:
                    room_a = room
                    break
            else:
                self._deleteme = True
                return
        if front not in room_b.shape:
            for room in room_b.derivatives:
                if front in room.shape:
                    room_b = room
                    break
            else:
                self._deleteme = True
                return
        self._rooms = room_a, room_b


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
        self.name = name
        self.color = color or QColor('white')
        self._items = list(items)

        # For internal use (e.g. undo/redo, room links)
        self._room_split = None

        self._door_links = []
        self._derivatives = []

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
        to_delete = self.item_at(item.position)
        self._items = [item for item in self._items if item is not to_delete]
        self._items.append(item)

    def item_at(self, point, within=0.45):
        for item in self._items:
            if item.position.distance(point) < within:
                return item

    def split_if_needed(self):
        """WARNING: this mutates the room in place as well as creating new rooms!"""
        if self._room_split is None:
            self._room_split = self._shape.shapes()
        if len(self._room_split) > 1:
            # TODO: make this transactional (to be exception-safe)
            all_items = self._items
            self._shape, *rest = self._room_split
            self._items = [item for item in all_items if item.position in self._shape]
            self._room_split = None
            self._derivatives = [
                self.__class__(
                    shape,
                    name=f"{self.name} ({i})",
                    color=self.color,
                    items=(item for item in all_items if item.position in shape)
                )
                for i, shape in enumerate(rest)
            ]
            return self._derivatives

    # -- properties --

    @property
    def shape(self):
        return self._shape

    @shape.setter
    def shape(self, value):
        self._shape = value
        self._room_split = None

    @property
    def id(self):
        return self._id

    @property
    def items(self):
        yield from self._items

    @property
    def derivatives(self):
        yield from self._derivatives

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

    def door_at(self, point, within=0.15):
        if isinstance(point, (QPoint, QPointF)):
            point = Point(point.x(), point.y())
        for door in self._doors:
            if door.hit_test(point, within):
                return door

    def item_at(self, point, within=0.45):
        room = self.room_at(point)
        if room:
            return room.item_at(point, within)

    def new_room(self, shape, color=Qt.white, *, replace=True):
        for room in self._rooms:
            if room.shape.intersects(shape):
                if replace:
                    room.shape -= shape
                else:
                    shape -= room.shape
        if shape:
            self._rooms.append(Room(shape, color=color))
            self._consistency_cleanup()

    def erase_rooms(self, shape):
        for room in self._rooms:
            if room.shape.intersects(shape):
                room.shape -= shape

        self._consistency_cleanup()

    def expand_room(self, target, shape):
        for room in self._rooms:
            if room is target:
                room.shape |= shape
            elif room.shape.intersects(shape):
                room.shape -= shape
        self._consistency_cleanup()

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
            self._consistency_cleanup()
        else:
            self._rooms.append(Room(shape))

    def add_door(self, position, normal, size, rooms, type=None):
        room_a, room_b = rooms
        if room_a is None or room_b is None or room_a is room_b:
            raise ValueError(rooms)
        door = Door(position, normal, rooms, size, type)
        if door.is_consistent:
            to_overwrite = self.door_at(position)
            if to_overwrite:  # TODO: what if the new door overlaps with multiple existing doors?
                to_overwrite.remove()
            self._doors.append(door)
            self._consistency_cleanup()
        else:
            raise ValueError("Inconsistency between rooms and door position")

    def _consistency_cleanup(self):
        self._rooms = [room for room in self._rooms if room.shape is not None]
        new_rooms = []
        for room in self._rooms:
            new_rooms.extend(room.split_if_needed() or [])
        self._rooms.extend(new_rooms)
        for door in self._doors:
            door.make_consistent()
        self._doors = [door for door in self._doors if door.is_consistent]

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
