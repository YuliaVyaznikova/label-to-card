import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def read_env(path=ROOT / ".env"):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def load_config(path=ROOT / "config.yaml"):
    read_env()
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for key, value in config["paths"].items():
        config["paths"][key] = ROOT / value
    config["vlm"]["api_key"] = os.environ.get("POLZA_API_KEY", "")
    config["vlm"]["model"] = os.environ.get("VLM_MODEL", config["vlm"]["model"])
    return config


def load_categories(path=ROOT / "categories.yaml"):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def category_fields(categories, category):
    return {
        name: spec for name, spec in categories["fields"].items()
        if "categories" not in spec or category in spec["categories"]
    }