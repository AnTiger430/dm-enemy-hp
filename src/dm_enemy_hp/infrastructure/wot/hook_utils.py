# -*- coding: utf-8 -*-
from __future__ import absolute_import


class MethodHookRegistry(object):
    """Installs reversible monkey-patches on classes/modules and restores them on fini()."""

    def __init__(self, logger=None):
        self._logger = logger
        self._hooks = []

    def hook(self, target, attr_name, wrapper_factory):
        for t, name, _raw, _orig, _rep in self._hooks:
            if t is target and name == attr_name:
                return False
        if not hasattr(target, attr_name):
            return False
        raw_orig = target.__dict__.get(attr_name) if hasattr(target, '__dict__') else None
        orig_callable = raw_orig if raw_orig is not None else getattr(target, attr_name)
        replacement = wrapper_factory(orig_callable)
        setattr(target, attr_name, replacement)
        self._hooks.append((target, attr_name, raw_orig, orig_callable, replacement))
        return True

    def restore_all(self):
        for target, attr_name, raw_orig, orig_callable, replacement in reversed(self._hooks):
            try:
                current = target.__dict__.get(attr_name) if hasattr(target, '__dict__') else getattr(target, attr_name, None)
                if current is replacement:
                    if raw_orig is not None or not hasattr(target, '__dict__'):
                        setattr(target, attr_name, raw_orig if raw_orig is not None else orig_callable)
                    else:
                        delattr(target, attr_name)
            except Exception:
                if self._logger is not None:
                    self._logger.error('Failed to restore hook %s.%s' % (target, attr_name))
        self._hooks = []
