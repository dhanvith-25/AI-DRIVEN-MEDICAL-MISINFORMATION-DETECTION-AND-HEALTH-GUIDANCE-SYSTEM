from app.services import symptom_checker as checker


def test_symptom_checker_matches_dataset_example_locally(monkeypatch):
    monkeypatch.setattr(checker, "get_symptom_mapping", lambda symptoms: None)
    monkeypatch.setattr(checker, "save_symptom_mapping", lambda *args: None)

    result = checker.symptom_checker(
        symptoms="fever muscle pain and yellow eyes after contact with floodwater"
    )

    assert result["cause"] == "Leptospirosis"
    assert result["analysis_method"] == "dataset"
    assert result["risk_level"] == "medium"
    assert "not a diagnosis" in result["prevention"]
    assert result["suggested_causes"][0]["cause"] == "Leptospirosis"
