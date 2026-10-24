import re

from .moderation import LINK, MEDICAL, PHONE, claims, found
from .normalize import norm, numbers

UNITS = {"g": "г", "ml": "мл", "pcs": "шт"}
PROMPT = (
    "Напиши описание товара для карточки на маркетплейсе фермерских продуктов. Два-четыре предложения, простым языком, "
    "без восклицательных знаков. Используй только факты из списка ниже и не добавляй свойств, которых в нём нет: "
    "ни вкуса, ни пользы для здоровья, ни слов вроде «натуральный» или «домашний», если их нет в фактах. "
    "Числа пиши так же, как в фактах. Пиши без тире, двоеточий и точек с запятой. Верни JSON вида {\"description\": \"...\"}.\n\nФакты:\n"
)


def show(field):
    value = field.get("value")
    if not value:
        return None
    if value.get("unit") == "unlimited":
        return "не ограничен"
    if "unit" in value and "days" not in value:
        return f"{value['value']:g} {UNITS.get(value['unit'], value['unit'])}"
    if field.get("raw") and isinstance(value.get("value"), float):
        return field["raw"]
    return str(value["value"])


def facts(fields, fields_spec):
    return {spec["title"]: show(fields[name]) for name, spec in fields_spec.items() if fields[name]["source"] in ("photo", "farmer", "edited") and show(fields[name])}


def problems(text, facts_text, evidence_text):
    found_problems = []
    allowed = set(numbers(norm(facts_text)))
    extra = [number for number in numbers(norm(text)) if number not in allowed]
    if extra:
        found_problems.append(f"числа без опоры на поля: {', '.join(f'{n:g}' for n in extra)}")
    evidence = (evidence_text or "").lower().replace("ё", "е")
    unsupported = [claim for claim in claims(text) if claim not in evidence]
    if unsupported:
        found_problems.append(f"утверждения без опоры: {', '.join(unsupported)}")
    if found(MEDICAL, text):
        found_problems.append("обещание лечебного эффекта")
    if found(PHONE, text) or found(LINK, text):
        found_problems.append("контакты или ссылка")
    return found_problems


def plain(text):
    return re.sub("\\s*[\u2014\u2013]\\s*", " ", text).strip()


def template(fields, fields_spec):
    parts = []
    name, quantity = show(fields["name"]), show(fields["net_quantity"])
    if name:
        parts.append(f"{name}{', ' + quantity if quantity else ''}.")
    if show(fields["composition"]):
        parts.append(f"Состав {show(fields['composition']).rstrip('.')}.")
    if show(fields["storage"]):
        parts.append(f"{show(fields['storage']).rstrip('.')}.")
    if show(fields["shelf_life"]):
        parts.append(f"Срок годности {show(fields['shelf_life']).rstrip('.')}.")
    return " ".join(parts)


def describe(fields, fields_spec, evidence_text, generate, settings):
    known = facts(fields, fields_spec)
    facts_text = "\n".join(f"- {title}: {value}" for title, value in known.items())
    if not known:
        return {"text": "", "checked": True, "method": "empty", "problems": []}
    last = []
    for _ in range(settings["attempts"]):
        text = generate(PROMPT + facts_text) if generate else None
        if not text:
            break
        text = plain(text)
        last = problems(text, facts_text, evidence_text)
        if not last:
            return {"text": text.strip(), "checked": True, "method": "model", "problems": []}
    text = template(fields, fields_spec)
    return {"text": text, "checked": not problems(text, facts_text, evidence_text), "method": "template", "problems": last}