from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import MLModel, ModelStatus, ModelType


User = get_user_model()


class ModelApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.developer = self.create_user("developer@example.com", "DEVELOPER")
        self.other_developer = self.create_user("other@example.com", "DEVELOPER")
        self.admin = self.create_user("admin@example.com", "SUPER_ADMIN")

    def create_user(self, email, role):
        extra_fields = {
            "role": role,
            "approval_status": "APPROVED",
            "is_active": True,
            "email_verified": True,
        }
        if role == "SUPER_ADMIN":
            return User.objects.create_superuser(
                name="Admin",
                email=email,
                password="correct horse battery staple",
            )
        return User.objects.create_user(
            name="Developer",
            email=email,
            password="correct horse battery staple",
            **extra_fields,
        )

    def authenticate(self, user):
        token = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def test_developer_can_create_csv_model(self):
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("model-list-create"),
            {
                "name": "Developer model",
                "description": "A test model",
                "model_type": ModelType.CSV,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["model"]["model_type"], ModelType.CSV)
        self.assertEqual(response.data["data"]["model"]["status"], ModelStatus.DRAFT)
        self.assertEqual(response.data["data"]["model"]["owner"], self.admin.id)

    def test_automatic_csv_model_uploads_infers_and_trains(self):
        self.authenticate(self.admin)
        csv_content = b"sepal_length,species\n5.1,setosa\n4.9,setosa\n5.0,setosa\n5.2,setosa\n4.8,setosa\n5.0,versicolor\n5.5,versicolor\n5.6,versicolor\n5.7,versicolor\n5.4,versicolor\n5.8,virginica\n6.0,virginica\n6.1,virginica\n6.3,virginica\n5.9,virginica\n"
        uploaded = SimpleUploadedFile("iris.csv", csv_content, content_type="text/csv")

        response = self.client.post(
            reverse("model-create-automatic"),
            {"file": uploaded, "algorithm": "RANDOM_FOREST_CLASSIFIER"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["target_column"], "species")
        self.assertEqual(response.data["data"]["model"]["status"], ModelStatus.TRAINED)

    def test_image_model_type_is_not_available(self):
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("model-list-create"),
            {"name": "Image model", "model_type": ModelType.IMAGE},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_developer_only_sees_owned_models(self):
        MLModel.objects.create(
            owner=self.developer,
            name="Owned model",
            model_type=ModelType.CSV,
            status=ModelStatus.TRAINED,
        )
        MLModel.objects.create(
            owner=self.other_developer,
            name="Other model",
            model_type=ModelType.CSV,
            status=ModelStatus.TRAINED,
        )
        self.authenticate(self.developer)

        response = self.client.get(reverse("model-list-create"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 2)

    def test_developer_cannot_read_another_developers_model(self):
        model = MLModel.objects.create(
            owner=self.other_developer,
            name="Private model",
            model_type=ModelType.CSV,
        )
        self.authenticate(self.developer)

        response = self.client.get(reverse("model-detail", args=[model.id]))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data["success"])

    def test_super_admin_can_see_all_models(self):
        MLModel.objects.create(
            owner=self.developer,
            name="Developer model",
            model_type=ModelType.CSV,
        )
        MLModel.objects.create(
            owner=self.other_developer,
            name="Other model",
            model_type=ModelType.CSV,
        )
        self.authenticate(self.admin)

        response = self.client.get(reverse("model-list-create"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 2)

    def test_developer_cannot_delete_draft_model(self):
        model = MLModel.objects.create(
            owner=self.developer,
            name="Draft model",
            model_type=ModelType.CSV,
        )
        self.authenticate(self.developer)

        response = self.client.delete(reverse("model-detail", args=[model.id]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(MLModel.objects.filter(pk=model.pk).exists())

    def test_model_api_does_not_expose_artifact_path(self):
        model = MLModel.objects.create(
            owner=self.developer,
            name="Trained model",
            model_type=ModelType.CSV,
            status=ModelStatus.TRAINED,
            artifact_reference="trained_models/1/model.joblib",
            metadata={"artifact_reference": "trained_models/1/model.joblib"},
        )
        self.authenticate(self.developer)

        response = self.client.get(reverse("model-detail", args=[model.id]))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("artifact_reference", response.data["data"]["model"])
        self.assertNotIn(
            "artifact_reference",
            response.data["data"]["model"]["metadata"],
        )
        self.assertTrue(response.data["data"]["model"]["has_artifact"])

    def test_developer_cannot_delete_trained_model(self):
        model = MLModel.objects.create(
            owner=self.developer,
            name="Trained model",
            model_type=ModelType.CSV,
            status=ModelStatus.TRAINED,
        )
        self.authenticate(self.developer)

        response = self.client.delete(reverse("model-detail", args=[model.id]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(MLModel.objects.filter(pk=model.pk).exists())
