# -*- coding: utf-8 -*-
from __future__ import absolute_import

import copy

from .config_defaults_accessor import load_validated_config


class BattleHealthSession(object):
    """Application use-case orchestrating live enemy HP tracking, ordering, and UI push."""

    def __init__(self, tracker, order_policy, battle_state, presenter,
                 panel_view, config_validator, config_repo, logger):
        self._tracker = tracker
        self._order_policy = order_policy
        self._battle_state = battle_state
        self._presenter = presenter
        self._panel_view = panel_view
        self._validator = config_validator
        self._config_repo = config_repo
        self._logger = logger

        self._in_battle = False
        self._cfg = load_validated_config(config_repo, config_validator)
        self._roster_meta = {}
        self._last_signature = None

    @property
    def config(self):
        return copy.deepcopy(self._cfg)

    @property
    def in_battle(self):
        return self._in_battle

    def reload_config(self):
        self._cfg = load_validated_config(self._config_repo, self._validator)
        if self._in_battle:
            self._sync_view(force=True)
        return self.config

    def start_battle(self):
        self._cfg = load_validated_config(self._config_repo, self._validator)
        self._in_battle = True
        self._last_signature = None
        self._roster_meta = {}
        self._tracker.reset()
        self.on_arena_vehicles_loaded()
        if self._last_signature is None:
            self._sync_view(force=True)

    def end_battle(self):
        self._in_battle = False
        self._last_signature = None
        self._roster_meta = {}
        self._tracker.reset()
        try:
            self._panel_view.destroy()
        except Exception:
            self._logger.error('Failed to destroy enemy HP panel view on battle end')

    def on_arena_vehicles_loaded(self):
        if not self._in_battle:
            return
        roster = self._battle_state.get_enemy_roster() or ()
        for item in roster:
            vid = item.get('vehicle_id')
            if vid is None:
                continue
            vid = int(vid)
            self._roster_meta[vid] = dict(item)
            snap = self._battle_state.get_health_snapshot(vid)
            current_hp = snap.get('health') if snap else item.get('current_hp')
            max_hp = (snap.get('max_hp') if snap and snap.get('max_hp') else item.get('max_hp', 0))
            is_alive = snap.get('is_alive', item.get('is_alive', True)) if snap else item.get('is_alive', True)
            self._tracker.register_enemy(
                vid,
                max_hp=max_hp,
                is_alive=is_alive,
                current_hp=current_hp,
                is_enemy=True,
            )
            if snap and snap.get('is_spotted'):
                self._tracker.mark_spotted(vid, server_hp=snap.get('health'), max_hp=snap.get('max_hp'))
        self._sync_view()

    def on_vehicle_added(self, vehicle_id, max_hp, is_alive=True, current_hp=None, is_enemy=True, meta=None):
        if not self._in_battle or not is_enemy:
            return False
        vid = int(vehicle_id)
        if isinstance(meta, dict):
            self._roster_meta[vid] = dict(meta, vehicle_id=vid, is_alive=bool(is_alive))
        elif vid not in self._roster_meta:
            self._roster_meta[vid] = {'vehicle_id': vid, 'is_alive': bool(is_alive)}

        changed = self._tracker.register_enemy(
            vid, max_hp=max_hp, is_alive=is_alive, current_hp=current_hp, is_enemy=True,
        )
        snap = self._battle_state.get_health_snapshot(vid)
        if snap is not None:
            changed = self._tracker.reconcile_from_snapshot(
                vid,
                health=snap.get('health'),
                max_hp=snap.get('max_hp'),
                is_alive=snap.get('is_alive'),
                is_spotted=snap.get('is_spotted'),
            ) or changed
        if changed:
            self._sync_view()
        return changed

    def on_vehicle_updated(self, vehicle_id, max_hp=None, is_alive=None, is_enemy=True, meta=None):
        if not self._in_battle or not is_enemy:
            return False
        vid = int(vehicle_id)
        if vid in self._roster_meta and isinstance(meta, dict):
            self._roster_meta[vid].update(meta)
        changed = False
        if self._tracker.get(vid) is None and max_hp is not None:
            changed = self._tracker.register_enemy(
                vid, max_hp=max_hp, is_alive=True if is_alive is None else is_alive, is_enemy=True,
            )
        else:
            if max_hp is not None:
                changed = self._tracker.update_max_health(vid, max_hp) or changed
            if is_alive is False:
                changed = self._tracker.mark_dead(vid) or changed
        if is_alive is False and vid in self._roster_meta:
            self._roster_meta[vid]['is_alive'] = False
        if changed:
            self._sync_view()
        return changed

    def on_vehicle_health_changed(self, vehicle_id, new_hp, max_hp=None, is_spotted=None):
        if not self._in_battle:
            return False
        changed = self._tracker.update_health(vehicle_id, new_hp, max_hp=max_hp, spotted=is_spotted)
        if changed:
            self._sync_view()
        return changed

    def on_vehicle_spotted(self, vehicle_id, server_hp=None, max_hp=None):
        if not self._in_battle:
            return False
        vid = int(vehicle_id)
        if server_hp is None or max_hp is None:
            snap = self._battle_state.get_health_snapshot(vid)
            if snap is not None:
                if server_hp is None:
                    server_hp = snap.get('health')
                if max_hp is None:
                    max_hp = snap.get('max_hp')
        changed = self._tracker.mark_spotted(vid, server_hp=server_hp, max_hp=max_hp)
        if changed:
            self._sync_view()
        return changed

    def on_vehicle_unspotted(self, vehicle_id):
        if not self._in_battle:
            return False
        changed = self._tracker.mark_unspotted(vehicle_id)
        if changed:
            self._sync_view()
        return changed

    def on_vehicle_killed(self, vehicle_id):
        if not self._in_battle:
            return False
        vid = int(vehicle_id)
        if vid in self._roster_meta:
            self._roster_meta[vid]['is_alive'] = False
        changed = self._tracker.mark_dead(vid)
        if changed:
            self._sync_view()
        return changed

    def on_panel_mode_changed(self, _mode=None):
        if self._in_battle:
            self._sync_view()

    def on_visibility_changed(self, _visible=None):
        if self._in_battle:
            self._sync_view()

    def reconcile_tick(self):
        if not self._in_battle:
            return False
        any_changed = False
        enemies = self._tracker.all_enemies()
        if not enemies:
            self.on_arena_vehicles_loaded()
            enemies = self._tracker.all_enemies()
        for enemy in enemies:
            snap = self._battle_state.get_health_snapshot(enemy.vehicle_id)
            if snap is None:
                continue
            changed = self._tracker.reconcile_from_snapshot(
                enemy.vehicle_id,
                health=snap.get('health'),
                max_hp=snap.get('max_hp'),
                is_alive=snap.get('is_alive'),
                is_spotted=snap.get('is_spotted'),
            )
            if changed:
                any_changed = True
                if not self._tracker.get(enemy.vehicle_id).is_alive and enemy.vehicle_id in self._roster_meta:
                    self._roster_meta[enemy.vehicle_id]['is_alive'] = False
        self._sync_view()
        return any_changed

    def _ordered_enemies(self):
        provider_ids = list(self._battle_state.get_ordered_enemy_ids() or ())
        if not provider_ids and self._roster_meta:
            for meta in self._roster_meta.values():
                ent = self._tracker.get(meta['vehicle_id'])
                if ent is not None:
                    meta['is_alive'] = ent.is_alive
            provider_ids = self._order_policy.sort_ids(list(self._roster_meta.values()))

        seen = set()
        ordered = []
        for vid in provider_ids:
            iv = int(vid)
            ent = self._tracker.get(iv)
            if ent is not None and iv not in seen:
                seen.add(iv)
                ordered.append(ent)

        remaining = [e for e in self._tracker.all_enemies() if e.vehicle_id not in seen]
        if remaining:
            remaining.sort(key=lambda e: (0 if e.is_alive else 1, e.vehicle_id))
            ordered.extend(remaining)
        return ordered

    def _sync_view(self, force=False):
        if not self._in_battle:
            return
        enabled = bool(self._cfg.get('enabled', True))
        if not enabled:
            sig = ('disabled',)
            if force or sig != self._last_signature:
                self._last_signature = sig
                self._panel_view.set_visible(False)
            return

        ordered = self._ordered_enemies()
        panel_mode = self._battle_state.get_panel_mode()
        hud_visible = bool(self._battle_state.is_hud_visible())
        screen_w, screen_h, ui_scale = self._battle_state.get_screen_metrics()
        payload = self._presenter.build_payload(
            ordered, self._cfg, screen_w, screen_h, ui_scale, panel_mode, hud_visible,
        )
        sig = payload.pop('_signature', None)
        if not force and sig is not None and sig == self._last_signature:
            return
        self._last_signature = sig
        want_visible = bool(payload.get('visible', False))
        if want_visible:
            self._panel_view.build()
        self._panel_view.set_visible(want_visible)
        self._panel_view.push_state(payload)
