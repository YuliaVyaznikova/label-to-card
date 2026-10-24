import numpy as np
from PIL import Image

from .normalize import norm


def pretrained(loader, name):
    try:
        return loader.from_pretrained(name, local_files_only=True)
    except OSError:
        return loader.from_pretrained(name)


class Classifier:
    def __init__(self, settings, categories):
        self.settings = settings
        self.categories = categories["categories"]
        self.model = None
        self.processor = None
        self.pairs = [(key, label) for key, spec in self.categories.items() for label in spec["labels"]]

    def load(self):
        if self.model is None:
            import torch
            from transformers import AutoModel, AutoProcessor
            self.torch = torch
            self.device = "cuda" if self.settings["device"] == "cuda" and torch.cuda.is_available() else "cpu"
            self.processor = pretrained(AutoProcessor, self.settings["model"])
            self.model = pretrained(AutoModel, self.settings["model"]).eval().to(self.device)

    def image_scores(self, paths):
        self.load()
        images = [Image.open(path).convert("RGB") for path in paths]
        texts = [f"фото товара: {label}" for _, label in self.pairs]
        inputs = self.processor(text=texts, images=images, padding="max_length", max_length=64, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            logits = self.model(**inputs).logits_per_image.cpu().numpy()
        by_label = logits.mean(axis=0)
        keys = list(self.categories)
        best = np.array([max(by_label[i] for i, (key, _) in enumerate(self.pairs) if key == category) for category in keys])
        weights = np.exp(best - best.max())
        return dict(zip(keys, weights / weights.sum()))

    def keyword_scores(self, text):
        words = set(norm(text).split())
        hits = {key: sum(any(word.startswith(norm(keyword)) for word in words) for keyword in spec["keywords"]) for key, spec in self.categories.items()}
        total = sum(hits.values())
        return {key: count / total for key, count in hits.items()} if total else None

    def classify(self, paths, text):
        scores = self.image_scores(paths)
        keywords = self.keyword_scores(text)
        if keywords:
            weight = self.settings["keyword_weight"]
            scores = {key: (1 - weight) * value + weight * keywords[key] for key, value in scores.items()}
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top, confidence = ranked[0]
        return {
            "key": top,
            "value": self.categories[top]["title"],
            "confidence": round(float(confidence), 3),
            "alternatives": [{"key": key, "value": self.categories[key]["title"], "confidence": round(float(score), 3)} for key, score in ranked[1:3]],
        }