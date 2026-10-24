from card.verify import verify

SETTINGS = {"text_ratio": 85, "coverage": 0.8, "long_text": 60, "conflict_tolerance": 0.01}
SPEC = {
    "net_quantity": {"title": "Масса", "kind": "quantity", "required": True},
    "proteins_g": {"title": "Белки", "kind": "number", "required": True},
    "composition": {"title": "Состав", "kind": "text", "required": True, "anchor": "состав"},
    "shelf_life": {"title": "Срок годности", "kind": "duration", "required": True},
}
LINES = {
    "p1:l1": {"id": "p1:l1", "photo": 1, "text": "Сыр Российский", "confidence": 0.9, "box": [0, 0, 10, 10]},
    "p1:l2": {"id": "p1:l2", "photo": 1, "text": "Масса нетто 200 г", "confidence": 0.8, "box": [0, 20, 10, 30]},
    "p2:l1": {"id": "p2:l1", "photo": 2, "text": "Состав: молоко нормализованное пастеризованное, соль поваренная,", "confidence": 0.7, "box": [0, 0, 10, 10]},
    "p2:l2": {"id": "p2:l2", "photo": 2, "text": "закваска мезофильных молочнокислых микроорганизмов, ферментный препарат", "confidence": 0.7, "box": [0, 10, 10, 20]},
    "p2:l3": {"id": "p2:l3", "photo": 2, "text": "Пищевая ценность на 100 г: белки 23,0 г, жиры 29,0 г", "confidence": 0.6, "box": [0, 20, 10, 30]},
}
COMPOSITION = "молоко нормализованное пастеризованное, соль поваренная, закваска мезофильных молочнокислых микроорганизмов, ферментный препарат"


def test_value_found_on_photo_is_accepted_with_evidence():
    proposals = {"net_quantity": {"raw": "200 г", "lines": ["p1:l2"], "source": "photo"}}
    fields, log, _ = verify(SPEC, proposals, LINES, {}, SETTINGS)
    assert fields["net_quantity"]["value"] == {"value": 200, "unit": "g"}
    assert fields["net_quantity"]["evidence"][0]["line"] == "p1:l2"
    assert log[0]["decision"] == "accepted"


def test_invented_number_is_rejected():
    proposals = {"proteins_g": {"raw": "белки 25 г", "lines": ["p2:l3"], "source": "photo"}}
    fields, log, _ = verify(SPEC, proposals, LINES, {}, SETTINGS)
    assert fields["proteins_g"]["source"] == "none"
    assert log[0]["decision"] == "rejected"


def test_wrong_line_reference_is_recovered_by_search():
    proposals = {"proteins_g": {"raw": "белки 23,0 г", "lines": ["p1:l1"], "source": "photo"}}
    fields, _, _ = verify(SPEC, proposals, LINES, {}, SETTINGS)
    assert fields["proteins_g"]["value"] == {"value": 23.0}
    assert fields["proteins_g"]["evidence"][0]["line"] == "p2:l3"


def test_long_composition_spanning_lines_is_accepted():
    proposals = {"composition": {"raw": COMPOSITION, "lines": ["p2:l1", "p2:l2"], "source": "photo"}}
    fields, _, _ = verify(SPEC, proposals, LINES, {}, SETTINGS)
    assert fields["composition"]["source"] == "photo"


def test_shelf_life_absent_from_photos_stays_empty():
    proposals = {"shelf_life": {"raw": "6 месяцев", "lines": [], "source": "photo"}}
    fields, log, _ = verify(SPEC, proposals, LINES, {}, SETTINGS)
    assert fields["shelf_life"]["source"] == "none"
    assert log[0]["reason"] == "значения нет на фото рядом с единицей или названием"


def test_farmer_words_are_a_valid_source():
    proposals = {"shelf_life": {"raw": "6 месяцев", "lines": [], "source": "farmer"}}
    fields, _, _ = verify(SPEC, proposals, LINES, {"notes": "храним до 6 месяцев в погребе"}, SETTINGS)
    assert fields["shelf_life"]["source"] == "farmer"


def test_weight_conflict_blocks():
    proposals = {"net_quantity": {"raw": "200 г", "lines": ["p1:l2"], "source": "photo"}}
    fields, _, issues = verify(SPEC, proposals, LINES, {"weight": "250 г"}, SETTINGS)
    assert fields["net_quantity"]["source"] == "conflict"
    assert issues[0]["severity"] == "block"


ENERGY = {"energy_kcal": {"title": "Энергетическая ценность", "kind": "energy", "required": True}}
ENERGY_LINES = {"p1:l1": {"id": "p1:l1", "photo": 1, "text": "энергетическая ценность 450 кДж/110 ккал", "confidence": 0.9, "box": [0, 0, 10, 10]}}


