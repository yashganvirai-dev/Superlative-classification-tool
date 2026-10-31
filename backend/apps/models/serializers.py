from rest_framework import serializers

from .models import Algorithm, MLModel, ModelType


class MLModelSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    has_dataset = serializers.SerializerMethodField()
    has_artifact = serializers.SerializerMethodField()
    target_column = serializers.SerializerMethodField()
    metadata = serializers.SerializerMethodField()

    class Meta:
        model = MLModel
        fields = (
            "id",
            "name",
            "owner",
            "owner_email",
            "model_type",
            "algorithm",
            "status",
            "description",
            "has_artifact",
            "metadata",
            "has_dataset",
            "target_column",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "owner_email",
            "status",
            "has_artifact",
            "metadata",
            "has_dataset",
            "target_column",
            "created_at",
            "updated_at",
        )

    def get_has_artifact(self, obj) -> bool:
        return bool(obj.artifact_reference)

    def get_metadata(self, obj) -> dict:
        metadata = dict(obj.metadata or {})
        metadata.pop("artifact_reference", None)
        return metadata

    def get_has_dataset(self, obj) -> bool:
        return hasattr(obj, "dataset")

    def get_target_column(self, obj) -> str:
        return getattr(getattr(obj, "dataset", None), "target_column", "")


class MLModelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MLModel
        fields = ("name", "description", "model_type", "algorithm")

    def validate_model_type(self, value):
        if value != ModelType.CSV:
            raise serializers.ValidationError("Only CSV tabular models are available in this phase.")
        return value

    def validate_algorithm(self, value):
        if value not in Algorithm.values:
            raise serializers.ValidationError("Select a supported CSV algorithm.")
        return value
