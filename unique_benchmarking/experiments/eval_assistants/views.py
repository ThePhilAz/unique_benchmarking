"""
API views for the eval_assistants app
"""

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request

from .models import Experiment, GoldenAnswer, AssistantResponse, Configuration
from .serializers import (
    ExperimentSerializer,
    ExperimentDetailSerializer,
    ExperimentCreateSerializer,
    ExperimentStatsSerializer,
    GoldenAnswerSerializer,
    AssistantResponseSerializer,
    ConfigurationSerializer,
    ConfigurationStatusSerializer,
)
from .management.commands.run_experiment import ExperimentRunner
from logging import getLogger


logger = getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ExperimentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing experiments

    Provides:
    - List experiments: GET /api/experiments/
    - Create experiment: POST /api/experiments/
    - Get experiment details: GET /api/experiments/{id}/
    - Update experiment: PUT/PATCH /api/experiments/{id}/
    - Delete experiment: DELETE /api/experiments/{id}/
    - Run experiment: POST /api/experiments/{id}/run/
    - Get experiment stats: GET /api/experiments/{id}/stats/
    """

    queryset = Experiment.objects.all()
    serializer_class = ExperimentSerializer
    pagination_class = StandardResultsSetPagination
    lookup_field = "experiment_id"  # Use experiment_id instead of pk

    def get_serializer_class(self):  # type: ignore
        """Return appropriate serializer based on action"""
        if self.action == "retrieve":
            return ExperimentDetailSerializer
        elif self.action == "create_and_run":
            return ExperimentCreateSerializer
        return ExperimentSerializer

    def get_queryset(self):  # type: ignore
        """Filter experiments by query parameters"""
        queryset = Experiment.objects.all().order_by("-start_time")
        request: Request = self.request  # type: ignore

        # Filter by user_id
        user_id = request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by company_id
        company_id = request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        # Filter by status
        status_filter = request.query_params.get("status")
        if status_filter == "running":
            queryset = queryset.filter(end_time__isnull=True)
        elif status_filter == "completed":
            queryset = queryset.filter(end_time__isnull=False)

        return queryset

    @action(detail=False, methods=["post"])
    def create_and_run(self, request: Request):
        """
        Create a new experiment and optionally run it immediately

        POST /api/experiments/create_and_run/
        """
        serializer = ExperimentCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            try:
                assert isinstance(data, dict)

                # Create experiment
                runner = ExperimentRunner()
                experiment_id = runner.initialize_experiment(
                    assistant_ids=data["assistant_ids"],
                    queries=data["queries"],
                )

                experiment = runner.experiment

                # Run experiment if requested
                if isinstance(data, dict) and data.get("run_immediately", True):
                    stats = runner.run_experiment()

                    return Response(
                        {
                            "experiment": ExperimentDetailSerializer(experiment).data,
                            "stats": stats,
                            "message": f"Experiment {experiment_id} completed successfully",
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    return Response(
                        {
                            "experiment": ExperimentSerializer(experiment).data,
                            "message": f"Experiment {experiment_id} created successfully",
                        },
                        status=status.HTTP_201_CREATED,
                    )

            except Exception as e:
                logger.exception(f"Failed to create/run experiment: {str(e)}")
                return Response(
                    {"error": f"Failed to create/run experiment: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def run(self, request, experiment_id=None):
        """
        Run an existing experiment

        POST /api/experiments/{experiment_id}/run/
        """
        try:
            experiment = self.get_object()

            # Check if experiment is already running
            if experiment.end_time is None and experiment.responses.exists():
                return Response(
                    {"error": "Experiment is already running"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Initialize runner configuration only (don't create new experiment)
            runner = ExperimentRunner()
            runner.initialize_runner_only()
            
            # Use the existing experiment
            runner.experiment = experiment

            # Reset experiment timing
            experiment.start_time = timezone.now()
            experiment.end_time = None
            experiment.save()

            # Clear previous responses if any
            experiment.responses.all().delete()

            # Run experiment
            logger.info(f"Starting experiment run for {experiment_id}")
            stats = runner.run_experiment()
            logger.info(f"Experiment run completed for {experiment_id}")

            return Response(
                {
                    "experiment": ExperimentDetailSerializer(experiment).data,
                    "stats": stats,
                    "message": f"Experiment {experiment_id} completed successfully",
                }
            )

        except Exception as e:
            logger.exception(f"Failed to run experiment {experiment_id}: {str(e)}")
            return Response(
                {"error": f"Failed to run experiment: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def stats(self, request, experiment_id=None):
        """
        Get experiment statistics

        GET /api/experiments/{experiment_id}/stats/
        """
        experiment = self.get_object()

        responses = experiment.responses.all()
        total_responses = responses.count()
        completed_responses = responses.filter(success=True).count()
        failed_responses = total_responses - completed_responses

        # Calculate average response time
        avg_response_time = None
        if total_responses > 0:
            response_times = []
            for response in responses:
                if response.started_at and response.ended_at:
                    duration = (response.ended_at - response.started_at).total_seconds()
                    response_times.append(duration)

            if response_times:
                avg_response_time = sum(response_times) / len(response_times)

        # Determine status
        if experiment.end_time is None:
            exp_status = "running" if total_responses > 0 else "created"
        else:
            exp_status = "completed"

        stats_data = {
            "experiment_id": experiment.experiment_id,
            "total_queries": len(experiment.queries),
            "total_assistants": len(experiment.assistant_ids),
            "total_responses": total_responses,
            "completed_responses": completed_responses,
            "failed_responses": failed_responses,
            "success_rate": (completed_responses / total_responses * 100)
            if total_responses > 0
            else 0,
            "average_response_time": avg_response_time,
            "status": exp_status,
        }

        serializer = ExperimentStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def progress(self, request, experiment_id=None):
        """
        Get experiment progress information

        GET /api/experiments/{experiment_id}/progress/
        """
        experiment = self.get_object()

        # Calculate time-based metrics
        elapsed_time = None
        eta_seconds = None

        if experiment.start_time:
            from django.utils import timezone

            elapsed_time = (timezone.now() - experiment.start_time).total_seconds()

            if experiment.estimated_completion:
                eta_seconds = (
                    experiment.estimated_completion - timezone.now()
                ).total_seconds()
                eta_seconds = max(0, eta_seconds)  # Don't show negative ETA

        progress_data = {
            "experiment_id": experiment.experiment_id,
            "status": experiment.status,
            "progress_percentage": experiment.progress_percentage,
            "current_step": experiment.current_step,
            "total_tasks": experiment.total_tasks,
            "completed_tasks": experiment.completed_tasks,
            "elapsed_time_seconds": elapsed_time,
            "eta_seconds": eta_seconds,
            "estimated_completion": experiment.estimated_completion.isoformat()
            if experiment.estimated_completion
            else None,
            "last_updated": experiment.last_updated.isoformat()
            if experiment.last_updated
            else None,
            "start_time": experiment.start_time.isoformat()
            if experiment.start_time
            else None,
            "end_time": experiment.end_time.isoformat()
            if experiment.end_time
            else None,
        }

        return Response(progress_data)


class GoldenAnswerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing golden answers

    Provides CRUD operations for golden answers
    """

    queryset = GoldenAnswer.objects.all().order_by("-updated_at")
    serializer_class = GoldenAnswerSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):  # type: ignore
        """Filter golden answers by query parameters"""
        queryset = GoldenAnswer.objects.all().order_by("-updated_at")
        request: Request = self.request  # type: ignore

        # Filter by model
        model_name = request.query_params.get("model")
        if model_name:
            queryset = queryset.filter(model_name=model_name)

        # Search in question text
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(question__icontains=search)

        return queryset


class AssistantResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing assistant responses

    Read-only access to assistant responses
    """

    queryset = AssistantResponse.objects.all().order_by("-started_at")
    serializer_class = AssistantResponseSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):  # type: ignore
        """Filter responses by query parameters"""
        queryset = AssistantResponse.objects.all().order_by("-started_at")
        request: Request = self.request  # type: ignore
        # Filter by experiment
        experiment_id = request.query_params.get("experiment_id")
        if experiment_id:
            queryset = queryset.filter(experiment__experiment_id=experiment_id)

        # Filter by assistant
        assistant_id = request.query_params.get("assistant_id")
        if assistant_id:
            queryset = queryset.filter(assistant_id=assistant_id)

        # Filter by success
        success = request.query_params.get("success")
        if success is not None:
            success_bool = success.lower() in ("true", "1", "yes")
            queryset = queryset.filter(success=success_bool)

        return queryset


class ConfigurationViewSet(viewsets.ViewSet):
    """
    ViewSet for managing system configuration

    Simple storage for last committed configuration from frontend
    """

    @action(detail=False, methods=["get"])
    def status(self, request):
        """
        Check configuration status

        GET /api/configuration/status/
        """
        config = Configuration.get_instance()

        required_fields = ["user_id", "company_id", "app_id", "api_key", "base_url"]
        missing_fields = []

        for field in required_fields:
            if not getattr(config, field, None):
                missing_fields.append(field)

        is_configured = len(missing_fields) == 0

        if is_configured:
            message = "System is properly configured and ready to use."
        else:
            message = f"System configuration is incomplete. Missing: {', '.join(missing_fields)}"

        data = {
            "is_configured": is_configured,
            "missing_fields": missing_fields,
            "message": message,
        }

        serializer = ConfigurationStatusSerializer(data)
        return Response(serializer.data)

    def list(self, request):
        """
        Get current configuration

        GET /api/configuration/
        """
        config = Configuration.get_instance()
        serializer = ConfigurationSerializer(config)
        return Response(serializer.data)

    def create(self, request):
        """
        Save configuration from frontend

        POST /api/configuration/
        """
        config = Configuration.get_instance()
        serializer = ConfigurationSerializer(config, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Configuration saved successfully",
                    "is_configured": config.is_configured,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """
        Update configuration

        PUT /api/configuration/1/
        """
        config = Configuration.get_instance()
        serializer = ConfigurationSerializer(config, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Configuration updated successfully",
                    "is_configured": config.is_configured,
                }
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        """
        Partially update configuration

        PATCH /api/configuration/1/
        """
        return self.update(request, pk)

    @action(detail=False, methods=["post"])
    def initialize_from_env(self, request):
        """
        Initialize configuration from environment variables

        POST /api/configuration/initialize_from_env/
        """
        import os
        from dotenv import load_dotenv

        # Load environment variables
        env_path = os.path.join(os.path.dirname(__file__), "../../../../unique.env")
        load_dotenv(env_path)

        config = Configuration.get_instance()

        # Update from environment variables if they exist
        env_mapping = {
            "user_id": "USER_ID",
            "company_id": "COMPANY_ID",
            "app_id": "APP_ID",
            "api_key": "API_KEY",
            "base_url": "BASE_URL",
            "timeout": "TIMEOUT",
        }

        updated_fields = []
        for field, env_var in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value:
                if field == "timeout":
                    env_value = int(env_value)
                setattr(config, field, env_value)
                updated_fields.append(field)

        config.save()

        return Response(
            {
                "message": "Configuration initialized from environment variables",
                "updated_fields": updated_fields,
                "is_configured": config.is_configured,
            }
        )
