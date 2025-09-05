"""
Experiment runner component for testing multiple assistants with multiple questions.
"""

import streamlit as st
import time
from typing import List
from config import ConfigManager
from experiment_executor import ExperimentExecutor
from schemas import ExperimentResult


class ExperimentRunnerComponent:
    """Handles experiment configuration and execution UI."""

    @staticmethod
    def render() -> None:
        """Render the experiment runner interface."""
        st.header("🧪 Experiment Runner")

        # Check if configuration is valid
        if not ConfigManager.is_config_valid():
            ExperimentRunnerComponent._render_config_required()
            return

        # Initialize experiment state
        ExperimentRunnerComponent._initialize_experiment_state()

        # Render experiment configuration
        ExperimentRunnerComponent._render_experiment_config()

        # Render experiment status
        ExperimentRunnerComponent._render_experiment_status()

    @staticmethod
    def _render_config_required() -> None:
        """Render message when configuration is required."""
        st.warning("⚠️ Configuration Required")
        st.info("""
        Please complete your configuration in the sidebar before running experiments.
        
        Required fields:
        - User ID
        - Company ID  
        - App ID
        - API Key
        """)

        # Show current config status
        config = ConfigManager.get_config()
        missing_fields = []

        if not config.user_id:
            missing_fields.append("User ID")
        if not config.company_id:
            missing_fields.append("Company ID")
        if not config.app_id:
            missing_fields.append("App ID")
        if not config.api_key:
            missing_fields.append("API Key")

        if missing_fields:
            st.error(f"Missing: {', '.join(missing_fields)}")

    @staticmethod
    def _initialize_experiment_state() -> None:
        """Initialize experiment-related session state."""
        if "experiment_assistant_ids" not in st.session_state:
            st.session_state.experiment_assistant_ids = []
        if "experiment_questions" not in st.session_state:
            st.session_state.experiment_questions = []
        if "experiment_configured" not in st.session_state:
            st.session_state.experiment_configured = False
        if "experiment_running" not in st.session_state:
            st.session_state.experiment_running = False
        if "experiment_results" not in st.session_state:
            st.session_state.experiment_results = []
        if "experiment_progress" not in st.session_state:
            st.session_state.experiment_progress = 0
        if "experiment_current_test" not in st.session_state:
            st.session_state.experiment_current_test = 0
        if "experiment_total_tests" not in st.session_state:
            st.session_state.experiment_total_tests = 0
        if "experiment_summary" not in st.session_state:
            st.session_state.experiment_summary = None
        if "experiment_executor" not in st.session_state:
            st.session_state.experiment_executor = None

    @staticmethod
    def _render_experiment_config() -> None:
        """Render experiment configuration interface."""
        st.subheader("Experiment Configuration")

        # Create two columns for assistants and questions
        col1, col2 = st.columns(2)

        with col1:
            ExperimentRunnerComponent._render_assistant_config()

        with col2:
            ExperimentRunnerComponent._render_questions_config()

        # Action buttons
        st.markdown("---")
        ExperimentRunnerComponent._render_action_buttons()

    @staticmethod
    def _render_assistant_config() -> None:
        """Render assistant IDs configuration."""
        st.markdown("### 🤖 Assistant IDs")

        # Text area for assistant IDs
        assistant_ids_text = st.text_area(
            "Enter Assistant IDs (one per line)",
            value="\n".join(st.session_state.experiment_assistant_ids),
            height=200,
            help="Enter each assistant ID on a separate line. Example: assistant_abc123def456",
            placeholder="assistant_abc123def456\nassistant_xyz789ghi012\n...",
        )

        # Parse assistant IDs
        assistant_ids = [
            aid.strip() for aid in assistant_ids_text.split("\n") if aid.strip()
        ]

        # Update session state
        st.session_state.experiment_assistant_ids = assistant_ids

        # Display current count
        if assistant_ids:
            st.success(f"✅ {len(assistant_ids)} assistant(s) configured")

            # Show preview in expander
            with st.expander("Preview Assistant IDs"):
                for i, aid in enumerate(assistant_ids, 1):
                    st.text(f"{i}. {aid}")
        else:
            st.warning("⚠️ No assistant IDs configured")

        # Validation
        ExperimentRunnerComponent._validate_assistant_ids(assistant_ids)

    @staticmethod
    def _render_questions_config() -> None:
        """Render questions configuration."""
        st.markdown("### ❓ Test Questions")

        # Text area for questions
        questions_text = st.text_area(
            "Enter Questions (one per line)",
            value="\n".join(st.session_state.experiment_questions),
            height=200,
            help="Enter each question on a separate line",
            placeholder="What is the capital of France?\nHow does photosynthesis work?\nExplain quantum computing...",
        )

        # Parse questions
        questions = [q.strip() for q in questions_text.split("\n") if q.strip()]

        # Update session state
        st.session_state.experiment_questions = questions

        # Display current count
        if questions:
            st.success(f"✅ {len(questions)} question(s) configured")

            # Show preview in expander
            with st.expander("Preview Questions"):
                for i, question in enumerate(questions, 1):
                    st.text(f"{i}. {question}")
        else:
            st.warning("⚠️ No questions configured")

        # Validation
        ExperimentRunnerComponent._validate_questions(questions)

    @staticmethod
    def _validate_assistant_ids(assistant_ids: List[str]) -> None:
        """Validate assistant IDs format."""
        if not assistant_ids:
            return

        invalid_ids = []
        for aid in assistant_ids:
            # Basic validation - should start with "assistant_"
            if not aid.startswith("assistant_"):
                invalid_ids.append(aid)

        if invalid_ids:
            st.error("❌ Invalid Assistant ID format:")
            for invalid_id in invalid_ids:
                st.text(f"  • {invalid_id}")
            st.info("Assistant IDs should start with 'assistant_'")

    @staticmethod
    def _validate_questions(questions: List[str]) -> None:
        """Validate questions."""
        if not questions:
            return

        # Check for very short questions
        short_questions = [q for q in questions if len(q) < 5]
        if short_questions:
            st.warning("⚠️ Very short questions detected:")
            for q in short_questions:
                st.text(f"  • {q}")

    @staticmethod
    def _render_action_buttons() -> None:
        """Render action buttons for experiment control."""
        col1, col2, col3 = st.columns(3)

        # Check if experiment is ready to run
        can_run = (
            len(st.session_state.experiment_assistant_ids) > 0
            and len(st.session_state.experiment_questions) > 0
            and not st.session_state.experiment_running
        )

        with col1:
            if st.button(
                "🚀 Run Experiment",
                disabled=not can_run,
                width="content",
                type="primary",
            ):
                ExperimentRunnerComponent._start_experiment()

        with col2:
            if st.button(
                "⏹️ Stop Experiment",
                disabled=not st.session_state.experiment_running,
                width="content",
            ):
                ExperimentRunnerComponent._stop_experiment()

        with col3:
            if st.button(
                "🗑️ Clear Results",
                disabled=len(st.session_state.experiment_results) == 0,
                width="content",
            ):
                ExperimentRunnerComponent._clear_results()

        # Display readiness status
        if not can_run and not st.session_state.experiment_running:
            missing = []
            if len(st.session_state.experiment_assistant_ids) == 0:
                missing.append("Assistant IDs")
            if len(st.session_state.experiment_questions) == 0:
                missing.append("Questions")

            if missing:
                st.info(f"ℹ️ Configure {' and '.join(missing)} to run experiment")

    @staticmethod
    def _render_experiment_status() -> None:
        """Render current experiment status and results."""
        st.markdown("---")
        st.subheader("Experiment Status")

        # Calculate total combinations
        total_combinations = len(st.session_state.experiment_assistant_ids) * len(
            st.session_state.experiment_questions
        )

        if total_combinations > 0:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Total Tests",
                    total_combinations,
                    help="Number of assistant-question combinations",
                )

            with col2:
                st.metric("Assistants", len(st.session_state.experiment_assistant_ids))

            with col3:
                st.metric("Questions", len(st.session_state.experiment_questions))

            # Experiment matrix preview
            if st.checkbox("Show Experiment Matrix"):
                ExperimentRunnerComponent._render_experiment_matrix()

        # Running status
        if st.session_state.experiment_running:
            st.info("🔄 Experiment is running...")

            # Execute next test if parameters are available
            if hasattr(st.session_state, "experiment_executor_params"):
                ExperimentRunnerComponent._execute_next_test()

            # Progress bar
            progress = st.session_state.experiment_progress
            current_test = st.session_state.experiment_current_test
            total_tests = st.session_state.experiment_total_tests

            if total_tests > 0:
                st.progress(
                    progress,
                    text=f"Running test {current_test} of {total_tests} ({progress * 100:.1f}%)",
                )
            else:
                st.progress(0.0, text="Preparing to run experiments...")

            # Auto-refresh while running
            if st.session_state.experiment_running:
                time.sleep(0.5)  # Reduced sleep time for more responsive UI
                st.rerun()

        # Results summary
        if st.session_state.experiment_results:
            successful_tests = sum(
                1 for r in st.session_state.experiment_results if r.success
            )
            total_results = len(st.session_state.experiment_results)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Completed Tests", total_results)
            with col2:
                st.metric("Successful", successful_tests)
            with col3:
                success_rate = (
                    (successful_tests / total_results * 100) if total_results > 0 else 0
                )
                st.metric("Success Rate", f"{success_rate:.1f}%")

        # Show completed experiment summary
        if (
            st.session_state.experiment_summary
            and not st.session_state.experiment_running
        ):
            ExperimentRunnerComponent._render_experiment_results()

        # Show experiment history
        ExperimentRunnerComponent._render_experiment_history()

    @staticmethod
    def _render_experiment_matrix() -> None:
        """Render a preview of the experiment matrix."""
        st.markdown("#### Experiment Matrix Preview")

        assistants = st.session_state.experiment_assistant_ids
        questions = st.session_state.experiment_questions

        if not assistants or not questions:
            st.info("Configure assistants and questions to see matrix")
            return

        # Create a simple table showing the combinations
        matrix_data = []
        for i, assistant in enumerate(assistants):
            for j, question in enumerate(questions):
                matrix_data.append(
                    {
                        "Test #": len(matrix_data) + 1,
                        "Assistant": assistant,
                        "Question": question[:50] + "..."
                        if len(question) > 50
                        else question,
                    }
                )

        # Display first few rows
        display_rows = min(10, len(matrix_data))
        st.dataframe(matrix_data[:display_rows], width="content", hide_index=True)

        if len(matrix_data) > display_rows:
            st.info(
                f"Showing first {display_rows} of {len(matrix_data)} total combinations"
            )

    @staticmethod
    def _start_experiment() -> None:
        """Start the experiment execution."""
        # Get configuration
        config = ConfigManager.get_config()

        # Initialize executor
        executor = ExperimentExecutor(
            user_id=config.user_id,
            company_id=config.company_id,
            app_id=config.app_id,
            api_key=config.api_key,
        )

        # Store executor in session state
        st.session_state.experiment_executor = executor

        # Set up experiment state
        st.session_state.experiment_running = True
        st.session_state.experiment_configured = True
        st.session_state.experiment_progress = 0
        st.session_state.experiment_current_test = 0
        st.session_state.experiment_total_tests = len(
            st.session_state.experiment_assistant_ids
        ) * len(st.session_state.experiment_questions)
        st.session_state.experiment_start_time = time.strftime("%Y-%m-%d %H:%M:%S")

        # Store experiment parameters for execution
        st.session_state.experiment_executor_params = {
            "executor": executor,
            "assistant_ids": st.session_state.experiment_assistant_ids.copy(),
            "questions": st.session_state.experiment_questions.copy(),
        }

        st.success("🚀 Experiment started!")
        st.rerun()

    @staticmethod
    def _stop_experiment() -> None:
        """Stop the running experiment."""
        st.session_state.experiment_running = False

        # Clean up experiment execution state
        if hasattr(st.session_state, "experiment_executor_params"):
            delattr(st.session_state, "experiment_executor_params")
        if hasattr(st.session_state, "experiment_test_queue"):
            delattr(st.session_state, "experiment_test_queue")
        if hasattr(st.session_state, "experiment_completed_tests"):
            delattr(st.session_state, "experiment_completed_tests")

        st.warning("⏹️ Experiment stopped")
        st.rerun()

    @staticmethod
    def _clear_results() -> None:
        """Clear experiment results."""
        st.session_state.experiment_results = []
        st.session_state.experiment_summary = None
        if hasattr(st.session_state, "experiment_results_file"):
            delattr(st.session_state, "experiment_results_file")
        if hasattr(st.session_state, "experiment_error"):
            delattr(st.session_state, "experiment_error")
        st.info("🗑️ Results cleared")
        st.rerun()

    @staticmethod
    def _render_experiment_results() -> None:
        """Render simplified experiment results summary."""
        summary = st.session_state.experiment_summary

        if not summary:
            return

        st.markdown("---")
        st.subheader("📊 Experiment Results")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Tests", summary.total_tests)
        with col2:
            st.metric("Completed", summary.completed_tests)
        with col3:
            st.metric("Failed", summary.failed_tests)
        with col4:
            st.metric("Success Rate", f"{summary.success_rate:.1f}%")

        # Show errors if any
        if hasattr(st.session_state, "experiment_error"):
            st.error(f"❌ Experiment Error: {st.session_state.experiment_error}")

    @staticmethod
    def _render_experiment_history() -> None:
        """Render experiment history table."""
        st.markdown("---")
        st.subheader("📋 Experiment History")

        # Load experiment history
        history = ConfigManager.load_experiment_history()

        if not history:
            st.info("No experiments have been conducted yet.")
            return

        # Create history table data
        history_data = []
        for i, exp in enumerate(history):
            # Format date for better display
            date_str = exp.get("date", "N/A")
            if date_str != "N/A" and len(date_str) > 16:
                date_str = date_str[:16]  # Show only date and time, not seconds

            history_data.append(
                {
                    "#": i + 1,
                    "Experiment": exp.get("experiment_name", "N/A"),
                    "Date": date_str,
                    "Assistants": exp.get("num_assistants", 0),
                    "Questions": exp.get("num_questions", 0),
                    "Total Tests": exp.get("total_tests", 0),
                    "Completed": exp.get("completed_tests", 0),
                    "Failed": exp.get("failed_tests", 0),
                    "Success Rate": f"{exp.get('success_rate', 0):.1f}%",
                    "Duration": f"{exp.get('execution_time', 0):.1f}s",
                }
            )

        # Display history table
        st.dataframe(history_data, width="stretch", hide_index=True)

        # Clear history button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ Clear All Experiments", type="secondary"):
                if ExperimentRunnerComponent._clear_all_experiments():
                    st.success("All experiments cleared!")
                    st.rerun()
                else:
                    st.error("Failed to clear experiments.")

        with col2:
            st.caption(
                f"Showing {len(history)} experiment(s) from the experiments directory."
            )

    @staticmethod
    def _clear_all_experiments() -> bool:
        """Clear all experiment directories."""
        try:
            from pathlib import Path
            import shutil

            experiments_dir = Path("experiments")
            if experiments_dir.exists():
                # Remove all experiment directories
                for exp_dir in experiments_dir.iterdir():
                    if exp_dir.is_dir() and exp_dir.name.startswith("experiment_"):
                        shutil.rmtree(exp_dir)
                        print(f"Removed experiment directory: {exp_dir}")

            return True
        except Exception as e:
            print(f"Error clearing experiments: {e}")
            return False

    @staticmethod
    def _execute_next_test() -> None:
        """Execute the next test in the experiment queue."""
        if not hasattr(st.session_state, "experiment_executor_params"):
            return

        params = st.session_state.experiment_executor_params
        executor = params["executor"]
        assistant_ids = params["assistant_ids"]
        questions = params["questions"]

        # Initialize test queue if not exists
        if not hasattr(st.session_state, "experiment_test_queue"):
            test_queue = []
            for assistant_id in assistant_ids:
                for question in questions:
                    test_queue.append((assistant_id, question))
            st.session_state.experiment_test_queue = test_queue
            st.session_state.experiment_completed_tests = []

            # Create experiment directory
            executor.create_experiment_directory(assistant_ids, questions)

        # Get next test from queue
        if st.session_state.experiment_test_queue:
            assistant_id, question = st.session_state.experiment_test_queue.pop(0)
            current_test_num = len(st.session_state.experiment_completed_tests) + 1
            total_tests = st.session_state.experiment_total_tests

            # Execute single test
            try:
                message, error, execution_time = executor.run_experiment_sync(
                    assistant_id, question
                )

                result = ExperimentResult(
                    test_id=current_test_num,
                    assistant_id=assistant_id,
                    question=question,
                    success=message is not None,
                    error=error,
                    execution_time=execution_time,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    message=message,
                )

                # Save individual result
                executor.save_individual_result(result)

                # Update session state
                st.session_state.experiment_results.append(result)
                st.session_state.experiment_completed_tests.append(result)
                st.session_state.experiment_current_test = current_test_num
                st.session_state.experiment_progress = current_test_num / total_tests

            except Exception as e:
                st.session_state.experiment_error = str(e)
                st.session_state.experiment_running = False
                return

        # Check if experiment is complete
        if not st.session_state.experiment_test_queue:
            # All tests completed
            ExperimentRunnerComponent._finalize_experiment()

    @staticmethod
    def _finalize_experiment() -> None:
        """Finalize the experiment and save summary."""
        if not hasattr(st.session_state, "experiment_executor_params"):
            return

        executor = st.session_state.experiment_executor_params["executor"]
        results = st.session_state.experiment_completed_tests

        # Calculate summary statistics
        total_tests = len(results)
        completed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - completed_tests
        success_rate = (completed_tests / total_tests) * 100 if total_tests > 0 else 0
        total_execution_time = sum(r.execution_time for r in results)

        # Create summary
        from experiment_executor import ExperimentSummary

        summary = ExperimentSummary(
            total_tests=total_tests,
            completed_tests=completed_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            total_execution_time=total_execution_time,
            start_time=st.session_state.get("experiment_start_time", ""),
            end_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            results=results,
            experiment_directory=executor.experiment_directory,
        )

        # Save summary
        executor.save_experiment_summary(summary)

        # Update session state
        st.session_state.experiment_summary = summary
        st.session_state.experiment_running = False

        # Clean up
        if hasattr(st.session_state, "experiment_executor_params"):
            delattr(st.session_state, "experiment_executor_params")
        if hasattr(st.session_state, "experiment_test_queue"):
            delattr(st.session_state, "experiment_test_queue")
        if hasattr(st.session_state, "experiment_completed_tests"):
            delattr(st.session_state, "experiment_completed_tests")
