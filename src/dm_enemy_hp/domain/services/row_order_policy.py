# -*- coding: utf-8 -*-
from __future__ import absolute_import

_CLASS_PRIORITY = {
    'heavyTank': 0,
    'mediumTank': 1,
    'AT-SPG': 2,
    'lightTank': 3,
    'SPG': 4,
}


class RowOrderPolicy(object):
    """Pure fallback enemy ordering policy matching WoT right PlayersPanel sorting."""

    @staticmethod
    def sort_key(meta):
        is_alive = 1 if meta.get('is_alive', True) else 0
        level = int(meta.get('level', 0) or 0)
        vclass = str(meta.get('class_tag', '') or '')
        class_rank = _CLASS_PRIORITY.get(vclass, 99)
        veh_name = str(meta.get('vehicle_name', '') or '').lower()
        player_name = str(meta.get('player_name', '') or '').lower()
        veh_id = int(meta.get('vehicle_id', 0) or 0)
        return (-is_alive, -level, class_rank, veh_name, player_name, veh_id)

    def sort_ids(self, entries):
        ordered = sorted(entries, key=self.sort_key)
        return [int(item['vehicle_id']) for item in ordered]
