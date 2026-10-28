
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

FEATURES = [
    "affected_people",
    "rainfall_mm",
    "wind_speed_kmph",
    "water_level_m",
]

def train_model():
    # Synthetic data for prototype testing only
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

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(data[FEATURES], data["severity"])
    return model


_model = train_model()


def predict_severity(
    affected_people,
    rainfall_mm,
    wind_speed_kmph,
    water_level_m,
):
    values = [affected_people, rainfall_mm, wind_speed_kmph, water_level_m]

    if any(not np.isfinite(float(v)) or float(v) < 0 for v in values):
        raise ValueError("All input values must be finite and non-negative.")

    sample = pd.DataFrame([dict(zip(FEATURES, map(float, values)))])
    prediction = _model.predict(sample)[0]
    probabilities = _model.predict_proba(sample)[0]
    confidence = float(max(probabilities))

    return {
        "predicted_severity": prediction,
        "model_confidence": round(confidence, 3),
        "model_type": "Random Forest",
        "data_type": "Synthetic training data - demonstration only",
    }
