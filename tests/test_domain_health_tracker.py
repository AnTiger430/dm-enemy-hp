# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from dm_enemy_hp.domain.services.enemy_health_tracker import EnemyHealthTracker
from dm_enemy_hp.domain.services.row_order_policy import RowOrderPolicy


class TestEnemyHealthTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = EnemyHealthTracker()

    def test_battle_start_initializes_base_max_health(self):
        self.assertTrue(self.tracker.register_enemy(101, max_hp=1500))
        ent = self.tracker.get(101)
        self.assertEqual(ent.hp, 1500)
        self.assertEqual(ent.max_hp, 1500)
        self.assertTrue(ent.is_alive)
        self.assertFalse(ent.is_spotted)

    def test_ignores_allies_on_registration_and_events(self):
        self.assertFalse(self.tracker.register_enemy(201, max_hp=1400, is_enemy=False))
        self.assertIsNone(self.tracker.get(201))
        self.assertFalse(self.tracker.update_health(201, 500))
        self.assertFalse(self.tracker.mark_spotted(201, server_hp=500))
        self.assertFalse(self.tracker.mark_dead(201))

    def test_hardening_max_health_growth_before_and_after_damage(self):
        # Full HP enemy gets spotted with Hardening (1500 -> 1650): hp grows proportionally
        self.tracker.register_enemy(101, max_hp=1500)
        self.assertTrue(self.tracker.update_max_health(101, 1650))
        ent = self.tracker.get(101)
        self.assertEqual((ent.hp, ent.max_hp), (1650, 1650))

        # Unspotted enemy took blind damage (1500 -> 1100), then spots with Hardening (1650): delta preserves damage until server_hp overrides
        self.tracker.register_enemy(102, max_hp=1500)
        self.tracker.update_health(102, 1100)
        self.tracker.update_max_health(102, 1650)
        self.assertEqual((self.tracker.get(102).hp, self.tracker.get(102).max_hp), (1250, 1650))
        # Then server_hp on spot snaps to exact 1250 -> no spurious drift
        self.tracker.mark_spotted(102, server_hp=1250, max_hp=1650)
        self.assertEqual(self.tracker.get(102).hp, 1250)

        # Already spotted and damaged enemy does NOT get fake HP added if max_hp updates late
        self.tracker.register_enemy(103, max_hp=1500)
        self.tracker.mark_spotted(103, server_hp=1200, max_hp=1500)
        self.tracker.update_max_health(103, 1650)
        self.assertEqual((self.tracker.get(103).hp, self.tracker.get(103).max_hp), (1200, 1650))

    def test_in_aoi_and_out_of_aoi_damage_updates(self):
        self.tracker.register_enemy(101, max_hp=2000)
        # Out-of-AOI (>564m): server sends newHealth while never having AOI entity
        self.assertTrue(self.tracker.update_health(101, 1620))
        self.assertEqual(self.tracker.get(101).hp, 1620)
        # In-AOI damage (shot / fire / ram)
        self.assertTrue(self.tracker.update_health(101, 980, spotted=True))
        ent = self.tracker.get(101)
        self.assertEqual(ent.hp, 980)
        self.assertTrue(ent.is_spotted)

    def test_unspot_preserves_last_known_hp_never_resets_to_max(self):
        self.tracker.register_enemy(101, max_hp=1800)
        self.tracker.mark_spotted(101, server_hp=1800, max_hp=1800)
        self.tracker.update_health(101, 640)
        self.assertTrue(self.tracker.mark_unspotted(101))
        ent = self.tracker.get(101)
        self.assertFalse(ent.is_spotted)
        self.assertEqual(ent.hp, 640)
        self.assertEqual(ent.max_hp, 1800)

        # Re-registering arena info during battle must NOT reset HP back to max_hp
        self.assertFalse(self.tracker.register_enemy(101, max_hp=1800, is_alive=True))
        self.assertEqual(self.tracker.get(101).hp, 640)

    def test_respot_after_blind_damage_updates_immediately(self):
        self.tracker.register_enemy(101, max_hp=1400)
        self.tracker.mark_spotted(101, server_hp=1100)
        self.tracker.mark_unspotted(101)
        self.assertEqual(self.tracker.get(101).hp, 1100)

        # Enemy took blind shot / fire / fall damage while unspotted -> real HP is now 420
        self.assertTrue(self.tracker.mark_spotted(101, server_hp=420, max_hp=1400))
        ent = self.tracker.get(101)
        self.assertTrue(ent.is_spotted)
        self.assertEqual(ent.hp, 420)

    def test_respot_without_hp_change_only_flips_spotted_and_noop_repeats(self):
        self.tracker.register_enemy(101, max_hp=900)
        self.tracker.mark_spotted(101, server_hp=700)
        self.tracker.mark_unspotted(101)
        self.assertTrue(self.tracker.mark_spotted(101, server_hp=700))
        # Second identical spot call is a no-op
        self.assertFalse(self.tracker.mark_spotted(101, server_hp=700))

    def test_death_in_spot_unspot_and_overkill_clamp_to_zero(self):
        self.tracker.register_enemy(101, max_hp=1000)
        self.tracker.mark_spotted(101, server_hp=1000)
        # Overkill (ammorack / big HE): negative raw health clamps to 0 and marks dead
        self.assertTrue(self.tracker.update_health(101, -350))
        ent1 = self.tracker.get(101)
        self.assertEqual(ent1.hp, 0)
        self.assertFalse(ent1.is_alive)
        self.assertFalse(ent1.is_spotted)

        # Killed in unspot via arena kill event
        self.tracker.register_enemy(102, max_hp=800)
        self.tracker.update_health(102, 500)
        self.assertTrue(self.tracker.mark_dead(102))
        ent2 = self.tracker.get(102)
        self.assertEqual(ent2.hp, 0)
        self.assertFalse(ent2.is_alive)

    def test_dead_enemy_is_not_resurrected_by_stale_updates(self):
        self.tracker.register_enemy(101, max_hp=1000)
        self.tracker.mark_dead(101)
        self.assertFalse(self.tracker.update_health(101, 200))
        self.assertFalse(self.tracker.mark_spotted(101, server_hp=200))
        self.assertFalse(self.tracker.reconcile_from_snapshot(101, health=200, is_alive=None))
        ent = self.tracker.get(101)
        self.assertEqual((ent.hp, ent.is_alive, ent.is_spotted), (0, False, False))

    def test_reset_between_battles_is_clean(self):
        self.tracker.register_enemy(101, max_hp=900)
        self.tracker.reset()
        self.assertEqual(self.tracker.all_enemies(), [])
        self.assertIsNone(self.tracker.get(101))

    def test_fallback_row_order_policy_matches_wot_order(self):
        policy = RowOrderPolicy()
        entries = [
            {'vehicle_id': 3, 'is_alive': False, 'level': 10, 'class_tag': 'heavyTank', 'vehicle_name': 'Maus', 'player_name': 'Z'},
            {'vehicle_id': 2, 'is_alive': True, 'level': 8, 'class_tag': 'SPG', 'vehicle_name': 'M40', 'player_name': 'A'},
            {'vehicle_id': 1, 'is_alive': True, 'level': 10, 'class_tag': 'mediumTank', 'vehicle_name': 'Obj140', 'player_name': 'B'},
            {'vehicle_id': 4, 'is_alive': True, 'level': 10, 'class_tag': 'heavyTank', 'vehicle_name': 'IS-7', 'player_name': 'C'},
        ]
        self.assertEqual(policy.sort_ids(entries), [4, 1, 2, 3])


if __name__ == '__main__':
    unittest.main()
