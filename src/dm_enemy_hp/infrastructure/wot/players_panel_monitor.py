# -*- coding: utf-8 -*-
from __future__ import absolute_import

try:
    import BigWorld
except Exception:
    BigWorld = None

try:
    import Keys
except Exception:
    Keys = None

try:
    from gui.shared import g_eventBus, events, EVENT_BUS_SCOPE
except Exception:
    g_eventBus = events = EVENT_BUS_SCOPE = None

try:
    from gui.Scaleform.genConsts.PLAYERS_PANEL_STATE import PLAYERS_PANEL_STATE
except Exception:
    PLAYERS_PANEL_STATE = None

try:
    from gui.Scaleform.genConsts.BATTLE_VIEW_ALIASES import BATTLE_VIEW_ALIASES
except Exception:
    BATTLE_VIEW_ALIASES = None

try:
    from gui.Scaleform.daapi.view.meta.PlayersPanelMeta import PlayersPanelMeta
except Exception:
    PlayersPanelMeta = None

try:
    from gui.Scaleform.daapi.view.meta.BattlePageMeta import BattlePageMeta
except Exception:
    BattlePageMeta = None

try:
    from gui.Scaleform.daapi.view.battle.shared.page import SharedPage
except Exception:
    SharedPage = None

_DEFAULT_STATE_MAP = {
    -1: 'short',
    0: 'hidden',
    1: 'short',
    2: 'medium',
    3: 'medium2',
    4: 'large',
    5: 'medium',
    6: 'large',
    7: 'medium',
    8: 'medium2',
    9: 'hidden',
    10: 'short',
    11: 'medium',
    12: 'medium2',
    13: 'short',
    14: 'medium',
    15: 'medium2',
    16: 'short',
    17: 'medium',
    18: 'medium2',
    19: 'hidden',
    20: 'short',
    21: 'medium2',
}


def normalize_panel_state(state_val):
    if isinstance(state_val, basestring):
        low = state_val.strip().lower()
        if low in ('hidden', 'short', 'medium', 'medium2', 'large'):
            return low
    try:
        iv = int(state_val)
    except (TypeError, ValueError):
        return 'short'

    if PLAYERS_PANEL_STATE is not None:
        if iv in (
            getattr(PLAYERS_PANEL_STATE, 'HIDDEN', 0),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_THREE_COLUMN_HIDDEN', 9),
        ):
            return 'hidden'
        if iv in (
            getattr(PLAYERS_PANEL_STATE, 'SHORT', 1),
            getattr(PLAYERS_PANEL_STATE, 'SHORT_NO_BADGES', 20),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_THREE_COLUMN_SHORT', 10),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_THREE_COLUMN_SHORT_SECOND_FOCUS', 13),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_THREE_COLUMN_SHORT_THIRD_FOCUS', 16),
        ):
            return 'short'
        if iv in (
            getattr(PLAYERS_PANEL_STATE, 'MEDIUM', 2),
            getattr(PLAYERS_PANEL_STATE, 'MEDIUM_NO_BADGES', 5),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_SINGLE_COLUMN_MEDIUM_PLAYER', 7),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_THREE_COLUMN_MEDIUM_PLAYER', 11),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_THREE_COLUMN_MEDIUM_PLAYER_SECOND_FOCUS', 14),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_THREE_COLUMN_MEDIUM_PLAYER_THIRD_FOCUS', 17),
        ):
            return 'medium'
        if iv in (
            getattr(PLAYERS_PANEL_STATE, 'LONG', 3),
            getattr(PLAYERS_PANEL_STATE, 'LONG_NO_BADGES', 21),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_SINGLE_COLUMN_MEDIUM_TANK', 8),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_THREE_COLUMN_MEDIUM_TANK', 12),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_THREE_COLUMN_MEDIUM_TANK_SECOND_FOCUS', 15),
            getattr(PLAYERS_PANEL_STATE, 'EPIC_RANDOM_THREE_COLUMN_MEDIUM_TANK_THIRD_FOCUS', 18),
        ):
            return 'medium2'
        if iv in (
            getattr(PLAYERS_PANEL_STATE, 'FULL', 4),
            getattr(PLAYERS_PANEL_STATE, 'FULL_NO_BADGES', 6),
        ):
            return 'large'

    return _DEFAULT_STATE_MAP.get(iv, 'short')


