# -*- coding: utf-8 -*-
from __future__ import absolute_import

_HEX_DIGITS = frozenset('0123456789ABCDEFabcdef')


class ColorSpec(object):
    """Immutable validated #RRGGBB color and opacity value object."""

    def __init__(self, hex_color='#FFFFFF', alpha=1.0):
        raw = str(hex_color or '#FFFFFF').strip()
        if len(raw) == 7 and raw[0] == '#' and all(ch in _HEX_DIGITS for ch in raw[1:]):
            self.hex_color = raw.upper()
        else:
            self.hex_color = '#FFFFFF'
        try:
            a = float(alpha)
        except (TypeError, ValueError):
            a = 1.0
        if a < 0.0:
            a = 0.0
        elif a > 1.0:
            a = 1.0
        self.alpha = a

    def as_tuple(self):
        return (self.hex_color, self.alpha)
