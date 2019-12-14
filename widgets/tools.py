"""Defines each of the editing tools

Expected interface from each tool class:

__init__(model, position, rightclick, modifiers) - on first click
update(position, modifiers) - when dragging or changing which modifier keys are held
commit(position) - when releasing the mouse. should edit the model
draw_hint(position) - what to draw when repainting

`position` is a QPoint position of the mouse in world coordinates
`model` is a Floor
`rightclick` is self-explanatory
`modifiers` is the set of modifier keys pressed

"""

from core.geometry import Path, Point
from core.model import Room


class RectTool:
    def __init__(self, model, position, rightclick, modifiers):
        self.model = model
        self.p1 = self.p2 = Point(*position.toTuple())

    def update(self, position):
        self.p2 = Point(*position.toTuple())

    def commit(self, position):
        self.p2 = Point(*position.toTuple())
        self.model.add_room(
            Room(Path.from_rect(self.p1, self.p2))
        )

    def draw_hint(self):
        return Path.from_rect(self.p1, self.p2).to_qpath()
