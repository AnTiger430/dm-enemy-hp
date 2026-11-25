# -*- coding: utf-8 -*-
from __future__ import absolute_import


class WotBattleFieldHook(object):
    """Hooks BattleFieldCtrl to capture server health, spot/re-spot, unspot, and maxHealth updates."""

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
            from gui.battle_control.controllers.battle_field_ctrl import BattleFieldCtrl
        except Exception:
            self._logger.error('BattleFieldCtrl import failed; battleField hook disabled')
            return

        session = self._session
        arena = self._arena
        logger = self._logger

        def wrap_set_health(orig):
            def _wrapped(ctrl_self, vehicleID, newHealth, *args, **kwargs):
                result = orig(ctrl_self, vehicleID, newHealth, *args, **kwargs)
                try:
                    if arena.is_enemy(vehicleID, ctrl_self):
                        session.on_vehicle_health_changed(vehicleID, newHealth)
                except Exception:
                    logger.error('setVehicleHealth hook error')
                return result
            return _wrapped

        def wrap_set_visible(orig):
            def _wrapped(ctrl_self, vehicleID, health, *args, **kwargs):
                result = orig(ctrl_self, vehicleID, health, *args, **kwargs)
                try:
                    if arena.is_enemy(vehicleID, ctrl_self):
                        info = ctrl_self.getVehicleHealthInfo(vehicleID) if hasattr(ctrl_self, 'getVehicleHealthInfo') else None
                        max_hp = info[1] if (info is not None and len(info) > 1) else None
                        session.on_vehicle_spotted(vehicleID, server_hp=health, max_hp=max_hp)
                except Exception:
                    logger.error('setVehicleVisible hook error')
                return result
            return _wrapped

        def wrap_stop_visual(orig):
            def _wrapped(ctrl_self, vehicleID, *args, **kwargs):
                result = orig(ctrl_self, vehicleID, *args, **kwargs)
                try:
                    if arena.is_enemy(vehicleID, ctrl_self):
                        session.on_vehicle_unspotted(vehicleID)
                except Exception:
                    logger.error('stopVehicleVisual hook error')
                return result
            return _wrapped

        def wrap_update_vehicles_info(orig):
            def _wrapped(ctrl_self, updated, arenaDP, *args, **kwargs):
                result = orig(ctrl_self, updated, arenaDP, *args, **kwargs)
                try:
                    for item in updated or ():
                        v_info = item[1] if (isinstance(item, (tuple, list)) and len(item) > 1) else item
                        vid = getattr(v_info, 'vehicleID', None)
                        if vid is None:
                            continue
                        is_enemy = arena.is_enemy(vid, ctrl_self, arena_dp=arenaDP, v_info=v_info)
                        if not is_enemy:
                            continue
                        vtype = getattr(v_info, 'vehicleType', None)
                        max_hp = getattr(vtype, 'maxHealth', None) if vtype is not None else None
                        alive = v_info.isAlive() if hasattr(v_info, 'isAlive') else None
                        session.on_vehicle_updated(vid, max_hp=max_hp, is_alive=alive, is_enemy=True)
                except Exception:
                    logger.error('updateVehiclesInfo hook error')
                return result
            return _wrapped

        def wrap_invalidate_status(orig):
            def _wrapped(ctrl_self, flags, vInfoVO, arenaDP, *args, **kwargs):
                result = orig(ctrl_self, flags, vInfoVO, arenaDP, *args, **kwargs)
                try:
                    vid = getattr(vInfoVO, 'vehicleID', None)
                    if vid is not None and arena.is_enemy(vid, ctrl_self, arena_dp=arenaDP, v_info=vInfoVO):
                        if hasattr(vInfoVO, 'isAlive') and not vInfoVO.isAlive():
                            session.on_vehicle_killed(vid)
                except Exception:
                    logger.error('invalidateVehicleStatus hook error')
                return result
            return _wrapped

        self._registry.hook(BattleFieldCtrl, 'setVehicleHealth', wrap_set_health)
        self._registry.hook(BattleFieldCtrl, 'setVehicleVisible', wrap_set_visible)
        self._registry.hook(BattleFieldCtrl, 'stopVehicleVisual', wrap_stop_visual)
        self._registry.hook(BattleFieldCtrl, 'updateVehiclesInfo', wrap_update_vehicles_info)
        self._registry.hook(BattleFieldCtrl, 'invalidateVehicleStatus', wrap_invalidate_status)
        self._installed = True

    def uninstall(self):
        self._installed = False
