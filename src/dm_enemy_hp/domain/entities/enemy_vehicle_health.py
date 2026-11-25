# -*- coding: utf-8 -*-
from __future__ import absolute_import


class EnemyVehicleHealth(object):
    """Domain entity holding invariant-guarded HP state for one enemy vehicle."""

    def __init__(self, vehicle_id, hp, max_hp, is_alive=True, is_spotted=False, ever_spotted=False):
        self.vehicle_id = int(vehicle_id)
        clean_max = max(0, int(max_hp))
        self.max_hp = clean_max
        self.is_alive = bool(is_alive)
        if not self.is_alive:
            self.hp = 0
            self.is_spotted = False
        else:
            self.hp = self.clamp_hp(hp, self.max_hp)
            self.is_spotted = bool(is_spotted)
        self.ever_spotted = bool(ever_spotted) or self.is_spotted

    @staticmethod
    def clamp_hp(value, max_hp):
        iv = int(value)
        if iv < 0:
            return 0
        if max_hp > 0 and iv > max_hp:
            return int(max_hp)
        return iv

    def to_snapshot(self):
        return (
            self.vehicle_id,
            int(self.hp),
            int(self.max_hp),
            bool(self.is_alive),
            bool(self.is_spotted),
            bool(self.ever_spotted),
        )
