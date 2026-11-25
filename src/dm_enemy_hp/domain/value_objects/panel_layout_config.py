# -*- coding: utf-8 -*-
from __future__ import absolute_import


DEFAULT_MODE_RIGHT_OFFSETS = {
    'short': 171,
    'medium': 246,
    'medium2': 243,
    'large': 382,
}


class PanelModeLayout(object):
    """Computed screen-space column box (in logical px before or with UI scale)."""

    def __init__(self, visible, mode, x, y, width, height, row_height, font_size, scale):
        self.visible = bool(visible)
        self.mode = str(mode)
        self.x = int(round(x))
        self.y = int(round(y))
        self.width = max(1, int(round(width)))
        self.height = max(1, int(round(height)))
        self.row_height = max(8, int(round(row_height)))
        self.font_size = max(8, int(round(font_size)))
        self.scale = float(scale)


class PanelLayoutConfig(object):
    """Pure geometry policy mapping WoT right-ear mode + resolution + uiScale to column box."""

    def __init__(
        self,
        top_y=67,
        row_height=25,
        col_width=54,
        font_size=14,
        offset_x=0,
        offset_y=0,
        mode_right_offsets=None,
    ):
        self.top_y = float(top_y)
        self.row_height = max(8.0, float(row_height))
        self.col_width = max(20.0, float(col_width))
        self.font_size = max(8, int(round(font_size)))
        self.offset_x = float(offset_x)
        self.offset_y = float(offset_y)
        offsets = dict(DEFAULT_MODE_RIGHT_OFFSETS)
        if isinstance(mode_right_offsets, dict):
            for k, v in mode_right_offsets.items():
                if k in offsets:
                    try:
                        offsets[k] = max(0.0, float(v))
                    except (TypeError, ValueError):
                        pass
        self.mode_right_offsets = offsets

    def compute(self, screen_w, screen_h, ui_scale, panel_mode, row_count, visible=True):
        try:
            scale = float(ui_scale)
        except (TypeError, ValueError):
            scale = 1.0
        if scale <= 0.1 or scale > 4.0:
            scale = 1.0

        mode_str = str(panel_mode or 'short')
        if not visible or mode_str == 'hidden' or row_count <= 0:
            return PanelModeLayout(False, mode_str, 0, 0, self.col_width, self.row_height, self.row_height, self.font_size, scale)

        right_off = float(self.mode_right_offsets.get(mode_str, self.mode_right_offsets['short']))
        col_w_scaled = self.col_width * scale
        row_h_scaled = self.row_height * scale
        total_h = max(row_h_scaled, float(row_count) * row_h_scaled)
        x = float(screen_w) - (right_off * scale) - col_w_scaled + (self.offset_x * scale)
        y = (self.top_y + self.offset_y) * scale

        x = max(0.0, min(max(0.0, float(screen_w) - col_w_scaled), x))
        y = max(0.0, min(max(0.0, float(screen_h) - row_h_scaled), y))

        return PanelModeLayout(
            True,
            mode_str,
            x,
            y,
            self.col_width,
            float(row_count) * self.row_height,
            self.row_height,
            self.font_size,
            scale,
        )
