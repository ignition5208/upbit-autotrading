import copy
from .safe import PRESET as SAFE
from .standard import PRESET as STANDARD
from .profit import PRESET as PROFIT
from .crazy import PRESET as CRAZY

PRESETS = {p["name"].upper(): p for p in [SAFE, STANDARD, PROFIT, CRAZY]}


def load_preset(name: str) -> dict:
    key = (name or "STANDARD").upper()
    if key not in PRESETS:
        raise ValueError(f"unknown preset: {name}")
    return copy.deepcopy(PRESETS[key])


def deep_merge(base: dict, override: dict | None) -> dict:
    if not override:
        return base
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base
