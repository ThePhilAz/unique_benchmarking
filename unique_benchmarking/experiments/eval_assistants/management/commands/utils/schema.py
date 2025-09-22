from pydantic import BaseModel, field_validator
from typing import Literal, List
from unique_toolkit.chat.schemas import ContentReference
from unique_toolkit.agentic.evaluation.schemas import EvaluationAssessmentMessage
import re
from markdown import markdown


class Message(BaseModel):
    """Represents a message in the space."""

    id: str
    chatId: str
    text: str | None
    originalText: str | None
    role: Literal["system", "user", "assistant"]
    debugInfo: dict | None
    completedAt: str | None
    createdAt: str | None
    updatedAt: str | None
    stoppedStreamingAt: str | None
    references: list[ContentReference]
    assessment: list[EvaluationAssessmentMessage]

    @field_validator("role", mode="before")
    def validate_role(cls, v):
        return v.lower()

    def get_optimized_text(self):
        def process_assistant_message(
            text: str, references: List[ContentReference]
        ) -> str:
            """
            Process the assistant's message and return the results.
            """
            refences_map = {
                reference.sequence_number: f"([{reference.name}]({reference.url}))"
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
            return process_assistant_message(self.text, self.references)

        return self.text

    def prepare_to_html(self):
        """Prepare the message to be used in the HTML report."""
        if self.text:
            self.text = markdown(self.text, output_format="html")
        return self
