"""
Serializers for the eval_assistants API
"""

from rest_framework import serializers
from .models import Experiment, GoldenAnswer, AssistantResponse, Configuration


class ExperimentSerializer(serializers.ModelSerializer):
    """Serializer for Experiment model"""

    class Meta:
        model = Experiment
        fields = [
            "id",
            "experiment_id",
            "assistant_ids",
            "user_id",
            "company_id",
            "queries",
            "start_time",
            "end_time",
        ]
        read_only_fields = ["id", "experiment_id", "start_time"]

    def create(self, validated_data):
        """Create a new experiment with auto-generated experiment_id"""
        import uuid

        if "experiment_id" not in validated_data:
            validated_data["experiment_id"] = f"exp_{uuid.uuid4().hex[:8]}"
        return super().create(validated_data)


class ExperimentCreateSerializer(serializers.Serializer):
    """Serializer for creating and running experiments"""

    assistant_ids = serializers.ListField(
        child=serializers.CharField(max_length=100),
        help_text="List of assistant IDs to test",
    )
    queries = serializers.ListField(
        child=serializers.CharField(), help_text="List of queries to test"
    )
    run_immediately = serializers.BooleanField(
        default=True,
        help_text="Whether to run the experiment immediately after creation",
    )


class GoldenAnswerSerializer(serializers.ModelSerializer):
    """Serializer for GoldenAnswer model"""

    class Meta:
        model = GoldenAnswer
        fields = [
            "id",
            "model_name",
            "question_hash",
            "question",
            "answer",
            "success",
            "updated_at",
            "started_at",
            "ended_at",
        ]
        read_only_fields = ["id", "question_hash", "updated_at"]


class AssistantResponseSerializer(serializers.ModelSerializer):
    """Serializer for AssistantResponse model"""

    experiment_id = serializers.CharField(
        source="experiment.experiment_id", read_only=True
    )

    class Meta:
        model = AssistantResponse
        fields = [
            "id",
            "experiment_id",
            "question",
            "assistant_id",
            "chat_id",
            "answer",
            "processed_answer",
            "hallucination_level",
            "hallucination_reason",
            "references",
            "debug_info",
            "success",
            "started_at",
            "ended_at",
        ]
        read_only_fields = ["id"]


class ExperimentDetailSerializer(ExperimentSerializer):
    """Detailed serializer for Experiment with related responses"""

    responses = AssistantResponseSerializer(many=True, read_only=True)

    class Meta(ExperimentSerializer.Meta):
        fields = ExperimentSerializer.Meta.fields + ["responses"]


class ExperimentStatsSerializer(serializers.Serializer):
    """Serializer for experiment statistics"""

    experiment_id = serializers.CharField()
    total_queries = serializers.IntegerField()
    total_assistants = serializers.IntegerField()
    total_responses = serializers.IntegerField()
    completed_responses = serializers.IntegerField()
    failed_responses = serializers.IntegerField()
    success_rate = serializers.FloatField()
    average_response_time = serializers.FloatField(allow_null=True)
    status = serializers.CharField()  # 'running', 'completed', 'failed'


class ConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for system configuration"""

    class Meta:
        model = Configuration
        fields = [
            "id",
            "user_id",
            "company_id",
            "app_id",
            "api_key",
            "base_url",
            "timeout",
            "default_golden_model",
            "is_configured",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_configured", "created_at", "updated_at"]

    def create(self, validated_data):
        """Override create to use singleton pattern"""
        config = Configuration.get_instance()
        for attr, value in validated_data.items():
            setattr(config, attr, value)
        config.save()
        return config

    def update(self, instance, validated_data):
        """Update the configuration instance"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ConfigurationStatusSerializer(serializers.Serializer):
    """Serializer for configuration status check"""

    is_configured = serializers.BooleanField()
    missing_fields = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    message = serializers.CharField()
