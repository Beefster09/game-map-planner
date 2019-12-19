"""Defines each of the editing tools

Expected interface from each tool class:

__init__(model, position, rightclick, modifiers) - on first click
update(position, modifiers) - when dragging or changing which modifier keys are held
finish(position, modifiers) - when releasing the mouse. should edit the model
update_modifiers(modifiers) - when toggling modifier keys
draw_hint(painter, pixel_size) - draw current state hint

`position` is a QPoint position of the mouse in world coordinates
`model` is a Floor
`rightclick` is self-explanatory
`modifiers` is the set of modifier keys pressed (a Qt.KeyboardModifiers)
`painter` is the active painter for drawing
`pixel_size` is the editor's current (width, height) of a single pixel

update(...) should return True if a repaint is needed

"""

import os.path
from contextlib import contextmanager
from math import floor, ceil

from PySide2.QtCore import Qt, QPoint, QPointF, QRectF
from PySide2.QtGui import *
from PySide2.QtWidgets import QToolBar, QToolButton, QButtonGroup

from core.geometry import Path, Point, Vector2
from core.model import Room


ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icons')

def _icon(name):
    return QIcon(os.path.join(ICON_DIR, name))

def _cell(point):
    x, y = point
    return Point(int(x), int(y))

def _cell_center(point):
    x, y = point
    return Point(int(x) + 0.5, int(y) + 0.5)

@contextmanager
def new_context(painter):
    painter.save()
    yield
    painter.restore()

class _ShapeTool:
    def finish(self, position, modifiers=0):
        self.update(position, modifiers)
        if self.erase:
            self.model.erase_rooms(self.shape)
        elif self.mode == 'auto' and self.target_room:
            self.model.expand_room(self.target_room, self.shape)
        elif self.mode == 'combine':
            self.model.combine_rooms(self.shape)
        else:
            self.model.new_room(self.shape, replace=(self.mode != 'polite'))

    def update_modifiers(self, modifiers):
        if hasattr(self, 'mode'):
            last_mode = self.mode
            last_snap = self.grid_snap
        else:
            last_mode = None
            last_snap = None
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
        return last_mode != self.mode or last_snap != self.grid_snap

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
    cursor = Qt.CrossCursor

    def __init__(self, model, position, rightclick, modifiers):
        self.model = model
        self.p1 = self.p2 = Point(*position.toTuple())
        self.erase = rightclick
        self.target_room = model.room_at(self.p1)
        self.update_modifiers(modifiers)

    def update(self, position, modifiers=0):
        old_p2 = _cell(self.p2) # FIXME - does not actually correspond to the shape changing
        self.p2 = Point(*position.toTuple())
        return self.update_modifiers(modifiers) or not self.grid_snap or old_p2 != _cell(self.p2)

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

VERTICAL = object()
HORIZONTAL = object()

class CorridorTool(_ShapeTool):
    icon = _icon('corridor-tool.svg')
    tooltip = "(C)orridor - Create hallways easily"
    shortcut = QKeySequence(Qt.Key_C)
    cursor = Qt.CrossCursor

    def __init__(self, model, position, rightclick, modifiers):
        self.model = model
        self.p1 = self.p2 = Point(*position.toTuple())
        self.target_room = model.room_at(self.p1)
        self.bias = None
        self.erase = rightclick
        self.update_modifiers(modifiers)

    def update(self, position, modifiers=0):
        old_p2 = _cell(self.p2)
        self.p2 = Point(*position.toTuple())
        if abs(self.p1.x - self.p2.x) < 0.5:
            self.bias = VERTICAL
        elif abs(self.p1.y - self.p2.y) < 0.5:
            self.bias = HORIZONTAL
        return self.update_modifiers(modifiers) or not self.grid_snap or old_p2 != _cell(self.p2)

    @property
    def shape(self):
        if self.grid_snap:
            p1 = _cell(self.p1)
            p2 = _cell(self.p2)
        else:
            p1 = self.p1 - Vector2(0.5, 0.5)
            p2 = self.p2 - Vector2(0.5, 0.5)
        if self.bias is VERTICAL:
            if p1.x == p2.x:
                if p1.y < p2.y:
                    p1, p2 = p1, p2
                else:
                    p1, p2 = p2, p1
                return Path.from_rect(*p1, 1, p2.y - p1.y + 1)
            else:
                if p1.x < p2.x:
                    x1o = p1.x
                    x1i = x1o + 1
                    x2 = p2.x + 1
                else:
                    x1i = p1.x
                    x1o = x1i + 1
                    x2 = p2.x

                if p1.y < p2.y:
                    y1 = p1.y
                    y2i = p2.y
                    y2o = y2i + 1
                else:
                    y1 = p1.y + 1
                    y2o = p2.y
                    y2i = y2o + 1

                return Path([
                    (x1o, y1),
                    (x1o, y2o),
                    (x2, y2o),
                    (x2, y2i),
                    (x1i, y2i),
                    (x1i, y1),
                ])
        elif self.bias is HORIZONTAL:
            if p1.y == p2.y:
                if p2.x > p1.x:
                    p1, p2 = p1, p2
                else:
                    p1, p2 = p2, p1
                return Path.from_rect(*p1, p2.x - p1.x + 1, 1)
            else:
                if p1.x < p2.x:
                    x1 = p1.x
                    x2i = p2.x
                    x2o = x2i + 1
                else:
                    x1 = p1.x + 1
                    x2o = p2.x
                    x2i = x2o + 1

                if p1.y < p2.y:
                    y1o = p1.y
                    y1i = y1o + 1
                    y2 = p2.y + 1
                else:
                    y1i = p1.y
                    y1o = y1i + 1
                    y2 = p2.y

                return Path([
                    (x1, y1o),
                    (x2o, y1o),
                    (x2o, y2),
                    (x2i, y2),
                    (x2i, y1i),
                    (x1, y1i),
                ])
        else:
            return Path.from_rect(*p1, 1, 1)


