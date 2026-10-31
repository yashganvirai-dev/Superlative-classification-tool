"""Training helpers for CSV classification and regression models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.base import clone
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline

from .evaluator import evaluate_classifier, evaluate_regressor
from .preprocessing import build_feature_schema, build_preprocessor, identify_feature_types
from .validation import (
    DatasetValidationError,
    detect_task,
    validate_dataframe,
    validate_regression_target,
    validate_target_column,
)


@dataclass(frozen=True)
class TrainingResult:
    pipeline: Pipeline
    metrics: dict
    metadata: dict
    stratified: bool


def _json_value(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


def compare_models(
    dataframe: pd.DataFrame,
    target_column: str,
    *,
    task_type: str = "auto",
    test_size: float = 0.2,
    random_state: int = 42,
) -> TrainingResult:
    task = detect_task(dataframe, target_column) if task_type == "auto" else task_type
    if task not in {"classification", "regression"}:
        raise DatasetValidationError("Select classification, regression, or automatic task detection.")
    if task == "classification":
        validate_target_column(dataframe, target_column, test_size=test_size)
        candidates = {
            "RANDOM_FOREST_CLASSIFIER": RandomForestClassifier(n_estimators=100, random_state=random_state),
            "DECISION_TREE_CLASSIFIER": DecisionTreeClassifier(random_state=random_state),
            "LOGISTIC_REGRESSION": LogisticRegression(max_iter=1000, random_state=random_state),
        }
    else:
        validate_regression_target(dataframe, target_column, test_size=test_size)
        candidates = {
            "RANDOM_FOREST_REGRESSOR": RandomForestRegressor(n_estimators=100, random_state=random_state),
            "LINEAR_REGRESSION": LinearRegression(),
        }

    features = dataframe.drop(columns=[target_column])
    target = dataframe[target_column]
    split_kwargs: dict = {"test_size": test_size, "random_state": random_state}
    if task == "classification":
        split_kwargs["stratify"] = target
    x_train, x_test, y_train, y_test = train_test_split(features, target, **split_kwargs)

    leaderboard = []
    fitted_candidates = {}
    for algorithm, estimator in candidates.items():
        pipeline = Pipeline([
            ("preprocessor", build_preprocessor(x_train, target_column)),
            ("estimator", estimator),
        ])
        try:
            pipeline.fit(x_train, y_train)
            predictions = pipeline.predict(x_test)
            if task == "classification":
                class_labels = pipeline.named_steps["estimator"].classes_
                metrics = evaluate_classifier(y_test, predictions, class_labels)
                primary_metric = float(metrics["f1"])
                cv_metric = "f1_weighted"
                class_counts = y_train.value_counts()
                cv_folds = min(5, int(class_counts.min())) if len(class_counts) > 1 else 2
                if cv_folds >= 2:
                    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
                    cv_scores = cross_val_score(clone(pipeline), x_train, y_train, cv=cv, scoring="f1_weighted")
                else:
                    cv_scores = None
            else:
                metrics = evaluate_regressor(y_test, predictions)
                primary_metric = -float(metrics["rmse"])
                cv_metric = "neg_root_mean_squared_error"
                cv_folds = min(5, len(x_train))
                if cv_folds >= 2:
                    cv = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
                    cv_scores = cross_val_score(clone(pipeline), x_train, y_train, cv=cv, scoring="neg_root_mean_squared_error")
                else:
                    cv_scores = None

            record = {
                "algorithm": algorithm,
                "metrics": metrics,
                "primary_metric": float(metrics["f1"] if task == "classification" else metrics["rmse"]),
                "cross_validation": {
                    "metric": cv_metric,
                    "folds": cv_folds if cv_scores is not None else 0,
                    "mean": float(cv_scores.mean()) if cv_scores is not None else None,
                    "std": float(cv_scores.std()) if cv_scores is not None else None,
                },
            }
            leaderboard.append(record)
            fitted_candidates[algorithm] = pipeline
        except Exception as exc:
            leaderboard.append({
                "algorithm": algorithm,
                "error": str(exc),
                "primary_metric": None,
            })

    usable = [record for record in leaderboard if record.get("primary_metric") is not None]
    if not usable:
        raise DatasetValidationError("None of the candidate algorithms could be trained successfully.")

    if task == "classification":
        winner = max(usable, key=lambda record: float(record["metrics"]["f1"]))
    else:
        winner = min(usable, key=lambda record: float(record["metrics"]["rmse"]))

    winning_algorithm = winner["algorithm"]
    winning_pipeline = fitted_candidates[winning_algorithm]
    winning_pipeline.fit(features, target)

    numeric_columns, categorical_columns = identify_feature_types(x_train, target_column)
    metadata = {
        "algorithm": winning_algorithm,
        "task": task,
        "target_column": target_column,
        "features": build_feature_schema(features, target_column),
        "feature_types": {
            "numerical": numeric_columns,
            "categorical": categorical_columns,
        },
        "class_labels": [] if task == "regression" else [_json_value(label) for label in winning_pipeline.named_steps["estimator"].classes_],
        "test_size": test_size,
        "random_state": random_state,
        "stratified": task == "classification",
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "algorithm_selection": {
            "primary_metric": "weighted_f1" if task == "classification" else "rmse",
            "winner": winning_algorithm,
            "leaderboard": leaderboard,
        },
    }
    return TrainingResult(
        pipeline=winning_pipeline,
        metrics=winner["metrics"],
        metadata=metadata,
        stratified=task == "classification",
    )


def train_random_forest(
    dataframe: pd.DataFrame,
    target_column: str,
    *,
    test_size: float = 0.2,
    random_state: int = 42,
    n_estimators: int = 100,
) -> TrainingResult:
    validate_dataframe(dataframe, min_rows=10)
    validate_target_column(dataframe, target_column, test_size=test_size)

    features = dataframe.drop(columns=[target_column])
    target = dataframe[target_column]
    class_counts = target.value_counts()
    test_rows = max(1, int(len(dataframe) * test_size))
    train_rows = len(dataframe) - test_rows
    can_stratify = bool(
        class_counts.min() >= 2
        and test_rows >= len(class_counts)
        and train_rows >= len(class_counts)
    )
    if not can_stratify:
        raise DatasetValidationError(
            "Every target class must be represented in both the training and evaluation splits."
        )
    split_kwargs = {
        "test_size": test_size,
        "random_state": random_state,
        "stratify": target,
    }

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        **split_kwargs,
    )
    for column in x_train.columns:
        if x_train[column].isna().all():
            raise DatasetValidationError(
                f"Feature '{column}' has no usable values in the training split."
            )
    expected_classes = set(target.unique())
    if set(y_train.unique()) != expected_classes or set(y_test.unique()) != expected_classes:
        raise DatasetValidationError(
            "Every target class must be represented in both the training and evaluation splits."
        )
    preprocessor = build_preprocessor(x_train, target_column)
    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=n_estimators,
                    random_state=random_state,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    class_labels = pipeline.named_steps["classifier"].classes_
    metrics = evaluate_classifier(y_test, predictions, class_labels)
    numeric_columns, categorical_columns = identify_feature_types(x_train, target_column)
    metadata = {
        "algorithm": "RANDOM_FOREST_CLASSIFIER",
        "target_column": target_column,
        "features": build_feature_schema(x_train, target_column),
        "feature_types": {
            "numerical": numeric_columns,
            "categorical": categorical_columns,
        },
        "class_labels": [_json_value(label) for label in class_labels],
        "test_size": test_size,
        "random_state": random_state,
        "n_estimators": n_estimators,
        "stratified": can_stratify,
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "preprocessing": {
            "numeric": "SimpleImputer(constant=0)",
            "categorical": "SimpleImputer(constant=__MISSING__) + OneHotEncoder(handle_unknown=ignore)",
            "scaling": False,
        },
    }
    return TrainingResult(
        pipeline=pipeline,
        metrics=metrics,
        metadata=metadata,
        stratified=can_stratify,
    )


def train(
    dataframe: pd.DataFrame,
    target_column: str,
    *,
    algorithm: str = "AUTO",
    task_type: str = "auto",
    test_size: float = 0.2,
    random_state: int = 42,
) -> TrainingResult:
    if algorithm == "AUTO":
        return compare_models(
            dataframe,
            target_column,
            task_type=task_type,
            test_size=test_size,
            random_state=random_state,
        )
    if algorithm == "RANDOM_FOREST_CLASSIFIER":
        return train_random_forest(
            dataframe,
            target_column,
            test_size=test_size,
            random_state=random_state,
        )
    classifiers = {
        "RANDOM_FOREST_CLASSIFIER": RandomForestClassifier(n_estimators=100, random_state=random_state),
        "DECISION_TREE_CLASSIFIER": DecisionTreeClassifier(random_state=random_state),
        "LOGISTIC_REGRESSION": LogisticRegression(max_iter=1000, random_state=random_state),
    }
    regressors = {
        "RANDOM_FOREST_REGRESSOR": RandomForestRegressor(n_estimators=100, random_state=random_state),
        "LINEAR_REGRESSION": LinearRegression(),
    }
    if algorithm in classifiers:
        validate_target_column(dataframe, target_column, test_size=test_size)
        target = dataframe[target_column]
        features = dataframe.drop(columns=[target_column])
        x_train, x_test, y_train, y_test = train_test_split(
            features, target, test_size=test_size, random_state=random_state, stratify=target
        )
        preprocessor = build_preprocessor(x_train, target_column)
        pipeline = Pipeline([("preprocessor", preprocessor), ("classifier", classifiers[algorithm])])
        pipeline.fit(x_train, y_train)
        labels = pipeline.named_steps["classifier"].classes_
        metrics = evaluate_classifier(y_test, pipeline.predict(x_test), labels)
        stratified = True
        target_type = "classification"
    elif algorithm in regressors:
        validate_regression_target(dataframe, target_column, test_size=test_size)
        features = dataframe.drop(columns=[target_column])
        target = dataframe[target_column]
        x_train, x_test, y_train, y_test = train_test_split(features, target, test_size=test_size, random_state=random_state)
        preprocessor = build_preprocessor(x_train, target_column)
        pipeline = Pipeline([("preprocessor", preprocessor), ("regressor", regressors[algorithm])])
        pipeline.fit(x_train, y_train)
        metrics = evaluate_regressor(y_test, pipeline.predict(x_test))
        labels = []
        stratified = False
        target_type = "regression"
    else:
        raise DatasetValidationError("Unsupported training algorithm.")
    numeric_columns, categorical_columns = identify_feature_types(x_train, target_column)
    metadata = {
        "algorithm": algorithm,
        "target_column": target_column,
        "task": target_type,
        "features": build_feature_schema(x_train, target_column),
        "feature_types": {"numerical": numeric_columns, "categorical": categorical_columns},
        "class_labels": [_json_value(label) for label in labels],
        "test_size": test_size,
        "random_state": random_state,
        "stratified": stratified,
        "train_rows": len(x_train),
        "test_rows": len(x_test),
    }
    return TrainingResult(pipeline=pipeline, metrics=metrics, metadata=metadata, stratified=stratified)
