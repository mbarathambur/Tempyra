
import math

import pytest

from models.severity_predictor import predict_severity


VALID_SEVERITIES = {"Low", "Medium", "High"}


def test_prediction_output():
    result = predict_severity(
        affected_people=5000,
        rainfall_mm=200,
        wind_speed_kmph=120,
        water_level_m=7,
    )

    assert result["predicted_severity"] in VALID_SEVERITIES
    assert 0 <= result["model_confidence"] <= 1
    assert result["model_type"] == "Random Forest"
    assert "Synthetic" in result["data_type"]


def test_negative_input_rejected():
    with pytest.raises(ValueError):
        predict_severity(-10, 100, 50, 2)


@pytest.mark.parametrize(
    "values",
    [
        (float("nan"), 100, 50, 2),
        (100, float("inf"), 50, 2),
        (100, 100, float("-inf"), 2),
        (100, 100, 50, -1),
    ],
)
def test_invalid_input_rejected(values):
    with pytest.raises(ValueError):
        predict_severity(*values)


@pytest.mark.parametrize(
    "values",
    [
        ("invalid", 100, 50, 2),
        (100, None, 50, 2),
    ],
)
def test_non_numeric_input_rejected(values):
    with pytest.raises((ValueError, TypeError)):
        predict_severity(*values)


def test_prediction_is_reproducible():
    values = (5000, 200, 120, 7)

    first = predict_severity(*values)
    second = predict_severity(*values)

    assert first["predicted_severity"] == second["predicted_severity"]
    assert first["model_confidence"] == second["model_confidence"]


def test_zero_values_are_accepted():
    result = predict_severity(0, 0, 0, 0)

    assert result["predicted_severity"] in VALID_SEVERITIES
    assert math.isfinite(result["model_confidence"])
