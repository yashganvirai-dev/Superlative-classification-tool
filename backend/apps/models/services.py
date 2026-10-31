"""Model registry business operations and storage lifecycle."""

import logging
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from apps.accounts.permissions import can_access_platform
from apps.accounts.models import UserRole

from .models import MLModel, ModelStatus, ModelType


logger = logging.getLogger("superlative.models")


class ModelCapacityError(Exception):
    """Raised when a user has reached a configured model/storage limit."""


class ModelLifecycleError(Exception):
    """Raised when a model cannot safely change state."""


class ModelStorageError(Exception):
    """Raised when a stored model reference is unsafe or cannot be cleaned up."""


def _storage_root() -> Path:
    return Path(settings.STORAGE_ROOT).resolve()


def _safe_storage_path(reference: str | None) -> Path | None:
    if not reference:
        return None
    if Path(reference).is_absolute():
        raise ModelStorageError("The model storage path must be relative.")
    root = _storage_root()
    path = (root / reference).resolve()
    if not path.is_relative_to(root):
        raise ModelStorageError("The model storage path is invalid.")
    return path


def _model_storage_references(user) -> list[str]:
    references = []
    models = MLModel.objects.filter(owner=user).prefetch_related("dataset")
    for model in models:
        try:
            dataset = model.dataset
        except ObjectDoesNotExist:
            dataset = None
        if dataset is not None:
            references.append(dataset.storage_path)
        if model.artifact_reference:
            references.append(model.artifact_reference)
    return references


def storage_usage(user, *, exclude_references: set[str] | None = None) -> int:
    """Return the user's current known artifact size in bytes."""
    excluded = exclude_references or set()
    total = 0
    for reference in _model_storage_references(user):
        if reference in excluded:
            continue
        path = _safe_storage_path(reference)
        if path is None:
            continue
        try:
            total += path.stat().st_size
        except FileNotFoundError:
            continue
        except OSError:
            logger.warning("Could not inspect model storage for quota calculation.")
            continue
    return total


def ensure_model_capacity(
    user,
    *,
    additional_bytes: int = 0,
    check_model_count: bool = True,
    exclude_references: set[str] | None = None,
) -> None:
    if check_model_count and MLModel.objects.filter(owner=user).count() >= settings.MAX_USER_MODEL_COUNT:
        raise ModelCapacityError("The maximum number of models has been reached.")
    try:
        projected = storage_usage(user, exclude_references=exclude_references) + max(0, additional_bytes)
    except ModelStorageError as exc:
        raise ModelCapacityError(str(exc)) from exc
    if projected > settings.MAX_USER_STORAGE_BYTES:
        raise ModelCapacityError("The model storage quota has been reached.")


def create_csv_model(
    *,
    owner,
    name: str,
    description: str = "",
    model_type: str = ModelType.CSV,
    algorithm: str = "RANDOM_FOREST_CLASSIFIER",
) -> MLModel:
    """Create a CSV model owned by the requesting user."""
    if model_type != ModelType.CSV:
        raise ValueError("Only CSV tabular models are available in this phase.")
    if owner.role != UserRole.SUPER_ADMIN:
        raise PermissionError("Only a Super Admin can create models.")
    if not can_access_platform(owner):
        raise PermissionError("An approved active account is required to create models.")
    ensure_model_capacity(owner)
    with transaction.atomic():
        return MLModel.objects.create(
            owner=owner,
            name=name,
            description=description,
            model_type=ModelType.CSV,
            algorithm="AUTO",
            status=ModelStatus.DRAFT,
        )


def visible_models(user):
    if user.role == UserRole.SUPER_ADMIN:
        return MLModel.objects.select_related("owner").prefetch_related("dataset")
    return MLModel.objects.filter(status=ModelStatus.TRAINED).select_related("owner").prefetch_related("dataset")


def get_visible_model(*, user, model_id: int) -> MLModel:
    try:
        return visible_models(user).get(pk=model_id)
    except MLModel.DoesNotExist as exc:
        raise LookupError("Model not found.") from exc


def delete_model_with_files(model: MLModel) -> None:
    """Delete a model and clean its generated dataset/artifact files."""
    with transaction.atomic():
        locked_model = MLModel.objects.select_for_update().get(pk=model.pk)
        if locked_model.status in {ModelStatus.TRAINING, ModelStatus.VALIDATING}:
            raise ModelLifecycleError("A model cannot be deleted while it is being processed.")
        try:
            dataset = locked_model.dataset
        except ObjectDoesNotExist:
            dataset = None
        references = []
        if dataset is not None:
            references.append(dataset.storage_path)
        if locked_model.artifact_reference:
            references.append(locked_model.artifact_reference)
        paths = [_safe_storage_path(reference) for reference in references]
        artifact_path = _safe_storage_path(locked_model.artifact_reference)
        if artifact_path is not None:
            paths.extend(
                [
                    artifact_path.with_suffix(".joblib.previous"),
                    artifact_path.with_suffix(".joblib.tmp"),
                ]
            )
        locked_model.delete()

    for path in paths:
        if path is None:
            continue
        try:
            path.unlink(missing_ok=True)
            parent = path.parent
            if parent != _storage_root() and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            # The database record is already gone; the logger leaves an actionable
            # orphan for the storage cleanup command rather than exposing paths.
            logger.exception("Could not remove model storage file for model %s", model.pk)
