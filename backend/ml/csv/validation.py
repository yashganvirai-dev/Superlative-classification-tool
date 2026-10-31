"""Pure dataframe validation and metadata helpers for CSV classification."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


MIN_DATASET_ROWS = 2
MIN_TRAINING_ROWS = 10
MIN_CLASS_COUNT = 2
MAX_CLASSIFICATION_CLASSES = 50
MAX_CATEGORICAL_CARDINALITY = 100
DEFAULT_TEST_SIZE = 0.2
DEFAULT_PREVIEW_ROWS = 10


class DatasetValidationError(ValueError):
    """Raised when a dataframe cannot support the CSV workflow."""


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def detect_task(dataframe: pd.DataFrame, target_column: str) -> str:
    target = dataframe[target_column]
    unique_count = int(target.nunique(dropna=True))
    if _is_numeric(target):
        unique_ratio = unique_count / max(len(target.dropna()), 1)
        if unique_count <= 50 and unique_ratio <= 0.05:
            return "classification"
        return "regression"
    return "classification"


def validate_dataframe(
    dataframe: pd.DataFrame,
    *,
    min_rows: int = MIN_DATASET_ROWS,
    max_rows: int | None = None,
    max_columns: int | None = None,
) -> None:
    if dataframe is None or dataframe.empty:
        raise DatasetValidationError("The CSV does not contain any data rows.")
    if len(dataframe) < min_rows:
        raise DatasetValidationError(
            f"The CSV must contain at least {min_rows} data rows."
        )
    if max_rows is not None and len(dataframe) > max_rows:
        raise DatasetValidationError(f"The CSV exceeds the {max_rows}-row limit.")

    columns = list(dataframe.columns)
    if max_columns is not None and len(columns) > max_columns:
        raise DatasetValidationError(f"The CSV exceeds the {max_columns}-column limit.")
    if len(columns) < 2:
        raise DatasetValidationError("The CSV must contain a feature column and a target column.")

    normalized_columns = [str(column).strip() for column in columns]
    if any(not column for column in normalized_columns):
        raise DatasetValidationError("CSV column names cannot be blank.")
    if len(set(normalized_columns)) != len(normalized_columns):
        raise DatasetValidationError("CSV column names must be unique.")
    dataframe.columns = normalized_columns

    for column in dataframe.columns:
        series = dataframe[column]
        if series.isna().all():
            raise DatasetValidationError(f"Column '{column}' contains no usable values.")
        if _is_numeric(series):
            try:
                finite = all(math.isfinite(float(value)) for value in series.dropna())
            except (TypeError, ValueError) as exc:
                raise DatasetValidationError(
                    f"Column '{column}' contains a non-numeric value."
                ) from exc
            if not finite:
                raise DatasetValidationError(
                    f"Column '{column}' contains an infinite or invalid numeric value."
                )


def build_metadata(
    dataframe: pd.DataFrame,
    *,
    preview_rows: int = DEFAULT_PREVIEW_ROWS,
    task: str = "classification",
) -> dict:
    columns = []
    for column in dataframe.columns:
        series = dataframe[column]
        missing_count = int(series.isna().sum())
        counts = series.value_counts(dropna=True)
        columns.append(
            {
                "name": str(column),
                "dtype": str(series.dtype),
                "missing_count": missing_count,
                "missing_percentage": round(missing_count / len(dataframe), 4),
                "unique_count": int(series.nunique(dropna=True)),
                "minimum_frequency": int(counts.min()) if not counts.empty else 0,
            }
        )

    preview = [
        {str(key): _json_value(value) for key, value in row.items()}
        for row in dataframe.head(preview_rows).to_dict(orient="records")
    ]
    if task == "regression":
        target_candidates = [
            column["name"]
            for column in columns
            if column["missing_count"] == 0
            and pd.api.types.is_numeric_dtype(dataframe[column["name"]])
            and not pd.api.types.is_bool_dtype(dataframe[column["name"]])
        ]
    elif task == "auto":
        target_candidates = [
            column["name"]
            for column in columns
            if (
                column["missing_count"] == 0
                and (
                    (
                        pd.api.types.is_numeric_dtype(dataframe[column["name"]])
                        and not pd.api.types.is_bool_dtype(dataframe[column["name"]])
                    )
                    or (
                        MIN_CLASS_COUNT <= column["unique_count"] <= MAX_CLASSIFICATION_CLASSES
                        and column["minimum_frequency"] >= MIN_CLASS_COUNT
                    )
                )
            )
        ]
    else:
        target_candidates = [
            column["name"]
            for column in columns
            if MIN_CLASS_COUNT <= column["unique_count"] <= MAX_CLASSIFICATION_CLASSES
            and column["minimum_frequency"] >= MIN_CLASS_COUNT
            and column["missing_count"] == 0
        ]
    return {
        "columns": columns,
        "preview": preview,
        "target_candidates": target_candidates,
    }


def validate_target_column(
    dataframe: pd.DataFrame,
    target_column: str,
    *,
    test_size: float = DEFAULT_TEST_SIZE,
) -> None:
    validate_dataframe(dataframe, min_rows=MIN_TRAINING_ROWS)
    if target_column not in dataframe.columns:
        raise DatasetValidationError("The selected target column does not exist.")
    target = dataframe[target_column]
    if target.isna().any():
        raise DatasetValidationError("The target column cannot contain missing values.")
    class_counts = target.value_counts(dropna=True)
    class_count = int(class_counts.size)
    if class_count < 2:
        raise DatasetValidationError("The target column must contain at least two classes.")
    if class_count > MAX_CLASSIFICATION_CLASSES:
        raise DatasetValidationError(
            f"The target column contains too many classes for classification (maximum {MAX_CLASSIFICATION_CLASSES})."
        )
    if int(class_counts.min()) < MIN_CLASS_COUNT:
        raise DatasetValidationError(
            "Every target class must appear at least twice so it can be represented in training and evaluation data."
        )
    test_rows = max(1, int(len(dataframe) * test_size))
    train_rows = len(dataframe) - test_rows
    if test_rows < class_count or train_rows < class_count:
        raise DatasetValidationError(
            "The dataset is too small to represent every target class in both training and evaluation data."
        )

    feature_columns = [column for column in dataframe.columns if column != target_column]
    if not feature_columns:
        raise DatasetValidationError("At least one feature column is required for training.")
    for column in feature_columns:
        series = dataframe[column]
        if series.isna().all():
            raise DatasetValidationError(f"Feature '{column}' contains no usable values.")
        if not _is_numeric(series):
            unique_count = int(series.nunique(dropna=True))
            if unique_count > MAX_CATEGORICAL_CARDINALITY:
                raise DatasetValidationError(
                    f"Feature '{column}' has too many categories (maximum {MAX_CATEGORICAL_CARDINALITY}). Encode or aggregate it before training."
                )


def validate_regression_target(dataframe: pd.DataFrame, target_column: str, *, test_size: float = DEFAULT_TEST_SIZE) -> None:
    validate_dataframe(dataframe, min_rows=MIN_TRAINING_ROWS)
    if target_column not in dataframe.columns:
        raise DatasetValidationError("The selected target column does not exist.")
    target = dataframe[target_column]
    if target.isna().any() or not _is_numeric(target):
        raise DatasetValidationError("Regression targets must be numeric and cannot contain missing values.")
    test_rows = max(1, int(len(dataframe) * test_size))
    if test_rows < 1 or len(dataframe) - test_rows < 1:
        raise DatasetValidationError("The dataset is too small for training and evaluation.")
    if len(dataframe.columns) < 2:
        raise DatasetValidationError("At least one feature column is required for training.")
    for column in dataframe.columns:
        if column == target_column:
            continue
        series = dataframe[column]
        if series.isna().all():
            raise DatasetValidationError(f"Feature '{column}' contains no usable values.")
        if not _is_numeric(series) and series.nunique(dropna=True) > MAX_CATEGORICAL_CARDINALITY:
            raise DatasetValidationError(
                f"Feature '{column}' has too many categories (maximum {MAX_CATEGORICAL_CARDINALITY})."
            )
