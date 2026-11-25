# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..entities.enemy_vehicle_health import EnemyVehicleHealth


class EnemyHealthTracker(object):
    """Domain service maintaining exact per-enemy HP with zero desync on unspot/re-spot."""

    def __init__(self):
        self._enemies = {}

    def reset(self):
        self._enemies = {}

    def register_enemy(self, vehicle_id, max_hp, is_alive=True, current_hp=None, is_enemy=True):
        if not is_enemy:
            return False
        vid = int(vehicle_id)
        clean_max = max(0, int(max_hp or 0))
        existing = self._enemies.get(vid)
        if existing is not None:
            changed = False
            if clean_max > existing.max_hp:
                changed = self.update_max_health(vid, clean_max) or changed
            if not is_alive and existing.is_alive:
                changed = self.mark_dead(vid) or changed
            elif current_hp is not None:
                changed = self.reconcile_from_snapshot(
                    vid, current_hp, max_hp=clean_max or None, is_alive=is_alive,
                ) or changed
            return changed

        init_hp = clean_max if current_hp is None else int(current_hp)
        if current_hp is not None and init_hp > clean_max:
            clean_max = init_hp
        entity = EnemyVehicleHealth(
            vehicle_id=vid,
            hp=init_hp,
            max_hp=clean_max,
            is_alive=bool(is_alive) and (init_hp > 0 or clean_max == 0),
            is_spotted=False,
            ever_spotted=(current_hp is not None and clean_max > 0 and init_hp < clean_max),
        )
        self._enemies[vid] = entity
        return True

    def update_max_health(self, vehicle_id, new_max_hp):
        vid = int(vehicle_id)
        entity = self._enemies.get(vid)
        if entity is None:
            return False
        clean_max = max(0, int(new_max_hp or 0))
        if clean_max <= entity.max_hp:
            return False

        old_snap = entity.to_snapshot()
        old_max = entity.max_hp
        entity.max_hp = clean_max
        if not entity.is_alive:
            entity.hp = 0
        elif (not entity.ever_spotted) or entity.hp == old_max:
            delta = clean_max - old_max
            entity.hp = EnemyVehicleHealth.clamp_hp(entity.hp + delta, clean_max)
        else:
            entity.hp = EnemyVehicleHealth.clamp_hp(entity.hp, clean_max)
        return entity.to_snapshot() != old_snap

    def update_health(self, vehicle_id, new_hp, max_hp=None, spotted=None):
        vid = int(vehicle_id)
        entity = self._enemies.get(vid)
        if entity is None:
            return False

        old_snap = entity.to_snapshot()
        if max_hp is not None:
            self.update_max_health(vid, max_hp)
        raw_hp = max(0, int(new_hp))
        if not entity.is_alive and raw_hp > 0:
            return False
        if raw_hp > entity.max_hp:
            entity.max_hp = raw_hp

        if raw_hp <= 0:
            entity.hp = 0
            entity.is_alive = False
            entity.is_spotted = False
        else:
            entity.is_alive = True
            entity.hp = EnemyVehicleHealth.clamp_hp(raw_hp, entity.max_hp)
            if spotted is not None:
                entity.is_spotted = bool(spotted)
                if entity.is_spotted:
                    entity.ever_spotted = True
        return entity.to_snapshot() != old_snap

    def mark_spotted(self, vehicle_id, server_hp=None, max_hp=None):
        vid = int(vehicle_id)
        entity = self._enemies.get(vid)
        if entity is None or not entity.is_alive:
            return False

        old_snap = entity.to_snapshot()
        if max_hp is not None and int(max_hp) > entity.max_hp:
            entity.max_hp = int(max_hp)
        if server_hp is not None:
            srv = max(0, int(server_hp))
            if srv > entity.max_hp:
                entity.max_hp = srv
            if srv <= 0:
                entity.hp = 0
                entity.is_alive = False
                entity.is_spotted = False
                entity.ever_spotted = True
            else:
                entity.is_alive = True
                entity.hp = EnemyVehicleHealth.clamp_hp(srv, entity.max_hp)
                entity.is_spotted = True
                entity.ever_spotted = True
        elif entity.is_alive:
            entity.is_spotted = True
            entity.ever_spotted = True
        return entity.to_snapshot() != old_snap

    def mark_unspotted(self, vehicle_id):
        vid = int(vehicle_id)
        entity = self._enemies.get(vid)
        if entity is None or not entity.is_spotted:
            return False
        entity.is_spotted = False
        return True

    def mark_dead(self, vehicle_id):
        vid = int(vehicle_id)
        entity = self._enemies.get(vid)
        if entity is None:
            return False
        old_snap = entity.to_snapshot()
        entity.hp = 0
        entity.is_alive = False
        entity.is_spotted = False
        return entity.to_snapshot() != old_snap

    def reconcile_from_snapshot(self, vehicle_id, health=None, max_hp=None, is_alive=None, is_spotted=None):
        vid = int(vehicle_id)
        entity = self._enemies.get(vid)
        if entity is None:
            return False

        old_snap = entity.to_snapshot()
        if max_hp is not None and int(max_hp) > entity.max_hp:
            self.update_max_health(vid, int(max_hp))

        if is_alive is False:
            self.mark_dead(vid)
            return entity.to_snapshot() != old_snap

        if not entity.is_alive and is_alive is not True:
            return False

        if health is not None:
            clean_hp = max(0, int(health))
            if clean_hp <= 0:
                self.mark_dead(vid)
                return entity.to_snapshot() != old_snap
            if clean_hp > entity.max_hp:
                entity.max_hp = clean_hp
            entity.hp = EnemyVehicleHealth.clamp_hp(clean_hp, entity.max_hp)
            entity.is_alive = True

        if is_spotted is True and entity.is_alive:
            entity.is_spotted = True
            entity.ever_spotted = True
        elif is_spotted is False and entity.is_spotted:
            entity.is_spotted = False

        return entity.to_snapshot() != old_snap

    def get(self, vehicle_id):
        return self._enemies.get(int(vehicle_id))

    def all_enemies(self):
        return list(self._enemies.values())
