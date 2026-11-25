# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class ILogger(object):
    """Port for mod file/diagnostic logging."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def info(self, msg):
        raise NotImplementedError

    @abc.abstractmethod
    def debug(self, msg):
        raise NotImplementedError

    @abc.abstractmethod
    def error(self, msg):
        raise NotImplementedError
