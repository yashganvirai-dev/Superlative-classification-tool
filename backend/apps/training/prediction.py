"""Dynamic prediction schema and saved-pipeline inference."""

import hashlib
import math
from pathlib import Path

import joblib
import pandas as pd
from django.core.exceptions import ObjectDoesNotExist

from apps.datasets.services import load_dataset_dataframe, resolve_dataset_path
from apps.models.models import MLModel, ModelStatus
from ml.csv.predictor import predict_with_pipeline

from .services import artifact_path_for_model


class PredictionError(Exception):
    """Raised when prediction input or artifact state is invalid."""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_model_metadata(model: MLModel) -> dict:
    if model.status != ModelStatus.TRAINED or not model.artifact_reference:
        raise PredictionError("The model is not trained and cannot make predictions.")
    try:
        dataset = model.dataset
    except ObjectDoesNotExist as exc:
        raise PredictionError("The training dataset is unavailable.") from exc

    metadata = dict(model.metadata or {})
    target_column = metadata.get("target_column")
    if not target_column or dataset.target_column != target_column:
        raise PredictionError(
            "The dataset target no longer matches the trained model. Retrain before predicting."
        )
    dataset_metadata = metadata.get("dataset") or {}
    if dataset_metadata.get("sha256") != dataset.sha256:
        raise PredictionError(
            "The training dataset changed after training. Retrain before predicting."
        )
    dataset_path = resolve_dataset_path(dataset.storage_path)
    if not dataset_path.is_file() or _file_sha256(dataset_path) != dataset.sha256:
        raise PredictionError("The training dataset is unavailable or has changed.")
    if not metadata.get("features"):
        raise PredictionError("Prediction feature metadata is unavailable.")

    expected_reference, artifact_path = artifact_path_for_model(model)
    if model.artifact_reference != expected_reference or not artifact_path.is_file():
        raise PredictionError("The trained model artifact is unavailable.")
    return metadata


def _load_artifact(model: MLModel):
    _validated_model_metadata(model)
    _, path = artifact_path_for_model(model)
    try:
        return joblib.load(path)
    except Exception as exc:
        raise PredictionError("The trained model artifact could not be loaded.") from exc


def prediction_schema(model: MLModel) -> dict:
    metadata = _validated_model_metadata(model)
    sample_values = {}
    try:
        dataset = model.dataset
        dataframe = load_dataset_dataframe(dataset)
        target_column = metadata["target_column"]
        for feature in metadata["features"]:
            name = feature["name"]
            if name not in dataframe.columns or name == target_column:
                continue
            series = dataframe[name].dropna()
            if series.empty:
                continue
            if feature["type"] == "numerical":
                sample_values[name] = float(series.median())
            elif feature.get("categories"):
                categories = {str(value) for value in feature["categories"]}
                represented = series.astype(str)
                matching = represented[represented.isin(categories)]
                sample_values[name] = str(matching.iloc[0]) if not matching.empty else str(feature["categories"][0])
            else:
                sample_values[name] = str(series.mode().iloc[0]) if not series.mode().empty else ""
    except Exception as exc:
        raise PredictionError("A sample prediction value could not be generated.") from exc

    return {
        "model_id": model.id,
        "target_column": metadata["target_column"],
        "features": metadata["features"],
        "sample_values": sample_values,
    }


def _validate_features(model: MLModel, values: dict) -> pd.DataFrame:
    schema = prediction_schema(model).get("features", [])
    expected = {feature["name"] for feature in schema}
    unknown = set(values) - expected
    missing_required = {
        feature["name"]
        for feature in schema
        if feature.get("required", True) and feature["name"] not in values
    }
    if unknown:
        raise PredictionError(f"Unexpected feature values: {', '.join(sorted(unknown))}.")
    if missing_required:
        raise PredictionError(
            f"Missing feature values: {', '.join(sorted(missing_required))}."
        )

    row = {}
    for feature in schema:
        name = feature["name"]
        value = values.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            if feature.get("required", True):
                raise PredictionError(f"{name} is required.")
            row[name] = None
            continue
        if feature["type"] == "numerical":
            if isinstance(value, bool):
                raise PredictionError(f"{name} must be numeric.")
            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as exc:
                raise PredictionError(f"{name} must be numeric.") from exc
            if not math.isfinite(numeric_value):
                raise PredictionError(f"{name} must be finite.")
            row[name] = numeric_value
        else:
            categories = feature.get("categories")
            if categories is None:
                raise PredictionError(
                    f"{name} has no category metadata and cannot be validated safely."
                )
            normalized_value = str(value).strip()
            if normalized_value not in [str(item) for item in categories]:
                raise PredictionError(f"{name} contains an unknown category.")
            row[name] = normalized_value
    return pd.DataFrame([row], columns=[feature["name"] for feature in schema])


def predict(model: MLModel, values: dict) -> dict:
    pipeline = _load_artifact(model)
    input_frame = _validate_features(model, values)
    try:
        result = predict_with_pipeline(pipeline, input_frame)
    except (ValueError, TypeError) as exc:
        raise PredictionError("The prediction values are incompatible with the trained pipeline.") from exc
    result["model_id"] = model.id
    result["model_name"] = model.name
    return result
