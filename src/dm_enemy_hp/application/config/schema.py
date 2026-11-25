# -*- coding: utf-8 -*-
from __future__ import absolute_import

INT_RANGES = {
    'fontSize': (8, 32),
    'rowHeight': (12, 60),
    'colWidth': (24, 140),
    'offsetX': (-800, 800),
    'offsetY': (-800, 800),
    'topY': (0, 600),
}

FLOAT_RANGES = {
    'unspottedAlpha': (0.05, 1.0),
    'deadAlpha': (0.05, 1.0),
    'reconcileIntervalSec': (0.2, 2.0),
}

BOOL_KEYS = (
    'enabled',
    'showDeadZero',
    'hideInKillcam',
    'debugLog',
)

COLOR_KEYS = (
    'colorAlive',
    'colorUnspotted',
    'colorDead',
)

MODE_KEYS = ('short', 'medium', 'medium2', 'large')
MODE_OFFSET_RANGE = (20, 800)
