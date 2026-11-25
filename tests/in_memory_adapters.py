# -*- coding: utf-8 -*-
from __future__ import absolute_import

import copy

from dm_enemy_hp.application.ports.battle_state_provider import IBattleStateProvider
from dm_enemy_hp.application.ports.config_repository import IConfigRepository
from dm_enemy_hp.application.ports.logger import ILogger
from dm_enemy_hp.application.ports.panel_view import IEnemyPanelView
from dm_enemy_hp.application.ports.scheduler import IScheduler


class InMemoryConfigRepository(IConfigRepository):
    def __init__(self, initial=None):
        self.data = copy.deepcopy(initial) if initial is not None else {}
        self.save_calls = 0

    def load(self):
        return copy.deepcopy(self.data)

    def save(self, data):
        self.save_calls += 1
        self.data = copy.deepcopy(data)


class InMemoryEnemyPanelView(IEnemyPanelView):
    def __init__(self):
        self.built = False
        self.destroyed = False
        self.visible = False
        self.pushed_payloads = []
        self.visibility_history = []

    def build(self):
        self.built = True
        self.destroyed = False

    def push_state(self, payload):
        self.pushed_payloads.append(copy.deepcopy(payload))

    def set_visible(self, visible):
        self.visible = bool(visible)
        self.visibility_history.append(self.visible)

    def destroy(self):
        self.destroyed = True
        self.built = False


class InMemoryBattleStateProvider(IBattleStateProvider):
    def __init__(self):
        self.roster = []
        self.ordered_ids = []
        self.snapshots = {}
        self.panel_mode = 'short'
        self.hud_visible = True
        self.screen_metrics = (1920.0, 1080.0, 1.0)

    def get_enemy_roster(self):
        return copy.deepcopy(self.roster)

    def get_ordered_enemy_ids(self):
        return list(self.ordered_ids)

    def get_health_snapshot(self, vehicle_id):
        snap = self.snapshots.get(int(vehicle_id))
        return dict(snap) if snap is not None else None

    def get_panel_mode(self):
        return self.panel_mode

    def is_hud_visible(self):
        return self.hud_visible

    def get_screen_metrics(self):
        return self.screen_metrics


class InMemoryLogger(ILogger):
    def __init__(self):
        self.infos = []
        self.debugs = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)

    def error(self, msg):
        self.errors.append(msg)


class ManualScheduler(IScheduler):
    def __init__(self):
        self._next_id = 1
        self.tasks = {}

    def schedule(self, delay_sec, callback):
        token = self._next_id
        self._next_id += 1
        self.tasks[token] = (float(delay_sec), callback)
        return token

    def cancel(self, token):
        self.tasks.pop(token, None)

    def run_next(self):
        if not self.tasks:
            return False
        token = sorted(self.tasks.keys())[0]
        _delay, cb = self.tasks.pop(token)
        cb()
        return True
