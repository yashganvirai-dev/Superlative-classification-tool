from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .models import Dataset


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = (
            "id",
            "model",
            "original_filename",
            "file_size",
            "sha256",
            "row_count",
            "column_count",
            "target_column",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DatasetUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if Path(value.name).suffix.lower() != ".csv":
            raise serializers.ValidationError("Only .csv files are supported.")
        if value.size > settings.MAX_DATASET_UPLOAD_BYTES:
            raise serializers.ValidationError("The CSV file exceeds the upload size limit.")
        allowed_types = {
            "",
            "text/csv",
            "application/csv",
            "application/vnd.ms-excel",
            "application/octet-stream",
        }
        content_type = (value.content_type or "").lower()
        if content_type not in allowed_types:
            raise serializers.ValidationError("The uploaded file is not a supported CSV file.")
        return value


class TargetColumnSerializer(serializers.Serializer):
    target_column = serializers.CharField(max_length=255)
    task_type = serializers.ChoiceField(
        choices=("auto", "classification", "regression"),
        default="auto",
    )
