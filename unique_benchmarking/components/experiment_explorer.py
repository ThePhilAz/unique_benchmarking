"""
Experiment explorer component for browsing and analyzing experiment results.
"""

import streamlit as st
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from schemas import ExperimentResult


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
                        result_data = ExperimentResult.model_validate(raw_data["results"])
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
                        result_data = ExperimentResult.model_validate(raw_data["results"])
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
