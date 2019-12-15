"""Defines each of the editing tools

Expected interface from each tool class:

__init__(model, position, rightclick, modifiers) - on first click
update(position, modifiers) - when dragging or changing which modifier keys are held
commit(position, modifiers) - when releasing the mouse. should edit the model
update_modifiers(modifiers) - when toggling modifier keys
draw_hint(painter, pixel_size) - draw current state hint

`position` is a QPoint position of the mouse in world coordinates
`model` is a Floor
`rightclick` is self-explanatory
`modifiers` is the set of modifier keys pressed (a Qt.KeyboardModifiers)
`painter` is the active painter for drawing
`pixel_size` is the editor's current (width, height) of a single pixel

"""

from math import floor, ceil

from PySide2.QtCore import Qt
from PySide2.QtGui import QPen, QBrush, QColor, QKeySequence
from PySide2.QtWidgets import QToolBar, QToolButton, QButtonGroup

from core.geometry import Path, Point
from core.model import Room


class _ShapeTool:
    def commit(self, position, modifiers = 0):
        self.update_modifiers(modifiers)
        if self.erase:
            self.model.erase_rooms(self.shape)
        elif self.mode == 'auto' and self.target_room:
            self.model.expand_room(self.target_room, self.shape)
        elif self.mode == 'combine':
            self.model.combine_rooms(self.shape)
        else:
            self.model.new_room(self.shape, replace=(self.mode != 'polite'))

    def update_modifiers(self, modifiers):
        if modifiers & Qt.ShiftModifier:
            if modifiers & Qt.ControlModifier:
                self.mode = 'replace'
            else:
                self.mode = 'combine'
        else:
            if modifiers & Qt.ControlModifier:
                self.mode = 'polite'
            else:
                self.mode = 'auto'
        self.grid_snap = modifiers & Qt.AltModifier == 0

    def draw_hint(self, painter, pixel_size):
        painter.strokePath(
            self.shape.qpath,
            QPen(self.hint_color, pixel_size[0] * 2)
        )

    @property
    def hint_color(self):
        if self.erase:
            return Qt.red
        elif self.mode == 'combine':
            return QColor('green')
        elif self.mode == 'auto' and self.target_room:
            return QColor('goldenrod')
        elif self.mode == 'polite':
            return Qt.blue
        else:
            return Qt.darkGray


class RectTool(_ShapeTool):
    shortcut = QKeySequence(Qt.Key_R)
    label = 'Rectangle'

    def __init__(self, model, position, rightclick, modifiers):
        self.model = model
        self.p1 = self.p2 = Point(*position.toTuple())
        self.erase = rightclick
        self.target_room = model.room_at(self.p1)
        self.update_modifiers(modifiers)

    def update(self, position, modifiers = 0):
        self.p2 = Point(*position.toTuple())
        self.update_modifiers(modifiers)

    def commit(self, position, modifiers = 0):
        self.p2 = Point(*position.toTuple())
        super().commit(position, modifiers)

    @property
    def shape(self):
        p1, p2 = self.p1, self.p2
        if not self.grid_snap:
            return Path.from_rect(p1, p2)
        if p1.x < p2.x:
            if p1.y < p2.y:
                return Path.from_rect(
                    Point(floor(p1.x), floor(p1.y)),
                    Point(ceil(p2.x), ceil(p2.y))
                )
            else:
                return Path.from_rect(
                    Point(floor(p1.x), ceil(p1.y)),
                    Point(ceil(p2.x), floor(p2.y))
                )
        else:
            if p1.y < p2.y:
                return Path.from_rect(
                    Point(ceil(p1.x), floor(p1.y)),
                    Point(floor(p2.x), ceil(p2.y))
                )
            else:
                return Path.from_rect(
                    Point(ceil(p1.x), ceil(p1.y)),
                    Point(floor(p2.x), floor(p2.y))
                )


class CorridorTool(_ShapeTool):
    shortcut = QKeySequence(Qt.Key_C)
    label = 'Corridor'

    def __init__(self, model, position, rightclick, modifiers):
        self.model = model
        self.p1 = self.p2 = Point(*position.toTuple())
        self.target_room = model.room_at(self.p1)
        self.erase = rightclick
        self.update_modifiers(modifiers)

    def update(self, position, modifiers = 0):
        self.p2 = Point(*position.toTuple())
        self.update_modifiers(modifiers)

    def commit(self, position, modifiers = 0):
        self.p2 = Point(*position.toTuple())
        super().commit(position, modifiers)


# === ToolBar ===

class EditingTools(QToolBar):
    EDIT_TOOLS = [
        RectTool,
        CorridorTool,
    ]

    def __init__(self, receiver):
        super().__init__()

        self.setMovable(False)

        self.edit_group = QButtonGroup()
        self.edit_group.setExclusive(True)
        self.tools = []

        for tool_class in self.EDIT_TOOLS:
            tool = QToolButton()
            if hasattr(tool_class, 'icon'):
                tool.setIcon(tool_class.icon)
            else:
                tool.setText(tool_class.label)
            if hasattr(tool_class, 'shortcut'):
                tool.setShortcut(tool_class.shortcut)
            tool.setCheckable(True)
            tool.tool = tool_class
            self.edit_group.addButton(tool)
            self.addWidget(tool)
            self.tools.append(tool)

        self.edit_group.buttonClicked.connect(receiver.set_tool)
        self.tools[0].click()
