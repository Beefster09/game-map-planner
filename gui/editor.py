"""Defines the core editor frame
"""

import functools
import json
import os.path

from PySide2.QtCore import Signal
from PySide2.QtGui import *
from PySide2.QtWidgets import QFrame, QApplication, QMessageBox

from core.model import Map
from gui.paintutil import *
from gui.tools import ToolNotAllowed
from gui import doors

BLACK_BRUSH = QBrush(QColor('black'))
WHITE_BRUSH = QBrush(QColor('white'))
GRID_BRUSH = QBrush(QColor(120, 185, 200, 100))

LeftAndRightButtons = Qt.LeftButton | Qt.RightButton

GRID_LINE_THICKNESS = 2
WHEEL_DEGREES_PER_2X_ZOOM = 180
WHEEL_UNITS_PER_2X_ZOOM = 8 * WHEEL_DEGREES_PER_2X_ZOOM
TOOLBAR_ZOOM_FACTOR = 15 / WHEEL_DEGREES_PER_2X_ZOOM

class MapDisplay(QFrame):
    status = Signal(str)

    def __init__(self, filename=None):
        super().__init__()
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setLineWidth(3)

        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.setFocusPolicy(Qt.ClickFocus)

        self.world_to_screen = QTransform().scale(20, 20)
        self.screen_to_world, _ = self.world_to_screen.inverted()

        self.model = Map()
        self.current_floor = 0

        self.pan_anchor = None

        self.current_tool = None
        self.edit_state = None
        self.edit_continued = False
        self.selection = None

        self.filename = None

        self.hover_key = None
        self.hover_position = None


        self._undo_history = []
        self._undo_index = 0
        if filename:
            self.open(filename)
        else:
            self._push_model_state()

    def pan(self, x, y):
        self.world_to_screen.translate(x, y)
        self.screen_to_world, _ = self.world_to_screen.inverted()
        self.update()

    def zoom(self, factor, center=None):
        if center is None:
            cx, cy = self.screen_to_world.map(
                QPointF(*(self.visibleRegion().boundingRect().size() / 2).toTuple())
            ).toTuple()
        else:
            cx, cy = self.screen_to_world.map(center).toTuple()
        self.world_to_screen.translate(cx, cy)
        self.world_to_screen.scale(factor, factor)
        self.world_to_screen.translate(-cx, -cy)
        self.screen_to_world, _ = self.world_to_screen.inverted()
        self.update()

    zoom_in = functools.partialmethod(zoom, 2.0 ** TOOLBAR_ZOOM_FACTOR)
    zoom_out = functools.partialmethod(zoom, 2.0 ** -TOOLBAR_ZOOM_FACTOR)

    def paintEvent(self, event):
        with Painter(self, self.world_to_screen) as p:
            pixel_size = self.screen_to_world.m11(), self.screen_to_world.m22()

            for room in self.model[self.current_floor].rooms():
                # TODO? Culling
                p.setPen(QPen(BLACK_BRUSH, self.screen_to_world.m11() * WALL_THICKNESS))
                p.setBrush(room.color)
                p.drawPath(room.get_path())

                for item in room.items:
                    if item.icon:
                        pass  # TODO
                    else:
                        fill_circle(p, item.position, 0.3)
                    # TODO: adjust label positions if offscreen or intersecting other labels.
                    draw_label(p, item.position, item.label_pos_hint, item.label, pixel_size)

            for door in self.model[self.current_floor].doors():
                door_style = doors.BASE_STYLES.get(door.type, doors.DEFAULT_STYLE)
                door_style.draw(
                    p,
                    door.position,
                    door.normal,
                    pixel_size,
                    door.extent,
                    room_colors=door.colors
                )

            if self.edit_state:
                self.edit_state.draw_hint(p, pixel_size)
            elif self.hover_key:
                self.current_tool.draw_hover_hint(
                    p,
                    self.model[self.current_floor],
                    self.hover_position,
                    pixel_size,
                    QApplication.keyboardModifiers()
                )

            # Draw grid lines
            visible = self.screen_to_world.mapRect(event.rect())
            top = int(visible.top() - 1)
            bottom = int(visible.bottom() + 2)
            left = int(visible.left() - 1)
            right = int(visible.right() + 2)

            # Vertical Lines
            p.setPen(QPen(GRID_BRUSH, pixel_size[0] * GRID_LINE_THICKNESS))
            for x in range(left, right):
                p.drawLine(x, top, x, bottom)

            # Horizontal Lines
            p.setPen(QPen(GRID_BRUSH, pixel_size[1] * GRID_LINE_THICKNESS))
            for y in range(top, bottom):
                p.drawLine(left, y, right, y)

            p.setWorldMatrixEnabled(False)
            self.drawFrame(p)

    def mousePressEvent(self, event):
        if self.edit_continued:
            return

        button = event.buttons()
        world_pos = self.screen_to_world.map(event.localPos())
        # TODO: Selections for tools that allow it
        if button & Qt.MiddleButton:
            self.pan_anchor = world_pos
        elif self.has_context_menu and button & Qt.RightButton:
            return  # Will context menu on release
        elif button & LeftAndRightButtons:
            if button & LeftAndRightButtons == LeftAndRightButtons:
                self.edit_state = None
            else:
                try:
                    self.edit_state = self.current_tool(
                        self.model[self.current_floor],
                        world_pos,
                        button == Qt.RightButton,
                        QApplication.keyboardModifiers()
                    )
                except ToolNotAllowed as nope:
                    self.status.emit(str(nope))
        else:
            return  # early return to avoid update/repaint
        self.update()

    def mouseMoveEvent(self, event):
        if self.edit_continued:
            return

        if self.pan_anchor:
            pan_target = self.screen_to_world.map(event.localPos())
            diff = pan_target - self.pan_anchor
            self.pan(diff.x(), diff.y())

        if self.edit_state:
            if self.edit_state.update(
                self.screen_to_world.map(event.localPos()),
                QApplication.keyboardModifiers()
            ):
                self.update()
        elif hasattr(self.current_tool, 'hover'):
            self.hover_position = self.screen_to_world.map(event.localPos())
            last_hover_key = self.hover_key
            self.hover_key = self.current_tool.hover(
                self.model[self.current_floor],
                self.hover_position,
                QApplication.keyboardModifiers()
            )
            if last_hover_key != self.hover_key:
                self.update()

    def mouseReleaseEvent(self, event):
        if self.edit_continued:
            return

        button = event.buttons()
        world_pos = self.screen_to_world.map(event.localPos())
        if not (button & Qt.MiddleButton):
            self.pan_anchor = None

        if self.has_context_menu and event.button() == Qt.RightButton:
            self.context_menu(world_pos, event.localPos())
        elif self.edit_state:
            continuation = self.edit_state.finish(
                self,
                world_pos,
                QApplication.keyboardModifiers()
            )
            if continuation:  # and is a Signal
                self.edit_continued = True
                def _done():
                    self.edit_continued = False
                    self.edit_state = None
                    self._push_model_state()
                continuation.connect(_done)
            else:
                self.edit_state = None
                self.update()
                self._push_model_state()

    def keyPressEvent(self, event):
        if (
            not self.edit_continued
            and self.edit_state
            and event.key() in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt)
        ):
            self.edit_state.update_modifiers(QApplication.queryKeyboardModifiers())
            self.update()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if (
            not self.edit_continued
            and self.edit_state
            and event.key() in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt)
        ):
            self.edit_state.update_modifiers(QApplication.queryKeyboardModifiers())
            self.update()
        else:
            super().keyReleaseEvent(event)

    def wheelEvent(self, event):
        sign = -1 if event.inverted() else 1
        zoom_pow = sign * event.angleDelta().y() / (8 * WHEEL_DEGREES_PER_2X_ZOOM)
        self.zoom(2.0 ** zoom_pow, (event.pos()))

    # -- misc. signal receivers --

    @property
    def has_context_menu(self):
        return (
            self.edit_state is None and hasattr(self.current_tool, 'context_menu')
            or hasattr(self.edit_state, 'instance_context_menu')
        )

    def context_menu(self, world_pos, widget_pos):
        if self.edit_state:
            menu = self.edit_state.instance_context_menu
        else:
            menu = self.current_tool.context_menu
        menu(
            self,
            self.model[self.current_floor],
            world_pos,
            widget_pos,
        )

    def set_tool(self, button):
        self.current_tool = button.tool
        self.edit_state = None
        self.edit_continued = None
        self.selection = None
        if hasattr(self.current_tool, 'cursor'):
            self.setCursor(QCursor(self.current_tool.cursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
        self.setMouseTracking(hasattr(self.current_tool, 'hover'))

    def save(self, filename=None):
        if filename is None:
            filename = self.filename
        if filename is None:
            raise Exception(f"Filename {filename} does not exist!")
        try:
            self.model.save(filename)
        except Exception:
            traceback.print_exc()
            self.status.emit
        else:
            self.filename = filename
            self.status.emit(f"Saved '{filename}'")

    def open(self, filename):
        try:
            self.model = Map.load(filename)
        except Exception:
            traceback.print_exc()
            self.status.emit(f"Unable to open '{filename}'")
        else:
            self.filename = filename
            self.update()
            self.status.emit(f"Opened '{filename}'")
            self._push_model_state()

    def new(self):
        # TODO: Tabs
        answer = QMessageBox.question(self, "Confirm New Map...", "Are you sure?")
        if answer == QMessageBox.Yes:
            self.model = Map()
            self._push_model_state()

    def undo(self):
        if self._undo_index > 0:
            self._undo_index -= 1
            filename, floor, state = self._undo_history[self._undo_index]
            self.model = Map.from_json(json.loads(state))
            self.filename = filename
            self.current_floor = floor
            self.update()

    def redo(self):
        if self._undo_index < len(self._undo_history) - 1:
            self._undo_index += 1
            filename, floor, state = self._undo_history[self._undo_index]
            self.model = Map.from_json(json.loads(state))
            self.filename = filename
            self.current_floor = floor
            self.update()

    def _push_model_state(self):
        # Quick and dirty solution - save the map as a json string at each step
        del self._undo_history[self._undo_index + 1:]
        state = json.dumps(self.model.to_json())
        self._undo_history.append(
            (self.filename, self.current_floor, state)
        )
        self._undo_index = len(self._undo_history) - 1
