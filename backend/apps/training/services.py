"""Synchronous training job orchestration."""

import hashlib
import logging
import os
from pathlib import Path

import joblib
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from apps.datasets.models import Dataset
from apps.datasets.services import load_dataset_dataframe, resolve_dataset_path
from apps.models.models import MLModel, ModelStatus
from apps.models.services import ModelCapacityError, ensure_model_capacity
from ml.csv.trainer import train, train_random_forest
from ml.csv.validation import DatasetValidationError

from .models import TrainingJob, TrainingStatus


logger = logging.getLogger("superlative.training")


class TrainingError(Exception):
    """Raised when a training job cannot be completed safely."""


def _storage_root() -> Path:
    return Path(settings.STORAGE_ROOT).resolve()


def artifact_path_for_model(model: MLModel) -> tuple[str, Path]:
    relative_path = Path("trained_models") / str(model.pk) / "model.joblib"
    root = _storage_root()
    absolute_path = (root / relative_path).resolve()
    if not absolute_path.is_relative_to(root):
        raise TrainingError("The training artifact path is invalid.")
    return str(relative_path), absolute_path


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _remove_if_exists(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not remove temporary model artifact %s", path)


def _restore_previous_artifact(
    final_path: Path,
    backup_path: Path,
    *,
    artifact_replaced: bool,
    backup_created: bool,
) -> None:
    """Restore the last known-good artifact after a failed retrain."""
    try:
        if artifact_replaced:
            _remove_if_exists(final_path)
        if backup_created and backup_path.exists():
            os.replace(backup_path, final_path)
    except OSError:
        logger.exception("Could not restore the previous model artifact")


def start_training(model: MLModel) -> TrainingJob:
    if model.model_type != "CSV":
        raise TrainingError("Only CSV models can be trained.")
    try:
        dataset = model.dataset
    except ObjectDoesNotExist as exc:
        raise TrainingError("Upload and validate a dataset before training.") from exc
    if not dataset.target_column:
        raise TrainingError("Select a target column before training.")

    with transaction.atomic():
        locked_model = MLModel.objects.select_for_update().get(pk=model.pk)
        locked_dataset = Dataset.objects.get(model=locked_model)
        if locked_model.status not in {
            ModelStatus.DRAFT,
            ModelStatus.FAILED,
            ModelStatus.TRAINED,
        }:
            raise TrainingError("Only draft, failed, or trained models can be trained.")
        job = TrainingJob.objects.create(
            model=locked_model,
            status=TrainingStatus.RUNNING,
            progress=10,
            algorithm=locked_model.algorithm,
            started_at=timezone.now(),
        )
        locked_model.status = ModelStatus.TRAINING
        locked_model.save(update_fields=["status", "updated_at"])

    temporary_artifact: Path | None = None
    final_artifact: Path | None = None
    backup_artifact: Path | None = None
    artifact_replaced = False
    backup_created = False
    previous_artifact_available = False

    try:
        dataset_path = resolve_dataset_path(locked_dataset.storage_path)
        if _file_sha256(dataset_path) != locked_dataset.sha256:
            raise TrainingError("The dataset changed after upload. Upload it again before training.")
        dataframe = load_dataset_dataframe(locked_dataset)
        job.progress = 35
        job.save(update_fields=["progress"])

        result = train(
            dataframe,
            locked_dataset.target_column,
            algorithm="AUTO",
            task_type=(locked_dataset.metadata or {}).get("task_type", "auto"),
        )
        job.progress = 80
        job.save(update_fields=["progress"])

        relative_artifact, final_artifact = artifact_path_for_model(locked_model)
        final_artifact.parent.mkdir(parents=True, exist_ok=True)
        temporary_artifact = final_artifact.with_suffix(".joblib.tmp")
        backup_artifact = final_artifact.with_suffix(".joblib.previous")
        previous_artifact_available = bool(locked_model.artifact_reference) and final_artifact.exists()
        if not final_artifact.exists() and backup_artifact.exists():
            os.replace(backup_artifact, final_artifact)
            previous_artifact_available = True
        joblib.dump(result.pipeline, temporary_artifact)
        artifact_size = temporary_artifact.stat().st_size
        try:
            ensure_model_capacity(
                locked_model.owner,
                additional_bytes=artifact_size,
                check_model_count=False,
                exclude_references={locked_model.artifact_reference}
                if locked_model.artifact_reference
                else set(),
            )
        except ModelCapacityError as exc:
            raise TrainingError(str(exc)) from exc

        # Keep a recoverable copy while the database metadata is being committed.
        if final_artifact.exists():
            _remove_if_exists(backup_artifact)
            os.replace(final_artifact, backup_artifact)
            backup_created = True
        os.replace(temporary_artifact, final_artifact)
        artifact_replaced = True
        temporary_artifact = None

        metadata = dict(locked_model.metadata or {})
        metadata.update(result.metadata)
        metadata.update(
            {
                "dataset": {
                    "id": locked_dataset.id,
                    "row_count": locked_dataset.row_count,
                    "column_count": locked_dataset.column_count,
                    "sha256": locked_dataset.sha256,
                },
                "trained_at": timezone.now().isoformat(),
                "artifact_reference": relative_artifact,
            }
        )
        with transaction.atomic():
            locked_model.status = ModelStatus.TRAINED
            locked_model.artifact_reference = relative_artifact
            locked_model.algorithm = result.metadata["algorithm"]
            locked_model.metadata = metadata
            locked_model.save(
                update_fields=["status", "artifact_reference", "algorithm", "metadata", "updated_at"]
            )
            job.algorithm = result.metadata["algorithm"]
            job.status = TrainingStatus.COMPLETED
            job.progress = 100
            job_metrics = dict(result.metrics)
            algorithm_selection = (result.metadata or {}).get("algorithm_selection")
            if algorithm_selection:
                job_metrics["algorithm_selection"] = algorithm_selection
            job.metrics = job_metrics
            job.completed_at = timezone.now()
            job.save(
                update_fields=["status", "progress", "metrics", "algorithm", "completed_at"]
            )
        # The database now points at the new artifact; cleanup is best effort.
        _remove_if_exists(backup_artifact)
    except Exception as exc:
        if not previous_artifact_available and locked_model.artifact_reference:
            try:
                _, existing_artifact = artifact_path_for_model(locked_model)
                previous_artifact_available = existing_artifact.is_file()
            except TrainingError:
                pass
        _remove_if_exists(temporary_artifact)
        if final_artifact is not None and backup_artifact is not None:
            _restore_previous_artifact(
                final_artifact,
                backup_artifact,
                artifact_replaced=artifact_replaced,
                backup_created=backup_created,
            )
        safe_message = (
            str(exc)
            if isinstance(exc, (TrainingError, DatasetValidationError))
            else "Training failed unexpectedly. Check the dataset and try again."
        )
        with transaction.atomic():
            job.status = TrainingStatus.FAILED
            job.error_message = safe_message
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "completed_at"])
            locked_model.status = (
                ModelStatus.TRAINED
                if previous_artifact_available
                else ModelStatus.FAILED
            )
            locked_model.save(update_fields=["status", "updated_at"])
        logger.exception("Training job %s failed", job.pk)
        raise TrainingError(safe_message) from exc

    return job


def latest_training_job(model: MLModel) -> TrainingJob | None:
    return model.training_jobs.order_by("-created_at").first()


def model_metrics(model: MLModel) -> dict:
    job = latest_training_job(model)
    if not job or job.status != TrainingStatus.COMPLETED:
        return {}
    metrics = dict(job.metrics or {})
    if "algorithm_selection" not in metrics:
        selection = (model.metadata or {}).get("algorithm_selection")
        if selection:
            metrics["algorithm_selection"] = selection
    return metrics
