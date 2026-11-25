# -*- coding: utf-8 -*-
from __future__ import absolute_import

import codecs
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from dm_enemy_hp.adapters.presenters.enemy_hp_payload_presenter import EnemyHpPayloadPresenter
from dm_enemy_hp.application.config.defaults import DEFAULT_CONFIG
from dm_enemy_hp.application.config.validator import ConfigValidator
from dm_enemy_hp.domain.entities.enemy_vehicle_health import EnemyVehicleHealth
from dm_enemy_hp.domain.value_objects.color_spec import ColorSpec
from dm_enemy_hp.domain.value_objects.panel_layout_config import PanelLayoutConfig
from dm_enemy_hp.infrastructure.storage.json_config_repository import JsonConfigRepository


class TestPresentersAndConfig(unittest.TestCase):
    def test_config_validator_clamps_and_recovers_corrupt_values(self):
        v = ConfigValidator()
        cfg = v.normalize({
            'fontSize': 999,
            'rowHeight': 2,
            'offsetX': 'bad',
            'colorAlive': 'not_hex',
            'unspottedAlpha': -5,
            'modeRightOffsets': {'short': 5, 'large': 2000},
        })
        self.assertEqual(cfg['fontSize'], 32)
        self.assertEqual(cfg['rowHeight'], 12)
        self.assertEqual(cfg['offsetX'], DEFAULT_CONFIG['offsetX'])
        self.assertEqual(cfg['colorAlive'], '#FFFFFF')
        self.assertEqual(cfg['unspottedAlpha'], 0.05)
        self.assertEqual(cfg['modeRightOffsets']['short'], 20)
        self.assertEqual(cfg['modeRightOffsets']['large'], 800)

    def test_color_spec_and_layout_scaling(self):
        self.assertEqual(ColorSpec('#a1b2c3', 1.5).as_tuple(), ('#A1B2C3', 1.0))
        self.assertEqual(ColorSpec('bad', 'x').as_tuple(), ('#FFFFFF', 1.0))

        layout = PanelLayoutConfig(top_y=67, row_height=25, col_width=54, font_size=14)
        l1 = layout.compute(1920, 1080, 1.0, 'short', 15, visible=True)
        l2 = layout.compute(3840, 2160, 2.0, 'short', 15, visible=True)
        self.assertEqual(l1.x, 1920 - 171 - 54)
        self.assertEqual(l1.y, 67)
        self.assertEqual(l2.x, 3840 - (171 * 2) - (54 * 2))
        self.assertEqual(l2.y, 134)

    def test_config_v1_to_v2_migration_preserves_custom_values(self):
        v = ConfigValidator()
        migrated_v1 = v.normalize({
            'enabled': True,
            'topY': 56,
            'modeRightOffsets': {'short': 116, 'medium': 212, 'medium2': 212, 'large': 336},
        })
        self.assertEqual(migrated_v1['configVersion'], 4)
        self.assertEqual(migrated_v1['topY'], 67)
        self.assertEqual(migrated_v1['modeRightOffsets'], {'short': 171, 'medium': 246, 'medium2': 243, 'large': 382})

        migrated_v3 = v.normalize({
            'configVersion': 3,
            'topY': 67,
            'modeRightOffsets': {'short': 133, 'medium': 204, 'medium2': 229, 'large': 356},
        })
        self.assertEqual(migrated_v3['configVersion'], 4)
        self.assertEqual(migrated_v3['modeRightOffsets'], {'short': 171, 'medium': 246, 'medium2': 243, 'large': 382})

        custom = v.normalize({
            'configVersion': 3,
            'enabled': True,
            'topY': 80,
            'modeRightOffsets': {'short': 133, 'medium': 225, 'medium2': 229, 'large': 390},
        })
        self.assertEqual(custom['topY'], 80)
        self.assertEqual(custom['modeRightOffsets']['short'], 171)
        self.assertEqual(custom['modeRightOffsets']['medium'], 225)
        self.assertEqual(custom['modeRightOffsets']['medium2'], 243)
        self.assertEqual(custom['modeRightOffsets']['large'], 390)

    def test_presenter_formats_spotted_unspotted_and_dead_rows(self):
        presenter = EnemyHpPayloadPresenter()
        cfg = dict(DEFAULT_CONFIG, colorUnspotted='#B0B0B0', unspottedAlpha=0.75, showDeadZero=True)
        enemies = [
            EnemyVehicleHealth(1, 800, 1000, is_alive=True, is_spotted=True, ever_spotted=True),
            EnemyVehicleHealth(2, 650, 900, is_alive=True, is_spotted=False, ever_spotted=True),
            EnemyVehicleHealth(3, 0, 700, is_alive=False, is_spotted=False, ever_spotted=True),
        ]
        payload = presenter.build_payload(enemies, cfg, 1920, 1080, 1.0, 'medium', True)
        self.assertTrue(payload['visible'])
        rows = payload['rows']
        self.assertEqual(len(rows), 3)
        self.assertEqual((rows[0]['text'], rows[0]['color'], rows[0]['alpha']), ('800', '#FFFFFF', 1.0))
        self.assertEqual((rows[1]['text'], rows[1]['color'], rows[1]['alpha']), ('650', '#B0B0B0', 0.75))
        self.assertEqual((rows[2]['text'], rows[2]['visible'], rows[2]['color']), ('0', True, '#8C8C8C'))

    def test_json_config_repository_roundtrip_and_corrupt_recovery(self):
        tmp_dir = tempfile.mkdtemp(prefix='dm_enemy_hp_cfg_')
        try:
            cfg_path = os.path.join(tmp_dir, 'nested', 'config.json')
            repo = JsonConfigRepository(path=cfg_path)
            self.assertEqual(repo.load(), {})

            repo.save({'enabled': True, 'fontSize': 16})
            loaded = repo.load()
            self.assertEqual(loaded['fontSize'], 16)

            with codecs.open(cfg_path, 'w', 'utf-8') as f:
                f.write('{corrupt json')
            self.assertEqual(repo.load(), {})
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
