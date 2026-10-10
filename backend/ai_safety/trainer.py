"""
SafeHer AI Safety Model Trainer
--------------------------------
Uses a Decision Tree trained on SYNTHETIC demo data.
This model produces assistive safety indications only.
It does NOT predict crime or guarantee safety outcomes.

Run once:
    python -m backend.ai_safety.trainer
"""
import pathlib
import pandas as pd
import joblib
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from backend.ai_safety.features import FEATURE_NAMES

DATASET_PATH = pathlib.Path(__file__).parent / "dataset" / "demo_safety_dataset.csv"
MODEL_PATH = pathlib.Path(__file__).parent / "model_artifact.pkl"


def train():
    df = pd.read_csv(DATASET_PATH)

    X = df[FEATURE_NAMES]
    y = df["label"]

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    model = DecisionTreeClassifier(max_depth=5, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("=== SafeHer AI Model — Training Report ===")
    print(classification_report(y_test, y_pred, target_names=le.classes_))
    print(f"Classes: {list(le.classes_)}")

    joblib.dump({"model": model, "label_encoder": le}, MODEL_PATH)
    print(f"Model saved → {MODEL_PATH}")


if __name__ == "__main__":
    train()
