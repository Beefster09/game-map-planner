
from PySide2.QtGui import *
from PySide2.QtWidgets import QWidget

from core.geometry import Path, Point
from core.model import Room

BLACK_BRUSH = QBrush(QColor('black'))
WHITE_BRUSH = QBrush(QColor('white'))

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

class RectToolEditState:
    def __init__(self, model, position):
        self.model = model
        self.p1 = self.p2 = Point(*position.toTuple())

    def update(self, position):
        self.p2 = Point(*position.toTuple())

    def finish(self, position):
        self.p2 = Point(*position.toTuple())
        self.model.add_room(
            Room(Path.from_rect(self.p1, self.p2))
        )

    def draw_hint(self):
        return Path.from_rect(self.p1, self.p2).to_qpath()

class MapDisplay(QWidget):
    def __init__(self, model):
        super().__init__()
        self.world_to_screen = QTransform().translate(-90, -90).scale(2, 2)
        self.screen_to_world, _ = self.world_to_screen.inverted()
        self.model = model
        self.edit_state = None
        self.current_tool = 'rect'
        self.current_floor = 0

    def paintEvent(self, event):
        with Painter(self, self.world_to_screen) as p:
            for room in self.model[self.current_floor].rooms():
                # TODO? Culling
                p.setPen(QPen(BLACK_BRUSH, 4))
                p.setBrush(WHITE_BRUSH)
                p.drawPath(room.get_path())

            if self.edit_state:
                p.strokePath(self.edit_state.draw_hint(), QPen(QColor('gray'), 1))

    def mousePressEvent(self, event):
        self.edit_state = RectToolEditState(
            self.model[self.current_floor],
            self.screen_to_world.map(event.localPos())
        )
        self.repaint()

    def mouseMoveEvent(self, event):
        if self.edit_state:
            self.edit_state.update(
                self.screen_to_world.map(event.localPos())
            )
            self.repaint()

    def mouseReleaseEvent(self, event):
        if self.edit_state:
            self.edit_state.finish(
                self.screen_to_world.map(event.localPos())
            )
            self.edit_state = None
            self.repaint()
