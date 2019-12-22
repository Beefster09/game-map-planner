"""Utilities for painting
"""

from contextlib import contextmanager

from PySide2.QtCore import Qt, QPoint, QPointF, QRectF
from PySide2.QtGui import *

from core.geometry import Orientation


LABEL_SIZE = 16 #px
LABEL_SPACING = 2
LABEL_LINE_THICKNESS = 2
WALL_THICKNESS = 4


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


@contextmanager
def new_context(painter):
    painter.save()
    yield
    painter.restore()


def inverse_color(color):
    c = QColor(color)
    return QColor.fromRgbF(
        1 - c.redF(),
        1 - c.greenF(),
        1 - c.blueF()
    )

def draw_label(
    painter,
    target, position,
    text,
    pixel_size=(1,1),
    *,
    color=Qt.black,
    font=LABEL_SIZE,
    spacing=LABEL_SPACING,
):
    if isinstance(font, int):
        label_font = QFont()
        label_font.setPixelSize(font)
    else:
        label_font = font
    label_width = QFontMetrics(label_font).width(text) * pixel_size[0]
    label_space = spacing * pixel_size[0]
    if position.distance(target) > 0.5:
        painter.setPen(QPen(color, pixel_size[0] * LABEL_LINE_THICKNESS))
        painter.drawLine(QPointF(*target), QPointF(*position))
        offset = position - target
        if abs(offset.x) > abs(offset.y):
            label_align = Qt.AlignVCenter
            label_y = position.y - 0.5
            if offset.x > 0:
                label_x = position.x + label_space
                label_align |= Qt.AlignLeft
            else:
                label_x = position.x - label_space - label_width
                label_align |= Qt.AlignRight
        else:
            label_align = Qt.AlignHCenter
            label_x = position.x - label_width / 2
            if offset.y > 0:
                label_y = position.y + label_space
                label_align |= Qt.AlignTop
            else:
                label_y = position.y - label_space - 1
                label_align |= Qt.AlignBottom
    else:
        label_align = Qt.AlignHCenter | Qt.AlignBottom
        label_x = target.x - label_width / 2
        label_y = target.y - 1.3 - label_space

    label_opts = QTextOption(label_align)
    painter.setFont(label_font)
    painter.setPen(color)
    bounding_box = painter.transform().mapRect(QRectF(label_x, label_y, label_width, 1))
    painter.setWorldMatrixEnabled(False)
    painter.drawText(bounding_box, text, label_opts)
    painter.setWorldMatrixEnabled(True)
    return bounding_box


def fill_circle(painter, center, radius, color=Qt.black):
    path = QPainterPath()
    path.addEllipse(QPointF(*center), radius, radius)
    painter.fillPath(path, QBrush(color))


def draw_open_door(
    painter,
    position,
    orientation,
    pixel_size,
    extents=(0.5, 0.2),  # width, depth
    *,
    room_colors=(Qt.white, Qt.white),
    wall_color=Qt.black,
):
    width, depth = extents
    if depth <= 0:
        depth = pixel_size[0] * WALL_THICKNESS
    if orientation is Orientation.Vertical:
        left = position.x - depth
        right = position.x + depth
        top = position.y - width
        bottom = position.y + width
        gradient = QLinearGradient(left, position.y, right, position.y)
    else:
        left = position.x - width
        right = position.x + width
        top = position.y - depth
        bottom = position.y + depth
        gradient = QLinearGradient(position.x, top, position.x, bottom)
    for i, color in enumerate(room_colors):
        gradient.setColorAt(i, color)
    painter.fillRect(QRectF(left, top, right - left, bottom - top), QBrush(gradient))
    painter.setPen(QPen(wall_color, pixel_size[0] * WALL_THICKNESS))
    if orientation is Orientation.Vertical:
        painter.drawLine(QPointF(left, top), QPointF(right, top))
        painter.drawLine(QPointF(left, bottom), QPointF(right, bottom))
    else:
        painter.drawLine(QPointF(left, top), QPointF(left, bottom))
        painter.drawLine(QPointF(right, top), QPointF(right, bottom))
