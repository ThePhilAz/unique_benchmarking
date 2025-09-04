"""
Experiment explorer component for browsing and analyzing experiment results.
"""

import streamlit as st
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


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
        st.subheader(f"📊 Analysis: {selected_exp['name']}")

        # Load all result files
        results = ExperimentExplorerComponent._load_experiment_results(exp_path)

        if not results:
            st.warning("No result files found in this experiment.")
            return

        # Create analysis table
        ExperimentExplorerComponent._render_analysis_table(results)

        # Show detailed results
        ExperimentExplorerComponent._render_detailed_results(results)

    @staticmethod
    def _load_experiment_results(exp_path: Path) -> List[Dict[str, Any]]:
        """Load all result files from an experiment directory."""
        results = []

        # Try to load experiment config for question mapping
        config_questions = []
        config_file = exp_path / "experiment_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config_data = json.load(f)
                config_questions = config_data.get("experiment_setup", {}).get(
                    "questions", []
                )
            except Exception:
                pass

        # Load successful results
        success_dir = exp_path / "success"
        if success_dir.exists():
            for result_file in success_dir.glob("*.json"):
                try:
                    with open(result_file, "r") as f:
                        result_data = json.load(f)

                    result_info = ExperimentExplorerComponent._extract_result_info(
                        result_data, "success", config_questions
                    )
                    if result_info:
                        results.append(result_info)

                except Exception as e:
                    st.warning(f"Error loading {result_file.name}: {e}")

        # Load failed results
        error_dir = exp_path / "error"
        if error_dir.exists():
            for result_file in error_dir.glob("*.json"):
                try:
                    with open(result_file, "r") as f:
                        result_data = json.load(f)

                    result_info = ExperimentExplorerComponent._extract_result_info(
                        result_data, "error", config_questions
                    )
                    if result_info:
                        results.append(result_info)

                except Exception as e:
                    st.warning(f"Error loading {result_file.name}: {e}")

        # Sort by test_id
        results.sort(key=lambda x: x.get("test_id", 0))

        return results

    @staticmethod
    def _extract_result_info(
        result_data: Dict[str, Any],
        status: str,
        config_questions: List[str] | None = None,
    ) -> Optional[Dict[str, Any]]:
        """Extract relevant information from a result file."""
        try:
            # Handle different file structures
            if "test_info" in result_data:
                # New structure with test_info and message_data
                test_info = result_data.get("test_info", {})
                message_data = result_data.get("message_data", {})

                assessment = []
                if message_data and "assessment" in message_data:
                    assessment = message_data["assessment"]

                message_text = test_info.get(
                    "response",
                    message_data.get("text", "N/A") if message_data else "N/A",
                )
                question = test_info.get("question", "N/A")
                assistant_id = test_info.get("assistant_id", "N/A")
                chat_id = message_data.get("chatId", "N/A") if message_data else "N/A"
                references = message_data.get("references", []) if message_data else []
                debug_info = message_data.get("debugInfo", {}) if message_data else {}

            elif "results" in result_data:
                # Alternative structure with results object
                results = result_data.get("results", {})
                message = results.get("message", {})

                assessment = message.get("assessment", [])
                message_text = message.get("text", "N/A")

                # Try to get question from config if not in results
                question = results.get("question", "N/A")
                if question == "N/A" and config_questions:
                    # Try to infer question from test_id
                    test_id = results.get("test_id", 1)
                    if test_id > 0 and test_id <= len(config_questions):
                        question = config_questions[test_id - 1]

                assistant_id = results.get("assistant_id", "N/A")
                chat_id = message.get("chatId", "N/A")
                references = message.get("references", [])
                debug_info = message.get("debugInfo", {})

                test_info = results  # Use results as test_info for other fields

            else:
                # Direct structure
                assessment = result_data.get("assessment", [])
                message_text = result_data.get("text", "N/A")
                question = result_data.get("question", "N/A")
                assistant_id = result_data.get("assistant_id", "N/A")
                chat_id = result_data.get("chatId", "N/A")
                references = result_data.get("references", [])
                debug_info = result_data.get("debugInfo", {})

                test_info = result_data

            # Format assessment for display
            assessment_text = "No assessment"
            if assessment:
                assessment_parts = []
                for assess in assessment:
                    if isinstance(assess, dict):
                        # Extract relevant assessment fields
                        title = assess.get("title", "")
                        explanation = assess.get("explanation", "")
                        label = assess.get("label", "")
                        assess_type = assess.get("type", "")

                        # Create a readable assessment string
                        parts = []
                        if title:
                            parts.append(f"Title: {title}")
                        if label:
                            parts.append(f"Label: {label}")
                        if assess_type:
                            parts.append(f"Type: {assess_type}")
                        if explanation:
                            parts.append(f"Explanation: {explanation}")

                        if parts:
                            assessment_parts.append(" | ".join(parts))
                        else:
                            assessment_parts.append(str(assess))
                    else:
                        assessment_parts.append(str(assess))
                assessment_text = (
                    " || ".join(assessment_parts)
                    if assessment_parts
                    else "No assessment"
                )

            return {
                "test_id": test_info.get("test_id", 0),
                "assistant_id": assistant_id,
                "question": question,
                "message": message_text,
                "assessment": assessment_text,
                "status": status,
                "success": test_info.get("success", False),
                "execution_time": test_info.get("execution_time", 0),
                "error": test_info.get("error", None),
                "timestamp": test_info.get("timestamp", "N/A"),
                "chat_id": chat_id,
                "references": references,
                "debug_info": debug_info,
            }

        except Exception as e:
            st.error(f"Error extracting result info: {e}")
            return None

    @staticmethod
    def _render_analysis_table(results: List[Dict[str, Any]]) -> None:
        """Render the main analysis table."""
        st.markdown("### 📋 Results Analysis Table")

        # Prepare table data
        table_data = []
        for result in results:
            # Truncate long text for table display
            question = (
                result["question"][:100] + "..."
                if len(result["question"]) > 100
                else result["question"]
            )
            message = (
                result["message"][:150] + "..."
                if len(result["message"]) > 150
                else result["message"]
            )
            assessment = (
                result["assessment"][:100] + "..."
                if len(result["assessment"]) > 100
                else result["assessment"]
            )

            table_data.append(
                {
                    "Test #": result["test_id"],
                    "Status": "✅ Success" if result["success"] else "❌ Failed",
                    "Assistant ID": result["assistant_id"],
                    "Question": question,
                    "Message": message,
                    "Assessment": assessment,
                    "Duration": f"{result['execution_time']:.2f}s",
                }
            )

        # Display table
        st.dataframe(table_data, width="stretch", hide_index=True)

        # Summary stats
        successful_tests = sum(1 for r in results if r["success"])
        total_tests = len(results)
        avg_time = (
            sum(r["execution_time"] for r in results) / total_tests
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
    def _render_detailed_results(results: List[Dict[str, Any]]) -> None:
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
            filtered_results = [r for r in results if r["success"]]
        elif status_filter == "Failed Only":
            filtered_results = [r for r in results if not r["success"]]

        # Display filtered results
        for result in filtered_results:
            with st.expander(
                f"Test {result['test_id']}: {result['assistant_id']} - {'✅ Success' if result['success'] else '❌ Failed'}"
            ):
                # Basic info
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Assistant ID:** {result['assistant_id']}")
                    st.markdown(
                        f"**Status:** {'✅ Success' if result['success'] else '❌ Failed'}"
                    )
                    st.markdown(f"**Duration:** {result['execution_time']:.2f}s")
                    st.markdown(f"**Timestamp:** {result['timestamp']}")

                with col2:
                    st.markdown(f"**Chat ID:** {result['chat_id']}")
                    if result["error"]:
                        st.error(f"**Error:** {result['error']}")

                # Question and Response
                st.markdown("**Question:**")
                st.text_area(
                    "Question",
                    value=result["question"],
                    height=60,
                    disabled=True,
                    key=f"q_{result['test_id']}",
                    label_visibility="hidden",
                )

                st.markdown("**Response/Message:**")
                st.text_area(
                    "Response",
                    value=result["message"],
                    height=120,
                    disabled=True,
                    key=f"m_{result['test_id']}",
                    label_visibility="hidden",
                )

                # Assessment
                st.markdown("**Assessment:**")
                st.text_area(
                    "Assessment",
                    value=result["assessment"],
                    height=80,
                    disabled=True,
                    key=f"a_{result['test_id']}",
                    label_visibility="hidden",
                )

                # Additional details if requested
                if show_details:
                    if result["references"]:
                        st.markdown("**References:**")
                        st.json(result["references"])

                    if result["debug_info"]:
                        st.markdown("**Debug Info:**")
                        st.json(result["debug_info"])

                st.markdown("---")
