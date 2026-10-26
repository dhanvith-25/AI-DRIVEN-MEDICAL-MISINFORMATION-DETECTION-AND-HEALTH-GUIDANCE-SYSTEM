import csv
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from app.db import get_symptom_mapping, save_symptom_mapping


DISCLAIMER = "This is not a medical diagnosis. Please consult a doctor. Results may be inaccurate."

DISEASE_PROFILES: dict[str, dict[str, str]] = {
    "Allergic rhinitis": {
        "risk_level": "low",
        "prevention": "Avoid known allergens when possible and discuss persistent symptoms with a healthcare professional.",
        "explanation": "Allergic rhinitis is an immune response to airborne allergens and can cause sneezing, nasal symptoms, and itchy or watery eyes.",
    },
    "Asthma": {
        "risk_level": "high",
        "prevention": "Follow your clinician's asthma plan and avoid known triggers. Seek urgent care for severe or worsening breathing difficulty.",
        "explanation": "Asthma can narrow and inflame the airways, causing wheezing, chest tightness, cough, or shortness of breath.",
    },
    "Common cold": {
        "risk_level": "low",
        "prevention": "Rest, drink fluids, wash hands often, and limit close contact while unwell. Contact a clinician if symptoms worsen or persist.",
        "explanation": "A common cold is a viral upper-respiratory infection that may cause a runny nose, cough, and sore throat.",
    },
    "Dehydration": {
        "risk_level": "medium",
        "prevention": "Drink fluids regularly. Seek medical advice for persistent vomiting, confusion, fainting, or inability to keep fluids down.",
        "explanation": "Dehydration occurs when the body loses more fluid than it takes in and may cause thirst, dizziness, and dark urine.",
    },
    "Gastroenteritis": {
        "risk_level": "medium",
        "prevention": "Wash hands carefully, use safe food and water, and replace fluids. Seek care for severe pain, blood, or dehydration signs.",
        "explanation": "Gastroenteritis irritates the stomach and intestines and can cause nausea, vomiting, diarrhea, or abdominal discomfort.",
    },
    "Influenza": {
        "risk_level": "medium",
        "prevention": "Stay home while feverish, wash hands, and discuss vaccination and treatment options with a healthcare professional.",
        "explanation": "Influenza is a viral respiratory illness that can cause fever, chills, body aches, cough, and fatigue.",
    },
    "Migraine": {
        "risk_level": "medium",
        "prevention": "Rest in a quiet, dark room and note possible triggers. Seek urgent care for a sudden severe headache or new neurological symptoms.",
        "explanation": "Migraine is a neurological condition that can cause recurring headache, nausea, and sensitivity to light or sound.",
    },
    "Sinusitis": {
        "risk_level": "low",
        "prevention": "Rest, drink fluids, and seek medical advice for severe symptoms, worsening pain, or symptoms that do not improve.",
        "explanation": "Sinusitis is inflammation of the sinuses and may cause facial pressure, congestion, and headache.",
    },
    "Strep throat": {
        "risk_level": "medium",
        "prevention": "Avoid sharing drinks and wash hands. A clinician can determine whether testing or treatment is needed.",
        "explanation": "Strep throat is a bacterial throat infection that may cause sore throat, fever, and pain with swallowing.",
    },
}

SYMPTOM_DATASET = Path(__file__).resolve().parents[2] / "data" / "symptom_examples.csv"


@lru_cache(maxsize=1)
def _load_classifier_examples() -> tuple[tuple[str, str], ...]:
    with SYMPTOM_DATASET.open(newline="", encoding="utf-8") as dataset_file:
        rows = csv.DictReader(dataset_file)
        examples = tuple(
            (row["text"].strip(), row["label"].strip())
            for row in rows
            if row.get("text", "").strip() and row.get("label", "").strip()
        )

    if not examples:
        raise ValueError(f"Symptom dataset is empty: {SYMPTOM_DATASET}")
    return examples

