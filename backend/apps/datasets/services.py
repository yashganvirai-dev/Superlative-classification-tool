"""Secure CSV storage, metadata, preview, and target operations."""

import csv
import hashlib
import logging
import uuid
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.db import transaction

from apps.models.models import MLModel, ModelStatus
from apps.models.services import ensure_model_capacity
from ml.csv.validation import (
    DatasetValidationError,
    build_metadata,
    detect_task,
    validate_dataframe,
    validate_target_column,
    validate_regression_target,
)

from .models import Dataset


logger = logging.getLogger("superlative.datasets")


class DatasetNotFound(Exception):
    """Raised when a model has no dataset."""


class TargetSelectionError(DatasetValidationError):
    """Raised when a target cannot be used for the selected task."""


def _storage_root() -> Path:
    return Path(settings.STORAGE_ROOT).resolve()


def resolve_dataset_path(storage_path: str) -> Path:
    if Path(storage_path).is_absolute():
        raise DatasetValidationError("The dataset storage path must be relative.")
    root = _storage_root()
    path = (root / storage_path).resolve()
    if not path.is_relative_to(root):
        raise DatasetValidationError("The dataset storage path is invalid.")
    return path


def _read_dataframe(path: Path) -> pd.DataFrame:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source)
            headers = next(reader, None)
            if not headers:
                raise DatasetValidationError("The CSV is empty.")
            normalized_headers = [header.strip() for header in headers]
            if any(not header for header in normalized_headers):
                raise DatasetValidationError("CSV column names cannot be blank.")
            if len(set(normalized_headers)) != len(normalized_headers):
                raise DatasetValidationError("CSV column names must be unique.")
            for row_number, row in enumerate(reader, start=2):
                if len(row) != len(headers):
                    raise DatasetValidationError(
                        f"CSV row {row_number} has an unexpected number of columns."
                    )
        dataframe = pd.read_csv(path, encoding="utf-8-sig")
        dataframe.columns = normalized_headers
        return dataframe
    except csv.Error as exc:
        raise DatasetValidationError("The CSV structure is invalid.") from exc
    except UnicodeDecodeError as exc:
        raise DatasetValidationError("The CSV must be UTF-8 encoded.") from exc
    except pd.errors.EmptyDataError as exc:
        raise DatasetValidationError("The CSV is empty.") from exc
    except pd.errors.ParserError as exc:
        raise DatasetValidationError("The CSV structure is invalid.") from exc
    except OSError as exc:
        raise DatasetValidationError("The CSV could not be read.") from exc


