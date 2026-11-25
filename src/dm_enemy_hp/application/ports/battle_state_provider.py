# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IBattleStateProvider(object):
    """Port querying live WoT arena roster, ordered enemy IDs, health snapshots, and screen metrics."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_enemy_roster(self):
        """Return list of dicts: {vehicle_id, max_hp, is_alive, current_hp, is_spotted, ...}."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_ordered_enemy_ids(self):
        """Return enemy vehicle IDs sorted identically to WoT right PlayersPanel."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_health_snapshot(self, vehicle_id):
        """Return dict {health, max_hp, is_alive, is_spotted} or None if unavailable."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_panel_mode(self):
        """Return normalized mode: 'hidden'|'short'|'medium'|'medium2'|'large'."""
        raise NotImplementedError

    @abc.abstractmethod
    def is_hud_visible(self):
        """Return True when battle HUD and right players panel should be visible."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_screen_metrics(self):
        """Return tuple (screen_w, screen_h, ui_scale)."""
        raise NotImplementedError
