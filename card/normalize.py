import re

NUMBER = r"\d+(?:[.,]\d+)?"
PER_100 = r"(?:(?:на|в)\s*)?100\s*(?:г|гр|грамм\w*|мл)\b\.?(?:\s*продукт\w*)?"
PER_100_CONTEXT = r"(?:на|в)\s*100\s*(?:г|гр|мл)(?![а-я])|100\s*(?:г|гр|мл)\.?\s*продукт\w*"
UNLIMITED = r"(?:не|ne)\s*ограничен"
ENERGY_UNIT = r"(?:к?кал|kcal)(?![а-я])"
QUANTITY = r"(\d+(?:[.,]\d+)?)\s*(кг|kg|килограмм\w*|граммов|грамм\w*|гр|г|g|мл|ml|миллилитр\w*|литр\w*|л|l|шт)(?![а-яa-z])"
NUTRIENTS = {
    "proteins_g": ("белк", "белок", "protein"),
    "fats_g": ("жир", "fat"),
    "carbohydrates_g": ("углевод", "carbohydr"),
}
NUTRIENT_PATTERNS = {
    "proteins_g": r"бел[кo]|protein",
    "fats_g": r"ж[иу][рп]|fat",
    "carbohydrates_g": r"уг?лев|carbohydr",
}
LATIN = "ABCEHKMOPTXYaceopxykΑΒΕΗΚΛΜΟΠΡΤΥΧαο"
LOOKALIKES = str.maketrans(LATIN, "АВСЕНКМОРТХУасеорхукАВЕНКЛМОПРТУХао")
DURATION_UNITS = [
    ("сут", "days", 1), ("дн", "days", 1), ("ден", "days", 1), ("час", "hours", 1 / 24),
    ("мес", "months", 30), ("год", "years", 365), ("лет", "years", 365),
]


def cyrillic(word):
    if re.search("[а-яёА-ЯЁ]", word) or all(letter in LATIN for letter in word):
        return word.translate(LOOKALIKES)
    return word