class PencilTool(_ShapeTool):
    icon = _icon('pencil-tool.svg')
    tooltip = "(P)encil - Carve out irregular room shapes"
    shortcut = QKeySequence(Qt.Key_P)
    cursor = Qt.CrossCursor

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


class SelectTool:
    icon = _icon('select.svg')
    tooltip = "(A) Select - Select objects and edit their properties"
    shortcut = QKeySequence(Qt.Key_A)

    def __init__(self, model, position, rightclick, modifiers):
        pass

    def update(self, position, modifiers=0):
        pass

    def finish(self, position, modifiers=0):
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

    def finish(self, position, modifiers=0):
        pass

    def update_modifiers(self, modifiers=0):
        pass

    def draw_hint(self, painter, pixel_size):
        pass


class ItemTool:
    icon = _icon('item.svg')
    tooltip = "(I) Item - add items to room"
    shortcut = QKeySequence(Qt.Key_I)

    LABEL_SIZE = 16 #px
    LABEL_SPACING = 4

    @classmethod
    def hover(cls, model, position, modifiers=0):
        grid_snap = modifiers & Qt.AltModifier == 0
        if model.room_at(position):
            return _cell(position.toTuple()) if grid_snap else position

    @classmethod
    def draw_hover_hint(cls, painter, position, pixel_size, modifiers=0):
        grid_snap = modifiers & Qt.AltModifier == 0
        center = _cell_center(position.toTuple()) if grid_snap else position.toTuple()
        cls.draw_item_hint(painter, center, pixel_size)

    @classmethod
    def draw_item_hint(cls, painter, position, pixel_size):
        path = QPainterPath()
        path.addEllipse(QPointF(*position), 0.3, 0.3)
        painter.fillPath(path, QBrush(Qt.darkGray))

    def __init__(self, model, position, rightclick, modifiers):
        grid_snap = modifiers & Qt.AltModifier == 0
        pos = Point(*position.toTuple())
        self.target_room = model.room_at(pos)
        self.item_pos = _cell_center(pos) if grid_snap else pos
        self.label_pos = pos

    def update(self, position, modifiers=0):
        self.label_pos = Point(*position.toTuple())
        return True

    def finish(self, position, modifiers=0):
        # self.target_room.add_item()
        pass

    def draw_hint(self, painter, pixel_size):
        self.draw_item_hint(painter, self.item_pos, pixel_size)
        offset = self.label_pos - self.item_pos
        cell_height = 1 / pixel_size[0]
        label_font = QFont()
        label_font.setPixelSize(self.LABEL_SIZE)
        label_text = "Item Label"
        label_width = QFontMetrics(label_font).width(label_text) * pixel_size[0]
        label_space = self.LABEL_SPACING * pixel_size[0]
        if offset.length_squared > 0.25:
            with new_context(painter):
                painter.setCompositionMode(QPainter.CompositionMode_Difference)
                painter.setPen(QPen(QColor('#cccccc'), pixel_size[0] * 2))
                painter.drawLine(QPointF(*self.item_pos), QPointF(*self.label_pos))
            if abs(offset.x) > abs(offset.y):
                label_align = Qt.AlignVCenter
                label_y = self.label_pos.y - 0.5
                if offset.x > 0:
                    label_x = self.label_pos.x + label_space
                    label_align |= Qt.AlignLeft
                else:
                    label_x = self.label_pos.x - label_space - label_width
                    label_align |= Qt.AlignRight
            else:
                label_align = Qt.AlignHCenter
                label_x = self.label_pos.x - label_width / 2
                if offset.y > 0:
                    label_y = self.label_pos.y + label_space
                    label_align |= Qt.AlignTop
                else:
                    label_y = self.label_pos.y - label_space - 1
                    label_align |= Qt.AlignBottom
        else:
            label_align = Qt.AlignHCenter | Qt.AlignBottom
            label_x = self.item_pos.x - label_width / 2
            label_y = self.item_pos.y - 1.3 - label_space

        label_opts = QTextOption(label_align)
        painter.setFont(label_font)
        painter.setPen(Qt.darkGray)
        bounding_box = painter.transform().mapRect(QRectF(label_x, label_y, label_width, 1))
        painter.setWorldMatrixEnabled(False)
        painter.drawText(bounding_box, label_text, label_opts)
        painter.setWorldMatrixEnabled(True)

class DoorTool:
    icon = _icon('door.svg')
    tooltip = "(D) Door - connect adjacent rooms with doors"
    shortcut = QKeySequence(Qt.Key_D)

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
        DoorTool,
        ItemTool,
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
