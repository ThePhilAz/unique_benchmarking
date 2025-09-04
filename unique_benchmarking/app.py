"""
Main Streamlit application entry point.
Modular benchmarking app with configuration management and experiment runner.
"""

import streamlit as st
from config import ConfigManager
from components import (
    SidebarComponent,
    MainContentComponent,
    ExperimentRunnerComponent,
    ExperimentExplorerComponent,
)
from utils import AppUtils


def main():
    """Main application entry point."""
    # Setup page configuration
    AppUtils.setup_page_config()

    # Initialize session state
    ConfigManager.initialize_session_state()

    # Render header
    AppUtils.render_header()

    # Render sidebar (always visible)
    SidebarComponent.render()

    # Tab-based navigation
    tab1, tab2, tab3 = st.tabs(["⚙️ Configuration", "🧪 Experiments", "🔍 Explorer"])

    with tab1:
        MainContentComponent.render()

    with tab2:
        ExperimentRunnerComponent.render()

    with tab3:
        ExperimentExplorerComponent.render()


if __name__ == "__main__":
    main()
