from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@lru_cache
def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())
