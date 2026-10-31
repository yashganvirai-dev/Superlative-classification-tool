"""Filesystem cleanup signals for deleted model records."""

import logging

from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist

from .models import MLModel
from .services import ModelStorageError, _safe_storage_path


logger = logging.getLogger("superlative.models")


@receiver(pre_delete, sender=MLModel)
def remember_model_storage(instance: MLModel, **kwargs) -> None:
    references = []
    try:
        dataset = instance.dataset
    except ObjectDoesNotExist:
        dataset = None
    if dataset is not None:
        references.append(dataset.storage_path)
    if instance.artifact_reference:
        references.append(instance.artifact_reference)
    instance._storage_references_to_cleanup = references


@receiver(post_delete, sender=MLModel)
def remove_deleted_model_storage(instance: MLModel, **kwargs) -> None:
    for reference in getattr(instance, "_storage_references_to_cleanup", []):
        try:
            path = _safe_storage_path(reference)
            if path is not None:
                paths = [path]
                if path.name == "model.joblib":
                    paths.extend(
                        [path.with_suffix(".joblib.previous"), path.with_suffix(".joblib.tmp")]
                    )
                for candidate in paths:
                    candidate.unlink(missing_ok=True)
        except (OSError, ModelStorageError):
            logger.exception("Could not clean deleted model storage")
