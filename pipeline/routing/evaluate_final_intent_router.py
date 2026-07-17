"""One-shot acceptance evaluation for the frozen intent router."""

import hashlib
import json
import sys
from pathlib import Path

import joblib
from sklearn.metrics import classification_report, confusion_matrix

sys.path.insert(0, str(Path(__file__).parent.parent))

from routing.final_intent_test_cases_v3 import FINAL_INTENT_CASES_V3
from routing.intent_normalizer import normalize_intent_text
from routing.intent_training_data import TRAIN_DATA


ROUTING_DIR = Path(__file__).parent
ARTIFACT = ROUTING_DIR / "intent_router.joblib"
REPORT = ROUTING_DIR / "final_intent_evaluation_v3.json"
LABELS = ["standard", "procedural", "comparison", "troubleshooting"]
MIN_MACRO_F1 = 0.90
MIN_CLASS_RECALL = 0.90


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    train_text = {text for text, _ in TRAIN_DATA}
    test_text = {text for text, _ in FINAL_INTENT_CASES_V3}
    exact_overlap = sorted(train_text & test_text)
    normalized_overlap = sorted(
        {normalize_intent_text(text) for text in train_text}
        & {normalize_intent_text(text) for text in test_text}
    )
    if exact_overlap or normalized_overlap:
        raise RuntimeError(
            f"train/test overlap: exact={exact_overlap}, "
            f"normalized={normalized_overlap}"
        )

    classifier = joblib.load(ARTIFACT)
    questions = [question for question, _ in FINAL_INTENT_CASES_V3]
    expected = [label for _, label in FINAL_INTENT_CASES_V3]
    predicted = classifier.predict(questions).tolist()
    probabilities = classifier.predict_proba(questions)

    metrics = classification_report(
        expected,
        predicted,
        labels=LABELS,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(expected, predicted, labels=LABELS).tolist()
    failures = []
    for question, wanted, actual, probs in zip(
        questions, expected, predicted, probabilities
    ):
        if wanted != actual:
            failures.append({
                "question": question,
                "expected": wanted,
                "predicted": actual,
                "confidence": round(float(max(probs)), 6),
            })

    macro_f1 = metrics["macro avg"]["f1-score"]
    recalls = {label: metrics[label]["recall"] for label in LABELS}
    accepted = (
        macro_f1 >= MIN_MACRO_F1
        and all(value >= MIN_CLASS_RECALL for value in recalls.values())
    )
    result = {
        "accepted": accepted,
        "thresholds": {
            "minimum_macro_f1": MIN_MACRO_F1,
            "minimum_class_recall": MIN_CLASS_RECALL,
        },
        "sample_count": len(FINAL_INTENT_CASES_V3),
        "class_order": LABELS,
        "confusion_matrix": matrix,
        "metrics": metrics,
        "failures": failures,
        "artifact_sha256": sha256(ARTIFACT),
        "test_set_sha256": sha256(Path(__file__).with_name(
            "final_intent_test_cases_v3.py"
        )),
        "exact_train_test_overlap": exact_overlap,
        "normalized_train_test_overlap": normalized_overlap,
    }
    REPORT.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"samples: {len(FINAL_INTENT_CASES_V3)}")
    print(f"macro-F1: {macro_f1:.3f}")
    for label in LABELS:
        print(
            f"{label:16} precision={metrics[label]['precision']:.3f} "
            f"recall={metrics[label]['recall']:.3f} "
            f"f1={metrics[label]['f1-score']:.3f}"
        )
    print("confusion matrix (rows=expected, columns=predicted):")
    print("labels:", LABELS)
    for row in matrix:
        print(row)
    print(f"failures: {len(failures)}")
    for failure in failures:
        print(
            f"[{failure['expected']}->{failure['predicted']} "
            f"@{failure['confidence']:.2f}] {failure['question']}"
        )
    print("ACCEPTED" if accepted else "REJECTED")
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
