from statistics import mean

from rapidfuzz import fuzz

from .normalize import beside, norm, parse, parse_quantity, present, tokens

NUMERIC = {"quantity", "duration", "energy", "number", "percent"}
SKELETON = str.maketrans({"a": "а", "b": "ь", "c": "с", "d": "д", "e": "е", "h": "н", "k": "к", "m": "т", "n": "п", "o": "о",
                          "p": "р", "r": "г", "t": "т", "u": "и", "x": "х", "y": "у"})


def skeleton(text):
    return norm(text).translate(SKELETON)


def token_coverage(raw, text):
    words = [word.translate(SKELETON) for word in tokens(raw)]
    have = [word.translate(SKELETON) for word in tokens(text)]
    if not words or not have:
        return 0.0
    found = sum(any(word == other or (len(word) > 3 and fuzz.ratio(word, other) >= 85) for other in have) for word in words)
    return found / len(words)


def similarity(raw, text, settings):
    a, b = skeleton(raw), skeleton(text)
    if not a or not b:
        return 0.0
    if len(a) > settings["long_text"]:
        return token_coverage(raw, text)
    if len(b) < len(a):
        return fuzz.ratio(a, b) / 100
    return fuzz.partial_ratio(a, b) / 100


def passes(raw, score, settings, ratio=None):
    if len(norm(raw)) > settings["long_text"]:
        return score >= settings["coverage"]
    return score >= (ratio or settings["text_ratio"]) / 100


def photo_text(lines, ids):
    return " ".join(lines[i]["text"] for i in ids)


def windows(ids, size):
    for start in range(len(ids)):
        for length in range(1, size + 1):
            if start + length <= len(ids):
                yield ids[start:start + length]


def best_lines(raw, lines, settings):
    best = (0.0, [])
    by_photo = {}
    for line_id, line in lines.items():
        by_photo.setdefault(line["photo"], []).append(line_id)
    for ids in by_photo.values():
        if len(norm(raw)) > settings["long_text"]:
            score = similarity(raw, photo_text(lines, ids), settings)
            chosen = [i for i in ids if token_coverage(lines[i]["text"], raw) >= 0.5] or ids
        else:
            scored = [(similarity(raw, photo_text(lines, window), settings), -len(window), window) for window in windows(ids, 3)]
            score, _, chosen = max(scored, default=(0.0, 0, []))
        if score > best[0]:
            best = (score, chosen)
    return best


def value_lines(kind, name, value, lines, cited):
    for i in cited + [i for i in lines if i not in cited]:
        if present(kind, name, value, lines[i]["text"]):
            return [i]
    by_photo = {}
    for line_id, line in lines.items():
        by_photo.setdefault(line["photo"], []).append(line_id)
    for ids in by_photo.values():
        for first, second in zip(ids, ids[1:]):
            a, b = lines[first]["text"], lines[second]["text"]
            if present(kind, name, value, f"{a} {b}") or (kind == "number" and (beside(name, value, a, b) or beside(name, value, b, a))):
                return [first, second]
    return []


def anchored(anchor, lines, ids):
    if not ids:
        return False
    photo = [i for i in lines if lines[i]["photo"] == lines[ids[0]]["photo"]]
    position = photo.index(ids[0])
    return anchor in norm(photo_text(lines, photo[max(0, position - 1):position] + ids))


def quoted(word, raw):
    a, b = skeleton(word), skeleton(raw)
    if len(a) < 2:
        return False
    if len(a) <= 3:
        return a in b.split()
    return fuzz.partial_ratio(a, b) >= 80


def evidence(lines, ids, raw):
    items = []
    for i in ids:
        line = lines[i]
        words = [word for word in line.get("words", []) if quoted(word["text"], raw)]
        text, box = line["text"], line["box"]
        if words:
            text = " ".join(word["text"] for word in words)
            box = [min(word["box"][0] for word in words), min(word["box"][1] for word in words),
                   max(word["box"][2] for word in words), max(word["box"][3] for word in words)]
        items.append({"source": "photo", "line": i, "photo": line["photo"], "text": text, "box": box})
    return items


