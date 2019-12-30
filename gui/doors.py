

from gui.paintutil import DoorStyle

door_open1 = DoorStyle(
    'open1', "Wide Open", True, 0.1,
    [
        ['moveTo', (-1, -1)],
        ['lineTo', (-1, 1)],
        ['moveTo', (1, -1)],
        ['lineTo', (1, 1)],
    ]
)

door_open2 = DoorStyle(
    'open2', "Narrow Open", True, 0,
    [
        ['moveTo', (-1, 0)],
        ['lineTo', (-0.75, 0)],
        ['moveTo', (1, 0)],
        ['lineTo', (0.75, 0)],
    ]
)

door_locked1 = DoorStyle(
    'locked1', "Locked 1", False, 0.15,
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
    'oneway1', "One Way 1", False, 0.15,
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

BASE_STYLES = {
    style.id: style
    for style in [
        door_open1,
        door_open2,
        door_locked1,
        door_oneway1,
    ]
}

DEFAULT_STYLE = door_open1
