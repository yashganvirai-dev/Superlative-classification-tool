"""Leakage-free preprocessing for mixed CSV feature types."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .validation import MAX_CATEGORICAL_CARDINALITY


def identify_feature_types(dataframe: pd.DataFrame, target_column: str) -> tuple[list[str], list[str]]:
    feature_columns = [column for column in dataframe.columns if column != target_column]
    numeric_columns = [
        column
        for column in feature_columns
        if pd.api.types.is_numeric_dtype(dataframe[column])
        and not pd.api.types.is_bool_dtype(dataframe[column])
    ]
    categorical_columns = [column for column in feature_columns if column not in numeric_columns]
    if not feature_columns:
        raise ValueError("At least one feature column is required for training.")
    return numeric_columns, categorical_columns


def build_preprocessor(dataframe: pd.DataFrame, target_column: str) -> ColumnTransformer:
    numeric_columns, categorical_columns = identify_feature_types(dataframe, target_column)
    transformers = []
    if numeric_columns:
        transformers.append(
            (
                "numeric",
                Pipeline([("imputer", SimpleImputer(strategy="constant", fill_value=0))]),
                numeric_columns,
            )
        )
    if categorical_columns:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(strategy="constant", fill_value="__MISSING__"),
                        ),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_columns,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop")


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def build_feature_schema(
    dataframe: pd.DataFrame,
    target_column: str,
    *,
    max_categories: int = MAX_CATEGORICAL_CARDINALITY,
) -> list[dict]:
    numeric_columns, categorical_columns = identify_feature_types(dataframe, target_column)
    numeric_set = set(numeric_columns)
    schema = []
    for column in dataframe.columns:
        if column == target_column:
            continue
        series = dataframe[column]
        entry = {
            "name": str(column),
            "type": "numerical" if column in numeric_set else "categorical",
            "required": not bool(series.isna().any()),
        }
        if column in categorical_columns:
            categories = series.dropna().unique().tolist()
            if len(categories) > max_categories:
                raise ValueError(
                    f"Categorical feature '{column}' has more than {max_categories} categories."
                )
            entry["categories"] = [_json_value(value) for value in categories]
        schema.append(entry)
    return schema
