# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json

from ...application.ports.panel_view import IEnemyPanelView
from .wulf_views import (
    EnemyHpView,
    EnemyHpWindow,
    GF_ERR,
    GF_OK,
    WindowStatus,
    get_main_window,
    window_alive,
)


class GamefaceEnemyPanelAdapter(IEnemyPanelView):
    """Non-interactive WULF/Gameface overlay adapter implementing IEnemyPanelView."""

    def __init__(self, scheduler, logger, visibility_guard=None):
        self._scheduler = scheduler
        self._logger = logger
        self._guard = visibility_guard

        self.model = None
        self.window = None
        self.payload = '{}'
        self._token = 0
        self._retry_token = None
        self._ready = False
        self._window_ready = False
        self._destroyed = False
        self._desired_visible = True
        self._actual_visible = None
        self._desired_pos = None
        self._last_pos = None

    @property
    def visibility_guard(self):
        return self._guard

    def build(self):
        self._destroyed = False
        if not GF_OK:
            if GF_ERR:
                self._logger.error('Gameface unavailable: %s' % GF_ERR)
            return
        if window_alive(self.window):
            return
        self._token += 1
        self._load(self._token, retry=0)

    def _load(self, token, retry=0):
        self._retry_token = None
        if token != self._token or self._destroyed:
            return
        parent = get_main_window()
        if parent is None or getattr(parent, 'proxy', None) is None or \
                getattr(parent, 'windowStatus', None) != WindowStatus.LOADED:
            if retry < 100:
                self._retry_token = self._scheduler.schedule(
                    0.1, lambda: self._load(token, retry + 1),
                )
            else:
                self._logger.error('Main window did not become ready for enemy HP overlay')
            return
        try:
            self.window = EnemyHpWindow(EnemyHpView(self), parent, owner=self)
            self.window.load()
        except Exception:
            self._logger.error('Failed to create EnemyHpWindow')

    def on_window_ready(self):
        self._window_ready = True
        self._move(force=True)
        self._apply_visibility(force=True)

    def on_js_ready(self, message=''):
        self._ready = True
        self._publish(force=True)
        self._move(force=True)
        self._apply_visibility(force=True)
        if self._logger is not None:
            self._logger.info('Overlay ready (%s, pos=%r)' % (message, self._last_pos))

    def push_state(self, payload):
        if self._destroyed:
            return
        if not isinstance(payload, dict):
            return
        x = payload.get('x')
        y = payload.get('y')
        if x is not None and y is not None:
            self._desired_pos = (int(x), int(y))
            self._move()
        raw = json.dumps(payload, ensure_ascii=True)
        if raw != self.payload:
            self.payload = raw
            self._publish()

    def set_visible(self, visible):
        self._desired_visible = bool(visible)
        self._apply_visibility()

    def is_covered(self):
        if self._guard is None:
            return False
        return bool(self._guard.is_covered(self.window))

    def _move(self, force=False):
        if self._desired_pos is None or not window_alive(self.window) or not self._ready:
            return
        if not force and self._last_pos == self._desired_pos:
            return
        try:
            self.window.move(self._desired_pos[0], self._desired_pos[1])
            self._last_pos = self._desired_pos
        except Exception:
            pass

    def _publish(self, force=False):
        if self.model is None or not (self._ready or force):
            return
        try:
            with self.model.transaction() as model:
                model.setPayload(self.payload)
        except Exception:
            pass

    def _apply_visibility(self, force=False):
        if not window_alive(self.window) or not self._window_ready or \
                getattr(self.window, 'windowStatus', None) != WindowStatus.LOADED:
            return
        want = bool(self._desired_visible) and not self.is_covered()
        if want and not self._ready:
            return
        if not force and want == self._actual_visible:
            return
        self._actual_visible = want
        try:
            if want:
                self.window.show(False)
            else:
                self.window.hide()
        except Exception:
            if not window_alive(self.window):
                self.window = None

    def destroy(self):
        self._destroyed = True
        self._token += 1
        if self._retry_token is not None:
            try:
                self._scheduler.cancel(self._retry_token)
            except Exception:
                pass
            self._retry_token = None
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
        self.model = None
        self._ready = False
        self._window_ready = False
        self._actual_visible = None
        self._desired_pos = None
        self._last_pos = None
        self.payload = '{}'
