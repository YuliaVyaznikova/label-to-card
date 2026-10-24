import json

from .vlm import image_part, parse_json

RULES = """Ты помогаешь фермеру заполнить карточку товара по фото упаковки. Тебе дают фото, распознанный текст с номерами строк и слова фермера.
Для каждого поля верни объект {"raw": ..., "lines": [...], "source": ...}:
- raw: дословная цитата с фото, как напечатано, вместе с числом и единицей измерения, или дословная цитата из слов фермера. Сверяйся с самим фото: в распознанном тексте бывают ошибки, а бессмысленные строки не цитируй;
- lines: номера строк распознанного текста, где стоит цитата, например ["p2:l7", "p2:l8"];
- source: "photo", если цитата с фото, "farmer", если из слов фермера, "none", если сведений нет.
Для каждого показателя пищевой ценности raw это фрагмент с названием показателя и его числом, например "белки 6,2 г" или "энергетическая ценность 250 ккал".
Если поля нет ни на фото, ни в словах фермера, верни {"raw": null, "lines": [], "source": "none"}.
Никогда не угадывай и не подставляй типичные для такого товара значения. Пустое поле лучше выдуманного.
Ответ только JSON вида {"fields": {"<поле>": {...}}}."""

BASELINE = """По фотографиям товара заполни карточку для маркетплейса. Для каждого поля верни значение строкой.
Если сведений нет на фото, верни null. Ответ только JSON вида {"fields": {"<поле>": "значение или null"}}."""


def field_list(fields_spec):
    return "\n".join(f"- {name}: {spec['title']}" + (f" ({spec['hint']})" if spec.get("hint") else "") for name, spec in fields_spec.items())


def ocr_block(lines, limit=300):
    rows = [f"{line_id} | {line['text']}" for line_id, line in list(lines.items())[:limit]]
    return "\n".join(rows) if rows else "(текст не распознан)"


def farmer_block(hints):
    rows = [f"- {key}: {value}" for key, value in hints.items() if value]
    return "\n".join(rows) if rows else "(фермер ничего не указал)"


def extract(vlm, photos, lines, fields_spec, hints, max_pixels, model=None):
    text = (
        f"{RULES}\n\nПоля:\n{field_list(fields_spec)}\n\nРаспознанный текст:\n{ocr_block(lines)}"
        f"\n\nСлова фермера:\n{farmer_block(hints)}"
    )
    content = [{"type": "text", "text": text}] + [image_part(path, max_pixels) for path in photos]
    result = vlm.chat([{"role": "user", "content": content}], model=model)
    parsed = parse_json(result["text"]) or {}
    proposals = parsed.get("fields", parsed) if isinstance(parsed, dict) else {}
    clean = {}
    for name in fields_spec:
        item = proposals.get(name)
        if isinstance(item, dict):
            clean[name] = {"raw": item.get("raw"), "lines": [str(i) for i in item.get("lines") or []], "source": item.get("source") or "photo"}
        elif isinstance(item, str):
            clean[name] = {"raw": item, "lines": [], "source": "photo"}
    return clean, {"model": result["model"], "usage": result["usage"], "seconds": result["seconds"]}


def baseline(vlm, photos, fields_spec, max_pixels, model=None):
    text = f"{BASELINE}\n\nПоля:\n{field_list(fields_spec)}"
    content = [{"type": "text", "text": text}] + [image_part(path, max_pixels) for path in photos]
    result = vlm.chat([{"role": "user", "content": content}], model=model)
    parsed = parse_json(result["text"]) or {}
    values = parsed.get("fields", parsed) if isinstance(parsed, dict) else {}
    return {name: (json.dumps(values[name], ensure_ascii=False) if isinstance(values.get(name), (dict, list)) else values.get(name)) for name in fields_spec}, {
        "model": result["model"], "usage": result["usage"], "seconds": result["seconds"]}