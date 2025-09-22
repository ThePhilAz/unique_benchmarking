from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import hashlib


class Experiment(models.Model):
    """Model to track experiment runs"""

    experiment_id = models.CharField(max_length=100, unique=True, db_index=True)
    assistant_ids = models.JSONField(
        default=list, help_text="List of assistant IDs tested"
    )
    user_id = models.CharField(max_length=100, help_text="User ID")
    company_id = models.CharField(max_length=100, help_text="Company ID")
    queries = models.JSONField(default=list, help_text="List of queries tested")
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(blank=True, null=True)

    # Progress tracking fields
    status = models.CharField(
        max_length=20,
        default="created",
        choices=[
            ("created", "Created"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        help_text="Current experiment status",
    )
    progress_percentage = models.FloatField(
        default=0.0, help_text="Progress percentage (0-100)"
    )
    current_step = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Description of current step being executed",
    )
    total_tasks = models.IntegerField(
        default=0, help_text="Total number of tasks to complete"
    )
    completed_tasks = models.IntegerField(
        default=0, help_text="Number of completed tasks"
    )
    estimated_completion = models.DateTimeField(
        blank=True, null=True, help_text="Estimated completion time"
    )
    last_updated = models.DateTimeField(
        auto_now=True, help_text="Last time progress was updated"
    )

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        return f"Experiment {self.experiment_id}"

    def update_progress(self, completed_tasks=None, current_step=None, status=None):
        """Update experiment progress"""
        if completed_tasks is not None:
            self.completed_tasks = completed_tasks
            if self.total_tasks > 0:
                self.progress_percentage = (completed_tasks / self.total_tasks) * 100

        if current_step is not None:
            self.current_step = current_step

        if status is not None:
            self.status = status

        # Update estimated completion time
        if self.progress_percentage > 0 and self.status == "running":
            from django.utils import timezone

            elapsed_time = timezone.now() - self.start_time
            total_estimated_time = elapsed_time * (100 / self.progress_percentage)
            self.estimated_completion = self.start_time + total_estimated_time

        self.save()

    def initialize_progress(self, total_tasks):
        """Initialize progress tracking for the experiment"""
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.progress_percentage = 0.0
        self.status = "running"
        self.current_step = "Initializing experiment..."
        self.save()

    def complete_experiment(self):
        """Mark experiment as completed"""
        from django.utils import timezone

        self.end_time = timezone.now()
        self.status = "completed"
        self.progress_percentage = 100.0
        self.current_step = "Experiment completed"
        self.estimated_completion = None
        self.save()

    def fail_experiment(self, error_message=None):
        """Mark experiment as failed"""
        from django.utils import timezone

        self.end_time = timezone.now()
        self.status = "failed"
        self.current_step = (
            f"Failed: {error_message}" if error_message else "Experiment failed"
        )
        self.estimated_completion = None
        self.save()


class GoldenAnswer(models.Model):
    """Model to store golden answers for queries"""

    model_name = models.CharField(
        max_length=100, help_text="Model used to generate the answer"
    )
    question_hash = models.CharField(max_length=64, unique=True, db_index=True)
    question = models.TextField()
    answer = models.TextField()
    success = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Golden Answer: {str(self.answer)[:50]}..."

    @staticmethod
    def _get_question_hash(question: str, model_name: str) -> str:
        """Generate hash for a question"""
        str_to_hash = f"{question} - {model_name}"
        return hashlib.sha256(str(str_to_hash).encode()).hexdigest()

    def save(self, *args, **kwargs):
        # Generate hash of question for fast lookups
        if self.question:
            self.question_hash = self._get_question_hash(
                str(self.question), self.model_name
            )
        super().save(*args, **kwargs)


class AssistantResponse(models.Model):
    """Model to store assistant responses to queries"""

    experiment = models.ForeignKey(
        Experiment, on_delete=models.CASCADE, related_name="responses"
    )
    chat_id = models.CharField(max_length=100)
    question = models.TextField()
    assistant_id = models.CharField(max_length=100)
    answer = models.TextField(blank=True, null=True)
    processed_answer = models.TextField(blank=True, null=True)
    debug_info = models.JSONField(default=dict, blank=True, null=True)
    hallucination_level = models.CharField(max_length=100, blank=True, null=True)
    hallucination_reason = models.TextField(blank=True, null=True)
    references = models.JSONField(default=list, blank=True, null=True)
    success = models.BooleanField()
    started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ["experiment", "assistant_id", "chat_id"]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.assistant_id}: {str(self.question)[:30]}..."


class Configuration(models.Model):
    """
    Model to store system configuration settings
    Only one instance should exist - singleton pattern
    """

    # Unique.app API Configuration
    user_id = models.CharField(max_length=100, help_text="User ID for unique.app API")
    company_id = models.CharField(
        max_length=100, help_text="Company ID for unique.app API"
    )
    app_id = models.CharField(
        max_length=100, help_text="Application ID for unique.app API"
    )
    api_key = models.CharField(max_length=200, help_text="API Key for unique.app API")
    base_url = models.URLField(
        default="https://api.uat1.unique.app/public/chat",
        help_text="Base URL for unique.app API",
    )
    timeout = models.IntegerField(default=600, help_text="API timeout in seconds")

    # Golden Answer Configuration
    default_golden_model = models.CharField(
        max_length=100,
        default="gpt-4",
        help_text="Default model for generating golden answers",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_configured = models.BooleanField(
        default=False, help_text="Whether the configuration is complete"
    )

    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configuration"

    def save(self, *args, **kwargs):
        """Ensure only one configuration instance exists"""
        if not self.pk and Configuration.objects.exists():
            raise ValidationError("Only one Configuration instance is allowed.")

        # Mark as configured if all required fields are present
        self.is_configured = all(
            [
                self.user_id,
                self.company_id,
                self.app_id,
                self.api_key,
                self.base_url,
            ]
        )

        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """Get the single configuration instance, create if doesn't exist"""
        config, created = cls.objects.get_or_create(pk=1)
        return config

    def __str__(self):
        status = "✓ Configured" if self.is_configured else "⚠ Not Configured"
        return f"System Configuration - {status}"
