# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IConfigRepository(object):
    """Port for reading and persisting validated mod configuration."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def load(self):
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, data):
        raise NotImplementedError
