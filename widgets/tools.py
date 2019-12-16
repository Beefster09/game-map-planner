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

import os.path
from math import floor, ceil

from PySide2.QtCore import Qt
from PySide2.QtGui import QPen, QBrush, QColor, QKeySequence, QIcon
from PySide2.QtWidgets import QToolBar, QToolButton, QButtonGroup

from core.geometry import Path, Point
from core.model import Room


ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icons')

def _icon(name):
    return QIcon(os.path.join(ICON_DIR, name))

class _ShapeTool:
    def commit(self, position, modifiers=0):
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
    icon = _icon('rect-tool.svg')
    tooltip = "(R)ectangle - Create, erase, and add to rooms with a rectangular shape."
    shortcut = QKeySequence(Qt.Key_R)

    def __init__(self, model, position, rightclick, modifiers):
        self.model = model
        self.p1 = self.p2 = Point(*position.toTuple())
        self.erase = rightclick
        self.target_room = model.room_at(self.p1)
        self.update_modifiers(modifiers)

    def update(self, position, modifiers=0):
        self.p2 = Point(*position.toTuple())
        self.update_modifiers(modifiers)

    def commit(self, position, modifiers=0):
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
    icon = _icon('corridor-tool.svg')
    tooltip = "(C)orridor - Create hallways easily"
    shortcut = QKeySequence(Qt.Key_C)

    def __init__(self, model, position, rightclick, modifiers):
        self.model = model
        self.p1 = self.p2 = Point(*position.toTuple())
        self.target_room = model.room_at(self.p1)
        self.erase = rightclick
        self.update_modifiers(modifiers)

    def update(self, position, modifiers=0):
        self.p2 = Point(*position.toTuple())
        self.update_modifiers(modifiers)

    def commit(self, position, modifiers=0):
        self.p2 = Point(*position.toTuple())
        super().commit(position, modifiers)


class PencilTool(_ShapeTool):
    icon = _icon('pencil-tool.svg')
    tooltip = "(P)encil - Carve out irregular room shapes"
    shortcut = QKeySequence(Qt.Key_P)

    def __init__(self, model, position, rightclick, modifiers):
        self.model = model
        x, y = mouse_pos = Point(*position.toTuple())
        self.target_room = model.room_at(mouse_pos)
        self.cells = {(int(x), int(y)): True}  # TEMP: this needs to be a better data structure
        self.erase = rightclick
        self.update_modifiers(modifiers)

    def update(self, position, modifiers=0):
        x, y = position.toTuple()
        self.cells[int(x), int(y)] = True
        self.update_modifiers(modifiers)

    def commit(self, position, modifiers=0):
        x, y = position.toTuple()
        self.cells[int(x), int(y)] = True
        super().commit(position, modifiers)


class SelectTool:
    icon = _icon('select.svg')
    tooltip = "(A) Select - Select objects and edit their properties"
    shortcut = QKeySequence(Qt.Key_A)

    def __init__(self, model, position, rightclick, modifiers):
        pass

    def update(self, position, modifiers=0):
        pass

    def commit(self, position, modifiers=0):
        pass

    def update_modifiers(self, modifiers=0):
        pass

    def draw_hint(self, painter, pixel_size):
        pass


class MoveTool:
    icon = _icon('move.svg')
    tooltip = "(M)ove - Move rooms and objects in one click"
    shortcut = QKeySequence(Qt.Key_M)

    def __init__(self, model, position, rightclick, modifiers):
        pass

    def update(self, position, modifiers=0):
        pass

    def commit(self, position, modifiers=0):
        pass

    def update_modifiers(self, modifiers=0):
        pass

    def draw_hint(self, painter, pixel_size):
        pass


# === ToolBar ===

class EditingTools(QToolBar):
    EDIT_TOOLS = [
        SelectTool,
        MoveTool,
        None,
        RectTool,
        CorridorTool,
        PencilTool,
        None,
        # VertexTool
        # WallTool
        # RazorbladeTool
        None,
        # DoorTool
        # ItemTool
    ]

    def __init__(self, receiver):
        super().__init__()

        self.setMovable(False)

        self.edit_group = QButtonGroup()
        self.edit_group.setExclusive(True)
        self.tools = []

        for tool_class in self.EDIT_TOOLS:
            if tool_class is None:
                self.addSeparator()
                continue

            tool = QToolButton()
            tool.setCheckable(True)
            tool.tool = tool_class

            if hasattr(tool_class, 'icon'):
                tool.setIcon(tool_class.icon)
            elif hasattr(tool_class, 'label'):
                tool.setText(tool_class.label)
            else:
                tool.setText(tool.__name__)

            if hasattr(tool_class, 'shortcut'):
                tool.setShortcut(tool_class.shortcut)

            if hasattr(tool_class, 'tooltip'):
                tool.setToolTip(tool_class.tooltip)

            self.edit_group.addButton(tool)
            self.addWidget(tool)
            self.tools.append(tool)

        self.edit_group.buttonClicked.connect(receiver.set_tool)
        self.tools[0].click()
