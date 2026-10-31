import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.datasets.models import Dataset
from apps.models.models import MLModel, ModelStatus, ModelType

from .models import TrainingJob, TrainingStatus


User = get_user_model()


class TrainingApiTests(APITestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        temp_root = Path(self.temp_directory.name)
        self.settings_override = override_settings(
            STORAGE_ROOT=temp_root,
            STORAGE_DATASETS_PATH=temp_root / "datasets",
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.temp_directory.cleanup)

        self.client = APIClient()
        self.user = User.objects.create_user(
            name="Model Owner",
            email="model.owner@example.com",
            password="correct horse battery staple",
            is_active=True,
            email_verified=True,
            approval_status="APPROVED",
        )
        self.user.role = "SUPER_ADMIN"
        self.user.save(update_fields=["role"])
        self.other_user = User.objects.create_user(
            name="Other Owner",
            email="other.model@example.com",
            password="correct horse battery staple",
            is_active=True,
            email_verified=True,
            approval_status="APPROVED",
        )
        self.model = MLModel.objects.create(
            owner=self.user,
            name="Training model",
            model_type=ModelType.CSV,
        )
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def csv_file(self):
        rows = ["age,city,target"]
        for index in range(20):
            city = "London" if index % 2 == 0 else "Paris"
            target = "yes" if index < 10 else "no"
            rows.append(f"{20 + index},{city},{target}")
        return SimpleUploadedFile(
            "training.csv",
            ("\n".join(rows) + "\n").encode(),
            content_type="text/csv",
        )

    def optional_feature_csv(self):
        rows = ["age,city,target"]
        for index in range(20):
            city = "London" if index % 2 == 0 else "Paris"
            age = "" if index % 4 == 0 else str(20 + index)
            target = "yes" if index < 10 else "no"
            rows.append(f"{age},{city},{target}")
        return SimpleUploadedFile(
            "optional.csv",
            ("\n".join(rows) + "\n").encode(),
            content_type="text/csv",
        )

    def regression_csv(self):
        rows = ["size,price"]
        rows.extend(f"{10 + index},{100 + index * 5}" for index in range(20))
        return SimpleUploadedFile(
            "regression.csv",
            ("\n".join(rows) + "\n").encode(),
            content_type="text/csv",
        )

    def prepare_dataset(self, select_target=True):
        self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file()},
            format="multipart",
        )
        if select_target:
            self.client.post(
                reverse("model-dataset-target", args=[self.model.id]),
                {"target_column": "target"},
                format="json",
            )

    def test_training_creates_completed_job_metrics_and_artifact(self):
        self.prepare_dataset()

        response = self.client.post(
            reverse("model-training", args=[self.model.id])
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["job"]["status"], TrainingStatus.COMPLETED)
        self.assertEqual(response.data["data"]["job"]["progress"], 100)
        metrics = response.data["data"]["job"]["metrics"]
        for metric in ("accuracy", "precision", "recall", "f1", "confusion_matrix"):
            self.assertIn(metric, metrics)
        self.model.refresh_from_db()
        self.assertEqual(self.model.status, ModelStatus.TRAINED)
        self.assertTrue(self.model.artifact_reference.endswith("model.joblib"))
        self.assertEqual(TrainingJob.objects.filter(model=self.model).count(), 1)
        self.assertNotIn("target", [feature["name"] for feature in self.model.metadata["features"]])
        self.assertEqual(
            self.model.metadata["train_rows"] + self.model.metadata["test_rows"],
            20,
        )
        self.assertTrue(self.model.metadata["stratified"])

    def test_auto_training_exposes_algorithm_comparison_metrics(self):
        self.prepare_dataset()
        self.model.algorithm = "AUTO"
        self.model.save(update_fields=["algorithm"])

        response = self.client.post(reverse("model-training", args=[self.model.id]))

        self.assertEqual(response.status_code, 201)
        selection = response.data["data"]["job"]["metrics"]["algorithm_selection"]
        self.assertEqual(selection["primary_metric"], "weighted_f1")
        self.assertEqual(selection["winner"], response.data["data"]["job"]["algorithm"])
        self.assertGreaterEqual(len(selection["leaderboard"]), 2)

    def test_regression_target_can_be_selected_and_compares_regressors(self):
        upload_response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.regression_csv()},
            format="multipart",
        )
        self.assertEqual(upload_response.status_code, 201)
        self.assertIn(
            "price",
            upload_response.data["data"]["preview"]["target_candidates"],
        )

        target_response = self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "price", "task_type": "regression"},
            format="json",
        )
        self.assertEqual(target_response.status_code, 200)

        training_response = self.client.post(
            reverse("model-training", args=[self.model.id])
        )

        self.assertEqual(training_response.status_code, 201)
        job = training_response.data["data"]["job"]
        self.assertEqual(job["status"], TrainingStatus.COMPLETED)
        self.assertIn(job["algorithm"], {
            "RANDOM_FOREST_REGRESSOR",
            "LINEAR_REGRESSION",
        })
        self.assertIn("rmse", job["metrics"])
        self.assertIn("mse", job["metrics"])
        self.assertNotIn("accuracy", job["metrics"])
        selection = job["metrics"]["algorithm_selection"]
        self.assertEqual(selection["primary_metric"], "rmse")
        self.assertEqual(
            {candidate["algorithm"] for candidate in selection["leaderboard"]},
            {"RANDOM_FOREST_REGRESSOR", "LINEAR_REGRESSION"},
        )
        self.assertEqual(selection["winner"], job["algorithm"])

        prediction_response = self.client.post(
            reverse("model-prediction", args=[self.model.id]),
            {"features": {"size": "25"}},
            format="json",
        )
        self.assertEqual(prediction_response.status_code, 200)
        self.assertIsNotNone(prediction_response.data["data"]["predicted_value"])

    def test_deleting_trained_model_removes_dataset_and_artifact_files(self):
        self.prepare_dataset()
        self.client.post(reverse("model-training", args=[self.model.id]))
        self.model.refresh_from_db()
        dataset = Dataset.objects.get(model=self.model)
        dataset_path = Path(settings.STORAGE_ROOT) / dataset.storage_path
        artifact_path = Path(settings.STORAGE_ROOT) / self.model.artifact_reference
        self.assertTrue(dataset_path.is_file())
        self.assertTrue(artifact_path.is_file())

        response = self.client.delete(reverse("model-detail", args=[self.model.id]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(dataset_path.exists())
        self.assertFalse(artifact_path.exists())

    def test_deleting_owner_cleans_owned_model_storage(self):
        self.prepare_dataset()
        self.client.post(reverse("model-training", args=[self.model.id]))
        self.model.refresh_from_db()
        dataset = Dataset.objects.get(model=self.model)
        dataset_path = Path(settings.STORAGE_ROOT) / dataset.storage_path
        artifact_path = Path(settings.STORAGE_ROOT) / self.model.artifact_reference

        self.user.delete()

        self.assertFalse(dataset_path.exists())
        self.assertFalse(artifact_path.exists())

    def test_trained_model_can_replace_dataset_and_target_then_retrain(self):
        self.prepare_dataset()
        self.client.post(reverse("model-training", args=[self.model.id]))

        upload_response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file()},
            format="multipart",
        )
        target_response = self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "target"},
            format="json",
        )
        retrain_response = self.client.post(
            reverse("model-training", args=[self.model.id])
        )

        self.assertEqual(upload_response.status_code, 201)
        self.assertEqual(target_response.status_code, 200)
        self.assertEqual(retrain_response.status_code, 201)
        self.assertEqual(TrainingJob.objects.filter(model=self.model).count(), 2)

    def test_failed_retrain_preserves_previous_artifact_and_trained_status(self):
        self.prepare_dataset()
        self.client.post(reverse("model-training", args=[self.model.id]))
        self.model.refresh_from_db()
        artifact_path = Path(settings.STORAGE_ROOT) / self.model.artifact_reference
        original_bytes = artifact_path.read_bytes()

        with patch("apps.training.services.train", side_effect=RuntimeError("boom")):
            response = self.client.post(
                reverse("model-training", args=[self.model.id])
            )

        self.assertEqual(response.status_code, 400)
        self.model.refresh_from_db()
        self.assertEqual(self.model.status, ModelStatus.TRAINED)
        self.assertEqual(artifact_path.read_bytes(), original_bytes)

    def test_metrics_and_prediction_schema_are_available_after_training(self):
        self.prepare_dataset()
        self.client.post(reverse("model-training", args=[self.model.id]))

        metrics_response = self.client.get(
            reverse("model-metrics", args=[self.model.id])
        )
        schema_response = self.client.get(
            reverse("model-prediction-schema", args=[self.model.id])
        )

        self.assertEqual(metrics_response.status_code, 200)
        self.assertIn("accuracy", metrics_response.data["data"]["metrics"])
        self.assertEqual(schema_response.status_code, 200)
        self.assertEqual(
            {feature["name"] for feature in schema_response.data["data"]["features"]},
            {"age", "city"},
        )
        self.assertEqual(schema_response.data["data"]["sample_values"]["age"], 29.5)
        self.assertIn(schema_response.data["data"]["sample_values"]["city"], {"London", "Paris"})

    def test_prediction_before_training_is_rejected(self):
        response = self.client.post(
            reverse("model-prediction", args=[self.model.id]),
            {"features": {"age": "26", "city": "Paris"}},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.data["success"])

    def test_prediction_returns_class_and_probability(self):
        self.prepare_dataset()
        self.client.post(reverse("model-training", args=[self.model.id]))

        response = self.client.post(
            reverse("model-prediction", args=[self.model.id]),
            {"features": {"age": "26", "city": "Paris"}},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.data["data"]["predicted_class"], {"yes", "no"})
        self.assertIsNotNone(response.data["data"]["probability"])
        self.assertIn("yes", response.data["data"]["probabilities"])
        self.assertIn("no", response.data["data"]["probabilities"])

    def test_prediction_accepts_optional_feature_omitted_when_training_had_missing_values(self):
        self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.optional_feature_csv()},
            format="multipart",
        )
        self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "target"},
            format="json",
        )
        self.client.post(reverse("model-training", args=[self.model.id]))

        response = self.client.post(
            reverse("model-prediction", args=[self.model.id]),
            {"features": {"city": "Paris"}},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.model.refresh_from_db()
        feature = next(
            feature
            for feature in self.model.metadata["features"]
            if feature["name"] == "age"
        )
        self.assertFalse(feature["required"])

    def test_prediction_rejects_missing_feature(self):
        self.prepare_dataset()
        self.client.post(reverse("model-training", args=[self.model.id]))

        response = self.client.post(
            reverse("model-prediction", args=[self.model.id]),
            {"features": {"age": "26"}},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_prediction_rejects_target_metadata_divergence(self):
        self.prepare_dataset()
        self.client.post(reverse("model-training", args=[self.model.id]))
        dataset = Dataset.objects.get(model=self.model)
        dataset.target_column = "city"
        dataset.save(update_fields=["target_column", "updated_at"])

        response = self.client.post(
            reverse("model-prediction", args=[self.model.id]),
            {"features": {"age": "26", "city": "Paris"}},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_prediction_rejects_invalid_feature_values(self):
        self.prepare_dataset()
        self.client.post(reverse("model-training", args=[self.model.id]))

        numeric_response = self.client.post(
            reverse("model-prediction", args=[self.model.id]),
            {"features": {"age": "not-a-number", "city": "Paris"}},
            format="json",
        )
        category_response = self.client.post(
            reverse("model-prediction", args=[self.model.id]),
            {"features": {"age": "26", "city": "Unknown City"}},
            format="json",
        )

        self.assertEqual(numeric_response.status_code, 400)
        self.assertEqual(category_response.status_code, 400)

    def test_training_requires_target_column(self):
        self.prepare_dataset(select_target=False)

        response = self.client.post(
            reverse("model-training", args=[self.model.id])
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.model.refresh_from_db()
        self.assertEqual(self.model.status, ModelStatus.DRAFT)

    def test_other_developer_cannot_train_or_predict(self):
        self.prepare_dataset()
        self.client.post(reverse("model-training", args=[self.model.id]))
        token = RefreshToken.for_user(self.other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

        training_response = self.client.post(
            reverse("model-training", args=[self.model.id])
        )
        prediction_response = self.client.post(
            reverse("model-prediction", args=[self.model.id]),
            {"features": {"age": "26", "city": "Paris"}},
            format="json",
        )

        self.assertEqual(training_response.status_code, 403)
        self.assertEqual(prediction_response.status_code, 200)
