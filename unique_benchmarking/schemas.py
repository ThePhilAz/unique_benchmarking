from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, List
from unique_toolkit.chat.schemas import ContentReference
from unique_toolkit.evals.schemas import EvaluationAssessmentMessage
import re


class TimeInfo(BaseModel):
    """Represents the time info in the debug info."""

    clean_time: float
    crawl_time: float
    total_time: float
    search_time: float


class SearchResult(BaseModel):
    """Represents a search result in the debug info."""

    title: str
    url: str
    content: str


class DebugInfoTool(BaseModel):
    """Represents a tool in the debug info."""

    time_info: TimeInfo
    search_query: str
    date_restrict: str
    refined_query: str
    search_results: list[SearchResult]
    num_chunks_in_final_prompts: int
    
    @model_validator(mode='before')
    def convert_key_format(cls, data):
        """Convert key from spaces to underscores format."""
        if isinstance(data, dict) and "num chunks in final prompts" in data:
            # Convert the key from spaces to underscores
            data = data.copy()  # Don't modify the original
            data["num_chunks_in_final_prompts"] = data.pop("num chunks in final prompts")
        return data
    

class DebugInfo(BaseModel):
    """Represents the debug info in the message."""

    tools: list[DebugInfoTool] | None


class Message(BaseModel):
    """Represents a message in the space."""

    id: str
    chatId: str
    text: str | None
    originalText: str | None
    role: Literal["system", "user", "assistant"]
    debugInfo: DebugInfo | None
    completedAt: str | None
    createdAt: str | None
    updatedAt: str | None
    stoppedStreamingAt: str | None
    references: list[ContentReference]
    assessment: list[EvaluationAssessmentMessage]

    @field_validator("role", mode="before")
    def validate_role(cls, v):
        return v.lower()

    def optimize_text(self):
        def process_assistant_message(
            text: str, references: List[ContentReference]
        ) -> str:
            """
            Process the assistant's message and return the results.
            """
            refences_map = {
                reference.sequence_number: f"[{reference.name}]({reference.url})"
                for reference in references
            }

            text = re.sub(
                r"<follow-up-question>.*?<\/follow-up-question>",
                "",
                text,
                flags=re.DOTALL,
            )

            for sequence_number, reference_url_markdown in refences_map.items():
                text = text.replace(
                    f"<sup>{sequence_number}</sup>", reference_url_markdown
                )
            return text

        if self.references and self.text:
            self.text = process_assistant_message(self.text, self.references)


class ExperimentResult(BaseModel):
    """Represents a single experiment result."""

    test_id: int
    assistant_id: str
    question: str
    success: bool
    error: str | None
    execution_time: float
    timestamp: str
    message: Message | None


class ExperimentSummary(BaseModel):
    """Represents the overall experiment summary."""

    total_tests: int
    completed_tests: int
    failed_tests: int
    success_rate: float
    total_execution_time: float
    start_time: str
    end_time: str | None
    results: List[ExperimentResult]
    experiment_directory: str | None = None
