"""Inference helpers for saved CSV pipelines."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _json_value(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


def predict_with_pipeline(pipeline, input_frame: pd.DataFrame) -> dict:
    prediction = pipeline.predict(input_frame)[0]
    result = {
        "predicted_class": _json_value(prediction),
        "predicted_value": _json_value(prediction),
        "probability": None,
        "probabilities": {},
    }
    if hasattr(pipeline, "predict_proba"):
        probabilities = pipeline.predict_proba(input_frame)[0]
        classifier = pipeline.named_steps.get("classifier") or pipeline.named_steps.get("estimator")
        labels = getattr(classifier, "classes_", [])
        result["probabilities"] = {
            str(_json_value(label)): float(probability)
            for label, probability in zip(labels, probabilities)
        }
        result["probability"] = result["probabilities"].get(
            str(_json_value(prediction)),
        )
    return result
