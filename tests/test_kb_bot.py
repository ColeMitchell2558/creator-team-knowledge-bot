from src.kb_bot import choose_update


def test_choose_update_prefers_strongest_article():
    matches = [
        {"score": 0.61, "metadata": {"topic": "Delivery", "text": "Links last 72 hours."}},
        {"score": 0.88, "metadata": {"topic": "Updates", "text": "Sent every Friday."}},
    ]
    assert choose_update("When is the update?", matches) == "Updates: Sent every Friday."


def test_choose_update_is_explicit_when_evidence_is_weak():
    assert choose_update("Unknown", [{"score": 0.2, "metadata": {"text": "Maybe"}}]).startswith("I could not")
