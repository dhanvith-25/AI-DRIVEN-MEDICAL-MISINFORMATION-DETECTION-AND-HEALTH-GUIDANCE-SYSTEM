from __future__ import annotations

import asyncio
import io
import shutil
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

import app.db as db
from app.dataset import get_top_k_matches, refresh_index
from app.services import evidence_reasoner, health_model, personal_records, symptom_checker


def test_symptom_parser_splits_and_normalizes_phrases():
    assert symptom_checker._parse_symptoms("  Fever, muscle-pain\nand cough! ") == [
        "fever",
        "muscle-pain",
        "cough",
    ]


def test_symptom_normalization_sorts_deduplicates_and_joins():
    assert symptom_checker._canonical_symptoms(["cough", "fever", "cough", ""]) == (
        "cough, fever"
    )


def test_symptom_dataset_prediction_matches_existing_floodwater_example(monkeypatch):
    monkeypatch.setattr(symptom_checker, "get_symptom_mapping", lambda _: None)
    monkeypatch.setattr(symptom_checker, "save_symptom_mapping", lambda *args: None)

    result = symptom_checker.symptom_checker(
        symptoms="fever muscle pain and yellow eyes after contact with floodwater"
    )

    assert result["cause"] == "Leptospirosis"
    assert result["analysis_method"] == "dataset"
    assert result["risk_level"] == "medium"


def test_symptom_response_keeps_disclaimer_and_profile_risk(monkeypatch):
    monkeypatch.setattr(symptom_checker, "get_symptom_mapping", lambda _: None)
    monkeypatch.setattr(symptom_checker, "save_symptom_mapping", lambda *args: None)
    monkeypatch.setattr(
        symptom_checker,
        "_predict_disease",
        lambda _: {
            "cause": "Asthma",
            "risk_level": "high",
            "prevention": "Follow the clinician's asthma plan.",
            "explanation": "Possible airway symptoms.",
            "confidence": 0.9,
        },
    )

    result = symptom_checker.symptom_checker("wheezing and chest tightness")

    assert result["risk_level"] == "high"
    assert result["disclaimer"] == symptom_checker.DISCLAIMER


def test_unmatched_symptoms_return_cautious_fallback(monkeypatch):
    monkeypatch.setattr(symptom_checker, "get_symptom_mapping", lambda _: None)
    monkeypatch.setattr(symptom_checker, "save_symptom_mapping", lambda *args: None)
    monkeypatch.setattr(symptom_checker, "_predict_disease", lambda _: None)

    result = symptom_checker.symptom_checker("unrecognized symptom phrase")

    assert result["cause"] == "Unable to determine"
    assert result["risk_level"] == "medium"
    assert result["suggested_causes"] == []
    assert "not a medical diagnosis" in result["disclaimer"].lower()


def test_report_text_normalization_removes_blank_lines_and_extra_spacing():
    assert personal_records.normalize_text(" Name:\tAsha \r\n\r\nValue:  98 ") == (
        "Name: Asha\nValue: 98"
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Fasting blood sugar glucose result", "Blood Sugar"),
        ("HbA1c glycated hemoglobin", "HbA1c"),
        ("Complete blood count CBC platelet", "Complete Blood Count (CBC)"),
        ("25 hydroxy vitamin D total", "Vitamin D"),
        ("Lipid profile cholesterol HDL LDL", "Lipid Profile"),
        ("Thyroid profile TSH free T4", "Thyroid Function"),
        ("Liver function bilirubin SGPT", "Liver Function"),
        ("Kidney renal creatinine eGFR", "Kidney Function"),
        ("Iron studies ferritin TIBC", "Iron Studies"),
        ("Urinalysis urine protein", "Urine Analysis"),
    ],
)
def test_report_classification_seeded_categories(text, expected):
    label, confidence = personal_records.classify_test_type(text)
    assert label == expected
    assert 0 < confidence <= 100


def test_measurement_extraction_includes_value_unit_reference_and_flag():
    result = personal_records.extract_measurements(
        "Fasting Glucose 110 mg/dL 70 - 99 H\nVitamin D: 25 ng/mL 30 - 100 L"
    )
    assert [(row["test_name"], row["value_num"], row["unit"], row["status"]) for row in result] == [
        ("Fasting Glucose", 110.0, "mg/dL", "high"),
        ("Vitamin D", 25.0, "ng/mL", "low"),
    ]


@pytest.mark.parametrize(
    ("raw", "bounds"),
    [
        ("70 - 99", (70.0, 99.0)),
        ("30 to 100", (30.0, 100.0)),
        ("< 5", (None, 5.0)),
        (">= 3.5", (3.5, None)),
        ("", (None, None)),
    ],
)
def test_reference_range_parsing(raw, bounds):
    assert personal_records.parse_reference_range(raw) == bounds


def test_report_details_extract_metadata_and_date():
    details = personal_records.extract_report_details(
        "Patient Name: Asha Rao\nReferring Doctor: Dr Mehta\n"
        "Report Date: 20/09/2026\nTest Name: Fasting Glucose\nGlucose: 95 mg/dL",
        "Blood Sugar",
    )
    assert details["patient_name"] == "Asha Rao"
    assert details["doctor_name"] == "Dr Mehta"
    assert details["reported_date"] == "2026-09-20"
    assert details["test_name"] == "Fasting Glucose"
    assert details["measurements"][0]["value_num"] == 95.0


