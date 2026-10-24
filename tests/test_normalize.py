import pytest

from card.normalize import norm, parse, parse_duration, present, parse_energy, parse_nutrient, parse_percent, parse_quantity


@pytest.mark.parametrize("raw, expected", [
    ("Масса нетто 200 г", {"value": 200, "unit": "g"}),
    ("0,5 кг", {"value": 500, "unit": "g"}),
    ("Объём 1 л", {"value": 1000, "unit": "ml"}),
    ("900 мл", {"value": 900, "unit": "ml"}),
    ("350 гр.", {"value": 350, "unit": "g"}),
])
def test_quantity(raw, expected):
    assert parse_quantity(raw) == expected


def test_quantity_ignores_words_starting_with_unit_letters():
    assert parse_quantity("5 лимонов") is None


@pytest.mark.parametrize("raw, unit, value", [
    ("Срок годности 12 месяцев", "months", 12),
    ("180 суток", "days", 180),
    ("2 года", "years", 2),
    ("30 дней", "days", 30),
])
def test_duration(raw, unit, value):
    parsed = parse_duration(raw)
    assert parsed["unit"] == unit and parsed["value"] == value


def test_batch_date_is_not_a_duration():
    assert parse_duration("Годен до 12.2026") is None


def test_energy_prefers_kcal():
    assert parse_energy("Энергетическая ценность 1046 кДж (250 ккал)") == {"value": 250}
    assert parse_energy("1046 кДж") is None


def test_nutrient_skips_per_100_g():
    raw = "Пищевая ценность на 100 г: белки 6,2 г, жиры 10 г, углеводы 30,5 г"
    assert parse_nutrient(raw, "proteins_g") == {"value": 6.2}
    assert parse_nutrient(raw, "fats_g") == {"value": 10}
    assert parse_nutrient(raw, "carbohydrates_g") == {"value": 30.5}


def test_percent():
    assert parse_percent("массовая доля жира 45 %") == {"value": 45}


def test_norm_replaces_latin_lookalikes_in_russian_text():
    assert norm("He содержит ГМО") == "не содержит гмо"
    assert norm("Maсса нетто 500 г") == "масса нетто 500 г"
    assert norm("НАТРИЯ Е50О (ii)") == "натрия е 500 ii"
    assert norm("OT 2C до6°C") == "от 2 с до 6 с"


def test_norm_keeps_english_words():
    assert norm("Protein 6.2 g") == "protein 6.2 g"


def test_unlimited_shelf_life():
    assert parse_duration("Срок годности не ограничен при соблюдении условий хранения") == {"value": None, "unit": "unlimited", "days": None}


def test_present_reads_ocr_variants():
    assert present("energy", "energy_kcal", {"value": 66.8}, "(66,8 кал)")
    assert present("number", "proteins_g", {"value": 8.0}, "6елки 8,0r")
    assert not present("quantity", "net_quantity", {"value": 100, "unit": "g"}, "Пищевая ценность на 100 г продукта")


def test_present_reads_ocr_variants_of_nutrient_names():
    assert present("number", "fats_g", {"value": 0.1}, "белки 1,0 г, *уры 0,1r углеводы 25,0r.")
    assert present("number", "fats_g", {"value": 67.0}, "значения): *упы 67r белки -0,4 г")
    assert present("number", "carbohydrates_g", {"value": 5.0}, "белка 6,1r улеводов-5")
    assert not present("number", "fats_g", {"value": 1.0}, "белки 1,0 г, *уры 0,1r")


def test_title_in_capitals_is_brought_to_sentence_case():
    assert parse("text", "name", "ХЛОПЬЯ ПШЕННЫЕ НЕ ТРЕБУЮЩИЕ ВАРКИ") == {"value": "Хлопья пшенные не требующие варки"}
    assert parse("text", "name", "Творог мягкий") == {"value": "Творог мягкий"}


def test_composition_drops_label_word():
    assert parse("text", "composition", "Состав: молоко нормализованное, закваска") == {"value": "молоко нормализованное, закваска"}
    assert parse("text", "composition", "СОСТАВ молоко") == {"value": "молоко"}
    assert parse("text", "composition", "Составной продукт") == {"value": "Составной продукт"}