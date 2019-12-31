"""Defines each of the editing tools

Expected interface from each tool class:

__init__(model, position, rightclick, modifiers) - on first click
update(position, modifiers) - when dragging or changing which modifier keys are held
finish(widget, position, modifiers) - when releasing the mouse. should edit the model
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
import sys
from math import floor, ceil, modf, copysign

from PySide2.QtCore import Qt, QPoint, QPointF, QRectF, Signal, QSize
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from core.geometry import Path, Point, Vector2, Orientation
from core.model import Room, Item
from gui import doors
from gui.paintutil import draw_label, fill_circle, LABEL_SIZE


ICON_DIR = os.path.join(sys.path[0], 'icons')

VERTICAL = Orientation.Vertical
HORIZONTAL = Orientation.Horizontal


def _icon(name):
    return QIcon(os.path.join(ICON_DIR, name))

def _cell(point):
    x, y = point
    return Point(int(x), int(y))

def _cell_center(point):
    x, y = point
    return Point(int(x) + 0.5, int(y) + 0.5)

def _wall(point):
    x, y = point
    fract_x, cell_x = modf(x)
    fract_y, cell_y = modf(y)
    if abs(fract_x - 0.5) < abs(fract_y - 0.5):
        wall_x = cell_x + 0.5
        wall_y = cell_y + round(fract_y)
        normal = Vector2(
            0,
            copysign(1, 0.5 - fract_y),
        )
    else:
        wall_y = cell_y + 0.5
        wall_x = cell_x + round(fract_x)
        normal = Vector2(
            copysign(1, 0.5 - fract_x),
            0
        )
    return Point(wall_x, wall_y), normal

class ToolNotAllowed(Exception):
    pass


class LabelEditor(QTextEdit):  # Maybe QLineEdit instead?
    commit = Signal(str)
    done = Signal()

    def __init__(self, parent, rect, placeholder="Label", alignment=None):
        super().__init__(parent=parent)
        self.move(rect.left(), rect.top())
        if alignment:
            self.setAlignment(alignment)
        self.setPlaceholderText(placeholder)
        self.setMinimumWidth(rect.width())
        font = QFont()
        font.setPixelSize(LABEL_SIZE)
        self.setCurrentFont(font)
        self.setAcceptRichText(False)
        self.setFrameStyle(QFrame.NoFrame)
        self.viewport().setAutoFillBackground(False)
        self.setContentsMargins(0, 0, 0, 0)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._done(self.toPlainText())
        elif event.key() == Qt.Key_Escape:
            self._done()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        self._done(self.toPlainText())

    def run(self, callback=None):
        if callback:
            self.commit.connect(callback)
        self.show()
        self.setFocus()

    def _done(self, result=None):
        if result:
            self.commit.emit(result)
        self.done.emit()
        parent = self.parent()
        self.close()
        self.destroy()
        parent.update()


class _ShapeTool:
    new_room_color = Qt.white

    def finish(self, widget, position, modifiers=0):
        self.update(position, modifiers)
        if self.erase:
            self.model.erase_rooms(self.shape)
        elif self.mode == 'auto' and self.target_room:
            self.model.expand_room(self.target_room, self.shape)
        elif self.mode == 'combine':
            self.model.combine_rooms(self.shape)
        else:
            self.model.new_room(self.shape, self.new_room_color, replace=(self.mode != 'polite'))

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
        self.p2 = Point(*position.toTuple())
        self.update_modifiers(modifiers)
        return True  # TODO: optimize for grid by returning False sometimes

    @property
    def shape(self):
        p1, p2 = self.p1, self.p2
        if not self.grid_snap:
            return Path.from_rect(p1, p2)

        return Path.from_rect(
            Point(floor(min(p1.x, p2.x)), floor(min(p1.y, p2.y))),
            Point(ceil(max(p1.x, p2.x)), ceil(max(p1.y, p2.y)))
        )


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

    def finish(self, widget, position, modifiers=0):
        pass

    def update_modifiers(self, modifiers=0):
        pass

    def draw_hint(self, painter, pixel_size):
        pass

    @classmethod
    def context_menu(cls, widget, model, world_pos, widget_pos):
        point = Point(*world_pos.toTuple())
        item = model.item_at(point)
        if item:
            cls._item_menu(widget, item, widget.mapToGlobal(QPoint(*widget_pos.toTuple())))
            return
        door = model.door_at(point)
        if door:
            cls._door_menu(widget, door, widget.mapToGlobal(QPoint(*widget_pos.toTuple())))
            return
        room = model.room_at(point)
        if room:
            cls._room_menu(widget, room, widget.mapToGlobal(QPoint(*widget_pos.toTuple())))
            return

    @classmethod
    def _item_menu(cls, widget, item, popup_position):
        def _change_label():
            new_label, valid = QInputDialog.getText(widget, "Item Label", 'Label')
            if valid:
                item.label = new_label
                widget.on_changed()
        menu = QMenu(widget)
        menu.addAction("Change Label...", _change_label)
        menu.popup(popup_position)

    @classmethod
    def _door_menu(cls, widget, door, popup_position):
        def _change_style():
            door.type = QInputDialog.getItem(
                widget,
                "Select Door Style",
                'Style',
                list(doors.BASE_STYLES),
                # TODO: actually have the correct one selected initially
            )
            widget.on_changed()
        def _flip():
            door.flip()
            widget.on_changed()
        menu = QMenu(widget)
        menu.addAction("Change Style...", _change_style)
        menu.addAction("Flip", _flip)
        menu.popup(popup_position)

    @classmethod
    def _room_menu(cls, widget, room, popup_position):
        def _change_color():
            room.color = QColorDialog.getColor(room.color, widget, "Select Room Color")
            widget.on_changed()
        menu = QMenu(widget)
        menu.addAction("Change Color...", _change_color)
        # menu.addAction("Change Name...")
        menu.popup(popup_position)



class MoveTool:
    icon = _icon('move.svg')
    tooltip = "(M)ove - Move rooms and objects in one click"
    shortcut = QKeySequence(Qt.Key_M)

    def __init__(self, model, position, rightclick, modifiers):
        pass

    def update(self, position, modifiers=0):
        pass

    def finish(self, widget, position, modifiers=0):
        pass

    def update_modifiers(self, modifiers=0):
        pass

    def draw_hint(self, painter, pixel_size):
        pass


class ItemTool:
    icon = _icon('item.svg')
    tooltip = "(I) Item - add items to room"
    shortcut = QKeySequence(Qt.Key_I)

    @classmethod
    def hover(cls, model, position, modifiers=0):
        grid_snap = modifiers & Qt.AltModifier == 0
        if model.room_at(position):
            return _cell(position.toTuple()) if grid_snap else position

    @classmethod
    def draw_hover_hint(cls, painter, model, position, pixel_size, modifiers=0):
        grid_snap = modifiers & Qt.AltModifier == 0
        center = _cell_center(position.toTuple()) if grid_snap else position.toTuple()
        cls.draw_item_hint(painter, center, pixel_size)

    @classmethod
    def draw_item_hint(cls, painter, position, pixel_size):
        fill_circle(painter, position, 0.3, Qt.darkGray)

    def __init__(self, model, position, rightclick, modifiers):
        grid_snap = modifiers & Qt.AltModifier == 0
        pos = Point(*position.toTuple())
        self.target_room = model.room_at(pos)
        if self.target_room is None:
            raise ToolNotAllowed("Items can only be placed inside rooms.")
        # TODO: test for items in the same position
        self.item_pos = _cell_center(pos) if grid_snap else pos
        self.label_pos = pos
        self.label_rect = None
        self.done = False

    def update(self, position, modifiers=0):
        self.label_pos = Point(*position.toTuple())
        return True

    def finish(self, widget, position, modifiers=0):
        self.done = True
        def commit(label):
            self.target_room.add_item(Item(
                self.item_pos,
                label,
                Point(*position.toTuple()),
            ))
            widget.update()

        label_editor = LabelEditor(widget, self.label_rect, placeholder="Item")
        label_editor.run(commit)
        return label_editor.done

    def draw_hint(self, painter, pixel_size):
        self.draw_item_hint(painter, self.item_pos, pixel_size)
        self.label_rect = draw_label(
            painter,
            self.item_pos, self.label_pos,
            "" if self.done else "Item",
            pixel_size,
            color=Qt.darkGray
        )


class DoorTool:
    icon = _icon('door.svg')
    tooltip = "(D) Door - connect adjacent rooms with doors"
    shortcut = QKeySequence(Qt.Key_D)

    new_door_style = doors.DEFAULT_STYLE

    @classmethod
    def hover(cls, model, position, modifiers=0):
        wall_pos, normal = _wall(position.toTuple())
        offset = normal * 0.2
        if model.room_at(wall_pos - offset) and model.room_at(wall_pos + offset):
            return wall_pos, normal

    @classmethod
    def draw_hover_hint(cls, painter, model, position, pixel_size, modifiers=0):
        wall_pos, normal = _wall(position.toTuple())
        offset = normal * 0.2
        room_a = model.room_at(wall_pos - offset)
        room_b = model.room_at(wall_pos + offset)
        if room_a is None or room_b is None or room_a is room_b:
            return
        cls.new_door_style.draw(
            painter,
            wall_pos,
            normal,
            pixel_size,
            room_colors=(room_a.color, room_b.color),
            highlight=75
        )

    @classmethod
    def add_toolbar_options(cls, parent):
        style_picker = QComboBox()
        for door_style in doors.BASE_STYLES.values():
            style_picker.addItem(door_style.name, door_style)
        def _set_door_style(_):
            cls.new_door_style = style_picker.currentData()
        style_picker.activated.connect(_set_door_style)
        return [QLabel("Door Style:"), style_picker]

    def __init__(self, model, position, rightclick, modifiers=0):
        self.w1, self.normal = _wall(position.toTuple())
        self.w2 = self.w1
        offset = self.normal * 0.2
        room_a = model.room_at(self.w1 - offset)
        room_b = model.room_at(self.w1 + offset)
        if room_a is None or room_b is None or room_a is room_b:
            raise ToolNotAllowed("Doors can only be placed on walls between two rooms.")
        self.rooms = room_a, room_b
        self.model = model

    def update(self, position, modifiers=0):
        pass  # TODO: widening the door

    def finish(self, widget, position, modifiers=0):
        self.model.add_door(
            self.position,
            self.normal,
            1,
            self.rooms,
            type=self.new_door_style.id,
        )

    def draw_hint(self, painter, pixel_size):
        self.new_door_style.draw(
            painter,
            self.w1,
            self.normal,
            pixel_size,
            room_colors=tuple(r.color for r in self.rooms),
            highlight=50
        )

    @property
    def position(self):
        return (self.w1 + self.w2) * 0.5


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

    def __init__(self, receiver, prefix_actions=()):
        super().__init__()

        self.setMovable(False)
        self.setIconSize(QSize(32, 32))

        for entry in prefix_actions:
            if entry is None:
                self.addSeparator()
                continue
            action, icon_filename = entry
            self.addAction(action)
            action.setIcon(_icon(icon_filename))
        self.addSeparator()

        self.edit_group = QButtonGroup()
        self.edit_group.setExclusive(True)
        self.tools = []

        for tool_class in self.EDIT_TOOLS:
            if tool_class is None:
                self.addSeparator()
                continue

            tool = QToolButton(self)
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

        self.addSeparator()

        self.new_room_color = Qt.white
        self.color_button = QToolButton(self)
        self.color_pixmap = QPixmap(32, 32)
        self.color_pixmap.fill()
        self._select_color(Qt.white)
        self.color_button.clicked.connect(lambda _=None: self._select_color())
        self.addWidget(QLabel("New Room Color:"))
        self.addWidget(self.color_button)

        self.subtools = {}
        for t in self.tools:
            if hasattr(t.tool, 'add_toolbar_options'):
                subtools = t.tool.add_toolbar_options(self)
                actions = []
                for subtool in subtools:
                    action = self.addWidget(subtool)
                    action.setVisible(False)
                    actions.append(action)
                self.subtools[t.tool.__name__] = actions
            else:
                self.subtools[t.tool.__name__] = []

        self.active_tool = None
        self.edit_group.buttonClicked.connect(receiver.set_tool)
        self.edit_group.buttonClicked.connect(self._set_tool)
        self.tools[0].click()

    def _set_tool(self, tool):
        if self.active_tool:
            for subtool in self.subtools[self.active_tool.__name__]:
                subtool.setVisible(False)
        self.active_tool = tool.tool
        for subtool in self.subtools[tool.tool.__name__]:
            subtool.setVisible(True)

    def _select_color(self, new_color=None):
        if new_color is None:
            new_color = QColorDialog.getColor(self.new_room_color, self, "Select Room Color")
        else:
            new_color = QColor(new_color)
        self.color_pixmap.fill(new_color)
        if new_color.lightnessF() > 0.75:  # TODO? Should use luminance instead of lightness
            p = QPainter(self.color_pixmap)
            p.drawRect(0, 0, 31, 31)
        self.color_button.setIcon(QIcon(self.color_pixmap))
        self.new_room_color = new_color
        for tool in self.EDIT_TOOLS:
            if tool:
                tool.new_room_color = new_color
