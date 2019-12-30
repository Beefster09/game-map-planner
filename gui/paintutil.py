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


class DoorStyle:
    def __init__(
        self,
        name,
        is_open,
        thickness,
        commands,
        use_world_space=True
    ):
        self.name = name
        self.is_open = is_open
        self.thickness = thickness
        self.commands = commands
        self.use_world_space = use_world_space

    def draw(
        self,
        painter,
        position,
        normal,
        pixel_size,
        extent=0.5,
        *,
        room_colors=(Qt.white, Qt.white),
        highlight=0,
    ):
        if self.use_world_space:
            thickness = max(
                self.thickness,
                pixel_size[0] * WALL_THICKNESS / 2
            )
        else:
            thickness = self.thickness * pixel_size[orientation.other_index]

        norm = normal * thickness
        tangent = normal.rotated90cw * extent

        def transform(x, y):
            return position + x * tangent + y * norm

        if self.is_open:
            gradient = QLinearGradient(*transform(0, -1), *transform(0, 1))
            for i, color in enumerate(room_colors):
                gradient.setColorAt(i, color.lighter(100 + highlight))
            path = QPainterPath()
            path.moveTo(*transform(-1, -1))
            path.lineTo(*transform(-1, 1))
            path.lineTo(*transform(1, 1))
            path.lineTo(*transform(1, -1))
            path.closeSubpath()
            painter.fillPath(path, QBrush(gradient))

        pen = QPen(QColor.fromHsvF(0, 0, max(highlight/200, 0)), pixel_size[0] * WALL_THICKNESS)
        path = QPainterPath()
        for command, *in_args in self.commands:
            if command == 'draw':
                painter.setBrush(QColor(*in_args))
                painter.setPen(pen)
                painter.drawPath(path)
                path.clear()
            elif command == 'fill':
                painter.fillPath(path, QBrush(QColor(*in_args)))
                path.clear()
            elif command == 'stroke':
                painter.strokePath(path, pen)
                path.clear()
            else:
                getattr(path, command)(*[
                    QPointF(*transform(*arg))
                    if isinstance(arg, (tuple, list))
                    else arg
                    for arg in in_args
                ])
        if not path.isEmpty():
            painter.strokePath(path, pen)


door_open1 = DoorStyle(
    'open1', True, 0.1,
    [
        ['moveTo', (-1, -1)],
        ['lineTo', (-1, 1)],
        ['moveTo', (1, -1)],
        ['lineTo', (1, 1)],
    ]
)

door_open2 = DoorStyle(
    'open2', True, 0,
    [
        ['moveTo', (-1, 0)],
        ['lineTo', (-0.75, 0)],
        ['moveTo', (1, 0)],
        ['lineTo', (0.75, 0)],
    ]
)

door_locked1 = DoorStyle(
    'locked1', False, 0.15,
    [
        ['moveTo', (-1, -1)],
        ['lineTo', (-1, 1)],
        ['moveTo', (1, -1)],
        ['lineTo', (1, 1)],
        ['stroke'],
        ['addEllipse', (0, 0), 0.15, 0.15],
        ['fill', 'black']
    ]
)

door_oneway1 = DoorStyle(
    'oneway1', False, 0.15,
    [
        ['moveTo', (-1, -1)],
        ['lineTo', (-1, 1)],
        ['moveTo', (1, -1)],
        ['lineTo', (1, 1)],
        ['moveTo', (0, 0)],
        ['lineTo', (0, 0.75)],
        ['moveTo', (-0.5, 0)],
        ['lineTo', (-0.5, 0.75)],
        ['moveTo', (0.5, 0)],
        ['lineTo', (0.5, 0.75)],
    ]
)

draw_open_door = door_open2.draw
# draw_open_door = door_oneway1.draw
