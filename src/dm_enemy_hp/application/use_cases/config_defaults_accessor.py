# -*- coding: utf-8 -*-
from __future__ import absolute_import


def load_validated_config(config_repo, validator):
    """Load config from repository and persist defaults/migrations if needed."""
    raw = config_repo.load()
    normalized = validator.normalize(raw)
    if not isinstance(raw, dict) or not raw or raw.get('configVersion') != normalized.get('configVersion'):
        try:
            config_repo.save(normalized)
        except Exception:
            pass
    return normalized
