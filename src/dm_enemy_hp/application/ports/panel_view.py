# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IEnemyPanelView(object):
    """Port driving the enemy HP overlay window."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def build(self):
        raise NotImplementedError

    @abc.abstractmethod
    def push_state(self, payload):
        raise NotImplementedError

    @abc.abstractmethod
    def set_visible(self, visible):
        raise NotImplementedError

    @abc.abstractmethod
    def destroy(self):
        raise NotImplementedError