def test_kilojoules_are_not_taken_for_kilocalories():
    fields, log, _ = verify(ENERGY, {"energy_kcal": {"raw": "450 ккал", "lines": ["p1:l1"], "source": "photo"}}, ENERGY_LINES, {}, SETTINGS)
    assert fields["energy_kcal"]["source"] == "none"
    fields, _, _ = verify(ENERGY, {"energy_kcal": {"raw": "110 ккал", "lines": ["p1:l1"], "source": "photo"}}, ENERGY_LINES, {}, SETTINGS)
    assert fields["energy_kcal"]["value"] == {"value": 110}


def test_ocr_lookalikes_in_quantity_are_accepted():
    lines = {"p1:l1": {"id": "p1:l1", "photo": 1, "text": "Macca HетTо 500r", "confidence": 0.8, "box": [0, 0, 10, 10]}}
    fields, _, _ = verify(SPEC, {"net_quantity": {"raw": "Масса нетто 500 г", "lines": ["p1:l1"], "source": "photo"}}, lines, {}, SETTINGS)
    assert fields["net_quantity"]["value"] == {"value": 500, "unit": "g"}


def test_nutrient_must_follow_its_name():
    proposals = {"proteins_g": {"raw": "29,0 г", "lines": ["p2:l3"], "source": "photo"}}
    fields, _, _ = verify(SPEC, proposals, LINES, {}, SETTINGS)
    assert fields["proteins_g"]["source"] == "none"


NAME = {"name": {"title": "Название", "kind": "text", "required": True, "ratio": 70}}


def test_extra_words_in_quote_are_not_confirmed_by_shorter_line():
    lines = {"p1:l1": {"id": "p1:l1", "photo": 1, "text": "Мёд", "confidence": 0.9, "box": [0, 0, 10, 10]}}
    fields, _, _ = verify(NAME, {"name": {"raw": "Мёд липовый натуральный", "lines": ["p1:l1"], "source": "photo"}}, lines, {}, SETTINGS)
    assert fields["name"]["source"] == "none"


def test_name_in_stylised_font_is_found_on_its_own_line():
    lines = {
        "p1:l1": {"id": "p1:l1", "photo": 1, "text": "Coda", "confidence": 0.6, "box": [0, 0, 10, 10]},
        "p1:l2": {"id": "p1:l2", "photo": 1, "text": "нищевая", "confidence": 0.7, "box": [0, 10, 10, 20]},
        "p2:l1": {"id": "p2:l1", "photo": 2, "text": "Пищевая добавка", "confidence": 0.9, "box": [0, 0, 10, 10]},
    }
    fields, _, _ = verify(NAME, {"name": {"raw": "Сода пищевая", "lines": [], "source": "photo"}}, lines, {}, SETTINGS)
    assert [item["line"] for item in fields["name"]["evidence"]] == ["p1:l1", "p1:l2"]


def test_nutrient_value_on_the_line_above_its_name_is_accepted():
    lines = {
        "p1:l1": {"id": "p1:l1", "photo": 1, "text": "Пищевая ценность 100 г продукта", "confidence": 0.9, "box": [0, 0, 10, 10]},
        "p1:l2": {"id": "p1:l2", "photo": 1, "text": "8,0r", "confidence": 0.9, "box": [0, 10, 10, 20]},
        "p1:l3": {"id": "p1:l3", "photo": 1, "text": "6eлkи акуыздар", "confidence": 0.7, "box": [0, 20, 10, 30]},
        "p1:l4": {"id": "p1:l4", "photo": 1, "text": "2,0r", "confidence": 0.9, "box": [0, 30, 10, 40]},
        "p1:l5": {"id": "p1:l5", "photo": 1, "text": "жиры майлар", "confidence": 0.7, "box": [0, 40, 10, 50]},
    }
    fields, _, _ = verify(SPEC, {"proteins_g": {"raw": "белки 8,0 г", "lines": [], "source": "photo"}}, lines, {}, SETTINGS)
    assert fields["proteins_g"]["value"] == {"value": 8.0}
    fields, _, _ = verify(SPEC, {"proteins_g": {"raw": "белки 9,0 г", "lines": [], "source": "photo"}}, lines, {}, SETTINGS)
    assert fields["proteins_g"]["source"] == "none"


def test_advertising_text_is_not_taken_for_composition():
    lines = {"p1:l1": {"id": "p1:l1", "photo": 1, "text": "100% НАТУРАЛЬНОЕ МОЛОКО", "confidence": 0.9, "box": [0, 0, 10, 10]}}
    fields, log, _ = verify(SPEC, {"composition": {"raw": "100% НАТУРАЛЬНОЕ МОЛОКО", "lines": ["p1:l1"], "source": "photo"}}, lines, {}, SETTINGS)
    assert fields["composition"]["source"] == "none"
    assert log[0]["reason"] == "рядом нет слова «состав»"