
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from models.severity_predictor import FEATURES, train_model
import pandas as pd
import numpy as np


def test_model_on_held_out_synthetic_data():
    rng = np.random.default_rng(42)
    size = 2000

    data = pd.DataFrame({
        "affected_people": rng.integers(0, 10001, size),
        "rainfall_mm": rng.uniform(0, 300, size),
        "wind_speed_kmph": rng.uniform(0, 180, size),
        "water_level_m": rng.uniform(0, 10, size),
    })

    score = (
        (data["affected_people"] >= 3000).astype(int)
        + (data["rainfall_mm"] >= 150).astype(int)
        + (data["wind_speed_kmph"] >= 100).astype(int)
        + (data["water_level_m"] >= 5).astype(int)
    )

    data["severity"] = np.select(
        [score >= 3, score >= 2],
        ["High", "Medium"],
        default="Low",
    )

    X_train, X_test, y_train, y_test = train_test_split(
        data[FEATURES],
        data["severity"],
        test_size=0.2,
        random_state=42,
        stratify=data["severity"],
    )

    model = train_model()
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(
        y_test,
        predictions,
        labels=["Low", "Medium", "High"],
        zero_division=0,
    )

    print(f"\nSynthetic held-out accuracy: {accuracy:.3f}")
    print(report)

    assert 0 <= accuracy <= 1
    assert set(predictions).issubset({"Low", "Medium", "High"})
