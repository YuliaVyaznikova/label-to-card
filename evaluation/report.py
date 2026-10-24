import argparse
import json
import random

import numpy as np
import pandas as pd

from .metrics import summarize
from .run import OUT

METRICS = ["precision", "recall", "invented_share"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="full")
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    folder = OUT / args.name
    rows = [json.loads(line) for line in open(folder / "predictions.jsonl", encoding="utf-8")]
    by_item = {}
    for row in rows:
        by_item.setdefault(row["id"], []).append(row)
    items = sorted(by_item)
    rng = random.Random(args.seed)
    draws = {}
    for _ in range(args.samples):
        sample = [rng.choice(items) for _ in items]
        for entry in summarize([row for item in sample for row in by_item[item]]):
            for metric in METRICS:
                if entry[metric] is not None:
                    draws.setdefault((entry["model"], entry["variant"], entry["method"], metric), []).append(entry[metric])
    table = []
    for entry in summarize(rows):
        for metric in METRICS:
            values = draws.get((entry["model"], entry["variant"], entry["method"], metric))
            if entry[metric] is None or not values:
                continue
            low, high = np.percentile(values, [2.5, 97.5])
            table.append({"model": entry["model"], "variant": entry["variant"], "method": entry["method"], "metric": metric,
                          "value": entry[metric], "low": round(low, 3), "high": round(high, 3), "items": entry["items"]})
    report = pd.DataFrame(table)
    report.to_csv(folder / "report.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(report.to_string(index=False))


if __name__ == "__main__":
    main()