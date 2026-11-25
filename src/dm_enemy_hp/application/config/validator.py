# -*- coding: utf-8 -*-
from __future__ import absolute_import

import copy

from ...domain.value_objects.color_spec import ColorSpec
from .defaults import DEFAULT_CONFIG
from .schema import (
    BOOL_KEYS,
    COLOR_KEYS,
    FLOAT_RANGES,
    INT_RANGES,
    MODE_KEYS,
    MODE_OFFSET_RANGE,
)


_V1_DEFAULT_TOP_Y = 56
_V1_MODE_RIGHT_OFFSETS = {
    'short': 116,
    'medium': 212,
    'medium2': 212,
    'large': 336,
}
_V2_MODE_RIGHT_OFFSETS = {
    'short': 112,
    'medium': 190,
    'medium2': 208,
    'large': 360,
}
_V3_MODE_RIGHT_OFFSETS = {
    'short': 133,
    'medium': 204,
    'medium2': 229,
    'large': 356,
}


class ConfigValidator(object):
    """Validates and normalizes user JSON config against defaults and safe bounds."""

    def normalize(self, raw_data):
        out = copy.deepcopy(DEFAULT_CONFIG)
        if not isinstance(raw_data, dict):
            return out

        raw_ver = self._clamp_int(raw_data.get('configVersion', 1), 1, 1, 999)
        out['configVersion'] = DEFAULT_CONFIG['configVersion']

        for key in BOOL_KEYS:
            if key in raw_data and isinstance(raw_data[key], (bool, int)):
                out[key] = bool(raw_data[key])

        for key, (lo, hi) in INT_RANGES.items():
            if key in raw_data:
                out[key] = self._clamp_int(raw_data[key], out[key], lo, hi)

        for key, (lo, hi) in FLOAT_RANGES.items():
            if key in raw_data:
                out[key] = self._clamp_float(raw_data[key], out[key], lo, hi)

        for key in COLOR_KEYS:
            if key in raw_data:
                out[key] = ColorSpec(raw_data[key]).hex_color

        raw_modes = raw_data.get('modeRightOffsets')
        if isinstance(raw_modes, dict):
            lo, hi = MODE_OFFSET_RANGE
            for mode_key in MODE_KEYS:
                if mode_key in raw_modes:
                    out['modeRightOffsets'][mode_key] = self._clamp_int(
                        raw_modes[mode_key], out['modeRightOffsets'][mode_key], lo, hi,
                    )

        if raw_ver < 2:
            if out['topY'] == _V1_DEFAULT_TOP_Y:
                out['topY'] = DEFAULT_CONFIG['topY']
        if raw_ver < 4:
            for mode_key in MODE_KEYS:
                cur_val = out['modeRightOffsets'][mode_key]
                if cur_val in (
                    _V1_MODE_RIGHT_OFFSETS[mode_key],
                    _V2_MODE_RIGHT_OFFSETS[mode_key],
                    _V3_MODE_RIGHT_OFFSETS[mode_key],
                ):
                    out['modeRightOffsets'][mode_key] = DEFAULT_CONFIG['modeRightOffsets'][mode_key]

        return out

    @staticmethod
    def _clamp_int(value, fallback, lo, hi):
        try:
            v = int(round(float(value)))
        except (TypeError, ValueError):
            return fallback
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v

    @staticmethod
    def _clamp_float(value, fallback, lo, hi):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return fallback
        if v != v:  # NaN
            return fallback
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v
