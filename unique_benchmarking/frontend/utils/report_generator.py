"""
Enhanced Report Generator for Experiment Results
"""

import os
from datetime import datetime
from typing import Dict, List, Any
from jinja2 import Environment, FileSystemLoader
import hashlib
import re
import markdown as md


class EnhancedReportGenerator:
    """Enhanced report generator with multi-dimensional evaluation and offline capabilities"""

    def __init__(self):
        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "../../../templates")
        self.env = Environment(loader=FileSystemLoader(template_dir))

        # Chart.js content for offline functionality
        self.chart_js_content = self._get_chart_js_content()

    def _get_chart_js_content(self) -> str:
        """Get Chart.js content for embedding (placeholder for now)"""
        # In production, this would contain the actual Chart.js library
        # For now, return a placeholder that creates a basic charting capability
        return """
        // Embedded Chart.js alternative - basic charting functionality
        class Chart {
            constructor(ctx, config) {
                this.ctx = ctx;
                this.config = config;
                this.render();
            }
            
            render() {
                const canvas = this.ctx.canvas;
                canvas.style.background = '#f8f9fa';
                canvas.style.border = '1px solid #dee2e6';
                canvas.style.borderRadius = '4px';
                
                // Simple text-based chart placeholder
                const ctx = this.ctx;
                ctx.font = '14px Arial';
                ctx.fillStyle = '#333';
                ctx.textAlign = 'center';
                ctx.fillText('Performance Chart', canvas.width / 2, canvas.height / 2 - 10);
                ctx.fillText('(Chart.js would render here)', canvas.width / 2, canvas.height / 2 + 10);
            }
        }
        """

    def generate_enhanced_report(
        self,
        experiment_data: Dict[str, Any],
        responses_data: List[Dict[str, Any]],
        golden_answers_data: List[Dict[str, Any]] | None = None,
    ) -> str:
        """
        Generate an enhanced HTML report with multi-dimensional evaluation

        Args:
            experiment_data: Experiment metadata
            responses_data: List of assistant responses
            golden_answers_data: List of golden answers (optional)

        Returns:
            Complete HTML report as string
        """

        # Process and structure the data
        processed_data = self._process_experiment_data(
            experiment_data, responses_data, golden_answers_data
        )

        # Load and render the template
        template = self.env.get_template("enhanced_summary.html")

        # Add Chart.js content and other template variables
        template_vars = {
            **processed_data,
            "chart_js_content": self.chart_js_content,
            "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "experiment_duration": self._calculate_duration(
                experiment_data.get("start_time"), experiment_data.get("end_time")
            ),
        }

        return template.render(**template_vars)

    def _process_experiment_data(
        self,
        experiment_data: Dict[str, Any],
        responses_data: List[Dict[str, Any]],
        golden_answers_data: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """Process raw experiment data into template-ready format"""

        # Basic experiment info
        experiment_id = experiment_data.get("experiment_id", "Unknown")
        experiment_name = f"Experiment_{experiment_id}"
        experiment_name_clean = self._clean_filename(experiment_name)

        # Calculate basic metrics
        total_tests = len(responses_data)
        completed_tests = len([r for r in responses_data if r.get("success", False)])
        failed_tests = total_tests - completed_tests
        success_rate = (completed_tests / total_tests * 100) if total_tests > 0 else 0

        # Create golden answers lookup
        golden_answers_lookup = {}
        if golden_answers_data:
            for ga in golden_answers_data:
                question = ga.get("question", "")
                raw_answer = ga.get("answer", "")
                golden_answers_lookup[question] = {
                    "answer": self._convert_markdown_to_html(raw_answer),
                    "raw_answer": raw_answer,
                    "model": ga.get("model_name", "Unknown"),
                    "generation_time": self._calculate_response_time(
                        ga.get("started_at"), ga.get("ended_at")
                    ),
                }

        # Group responses by question for question-centric view
        questions_map = {}
        for response in responses_data:
            question = response.get("question", "")
            if question not in questions_map:
                questions_map[question] = {
                    "question": question,
                    "assistant_results": [],
                    "total_assistants": 0,
                    "successful_assistants": 0,
                    "failed_assistants": 0,
                    "golden_answer": golden_answers_lookup.get(question),
                }

            # Add test_id for evaluation tracking
            test_id = self._generate_test_id(response)

            assistant_result = {
                "test_id": test_id,
                "assistant_id": response.get("assistant_id", ""),
                "success": response.get("success", False),
                "execution_time": self._calculate_response_time(
                    response.get("started_at"), response.get("ended_at")
                ),
                "message": self._process_message_data(response),
            }

            questions_map[question]["assistant_results"].append(assistant_result)
            questions_map[question]["total_assistants"] += 1
            if response.get("success", False):
                questions_map[question]["successful_assistants"] += 1
            else:
                questions_map[question]["failed_assistants"] += 1

        # Calculate success rates for each question
        question_results = []
        for question_data in questions_map.values():
            total = question_data["total_assistants"]
            successful = question_data["successful_assistants"]
            question_data["success_rate"] = (
                (successful / total * 100) if total > 0 else 0
            )
            question_results.append(question_data)

        # Sort questions by success rate (lowest first for attention)
        question_results.sort(key=lambda x: x["success_rate"])

        # Calculate average times per assistant (if available)
        average_time_per_assistant = self._calculate_average_times(responses_data)

        return {
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "experiment_name_clean": experiment_name_clean,
            "start_time": self._format_datetime(experiment_data.get("start_time")),
            "end_time": self._format_datetime(experiment_data.get("end_time")),
            "total_tests": total_tests,
            "completed_tests": completed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "question_results": question_results,
            "has_question_results": len(question_results) > 0,
            "average_time_per_assistant": average_time_per_assistant,
            "results": self._format_legacy_results(
                responses_data
            ),  # For backward compatibility
        }

    def _process_message_data(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process message data from response"""
        raw_text = response.get("processed_answer", response.get("answer", ""))
        return {
            "chatId": response.get("chat_id", ""),
            "text": self._convert_markdown_to_html(raw_text),
            "raw_text": raw_text,
            "assessment": self._process_assessment(response),
            "references": self._process_references(response),
        }

    def _process_assessment(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process hallucination assessment data"""
        if response.get("hallucination_level"):
            return [
                {
                    "label": response.get("hallucination_level", "UNKNOWN"),
                    "explanation": response.get("hallucination_reason", ""),
                }
            ]
        return []

    def _process_references(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process references data with markdown conversion"""
        references = response.get("references", [])
        if not references:
            return []

        processed_refs = []
        for ref in references:
            if isinstance(ref, dict):
                # Convert any text content in references to HTML
                processed_ref = {}
                for key, value in ref.items():
                    if isinstance(value, str) and key in [
                        "title",
                        "description",
                        "content",
                        "snippet",
                    ]:
                        processed_ref[key] = self._convert_markdown_to_html(value)
                        processed_ref[f"raw_{key}"] = value
                    else:
                        processed_ref[key] = value
                processed_refs.append(processed_ref)
            elif isinstance(ref, str):
                # If reference is just a string, convert it to HTML
                processed_refs.append(
                    {"text": self._convert_markdown_to_html(ref), "raw_text": ref}
                )
            else:
                processed_refs.append(ref)

        return processed_refs

    def _generate_test_id(self, response: Dict[str, Any]) -> str:
        """Generate unique test ID for evaluation tracking"""
        # Create a unique ID based on assistant_id, question, and chat_id
        identifier = f"{response.get('assistant_id', '')}_{response.get('question', '')}_{response.get('chat_id', '')}"
        return hashlib.md5(identifier.encode()).hexdigest()[:12]

    def _calculate_average_times(
        self, responses_data: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate average response times per assistant"""
        assistant_times = {}

        for response in responses_data:
            assistant_id = response.get("assistant_id", "")
            if assistant_id not in assistant_times:
                assistant_times[assistant_id] = {
                    "search_time": [],
                    "crawl_time": [],
                    "execution_time": [],
                    "total_time": [],
                }

            # Extract timing data if available from debug_info
            debug_info = response.get("debug_info", {})
            if isinstance(debug_info, dict):
                assistant_times[assistant_id]["search_time"].append(
                    debug_info.get("search_time", 0)
                )
                assistant_times[assistant_id]["crawl_time"].append(
                    debug_info.get("crawl_time", 0)
                )

            # Calculate execution time from timestamps
            execution_time = self._calculate_response_time(
                response.get("started_at"), response.get("ended_at")
            )
            assistant_times[assistant_id]["execution_time"].append(execution_time)

        # Calculate averages
        averages = {}
        for assistant_id, times in assistant_times.items():
            averages[assistant_id] = {}
            for time_type, time_list in times.items():
                if time_list and any(t > 0 for t in time_list):
                    averages[assistant_id][time_type] = sum(time_list) / len(time_list)
                else:
                    averages[assistant_id][time_type] = 0.0

        return (
            averages if any(any(times.values()) for times in averages.values()) else {}
        )

    def _format_legacy_results(
        self, responses_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format results for legacy template compatibility"""
        legacy_results = []

        for response in responses_data:
            raw_answer = response.get("processed_answer", response.get("answer", ""))
            legacy_result = {
                "test_id": self._generate_test_id(response),
                "assistant_id": response.get("assistant_id", ""),
                "chat_id": response.get("chat_id", ""),
                "status": "✅" if response.get("success", False) else "❌",
                "question": response.get("question", ""),
                "answer": self._convert_markdown_to_html(raw_answer),
                "raw_answer": raw_answer,
                "hallucination_level": response.get("hallucination_level", ""),
                "assessment": self._format_assessment_text(response),
            }
            legacy_results.append(legacy_result)

        return legacy_results

    def _format_assessment_text(self, response: Dict[str, Any]) -> str:
        """Format assessment for display"""
        level = response.get("hallucination_level", "")
        if level == "GREEN":
            return "🟢 Low Risk"
        elif level == "YELLOW":
            return "🟡 Medium Risk"
        elif level == "RED":
            return "🔴 High Risk"
        else:
            return "❓ Not Assessed"

    def _calculate_response_time(
        self, start_time: str | None, end_time: str | None
    ) -> float:
        """Calculate response time in seconds"""
        if not start_time or not end_time:
            return 0.0

        try:
            from dateutil.parser import parse

            start = parse(start_time)
            end = parse(end_time)
            return (end - start).total_seconds()
        except Exception:
            return 0.0

    def _calculate_duration(self, start_time: str | None, end_time: str | None) -> str:
        """Calculate and format experiment duration"""
        if not start_time or not end_time:
            return "Unknown"

        try:
            from dateutil.parser import parse

            start = parse(start_time)
            end = parse(end_time)
            duration = end - start

            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours > 0:
                return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            elif minutes > 0:
                return f"{int(minutes)}m {int(seconds)}s"
            else:
                return f"{int(seconds)}s"
        except Exception:
            return "Unknown"

    def _format_datetime(self, datetime_str: str | None) -> str:
        """Format datetime string for display"""
        if not datetime_str:
            return "Unknown"

        try:
            from dateutil.parser import parse

            dt = parse(datetime_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime_str

    def _convert_markdown_to_html(self, text: str) -> str:
        """Convert markdown text to HTML"""
        if not text:
            return ""

        try:
            html = md.markdown(
                text, extensions=["tables", "fenced_code", "nl2br"], tab_length=2
            )
            return html
        except Exception:
            # Fallback to basic conversion if markdown library fails
            pass

        # Basic markdown to HTML conversion (fallback)
        html = text

        # Headers
        html = re.sub(r"^### (.*?)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.*?)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.*?)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)

        # Links
        html = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank">\1</a>', html
        )

        # Lists
        lines = html.split("\n")
        in_list = False
        result_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                if not in_list:
                    result_lines.append("<ul>")
                    in_list = True
                result_lines.append(f"<li>{stripped[2:].strip()}</li>")
            elif stripped.startswith(
                ("1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. ")
            ):
                if not in_list:
                    result_lines.append("<ol>")
                    in_list = True
                result_lines.append(f"<li>{stripped[3:].strip()}</li>")
            else:
                if in_list:
                    result_lines.append(
                        "</ul>" if result_lines[-2].startswith("<li>") else "</ol>"
                    )
                    in_list = False
                if stripped:
                    result_lines.append(f"<p>{stripped}</p>")
                else:
                    result_lines.append("<br>")

        if in_list:
            result_lines.append("</ul>")

        # Code blocks
        html = "\n".join(result_lines)
        html = re.sub(
            r"```([^`]+)```", r"<pre><code>\1</code></pre>", html, flags=re.DOTALL
        )
        html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

        # Line breaks
        html = html.replace("\n", "<br>\n")

        return html

    def _clean_filename(self, filename: str) -> str:
        """Clean filename for safe file operations"""
        import re

        # Remove or replace invalid characters
        cleaned = re.sub(r'[<>:"/\\|?*]', "_", filename)
        # Remove extra spaces and limit length
        cleaned = re.sub(r"\s+", "_", cleaned.strip())[:50]
        return cleaned

    def save_report(
        self, html_content: str, filename: str, output_dir: str | None = None
    ) -> str:
        """Save HTML report to file"""
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "../../../reports")

        os.makedirs(output_dir, exist_ok=True)

        # Ensure .html extension
        if not filename.endswith(".html"):
            filename += ".html"

        file_path = os.path.join(output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return file_path

    def generate_and_save_report(
        self,
        experiment_data: Dict[str, Any],
        responses_data: List[Dict[str, Any]],
        golden_answers_data: List[Dict[str, Any]] | None = None,
        output_dir: str | None = None,
    ) -> str:
        """Generate and save enhanced report in one step"""

        html_content = self.generate_enhanced_report(
            experiment_data, responses_data, golden_answers_data
        )

        experiment_id = experiment_data.get("experiment_id", "unknown")
        filename = f"enhanced_report_{experiment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        return self.save_report(html_content, filename, output_dir)


def generate_experiment_report(
    experiment_data: Dict[str, Any],
    responses_data: List[Dict[str, Any]],
    golden_answers_data: List[Dict[str, Any]] | None = None,
) -> str:
    """Convenience function to generate enhanced experiment report"""
    generator = EnhancedReportGenerator()
    return generator.generate_enhanced_report(
        experiment_data, responses_data, golden_answers_data
    )


def generate_and_save_experiment_report(
    experiment_data: Dict[str, Any],
    responses_data: List[Dict[str, Any]],
    golden_answers_data: List[Dict[str, Any]] | None = None,
    output_dir: str | None = None,
) -> str:
    """Convenience function to generate and save enhanced experiment report"""
    generator = EnhancedReportGenerator()
    return generator.generate_and_save_report(
        experiment_data, responses_data, golden_answers_data, output_dir
    )
