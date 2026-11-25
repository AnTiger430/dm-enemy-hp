# -*- coding: utf-8 -*-
from __future__ import absolute_import

try:
    from gui.mods.dm_enemy_hp.bootstrap.container import build_application
except ImportError:
    from dm_enemy_hp.bootstrap.container import build_application

_app = None


def init():
    global _app
    if _app is None:
        _app = build_application()
    _app.init()


def fini():
    global _app
    if _app is not None:
        _app.fini()
        _app = None
