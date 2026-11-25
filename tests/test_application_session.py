# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dm_enemy_hp.adapters.presenters.enemy_hp_payload_presenter import EnemyHpPayloadPresenter
from dm_enemy_hp.application.config.validator import ConfigValidator
from dm_enemy_hp.application.use_cases.battle_health_session import BattleHealthSession
from dm_enemy_hp.domain.services.enemy_health_tracker import EnemyHealthTracker
from dm_enemy_hp.domain.services.row_order_policy import RowOrderPolicy
from in_memory_adapters import (
    InMemoryBattleStateProvider,
    InMemoryConfigRepository,
    InMemoryEnemyPanelView,
    InMemoryLogger,
)


class TestBattleHealthSession(unittest.TestCase):
    def setUp(self):
        self.tracker = EnemyHealthTracker()
        self.order_policy = RowOrderPolicy()
        self.state = InMemoryBattleStateProvider()
        self.presenter = EnemyHpPayloadPresenter()
        self.view = InMemoryEnemyPanelView()
        self.validator = ConfigValidator()
        self.repo = InMemoryConfigRepository()
        self.logger = InMemoryLogger()
        self.session = BattleHealthSession(
            self.tracker, self.order_policy, self.state, self.presenter,
            self.view, self.validator, self.repo, self.logger,
        )

    def test_row_order_matches_players_panel_and_dirty_check_suppresses_duplicates(self):
        self.state.roster = [
            {'vehicle_id': 11, 'max_hp': 900, 'is_alive': True},
            {'vehicle_id': 12, 'max_hp': 650, 'is_alive': True},
            {'vehicle_id': 13, 'max_hp': 470, 'is_alive': True},
        ]
        # PlayersPanel order puts 12 first, 11 second, 13 third
        self.state.ordered_ids = [12, 11, 13]
        self.session.start_battle()

        self.assertTrue(self.view.built)
        self.assertEqual(len(self.view.pushed_payloads), 1)
        rows = self.view.pushed_payloads[-1]['rows']
        self.assertEqual([(r['id'], r['text']) for r in rows], [(12, '650'), (11, '900'), (13, '470')])

        # Duplicate panel mode callback without change must NOT push duplicate state
        self.session.on_panel_mode_changed('short')
        self.assertEqual(len(self.view.pushed_payloads), 1)

        # Switching panel mode to 'large' shifts x and pushes once
        self.state.panel_mode = 'large'
        self.session.on_panel_mode_changed('large')
        self.assertEqual(len(self.view.pushed_payloads), 2)
        self.assertLess(self.view.pushed_payloads[1]['x'], self.view.pushed_payloads[0]['x'])

    def test_visibility_toggles_hide_and_restore(self):
        self.state.roster = [{'vehicle_id': 1, 'max_hp': 900, 'is_alive': True}]
        self.state.ordered_ids = [1]
        self.session.start_battle()
        self.assertTrue(self.view.visible)

        # HUD hidden (V / Tab / Esc / Killcam)
        self.state.hud_visible = False
        self.session.on_visibility_changed(False)
        self.assertFalse(self.view.visible)

        # HUD restored, panel mode 'hidden'
        self.state.hud_visible = True
        self.state.panel_mode = 'hidden'
        self.session.on_panel_mode_changed('hidden')
        self.assertFalse(self.view.visible)

        # Panel mode 'medium' restores visibility
        self.state.panel_mode = 'medium'
        self.session.on_panel_mode_changed('medium')
        self.assertTrue(self.view.visible)

    def test_mid_battle_reconnect_and_reconciler_catch_blind_damage(self):
        self.state.roster = [
            {'vehicle_id': 10, 'max_hp': 1500, 'is_alive': True, 'current_hp': 950, 'is_spotted': False},
            {'vehicle_id': 20, 'max_hp': 1200, 'is_alive': False, 'current_hp': 0},
        ]
        self.state.ordered_ids = [10, 20]
        self.session.start_battle()
        rows = self.view.pushed_payloads[-1]['rows']
        self.assertEqual(rows[0]['text'], '950')
        self.assertEqual((rows[1]['text'], rows[1]['visible']), ('', False))

        # Enemy 10 re-enters spot with updated server snapshot via reconciler tick
        self.state.snapshots[10] = {'health': 410, 'max_hp': 1650, 'is_alive': True, 'is_spotted': True}
        self.assertTrue(self.session.reconcile_tick())
        rows = self.view.pushed_payloads[-1]['rows']
        self.assertEqual(rows[0]['text'], '410')
        self.assertTrue(rows[0]['spotted'])

        self.session.end_battle()
        self.assertTrue(self.view.destroyed)
        self.assertFalse(self.session.in_battle)


if __name__ == '__main__':
    unittest.main()
