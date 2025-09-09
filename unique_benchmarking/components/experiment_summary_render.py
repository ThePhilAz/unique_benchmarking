from collections import defaultdict
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from schemas import ExperimentSummary, ExperimentResult
from pydantic import BaseModel
from typing import List
from markdown import markdown


def hallucination_level_to_emoji(hallucination_level: str) -> str:
    if hallucination_level == "GREEN":
        return "🟢"
    elif hallucination_level == "YELLOW":
        return "🟡"
    elif hallucination_level == "RED":
        return "🔴"
    else:
        return "❌"


class AssistantResult(BaseModel):
    test_id: int
    assistant_id: str
    chat_id: str
    status: str
    question: str
    answer: str
    hallucination_level: str
    assessment: str

    @classmethod
    def from_result(cls, result: ExperimentResult) -> "AssistantResult":
        # Process the answer text and convert basic markdown to HTML
        answer_text = (
            result.message.text if result.message and result.message.text else "N/A"
        )
        if answer_text != "N/A":
            # Simple markdown-like conversion for basic formatting
            answer_html = markdown(answer_text, output_format="html")
        else:
            answer_html = answer_text

        return cls(
            test_id=result.test_id,
            assistant_id=result.assistant_id,
            chat_id=result.message.chatId if result.message else "N/A",
            status="✅" if result.success else "❌",
            question=result.question,
            answer=answer_html,
            hallucination_level=hallucination_level_to_emoji(
                result.message.assessment[0].label
                if result.message and result.message.assessment
                else "N/A"
            ),
            assessment=result.message.assessment[0].label
            if result.message and result.message.assessment
            else "N/A",
        )


class ExperimentSummaryRender(BaseModel):
    total_tests: int
    completed_tests: int
    failed_tests: int
    average_time_per_assistant: dict[str, dict[str, float]]
    results: List[AssistantResult]

    @classmethod
    def from_summary(cls, summary: ExperimentSummary) -> "ExperimentSummaryRender":
        time_data = cls._aggregate_time_metrics(summary.results)

        return cls(
            total_tests=summary.total_tests,
            completed_tests=summary.completed_tests,
            failed_tests=summary.failed_tests,
            average_time_per_assistant=time_data,
            results=[AssistantResult.from_result(r) for r in summary.results],
        )

    @staticmethod
    def _aggregate_time_metrics(
        results: List[ExperimentResult],
    ) -> dict[str, dict[str, float]]:
        """Aggregate time metrics per assistant with improved efficiency and error handling."""
        # Collect all time data in a single pass
        time_collections = {
            "search_time": defaultdict(list),
            "crawl_time": defaultdict(list),
            "execution_time": defaultdict(list),
        }

        for result in results:
            assistant_id = result.assistant_id

            # Collect tool-based timing data
            if (
                result.message
                and result.message.debugInfo
                and result.message.debugInfo.tools
            ):
                for tool in result.message.debugInfo.tools:
                    if hasattr(tool, "time_info") and tool.time_info:
                        if tool.time_info.search_time:
                            time_collections["search_time"][assistant_id].append(
                                tool.time_info.search_time
                            )
                        if tool.time_info.crawl_time:
                            time_collections["crawl_time"][assistant_id].append(
                                tool.time_info.crawl_time
                            )

            # Collect execution time
            if result.execution_time:
                time_collections["execution_time"][assistant_id].append(
                    result.execution_time
                )

        # Build simplified structure: assistant_id -> {time_type: average_time}
        assistant_times = defaultdict(dict)

        # Get all unique assistant IDs
        all_assistants = set()
        for time_data in time_collections.values():
            all_assistants.update(time_data.keys())

        # Calculate averages for each assistant and time type
        for assistant_id in all_assistants:
            for time_type, time_data in time_collections.items():
                if assistant_id in time_data and time_data[assistant_id]:
                    assistant_times[assistant_id][time_type] = sum(
                        time_data[assistant_id]
                    ) / len(time_data[assistant_id])
                else:
                    assistant_times[assistant_id][time_type] = 0.0

        return dict(assistant_times)


def render_experiment_summary(summary: ExperimentSummary) -> str:
    """Render the experiment summary using the new question-centric format if available."""
    cwd = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(cwd))
    
    # Check if we have question_results (new format)
    if hasattr(summary, 'question_results') and summary.question_results:
        template = env.get_template("experiment_summary_template.j2")
        summary = summary.prepare_to_html()
        # Calculate time metrics from the results for compatibility
        time_data = {}
        if summary.results:  # Use legacy results if available
            time_data = ExperimentSummaryRender._aggregate_time_metrics(summary.results)
        
        # Prepare data for question-centric template
        template_data = {
            "total_tests": summary.total_tests,
            "completed_tests": summary.completed_tests,
            "failed_tests": summary.failed_tests,
            "success_rate": (summary.completed_tests / summary.total_tests * 100) if summary.total_tests > 0 else 0,
            "question_results": summary.question_results,
            "has_question_results": True,
            "average_time_per_assistant": time_data  # Include for template compatibility
        }
        
        return template.render(**template_data)
    else:
        # Fallback to old format
        template = env.get_template("experiment_summary_template.j2")
        data = ExperimentSummaryRender.from_summary(summary)
        render_data = data.model_dump()
        render_data["has_question_results"] = False
        return template.render(**render_data)