def _copy_upload(uploaded_file, destination: Path) -> tuple[int, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    total_bytes = 0
    with uploaded_file.open("rb") as source, destination.open("wb") as target:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > settings.MAX_DATASET_UPLOAD_BYTES:
                raise DatasetValidationError("The CSV file exceeds the upload size limit.")
            digest.update(chunk)
            target.write(chunk)
    return total_bytes, digest.hexdigest()


def load_dataset_dataframe(dataset: Dataset) -> pd.DataFrame:
    path = resolve_dataset_path(dataset.storage_path)
    if not path.is_file():
        raise DatasetNotFound("The dataset file is no longer available.")
    return _read_dataframe(path)


def upload_dataset(*, model: MLModel, uploaded_file, expand_existing: bool = False) -> Dataset:
    if model.model_type != "CSV":
        raise DatasetValidationError("Only CSV models can use datasets.")

    with transaction.atomic():
        locked_model = MLModel.objects.select_for_update().get(pk=model.pk)
        if expand_existing:
            if locked_model.status != ModelStatus.TRAINED:
                raise DatasetValidationError(
                    "Expansion is available only for trained models."
                )
        elif locked_model.status not in {
            ModelStatus.DRAFT,
            ModelStatus.FAILED,
            ModelStatus.TRAINED,
        }:
            raise DatasetValidationError(
                "Datasets can only be replaced on draft, failed, or trained models."
            )
        relative_path = Path("datasets") / str(locked_model.pk) / f"{uuid.uuid4().hex}.csv"
        absolute_path = resolve_dataset_path(str(relative_path))
        original_status = locked_model.status
        old_dataset = Dataset.objects.filter(model=locked_model).first()
        old_path = resolve_dataset_path(old_dataset.storage_path) if old_dataset else None
        excluded_references = {old_dataset.storage_path} if old_dataset else set()
        ensure_model_capacity(
            locked_model.owner,
            additional_bytes=getattr(uploaded_file, "size", 0) or 0,
            check_model_count=False,
            exclude_references=excluded_references,
        )
        locked_model.status = ModelStatus.VALIDATING
        locked_model.save(update_fields=["status", "updated_at"])
        model = locked_model

    try:
        uploaded_size, uploaded_sha256 = _copy_upload(uploaded_file, absolute_path)
        uploaded_dataframe = _read_dataframe(absolute_path)

        if expand_existing:
            if original_status != ModelStatus.TRAINED:
                raise DatasetValidationError("Expansion is available only after the model is trained.")
            if old_dataset is None:
                raise DatasetValidationError("The existing dataset is required before expansion.")
            existing_dataframe = load_dataset_dataframe(old_dataset)
            existing_columns = list(existing_dataframe.columns)
            uploaded_columns = list(uploaded_dataframe.columns)
            if uploaded_columns != existing_columns:
                raise DatasetValidationError(
                    "The expansion CSV must contain the same columns in the same order as the existing dataset."
                )
            dataframe = pd.concat([existing_dataframe, uploaded_dataframe], ignore_index=True)
            duplicate_column_rows = len(existing_dataframe) + len(uploaded_dataframe)
            target_column = old_dataset.target_column
        else:
            dataframe = uploaded_dataframe
            target_column = ""
            duplicate_column_rows = len(dataframe)

        validate_dataframe(
            dataframe,
            max_rows=settings.MAX_DATASET_ROWS,
            max_columns=settings.MAX_DATASET_COLUMNS,
        )

        expanded_path = absolute_path
        if expand_existing and old_dataset is not None:
            dataframe.to_csv(expanded_path, index=False, encoding="utf-8")
            file_size = expanded_path.stat().st_size
            sha256 = hashlib.sha256(expanded_path.read_bytes()).hexdigest()
        else:
            file_size = uploaded_size
            sha256 = uploaded_sha256

        metadata = build_metadata(
            dataframe,
            preview_rows=settings.MAX_PREVIEW_ROWS,
            task="auto",
        )
        if expand_existing and old_dataset is not None:
            task_type = (old_dataset.metadata or {}).get("task_type")
            if task_type:
                metadata["task_type"] = task_type
        original_filename = Path(uploaded_file.name).name[:255]
        with transaction.atomic():
            dataset, _ = Dataset.objects.update_or_create(
                model=model,
                defaults={
                    "original_filename": original_filename,
                    "storage_path": str(relative_path),
                    "file_size": file_size,
                    "sha256": sha256,
                    "row_count": len(dataframe),
                    "column_count": len(dataframe.columns),
                    "target_column": target_column,
                    "metadata": metadata,
                },
            )
            model.status = ModelStatus.DRAFT
            model.save(update_fields=["status", "updated_at"])
    except Exception:
        absolute_path.unlink(missing_ok=True)
        model.status = ModelStatus.FAILED
        model.save(update_fields=["status", "updated_at"])
        raise

    if old_path and old_path != absolute_path:
        try:
            old_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove replaced dataset file for model %s", model.pk)
    return dataset


def infer_target_column(dataframe: pd.DataFrame, metadata: dict | None = None) -> str:
    """Infer a likely classification or regression target."""
    candidates = list((metadata or {}).get("target_candidates") or [])
    if not candidates:
        candidates = list(build_metadata(dataframe, task="auto")["target_candidates"])

    if not candidates:
        raise TargetSelectionError(
            "No valid target column could be inferred from the CSV."
        )

    normalized = {str(column).strip().lower(): column for column in candidates}
    preferred_names = {
        "target", "label", "class", "classes", "category", "outcome",
        "result", "diagnosis", "status", "species", "survival", "churn",
        "risk", "prediction", "predicted", "answer", "decision",
    }

    preferred_matches = [
        column for key, column in normalized.items()
        if key in preferred_names or key.endswith("_target") or key.endswith("_label")
        or key.endswith("_class") or key.endswith("_status") or key.endswith("_outcome")
    ]
    if len(preferred_matches) == 1:
        return preferred_matches[0]

    if len(candidates) == 1:
        return candidates[0]

    last_candidate = candidates[-1]
    for candidate in reversed(list(dataframe.columns)):
        if candidate == last_candidate:
            return candidate
        if candidate in candidates:
            last_candidate = candidate
            break
    return last_candidate

    names = ", ".join(str(candidate) for candidate in candidates)
    raise TargetSelectionError(
        f"Multiple target columns could be inferred ({names}). "
        "Use manual mode to select a target column explicitly."
    )


def get_dataset(model: MLModel) -> Dataset:
    try:
        return model.dataset
    except Dataset.DoesNotExist as exc:
        raise DatasetNotFound("This model does not have a dataset yet.") from exc


def select_target_column(*, model: MLModel, target_column: str, task_type: str = "auto") -> Dataset:
    if task_type not in {"auto", "classification", "regression"}:
        raise TargetSelectionError(
            "Select automatic task detection, classification, or regression."
        )
    with transaction.atomic():
        locked_model = MLModel.objects.select_for_update().get(pk=model.pk)
        dataset = get_dataset(locked_model)
        if locked_model.status not in {ModelStatus.DRAFT, ModelStatus.FAILED, ModelStatus.TRAINED}:
            metadata_target = (locked_model.metadata or {}).get("target_column")
            if (
                locked_model.status == ModelStatus.TRAINED
                and dataset.target_column == target_column
                and metadata_target == target_column
                and (dataset.metadata or {}).get("task_type", "auto") == task_type
            ):
                return dataset
            raise TargetSelectionError(
                "The target cannot be changed after training. Create a new model for a different target."
            )
        locked_model.status = ModelStatus.VALIDATING
        locked_model.save(update_fields=["status", "updated_at"])

    try:
        dataframe = load_dataset_dataframe(dataset)
        if target_column not in dataframe.columns:
            raise DatasetValidationError("The selected target column does not exist.")
        selected_task = (
            detect_task(dataframe, target_column)
            if task_type == "auto"
            else task_type
        )
        if selected_task == "regression":
            validate_regression_target(dataframe, target_column)
        else:
            validate_target_column(dataframe, target_column)
    except DatasetNotFound:
        with transaction.atomic():
            locked_model = MLModel.objects.select_for_update().get(pk=model.pk)
            locked_model.status = ModelStatus.FAILED
            locked_model.save(update_fields=["status", "updated_at"])
        raise
    except DatasetValidationError as exc:
        with transaction.atomic():
            locked_model = MLModel.objects.select_for_update().get(pk=model.pk)
            locked_model.status = ModelStatus.FAILED
            locked_model.save(update_fields=["status", "updated_at"])
        raise TargetSelectionError(str(exc)) from exc

    with transaction.atomic():
        locked_model = MLModel.objects.select_for_update().get(pk=model.pk)
        dataset = Dataset.objects.get(pk=dataset.pk)
        dataset.target_column = target_column
        dataset.metadata = {**(dataset.metadata or {}), "task_type": task_type}
        dataset.save(update_fields=["target_column", "metadata", "updated_at"])
        locked_model.status = ModelStatus.DRAFT
        locked_model.save(update_fields=["status", "updated_at"])
    return dataset


def dataset_preview(dataset: Dataset) -> dict:
    dataframe = load_dataset_dataframe(dataset)
    metadata = build_metadata(
        dataframe,
        preview_rows=settings.MAX_PREVIEW_ROWS,
        task="auto",
    )
    return {
        "columns": metadata["columns"],
        "preview": metadata["preview"],
        "target_candidates": metadata["target_candidates"],
        "task_type": (dataset.metadata or {}).get("task_type", "auto"),
        "row_count": len(dataframe),
        "column_count": len(dataframe.columns),
        "target_column": dataset.target_column,
    }
