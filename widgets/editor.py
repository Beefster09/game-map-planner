"""Defines the core editor frame
"""

from PySide2.QtGui import *
from PySide2.QtWidgets import QFrame

from widgets.tools import RectTool

BLACK_BRUSH = QBrush(QColor('black'))
WHITE_BRUSH = QBrush(QColor('white'))
GRID_BRUSH = QBrush(QColor(120, 185, 200, 100))

LeftAndRightButtons = Qt.LeftButton | Qt.RightButton

class Painter:
    def __init__(self, widget, transform=None):
        self.painter = QPainter()
        self.widget = widget
        self.transform = transform

    def __enter__(self):
        self.painter.begin(self.widget)
        if self.transform:
            self.painter.setWorldTransform(self.transform)
        return self.painter

    def __exit__(self, a, b, c):
        self.painter.end()
        return False

class MapDisplay(QFrame):
    def __init__(self, model):
        super().__init__()
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setLineWidth(3)

        self.world_to_screen = QTransform().scale(20, 20)
        self.screen_to_world, _ = self.world_to_screen.inverted()
        self.model = model
        self.current_floor = 0

        self.current_tool = RectTool
        self.edit_state = None
        self.pan_anchor = None

        self.grid_size = 1.0, 1.0

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
            for room in self.model[self.current_floor].rooms():
                # TODO? Culling
                p.setPen(QPen(BLACK_BRUSH, self.screen_to_world.m11() * 4))
                p.setBrush(WHITE_BRUSH)
                p.drawPath(room.get_path())

            # Draw grid lines
            visible = self.screen_to_world.mapRect(event.rect())
            top = int(visible.top() - 1)
            bottom = int(visible.bottom() + 1)
            left = int(visible.left() - 1)
            right = int(visible.right() + 1)

            grid_x, grid_y = self.grid_size

            # Vertical Lines
            p.setPen(QPen(GRID_BRUSH, self.screen_to_world.m11() * 2))
            for x in range(left, right):
                p.drawLine(x, top, x, bottom)

            # Horizontal Lines
            p.setPen(QPen(GRID_BRUSH, self.screen_to_world.m22() * 2))
            for y in range(top, bottom):
                p.drawLine(left, y, right, y)

            if self.edit_state:
                self.edit_state.draw_hint(
                    p,
                    (self.screen_to_world.m11(), self.screen_to_world.m22())
                )

            p.setWorldTransform(QTransform())
            self.drawFrame(p)

    def mousePressEvent(self, event):
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
                    event.flags()
                )
        else:
            return  # early return to avoid update/repaint
        self.update()

    def mouseMoveEvent(self, event):
        should_repaint = False

        if self.pan_anchor:
            pan_target = self.screen_to_world.map(event.localPos())
            diff = pan_target - self.pan_anchor
            self.pan(diff.x(), diff.y())

        if self.edit_state:
            self.edit_state.update(
                self.screen_to_world.map(event.localPos())
            )
            self.update()

    def mouseReleaseEvent(self, event):
        button = event.buttons()
        if not (button & Qt.MiddleButton):
            self.pan_anchor = None

        if self.edit_state:
            self.edit_state.commit(
                self.screen_to_world.map(event.localPos())
            )
            self.edit_state = None
            self.update()

    def wheelEvent(self, event):
        sign = -1 if event.inverted() else 1
        zoom_pow = sign * event.angleDelta().y() / (8 * 180)
        self.zoom(2.0 ** zoom_pow, (event.pos()))
