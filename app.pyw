#!/usr/bin/env python3

import itertools
import os.path
import sys

from PySide2.QtCore import Slot, qApp, Qt
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import QMainWindow, QAction, QApplication, QFileDialog

from widgets import editor, tools
from core.model import Map, Floor, Room


class MapDesigner(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Map Designer Tool")

        self.recent_files = self._get_recent_files()

        self.editor = editor.MapDisplay()
        self.setCentralWidget(self.editor)
        self.addToolBar(tools.EditingTools(self.editor))

        self.menu = self.menuBar()

        # File Menu
        self.file_menu = self.menu.addMenu("File")

        new_action = QAction("New Map", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.editor.new)
        self.file_menu.addAction(new_action)

        open_action = QAction("Open...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open)
        self.file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save)
        self.file_menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self.save_as)
        self.file_menu.addAction(save_as_action)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        # Edit Menu
        # TODO: Undo/Redo

        # Status Bar
        self.status = self.statusBar()
        self.status.showMessage("Maps are pretty neat")

        # Window dimensions
        geometry = qApp.desktop().availableGeometry(self)
        self.resize(
            geometry.width() * 0.7,
            geometry.height() * 0.8
        )

    @classmethod
    def _get_recent_files(cls):
        try:
            with open(os.path.join(sys.path[0], '.recent')) as f:
                return f.readlines()
        except OSError:
            print("No recent files found. :(")
            return []

    @classmethod
    def _update_recent_files(cls, filename):
        recent = cls._get_recent_files()
        if filename in recent:
            recent.remove(filename)
        with open(os.path.join(sys.path[0], '.recent'), 'w') as f:
            for fn in itertools.chain([filename], recent):
                f.write(fn + '\n')

    @property
    def last_dir(self):
        if self.recent_files:
            return os.path.dirname(self.recent_files[0])
        else:
            return os.path.expanduser('~')

    def save(self):
        if self.editor.filename is None:
            self.save_as()
        else:
            self._update_recent_files(filename)
            self.editor.save()

    def save_as(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save map as...",
            self.last_dir,
            "Maps (*.gmap *.json)",
        )
        self._update_recent_files(filename)
        self.editor.save(filename)

    def open(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open map...",
            self.last_dir,
            "Maps (*.gmap *.json)",
        )
        self._update_recent_files(filename)
        self.editor.open(filename)


if __name__ == "__main__":
    app = QApplication([])

    widget = MapDesigner()
    widget.show()

    sys.exit(app.exec_())
