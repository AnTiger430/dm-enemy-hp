# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IEnemyHpPresenter(object):
    """Port converting ordered enemy entities + layout state into UI payload dict."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def build_payload(self, enemies, cfg, screen_w, screen_h, ui_scale, panel_mode, visible):
        raise NotImplementedError
