# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...application.ports.scheduler import IScheduler

try:
    import BigWorld
except Exception:
    BigWorld = None


class WotScheduler(IScheduler):
    """BigWorld.callback / cancelCallback adapter implementing IScheduler."""

    def __init__(self):
        self._tokens = set()

    def schedule(self, delay_sec, callback):
        if BigWorld is None:
            return None
        try:
            token = BigWorld.callback(float(delay_sec), callback)
            if token is not None:
                self._tokens.add(token)
            return token
        except Exception:
            return None

    def cancel(self, token):
        if token is None:
            return
        self._tokens.discard(token)
        if BigWorld is not None:
            try:
                BigWorld.cancelCallback(token)
            except Exception:
                pass

    def cancel_all(self):
        for token in list(self._tokens):
            self.cancel(token)
        self._tokens.clear()


class WotReconcilerTimer(object):
    """Periodic 0.5s battle health reconciliation safety timer."""

    def __init__(self, scheduler, session, logger, interval_sec=0.5):
        self._scheduler = scheduler
        self._session = session
        self._logger = logger
        self._interval = max(0.2, float(interval_sec))
        self._running = False
        self._token = None

    def start(self, interval_sec=None):
        if interval_sec is not None:
            self._interval = max(0.2, float(interval_sec))
        self.stop()
        self._running = True
        self._token = self._scheduler.schedule(self._interval, self._on_tick)

    def stop(self):
        self._running = False
        if self._token is not None:
            self._scheduler.cancel(self._token)
            self._token = None

    def _on_tick(self):
        self._token = None
        if not self._running or not self._session.in_battle:
            return
        try:
            self._session.reconcile_tick()
        except Exception:
            self._logger.error('reconcile_tick failed')
        if self._running and self._session.in_battle:
            self._token = self._scheduler.schedule(self._interval, self._on_tick)
