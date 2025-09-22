"""
Main Streamlit application for Unique Benchmarking
"""

import streamlit as st
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from components.sidebar import render_configuration_sidebar
from components.experiment_runner import render_experiment_runner
from components.experiment_manager import ExperimentManager
from utils.api_client import clear_api_client_cache


def main():
    """Main application entry point"""
    # Page configuration
    st.set_page_config(
        page_title="Unique Benchmarking",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Render sidebar for configuration
    config = render_configuration_sidebar()

    # Main content area
    st.title("🎯 Unique Benchmarking Dashboard")

    if config is None:
        # System not configured yet
        st.info("👈 Please configure your API settings in the sidebar to get started.")

        st.markdown("""
        ### Welcome to Unique Benchmarking!
        
        This application helps you benchmark and evaluate AI assistants using the Unique.app platform.
        
        **To get started:**
        1. Configure your API settings in the sidebar
        2. Create and run experiments
        3. Analyze results and performance metrics
        
        **You'll need:**
        - Your Unique.app User ID
        - Your Company ID  
        - Application ID
        - API Key
        """)

    else:
        # System is configured, show main application
        # Add cache clearing button in sidebar for development
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔧 Developer Tools")
        if st.sidebar.button(
            "🔄 Clear Cache", help="Clear cached data (for development)"
        ):
            clear_api_client_cache()
            st.sidebar.success("Cache cleared!")
            st.rerun()

        # Create clean tab navigation in main content area
        tab1, tab2 = st.tabs(["🚀 Run New Experiment", "📊 View Experiments"])

        with tab1:
            render_experiment_runner(config)

        with tab2:
            render_experiment_list(config)


def render_experiment_list(config: dict) -> None:
    """Render the experiment list page"""
    manager = ExperimentManager()
    manager._config = config
    manager._render_experiments_list_tab()


if __name__ == "__main__":
    main()
