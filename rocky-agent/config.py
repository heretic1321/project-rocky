"""Load rocky-agent configuration."""

from pathlib import Path
import yaml

_CFG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    with open(_CFG_PATH) as f:
        return yaml.safe_load(f)
