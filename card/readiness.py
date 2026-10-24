from statistics import mean

from .moderation import caps_share

ACTIONS = {
    "name": "Сфотографируйте лицевую сторону упаковки с названием или впишите название.",
    "composition": "Сфотографируйте часть этикетки с составом или впишите состав.",
    "net_quantity": "Укажите массу или объём, сервис не нашёл их на фото.",
    "shelf_life": "Укажите срок годности, сервис не нашёл его на фото.",
    "storage": "Укажите условия хранения или сфотографируйте их на этикетке.",
    "manufacturer": "Укажите изготовителя и его адрес.",
    "energy_kcal": "Сфотографируйте таблицу пищевой ценности или впишите белки, жиры, углеводы и калорийность.",
    "proteins_g": "Сфотографируйте таблицу пищевой ценности или впишите белки, жиры, углеводы и калорийность.",
    "fats_g": "Сфотографируйте таблицу пищевой ценности или впишите белки, жиры, углеводы и калорийность.",
    "carbohydrates_g": "Сфотографируйте таблицу пищевой ценности или впишите белки, жиры, углеводы и калорийность.",
}


def field_credit(field, threshold):
    if field["source"] in ("farmer", "edited"):
        return 1.0
    if field["source"] == "photo":
        return 1.0 if field["confidence"] >= threshold else 0.5
    if field["source"] == "conflict":
        return 0.5
    return 0.0


def text_checks(title, description, description_checked, settings):
    length = len(description or "")
    return [
        {"name": "title_present", "passed": bool(title), "message": "Добавьте название товара."},
        {"name": "title_length", "passed": not title or 5 <= len(title) <= 80, "message": "Название должно быть от 5 до 80 символов."},
        {"name": "title_case", "passed": caps_share(title) <= 0.6, "message": "Не набирайте название заглавными буквами."},
        {"name": "description_length", "passed": settings["min_length"] <= length <= settings["max_length"],
         "message": f"Описание должно быть от {settings['min_length']} до {settings['max_length']} символов."},
        {"name": "description_checked", "passed": description_checked, "message": "Описание не прошло проверку фактов, поправьте его."},
    ]


def readiness(fields, fields_spec, photo_checks, text_list, threshold):
    required = [name for name, spec in fields_spec.items() if spec["required"]]
    credits = [field_credit(fields[name], threshold) for name in required]
    field_part = mean(credits) if credits else 1.0
    photo_part = mean(check["passed"] for check in photo_checks) if photo_checks else 0.0
    text_part = mean(check["passed"] for check in text_list) if text_list else 0.0
    score = round(60 * field_part + 20 * photo_part + 20 * text_part)
    missing, seen = [], set()
    for name in required:
        field = fields[name]
        if field["source"] == "none":
            action = ACTIONS.get(name, f"Заполните поле «{fields_spec[name]['title']}».")
        elif field["source"] == "conflict":
            action = f"Выберите верное значение поля «{fields_spec[name]['title']}»."
        elif field["source"] == "photo" and field["confidence"] < threshold:
            action = f"Проверьте поле «{fields_spec[name]['title']}», текст на фото читается плохо."
        else:
            continue
        if action not in seen:
            seen.add(action)
            missing.append({"field": name, "action": action})
    named = {item["field"] for item in missing}
    for check in photo_checks + text_list:
        if not check["passed"] and check["message"] not in seen and check.get("field") not in named:
            seen.add(check["message"])
            missing.append({"field": None, "action": check["message"]})
    return {"score": score, "fields": round(field_part, 3), "photos": round(photo_part, 3), "text": round(text_part, 3)}, missing