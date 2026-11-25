# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...application.ports.battle_state_provider import IBattleStateProvider

try:
    import BigWorld
except Exception:
    BigWorld = None

try:
    import GUI
except Exception:
    GUI = None

try:
    from helpers import dependency
    from skeletons.gui.battle_session import IBattleSessionProvider
except Exception:
    dependency = None
    IBattleSessionProvider = None

try:
    from skeletons.account_helpers.settings_core import ISettingsCore
    from account_helpers.settings_core.settings_constants import GRAPHICS
except Exception:
    ISettingsCore = None
    GRAPHICS = None

try:
    from gui.battle_control.arena_info.vos_collections import EnemyItemsCollection, VehicleInfoSortKey
except Exception:
    EnemyItemsCollection = None
    VehicleInfoSortKey = None


class WotArenaBridge(IBattleStateProvider):
    """Bridges WoT ClientArena, BattleSessionProvider, BattleFieldCtrl, and entities."""

    def __init__(self, panel_monitor, logger):
        self._panel_monitor = panel_monitor
        self._logger = logger
        self._session = None
        self._arena = None
        self._cb_new_list = None
        self._cb_added = None
        self._cb_updated = None
        self._cb_killed = None
        self._cb_health = None

    def bind_arena(self, session):
        self.unbind_arena()
        self._session = session
        player = BigWorld.player() if BigWorld is not None else None
        arena = getattr(player, 'arena', None) if player is not None else None
        if arena is None:
            return
        self._arena = arena

        def on_new_list(*_args):
            try:
                session.on_arena_vehicles_loaded()
            except Exception:
                self._logger.error('onNewVehicleListReceived error')

        def on_added(*args):
            try:
                if args:
                    self._handle_arena_add_or_update(int(args[0]), is_add=True)
            except Exception:
                self._logger.error('onVehicleAdded error')

        def on_updated(*args):
            try:
                if args:
                    self._handle_arena_add_or_update(int(args[0]), is_add=False)
            except Exception:
                self._logger.error('onVehicleUpdated error')

        def on_killed(*args):
            try:
                if args and self.is_enemy(int(args[0])):
                    session.on_vehicle_killed(int(args[0]))
            except Exception:
                self._logger.error('onVehicleKilled error')

        def on_health(*args):
            try:
                if not args:
                    return
                vid = int(args[0])
                if not self.is_enemy(vid):
                    return
                snap = self.get_health_snapshot(vid)
                if snap is not None and snap.get('health') is not None:
                    session.on_vehicle_health_changed(
                        vid, snap['health'], max_hp=snap.get('max_hp'), is_spotted=snap.get('is_spotted'),
                    )
            except Exception:
                self._logger.error('onVehicleHealthChanged error')

        self._cb_new_list = on_new_list
        self._cb_added = on_added
        self._cb_updated = on_updated
        self._cb_killed = on_killed
        self._cb_health = on_health

        self._subscribe(arena, 'onNewVehicleListReceived', on_new_list)
        self._subscribe(arena, 'onVehicleAdded', on_added)
        self._subscribe(arena, 'onVehicleUpdated', on_updated)
        self._subscribe(arena, 'onVehicleKilled', on_killed)
        self._subscribe(arena, 'onVehicleHealthChanged', on_health)

    def unbind_arena(self):
        arena = self._arena
        self._arena = None
        self._session = None
        if arena is not None:
            self._unsubscribe(arena, 'onNewVehicleListReceived', self._cb_new_list)
            self._unsubscribe(arena, 'onVehicleAdded', self._cb_added)
            self._unsubscribe(arena, 'onVehicleUpdated', self._cb_updated)
            self._unsubscribe(arena, 'onVehicleKilled', self._cb_killed)
            self._unsubscribe(arena, 'onVehicleHealthChanged', self._cb_health)
        self._cb_new_list = None
        self._cb_added = None
        self._cb_updated = None
        self._cb_killed = None
        self._cb_health = None

    @staticmethod
    def _subscribe(arena, event_name, fn):
        if fn is None or not hasattr(arena, event_name):
            return
        try:
            ev = getattr(arena, event_name)
            ev += fn
            setattr(arena, event_name, ev)
        except Exception:
            pass

    @staticmethod
    def _unsubscribe(arena, event_name, fn):
        if fn is None or not hasattr(arena, event_name):
            return
        try:
            ev = getattr(arena, event_name)
            ev -= fn
            setattr(arena, event_name, ev)
        except Exception:
            pass

    def _get_session_provider(self):
        if dependency is None or IBattleSessionProvider is None:
            return None
        try:
            return dependency.instance(IBattleSessionProvider)
        except Exception:
            return None

    def _get_arena_dp(self):
        sp = self._get_session_provider()
        if sp is None:
            return None
        try:
            return sp.getArenaDP()
        except Exception:
            return None

    def _get_battle_field_ctrl(self):
        sp = self._get_session_provider()
        shared = getattr(sp, 'shared', None) if sp is not None else None
        return getattr(shared, 'battleField', None) if shared is not None else None

    @staticmethod
    def _safe_get_entity(vid):
        if BigWorld is None:
            return None
        entities = getattr(BigWorld, 'entities', None)
        if entities is None:
            return None
        try:
            return entities.get(vid)
        except Exception:
            return None

    def is_enemy(self, vehicle_id, battle_field=None, arena_dp=None, v_info=None):
        vid = int(vehicle_id)
        dp = arena_dp if arena_dp is not None else self._get_arena_dp()
        if dp is not None:
            info = v_info if v_info is not None else dp.getVehicleInfo(vid)
            if info is not None:
                try:
                    if hasattr(info, 'isObserver') and info.isObserver():
                        return False
                except Exception:
                    pass
                try:
                    return bool(dp.isEnemyTeam(info.team))
                except Exception:
                    pass
        player = BigWorld.player() if BigWorld is not None else None
        arena = getattr(player, 'arena', None) if player is not None else None
        if arena is not None:
            vmap = getattr(arena, 'vehicles', None)
            raw = vmap.get(vid) if isinstance(vmap, dict) else None
            if isinstance(raw, dict):
                player_team = getattr(player, 'team', None)
                if player_team is not None and 'team' in raw:
                    return int(raw['team']) != int(player_team)
        return False

    def _handle_arena_add_or_update(self, vid, is_add):
        if self._session is None or not self.is_enemy(vid):
            return
        dp = self._get_arena_dp()
        max_hp = None
        is_alive = True
        meta = {'vehicle_id': vid}
        if dp is not None:
            v_info = dp.getVehicleInfo(vid)
            if v_info is not None:
                meta = self._meta_from_vo(v_info)
                vtype = getattr(v_info, 'vehicleType', None)
                max_hp = getattr(vtype, 'maxHealth', None) if vtype is not None else None
                is_alive = v_info.isAlive() if hasattr(v_info, 'isAlive') else True
        if max_hp is None:
            player = BigWorld.player() if BigWorld is not None else None
            arena = getattr(player, 'arena', None) if player is not None else None
            raw = (arena.vehicles or {}).get(vid) if arena is not None else None
            if isinstance(raw, dict):
                vtype = raw.get('vehicleType')
                max_hp = getattr(vtype, 'maxHealth', None) if vtype is not None else raw.get('maxHealth')
                if 'isAlive' in raw:
                    is_alive = bool(raw['isAlive'])
        if is_add and max_hp is not None:
            self._session.on_vehicle_added(vid, max_hp=max_hp, is_alive=is_alive, is_enemy=True, meta=meta)
        else:
            self._session.on_vehicle_updated(vid, max_hp=max_hp, is_alive=is_alive, is_enemy=True, meta=meta)

    @staticmethod
    def _meta_from_vo(v_info):
        vtype = getattr(v_info, 'vehicleType', None)
        player = getattr(v_info, 'player', None)
        return {
            'vehicle_id': int(getattr(v_info, 'vehicleID', 0)),
            'is_alive': bool(v_info.isAlive()) if hasattr(v_info, 'isAlive') else True,
            'max_hp': int(getattr(vtype, 'maxHealth', 0) or 0) if vtype is not None else 0,
            'level': int(getattr(vtype, 'level', 0) or 0) if vtype is not None else 0,
            'class_tag': str(getattr(vtype, 'classTag', '') or '') if vtype is not None else '',
            'vehicle_name': str(getattr(vtype, 'shortName', '') or '') if vtype is not None else '',
            'player_name': str(getattr(player, 'name', '') or '') if player is not None else '',
        }

    def get_enemy_roster(self):
        dp = self._get_arena_dp()
        roster = []
        if dp is not None and hasattr(dp, 'getVehiclesInfoIterator'):
            try:
                for v_info in dp.getVehiclesInfoIterator():
                    if v_info is None:
                        continue
                    if hasattr(v_info, 'isObserver') and v_info.isObserver():
                        continue
                    if not dp.isEnemyTeam(v_info.team):
                        continue
                    meta = self._meta_from_vo(v_info)
                    snap = self.get_health_snapshot(meta['vehicle_id'])
                    if snap is not None:
                        meta['current_hp'] = snap.get('health')
                        if snap.get('max_hp'):
                            meta['max_hp'] = snap['max_hp']
                        if snap.get('is_alive') is not None:
                            meta['is_alive'] = snap['is_alive']
                        meta['is_spotted'] = snap.get('is_spotted', False)
                    roster.append(meta)
                if roster:
                    return roster
            except Exception:
                self._logger.error('getVehiclesInfoIterator failed')

        player = BigWorld.player() if BigWorld is not None else None
        arena = getattr(player, 'arena', None) if player is not None else None
        if arena is None:
            return []
        player_team = getattr(player, 'team', None)
        vmap = getattr(arena, 'vehicles', None) or {}
        for vid, raw in vmap.items():
            if not isinstance(raw, dict):
                continue
            if player_team is not None and raw.get('team') == player_team:
                continue
            vtype = raw.get('vehicleType')
            if vtype is not None and 'observer' in (getattr(getattr(vtype, 'type', None), 'tags', ()) or ()):
                continue
            max_hp = getattr(vtype, 'maxHealth', None) if vtype is not None else raw.get('maxHealth', 0)
            roster.append({
                'vehicle_id': int(vid),
                'max_hp': int(max_hp or 0),
                'is_alive': bool(raw.get('isAlive', True)),
                'player_name': str(raw.get('name', '') or ''),
            })
        return roster

    def get_ordered_enemy_ids(self):
        dp = self._get_arena_dp()
        if dp is None:
            return []
        if EnemyItemsCollection is not None and VehicleInfoSortKey is not None:
            try:
                col = EnemyItemsCollection(sortKey=VehicleInfoSortKey)
                ids = []
                for v_info, _v_stats in col.iterator(dp):
                    if v_info is None:
                        continue
                    if hasattr(v_info, 'isObserver') and v_info.isObserver():
                        continue
                    ids.append(int(v_info.vehicleID))
                return ids
            except Exception:
                self._logger.error('EnemyItemsCollection.iterator failed')
        return []

    def get_health_snapshot(self, vehicle_id):
        vid = int(vehicle_id)
        dp = self._get_arena_dp()
        bf = self._get_battle_field_ctrl()

        is_alive = None
        if dp is not None:
            v_info = dp.getVehicleInfo(vid)
            if v_info is not None and hasattr(v_info, 'isAlive'):
                is_alive = bool(v_info.isAlive())

        player = BigWorld.player() if BigWorld is not None else None
        arena = getattr(player, 'arena', None) if player is not None else None
        if arena is not None:
            vmap = getattr(arena, 'vehicles', None)
            raw_v = vmap.get(vid) if isinstance(vmap, dict) else None
            if isinstance(raw_v, dict) and raw_v.get('isAlive') is False:
                is_alive = False

        bf_health = None
        bf_max = None
        if bf is not None and hasattr(bf, 'getVehicleHealthInfo'):
            try:
                info = bf.getVehicleHealthInfo(vid)
                if info is not None and len(info) >= 2:
                    bf_health = int(info[0])
                    bf_max = int(info[1])
            except Exception:
                pass

        ent = self._safe_get_entity(vid)
        ent_health = None
        ent_max = None
        is_spotted = None
        if ent is not None and getattr(ent, 'isStarted', False):
            is_spotted = True
            if hasattr(ent, 'isAlive') and not ent.isAlive():
                is_alive = False
                ent_health = 0
                is_spotted = False
            elif hasattr(ent, 'health'):
                ent_health = int(getattr(ent, 'health'))
                if ent_health <= 0:
                    is_alive = False
                    ent_health = 0
                    is_spotted = False
            em = getattr(ent, 'maxHealth', None)
            if not em and isinstance(getattr(ent, 'publicInfo', None), dict):
                em = ent.publicInfo.get('maxHealth')
            if em:
                ent_max = int(em)
        elif ent is None and is_alive is True:
            is_spotted = False

        if is_alive is False:
            return {'health': 0, 'max_hp': ent_max or bf_max, 'is_alive': False, 'is_spotted': False}

        health = ent_health if ent_health is not None else bf_health
        max_hp = ent_max if ent_max is not None else bf_max
        if health is None and max_hp is None and is_alive is None:
            return None
        return {
            'health': health,
            'max_hp': max_hp,
            'is_alive': is_alive,
            'is_spotted': is_spotted,
        }

    def get_panel_mode(self):
        return self._panel_monitor.get_mode()

    def is_hud_visible(self):
        return self._panel_monitor.is_hud_visible()

    def get_screen_metrics(self):
        sw, sh = 1920.0, 1080.0
        if GUI is not None:
            try:
                w, h = GUI.screenResolution()[:2]
                sw, sh = float(w), float(h)
            except Exception:
                pass
        ui_scale = 1.0
        if dependency is not None and ISettingsCore is not None:
            try:
                sc = dependency.instance(ISettingsCore)
                scale_mgr = getattr(sc, 'interfaceScale', None) if sc is not None else None
                raw = scale_mgr.get() if scale_mgr is not None and hasattr(scale_mgr, 'get') else None
                if raw is not None:
                    fval = float(raw)
                    if 0.1 < fval <= 4.0:
                        ui_scale = fval
            except Exception:
                pass
        return sw, sh, ui_scale
