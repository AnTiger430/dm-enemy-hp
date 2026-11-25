# -*- coding: utf-8 -*-
from __future__ import absolute_import

MOD_ID = 'dm.enemy_hp'
MOD_NAME = u'ХП противников в ушах'
MOD_VERSION = '1.0.6'

DEFAULT_CONFIG = {
    'configVersion': 4,
    'enabled': True,
    'fontSize': 14,
    'rowHeight': 25,
    'colWidth': 54,
    'offsetX': 0,
    'offsetY': 0,
    'topY': 67,
    'modeRightOffsets': {
        'short': 171,
        'medium': 246,
        'medium2': 243,
        'large': 382,
    },
    'colorAlive': '#FFFFFF',
    'colorUnspotted': '#FFFFFF',
    'unspottedAlpha': 1.0,
    'showDeadZero': False,
    'colorDead': '#8C8C8C',
    'deadAlpha': 0.55,
    'hideInKillcam': True,
    'reconcileIntervalSec': 0.5,
    'debugLog': False,
}
