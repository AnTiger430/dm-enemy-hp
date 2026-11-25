# -*- coding: utf-8 -*-
from __future__ import absolute_import


class WotVehicleHook(object):
    """Hooks Vehicle AOI lifecycle (onEnterWorld, onLeaveWorld, onHealthChanged) for instant sync."""

    def __init__(self, registry, session, arena_bridge, logger):
        self._registry = registry
        self._session = session
        self._arena = arena_bridge
        self._logger = logger
        self._installed = False

    def install(self):
        if self._installed:
            return
        try:
            from Vehicle import Vehicle
        except Exception:
            self._logger.error('Vehicle import failed; AOI hook disabled')
            return

        session = self._session
        arena = self._arena
        logger = self._logger

        def _is_enemy_vehicle(veh):
            if getattr(veh, 'isPlayerTeam', False):
                return False
            vid = getattr(veh, 'id', None)
            if vid is None:
                return False
            return arena.is_enemy(vid)

        def _read_max_hp(veh):
            max_hp = getattr(veh, 'maxHealth', None)
            if not max_hp:
                pub = getattr(veh, 'publicInfo', None)
                if isinstance(pub, dict):
                    max_hp = pub.get('maxHealth')
            return max_hp

        def wrap_enter_world(orig):
            def _wrapped(veh_self, *args, **kwargs):
                result = orig(veh_self, *args, **kwargs)
                try:
                    if _is_enemy_vehicle(veh_self):
                        vid = int(veh_self.id)
                        max_hp = _read_max_hp(veh_self)
                        hp = getattr(veh_self, 'health', None)
                        is_alive = veh_self.isAlive() if hasattr(veh_self, 'isAlive') else (hp is None or hp > 0)
                        if not is_alive or (hp is not None and int(hp) <= 0):
                            session.on_vehicle_killed(vid)
                        else:
                            session.on_vehicle_spotted(vid, server_hp=hp, max_hp=max_hp)
                except Exception:
                    logger.error('Vehicle.onEnterWorld hook error')
                return result
            return _wrapped

        def wrap_leave_world(orig):
            def _wrapped(veh_self, *args, **kwargs):
                try:
                    if _is_enemy_vehicle(veh_self):
                        session.on_vehicle_unspotted(int(veh_self.id))
                except Exception:
                    logger.error('Vehicle.onLeaveWorld hook error')
                return orig(veh_self, *args, **kwargs)
            return _wrapped

        def wrap_health_changed(orig):
            def _wrapped(veh_self, newHealth, *args, **kwargs):
                result = orig(veh_self, newHealth, *args, **kwargs)
                try:
                    if _is_enemy_vehicle(veh_self):
                        vid = int(veh_self.id)
                        max_hp = _read_max_hp(veh_self)
                        session.on_vehicle_health_changed(vid, newHealth, max_hp=max_hp, is_spotted=True)
                except Exception:
                    logger.error('Vehicle.onHealthChanged hook error')
                return result
            return _wrapped

        self._registry.hook(Vehicle, 'onEnterWorld', wrap_enter_world)
        self._registry.hook(Vehicle, 'onLeaveWorld', wrap_leave_world)
        self._registry.hook(Vehicle, 'onHealthChanged', wrap_health_changed)
        self._installed = True

    def uninstall(self):
        self._installed = False
