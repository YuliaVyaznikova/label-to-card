import hashlib
import json
import re
from pathlib import Path

import cv2

from .quality import fit, read_image

VERSION = 3
ROTATIONS = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}


def back(x, y, angle, width, height):
    if angle == 90:
        return y, height - x
    if angle == 180:
        return width - x, height - y
    if angle == 270:
        return width - y, x
    return x, y


def letters(items):
    return sum(item["confidence"] * len(re.findall(r"[^\W\d_]", item["text"])) for item in items if item["confidence"] >= 0.5)


def join(items):
    size = sum(len(item["text"]) for item in items)
    return {
        "text": " ".join(item["text"] for item in items),
        "confidence": round(sum(item["confidence"] * len(item["text"]) for item in items) / max(size, 1), 3),
        "box": [min(item["box"][0] for item in items), min(item["box"][1] for item in items),
                max(item["box"][2] for item in items), max(item["box"][3] for item in items)],
        "words": [{"text": item["text"], "box": item["box"]} for item in items],
    }


def merge(fragments, overlap, gap):
    rows = []
    for item in sorted(fragments, key=lambda item: item["view"][0]):
        left, top, _, bottom = item["view"]
        best, best_shared = None, 0.0
        for row in rows:
            last = row[-1]["view"]
            shared = min(bottom, last[3]) - max(top, last[1])
            near = left - last[2] <= gap * max(bottom - top, last[3] - last[1])
            if near and shared > overlap * min(bottom - top, last[3] - last[1]) and shared > best_shared:
                best, best_shared = row, shared
        if best is None:
            rows.append([item])
        else:
            best.append(item)
    rows.sort(key=lambda row: (round(min(item["view"][1] for item in row) / 20), row[0]["view"][0]))
    return [join(row) for row in rows]


class Ocr:
    def __init__(self, settings, cache=None):
        self.settings = settings
        self.engine = None
        self.cache = Path(cache) / "ocr" if cache else None
        if self.cache:
            self.cache.mkdir(parents=True, exist_ok=True)

    def load(self):
        if self.engine is None:
            from rapidocr import LangDet, LangRec, ModelType, OCRVersion, RapidOCR
            self.engine = RapidOCR(params={
                "Det.ocr_version": OCRVersion.PPOCRV5, "Det.lang_type": LangDet.MULTI, "Det.model_type": ModelType.MOBILE,
                "Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.lang_type": LangRec.ESLAV, "Rec.model_type": ModelType.MOBILE,
                "Global.text_score": self.settings["min_confidence"], "Global.log_level": "error",
            })
        return self.engine

    def recognize(self, path):
        image = read_image(path)
        if image is None:
            return []
        image, scale = fit(image, self.settings["max_pixels"])
        best, best_score = [], -1.0
        for angle in [0, *self.settings["rotations"]]:
            items = self.recognize_view(image, angle, scale)
            score = letters(items)
            if score > best_score:
                best, best_score = items, score
            if angle == 0 and score >= self.settings["enough_letters"]:
                break
        return best

    def recognize_view(self, image, angle, scale):
        height, width = image.shape[:2]
        view = cv2.rotate(image, ROTATIONS[angle]) if angle else image
        result = self.load()(view)
        boxes = result.boxes if result.boxes is not None else []
        fragments = []
        for corners, text, confidence in zip(boxes, result.txts or (), result.scores or ()):
            if not text.strip():
                continue
            points = [back(x, y, angle, width, height) for x, y in corners]
            xs = [point[0] / scale for point in points]
            ys = [point[1] / scale for point in points]
            fragments.append({
                "text": text.strip(), "confidence": float(confidence),
                "box": [int(round(min(xs))), int(round(min(ys))), int(round(max(xs))), int(round(max(ys)))],
                "view": [min(x for x, _ in corners), min(y for _, y in corners), max(x for x, _ in corners), max(y for _, y in corners)],
            })
        return merge(fragments, self.settings["row_overlap"], self.settings["column_gap"]) if fragments else []

    def read(self, path, photo):
        items = None
        if self.cache:
            key = hashlib.sha256(Path(path).read_bytes() + json.dumps([VERSION, self.settings], sort_keys=True).encode()).hexdigest()
            cached = self.cache / f"{key}.json"
            if cached.exists():
                items = json.loads(cached.read_text(encoding="utf-8"))
        if items is None:
            items = self.recognize(path)
            if self.cache:
                cached.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        return [{"id": f"p{photo}:l{number}", "photo": photo, **item} for number, item in enumerate(items, 1)]