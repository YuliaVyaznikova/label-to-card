from card.describe import problems
from card.moderation import moderate
from card.readiness import readiness
from card.classify import Classifier
from card.config import load_categories
from card.store import Store


def test_contacts_and_medical_claims_block():
    issues = moderate("Мёд липовый", "Звоните +7 913 123-45-67, мёд лечит простуду", {}, "", None, None)
    rules = {issue["rule"] for issue in issues}
    assert {"contacts", "medical_claims"} <= rules
    assert all(issue["severity"] == "block" for issue in issues)


def test_farmer_claim_without_label_support_warns():
    issues = moderate("Мёд липовый", "", {"notes": "органический мёд"}, "мёд липовый масса 500 г", None, None)
    assert [issue["rule"] for issue in issues] == ["unsupported_claim"]


def test_description_with_new_number_or_claim_fails():
    facts = "- Масса: 500 г\n- Состав: мёд липовый"
    assert problems("Липовый мёд, 500 г.", facts, "мёд липовый 500 г") == []
    assert problems("Липовый мёд, 450 г, натуральный продукт.", facts, "мёд липовый 500 г")


def test_readiness_counts_missing_fields():
    spec = {"name": {"title": "Название", "kind": "text", "required": True},
            "shelf_life": {"title": "Срок годности", "kind": "duration", "required": True}}
    fields = {"name": {"source": "photo", "confidence": 0.9}, "shelf_life": {"source": "none", "confidence": 0.0}}
    score, missing = readiness(fields, spec, [{"passed": True, "message": ""}], [{"passed": True, "message": ""}], 0.6)
    assert score["score"] == 70
    assert missing[0]["field"] == "shelf_life"

def test_store_keeps_status_from_column(tmp_path):
    store = Store(tmp_path)
    draft_id, _ = store.new({})
    data = store.get(draft_id)
    store.put(draft_id, {**data, "error": "boom"}, "failed")
    assert store.get(draft_id)["status"] == "failed"


def test_verified_name_outweighs_stray_label_words():
    classifier = Classifier({"keyword_weight": 0.3, "name_weight": 0.6}, load_categories())
    classifier.image_scores = lambda paths: {key: 1 / len(classifier.categories) for key in classifier.categories}
    label = "хлопья пшенные варить на молоке молочную кашу"
    assert classifier.classify([], label)["key"] == "dairy"
    assert classifier.classify([], label, "Хлопья пшенные не требующие варки")["key"] == "grocery"