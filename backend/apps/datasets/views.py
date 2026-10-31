"""CSV dataset API views."""

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ml.csv.validation import DatasetValidationError

from apps.models.services import ModelCapacityError, get_visible_model
from config.api import success

from .permissions import IsDatasetOwnerOrSuperAdmin
from .serializers import DatasetSerializer, DatasetUploadSerializer, TargetColumnSerializer
from .services import (
    DatasetNotFound,
    TargetSelectionError,
    dataset_preview,
    get_dataset,
    select_target_column,
    upload_dataset,
)


class DatasetView(APIView):
    permission_classes = [IsAuthenticated, IsDatasetOwnerOrSuperAdmin]

    def get(self, request, model_id: int):
        model = _get_model(request, model_id)
        self.check_object_permissions(request, model)
        try:
            dataset = get_dataset(model)
            preview = dataset_preview(dataset)
        except DatasetNotFound as exc:
            raise NotFound(str(exc)) from exc
        return success(
            {
                "dataset": DatasetSerializer(dataset).data,
                "preview": preview,
                "model_status": model.status,
            }
        )

    def post(self, request, model_id: int):
        model = _get_model(request, model_id)
        self.check_object_permissions(request, model)
        serializer = DatasetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            dataset = upload_dataset(
                model=model,
                uploaded_file=serializer.validated_data["file"],
                expand_existing=str(request.data.get("expand_existing", "false")).lower() in {"1", "true", "yes", "on"},
            )
        except (DatasetValidationError, ModelCapacityError) as exc:
            raise ValidationError({"file": str(exc)}) from exc
        return success(
            {
                "dataset": DatasetSerializer(dataset).data,
                "preview": dataset_preview(dataset),
                "model_status": model.status,
            },
            status_code=status.HTTP_201_CREATED,
        )


class TargetColumnView(APIView):
    permission_classes = [IsAuthenticated, IsDatasetOwnerOrSuperAdmin]

    def post(self, request, model_id: int):
        model = _get_model(request, model_id)
        self.check_object_permissions(request, model)
        serializer = TargetColumnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            dataset = select_target_column(
                model=model,
                target_column=serializer.validated_data["target_column"],
                task_type=serializer.validated_data["task_type"],
            )
        except DatasetNotFound as exc:
            raise NotFound(str(exc)) from exc
        except TargetSelectionError as exc:
            raise ValidationError({"target_column": str(exc)}) from exc
        return success({"dataset": DatasetSerializer(dataset).data})


def _get_model(request, model_id: int):
    try:
        return get_visible_model(user=request.user, model_id=model_id)
    except LookupError as exc:
        raise NotFound(str(exc)) from exc