def norm(text):
    text = re.sub(r"\*(?=[^\W\d_])", "ж", text or "")
    text = re.sub(r"[^\W\d_]+", lambda match: cyrillic(match.group(0)), text)
    text = text.lower().replace("ё", "е")
    text = re.sub(r"(?<=\d)о|о(?=\d)", "0", text)
    text = re.sub(r"(?<=\d)r(?![a-zа-я])", "г", text)
    text = re.sub(r"(\d)\s*[,.]\s*(\d)", r"\1.\2", text)
    text = re.sub(r"[^\w.%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text):
    return [token for token in norm(text).split() if len(token) >= 3 or re.fullmatch(NUMBER, token)]


def to_float(token):
    return float(token.replace(",", "."))


def numbers(text):
    return [to_float(token) for token in re.findall(NUMBER, text or "")]


def quantity(number, unit):
    value = to_float(number)
    if unit.startswith(("кг", "kg", "килограмм")):
        return {"value": round(value * 1000, 3), "unit": "g"}
    if unit.startswith(("мл", "ml", "миллилитр")):
        return {"value": value, "unit": "ml"}
    if unit.startswith(("л", "l", "литр")):
        return {"value": round(value * 1000, 3), "unit": "ml"}
    if unit == "шт":
        return {"value": value, "unit": "pcs"}
    return {"value": value, "unit": "g"}


def parse_quantity(raw):
    match = re.search(QUANTITY, (raw or "").lower().replace("ё", "е"))
    return quantity(*match.groups()) if match else None


def durations(text):
    for match in re.finditer(rf"({NUMBER})\s*([а-я]+)", text):
        word = match.group(2)
        for prefix, unit, days in DURATION_UNITS:
            if word.startswith(prefix):
                value = to_float(match.group(1))
                yield {"value": value, "unit": unit, "days": round(value * days, 1)}
                break


def parse_duration(raw):
    text = (raw or "").lower().replace("ё", "е")
    if re.search(UNLIMITED, text):
        return {"value": None, "unit": "unlimited", "days": None}
    return next(durations(text), None)


def parse_energy(raw):
    text = (raw or "").lower().replace("ё", "е")
    match = re.search(rf"({NUMBER})\s*{ENERGY_UNIT}", text) or re.search(rf"{ENERGY_UNIT}\D{{0,4}}({NUMBER})", text)
    return {"value": to_float(match.group(1))} if match else None


def parse_percent(raw):
    match = re.search(rf"({NUMBER})\s*%", raw or "")
    return {"value": to_float(match.group(1))} if match else None


def parse_nutrient(raw, field):
    text = re.sub(PER_100, " ", (raw or "").lower().replace("ё", "е"))
    for keyword in NUTRIENTS[field]:
        position = text.find(keyword)
        if position >= 0:
            found = re.search(NUMBER, text[position:])
            return {"value": to_float(found.group(0))} if found else None
    found = re.findall(NUMBER, text)
    return {"value": to_float(found[0])} if len(found) == 1 else None


def parse_text(raw):
    text = re.sub(r"\s+", " ", raw or "").strip(" .;:,")
    return {"value": text} if text else None


def parse_title(raw):
    parsed = parse_text(raw)
    if not parsed:
        return None
    letters = [char for char in parsed["value"] if char.isalpha()]
    if letters and sum(char.isupper() for char in letters) / len(letters) > 0.6:
        lowered = parsed["value"].lower()
        parsed["value"] = lowered[:1].upper() + lowered[1:]
    return parsed


def parse(kind, field, raw):
    if kind == "quantity":
        return parse_quantity(raw)
    if kind == "duration":
        return parse_duration(raw)
    if kind == "energy":
        return parse_energy(raw)
    if kind == "percent":
        return parse_percent(raw)
    if kind == "number":
        return parse_nutrient(raw, field)
    if field == "name":
        return parse_title(raw)
    return parse_text(raw)


def nutrient_text(text):
    return re.sub(r"(?<![\d.])6(?=ел)", "б", re.sub(PER_100, " ", text))


def nutrient_numbers(text, field):
    text = nutrient_text(text)
    found = []
    for match in re.finditer(NUTRIENT_PATTERNS[field], text):
        after = re.search(NUMBER, text[match.end():match.end() + 30])
        if after:
            found.append(after.group(0))
    return found


def same(a, b):
    return a is not None and b is not None and abs(a - b) < 1e-6


def present(kind, field, value, text):
    text = norm(text)
    if kind == "quantity":
        found = (quantity(*match.groups()) for match in re.finditer(QUANTITY, re.sub(PER_100_CONTEXT, " ", text)))
        return any(same(item["value"], value["value"]) and item["unit"] == value["unit"] for item in found)
    if kind == "duration":
        if value["unit"] == "unlimited":
            return bool(re.search(UNLIMITED, text))
        return any(same(item["days"], value["days"]) for item in durations(text))
    if kind == "energy":
        found = re.findall(rf"({NUMBER})\s*{ENERGY_UNIT}", text) + re.findall(rf"{ENERGY_UNIT}\D{{0,4}}({NUMBER})", text)
    elif kind == "percent":
        found = re.findall(rf"({NUMBER})\s*%", text)
    elif kind == "number":
        found = nutrient_numbers(text, field)
    else:
        return True
    return any(same(to_float(item), value["value"]) for item in found)


def beside(field, value, label, neighbour):
    label, neighbour = nutrient_text(norm(label)), nutrient_text(norm(neighbour))
    if not re.search(NUTRIENT_PATTERNS[field], label):
        return False
    if any(re.search(pattern, neighbour) for pattern in NUTRIENT_PATTERNS.values()):
        return False
    return any(same(to_float(number), value["value"]) for number in re.findall(NUMBER, neighbour))