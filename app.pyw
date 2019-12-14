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

        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")

        # Exit QAction
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)

        self.file_menu.addAction(exit_action)

        self.addToolBar(tools.EditingTools())

        self.editor = editor.MapDisplay(
            Map([
                Floor(
                    [Room([
                        [
                            (5, 5),
                            (5, 20),
                            (15, 20),
                            (15, 25),
                            (20, 25),
                            (20, 5),
                        ],
                        [
                            (10, 10),
                            (12, 10),
                            (12, 12),
                            (10, 12),
                        ]
                    ])]
                )
            ])
        )
        self.setCentralWidget(self.editor)

        # Status Bar
        self.status = self.statusBar()
        self.status.showMessage("Maps are pretty neat")

        # Window dimensions
        geometry = qApp.desktop().availableGeometry(self)
        self.setGeometry(
            geometry.width() * 0.15,
            geometry.height() * 0.1,
            geometry.width() * 0.7,
            geometry.height() * 0.8
        )

if __name__ == "__main__":
    app = QApplication([])

    widget = MapDesigner()
    widget.show()

    sys.exit(app.exec_())
