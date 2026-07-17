"""Train the deterministic intent classifier and evaluate on the held-out
test cases. Frozen artifact: routing/intent_router.joblib.

Reproducibility: fixed random_state, fixed training data, pinned sklearn
version. Re-running produces an identical model.
"""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sklearn
import joblib
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from routing.intent_training_data import TRAIN_DATA
from routing.intent_normalizer import normalize_intent_text
from routing.test_intent_cases import INTENT_CASES

ARTIFACT = os.path.join(os.path.dirname(__file__), "intent_router.joblib")


def build_and_train():
    train_x = [q for q, _ in TRAIN_DATA]
    train_y = [y for _, y in TRAIN_DATA]
    clf = Pipeline([
        ("features", FeatureUnion([
            ("char", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                preprocessor=normalize_intent_text,
            )),
            ("word", TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 3),
                preprocessor=normalize_intent_text,
            )),
        ])),
        ("model", LogisticRegression(
            C=4.0,
            random_state=0,
            max_iter=1000,
            class_weight="balanced",
        )),
    ])
    clf.fit(train_x, train_y)
    return clf


def evaluate(clf):
    correct = 0
    failures = []
    for question, expected in INTENT_CASES:
        probs = clf.predict_proba([question])[0]
        classes = list(clf.classes_)
        best_i = int(probs.argmax())
        pred = classes[best_i]
        conf = float(probs[best_i])
        if pred == expected:
            correct += 1
        else:
            failures.append((question, expected, pred, conf))
    return correct, failures


if __name__ == "__main__":
    print("sklearn version:", sklearn.__version__)
    clf = build_and_train()
    joblib.dump(clf, ARTIFACT)
    h = hashlib.md5(open(ARTIFACT, "rb").read()).hexdigest()[:12]
    print("saved artifact:", ARTIFACT)
    print("artifact md5:", h)
    print()
    correct, failures = evaluate(clf)
    total = len(INTENT_CASES)
    print("TEST ACCURACY: %d/%d (%.0f%%)" % (correct, total, 100*correct/total))
    if failures:
        print("\nFAILURES (%d):" % len(failures))
        for q, exp, pred, conf in failures:
            print("  [%s->%s @%.2f] %s" % (exp, pred, conf, q))
