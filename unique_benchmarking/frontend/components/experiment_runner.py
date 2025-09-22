"""
Experiment Runner component for creating and running benchmarking experiments
"""

import streamlit as st
import json
import csv
import io
import time
import threading
from typing import List, Dict, Any, Optional
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api_client import get_api_client


class ExperimentRunner:
    """Component for creating and running experiments"""

    def __init__(self):
        self.api_client = get_api_client()

    def render(self, config: Dict[str, Any]) -> None:
        """
        Render the experiment runner interface

        Args:
            config: Configuration data from sidebar
        """

        if not config:
            st.error("⚠️ Please configure your API settings first!")
            return

        # Store config for use in other methods
        self._config = config

        # Debug panel (can be removed later)
        with st.sidebar.expander("🔧 Debug Info", expanded=False):
            st.write("**Session State:**")
            tracking_id = st.session_state.get("tracking_experiment_id", "None")
            experiment_started = st.session_state.get("experiment_started", "None")
            run_result = st.session_state.get("experiment_run_result", "None")
            st.write(f"Tracking ID: {tracking_id}")
            st.write(f"Experiment Started: {experiment_started}")
            st.write(f"Run Result: {run_result}")
        
        # Check for active progress tracking first
        self._render_progress_tracking()
        
        # Render the setup and run interface directly
        self._render_setup_and_run_tab()

    def _render_setup_and_run_tab(self):
        """Render combined setup and run tab"""
        # Get config from the component's config parameter
        config = getattr(self, "_config", {})

        # Get current data
        assistant_ids = st.session_state.get("assistant_ids", [])
        questions = st.session_state.get("questions", [])

        # Top section: Quick overview and run button
        col1, col2 = st.columns([3, 1])

        with col1:
            # Quick metrics
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("🤖 Assistants", len(assistant_ids))
            with metric_col2:
                st.metric("❓ Questions", len(questions))
            with metric_col3:
                st.metric("🧪 Total Tests", len(assistant_ids) * len(questions))

        with col2:
            # Quick run button
            missing_items = []
            if not assistant_ids:
                missing_items.append("assistants")
            if not questions:
                missing_items.append("questions")

            if missing_items:
                st.error(f"Missing: {', '.join(missing_items)}")
            else:
                if st.button(
                    "🚀 **RUN EXPERIMENT**", type="primary", width='stretch'
                ):
                    self._run_experiment(config)

        st.divider()

        # Configuration section - compact
        with st.expander("⚙️ **Configuration**", expanded=True):
            # Two column layout for inputs
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**🤖 Assistants**")

                # Compact assistant input
                assistant_input = st.text_area(
                    "Assistant IDs (one per line)",
                    value=st.session_state.get("assistant_ids_text", ""),
                    height=80,
                    placeholder="assistant_1\nassistant_2",
                    key="assistant_input",
                    label_visibility="collapsed",
                )

                # File upload
                assistant_file = st.file_uploader(
                    "Upload assistants file",
                    type=["txt", "json", "csv"],
                    key="assistant_file",
                    label_visibility="collapsed",
                )

                # Process assistant input
                if assistant_input != st.session_state.get("assistant_ids_text", ""):
                    st.session_state.assistant_ids_text = assistant_input
                    new_assistant_ids = [
                        aid.strip()
                        for aid in assistant_input.split("\n")
                        if aid.strip()
                    ]
                    st.session_state.assistant_ids = new_assistant_ids

                if assistant_file:
                    new_assistant_ids = self._parse_assistant_file(assistant_file)
                    if new_assistant_ids:
                        st.session_state.assistant_ids = new_assistant_ids
                        st.session_state.assistant_ids_text = "\n".join(
                            new_assistant_ids
                        )
                        st.rerun()

            with col2:
                st.markdown("**❓ Questions**")

                # Compact questions input
                questions_input = st.text_area(
                    "Questions (one per line)",
                    value=st.session_state.get("questions_text", ""),
                    height=80,
                    placeholder="What is AI?\nHow does ML work?",
                    key="questions_input",
                    label_visibility="collapsed",
                )

                # File upload
                questions_file = st.file_uploader(
                    "Upload questions file",
                    type=["txt", "json", "csv"],
                    key="questions_file",
                    label_visibility="collapsed",
                )

                # Process questions input
                if questions_input != st.session_state.get("questions_text", ""):
                    st.session_state.questions_text = questions_input
                    new_questions = [
                        q.strip() for q in questions_input.split("\n") if q.strip()
                    ]
                    st.session_state.questions = new_questions

                if questions_file:
                    new_questions = self._parse_questions_file(questions_file)
                    if new_questions:
                        st.session_state.questions = new_questions
                        st.session_state.questions_text = "\n".join(new_questions)
                        st.rerun()

            # Settings row
            st.markdown("**⚙️ Settings**")
            settings_col1, settings_col2, settings_col3 = st.columns(3)

            with settings_col1:
                run_immediately = st.checkbox("Run immediately", value=True)
                st.session_state.run_immediately = run_immediately

            with settings_col2:
                golden_model = config.get("default_golden_model", "gpt-4")
                st.info(f"Golden Model: **{golden_model}**")

            with settings_col3:
                user_id = config.get("user_id", "Not set")
                display_user = user_id[:12] + "..." if len(user_id) > 15 else user_id
                st.info(f"User: **{display_user}**")

        # Show current data if available
        if assistant_ids or questions:
            with st.expander("📋 **Current Data**", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    if assistant_ids:
                        st.markdown(f"**🤖 Assistants ({len(assistant_ids)}):**")
                        display_assistants = assistant_ids[:3]
                        for i, aid in enumerate(display_assistants, 1):
                            st.text(f"{i}. {aid}")
                        if len(assistant_ids) > 3:
                            st.text(f"... and {len(assistant_ids) - 3} more")

                with col2:
                    if questions:
                        st.markdown(f"**❓ Questions ({len(questions)}):**")
                        display_questions = questions[:3]
                        for i, q in enumerate(display_questions, 1):
                            display_q = q[:50] + "..." if len(q) > 50 else q
                            st.text(f"{i}. {display_q}")
                        if len(questions) > 3:
                            st.text(f"... and {len(questions) - 3} more")


    def _parse_assistant_file(self, file) -> List[str]:
        """Parse uploaded assistant file"""
        try:
            content = file.read()

            if file.type == "text/plain":
                # Plain text file
                text = content.decode("utf-8")
                assistant_ids = [aid.strip() for aid in text.split("\n") if aid.strip()]

            elif file.type == "application/json":
                # JSON file
                data = json.loads(content.decode("utf-8"))
                if isinstance(data, list):
                    assistant_ids = [str(aid) for aid in data]
                else:
                    assistant_ids = [str(data.get("assistant_id", ""))]

            elif file.type == "text/csv":
                # CSV file
                text = content.decode("utf-8")
                csv_reader = csv.reader(io.StringIO(text))
                assistant_ids = []
                for row in csv_reader:
                    if row:
                        assistant_ids.append(row[0].strip())

            else:
                st.error("Unsupported file type")
                return []

            st.success(f"✅ Loaded {len(assistant_ids)} assistants from file")
            return assistant_ids

        except Exception as e:
            st.error(f"Error parsing assistant file: {str(e)}")
            return []

    def _parse_questions_file(self, file) -> List[str]:
        """Parse uploaded questions file"""
        try:
            content = file.read()

            if file.type == "text/plain":
                # Plain text file
                text = content.decode("utf-8")
                questions = [q.strip() for q in text.split("\n") if q.strip()]

            elif file.type == "application/json":
                # JSON file
                data = json.loads(content.decode("utf-8"))
                if isinstance(data, list):
                    questions = [str(q) for q in data]
                else:
                    questions = [str(data.get("question", ""))]

            elif file.type == "text/csv":
                # CSV file
                text = content.decode("utf-8")
                csv_reader = csv.reader(io.StringIO(text))
                questions = []
                for row in csv_reader:
                    if row:
                        questions.append(row[0].strip())

            else:
                st.error("Unsupported file type")
                return []

            st.success(f"✅ Loaded {len(questions)} questions from file")
            return questions

        except Exception as e:
            st.error(f"Error parsing questions file: {str(e)}")
            return []

    def _run_experiment(self, config: Dict[str, Any]):
        """Execute the experiment"""
        experiment_data = {
            "assistant_ids": st.session_state.assistant_ids,
            "queries": st.session_state.questions,
            "run_immediately": st.session_state.get("run_immediately", True),
        }

        # Check if we should run immediately or create first for progress tracking
        run_immediately = experiment_data.get("run_immediately", True)
        
        if run_immediately:
            # Create experiment without running it first
            experiment_data_create_only = experiment_data.copy()
            experiment_data_create_only["run_immediately"] = False
            
            with st.spinner("🚀 Creating experiment..."):
                response = self.api_client.create_and_run_experiment(experiment_data_create_only)
            
            # If experiment was created successfully, start progress tracking and run
            if response.get("success") and response.get("data", {}).get("experiment"):
                experiment_id = response["data"]["experiment"]["experiment_id"]
                
                # Store experiment ID in session state for progress tracking
                st.session_state.tracking_experiment_id = experiment_id
                st.session_state.tracking_start_time = time.time()
                
                # Now run the experiment in the background (this will be async in real implementation)
                st.info("🚀 Experiment created! Starting execution with progress tracking...")
                st.rerun()  # Refresh to start showing progress
            else:
                st.error(f"❌ Failed to create experiment: {response.get('error', 'Unknown error')}")
                return
        else:
            # Original logic for non-immediate execution
            with st.spinner("🚀 Creating experiment..."):
                response = self.api_client.create_and_run_experiment(experiment_data)

        if response["success"]:
            data = response["data"]
            experiment_id = data["experiment"]["experiment_id"]

            st.success(f"✅ Experiment {experiment_id} completed successfully!")

            # Show results
            stats = data.get("stats", {})
            if stats:
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total Responses", stats.get("total_responses", 0))

                with col2:
                    st.metric("Successful", stats.get("completed_responses", 0))

                with col3:
                    st.metric("Failed", stats.get("failed_responses", 0))

                with col4:
                    success_rate = (
                        stats.get("completed_responses", 0)
                        / stats.get("total_responses", 1)
                    ) * 100
                    st.metric("Success Rate", f"{success_rate:.1f}%")

            # Guide user to next steps
            st.info("🎉 **What's next?**\n\n"
                   "• Go to **📊 View Experiments** to see all your experiments\n"
                   "• Go to **📈 Generate Reports** to create detailed analysis reports")

            st.balloons()

        else:
            st.error(f"❌ Failed to run experiment: {response['error']}")

    def _render_progress_tracking(self):
        """Render progress tracking UI for running experiments"""
        tracking_experiment_id = st.session_state.get("tracking_experiment_id")
        tracking_start_time = st.session_state.get("tracking_start_time")
        experiment_started = st.session_state.get("experiment_started", False)
        
        if not tracking_experiment_id:
            return
        
        # If experiment hasn't been started yet, start it
        if not experiment_started:
            st.info("🚀 Starting experiment execution...")
            
            # Start the experiment in a separate thread to avoid blocking
            def start_experiment_async():
                try:
                    run_response = self.api_client.run_existing_experiment(tracking_experiment_id)
                    if run_response.get("success"):
                        st.session_state.experiment_run_result = "success"
                    else:
                        st.session_state.experiment_run_result = f"error: {run_response.get('error', 'Unknown error')}"
                except Exception as e:
                    st.session_state.experiment_run_result = f"error: {str(e)}"
            
            # Start the thread
            thread = threading.Thread(target=start_experiment_async)
            thread.daemon = True  # Dies when main thread dies
            thread.start()
            
            # Mark as started so we don't start it again
            st.session_state.experiment_started = True
            st.success("✅ Experiment started in background!")
            time.sleep(1)  # Give it a moment to start
            st.rerun()
        
        # Check if tracking has been going on too long (5 minutes timeout)
        if tracking_start_time and (time.time() - tracking_start_time) > 300:
            st.warning("⚠️ Progress tracking timed out. The experiment may still be running.")
            del st.session_state.tracking_experiment_id
            del st.session_state.tracking_start_time
            if "experiment_started" in st.session_state:
                del st.session_state.experiment_started
            return
        
        # Check if there's an async experiment run result
        experiment_run_result = st.session_state.get("experiment_run_result")
        if experiment_run_result and experiment_run_result.startswith("error:"):
            st.error(f"❌ Failed to start experiment: {experiment_run_result[7:]}")  # Remove "error: " prefix
            # Clear tracking on error
            del st.session_state.tracking_experiment_id
            if "tracking_start_time" in st.session_state:
                del st.session_state.tracking_start_time
            if "experiment_started" in st.session_state:
                del st.session_state.experiment_started
            if "experiment_run_result" in st.session_state:
                del st.session_state.experiment_run_result
            return
        
        # Get progress data
        progress_response = self.api_client.get_experiment_progress(tracking_experiment_id)
        
        if not progress_response["success"]:
            st.error(f"Failed to get progress: {progress_response['error']}")
            # Clear tracking on error
            del st.session_state.tracking_experiment_id
            if "tracking_start_time" in st.session_state:
                del st.session_state.tracking_start_time
            if "experiment_started" in st.session_state:
                del st.session_state.experiment_started
            return
        
        progress_data = progress_response["data"]
        status = progress_data.get("status", "unknown")
        progress_percentage = progress_data.get("progress_percentage", 0)
        current_step = progress_data.get("current_step", "")
        completed_tasks = progress_data.get("completed_tasks", 0)
        total_tasks = progress_data.get("total_tasks", 0)
        eta_seconds = progress_data.get("eta_seconds")
        
        # Display progress UI
        st.subheader("📊 Experiment Progress")
        
        # Status
        if status == "running":
            st.info(f"🔄 Status: Running ({completed_tasks}/{total_tasks} tasks)")
        elif status == "completed":
            st.success("✅ Status: Completed")
            # Clear tracking when completed
            del st.session_state.tracking_experiment_id
            if "tracking_start_time" in st.session_state:
                del st.session_state.tracking_start_time
            if "experiment_started" in st.session_state:
                del st.session_state.experiment_started
            if "experiment_run_result" in st.session_state:
                del st.session_state.experiment_run_result
        elif status == "failed":
            st.error("❌ Status: Failed")
            # Clear tracking when failed
            del st.session_state.tracking_experiment_id
            if "tracking_start_time" in st.session_state:
                del st.session_state.tracking_start_time
            if "experiment_started" in st.session_state:
                del st.session_state.experiment_started
            if "experiment_run_result" in st.session_state:
                del st.session_state.experiment_run_result
        else:
            st.info(f"📋 Status: {status.title()}")
        
        # Progress bar
        st.progress(progress_percentage / 100.0)
        st.text(f"Progress: {progress_percentage:.1f}%")
        
        # Current step
        if current_step:
            st.text(f"Current step: {current_step}")
        
        # ETA
        if eta_seconds and eta_seconds > 0:
            eta_minutes = eta_seconds / 60
            if eta_minutes < 1:
                st.text(f"⏱️ ETA: {eta_seconds:.0f} seconds")
            else:
                st.text(f"⏱️ ETA: {eta_minutes:.1f} minutes")
        
        # Auto-refresh every 2 seconds if still running
        if status == "running":
            time.sleep(2)
            st.rerun()

def render_experiment_runner(config: Dict[str, Any]) -> None:
    """
    Render the experiment runner component

    Args:
        config: Configuration data from sidebar
    """
    runner = ExperimentRunner()
    runner.render(config)
