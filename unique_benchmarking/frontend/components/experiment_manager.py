"""
Experiment Manager component for viewing and managing experiments
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, Optional
from datetime import datetime
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api_client import get_api_client


class ExperimentManager:
    """Component for managing and viewing experiments"""

    def __init__(self):
        self.api_client = get_api_client()

    def render(self, config: Dict[str, Any]) -> None:
        """
        Render the experiment manager interface (deprecated - use individual methods)

        Args:
            config: Configuration data from sidebar
        """
        st.warning("⚠️ This method is deprecated. Use individual page methods instead.")

        if not config:
            st.error("⚠️ Please configure your API settings first!")
            return

        # Store config for use in other methods
        self._config = config

    def _render_experiments_list_tab(self):
        """Render the experiments list tab"""
        if not hasattr(self, "_config") or not self._config:
            st.error("⚠️ Please configure your API settings first!")
            return

        # Header with refresh button
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("## 🧪 Experiment Dashboard")
        with col2:
            if st.button("🔄 Refresh", type="secondary", width="stretch"):
                st.rerun()

        # Get all experiments (no filters)
        with st.spinner("🔍 Loading your experiments..."):
            experiments_response = self.api_client.get_experiments()

        if not experiments_response["success"]:
            st.error(f"❌ Failed to load experiments: {experiments_response['error']}")
            return

        experiments_data = experiments_response["data"]
        experiments = experiments_data.get("results", [])

        if not experiments:
            st.warning(
                "📭 No experiments found. Create your first experiment in the 'Run New Experiment' section!"
            )
            return

        # Stats overview
        total_count = experiments_data.get("count", len(experiments))
        completed_count = len([exp for exp in experiments if exp.get("end_time")])
        running_count = total_count - completed_count

        # Nice metrics display
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Experiments", total_count)
        with col2:
            st.metric("✅ Completed", completed_count)
        with col3:
            st.metric("⏳ Running", running_count)

        st.markdown("---")

        # Create options for the selectbox with better formatting
        experiment_options = ["🔍 Select an experiment to analyze..."]
        experiment_map = {}

        for exp in experiments:
            exp_id = exp["experiment_id"]
            start_time = self._format_datetime(exp.get("start_time"))
            status = "✅" if exp.get("end_time") else "⏳"
            assistants_count = len(exp.get("assistant_ids", []))
            questions_count = len(exp.get("queries", []))
            label = f"{status} {exp_id} | {start_time} | {assistants_count} assistants, {questions_count} questions"
            experiment_options.append(label)
            experiment_map[label] = exp

        # Beautiful experiment selector
        st.markdown("### 🎯 Select Experiment")
        selected_experiment_label = st.selectbox(
            "Choose an experiment to analyze:",
            experiment_options,
            index=0,
            key="experiment_selector",
            help="Select an experiment to view detailed statistics, configuration, or generate reports",
        )

        if selected_experiment_label != "🔍 Select an experiment to analyze...":
            selected_exp = experiment_map[selected_experiment_label]
            exp_id = selected_exp["experiment_id"]

            # Experiment quick info (only relevant metrics)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(
                    f"**🤖 Assistants**\n{len(selected_exp.get('assistant_ids', []))}"
                )
            with col2:
                st.info(f"**❓ Questions**\n{len(selected_exp.get('queries', []))}")
            with col3:
                status = (
                    "✅ Completed" if selected_exp.get("end_time") else "⏳ Running"
                )
                st.info(f"**📊 Status**\n{status}")

            # Automatically show statistics
            st.markdown("---")
            self._show_experiment_stats(exp_id)

            st.markdown("---")
            st.markdown("### 🎛️ Additional Actions")

            # Action buttons for additional actions
            col1, col2, col3 = st.columns(3)

            with col1:
                show_details = st.button(
                    "📋 View Detailed Results",
                    key="show_selected_details",
                    width="stretch",
                    type="primary",
                )

            with col2:
                if st.button(
                    "📈 Generate Report", key="show_selected_report", width="stretch"
                ):
                    self._generate_and_download_html_report(exp_id)

            with col3:
                export_data = st.button(
                    "📥 Export Data", key="show_selected_export", width="stretch"
                )

            # Display the requested information
            if show_details:
                st.divider()
                self._show_experiment_detailed_results(exp_id)

            if export_data:
                st.divider()
                self._export_experiment_data(exp_id)

        # Quick reference section
        st.markdown("---")
        with st.expander("📋 **All Experiments Overview**", expanded=False):
            st.markdown("*Quick reference for all your experiments*")

            # Create a nice table view
            table_data = []
            for exp in experiments:
                status = "✅ Completed" if exp.get("end_time") else "⏳ Running"
                table_data.append(
                    {
                        "Experiment": exp["experiment_id"],
                        "Status": status,
                        "Started": self._format_datetime(exp.get("start_time")),
                        "Assistants": len(exp.get("assistant_ids", [])),
                        "Questions": len(exp.get("queries", [])),
                    }
                )

            if table_data:
                import pandas as pd

                df = pd.DataFrame(table_data)
                st.dataframe(df, width="stretch", hide_index=True)

    def _render_generate_report_tab(self):
        """Render the generate report tab"""
        if not hasattr(self, "_config") or not self._config:
            st.error("⚠️ Please configure your API settings first!")
            return

        st.subheader("📈 Generate Experiment Report")

        # Check if an experiment is selected
        selected_exp_id = st.session_state.get("selected_experiment_id")
        selected_exp = st.session_state.get("selected_experiment")

        if not selected_exp_id:
            st.info(
                "👈 Please select an experiment from the 'Experiments List' tab first."
            )
            return

        # Display selected experiment info
        st.success(f"🎯 **Selected Experiment:** {selected_exp_id}")

        if selected_exp:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Assistants", len(selected_exp.get("assistant_ids", [])))
            with col2:
                st.metric("Questions", len(selected_exp.get("queries", [])))
            with col3:
                status = "Completed" if selected_exp.get("end_time") else "Running"
                st.metric("Status", status)

        st.divider()

        # Report configuration
        st.subheader("⚙️ Report Configuration")

        col1, col2 = st.columns(2)

        with col1:
            report_type = st.selectbox(
                "Report Type",
                options=["summary", "detailed", "comparison", "performance_analysis"],
                index=0,
                help="Choose the type of report to generate",
            )

        with col2:
            include_raw_data = st.checkbox(
                "Include Raw Data",
                value=False,
                help="Include raw response data in the report",
                key="mgr_include_raw_data",
            )

        # Additional options
        with st.expander("📋 Additional Options", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                export_format = st.selectbox(
                    "Export Format", options=["html", "pdf", "csv", "json"], index=0
                )

            with col2:
                include_charts = st.checkbox(
                    "Include Charts",
                    value=True,
                    help="Include visualization charts in the report",
                    key="mgr_include_charts",
                )

        # Generate report button
        st.divider()

        if st.button(
            "🚀 Generate Report",
            type="primary",
            width="stretch",
            key="mgr_generate_report_main",
        ):
            self._generate_report(
                experiment_id=selected_exp_id,
                report_type=report_type,
                include_raw_data=include_raw_data,
                export_format=export_format,
                include_charts=include_charts,
            )

        # Show current experiment results preview
        if st.checkbox(
            "👀 Preview Experiment Results", value=False, key="mgr_preview_results"
        ):
            self._show_experiment_results_preview(selected_exp_id)

    def _show_experiment_stats(self, experiment_id: str):
        """Show detailed experiment statistics"""
        with st.spinner("Loading experiment statistics..."):
            stats_response = self.api_client.get_experiment_stats(experiment_id)

        if stats_response["success"]:
            stats = stats_response["data"]

            st.markdown(f"### 📊 Statistics for {experiment_id}")

            # Create a clean, organized layout

            # Success Rate - Most important metric, highlighted
            success_rate = stats.get("success_rate", 0)
            if success_rate >= 80:
                st.success(f"🎯 **Success Rate: {success_rate:.1f}%** (Excellent)")
            elif success_rate >= 60:
                st.info(f"🎯 **Success Rate: {success_rate:.1f}%** (Good)")
            elif success_rate >= 40:
                st.warning(f"🎯 **Success Rate: {success_rate:.1f}%** (Fair)")
            else:
                st.error(
                    f"🎯 **Success Rate: {success_rate:.1f}%** (Needs Improvement)"
                )

            st.divider()

            # Response Statistics - 3 columns for full width utilization
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**📈 Response Metrics**")
                total_responses = stats.get("total_responses", 0)
                completed_responses = stats.get("completed_responses", 0)
                failed_responses = stats.get("failed_responses", 0)

                st.metric("Total Responses", total_responses)
                st.metric("✅ Completed", completed_responses)
                st.metric("❌ Failed", failed_responses)

            with col2:
                st.markdown("**⚙️ Configuration**")
                st.metric("Questions", stats.get("total_queries", 0))
                st.metric("Assistants", stats.get("total_assistants", 0))

            with col3:
                st.markdown("**⏱️ Performance**")
                # Performance metric
                avg_time = stats.get("average_response_time")
                if avg_time:
                    if avg_time < 5:
                        st.metric(
                            "⚡ Avg Response Time", f"{avg_time:.2f}s", delta="Fast"
                        )
                    elif avg_time < 15:
                        st.metric(
                            "⏱️ Avg Response Time", f"{avg_time:.2f}s", delta="Normal"
                        )
                    else:
                        st.metric(
                            "🐌 Avg Response Time", f"{avg_time:.2f}s", delta="Slow"
                        )
                else:
                    st.metric("⏱️ Avg Response Time", "N/A")

                # Add experiment status
                if stats.get("status"):
                    status = stats.get("status", "Unknown")
                    st.metric("Status", status.title())

            # Additional insights
            if total_responses > 0:
                st.divider()
                st.markdown("**🔍 Insights**")

                # Create insights based on the data
                insights = []

                if success_rate == 100:
                    insights.append(
                        "🌟 Perfect success rate! All assistants performed flawlessly."
                    )
                elif success_rate == 0:
                    insights.append(
                        "⚠️ No successful responses. Check assistant configurations."
                    )
                elif completed_responses > failed_responses:
                    insights.append(
                        f"✅ More successes ({completed_responses}) than failures ({failed_responses})."
                    )
                else:
                    insights.append(
                        f"❌ More failures ({failed_responses}) than successes ({completed_responses})."
                    )

                if avg_time:
                    if avg_time < 5:
                        insights.append(
                            "⚡ Excellent response times - under 5 seconds average."
                        )
                    elif avg_time > 30:
                        insights.append(
                            "🐌 Slow response times - consider optimizing assistants."
                        )

                for insight in insights:
                    st.write(f"• {insight}")

        else:
            st.error(f"Failed to load stats: {stats_response['error']}")

    def _show_experiment_detailed_results(self, experiment_id: str):
        """Show detailed results table with assistant responses and golden answers"""
        st.markdown(f"### 📋 Detailed Results for {experiment_id}")

        with st.spinner("Loading detailed experiment results..."):
            # Get experiment details and responses
            details_response = self.api_client.get_experiment_details(experiment_id)
            responses_response = self.api_client.get_experiment_responses(experiment_id)

        if not details_response["success"] or not responses_response["success"]:
            st.error("Failed to load experiment details or responses")
            return

        responses_data = responses_response["data"]
        responses = responses_data.get("results", [])

        if not responses:
            st.warning("No responses found for this experiment.")
            return

        # Get all golden answers for the questions in this experiment
        with st.spinner("Loading golden answers..."):
            golden_answers_response = self.api_client.get_golden_answers()

        golden_answers = {}
        if golden_answers_response["success"]:
            for golden_answer in golden_answers_response["data"].get("results", []):
                question = golden_answer.get("question", "")
                golden_answers[question] = golden_answer

        # Create comprehensive results table
        st.markdown("#### 📊 Assistant Performance Table")

        table_data = []
        for response in responses:
            question = response.get("question", "")
            # Get golden answer from the golden answers table
            golden_answer = golden_answers.get(question, {})
            golden_answer_text = golden_answer.get("answer", "No golden answer found")

            table_data.append(
                {
                    "Assistant ID": response.get("assistant_id", "N/A"),
                    "Question": question[:100] + ("..." if len(question) > 100 else ""),
                    "Assistant Answer": response.get("processed_answer", "N/A")[:150]
                    + (
                        "..." if len(response.get("processed_answer", "")) > 150 else ""
                    ),
                    "Golden Answer": golden_answer_text[:150]
                    + ("..." if len(golden_answer_text) > 150 else ""),
                    "Success": "✅" if response.get("success") else "❌",
                    "Hallucination": response.get("hallucination_level", "N/A"),
                    "Response Time": f"{self._calculate_duration(response.get('started_at'), response.get('ended_at'))}",
                    "Started": self._format_datetime(response.get("started_at")),
                }
            )

        if table_data:
            import pandas as pd

            df = pd.DataFrame(table_data)

            # Display metrics summary
            total_responses = len(table_data)
            successful_responses = len([r for r in table_data if r["Success"] == "✅"])
            success_rate = (
                (successful_responses / total_responses) * 100
                if total_responses > 0
                else 0
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Responses", total_responses)
            with col2:
                st.metric("Successful", successful_responses)
            with col3:
                st.metric("Success Rate", f"{success_rate:.1f}%")

            st.markdown("---")

            # Display the detailed table
            st.dataframe(df, width="stretch", hide_index=True)

            # Show individual response details if requested
            st.markdown("#### 🔍 Individual Response Analysis")

            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                filter_success = st.selectbox(
                    "Filter by Success:",
                    ["All", "✅ Successful Only", "❌ Failed Only"],
                    key="filter_success",
                )
            with col2:
                filter_assistant = st.selectbox(
                    "Filter by Assistant:",
                    ["All"] + list(set([r["Assistant ID"] for r in table_data])),
                    key="filter_assistant",
                )

            # Apply filters
            filtered_data = table_data
            if filter_success != "All":
                success_value = "✅" if filter_success == "✅ Successful Only" else "❌"
                filtered_data = [
                    r for r in filtered_data if r["Success"] == success_value
                ]

            if filter_assistant != "All":
                filtered_data = [
                    r for r in filtered_data if r["Assistant ID"] == filter_assistant
                ]

            # Show filtered results
            st.write(f"Showing {len(filtered_data)} of {total_responses} responses")

            # Find matching responses for filtered data
            filtered_responses = []
            for response_data in filtered_data[:10]:  # Show first 10 filtered results
                # Find the matching response from the original responses list
                matching_response = None
                for response in responses:
                    if (
                        response.get("assistant_id") == response_data["Assistant ID"]
                        and response.get("question", "")[:100]
                        == response_data["Question"][:100]
                    ):
                        matching_response = response
                        break
                if matching_response:
                    filtered_responses.append(matching_response)

            for i, response in enumerate(filtered_responses):
                response_data = filtered_data[i]
                question = response.get("question", "")
                golden_answer = golden_answers.get(question, {})

                with st.expander(
                    f"{response_data['Success']} {response_data['Assistant ID']} - Response {i + 1}"
                ):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Question:**")
                        st.write(question)

                        st.markdown("**Assistant Answer:**")
                        st.write(response.get("processed_answer", "N/A"))

                        if response_data["Hallucination"] != "N/A":
                            st.markdown(
                                f"**Hallucination Level:** {response_data['Hallucination']}"
                            )

                        if response.get("hallucination_reason"):
                            st.markdown("**Hallucination Reason:**")
                            st.write(response.get("hallucination_reason"))

                    with col2:
                        st.markdown("**Golden Answer (Reference):**")
                        st.write(golden_answer.get("answer", "No golden answer found"))

                        st.markdown("**Performance Metrics:**")
                        st.write(f"• Success: {response_data['Success']}")
                        st.write(f"• Response Time: {response_data['Response Time']}")
                        st.write(f"• Started: {response_data['Started']}")

                        if response.get("references"):
                            st.markdown("**References:**")
                            refs = response.get("references", [])
                            for ref in refs[:3]:  # Show first 3 references
                                st.write(f"• {ref}")

    def _show_experiment_details(self, experiment_id: str):
        """Show detailed experiment information"""
        with st.spinner("Loading experiment details..."):
            details_response = self.api_client.get_experiment_details(experiment_id)

        if details_response["success"]:
            experiment = details_response["data"]

            st.markdown(f"### 📋 Details for {experiment_id}")

            # Basic information
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Basic Information:**")
                st.write(f"- **Experiment ID:** {experiment.get('experiment_id')}")
                st.write(f"- **User ID:** {experiment.get('user_id')}")
                st.write(f"- **Company ID:** {experiment.get('company_id')}")
                st.write(f"- **Start Time:** {experiment.get('start_time')}")
                st.write(
                    f"- **End Time:** {experiment.get('end_time', 'Still running')}"
                )

            with col2:
                st.write("**Configuration:**")
                assistants = experiment.get("assistant_ids", [])
                queries = experiment.get("queries", [])
                st.write(f"- **Assistants Count:** {len(assistants)}")
                st.write(f"- **Queries Count:** {len(queries)}")

            # Show assistants
            if assistants:
                st.write("**Assistant IDs:**")
                for i, assistant_id in enumerate(assistants, 1):
                    st.write(f"{i}. {assistant_id}")

            # Show queries (first few)
            if queries:
                st.write("**Queries:**")
                display_queries = queries[:5]  # Show first 5
                for i, query in enumerate(display_queries, 1):
                    st.write(f"{i}. {query}")
                if len(queries) > 5:
                    st.write(f"... and {len(queries) - 5} more queries")

        else:
            st.error(f"Failed to load details: {details_response['error']}")

    def _show_experiment_results_preview(self, experiment_id: str):
        """Show a preview of experiment results"""
        with st.spinner("Loading experiment results..."):
            responses_response = self.api_client.get_experiment_responses(experiment_id)

        if responses_response["success"]:
            responses_data = responses_response["data"]
            responses = responses_data.get("results", [])

            if not responses:
                st.info("No responses found for this experiment.")
                return

            st.markdown(f"### 👀 Results Preview ({len(responses)} responses)")

            # Create a DataFrame for better display
            df_data = []
            for response in responses:
                df_data.append(
                    {
                        "Assistant ID": response.get("assistant_id", "N/A"),
                        "Question": response.get("question", "N/A")[:50] + "..."
                        if len(response.get("question", "")) > 50
                        else response.get("question", "N/A"),
                        "Success": "✅" if response.get("success") else "❌",
                        "Hallucination": response.get("hallucination_level", "N/A"),
                        "Started": self._format_datetime(response.get("started_at")),
                        "Duration": self._calculate_duration(
                            response.get("started_at"), response.get("ended_at")
                        ),
                    }
                )

            df = pd.DataFrame(df_data)
            st.dataframe(df, width="stretch")

            # Show some sample responses
            if st.checkbox(
                "Show Sample Responses", value=False, key="mgr_show_samples"
            ):
                sample_responses = responses[:3]  # Show first 3
                for i, response in enumerate(sample_responses, 1):
                    with st.expander(
                        f"Response {i}: {response.get('assistant_id')} - {'✅' if response.get('success') else '❌'}"
                    ):
                        st.write(f"**Question:** {response.get('question')}")
                        st.write(
                            f"**Answer:** {response.get('processed_answer', 'No answer')}"
                        )
                        if response.get("hallucination_level"):
                            st.write(
                                f"**Hallucination Level:** {response.get('hallucination_level')}"
                            )
                        if response.get("hallucination_reason"):
                            st.write(
                                f"**Hallucination Reason:** {response.get('hallucination_reason')}"
                            )

        else:
            st.error(f"Failed to load results: {responses_response['error']}")

    def _calculate_duration(self, started_at: str, ended_at: str) -> str:
        """Calculate duration between two timestamps"""
        if not started_at or not ended_at:
            return "N/A"

        try:
            # Parse timestamps (assuming ISO format)
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            duration = (end - start).total_seconds()
            return f"{duration:.2f}s"
        except Exception:
            return "N/A"

    def _export_experiment_data(self, experiment_id: str):
        """Export experiment data"""
        with st.spinner("Exporting experiment data..."):
            # Get experiment details and responses
            details_response = self.api_client.get_experiment_details(experiment_id)
            responses_response = self.api_client.get_experiment_responses(experiment_id)

            if details_response["success"] and responses_response["success"]:
                experiment = details_response["data"]
                responses = responses_response["data"].get("results", [])

                # Create export data
                export_data = {
                    "experiment": experiment,
                    "responses": responses,
                    "export_timestamp": datetime.now().isoformat(),
                }

                # Convert to JSON for download
                import json

                json_str = json.dumps(export_data, indent=2, default=str)

                st.download_button(
                    label="📥 Download Experiment Data (JSON)",
                    data=json_str,
                    file_name=f"experiment_{experiment_id}_data.json",
                    mime="application/json",
                )

                st.success("✅ Export data prepared! Click the download button above.")

            else:
                st.error("Failed to export experiment data.")

    def _generate_and_download_html_report(self, experiment_id: str):
        """Generate and download the enhanced HTML report directly"""

        with st.spinner("🔄 Generating enhanced HTML report..."):
            try:
                # Get experiment details and responses
                details_response = self.api_client.get_experiment_details(experiment_id)
                responses_response = self.api_client.get_experiment_responses(
                    experiment_id
                )

                if not details_response["success"] or not responses_response["success"]:
                    st.error("❌ Failed to fetch experiment data")
                    return

                # Get golden answers
                golden_answers_data = []
                golden_answers_response = self.api_client.get_golden_answers()
                if golden_answers_response["success"]:
                    golden_answers_data = golden_answers_response["data"].get(
                        "results", []
                    )

                # Import report generator
                import sys
                import os
                from datetime import datetime

                sys.path.append(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                from utils.report_generator import EnhancedReportGenerator

                # Generate enhanced HTML report
                generator = EnhancedReportGenerator()

                experiment_full_data = details_response["data"]
                responses_data = responses_response["data"].get("results", [])

                html_content = generator.generate_enhanced_report(
                    experiment_full_data, responses_data, golden_answers_data
                )

                # Create download button
                filename = f"enhanced_report_{experiment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

                st.success("✅ Enhanced HTML report generated successfully!")

                st.download_button(
                    "📥 Download Enhanced HTML Report",
                    data=html_content,
                    file_name=filename,
                    mime="text/html",
                    width="stretch",
                    key=f"download_html_{experiment_id}",
                    type="primary",
                )

            except Exception as e:
                st.error(f"❌ Error generating report: {str(e)}")
                st.exception(e)

    def _generate_report(
        self,
        experiment_id: str,
        report_type: str,
        include_raw_data: bool,
        export_format: str,
        include_charts: bool,
    ):
        """Generate enhanced experiment report"""

        with st.spinner("🔄 Generating enhanced report..."):
            try:
                # Get experiment details and responses
                details_response = self.api_client.get_experiment_details(experiment_id)
                responses_response = self.api_client.get_experiment_responses(
                    experiment_id
                )

                if not details_response["success"] or not responses_response["success"]:
                    st.error("❌ Failed to fetch experiment data")
                    return

                # Get golden answers
                golden_answers_data = []
                golden_answers_response = self.api_client.get_golden_answers()
                if golden_answers_response["success"]:
                    golden_answers_data = golden_answers_response["data"].get(
                        "results", []
                    )

                # Import report generator
                import sys
                import os
                from datetime import datetime

                sys.path.append(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                from utils.report_generator import EnhancedReportGenerator

                # Generate report
                generator = EnhancedReportGenerator()

                experiment_full_data = details_response["data"]
                responses_data = responses_response["data"].get("results", [])

                if export_format == "html":
                    html_content = generator.generate_enhanced_report(
                        experiment_full_data, responses_data, golden_answers_data
                    )

                    # Show success message
                    st.success("✅ Enhanced HTML report generated successfully!")

                    # Create download button
                    filename = f"enhanced_report_{experiment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

                    st.download_button(
                        "📥 Download Enhanced HTML Report",
                        data=html_content,
                        file_name=filename,
                        mime="text/html",
                        width="stretch",
                        key=f"download_html_{experiment_id}",
                    )

                    # Show report features
                    with st.expander("📋 **Enhanced Report Features**", expanded=True):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("""
                            **📊 Analytics:**
                            - Multi-dimensional scoring
                            - Performance charts
                            - Success rate analysis
                            - Question-centric view
                            """)

                        with col2:
                            st.markdown("""
                            **🎯 Evaluation Tools:**
                            - Interactive scoring (0-5)
                            - Comment fields
                            - Flag system
                            - Auto-save functionality
                            """)

                        with col3:
                            st.markdown("""
                            **⚡ Advanced Features:**
                            - Offline-ready
                            - Bulk operations
                            - Keyboard shortcuts
                            - Export capabilities
                            """)

                elif export_format == "json":
                    # Generate JSON export
                    json_data = {
                        "experiment": experiment_full_data,
                        "responses": responses_data,
                        "golden_answers": golden_answers_data,
                        "metadata": {
                            "generated_at": datetime.now().isoformat(),
                            "report_type": report_type,
                            "include_raw_data": include_raw_data,
                            "include_charts": include_charts,
                            "version": "2.0",
                        },
                    }

                    filename = f"experiment_data_{experiment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

                    st.success("✅ JSON data export ready!")
                    st.download_button(
                        "📥 Download JSON Data",
                        data=json.dumps(json_data, indent=2),
                        file_name=filename,
                        mime="application/json",
                        width="stretch",
                        key=f"download_json_{experiment_id}",
                    )

                elif export_format == "csv":
                    # Generate CSV export
                    import pandas as pd

                    # Flatten responses data for CSV
                    csv_data = []
                    for response in responses_data:
                        csv_row = {
                            "experiment_id": experiment_id,
                            "assistant_id": response.get("assistant_id", ""),
                            "chat_id": response.get("chat_id", ""),
                            "question": response.get("question", ""),
                            "answer": response.get(
                                "processed_answer", response.get("answer", "")
                            ),
                            "success": response.get("success", False),
                            "hallucination_level": response.get(
                                "hallucination_level", ""
                            ),
                            "hallucination_reason": response.get(
                                "hallucination_reason", ""
                            ),
                            "started_at": response.get("started_at", ""),
                            "ended_at": response.get("ended_at", ""),
                        }
                        csv_data.append(csv_row)

                    df = pd.DataFrame(csv_data)
                    csv_content = df.to_csv(index=False)

                    filename = f"experiment_responses_{experiment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

                    st.success("✅ CSV export ready!")
                    st.download_button(
                        "📥 Download CSV Export",
                        data=csv_content,
                        file_name=filename,
                        mime="text/csv",
                        width="stretch",
                        key=f"download_csv_{experiment_id}",
                    )

                else:
                    st.warning(
                        f"⚠️ Export format '{export_format}' not yet implemented. Using HTML instead."
                    )
                    # Fallback to HTML
                    html_content = generator.generate_enhanced_report(
                        experiment_full_data, responses_data, golden_answers_data
                    )

                    filename = f"enhanced_report_{experiment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

                    st.download_button(
                        "📥 Download Enhanced HTML Report",
                        data=html_content,
                        file_name=filename,
                        mime="text/html",
                        width="stretch",
                        key=f"download_html_fallback_{experiment_id}",
                    )

                # Show report statistics
                st.markdown("### 📈 Report Statistics")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total Responses", len(responses_data))
                with col2:
                    st.metric(
                        "Questions",
                        len(set(r.get("question", "") for r in responses_data)),
                    )
                with col3:
                    st.metric(
                        "Assistants",
                        len(set(r.get("assistant_id", "") for r in responses_data)),
                    )
                with col4:
                    st.metric("Golden Answers", len(golden_answers_data))

            except Exception as e:
                st.error(f"❌ Error generating report: {str(e)}")
                st.exception(e)

    def _format_datetime(self, datetime_str: Optional[str]) -> str:
        """Format datetime string to remove timezone info"""
        if not datetime_str:
            return "Unknown time"

        try:
            # Parse the datetime string (assuming ISO format with timezone)
            from datetime import datetime

            # Handle different datetime formats
            if "T" in datetime_str:
                # ISO format: "2025-09-22T18:32:34.508136+00:00"
                if "+" in datetime_str:
                    dt_part = datetime_str.split("+")[0]
                elif "Z" in datetime_str:
                    dt_part = datetime_str.replace("Z", "")
                else:
                    dt_part = datetime_str

                # Parse and format
                if "." in dt_part:
                    # With microseconds
                    dt = datetime.fromisoformat(dt_part)
                else:
                    # Without microseconds
                    dt = datetime.fromisoformat(dt_part)

                # Format as readable string without timezone
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                # Already in simple format
                return datetime_str

        except Exception:
            # If parsing fails, return the original string
            return str(datetime_str)


def render_experiment_manager(config: Dict[str, Any]) -> None:
    """
    Render the experiment manager component

    Args:
        config: Configuration data from sidebar
    """
    manager = ExperimentManager()
    manager.render(config)
