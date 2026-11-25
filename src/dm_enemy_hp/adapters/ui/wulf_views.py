# -*- coding: utf-8 -*-
from __future__ import absolute_import

import traceback

try:
    from frameworks.wulf import (
        ViewFlags,
        ViewModel,
        ViewSettings,
        WindowFlags,
        WindowLayer,
        WindowStatus,
    )
    from gui.impl.gui_decorators import args2params
    from gui.impl.pub import ViewImpl, WindowImpl
    from gui.impl.gen import R
    from helpers import dependency
    from skeletons.gui.impl import IGuiLoader

    GF_LAYOUT = R.mods.dm.enemy_hp.views.EnemyHpOverlay
    GF_OK = True
    GF_ERR = None
    COVERING_LAYERS = (WindowLayer.FULLSCREEN_WINDOW, WindowLayer.TOP_WINDOW, WindowLayer.OVERLAY)
    GONE_WINDOW_STATUSES = (WindowStatus.DESTROYING, WindowStatus.DESTROYED)
except Exception:
    GF_LAYOUT = None
    GF_OK = False
    GF_ERR = traceback.format_exc()
    COVERING_LAYERS = ()
    GONE_WINDOW_STATUSES = ()
    ViewFlags = ViewModel = ViewSettings = WindowFlags = WindowLayer = WindowStatus = None
    IGuiLoader = dependency = None
    ViewImpl = object
    WindowImpl = object

    def args2params(*_args):
        return lambda fn: fn


def window_alive(window):
    try:
        return (
            window is not None
            and window.proxy is not None
            and window.windowStatus not in GONE_WINDOW_STATUSES
        )
    except Exception:
        return False


def get_main_window():
    if not GF_OK or dependency is None or IGuiLoader is None:
        return None
    return dependency.instance(IGuiLoader).windowsManager.getMainWindow()


if GF_OK:
    class EnemyHpModel(ViewModel):

        def __init__(self, payload):
            self.__payload = payload
            super(EnemyHpModel, self).__init__(properties=1, commands=1)

        def _initialize(self):
            super(EnemyHpModel, self)._initialize()
            self._addStringProperty('payload', self.__payload)
            self.onReady = self._addCommand('onReady')

        def setPayload(self, value):
            self._setString(0, value)

    class EnemyHpView(ViewImpl):

        def __init__(self, owner):
            self.__owner = owner
            model = EnemyHpModel(owner.payload)
            owner.model = model
            settings = ViewSettings(layoutID=GF_LAYOUT(), flags=ViewFlags.VIEW, model=model)
            super(EnemyHpView, self).__init__(settings)

        def _getEvents(self):
            model = self.getViewModel()
            return ((model.onReady, self.__onReady),)

        @args2params(str)
        def __onReady(self, message):
            self.__owner.on_js_ready(message)

        def _finalize(self):
            self.__owner.model = None
            super(EnemyHpView, self)._finalize()

    class EnemyHpWindow(WindowImpl):

        def __init__(self, content, parent, owner=None):
            self.__owner = owner
            super(EnemyHpWindow, self).__init__(
                WindowFlags.WINDOW,
                content=content,
                layer=WindowLayer.WINDOW,
                name='DmEnemyHpOverlay',
                parent=parent,
            )

        def _onReady(self):
            if self.__owner is not None:
                self.__owner.on_window_ready()
            else:
                self.show(False)
else:
    EnemyHpModel = None
    EnemyHpView = None
    EnemyHpWindow = None
