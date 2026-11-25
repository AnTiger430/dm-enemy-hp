# -*- coding: utf-8 -*-
from __future__ import absolute_import


class HealthRowView(object):
    """Immutable presentation-ready HP value object for one right-ear row."""

    def __init__(self, vehicle_id, text, hp, max_hp, is_alive, is_spotted, visible, color, alpha):
        self.vehicle_id = int(vehicle_id)
        self.text = str(text)
        self.hp = int(hp)
        self.max_hp = int(max_hp)
        self.is_alive = bool(is_alive)
        self.is_spotted = bool(is_spotted)
        self.visible = bool(visible)
        self.color = str(color)
        self.alpha = float(alpha)

    def signature(self):
        return (
            self.vehicle_id,
            self.text,
            self.visible,
            self.color,
            round(self.alpha, 3),
        )