def check_field(name, spec, proposal, lines, farmer_text, settings):
    raw = (proposal or {}).get("raw")
    source = (proposal or {}).get("source", "photo")
    empty = {"value": None, "raw": None, "source": "none", "confidence": 0.0, "evidence": []}
    if not raw or source == "none":
        return empty, None
    parsed = parse(spec["kind"], name, raw)
    entry = {"field": name, "proposed": raw, "source": source}
    if parsed is None:
        return empty, {**entry, "decision": "rejected", "reason": "значение не разбирается"}
    if source == "farmer":
        score = similarity(raw, farmer_text, settings)
        if passes(raw, score, settings) and (spec["kind"] not in NUMERIC or present(spec["kind"], name, parsed, farmer_text)):
            result = {"value": parsed, "raw": raw, "source": "farmer", "confidence": round(score, 3),
                      "evidence": [{"source": "farmer", "text": raw}]}
            return result, {**entry, "decision": "accepted", "score": round(score, 3)}
        return empty, {**entry, "decision": "rejected", "reason": "нет в словах фермера", "score": round(score, 3)}
    cited = [i for i in (proposal.get("lines") or []) if i in lines]
    if spec["kind"] in NUMERIC:
        cited = value_lines(spec["kind"], name, parsed, lines, cited)
        if not cited:
            return empty, {**entry, "decision": "rejected", "reason": "значения нет на фото рядом с единицей или названием"}
        score = similarity(raw, photo_text(lines, cited), settings)
    else:
        score = similarity(raw, photo_text(lines, cited), settings) if cited else 0.0
        if not passes(raw, score, settings, spec.get("ratio")):
            score, cited = best_lines(raw, lines, settings)
        if not passes(raw, score, settings, spec.get("ratio")):
            return empty, {**entry, "decision": "rejected", "reason": "нет в тексте фото", "score": round(score, 3)}
        if spec.get("anchor") and not anchored(spec["anchor"], lines, cited):
            return empty, {**entry, "decision": "rejected", "reason": f"рядом нет слова «{spec['anchor']}»", "score": round(score, 3)}
    confidence = mean(lines[i]["confidence"] for i in cited) * min(score, 1.0)
    result = {"value": parsed, "raw": raw, "source": "photo", "confidence": round(confidence, 3), "evidence": evidence(lines, cited, raw)}
    return result, {**entry, "decision": "accepted", "score": round(score, 3), "lines": cited}


def apply_conflicts(fields, hints, settings):
    issues = []
    farmer_weight = parse_quantity(hints.get("weight") or "")
    current = fields.get("net_quantity")
    if farmer_weight and current and current["source"] == "photo":
        label = current["value"]
        if label["unit"] == farmer_weight["unit"]:
            gap = abs(label["value"] - farmer_weight["value"]) / max(label["value"], 1e-9)
            if gap > settings["conflict_tolerance"]:
                fields["net_quantity"] = {
                    **current, "source": "conflict",
                    "alternatives": [{"value": label, "source": "photo"}, {"value": farmer_weight, "source": "farmer"}],
                }
                issues.append({"rule": "label_farmer_mismatch", "severity": "block", "field": "net_quantity",
                               "message": f"На этикетке {label['value']:g}, а в вашем вводе {farmer_weight['value']:g}. Выберите верное значение."})
    return issues


def verify(fields_spec, proposals, lines, hints, settings):
    farmer_text = " ".join(str(value) for value in hints.values() if value)
    fields, log = {}, []
    for name, spec in fields_spec.items():
        result, entry = check_field(name, spec, proposals.get(name), lines, farmer_text, settings)
        fields[name] = result
        if entry:
            log.append(entry)
    return fields, log, apply_conflicts(fields, hints, settings)