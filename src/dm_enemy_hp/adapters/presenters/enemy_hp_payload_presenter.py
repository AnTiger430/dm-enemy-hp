# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...application.ports.payload_presenter import IEnemyHpPresenter
from ...domain.value_objects.color_spec import ColorSpec
from ...domain.value_objects.health_row_view import HealthRowView
from ...domain.value_objects.panel_layout_config import PanelLayoutConfig


class EnemyHpPayloadPresenter(IEnemyHpPresenter):
    """Formats ordered enemy HP entities and layout metrics into Gameface payload dicts."""

    def build_payload(self, enemies, cfg, screen_w, screen_h, ui_scale, panel_mode, visible):
        alive_spec = ColorSpec(cfg.get('colorAlive', '#FFFFFF'), 1.0)
        unspotted_spec = ColorSpec(cfg.get('colorUnspotted', '#FFFFFF'), cfg.get('unspottedAlpha', 1.0))
        dead_spec = ColorSpec(cfg.get('colorDead', '#8C8C8C'), cfg.get('deadAlpha', 0.55))
        show_dead = bool(cfg.get('showDeadZero', False))

        row_views = []
        for enemy in enemies or ():
            if enemy.is_alive:
                spec = alive_spec if enemy.is_spotted else unspotted_spec
                rv = HealthRowView(
                    vehicle_id=enemy.vehicle_id,
                    text=str(enemy.hp),
                    hp=enemy.hp,
                    max_hp=enemy.max_hp,
                    is_alive=True,
                    is_spotted=enemy.is_spotted,
                    visible=True,
                    color=spec.hex_color,
                    alpha=spec.alpha,
                )
            elif show_dead:
                rv = HealthRowView(
                    vehicle_id=enemy.vehicle_id,
                    text='0',
                    hp=0,
                    max_hp=enemy.max_hp,
                    is_alive=False,
                    is_spotted=False,
                    visible=True,
                    color=dead_spec.hex_color,
                    alpha=dead_spec.alpha,
                )
            else:
                rv = HealthRowView(
                    vehicle_id=enemy.vehicle_id,
                    text='',
                    hp=0,
                    max_hp=enemy.max_hp,
                    is_alive=False,
                    is_spotted=False,
                    visible=False,
                    color=dead_spec.hex_color,
                    alpha=0.0,
                )
            row_views.append(rv)

        layout_cfg = PanelLayoutConfig(
            top_y=cfg.get('topY', 67),
            row_height=cfg.get('rowHeight', 25),
            col_width=cfg.get('colWidth', 54),
            font_size=cfg.get('fontSize', 14),
            offset_x=cfg.get('offsetX', 0),
            offset_y=cfg.get('offsetY', 0),
            mode_right_offsets=cfg.get('modeRightOffsets'),
        )
        layout = layout_cfg.compute(screen_w, screen_h, ui_scale, panel_mode, len(row_views), visible=visible)

        row_dicts = [
            {
                'id': rv.vehicle_id,
                'text': rv.text,
                'visible': rv.visible,
                'color': rv.color,
                'alpha': round(rv.alpha, 3),
                'alive': rv.is_alive,
                'spotted': rv.is_spotted,
            }
            for rv in row_views
        ]
        sig = (
            layout.visible,
            layout.mode,
            layout.x,
            layout.y,
            layout.width,
            layout.height,
            layout.row_height,
            layout.font_size,
            round(layout.scale, 3),
            tuple(rv.signature() for rv in row_views),
        )
        return {
            'visible': layout.visible,
            'mode': layout.mode,
            'x': layout.x,
            'y': layout.y,
            'width': layout.width,
            'height': layout.height,
            'rowHeight': layout.row_height,
            'fontSize': layout.font_size,
            'scale': round(layout.scale, 3),
            'rows': row_dicts,
            '_signature': sig,
        }
