import base64
import hashlib
import json
import re
import time
from pathlib import Path

import cv2

from .quality import fit, read_image


def image_part(path, max_pixels):
    image, _ = fit(read_image(path), max_pixels)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    data = base64.b64encode(encoded.tobytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}}


def parse_json(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


class Vlm:
    def __init__(self, settings, cache):
        self.settings = settings
        self.cache = Path(cache) / "vlm"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.client = None

    def connect(self):
        if self.client is None:
            from openai import OpenAI
            if not self.settings["api_key"]:
                raise RuntimeError("POLZA_API_KEY не задан, впишите ключ в файл .env")
            self.client = OpenAI(base_url=self.settings["base_url"], api_key=self.settings["api_key"], timeout=120, max_retries=0)
        return self.client

    def chat(self, messages, model=None, json_mode=True):
        model = model or self.settings["model"]
        key = hashlib.sha256(json.dumps([model, messages, json_mode], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        path = self.cache / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        from openai import APIConnectionError, BadRequestError, InternalServerError, RateLimitError
        arguments = {"model": model, "messages": messages, "temperature": self.settings["temperature"], "max_tokens": self.settings["max_tokens"]}
        if json_mode:
            arguments["response_format"] = {"type": "json_object"}
        started = time.time()
        for attempt in range(self.settings["retries"]):
            try:
                response = self.connect().chat.completions.create(**arguments)
                break
            except RateLimitError as error:
                wait = float(error.response.headers.get("retry-after") or 2 ** attempt)
                time.sleep(min(wait, 60))
            except (APIConnectionError, InternalServerError):
                time.sleep(5 * (attempt + 1))
            except BadRequestError:
                if "response_format" not in arguments:
                    raise
                arguments.pop("response_format")
        else:
            raise RuntimeError("VLM: модель не ответила после нескольких попыток")
        usage = response.usage.model_dump() if response.usage else {}
        result = {"text": response.choices[0].message.content, "model": model, "usage": usage, "seconds": round(time.time() - started, 2)}
        path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        with open(self.cache / "usage.jsonl", "a", encoding="utf-8") as log:
            log.write(json.dumps({"model": model, "usage": usage, "seconds": result["seconds"], "at": time.time()}) + "\n")
        return result