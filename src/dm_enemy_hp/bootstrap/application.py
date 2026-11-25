# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..application.config.defaults import MOD_ID, MOD_VERSION

try:
    from PlayerEvents import g_playerEvents
except Exception:
    g_playerEvents = None

try:
    from ReplayEvents import g_replayEvents
except Exception:
    g_replayEvents = None

try:
    from helpers import isPlayerAvatar
except Exception:
    isPlayerAvatar = None


class ModApplication(object):
    """Lifecycle controller binding WoT player/replay events to BattleHealthSession."""

    def __init__(self, session, hook_registry, bf_hook, veh_hook,
                 panel_monitor, arena_bridge, reconciler, scheduler, logger):
        self._session = session
        self._hook_registry = hook_registry
        self._bf_hook = bf_hook
        self._veh_hook = veh_hook
        self._panel_monitor = panel_monitor
        self._arena_bridge = arena_bridge
        self._reconciler = reconciler
        self._scheduler = scheduler
        self._logger = logger
        self._started = False

    def init(self):
        if self._started:
            return
        self._started = True
        try:
            self._bf_hook.install()
            self._veh_hook.install()
            self._panel_monitor.install()
            self._bind_global_events(True)
            self._logger.info('%s %s initialized' % (MOD_ID, MOD_VERSION))
            if isPlayerAvatar is not None and isPlayerAvatar():
                self.on_avatar_ready()
        except Exception:
            self._logger.error('%s init failed' % MOD_ID)

    def fini(self):
        if not self._started:
            return
        self._started = False
        try:
            self._bind_global_events(False)
            self.on_battle_end()
            self._bf_hook.uninstall()
            self._veh_hook.uninstall()
            self._hook_registry.restore_all()
            self._scheduler.cancel_all()
            self._logger.info('%s finalized' % MOD_ID)
        except Exception:
            self._logger.error('%s fini failed' % MOD_ID)

    def on_avatar_ready(self, *_args):
        if isPlayerAvatar is not None and not isPlayerAvatar():
            return
        try:
            cfg = self._session.reload_config()
            if hasattr(self._logger, 'set_debug'):
                self._logger.set_debug(bool(cfg.get('debugLog', False)))
            self._panel_monitor.set_hide_in_killcam(bool(cfg.get('hideInKillcam', True)))
            self._panel_monitor.reset_battle_flags()
            self._panel_monitor.bind_events()
            self._arena_bridge.bind_arena(self._session)
            self._session.start_battle()
            interval = float(cfg.get('reconcileIntervalSec', 0.5))
            self._reconciler.start(interval_sec=interval)
            self._logger.debug('Battle session started (mode=%s)' % self._panel_monitor.get_mode())
        except Exception:
            self._logger.error('on_avatar_ready failed')

    def on_battle_end(self, *_args):
        try:
            self._reconciler.stop()
            self._panel_monitor.unbind_events()
            self._panel_monitor.clear_battle_state()
            self._arena_bridge.unbind_arena()
            self._session.end_battle()
        except Exception:
            self._logger.error('on_battle_end failed')

    def on_warp_start(self, *_args):
        self.on_battle_end()

    def on_warp_finish(self, *_args):
        if isPlayerAvatar is None or isPlayerAvatar():
            self.on_avatar_ready()

    def _bind_global_events(self, bind):
        if g_playerEvents is not None:
            for ev_name, handler in (
                ('onAvatarReady', self.on_avatar_ready),
                ('onAvatarBecomeNonPlayer', self.on_battle_end),
                ('onPlayerEntityChanging', self.on_battle_end),
            ):
                if hasattr(g_playerEvents, ev_name):
                    ev = getattr(g_playerEvents, ev_name)
                    if bind:
                        ev += handler
                    else:
                        ev -= handler
        if g_replayEvents is not None:
            for ev_name, handler in (
                ('onTimeWarpStart', self.on_warp_start),
                ('onTimeWarpFinish', self.on_warp_finish),
            ):
                if hasattr(g_replayEvents, ev_name):
                    ev = getattr(g_replayEvents, ev_name)
                    if bind:
                        ev += handler
                    else:
                        ev -= handler
