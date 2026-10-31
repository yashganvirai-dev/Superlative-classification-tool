from pathlib import Path

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api import success
from apps.datasets.serializers import DatasetSerializer, DatasetUploadSerializer
from apps.datasets.services import (
    DatasetNotFound,
    TargetSelectionError,
    infer_target_column,
    load_dataset_dataframe,
    select_target_column,
    upload_dataset,
)
from apps.training.serializers import TrainingJobSerializer
from apps.training.services import TrainingError, start_training
from ml.csv.validation import DatasetValidationError

from .permissions import IsModelOwnerOrSuperAdmin
from .serializers import MLModelCreateSerializer, MLModelSerializer
from .services import (
    ModelCapacityError,
    ModelLifecycleError,
    ModelStorageError,
    create_csv_model,
    delete_model_with_files,
    get_visible_model,
    visible_models,
)


class ModelListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        models = list(visible_models(request.user).order_by("-created_at"))
        return success(
            {
                "models": MLModelSerializer(models, many=True).data,
                "count": len(models),
            }
        )

    def post(self, request):
        serializer = MLModelCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            model = create_csv_model(owner=request.user, **serializer.validated_data)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except (ModelCapacityError, ValueError) as exc:
            raise ValidationError({"model": str(exc)}) from exc
        return success(
            {"model": MLModelSerializer(model).data},
            status_code=status.HTTP_201_CREATED,
        )


class AutomaticModelCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        dataset_serializer = DatasetUploadSerializer(data=request.data)
        dataset_serializer.is_valid(raise_exception=True)

        algorithm = request.data.get("algorithm", "AUTO")
        from .models import Algorithm

        if algorithm not in Algorithm.values:
            raise ValidationError({"algorithm": "Select a supported CSV algorithm."})
        description = request.data.get("description", "").strip()
        uploaded_file = dataset_serializer.validated_data["file"]
        name = request.data.get("name", "").strip()
        if not name:
            name = Path(uploaded_file.name).stem.replace("_", " ").replace("-", " ").strip()[:255]
        if not name:
            name = "Automatic CSV Model"

        try:
            model = create_csv_model(
                owner=request.user,
                name=name,
                description=description,
                model_type="CSV",
                algorithm=algorithm,
            )
            dataset = upload_dataset(model=model, uploaded_file=uploaded_file)
            dataframe = load_dataset_dataframe(dataset)
            target_column = infer_target_column(dataframe, dataset.metadata or {})
            dataset = select_target_column(model=model, target_column=target_column)
            job = start_training(model)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except (ModelCapacityError, ValueError, DatasetValidationError) as exc:
            raise ValidationError({"automatic": str(exc)}) from exc
        except (DatasetNotFound, TargetSelectionError, TrainingError) as exc:
            raise ValidationError({"automatic": str(exc)}) from exc

        return success(
            {
                "model": MLModelSerializer(job.model).data,
                "dataset": DatasetSerializer(dataset).data,
                "job": TrainingJobSerializer(job).data,
                "target_column": target_column,
            },
            status_code=status.HTTP_201_CREATED,
        )


class ModelDetailView(APIView):
    permission_classes = [IsAuthenticated, IsModelOwnerOrSuperAdmin]

    def get(self, request, model_id: int):
        model = _get_model(request, model_id)
        self.check_object_permissions(request, model)
        return success({"model": MLModelSerializer(model).data})

    def delete(self, request, model_id: int):
        model = _get_model(request, model_id)
        self.check_object_permissions(request, model)
        try:
            delete_model_with_files(model)
        except (ModelLifecycleError, ModelStorageError) as exc:
            raise ValidationError({"model": str(exc)}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


def _get_model(request, model_id: int):
    try:
        return get_visible_model(user=request.user, model_id=model_id)
    except LookupError as exc:
        raise NotFound(str(exc)) from exc