class WotPlayersPanelMonitor(object):
    """Tracks right PlayersPanel mode, V HUD visibility, Tab scoreboard, Esc overlays, and Killcam."""

    def __init__(self, registry, panel_view, logger):
        self._registry = registry
        self._panel_view = panel_view
        self._logger = logger
        self._session = None
        self._mode = 'short'
        self._active_panel = None
        self._panel_present = False
        self._mode_from_panel = False
        self._battle_page = None
        self._component_visible = True
        self._hud_hidden = False
        self._full_stats = False
        self._hide_in_killcam = True
        self._hooks_installed = False
        self._events_bound = False

    def set_session(self, session):
        self._session = session

    def set_hide_in_killcam(self, enabled):
        self._hide_in_killcam = bool(enabled)

    def clear_battle_state(self):
        self._active_panel = None
        self._panel_present = False
        self._mode_from_panel = False
        self._battle_page = None
        self._component_visible = True
        self._hud_hidden = False
        self._full_stats = False

    def reset_battle_flags(self):
        self._hud_hidden = False
        self._full_stats = False
        self._component_visible = True
        if not self._panel_present:
            self._probe_live_players_panel()
        live_mode = getattr(self._active_panel, '_mode', None) if self._active_panel is not None else None
        if live_mode is not None:
            self._mode = normalize_panel_state(live_mode)
        elif not self._mode_from_panel:
            if self._is_prebattle_period():
                self._mode = 'large'
            else:
                self._read_initial_mode()

    def _probe_live_players_panel(self):
        try:
            from frameworks.wulf import WindowLayer
            from helpers import dependency
            from skeletons.gui.app_loader import IAppLoader
            app = dependency.instance(IAppLoader).getDefBattleApp()
            cm = getattr(app, 'containerManager', None) if app is not None else None
            page = cm.getView(WindowLayer.VIEW) if cm is not None else None
            if page is None:
                return False
            self._battle_page = page
            alias = getattr(BATTLE_VIEW_ALIASES, 'PLAYERS_PANEL', 'playersPanel') if BATTLE_VIEW_ALIASES is not None else 'playersPanel'
            comp = page.getComponent(alias) if hasattr(page, 'getComponent') else None
            if comp is not None and (PlayersPanelMeta is None or isinstance(comp, PlayersPanelMeta)):
                self._active_panel = comp
                self._panel_present = True
                live_mode = getattr(comp, '_mode', None)
                if live_mode is not None:
                    self._mode = normalize_panel_state(live_mode)
                    self._mode_from_panel = True
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _is_prebattle_period():
        if BigWorld is None:
            return False
        try:
            player = BigWorld.player()
            arena = getattr(player, 'arena', None) if player is not None else None
            return getattr(arena, 'period', None) in (1, 2)
        except Exception:
            return False

    def _read_initial_mode(self):
        try:
            from gui.Scaleform.daapi.view.battle.classic.players_panel import PlayerPanelStateSetting
            state = PlayerPanelStateSetting.read()
            self._mode = normalize_panel_state(state)
        except Exception:
            pass

    def install(self):
        if self._hooks_installed:
            return
        if PlayersPanelMeta is not None:
            self._hook_panel_meta(PlayersPanelMeta)
        try:
            from gui.Scaleform.daapi.view.battle.classic.players_panel import PlayersPanel
            self._hook_panel_cls(PlayersPanel, '_PlayersPanel__setMode')
        except Exception:
            self._logger.error('Failed to hook classic PlayersPanel')

        try:
            from gui.Scaleform.daapi.view.battle.epic_random.players_panel import EpicRandomPlayersPanel
            self._hook_panel_cls(EpicRandomPlayersPanel, '_EpicRandomPlayersPanel__setMode')
        except Exception:
            pass

        if BattlePageMeta is not None:
            self._hook_battle_page_meta(BattlePageMeta)
        if SharedPage is not None:
            self._hook_shared_page_dispose(SharedPage)
        self._hooks_installed = True

    def _hook_panel_meta(self, meta_cls):
        monitor = self

        def wrap_as_mode(orig):
            def _wrapped(panel_self, mode, *args, **kwargs):
                result = orig(panel_self, mode, *args, **kwargs)
                was_present = monitor._panel_present
                monitor._active_panel = panel_self
                monitor._panel_present = True
                monitor._mode_from_panel = True
                monitor._on_raw_mode(mode)
                if not was_present and monitor._session is not None:
                    monitor._session.on_visibility_changed(True)
                return result
            return _wrapped

        self._registry.hook(meta_cls, 'as_setPanelModeS', wrap_as_mode)

    def _hook_battle_page_meta(self, page_meta_cls):
        monitor = self
        alias = getattr(BATTLE_VIEW_ALIASES, 'PLAYERS_PANEL', 'playersPanel') if BATTLE_VIEW_ALIASES is not None else 'playersPanel'

        def _update_comp_visibility(page_self, visible, hidden):
            monitor._battle_page = page_self
            if hidden and alias in hidden:
                if monitor._component_visible:
                    monitor._component_visible = False
                    if monitor._session is not None:
                        monitor._session.on_visibility_changed(False)
            elif visible and alias in visible:
                if not monitor._component_visible:
                    monitor._component_visible = True
                    if monitor._session is not None:
                        monitor._session.on_visibility_changed(True)

        def wrap_set_vis(orig):
            def _wrapped(page_self, visible=(), hidden=(), *args, **kwargs):
                result = orig(page_self, visible, hidden, *args, **kwargs)
                _update_comp_visibility(page_self, visible, hidden)
                return result
            return _wrapped

        self._registry.hook(page_meta_cls, 'as_setComponentsVisibilityS', wrap_set_vis)
        self._registry.hook(page_meta_cls, 'as_setComponentsVisibilityWithFadeS', wrap_set_vis)

    def _hook_shared_page_dispose(self, shared_page_cls):
        monitor = self

        def wrap_page_dispose(orig):
            def _wrapped(page_self, *args, **kwargs):
                if page_self is monitor._battle_page:
                    monitor._battle_page = None
                return orig(page_self, *args, **kwargs)
            return _wrapped

        self._registry.hook(shared_page_cls, '_dispose', wrap_page_dispose)

    def _hook_panel_cls(self, panel_cls, priv_attr):
        monitor = self

        def wrap_populate(orig):
            def _wrapped(panel_self, *args, **kwargs):
                result = orig(panel_self, *args, **kwargs)
                was_present = monitor._panel_present
                monitor._active_panel = panel_self
                monitor._panel_present = True
                live_mode = getattr(panel_self, '_mode', None)
                if live_mode is not None:
                    monitor._mode_from_panel = True
                    monitor._on_raw_mode(live_mode)
                if not was_present and monitor._session is not None:
                    monitor._session.on_visibility_changed(True)
                return result
            return _wrapped

        def wrap_mode(orig):
            def _wrapped(panel_self, mode, *args, **kwargs):
                result = orig(panel_self, mode, *args, **kwargs)
                was_present = monitor._panel_present
                monitor._active_panel = panel_self
                monitor._panel_present = True
                monitor._mode_from_panel = True
                monitor._on_raw_mode(mode)
                if not was_present and monitor._session is not None:
                    monitor._session.on_visibility_changed(True)
                return result
            return _wrapped

        def wrap_dispose(orig):
            def _wrapped(panel_self, *args, **kwargs):
                if panel_self is monitor._active_panel:
                    monitor._active_panel = None
                    monitor._panel_present = False
                    if monitor._session is not None:
                        monitor._session.on_visibility_changed(False)
                return orig(panel_self, *args, **kwargs)
            return _wrapped

        self._registry.hook(panel_cls, '_populate', wrap_populate)
        if not self._registry.hook(panel_cls, priv_attr, wrap_mode):
            self._registry.hook(panel_cls, 'as_setPanelModeS', wrap_mode)
        self._registry.hook(panel_cls, '_dispose', wrap_dispose)

    def bind_events(self):
        if self._events_bound or g_eventBus is None or events is None or EVENT_BUS_SCOPE is None:
            return
        try:
            ge = events.GameEvent
            scope = EVENT_BUS_SCOPE.BATTLE
            gui_vis = getattr(ge, 'GUI_VISIBILITY', None)
            if gui_vis is not None:
                g_eventBus.addListener(gui_vis, self._on_gui_visibility, scope=scope)
            full_stats = getattr(ge, 'FULL_STATS', None) or getattr(ge, 'SHOW_FULL_STATS', None)
            if full_stats is not None:
                g_eventBus.addListener(full_stats, self._on_full_stats, scope=scope)
            self._events_bound = True
        except Exception:
            self._logger.error('Failed to bind battle visibility events')

    def unbind_events(self):
        if not self._events_bound or g_eventBus is None or events is None or EVENT_BUS_SCOPE is None:
            return
        try:
            ge = events.GameEvent
            scope = EVENT_BUS_SCOPE.BATTLE
            gui_vis = getattr(ge, 'GUI_VISIBILITY', None)
            if gui_vis is not None:
                g_eventBus.removeListener(gui_vis, self._on_gui_visibility, scope=scope)
            full_stats = getattr(ge, 'FULL_STATS', None) or getattr(ge, 'SHOW_FULL_STATS', None)
            if full_stats is not None:
                g_eventBus.removeListener(full_stats, self._on_full_stats, scope=scope)
        except Exception:
            pass
        self._events_bound = False

    def _on_raw_mode(self, raw_mode):
        new_mode = normalize_panel_state(raw_mode)
        if new_mode != self._mode:
            self._mode = new_mode
            if self._session is not None:
                self._session.on_panel_mode_changed(new_mode)

    def _on_gui_visibility(self, event):
        ctx = getattr(event, 'ctx', None) or {}
        if 'visible' in ctx:
            self._hud_hidden = not bool(ctx['visible'])
            if self._session is not None:
                self._session.on_visibility_changed(not self._hud_hidden)

    def _on_full_stats(self, event):
        ctx = getattr(event, 'ctx', None) or {}
        if 'isDown' in ctx:
            self._full_stats = bool(ctx['isDown'])
            if self._session is not None:
                self._session.on_visibility_changed(not self._full_stats)

    def get_mode(self):
        if self._active_panel is not None:
            live = getattr(self._active_panel, '_mode', None)
            if live is not None:
                self._mode = normalize_panel_state(live)
        return self._mode

    @staticmethod
    def _is_tab_down():
        if BigWorld is None or Keys is None:
            return False
        try:
            key = getattr(Keys, 'KEY_TAB', None)
            return bool(key is not None and BigWorld.isKeyDown(key))
        except Exception:
            return False

    @staticmethod
    def _is_killcam_active():
        if BigWorld is None:
            return False
        try:
            player = BigWorld.player()
            handler = getattr(player, 'inputHandler', None) if player is not None else None
            name = str(getattr(handler, 'ctrlModeName', '') or '').replace('_', '').lower()
            if not name:
                return False
            return ('kill' in name) or ('death' in name and name != 'deathfreecam')
        except Exception:
            return False

    def is_hud_visible(self):
        if not self._panel_present:
            self._probe_live_players_panel()
            if not self._panel_present:
                return False
        if not self._component_visible:
            return False
        if self._battle_page is not None and hasattr(self._battle_page, 'as_isComponentVisibleS'):
            try:
                alias = getattr(BATTLE_VIEW_ALIASES, 'PLAYERS_PANEL', 'playersPanel') if BATTLE_VIEW_ALIASES is not None else 'playersPanel'
                if self._battle_page.as_isComponentVisibleS(alias) is False:
                    return False
            except Exception:
                pass
        if self._mode == 'hidden' or self._hud_hidden or self._full_stats or self._is_tab_down():
            return False
        if self._hide_in_killcam and self._is_killcam_active():
            return False
        if self._panel_view is not None and hasattr(self._panel_view, 'is_covered') and self._panel_view.is_covered():
            return False
        return True
