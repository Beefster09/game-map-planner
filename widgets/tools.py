"""Defines each of the editing tools

Expected interface from each tool class:

__init__(model, position, rightclick, modifiers) - on first click
update(position, modifiers) - when dragging or changing which modifier keys are held
commit(position) - when releasing the mouse. should edit the model
draw_hint(painter, pixel_size) - draw current state hint

`position` is a QPoint position of the mouse in world coordinates
`model` is a Floor
`rightclick` is self-explanatory
`modifiers` is the set of modifier keys pressed
`painter` is the active painter for drawing
`pixel_size` is the editor's current (width, height) of a single pixel

"""

from math import floor, ceil

from PySide2.QtCore import Qt
from PySide2.QtGui import QPen, QBrush, QColor
from PySide2.QtWidgets import QToolBar

from core.geometry import Path, Point
from core.model import Room


class RectTool:
    def __init__(self, model, position, rightclick, modifiers):
        self.model = model
        self.p1 = self.p2 = Point(*position.toTuple())
        self.erase = rightclick
        self.hint_color = QColor('red') if rightclick else QColor('green')

    def update(self, position, modifiers = 0):
        self.p2 = Point(*position.toTuple())

    def commit(self, position):
        self.p2 = Point(*position.toTuple())
        shape = Path.from_rect(*self.quantized)
        if self.erase:
            self.model.erase_rooms(shape)
        else:
            self.model.add_room(Room(shape))

    def draw_hint(self, painter, pixel_size):
        painter.strokePath(
            Path.from_rect(*self.quantized).to_qpath(),
            QPen(self.hint_color, pixel_size[0] * 2)
        )


    @property
    def quantized(self):
        p1, p2 = self.p1, self.p2
        if p1.x < p2.x:
            if p1.y < p2.y:
                return (
                    Point(floor(p1.x), floor(p1.y)),
                    Point(ceil(p2.x), ceil(p2.y))
                )
            else:
                return (
                    Point(floor(p1.x), ceil(p1.y)),
                    Point(ceil(p2.x), floor(p2.y))
                )
        else:
            if p1.y < p2.y:
                return (
                    Point(ceil(p1.x), floor(p1.y)),
                    Point(floor(p2.x), ceil(p2.y))
                )
            else:
                return (
                    Point(ceil(p1.x), ceil(p1.y)),
                    Point(floor(p2.x), floor(p2.y))
                )

class EditingTools(QToolBar):
    def __init__(self):
        super().__init__()
        # self.addAction()
