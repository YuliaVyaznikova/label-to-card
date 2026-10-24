import re

PHONE = r"(?:\+7|\b8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}"
LINK = r"https?://|www\.|\b[\w-]+\.(?:ru|com|рф|net|org)\b|t\.me/|vk\.com"
HANDLE = r"@\w{3,}|whatsapp|ватсап|вотсап|телеграм|telegram|звоните|пишите в личку"
MEDICAL = r"лечит|лечебн|исцел|от давлени|от простуд|от рака|от диабет|панаце|вылеч|избавит от|укрепляет иммунитет"
DISCOUNT = r"скидк|акци[яи]|распродаж|-\s?\d+\s?%|\d+\s?%\s?скидк"
CLAIMS = [
    "натуральн", "без консервант", "органическ", "эко", "без гмо", "гост", "домашн", "фермерск",
    "без сахара", "без глютена", "без лактозы", "полезн", "диетическ",
]
EMOJI = r"[\U0001F300-\U0001FAFF☀-➿]"


def found(pattern, text):
    return re.search(pattern, (text or "").lower()) is not None


def claims(text):
    text = (text or "").lower().replace("ё", "е")
    return [claim for claim in CLAIMS if claim in text]


def caps_share(text):
    letters = [char for char in text or "" if char.isalpha()]
    return sum(char.isupper() for char in letters) / len(letters) if letters else 0.0


def moderate(title, description, hints, label_text, category, category_spec):
    notes = hints.get("notes") or ""
    texts = {"название": title or "", "описание": description or "", "уточнения": notes}
    issues = []
    for place, text in texts.items():
        if found(PHONE, text) or found(LINK, text) or found(HANDLE, text):
            issues.append({"rule": "contacts", "severity": "block", "field": place,
                           "message": f"В поле «{place}» есть контакты или ссылка, площадка не разрешает их в карточке"})
        if found(MEDICAL, text):
            issues.append({"rule": "medical_claims", "severity": "block", "field": place,
                           "message": f"В поле «{place}» есть обещание лечебного эффекта, для пищевых продуктов это запрещено"})
    label = (label_text or "").lower().replace("ё", "е")
    for claim in claims(notes):
        if claim not in label:
            issues.append({"rule": "unsupported_claim", "severity": "warning", "field": "уточнения",
                           "message": f"Утверждение «{claim}…» есть только в Ваших словах, приложите документ, который его подтверждает"})
    if title:
        if caps_share(title) > 0.6 and len(title) > 6:
            issues.append({"rule": "title_caps", "severity": "warning", "field": "название", "message": "Название набрано заглавными буквами"})
        if found(DISCOUNT, title) or re.search(r"\d+\s?(?:₽|руб)", title.lower()):
            issues.append({"rule": "title_price", "severity": "warning", "field": "название", "message": "Цену и скидки в название не пишут"})
        if re.search(EMOJI, title):
            issues.append({"rule": "title_emoji", "severity": "warning", "field": "название", "message": "Уберите эмодзи из названия"})
    chosen = hints.get("category")
    if chosen and category and category["value"] and chosen != category["value"] and category["confidence"] >= 0.6:
        issues.append({"rule": "category_mismatch", "severity": "warning", "field": "категория",
                       "message": f"Вы выбрали «{chosen}», а по фото товар похож на «{category['value']}»"})
    if category_spec and category_spec.get("animal"):
        issues.append({"rule": "vet_documents", "severity": "warning", "field": "категория",
                       "message": "Для продукции животного происхождения площадке могут понадобиться ветеринарные документы, уточните её требования"})
    return issues