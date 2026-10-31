from rest_framework import serializers

from .models import TrainingJob


class PredictionInputSerializer(serializers.Serializer):
    features = serializers.DictField()


class TrainingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingJob
        fields = (
            "id",
            "model",
            "status",
            "progress",
            "algorithm",
            "metrics",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
        )
        read_only_fields = fields
