import time

from .classify import Classifier
from .config import category_fields, load_categories, load_config
from .describe import describe, show
from .extract import extract
from .moderation import moderate
from .normalize import parse
from .ocr import Ocr
from .quality import photo_checks, photo_quality
from .readiness import readiness, text_checks
from .verify import verify
from .vlm import parse_json, Vlm


class Pipeline:
    def __init__(self, config=None, categories=None):
        self.config = config or load_config()
        self.categories = categories or load_categories()
        self.ocr = Ocr(self.config["ocr"], self.config["paths"]["cache"])
        self.classifier = Classifier(self.config["classify"], self.categories)
        self.vlm = Vlm(self.config["vlm"], self.config["paths"]["cache"])

    def generate(self, prompt):
        result = self.vlm.chat([{"role": "user", "content": prompt}])
        parsed = parse_json(result["text"]) or {}
        return parsed.get("description")

    def read(self, photos):
        lines = {}
        for number, path in enumerate(photos, 1):
            for line in self.ocr.read(path, number):
                lines[line["id"]] = line
        return lines

    def run(self, photos, hints, model=None):
        timings = {}
        started = time.time()
        qualities = [photo_quality(path, self.config["quality"]) for path in photos]
        lines = self.read(photos)
        timings["ocr"] = round(time.time() - started, 2)
        label_text = " ".join(line["text"] for line in lines.values())
        step = time.time()
        category = self.classifier.classify(photos, label_text)
        timings["classify"] = round(time.time() - step, 2)
        fields_spec = category_fields(self.categories, category["key"])
        step = time.time()
        proposals, call = extract(self.vlm, photos, lines, fields_spec, hints, self.config["vlm"]["max_pixels"], model)
        timings["extract"] = round(time.time() - step, 2)
        fields, log, conflicts = verify(fields_spec, proposals, lines, hints, self.config["verify"])
        name = (fields.get("name") or {}).get("value") or {}
        if name.get("value"):
            category = self.classifier.classify(photos, label_text, name["value"])
        draft = {
            "category": category, "fields": fields, "log": log, "lines": lines, "photos": qualities,
            "hints": hints, "proposals": proposals, "calls": [call], "conflicts": conflicts,
        }
        step = time.time()
        self.finish(draft)
        timings["finish"] = round(time.time() - step, 2)
        timings["total"] = round(time.time() - started, 2)
        draft["timings"] = timings
        return draft

    def finish(self, draft, regenerate=True):
        category_spec = self.categories["categories"][draft["category"]["key"]]
        fields_spec = category_fields(self.categories, draft["category"]["key"])
        fields, lines, hints = draft["fields"], draft["lines"], draft["hints"]
        for name in fields_spec:
            fields.setdefault(name, {"value": None, "raw": None, "source": "none", "confidence": 0.0, "evidence": []})
        label_text = " ".join(line["text"] for line in lines.values())
        evidence_text = label_text + " " + " ".join(str(value) for value in hints.values() if value)
        if regenerate or not draft.get("description"):
            draft["description"] = describe(fields, fields_spec, evidence_text, self.generate, self.config["description"])
        title = show(fields["name"]) or ""
        issues = moderate(title, draft["description"]["text"], hints, label_text, draft["category"], category_spec)
        issues += [issue for issue in draft.get("conflicts", []) if fields.get(issue["field"], {}).get("source") == "conflict"]
        checks = photo_checks(draft["photos"], lines, fields)
        texts = text_checks(title, draft["description"]["text"], draft["description"]["checked"], self.config["description"])
        draft["readiness"], draft["missing"] = readiness(fields, fields_spec, checks, texts, self.config["readiness"]["confidence"])
        draft["moderation"] = issues
        blocked = any(issue["severity"] == "block" for issue in issues)
        empty = any(fields[name]["source"] in ("none", "conflict") for name, spec in fields_spec.items() if spec["required"])
        draft["status"] = "draft" if blocked or empty else "ready"
        return draft

    def edit(self, draft, edits):
        fields_spec = category_fields(self.categories, draft["category"]["key"])
        changed = False
        for name, raw in edits.items():
            if name == "description":
                draft["description"] = {"text": raw, "checked": True, "method": "edited", "problems": []}
                continue
            if name == "category":
                key = next((key for key, spec in self.categories["categories"].items() if key == raw or spec["title"] == raw), None)
                if key:
                    draft["category"] = {**draft["category"], "key": key, "value": self.categories["categories"][key]["title"], "confidence": 1.0}
                continue
            if name not in fields_spec:
                continue
            parsed = parse(fields_spec[name]["kind"], name, raw) if raw else None
            draft["fields"][name] = {
                "value": parsed, "raw": raw or None, "source": "edited" if parsed else "none",
                "confidence": 1.0 if parsed else 0.0, "evidence": [{"source": "farmer", "text": raw}] if parsed else [],
            }
            changed = True
        return self.finish(draft, regenerate=changed and draft["description"].get("method") != "edited")