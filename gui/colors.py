

from PySide2.QtGui import QColor
from PySide2.QtWidgets import QColorDialog

STANDARD_COLORS = [
    '#ffffff',
    '#cccccc',
    '#aaaaaa',
    '#888888',
    '#666666',
    '#444444',

    '#ffcccc',
    '#d54444',
    '#881111',
    '#ff4444',
    '#cc0000',
    '#880000',

    '#fee788',
    '#feae34',
    '#e87022',
    '#e4a672',
    '#b86f50',
    '#743f39',

    '#ffff88',
    '#cccc44',
    '#888800',
    '#fff8aa',
    '#ddb433',
    '#997700',

    '#ddffcc',
    '#77cc66',
    '#338811',
    '#44ff44',
    '#00cc00',
    '#008800',

    '#99eeff',
    '#2ce8f9',
    '#0095e9',
    '#44ffff',
    '#00cccc',
    '#008888',

    '#bbddff',
    '#4488cc',
    '#113388',
    '#c0cbdc',
    '#8b9bb4',
    '#5a6988',

    '#ddbbff',
    '#9966cc',
    '#662288',
    '#ffccee',
    '#d577bb',
    '#881166',
]

def init_colors():
    for i, color in enumerate(STANDARD_COLORS):
        QColorDialog.setStandardColor(i, QColor(color))
