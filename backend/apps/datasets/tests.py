import json
import tempfile
from pathlib import Path

import pandas as pd

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.models.models import MLModel, ModelStatus, ModelType

from .models import Dataset
from .services import infer_target_column, resolve_dataset_path, TargetSelectionError


User = get_user_model()


class TargetInferenceTests(APITestCase):
    def test_preferred_column_name_is_selected(self):
        dataframe = pd.DataFrame({
            "age": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
            "city_group": ["a", "b", "a", "b", "a", "b", "a", "b", "a", "b"],
            "target": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        })
        self.assertEqual(infer_target_column(dataframe), "target")

    def test_last_valid_column_is_selected_when_no_name_matches(self):
        dataframe = pd.DataFrame({
            "feature_a": [1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
            "feature_b": [10, 20, 10, 20, 10, 20, 10, 20, 10, 20],
            "result_group": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        })
        metadata = {"target_candidates": ["feature_a", "feature_b", "result_group"]}
        self.assertEqual(infer_target_column(dataframe, metadata), "result_group")


class DatasetApiTests(APITestCase):
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
            name="Dataset Owner",
            email="dataset.owner@example.com",
            password="correct horse battery staple",
            is_active=True,
            email_verified=True,
            approval_status="APPROVED",
        )
        self.user.role = "SUPER_ADMIN"
        self.user.save(update_fields=["role"])
        self.other_user = User.objects.create_user(
            name="Other Owner",
            email="other.owner@example.com",
            password="correct horse battery staple",
            is_active=True,
            email_verified=True,
            approval_status="APPROVED",
        )
        self.model = MLModel.objects.create(
            owner=self.user,
            name="Classification model",
            model_type=ModelType.CSV,
        )
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def csv_file(self, content=None, filename="developer data.csv"):
        if content is None:
            content = (
                b"age,city,target\n"
                b"21,London,yes\n22,London,no\n23,Paris,yes\n24,Paris,no\n"
                b"25,Berlin,yes\n26,Berlin,no\n27,Madrid,yes\n28,Madrid,no\n"
                b"29,Lisbon,yes\n30,Lisbon,no\n31,Rome,yes\n32,Rome,no\n"
            )
        return SimpleUploadedFile(filename, content, content_type="text/csv")

    def test_upload_stores_generated_path_and_returns_preview(self):
        response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        dataset = Dataset.objects.get(model=self.model)
        self.assertNotEqual(dataset.storage_path, "developer data.csv")
        self.assertEqual(dataset.row_count, 12)
        self.assertEqual(dataset.column_count, 3)
        self.assertEqual(dataset.original_filename, "developer data.csv")
        self.assertEqual(dataset.target_column, "")
        self.assertEqual(len(response.data["data"]["preview"]["preview"]), 10)
        self.assertTrue(resolve_dataset_path(dataset.storage_path).is_file())
        self.model.refresh_from_db()
        self.assertEqual(self.model.status, ModelStatus.DRAFT)

    def test_trained_dataset_can_be_expanded_with_matching_columns(self):
        upload = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file()},
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201)
        target = self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "target"},
            format="json",
        )
        self.assertEqual(target.status_code, 200)
        self.model.status = ModelStatus.TRAINED
        self.model.save(update_fields=["status"])

        expansion = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {
                "file": self.csv_file(
                    content=(
                        b"age,city,target\n33,Tokyo,yes\n34,Tokyo,no\n"
                        b"35,Osaka,yes\n36,Osaka,no\n"
                    ),
                    filename="expansion.csv",
                ),
                "expand_existing": "true",
            },
            format="multipart",
        )

        self.assertEqual(expansion.status_code, 201)
        dataset = Dataset.objects.get(model=self.model)
        self.assertEqual(dataset.row_count, 16)
        self.assertEqual(dataset.target_column, "target")
        self.model.refresh_from_db()
        self.assertEqual(self.model.status, ModelStatus.DRAFT)

    def test_expansion_rejects_different_columns(self):
        upload = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file()},
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201)
        self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "target"},
            format="json",
        )
        self.model.status = ModelStatus.TRAINED
        self.model.save(update_fields=["status"])

        response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {
                "file": self.csv_file(content=b"age,target\n33,yes\n34,no\n"),
                "expand_existing": "true",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_target_column_can_be_selected_and_validated(self):
        self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file()},
            format="multipart",
        )

        response = self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "target"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        dataset = Dataset.objects.get(model=self.model)
        self.assertEqual(dataset.target_column, "target")

    def test_missing_target_column_is_rejected(self):
        self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file()},
            format="multipart",
        )

        response = self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "does_not_exist"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_empty_csv_is_rejected_without_database_record(self):
        response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file(content=b"", filename="empty.csv")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Dataset.objects.filter(model=self.model).exists())

    def test_inconsistent_csv_row_is_rejected(self):
        response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {
                "file": self.csv_file(
                    content=b"age,city,target\n21,London,yes,extra\n22,Paris,no\n",
                    filename="malformed.csv",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Dataset.objects.filter(model=self.model).exists())

    def test_non_csv_extension_is_rejected(self):
        response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file(filename="data.txt")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Dataset.objects.filter(model=self.model).exists())

    def test_non_finite_numeric_values_are_rejected(self):
        response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {
                "file": self.csv_file(
                    content=(
                        b"age,city,target\ninf,London,yes\n22,London,no\n"
                        b"23,Paris,yes\n24,Paris,no\n25,Berlin,yes\n"
                        b"26,Berlin,no\n27,Madrid,yes\n28,Madrid,no\n"
                        b"29,Lisbon,yes\n30,Lisbon,no\n"
                    ),
                    filename="infinite.csv",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Dataset.objects.filter(model=self.model).exists())

    def test_all_missing_feature_is_rejected(self):
        response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {
                "file": self.csv_file(
                    content=(
                        b"age,city,target\n,London,yes\n,London,no\n"
                        b",Paris,yes\n,Paris,no\n,Berlin,yes\n,Berlin,no\n"
                        b",Madrid,yes\n,MADRID,no\n,Lisbon,yes\n,Lisbon,no\n"
                    ),
                    filename="missing-feature.csv",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Dataset.objects.filter(model=self.model).exists())

    def test_singleton_target_class_is_rejected(self):
        self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file()},
            format="multipart",
        )

        response = self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "target"},
            format="json",
        )

        # The default fixture has two balanced classes, so replace the target
        # with a singleton-class dataset for the actual rejection check.
        dataset = Dataset.objects.get(model=self.model)
        path = resolve_dataset_path(dataset.storage_path)
        path.write_text(
            "age,city,target\n"
            "21,London,yes\n22,London,yes\n23,Paris,yes\n24,Paris,yes\n"
            "25,Berlin,yes\n26,Berlin,yes\n27,Madrid,yes\n28,Madrid,yes\n"
            "29,Lisbon,no\n30,Lisbon,yes\n",
            encoding="utf-8",
        )
        response = self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "target"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_whitespace_headers_are_normalized_consistently(self):
        upload_response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {
                "file": self.csv_file(
                    content=(
                        b" age , city , target \n"
                        b"21,London,yes\n22,London,no\n23,Paris,yes\n24,Paris,no\n"
                        b"25,Berlin,yes\n26,Berlin,no\n27,Madrid,yes\n28,Madrid,no\n"
                        b"29,Lisbon,yes\n30,Lisbon,no\n31,Rome,yes\n32,Rome,no\n"
                    ),
                    filename="spaced.csv",
                )
            },
            format="multipart",
        )
        self.assertEqual(upload_response.status_code, 201)
        preview_response = self.client.get(reverse("model-dataset", args=[self.model.id]))
        target_response = self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "target"},
            format="json",
        )

        self.assertEqual(
            [column["name"] for column in preview_response.data["data"]["preview"]["columns"]],
            ["age", "city", "target"],
        )
        self.assertEqual(target_response.status_code, 200)

    def test_high_cardinality_categorical_feature_is_rejected_for_training(self):
        rows = ["feature,target"]
        rows.extend(f"category_{index},yes" for index in range(101))
        rows.extend(f"category_{index},no" for index in range(101))
        upload_response = self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {
                "file": self.csv_file(
                    content=("\n".join(rows) + "\n").encode(),
                    filename="high-cardinality.csv",
                )
            },
            format="multipart",
        )
        self.assertEqual(upload_response.status_code, 201)

        target_response = self.client.post(
            reverse("model-dataset-target", args=[self.model.id]),
            {"target_column": "target"},
            format="json",
        )

        self.assertEqual(target_response.status_code, 400)

    def test_request_size_limit_rejects_upload_before_view_processing(self):
        with self.settings(MAX_DATASET_REQUEST_BYTES=10):
            response = self.client.post(
                reverse("model-dataset", args=[self.model.id]),
                {"file": self.csv_file()},
                format="multipart",
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(json.loads(response.content)["error"]["code"], "REQUEST_TOO_LARGE")
        self.assertFalse(Dataset.objects.filter(model=self.model).exists())

    def test_storage_quota_rejects_large_upload(self):
        with self.settings(MAX_USER_STORAGE_BYTES=10):
            response = self.client.post(
                reverse("model-dataset", args=[self.model.id]),
                {"file": self.csv_file()},
                format="multipart",
            )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Dataset.objects.filter(model=self.model).exists())

    def test_other_developer_cannot_access_dataset(self):
        self.client.post(
            reverse("model-dataset", args=[self.model.id]),
            {"file": self.csv_file()},
            format="multipart",
        )
        token = RefreshToken.for_user(self.other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

        response = self.client.get(reverse("model-dataset", args=[self.model.id]))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data["success"])
