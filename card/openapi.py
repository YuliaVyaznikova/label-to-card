import json

import yaml

from .api import app
from .config import ROOT


def main():
    schema = app.openapi()
    (ROOT / "openapi.json").write_text(json.dumps(schema, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "openapi.yaml").write_text(yaml.safe_dump(schema, allow_unicode=True, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()