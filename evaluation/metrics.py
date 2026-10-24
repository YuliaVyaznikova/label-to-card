import re

from rapidfuzz import fuzz

from card.normalize import QUANTITY, norm, quantity
from card.verify import token_coverage

ABLATED = ["composition", "energy_kcal", "proteins_g", "fats_g", "carbohydrates_g"]
NUMERIC = {"energy_kcal", "proteins_g", "fats_g", "carbohydrates_g"}


def correct(name, predicted, truth):
    if predicted is None or truth is None:
        return False
    value = predicted.get("value")
    if name in NUMERIC:
        return isinstance(value, (int, float)) and abs(value - float(truth)) <= max(0.15, 0.05 * abs(float(truth)))
    if name == "net_quantity":
        expected = [quantity(*match.groups()) for match in re.finditer(QUANTITY, str(truth).lower())]
        return any(predicted.get("unit") == item["unit"] and abs(value - item["value"]) <= 0.01 * item["value"] for item in expected)
    if name == "composition":
        return token_coverage(str(truth), str(value)) >= 0.8
    return fuzz.token_set_ratio(norm(str(value)), norm(str(truth))) >= 80


def front_mentions(lines):
    text = " ".join(norm(line["text"]) for line in lines.values() if line["photo"] == 1)
    return {"composition": "состав" in text, "nutrition": any(word in text for word in ("белк", "углевод", "ккал"))}


def summarize(rows):
    table = {}
    for row in rows:
        key = (row["model"], row["variant"], row["method"])
        stats = table.setdefault(key, {"filled": 0, "correct": 0, "with_truth": 0, "found": 0, "ablated": 0, "invented": 0, "items": 0})
        stats["items"] += 1
        for name, item in row["fields"].items():
            filled = item["predicted"] is not None
            if row["variant"] == "front_only" and name in ABLATED:
                if item["visible"]:
                    continue
                stats["ablated"] += 1
                stats["invented"] += filled
                continue
            if item["truth"] is None:
                continue
            stats["with_truth"] += 1
            stats["filled"] += filled
            good = correct(name, item["predicted"], item["truth"])
            stats["correct"] += good
            stats["found"] += good
    result = []
    for (model, variant, method), stats in table.items():
        result.append({
            "model": model, "variant": variant, "method": method, "items": stats["items"],
            "precision": round(stats["correct"] / stats["filled"], 3) if stats["filled"] else None,
            "recall": round(stats["found"] / stats["with_truth"], 3) if stats["with_truth"] else None,
            "filled": stats["filled"], "with_truth": stats["with_truth"],
            "invented": stats["invented"], "ablated": stats["ablated"],
            "invented_share": round(stats["invented"] / stats["ablated"], 3) if stats["ablated"] else None,
        })
    return result


def by_field(rows):
    table = {}
    for row in rows:
        for name, item in row["fields"].items():
            if item["truth"] is None or (row["variant"] == "front_only" and name in ABLATED):
                continue
            stats = table.setdefault((row["model"], row["variant"], row["method"], name), {"filled": 0, "correct": 0, "with_truth": 0})
            stats["with_truth"] += 1
            stats["filled"] += item["predicted"] is not None
            stats["correct"] += correct(name, item["predicted"], item["truth"])
    return [{
        "model": model, "variant": variant, "method": method, "field": name, "with_truth": stats["with_truth"], "filled": stats["filled"],
        "precision": round(stats["correct"] / stats["filled"], 3) if stats["filled"] else None,
        "recall": round(stats["correct"] / stats["with_truth"], 3),
    } for (model, variant, method, name), stats in table.items()]