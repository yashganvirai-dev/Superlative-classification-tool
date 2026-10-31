from django.conf import settings
from django.db import models


class ModelType(models.TextChoices):
    CSV = "CSV", "CSV / Tabular Classification"
    IMAGE = "IMAGE", "Image Classification"


class Algorithm(models.TextChoices):
    AUTO = "AUTO", "Automatic model selection"
    RANDOM_FOREST_CLASSIFIER = "RANDOM_FOREST_CLASSIFIER", "Random Forest Classifier"
    DECISION_TREE_CLASSIFIER = "DECISION_TREE_CLASSIFIER", "Decision Tree Classifier"
    LOGISTIC_REGRESSION = "LOGISTIC_REGRESSION", "Logistic Regression"
    RANDOM_FOREST_REGRESSOR = "RANDOM_FOREST_REGRESSOR", "Random Forest Regressor"
    LINEAR_REGRESSION = "LINEAR_REGRESSION", "Linear Regression"


class ModelStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    VALIDATING = "VALIDATING", "Validating"
    TRAINING = "TRAINING", "Training"
    TRAINED = "TRAINED", "Trained"
    FAILED = "FAILED", "Failed"


class MLModel(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ml_models",
    )
    model_type = models.CharField(
        max_length=20,
        choices=ModelType.choices,
        default=ModelType.CSV,
    )
    algorithm = models.CharField(
        max_length=40,
        choices=Algorithm.choices,
        default=Algorithm.RANDOM_FOREST_CLASSIFIER,
    )
    status = models.CharField(
        max_length=20,
        choices=ModelStatus.choices,
        default=ModelStatus.DRAFT,
        db_index=True,
    )
    description = models.TextField(blank=True)
    artifact_reference = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["model_type", "status"]),
        ]

    def __str__(self) -> str:
        return self.name