SYMPTOM_RULES: dict[str, list[str]] = {
    "Common cold": ["runny nose", "cough", "sneezing", "mild fever", "sore throat", "fatigue"],
    "Influenza / flu": ["fever", "body aches", "chills", "cough", "fatigue", "headache"],
    "Allergic reaction": ["sneezing", "itchy eyes", "runny nose", "watery eyes", "cough"],
    "Strep throat": ["sore throat", "fever", "swollen glands", "pain when swallowing"],
    "Asthma / breathing irritation": ["wheezing", "shortness of breath", "chest tightness", "cough"],
    "Dehydration": ["dry mouth", "dizziness", "fatigue", "dark urine", "nausea", "thirst"],
    "Migraine": ["headache", "nausea", "light sensitivity", "sensitivity to sound"],
    "Gastrointestinal illness": ["nausea", "vomiting", "stomach pain", "diarrhea", "bloating"],
    "Sinus infection": ["facial pain", "nasal congestion", "headache", "fever", "pressure in face"],
}


def _normalize_phrase(value: str) -> str:
    return re.sub(r"[^a-z0-9\s-]", " ", (value or "").lower()).strip()


def _parse_symptoms(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[,;\n]+|\band\b", text)
    cleaned: list[str] = []
    for part in parts:
        normalized = _normalize_phrase(part)
        if normalized:
            cleaned.append(normalized)
    return cleaned


def _canonical_symptoms(symptoms: Iterable[str]) -> str:
    return ", ".join(sorted(set(symptom for symptom in symptoms if symptom)))


@lru_cache(maxsize=1)
def _load_dataset_index() -> tuple[
    dict[str, float], tuple[dict[str, float], ...], tuple[str, ...]
]:
    classifier_examples = _load_classifier_examples()
    documents = [Counter(_text_features(text)) for text, _ in classifier_examples]
    labels = tuple(label for _, label in classifier_examples)
    document_frequency = Counter(
        feature for document in documents for feature in document
    )
    document_count = len(documents)
    inverse_document_frequency = {
        feature: math.log((1 + document_count) / (1 + frequency)) + 1
        for feature, frequency in document_frequency.items()
    }
    example_vectors = tuple(
        _normalized_tfidf(document, inverse_document_frequency)
        for document in documents
    )
    return inverse_document_frequency, example_vectors, labels


def _predict_disease(symptom_text: str) -> dict[str, Any] | None:
    inverse_document_frequency, example_vectors, labels = _load_dataset_index()
    query_vector = _normalized_tfidf(
        Counter(_text_features(symptom_text)), inverse_document_frequency
    )
    if not query_vector:
        return None

    similarities = [
        sum(
            weight * vector.get(feature, 0.0)
            for feature, weight in query_vector.items()
        )
        for vector in example_vectors
    ]
    best_index = max(range(len(similarities)), key=similarities.__getitem__)
    disease = labels[best_index]
    profile = DISEASE_PROFILES.get(
        disease,
        {
            "risk_level": "medium",
            "prevention": "This dataset match is not a diagnosis. Consult a healthcare professional, especially if symptoms are severe or worsening.",
            "explanation": (
                f"The symptom dataset matched this input to {disease}; "
                "symptoms alone cannot confirm this condition."
            ),
        },
    )
    return {
        "cause": disease,
        "risk_level": profile["risk_level"],
        "prevention": profile["prevention"],
        "explanation": profile["explanation"],
        "confidence": min(max(float(similarities[best_index]), 0.0), 1.0),
    }


def _text_features(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return words + [f"{first} {second}" for first, second in zip(words, words[1:])]


def _normalized_tfidf(
    term_counts: Counter[str], inverse_document_frequency: dict[str, float]
) -> dict[str, float]:
    weighted = {
        feature: count * inverse_document_frequency[feature]
        for feature, count in term_counts.items()
        if feature in inverse_document_frequency
    }
    magnitude = math.sqrt(sum(weight * weight for weight in weighted.values()))
    if not magnitude:
        return {}
    return {feature: weight / magnitude for feature, weight in weighted.items()}


def _match_causes(symptoms: Iterable[str]) -> list[dict[str, Any]]:
    symptom_list = [sym for sym in symptoms if sym]
    matched: list[dict[str, Any]] = []
    seen: set[str] = set()

    for cause, keywords in SYMPTOM_RULES.items():
        matched_keywords = [sym for sym in symptom_list if any(sym in keyword or keyword in sym for keyword in keywords)]
        if not matched_keywords:
            continue

        if cause in seen:
            continue
        seen.add(cause)

        confidence = "high" if len(matched_keywords) >= 2 else "medium"
        matched.append({
            "cause": cause,
            "confidence": confidence,
            "matched_symptoms": sorted(set(matched_keywords)),
        })

    matched.sort(key=lambda item: (0 if item["confidence"] == "high" else 1, item["cause"]))
    return matched


def symptom_checker(
    symptoms: str = "",
    report_text: str = "",
    report_status: str = "No report provided",
) -> dict[str, Any]:
    manual_symptoms = _parse_symptoms(symptoms)
    all_symptoms = manual_symptoms

    canonical_symptoms = _canonical_symptoms(all_symptoms)
    prediction_text = " ".join(
        text.strip()
        for text in (symptoms, report_text)
        if text and text.strip()
    )
    mapping = (
        get_symptom_mapping(canonical_symptoms)
        if canonical_symptoms and not report_text
        else None
    )
    prediction: dict[str, Any] | None = None
    analysis_method = "symptoms_db"

    if mapping:
        prediction = {
            "cause": mapping["mapped_disease"],
            "risk_level": mapping["risk_level"],
            "prevention": mapping["prevention_notes"],
            "explanation": mapping["explanation"],
            "confidence": 1.0,
        }
    elif prediction_text:
        analysis_method = "dataset"
        prediction = _predict_disease(prediction_text)

        if prediction and not report_text:
            try:
                save_symptom_mapping(
                    canonical_symptoms,
                    prediction["cause"],
                    prediction["risk_level"],
                    prediction["prevention"],
                    prediction["explanation"],
                )
            except Exception:
                pass

    if prediction is None:
        if all_symptoms or report_text:
            cause = "Unable to determine"
            risk_level = "medium"
            prevention = "The symptom dataset did not provide a reliable match. Please ask a healthcare professional to interpret the report and symptoms."
            explanation = (
                "No symptom terms matched the available dataset examples. "
                "This tool does not clinically interpret laboratory results."
            )
            summary = f"{prevention} {DISCLAIMER}"
            suggested_causes: list[dict[str, Any]] = []
        else:
            cause = "No symptoms provided"
            risk_level = "low"
            prevention = "Enter symptoms to receive an assessment."
            explanation = "No symptoms were provided."
            summary = f"{prevention} {DISCLAIMER}"
            suggested_causes = []
    else:
        cause = prediction["cause"]
        risk_level = prediction["risk_level"]
        prevention = prediction["prevention"]
        explanation = prediction["explanation"]
        confidence = float(prediction.get("confidence", 0.0))
        suggested_causes = [{
            "cause": cause,
            "confidence": "high" if confidence >= 0.75 else "medium" if confidence >= 0.45 else "low",
            "matched_symptoms": all_symptoms,
        }]
        summary = f"Possible cause: {cause}. {prevention} {DISCLAIMER}"

    return {
        "cause": cause,
        "prevention": prevention,
        "risk_level": risk_level,
        "disclaimer": DISCLAIMER,
        "explanation": explanation,
        "analysis_method": analysis_method,
        "report_text": report_text,
        "report_status": report_status,
        "manual_symptoms": manual_symptoms,
        "detected_symptoms": all_symptoms,
        "suggested_causes": suggested_causes,
        "summary": summary,
    }
