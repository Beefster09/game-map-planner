#!/usr/bin/env python3

import sys

from PySide2.QtCore import Slot, qApp
from PySide2.QtGui import QKeySequence, QPainter, QPen, QBrush, QColor, QPainterPath
from PySide2.QtWidgets import QMainWindow, QAction, QApplication, QWidget

BLACK_BRUSH = QBrush(QColor('black'))
WHITE_BRUSH = QBrush(QColor('white'))

class MapperWidget(QWidget):
    def __init__(self):
        super().__init__()

    def paintEvent(self, event):
        p = QPainter()
        p.begin(self)
        path = QPainterPath()
        path.moveTo(100, 100)
        path.lineTo(100, 400)
        path.lineTo(300, 400)
        path.lineTo(300, 500)
        path.lineTo(400, 500)
        path.lineTo(400, 100)
        path.closeSubpath()
        path.moveTo(225, 225)
        path.lineTo(275, 225)
        path.lineTo(275, 275)
        path.lineTo(225, 275)
        path.closeSubpath()
        p.setPen(QPen(BLACK_BRUSH, 4))
        p.fillPath(path, WHITE_BRUSH)
        p.drawPath(path)
        p.end()

class MapDesigner(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Map Designer Tool")

        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")

        # Exit QAction
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)

        self.file_menu.addAction(exit_action)

        self.editor = MapperWidget()
        self.setCentralWidget(self.editor)

        # Status Bar
        self.status = self.statusBar()
        self.status.showMessage("Data loaded and plotted")

        # Window dimensions
        geometry = qApp.desktop().availableGeometry(self)
        self.setFixedSize(geometry.width() * 0.8, geometry.height() * 0.7)

if __name__ == "__main__":
    app = QApplication([])

    widget = MapDesigner()
    widget.show()

    sys.exit(app.exec_())
