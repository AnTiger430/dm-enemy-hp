# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..adapters.presenters.enemy_hp_payload_presenter import EnemyHpPayloadPresenter
from ..adapters.ui.gameface_panel_adapter import GamefaceEnemyPanelAdapter
from ..adapters.ui.visibility_guard import BattleVisibilityGuard
from ..application.config.validator import ConfigValidator
from ..application.use_cases.battle_health_session import BattleHealthSession
from ..domain.services.enemy_health_tracker import EnemyHealthTracker
from ..domain.services.row_order_policy import RowOrderPolicy
from ..infrastructure.logging_adapter.mod_file_logger import ModFileLogger
from ..infrastructure.storage.json_config_repository import JsonConfigRepository
from ..infrastructure.wot.arena_bridge import WotArenaBridge
from ..infrastructure.wot.battle_field_hook import WotBattleFieldHook
from ..infrastructure.wot.hook_utils import MethodHookRegistry
from ..infrastructure.wot.players_panel_monitor import WotPlayersPanelMonitor
from ..infrastructure.wot.reconciler_timer import WotReconcilerTimer, WotScheduler
from ..infrastructure.wot.vehicle_hook import WotVehicleHook
from .application import ModApplication


def build_application():
    """Composition Root constructing all layers with manual Constructor DI."""
    logger = ModFileLogger()
    config_repo = JsonConfigRepository(logger=logger)
    validator = ConfigValidator()

    tracker = EnemyHealthTracker()
    order_policy = RowOrderPolicy()
    presenter = EnemyHpPayloadPresenter()
    scheduler = WotScheduler()
    visibility_guard = BattleVisibilityGuard()
    panel_view = GamefaceEnemyPanelAdapter(scheduler=scheduler, logger=logger, visibility_guard=visibility_guard)

    hook_registry = MethodHookRegistry(logger=logger)
    panel_monitor = WotPlayersPanelMonitor(registry=hook_registry, panel_view=panel_view, logger=logger)
    arena_bridge = WotArenaBridge(panel_monitor=panel_monitor, logger=logger)

    session = BattleHealthSession(
        tracker=tracker,
        order_policy=order_policy,
        battle_state=arena_bridge,
        presenter=presenter,
        panel_view=panel_view,
        config_validator=validator,
        config_repo=config_repo,
        logger=logger,
    )
    panel_monitor.set_session(session)

    bf_hook = WotBattleFieldHook(registry=hook_registry, session=session, arena_bridge=arena_bridge, logger=logger)
    veh_hook = WotVehicleHook(registry=hook_registry, session=session, arena_bridge=arena_bridge, logger=logger)
    reconciler = WotReconcilerTimer(scheduler=scheduler, session=session, logger=logger)

    return ModApplication(
        session=session,
        hook_registry=hook_registry,
        bf_hook=bf_hook,
        veh_hook=veh_hook,
        panel_monitor=panel_monitor,
        arena_bridge=arena_bridge,
        reconciler=reconciler,
        scheduler=scheduler,
        logger=logger,
    )
