"""
Experiment explorer component for browsing and analyzing experiment results.
"""

import streamlit as st
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from schemas import ExperimentResult, ExperimentSummary, QuestionResult
from components.experiment_summary_render import render_experiment_summary
import pandas as pd


class ExperimentExplorerComponent:
    """Handles experiment exploration and analysis UI."""

    @staticmethod
    def render() -> None:
        """Render the experiment explorer interface."""
        st.header("🔍 Experiment Explorer")

        # Get available experiments
        experiments = ExperimentExplorerComponent._get_available_experiments()

        if not experiments:
            st.info(
                "No experiments found. Run some experiments first to explore results."
            )
            return

        # Experiment selector
        ExperimentExplorerComponent._render_experiment_selector(experiments)

        # Show selected experiment analysis
        if (
            "selected_experiment" in st.session_state
            and st.session_state.selected_experiment
        ):
            ExperimentExplorerComponent._render_experiment_analysis()

    @staticmethod
    def _get_available_experiments() -> List[Dict[str, Any]]:
        """Get list of available experiment directories."""
        experiments_dir = Path("experiments")

        if not experiments_dir.exists():
            return []

        experiments = []

        try:
            for exp_dir in experiments_dir.iterdir():
                if exp_dir.is_dir() and exp_dir.name.startswith("experiment_"):
                    # Get experiment info
                    config_file = exp_dir / "experiment_config.json"

                    experiment_info = {
                        "name": exp_dir.name,
                        "path": str(exp_dir),
                        "date": "N/A",
                        "total_tests": 0,
                        "success_rate": 0,
                    }

                    # Try to get basic info from config
                    if config_file.exists():
                        try:
                            with open(config_file, "r") as f:
                                config_data = json.load(f)
                            experiment_info["date"] = config_data.get(
                                "created_at", "N/A"
                            )
                        except Exception:
                            pass

                    # Count actual results
                    success_dir = exp_dir / "success"
                    error_dir = exp_dir / "error"

                    success_count = 0
                    error_count = 0

                    if success_dir.exists():
                        success_count = len(
                            [
                                f
                                for f in success_dir.iterdir()
                                if f.is_file() and f.name.endswith(".json")
                            ]
                        )

                    if error_dir.exists():
                        error_count = len(
                            [
                                f
                                for f in error_dir.iterdir()
                                if f.is_file() and f.name.endswith(".json")
                            ]
                        )

                    total_tests = success_count + error_count
                    success_rate = (
                        (success_count / total_tests * 100) if total_tests > 0 else 0
                    )

                    experiment_info["total_tests"] = total_tests
                    experiment_info["success_rate"] = success_rate

                    experiments.append(experiment_info)

            # Sort by date (most recent first)
            experiments.sort(key=lambda x: x["date"], reverse=True)

        except Exception as e:
            st.error(f"Error loading experiments: {e}")

        return experiments

    @staticmethod
    def _render_experiment_selector(experiments: List[Dict[str, Any]]) -> None:
        """Render experiment selector interface."""
        st.subheader("Select Experiment to Analyze")

        # Create experiment options for selectbox
        experiment_options = []
        for exp in experiments:
            date_str = (
                exp["date"][:16]
                if exp["date"] != "N/A" and len(exp["date"]) > 16
                else exp["date"]
            )
            option_text = f"{exp['name']} ({date_str}) - {exp['total_tests']} tests, {exp['success_rate']:.1f}% success"
            experiment_options.append(option_text)

        # Experiment selector
        selected_index = st.selectbox(
            "Choose an experiment:",
            range(len(experiment_options)),
            format_func=lambda x: experiment_options[x],
            key="experiment_selector",
        )

        # Store selected experiment
        if selected_index is not None:
            selected_experiment = experiments[selected_index]
            st.session_state.selected_experiment = selected_experiment

            # Show experiment summary
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Tests", selected_experiment["total_tests"])
            with col2:
                success_count = int(
                    selected_experiment["total_tests"]
                    * selected_experiment["success_rate"]
                    / 100
                )
                st.metric("Successful", success_count)
            with col3:
                failed_count = selected_experiment["total_tests"] - success_count
                st.metric("Failed", failed_count)
            with col4:
                st.metric("Success Rate", f"{selected_experiment['success_rate']:.1f}%")

    @staticmethod
    def _render_experiment_analysis() -> None:
        """Render detailed experiment analysis."""
        if "selected_experiment" not in st.session_state:
            return

        selected_exp = st.session_state.selected_experiment
        exp_path = Path(selected_exp["path"])

        st.markdown("---")

        # Add markdown report generation button
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"📊 Analysis: {selected_exp['name']}")
        with col2:
            if st.button("📄 Export HTML Report", key="generate_markdown_btn"):
                ExperimentExplorerComponent._generate_markdown_report(
                    exp_path, selected_exp["name"]
                )

        # Load all result files
        results = ExperimentExplorerComponent._load_experiment_results(exp_path)

        if not results:
            st.warning("No result files found in this experiment.")
            return

        # Try to load experiment summary for question-centric display
        summary = ExperimentExplorerComponent._load_experiment_summary(exp_path)
        
        if summary and hasattr(summary, 'question_results') and summary.question_results:
            # New question-centric display
            ExperimentExplorerComponent._render_question_centric_results(summary)
        else:
            # Fallback to old format
            st.info("Using legacy result format (no question-centric data available)")
            # Create analysis table
            ExperimentExplorerComponent._render_analysis_table(results)

            # Show detailed results
            ExperimentExplorerComponent._render_detailed_results(results)

    @staticmethod
    def _load_experiment_results(exp_path: Path) -> List[ExperimentResult]:
        """Load all result files from an experiment directory."""
        results = []

        # Load successful results
        success_dir = exp_path / "success"
        if success_dir.exists():
            for result_file in success_dir.glob("*.json"):
                try:
                    with open(result_file, "r") as f:
                        raw_data = json.load(f)

                    # Handle nested structure with "results" key
                    if "results" in raw_data:
                        result_data = ExperimentResult.model_validate(
                            raw_data["results"]
                        )
                    else:
                        result_data = ExperimentResult.model_validate(raw_data)

                    if result_data:
                        results.append(result_data)

                except Exception as e:
                    st.warning(f"Error loading {result_file.name}: {e}")

        # Load failed results
        error_dir = exp_path / "error"
        if error_dir.exists():
            for result_file in error_dir.glob("*.json"):
                try:
                    with open(result_file, "r") as f:
                        raw_data = json.load(f)

                    # Handle nested structure with "results" key
                    if "results" in raw_data:
                        result_data = ExperimentResult.model_validate(
                            raw_data["results"]
                        )
                    else:
                        result_data = ExperimentResult.model_validate(raw_data)

                    if result_data:
                        results.append(result_data)

                except Exception as e:
                    st.warning(f"Error loading {result_file.name}: {e}")

        # Sort by test_id
        results.sort(key=lambda x: x.test_id)

        return results

    @staticmethod
    def _convert_assessment_message_to_emoji(assessment_message: str | None) -> str:
        """Convert the assessment message to an emoji."""
        if assessment_message == "GREEN":
            return "🟢"
        elif assessment_message == "YELLOW":
            return "🟡"
        elif assessment_message == "RED":
            return "🔴"
        else:
            return "❌"

    @staticmethod
    def _render_analysis_table(results: List[ExperimentResult]) -> None:
        """Render the main analysis table."""
        st.markdown("### 📋 Results Analysis Table")

        # Prepare table data
        table_data = []
        for result in results:
            message = None
            assessment_message = None
            hallucination_level = None
            if result.message and len(result.message.assessment) > 0:
                message = result.message.text
                assessment_message = result.message.assessment[0].explanation
                hallucination_level = (
                    ExperimentExplorerComponent._convert_assessment_message_to_emoji(
                        result.message.assessment[0].label
                    )
                )

            table_data.append(
                {
                    "Test #": result.test_id,
                    "Status": "✅" if result.success else "❌",
                    "Assistant ID": result.assistant_id,
                    "Question": result.question,
                    "Message": message,
                    "Hallucination Level": hallucination_level,
                    "Assesment Message": assessment_message,
                    "Duration": f"{result.execution_time:.2f}s",
                }
            )

        # Display table
        st.dataframe(table_data, width="stretch", hide_index=True)

        # Summary stats
        successful_tests = sum(1 for r in results if r.success)
        total_tests = len(results)
        avg_time = (
            sum(r.execution_time for r in results) / total_tests
            if total_tests > 0
            else 0
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Results", total_tests)
        with col2:
            st.metric(
                "Success Rate",
                f"{(successful_tests / total_tests * 100):.1f}%"
                if total_tests > 0
                else "0%",
            )
        with col3:
            st.metric("Avg Duration", f"{avg_time:.2f}s")

    @staticmethod
    def _render_detailed_results(results: List[ExperimentResult]) -> None:
        """Render detailed expandable results."""
        st.markdown("### 🔍 Detailed Results")

        # Filter options
        col1, col2 = st.columns(2)

        with col1:
            status_filter = st.selectbox(
                "Filter by Status:",
                ["All", "Success Only", "Failed Only"],
                key="status_filter",
            )

        with col2:
            show_details = st.checkbox(
                "Show Full Details", value=False, key="show_details"
            )

        # Apply filters
        filtered_results = results
        if status_filter == "Success Only":
            filtered_results = [r for r in results if r.success]
        elif status_filter == "Failed Only":
            filtered_results = [r for r in results if not r.success]

        # Display filtered results
        for result in filtered_results:
            with st.expander(
                f"Test {result.test_id}: {result.assistant_id} - {'✅ Success' if result.success else '❌ Failed'}"
            ):
                # Basic info
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Assistant ID:** {result.assistant_id}")
                    st.markdown(
                        f"**Status:** {'✅ Success' if result.success else '❌ Failed'}"
                    )
                    st.markdown(f"**Duration:** {result.execution_time:.2f}s")
                    st.markdown(f"**Timestamp:** {result.timestamp}")

                with col2:
                    if result.message:
                        st.markdown(f"**Chat ID:** {result.message.chatId}")
                    if result.error:
                        st.error(f"**Error:** {result.error}")

                # Question and Response
                st.markdown("**Question:**")
                st.text_area(
                    "Question",
                    value=result.question,
                    height=60,
                    disabled=True,
                    key=f"q_{result.test_id}",
                    label_visibility="hidden",
                )

                st.markdown("**Response/Message:**")
                st.text_area(
                    "Response",
                    value=result.message.text if result.message else "N/A",
                    height=120,
                    disabled=True,
                    key=f"m_{result.test_id}",
                    label_visibility="hidden",
                )

                # Assessment
                st.markdown("**Assessment:**")
                st.text_area(
                    "Assessment",
                    value=result.message.assessment[0].label
                    if result.message and result.message.assessment
                    else "N/A",
                    height=80,
                    disabled=True,
                    key=f"a_{result.test_id}",
                    label_visibility="hidden",
                )

                # Additional details if requested
                if show_details:
                    if result.message and result.message.references:
                        st.markdown("**References:**")
                        st.json(result.message.references)

                    if result.message and result.message.debugInfo:
                        st.markdown("**Debug Info:**")
                        st.json(result.message.debugInfo)

                st.markdown("---")

    @staticmethod
    def _render_question_centric_results(summary: ExperimentSummary) -> None:
        """Render results organized by questions with golden answers and assistant results."""
        st.markdown("### 📝 Question-Centric Results Analysis")
        
        st.info(f"🔍 Displaying results for {len(summary.question_results)} questions with golden answers")
        
        # Overall summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Questions", len(summary.question_results))
        
        with col2:
            golden_answers_count = sum(1 for qr in summary.question_results if qr.golden_answer)
            st.metric("Golden Answers", golden_answers_count)
        
        with col3:
            avg_success_rate = sum(qr.success_rate for qr in summary.question_results) / len(summary.question_results) if summary.question_results else 0
            st.metric("Avg Success Rate", f"{avg_success_rate:.1f}%")
        
        with col4:
            total_assistants = summary.question_results[0].total_assistants if summary.question_results else 0
            st.metric("Assistants per Question", total_assistants)

        # Export evaluations button
        if st.button("📥 Export All Evaluations", help="Download all reviewer evaluations as JSON"):
            ExperimentExplorerComponent._export_evaluations()

        st.markdown("---")
        
        # Render each question
        for i, question_result in enumerate(summary.question_results, 1):
            ExperimentExplorerComponent._render_single_question_result(question_result, i)
            
            # Add separator between questions
            if i < len(summary.question_results):
                st.markdown("---")

    @staticmethod
    def _render_single_question_result(question_result: QuestionResult, question_num: int) -> None:
        """Render a single question with its golden answer and assistant results."""
        
        # Question Header
        st.markdown(f"## 🔤 Question {question_num}")
        st.markdown(f"**{question_result.question}**")
        
        # Question metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Assistants", question_result.total_assistants)
        with col2:
            st.metric("Successful", question_result.successful_assistants)
        with col3:
            st.metric("Failed", question_result.failed_assistants)
        with col4:
            st.metric("Success Rate", f"{question_result.success_rate:.1f}%")
        
        # Golden Answer Section
        if question_result.golden_answer:
            st.markdown("### 🏆 Golden Answer")
            
            # Golden answer metadata
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(f"**Model:** {question_result.golden_answer.model}")
            with col2:
                st.caption(f"**Generation Time:** {question_result.golden_answer.generation_time:.2f}s")
            with col3:
                st.caption(f"**Timestamp:** {question_result.golden_answer.timestamp}")
            
            # Golden answer content
            with st.expander("📖 View Golden Answer", expanded=True):
                st.markdown(question_result.golden_answer.answer)
        else:
            st.warning("⚠️ No golden answer available for this question")
        
        # Assistant Results Table
        st.markdown("### 🤖 Assistant Results")
        
        if question_result.assistant_results:
            # Prepare table data
            table_data = []
            for result in question_result.assistant_results:
                # Get assessment info
                hallucination_level = "❌"
                assessment_message = "N/A"
                
                if result.message and result.message.assessment:
                    assessment_message = result.message.assessment[0].explanation if result.message.assessment[0].explanation else result.message.assessment[0].label
                    hallucination_level = ExperimentExplorerComponent._convert_assessment_message_to_emoji(
                        result.message.assessment[0].label
                    )
                
                # Truncate message for table display
                message_preview = "N/A"
                if result.message and result.message.text:
                    message_preview = result.message.text[:200] + "..." if len(result.message.text) > 200 else result.message.text
                
                table_data.append({
                    "Assistant ID": result.assistant_id,
                    "Status": "✅" if result.success else "❌",
                    "Duration": f"{result.execution_time:.2f}s",
                    "Chat ID": result.message.chatId if result.message else "N/A",
                    "Hallucination": hallucination_level,
                    "Assessment": assessment_message,
                    "Response Preview": message_preview
                })
            
            # Display table
            df = pd.DataFrame(table_data)
            st.dataframe(df, width='stretch', hide_index=True)
            
            # Detailed responses in expandable sections
            st.markdown("#### 📋 Detailed Responses")
            
            for result in question_result.assistant_results:
                status_icon = "✅" if result.success else "❌"
                with st.expander(f"{status_icon} {result.assistant_id} - {result.execution_time:.2f}s"):
                    
                    # Basic info
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Chat ID:** {result.message.chatId if result.message else 'N/A'}")
                        st.markdown(f"**Status:** {status_icon}")
                        st.markdown(f"**Duration:** {result.execution_time:.2f}s")
                    
                    with col2:
                        st.markdown(f"**Timestamp:** {result.timestamp}")
                        if result.error:
                            st.error(f"**Error:** {result.error}")
                    
                    # Response content
                    if result.message and result.message.text:
                        st.markdown("**Response:**")
                        st.markdown(result.message.text)
                    
                    # Assessment
                    if result.message and result.message.assessment:
                        st.markdown("**Assessment:**")
                        assessment = result.message.assessment[0]
                        st.markdown(f"**Level:** {ExperimentExplorerComponent._convert_assessment_message_to_emoji(assessment.label)} {assessment.label}")
                        if assessment.explanation:
                            st.markdown(f"**Explanation:** {assessment.explanation}")
                    
                    # Reviewer Interface
                    st.markdown("---")
                    st.markdown("**👤 Reviewer Evaluation:**")
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # User-friendly score evaluator
                        score_options = {
                            "": "Select Score",
                            "5": "⭐⭐⭐⭐⭐ Excellent (5)",
                            "4": "⭐⭐⭐⭐☆ Very Good (4)", 
                            "3": "⭐⭐⭐☆☆ Good (3)",
                            "2": "⭐⭐☆☆☆ Fair (2)",
                            "1": "⭐☆☆☆☆ Poor (1)",
                            "0": "☆☆☆☆☆ Very Poor (0)"
                        }
                        
                        selected_score = st.selectbox(
                            "Quality Score:",
                            options=list(score_options.keys()),
                            format_func=lambda x: score_options[x],
                            key=f"score_{result.test_id}_{result.assistant_id}",
                            help="Rate the quality of this assistant's response"
                        )
                    
                    with col2:
                        # Comment text area
                        comment = st.text_area(
                            "Reviewer Comments:",
                            placeholder="Enter your detailed feedback about this response...",
                            height=100,
                            key=f"comment_{result.test_id}_{result.assistant_id}",
                            help="Provide specific feedback about accuracy, completeness, clarity, etc."
                        )
                    
                    # Save evaluation button
                    if st.button("💾 Save Evaluation", key=f"save_{result.test_id}_{result.assistant_id}"):
                        if selected_score or comment:
                            # Store evaluation in session state
                            if "evaluations" not in st.session_state:
                                st.session_state.evaluations = {}
                            
                            eval_key = f"{result.test_id}_{result.assistant_id}"
                            st.session_state.evaluations[eval_key] = {
                                "test_id": result.test_id,
                                "assistant_id": result.assistant_id,
                                "question": question_result.question,
                                "score": selected_score if selected_score else "",
                                "comment": comment,
                                "timestamp": datetime.now().isoformat()
                            }
                            st.success("✅ Evaluation saved!")
                        else:
                            st.warning("Please provide at least a score or comment before saving.")
        else:
            st.warning("No assistant results found for this question")

    @staticmethod
    def _export_evaluations() -> None:
        """Export all reviewer evaluations as a downloadable JSON file."""
        if "evaluations" not in st.session_state or not st.session_state.evaluations:
            st.warning("No evaluations to export. Please evaluate some responses first.")
            return
        
        # Prepare evaluation data
        evaluations_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_evaluations": len(st.session_state.evaluations),
            "evaluations": list(st.session_state.evaluations.values())
        }
        
        # Create JSON string
        import json
        json_data = json.dumps(evaluations_data, indent=2)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reviewer_evaluations_{timestamp}.json"
        
        # Offer download
        st.download_button(
            label="📥 Download Evaluations JSON",
            data=json_data,
            file_name=filename,
            mime="application/json",
            help=f"Download {len(st.session_state.evaluations)} evaluations as JSON file"
        )
        
        # Show summary
        st.success(f"✅ Ready to download {len(st.session_state.evaluations)} evaluations!")
        
        # Show evaluation summary
        with st.expander("📊 Evaluation Summary", expanded=True):
            scores = [eval_data["score"] for eval_data in st.session_state.evaluations.values() if eval_data["score"]]
            if scores:
                score_counts = {}
                for score in scores:
                    score_counts[score] = score_counts.get(score, 0) + 1
                
                st.write("**Score Distribution:**")
                for score in sorted(score_counts.keys(), reverse=True):
                    count = score_counts[score]
                    stars = "⭐" * int(score) + "☆" * (5 - int(score)) if score else "No Score"
                    st.write(f"- {stars} ({score}): {count} evaluations")
            
            comments_count = len([eval_data for eval_data in st.session_state.evaluations.values() if eval_data["comment"].strip()])
            st.write(f"**Comments:** {comments_count} responses have detailed comments")

    @staticmethod
    def _load_experiment_summary(exp_path: Path) -> ExperimentSummary | None:
        """Load experiment_summary.json file from the experiment directory."""
        summary_file = exp_path / "experiment_summary.json"

        if not summary_file.exists():
            st.error(f"No experiment_summary.json found in {exp_path}")
            return None

        try:
            with open(summary_file, "r") as f:
                return ExperimentSummary.model_validate_json(f.read())
        except Exception as e:
            st.error(f"Error loading experiment summary: {e}")
            return None

    @staticmethod
    def _generate_markdown_report(exp_path: Path, experiment_name: str) -> None:
        """Generate and export an HTML report from the experiment summary."""
        # Load the experiment summary
        summary_data = ExperimentExplorerComponent._load_experiment_summary(exp_path)

        if not summary_data:
            return

        try:
            # Generate the HTML report content using the existing render function
            html_content = render_experiment_summary(summary_data)

            # Load the HTML template
            template_path = (
                Path(__file__).parent.parent / "experiment_report_template.html"
            )
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # Clean experiment name for use in JavaScript identifiers
            experiment_name_clean = (
                experiment_name.replace(" ", "_").replace(":", "_").replace("-", "_")
            )

            # Replace template variables
            complete_html = template_content.replace(
                "{{ experiment_name }}", experiment_name
            )
            complete_html = complete_html.replace(
                "{{ experiment_name_clean }}", experiment_name_clean
            )
            complete_html = complete_html.replace(
                "{{ start_time }}", summary_data.start_time
            )
            complete_html = complete_html.replace(
                "{{ end_time }}", summary_data.end_time or "In Progress"
            )
            complete_html = complete_html.replace("{{ html_content }}", html_content)

            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_report_{experiment_name}_{timestamp}.html"

            # Offer the file for download
            st.success("✅ HTML report generated successfully!")
            st.download_button(
                label="📥 Download HTML Report",
                data=complete_html,
                file_name=filename,
                mime="text/html",
                help="Click to download the complete HTML experiment report",
            )

            # Show a preview of what was generated
            st.info(f"📄 Report contains {len(summary_data.results)} test results")
            with st.expander("🔍 Preview Report Content", expanded=False):
                st.write("The report includes:")
                st.write("- Summary statistics table")
                st.write("- Detailed results table with all test data")
                st.write("- Properly formatted markdown content in answers")
                st.write("- Professional styling and layout")

        except Exception as e:
            st.error(f"Error generating HTML report: {e}")
            st.exception(e)
