#!/usr/bin/env python3

import sys

from PySide2.QtCore import Slot, qApp, Qt
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import QMainWindow, QAction, QApplication

from widgets import editor, tools
from core.model import Map, Floor, Room

class MapDesigner(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Map Designer Tool")

        self.editor = editor.MapDisplay()
        self.setCentralWidget(self.editor)
        self.addToolBar(tools.EditingTools(self.editor))

        self.menu = self.menuBar()

        # File Menu
        self.file_menu = self.menu.addMenu("File")

        open_action = QAction("Open...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.editor.open)
        self.file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.editor.save)
        self.file_menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self.editor.save_as)
        self.file_menu.addAction(save_as_action)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)


        # Status Bar
        self.status = self.statusBar()
        self.status.showMessage("Maps are pretty neat")

        # Window dimensions
        geometry = qApp.desktop().availableGeometry(self)
        self.resize(
            geometry.width() * 0.7,
            geometry.height() * 0.8
        )

if __name__ == "__main__":
    app = QApplication([])

    widget = MapDesigner()
    widget.show()

    sys.exit(app.exec_())
