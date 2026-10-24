import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from card.config import ROOT, category_fields
from card.extract import baseline, extract
from card.normalize import numbers, parse
from card.pipeline import Pipeline
from card.verify import verify

from .metrics import ABLATED, by_field, front_mentions, summarize

OUT = ROOT / "data" / "eval"


def load_items(name, limit):
    if name == "off":
        rows = json.loads((ROOT / "data" / "off" / "manifest.json").read_text(encoding="utf-8"))
        items = []
        for row in rows:
            folder = ROOT / "data" / "off" / "images" / row["code"]
            photos = [folder / f"{photo['imgid']}.jpg" for photo in row["photos"]]
            if all(path.exists() for path in photos):
                items.append({**row, "photos": photos, "hints": {}})
        return items[:limit]
    folder = ROOT / "data" / name
    rows = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    return [{**row, "photos": [folder / path for path in row["photos"]], "hints": row.get("hints", {})} for row in rows][:limit]


def lenient(kind, name, value):
    if value in (None, "", "null"):
        return None
    parsed = parse(kind, name, str(value))
    found = numbers(str(value))
    if parsed is None and kind in ("energy", "number", "percent") and len(found) == 1:
        return {"value": found[0]}
    return parsed


def predict(pipeline, method, photos, spec, hints, lines, model):
    max_pixels = pipeline.config["vlm"]["max_pixels"]
    if method == "baseline":
        values, call = baseline(pipeline.vlm, photos, spec, max_pixels, model)
        return {name: lenient(spec[name]["kind"], name, value) for name, value in values.items()}, call, []
    proposals, call = extract(pipeline.vlm, photos, lines, spec, hints, max_pixels, model)
    if method == "nocheck":
        predicted = {}
        for name in spec:
            proposal = proposals.get(name) or {}
            raw = proposal.get("raw")
            predicted[name] = parse(spec[name]["kind"], name, raw) if raw and proposal.get("source") != "none" else None
        return predicted, call, []
    fields, log, _ = verify(spec, proposals, lines, hints, pipeline.config["verify"])
    return {name: field["value"] if field["source"] in ("photo", "farmer") else None for name, field in fields.items()}, call, log


def visibility(variant, mentions):
    if variant == "full":
        return {}
    return {name: mentions["composition"] if name == "composition" else mentions["nutrition"] for name in ABLATED}


def run_item(pipeline, spec, methods, model, item, variant, lines, visible):
    photos = item["photos"] if variant == "full" else item["photos"][:1]
    rows = []
    for method in methods:
        try:
            predicted, call, log = predict(pipeline, method, photos, spec, item["hints"], lines, model)
        except Exception as error:
            print(f"{item['id']} {variant} {method}: {error}", flush=True)
            continue
        rows.append({
            "id": item["id"], "model": model, "variant": variant, "method": method, "category": item.get("category"),
            "fields": {name: {"predicted": predicted.get(name), "truth": item["truth"].get(name), "visible": visible.get(name, True)} for name in spec},
            "usage": call["usage"], "seconds": call["seconds"], "log": log,
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default="off")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--models", default="")
    parser.add_argument("--variants", default="full,front_only")
    parser.add_argument("--methods", default="baseline,nocheck,pipeline")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--name", default="run")
    args = parser.parse_args()
    pipeline = Pipeline()
    models = [model for model in args.models.split(",") if model] or [pipeline.config["vlm"]["model"]]
    methods = args.methods.split(",")
    spec = category_fields(pipeline.categories, "other")
    items = load_items(args.set, args.limit)
    jobs = []
    for item in items:
        for variant in args.variants.split(","):
            lines = pipeline.read(item["photos"] if variant == "full" else item["photos"][:1])
            jobs.append((item, variant, lines, visibility(variant, front_mentions(lines))))
    print(f"ocr ready for {len(items)} items", flush=True)
    folder = OUT / args.name
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(folder / "predictions.jsonl", "w", encoding="utf-8") as out, ThreadPoolExecutor(args.workers) as pool:
        for model in models:
            futures = [pool.submit(run_item, pipeline, spec, methods, model, *job) for job in jobs]
            for number, future in enumerate(futures, 1):
                for row in future.result():
                    rows.append(row)
                    out.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                if number % 10 == 0 or number == len(futures):
                    print(f"{model}: {number}/{len(futures)}", flush=True)
    summary = pd.DataFrame(summarize(rows))
    summary.to_csv(folder / "metrics.csv", index=False)
    pd.DataFrame(by_field(rows)).to_csv(folder / "fields.csv", index=False)
    usage = pd.DataFrame([{"model": row["model"], "method": row["method"], **{key: row["usage"].get(key, 0) for key in ("prompt_tokens", "completion_tokens")}, "seconds": row["seconds"]} for row in rows])
    usage.groupby(["model", "method"]).agg(["sum", "median"]).round(1).to_csv(folder / "usage.csv")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()