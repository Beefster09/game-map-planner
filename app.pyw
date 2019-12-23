#!/usr/bin/env python3

import argparse
import functools
import itertools
import os.path
import sys

from PySide2.QtCore import Slot, qApp, Qt
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import QMainWindow, QAction, QApplication, QFileDialog

from gui import editor, tools, colors
from core.model import Map, Floor, Room


def _uniq(seq):
    seen = set()
    ret = []
    for element in seq:
        if element not in seen:
            seen.add(element)
            ret.append(element)
    return ret


class MapDesigner(QMainWindow):
    def __init__(self, file_to_open=None):
        super().__init__()

        self.setWindowTitle("Map Designer Tool")

        self.recent_files = self._get_recent_files()

        self.editor = editor.MapDisplay(file_to_open)
        self.setCentralWidget(self.editor)

        self.menu = self.menuBar()

        # File Menu
        self.file_menu = self.menu.addMenu("File")

        self.file_menu.addAction("New Map", self.editor.new, QKeySequence.New)
        open_action = self.file_menu.addAction("Open...", self.open, QKeySequence.Open)

        self.open_recent_menu = self.file_menu.addMenu("Open Recent")
        self.open_recent_menu.aboutToShow.connect(self._update_open_recent_menu)

        save_action = self.file_menu.addAction("Save", self.save, QKeySequence.Save)
        self.file_menu.addAction("Save As...", self.save_as, QKeySequence("Ctrl+Shift+S"))
        self.file_menu.addAction("Exit", self.close, QKeySequence.Quit)

        self.edit_menu = self.menu.addMenu("Edit")

        self.edit_menu.addAction("Undo", self.editor.undo, QKeySequence.Undo)
        self.edit_menu.addAction("Redo", self.editor.redo, QKeySequence("Ctrl+Shift+Z"))

        self.view_menu = self.menu.addMenu("View")

        zoom_in = self.view_menu.addAction("Zoom In", self.editor.zoom_in, QKeySequence.ZoomIn)
        zoom_out = self.view_menu.addAction("Zoom Out", self.editor.zoom_out, QKeySequence.ZoomOut)

        self.floor_menu = self.menu.addMenu("Floor")
        self.help_menu = self.menu.addMenu("Help")

        # Tool bar
        self.addToolBar(tools.EditingTools(self.editor, [
            (open_action, 'open.svg'),
            (save_action, 'save.svg'),
            None,
            (zoom_in, 'zoom-in.svg'),
            (zoom_out, 'zoom-out.svg'),
        ]))

        # Status Bar
        self.status = self.statusBar()
        self.editor.status.connect(self.status.showMessage)

        # Window dimensions
        geometry = qApp.desktop().availableGeometry(self)
        self.resize(
            geometry.width() * 0.7,
            geometry.height() * 0.8
        )

    def _get_recent_files(self):
        try:
            with open(os.path.join(sys.path[0], '.recent')) as f:
                return _uniq(line.strip() for line in f if line and not line.isspace())
        except OSError:
            print("No recent files found. :(")
            return []

    def _update_recent_files(self, filename):
        recent = self._get_recent_files()
        if filename in recent:
            recent.remove(filename)
        with open(os.path.join(sys.path[0], '.recent'), 'w') as f:
            for fn in itertools.chain([filename], recent):
                f.write(fn + '\n')

    def _update_open_recent_menu(self):
        self.open_recent_menu.clear()
        for filepath in self._get_recent_files():
            self.open_recent_menu.addAction(filepath, functools.partial(self.open, filepath))

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
        if filename:
            self._update_recent_files(filename)
            self.editor.save(filename)
        else:
            self.status.showMessage("Save as canceled.")

    def open(self, filename=None):
        if filename is None:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Open map...",
                self.last_dir,
                "Maps (*.gmap *.json)",
            )
        if filename:
            self._update_recent_files(filename)
            self.editor.open(filename)
        else:
            self.status.showMessage("File open canceled.")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('map_file', nargs='?')

    args = parser.parse_args()

    app = QApplication([])

    colors.init_colors()

    widget = MapDesigner(args.map_file)
    widget.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
