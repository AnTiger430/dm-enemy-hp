# -*- coding: utf-8 -*-
from __future__ import absolute_import

import codecs
import os
import time
import traceback

from ...application.ports.logger import ILogger

try:
    from debug_utils import LOG_ERROR, LOG_NOTE
except Exception:
    LOG_ERROR = None
    LOG_NOTE = None


class ModFileLogger(ILogger):
    """Best-effort UTF-8 file logger under mods/configs/dm_enemy_hp/enemy_hp.log."""

    def __init__(self, path=None, debug_enabled=False, max_bytes=524288):
        self._path = path or os.path.join('mods', 'configs', 'dm_enemy_hp', 'enemy_hp.log')
        self._debug_enabled = bool(debug_enabled)
        self._max_bytes = int(max_bytes)

    def set_debug(self, enabled):
        self._debug_enabled = bool(enabled)

    def info(self, msg):
        self._write('INFO', msg)
        if LOG_NOTE is not None:
            try:
                LOG_NOTE('[dm.enemy_hp] %s' % msg)
            except Exception:
                pass

    def debug(self, msg):
        if self._debug_enabled:
            self._write('DEBUG', msg)

    def error(self, msg):
        tb = traceback.format_exc()
        if tb and tb.strip() != 'None':
            full_msg = '%s\n%s' % (msg, tb.rstrip())
        else:
            full_msg = msg
        self._write('ERROR', full_msg)
        if LOG_ERROR is not None:
            try:
                LOG_ERROR('[dm.enemy_hp] %s' % full_msg)
            except Exception:
                pass

    def _write(self, level, msg):
        try:
            parent = os.path.dirname(self._path)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent)
            if os.path.isfile(self._path) and os.path.getsize(self._path) > self._max_bytes:
                try:
                    os.remove(self._path)
                except Exception:
                    pass
            stamp = time.strftime('%Y-%m-%d %H:%M:%S')
            text_msg = msg if isinstance(msg, unicode) else str(msg).decode('utf-8', 'replace')
            line = u'[%s] [%s] %s\n' % (stamp, level, text_msg)
            with codecs.open(self._path, 'a', 'utf-8') as f:
                f.write(line)
        except Exception:
            pass
