"""Defines the core editor frame
"""

import os.path
import json

from PySide2.QtGui import *
from PySide2.QtWidgets import QFrame, QApplication, QFileDialog, QMessageBox

from core.model import Map
from widgets.paintutil import Painter, fill_circle, draw_label

BLACK_BRUSH = QBrush(QColor('black'))
WHITE_BRUSH = QBrush(QColor('white'))
GRID_BRUSH = QBrush(QColor(120, 185, 200, 100))

LeftAndRightButtons = Qt.LeftButton | Qt.RightButton

class MapDisplay(QFrame):
    def __init__(self):
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

        self.filename = None

        self.hover_key = None
        self.hover_position = None

    def pan(self, x, y):
        self.world_to_screen.translate(x, y)
        self.screen_to_world, _ = self.world_to_screen.inverted()
        self.update()

    def zoom(self, factor, center=None):
        if center is None:
            cx, cy = self.screen_to_world.map(
                self.visibleRegion().boundingRect().size() / 2
            ).toTuple()
        else:
            cx, cy = self.screen_to_world.map(center).toTuple()
        self.world_to_screen.translate(cx, cy)
        self.world_to_screen.scale(factor, factor)
        self.world_to_screen.translate(-cx, -cy)
        self.screen_to_world, _ = self.world_to_screen.inverted()
        self.update()

    def paintEvent(self, event):
        with Painter(self, self.world_to_screen) as p:
            pixel_size = self.screen_to_world.m11(), self.screen_to_world.m22()
            for room in self.model[self.current_floor].rooms():
                # TODO? Culling
                p.setPen(QPen(BLACK_BRUSH, self.screen_to_world.m11() * 4))
                p.setBrush(WHITE_BRUSH)
                p.drawPath(room.get_path())

                for item in room.items:
                    if item.icon:
                        pass  # TODO
                    else:
                        fill_circle(p, item.position, 0.3)
                    draw_label(p, item.position, item.label_pos_hint, item.label, pixel_size)

            # Draw grid lines
            visible = self.screen_to_world.mapRect(event.rect())
            top = int(visible.top() - 1)
            bottom = int(visible.bottom() + 2)
            left = int(visible.left() - 1)
            right = int(visible.right() + 2)

            # Vertical Lines
            p.setPen(QPen(GRID_BRUSH, self.screen_to_world.m11() * 2))
            for x in range(left, right):
                p.drawLine(x, top, x, bottom)

            # Horizontal Lines
            p.setPen(QPen(GRID_BRUSH, self.screen_to_world.m22() * 2))
            for y in range(top, bottom):
                p.drawLine(left, y, right, y)

            if self.edit_state:
                self.edit_state.draw_hint(p, pixel_size)
            elif self.hover_key:
                self.current_tool.draw_hover_hint(
                    p,
                    self.hover_position,
                    pixel_size,
                    QApplication.keyboardModifiers()
                )

            p.setWorldTransform(QTransform())
            self.drawFrame(p)

    def mousePressEvent(self, event):
        if self.edit_continued:
            return

        button = event.buttons()
        if button & Qt.MiddleButton:
            self.pan_anchor = self.screen_to_world.map(event.localPos())
        elif button & LeftAndRightButtons:
            if button & LeftAndRightButtons == LeftAndRightButtons:
                self.edit_state = None
            else:
                self.edit_state = self.current_tool(
                    self.model[self.current_floor],
                    self.screen_to_world.map(event.localPos()),
                    button == Qt.RightButton,
                    QApplication.keyboardModifiers()
                )
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
        if not (button & Qt.MiddleButton):
            self.pan_anchor = None

        if self.edit_state:
            continuation = self.edit_state.finish(
                self,
                self.screen_to_world.map(event.localPos()),
                QApplication.keyboardModifiers()
            )
            if continuation:
                self.edit_continued = True
                def _done():
                    self.edit_continued = False
                    self.edit_state = None
                continuation.connect(_done)
            else:
                self.edit_state = None
                self.update()

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
        zoom_pow = sign * event.angleDelta().y() / (8 * 180)
        self.zoom(2.0 ** zoom_pow, (event.pos()))

    # -- misc. signal receivers --

    def set_tool(self, button):
        self.edit_state = None
        self.current_tool = button.tool
        if hasattr(self.current_tool, 'cursor'):
            self.setCursor(QCursor(self.current_tool.cursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
        self.setMouseTracking(hasattr(self.current_tool, 'hover'))

    def save_as(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save map as...",
            os.path.dirname(self.filename) if self.filename else os.path.expanduser('~'),
            "Maps (*.gmap *.json)",
        )
        self._save_model(filename)

    def save(self):
        if self.filename is None:
            self.save_as()
        else:
            self._save_model()

    def _save_model(self, file=None):
        if file is None:
            file = self.filename
        if file is None:
            raise Exception(f"Filename {file} does not exist!")
        self.model.save(file)
        self.filename = file

    def open(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open map...",
            os.path.dirname(self.filename) if self.filename else os.path.expanduser('~'),
            "Maps (*.gmap *.json)",
        )
        self.filename = filename
        self.model = Map.load(filename)
        self.update()

    def new(self):
        # TODO: Tabs
        answer = QMessageBox.question(self, "Confirm New Map...", "Are you sure?")
        if answer == QMessageBox.Yes:
            self.model = Map()
