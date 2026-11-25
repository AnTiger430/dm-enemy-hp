# -*- coding: utf-8 -*-
from __future__ import absolute_import

import codecs
import json
import os
import shutil

from ...application.ports.config_repository import IConfigRepository


class JsonConfigRepository(IConfigRepository):
    """Atomic JSON configuration store under mods/configs/dm_enemy_hp/config.json."""

    def __init__(self, path=None, logger=None):
        self._path = path or os.path.join('mods', 'configs', 'dm_enemy_hp', 'config.json')
        self._logger = logger

    @property
    def path(self):
        return self._path

    def load(self):
        if not os.path.isfile(self._path):
            return {}
        try:
            with codecs.open(self._path, 'r', 'utf-8') as f:
                raw = json.load(f)
            return raw if isinstance(raw, dict) else {}
        except Exception:
            if self._logger is not None:
                self._logger.error('Failed to read config JSON at %s, using defaults' % self._path)
            return {}

    def save(self, data):
        parent = os.path.dirname(self._path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        tmp_path = self._path + '.tmp'
        text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        with codecs.open(tmp_path, 'w', 'utf-8') as f:
            f.write(text)
        if hasattr(os, 'replace'):
            os.replace(tmp_path, self._path)
        elif os.path.exists(self._path):
            shutil.move(tmp_path, self._path)
        else:
            os.rename(tmp_path, self._path)