def _text_pdf(text: str) -> bytes:
    content = f"BT /F1 16 Tf 40 250 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(content)).encode("ascii")
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def test_pdf_text_extraction_reads_a_synthetic_text_pdf():
    text, method = personal_records.extract_report_text_from_bytes(
        _text_pdf("Glucose: 95 mg/dL"), ".pdf"
    )
    assert text == "Glucose: 95 mg/dL"
    assert method == "pdf_text"


def test_image_ocr_extracts_synthetic_lab_text():
    import pytesseract

    if not shutil.which(pytesseract.pytesseract.tesseract_cmd):
        pytest.skip("Tesseract executable is not available on PATH.")
    image = Image.new("RGB", (1500, 240), "white")
    draw = ImageDraw.Draw(image)
    font_path = r"C:\Windows\Fonts\arial.ttf"
    font = ImageFont.truetype(font_path, 72)
    draw.text((40, 45), "Glucose 95 mg/dL", fill="black", font=font)
    raw = io.BytesIO()
    image.save(raw, format="PNG")

    text, method = personal_records.extract_report_text_from_bytes(
        raw.getvalue(), ".png"
    )

    assert method == "tesseract_ocr"
    assert "glucose" in text.lower()
    assert "95" in text


def test_database_symptom_mapping_upserts_and_reads(tmp_path, monkeypatch):
    monkeypatch.setattr(
        db, "settings", lambda: SimpleNamespace(db_path=str(tmp_path / "unit.db"))
    )
    db.init_db()
    db.save_symptom_mapping("Cough, fever", "Influenza", "MEDIUM", "Rest.", "Possible flu.")
    db.save_symptom_mapping("cough, fever", "Influenza", "high", "Seek care.", "Updated.")

    result = db.get_symptom_mapping("COUGH, FEVER")

    assert result["mapped_disease"] == "Influenza"
    assert result["risk_level"] == "high"
    assert result["prevention_notes"] == "Seek care."


def test_personal_report_database_persistence_and_cascade(tmp_path, monkeypatch):
    monkeypatch.setattr(
        db, "settings", lambda: SimpleNamespace(db_path=str(tmp_path / "reports.db"))
    )
    db.init_db()
    report = db.create_personal_report(
        {
            "original_filename": "synthetic.pdf",
            "stored_path": str(tmp_path / "synthetic.pdf"),
            "file_size": 123,
            "extracted_text": "Glucose 95 mg/dL",
            "extraction_method": "pdf_text",
            "test_type": "Blood Sugar",
        },
        [{"test_name": "Glucose", "value_raw": "95", "value_num": 95, "unit": "mg/dL"}],
    )
    assert db.get_personal_report(report["id"])["measurements"][0]["value_num"] == 95
    assert len(db.list_personal_reports(query="glucose")) == 1

    db.delete_personal_report(report["id"])

    assert db.get_personal_report(report["id"]) is None
    assert db.personal_reports_summary()["total_measurements"] == 0


def test_faiss_index_ranks_expected_local_claim_without_downloading_model(
    tmp_path, monkeypatch
):
    import app.dataset as dataset

    monkeypatch.setattr(
        db, "settings", lambda: SimpleNamespace(db_path=str(tmp_path / "faiss.db"))
    )
    monkeypatch.setattr(dataset, "INDEX_FILE", tmp_path / "index.bin")
    monkeypatch.setattr(dataset, "METADATA_FILE", tmp_path / "metadata.pkl")

    class FixedEncoder:
        def encode(self, texts, **_kwargs):
            vectors = []
            for text in texts:
                lower = text.lower()
                vectors.append(
                    [1.0, 0.0]
                    if "vaccine" in lower or "vaccination" in lower
                    else [0.0, 1.0]
                )
            return np.asarray(vectors, dtype=np.float32)

    monkeypatch.setattr(dataset, "get_model", FixedEncoder)
    db.init_db()
    db.upsert_claim(
        "Vaccination reduces severe disease risk.",
        "Vaccines can reduce severe disease risk.",
        "SUPPORTED",
        96,
        [],
        "test",
    )
    db.upsert_claim(
        "Drinking water helps maintain hydration.",
        "Water supports hydration.",
        "SUPPORTED",
        90,
        [],
        "test",
    )
    refresh_index()

    matches = get_top_k_matches("Does vaccination help?", k=2)

    assert matches[0]["canonical_claim"].startswith("Vaccination")
    assert matches[0]["similarity_score"] == pytest.approx(1.0)
    assert matches[0]["verdict"] == "SUPPORTED"


def test_claim_classifier_applies_confidence_threshold(monkeypatch):
    class FixedModel:
        classes_ = np.asarray(["CONTRADICTED", "SUPPORTED"])

        def predict_proba(self, _texts):
            return np.asarray([[0.9, 0.1]])

    monkeypatch.setattr(health_model, "_load_model", lambda: FixedModel())

    result = health_model.predict_health_claim("Antibiotics cure the common cold")

    assert result["verdict"] == "CONTRADICTED"
    assert 0 <= result["confidence"] <= 100


def test_evidence_reasoner_abstains_when_search_returns_no_sources(monkeypatch):
    async def no_sources(_):
        return []

    monkeypatch.setattr(evidence_reasoner, "search", no_sources)
    monkeypatch.setattr(
        evidence_reasoner,
        "predict_health_claim",
        lambda claim: {
            "claim": claim,
            "verdict": "SUPPORTED",
            "confidence": 88.0,
            "probabilities": {},
            "model": "test",
        },
    )

    result = asyncio.run(evidence_reasoner.reason_about_claim("Water is healthy"))

    assert result["verdict"] == "UNCERTAIN"
    assert result["evidence_sources"] == []
    assert "No external evidence" in result["warning"]
