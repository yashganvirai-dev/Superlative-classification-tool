"""Training, metrics, and prediction API views."""

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.models.services import get_visible_model
from config.api import success

from .permissions import IsTrainedModelUser, IsTrainingOwnerOrSuperAdmin
from .prediction import PredictionError, predict, prediction_schema
from .serializers import PredictionInputSerializer, TrainingJobSerializer
from .services import TrainingError, latest_training_job, model_metrics, start_training


class TrainingView(APIView):
    permission_classes = [IsAuthenticated, IsTrainingOwnerOrSuperAdmin]

    def get(self, request, model_id: int):
        model = _get_model(request, model_id)
        self.check_object_permissions(request, model)
        job = latest_training_job(model)
        return success({"job": TrainingJobSerializer(job).data if job else None})

    def post(self, request, model_id: int):
        model = _get_model(request, model_id)
        self.check_object_permissions(request, model)
        try:
            job = start_training(model)
        except TrainingError as exc:
            raise ValidationError({"training": str(exc)}) from exc
        return success(
            {
                "job": TrainingJobSerializer(job).data,
                "model_status": job.model.status,
            },
            status_code=status.HTTP_201_CREATED,
        )


class MetricsView(APIView):
    permission_classes = [IsAuthenticated, IsTrainingOwnerOrSuperAdmin]

    def get(self, request, model_id: int):
        model = _get_model(request, model_id)
        self.check_object_permissions(request, model)
        return success(
            {
                "model_id": model.id,
                "status": model.status,
                "metrics": model_metrics(model),
            }
        )


class PredictionSchemaView(APIView):
    permission_classes = [IsAuthenticated, IsTrainedModelUser]

    def get(self, request, model_id: int):
        model = _get_model(request, model_id)
        self.check_object_permissions(request, model)
        try:
            schema = prediction_schema(model)
        except PredictionError as exc:
            raise ValidationError({"prediction": str(exc)}) from exc
        return success(schema)


class PredictionView(APIView):
    permission_classes = [IsAuthenticated, IsTrainedModelUser]

    def post(self, request, model_id: int):
        model = _get_model(request, model_id)
        self.check_object_permissions(request, model)
        serializer = PredictionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = predict(model, serializer.validated_data["features"])
        except PredictionError as exc:
            raise ValidationError({"prediction": str(exc)}) from exc
        return success(result)


def _get_model(request, model_id: int):
    try:
        return get_visible_model(user=request.user, model_id=model_id)
    except LookupError as exc:
        raise NotFound(str(exc)) from exc
