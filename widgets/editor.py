
from PySide2.QtGui import *
from PySide2.QtWidgets import QWidget

BLACK_BRUSH = QBrush(QColor('black'))
WHITE_BRUSH = QBrush(QColor('white'))

class Painter:
    def __init__(self, widget, transform = None):
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

class MapDisplay(QWidget):
    def __init__(self, model):
        super().__init__()
        self.transform = QTransform().translate(-90, -90).scale(2, 2)
        self.model = model

    def paintEvent(self, event):
        with Painter(self, self.transform) as p:
            for room in self.model[0].rooms():
                # TODO? Culling
                p.setPen(QPen(BLACK_BRUSH, 4))
                p.setBrush(WHITE_BRUSH)
                p.drawPath(room.get_path())
