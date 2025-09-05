"""
Main Streamlit application entry point.
Modular benchmarking app with configuration management and experiment runner.
"""

import streamlit as st
import logging
import sys
from config import ConfigManager
from components import (
    SidebarComponent,
    MainContentComponent,
    ExperimentRunnerComponent,
    ExperimentExplorerComponent,
)
from utils import AppUtils, LoggingUtils

# Configure logging for Streamlit
def setup_logging():
    """Configure logging to be visible in Streamlit."""
    # Create a custom formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler that writes to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Get the root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Add our console handler
    root_logger.addHandler(console_handler)
    
    # Add Streamlit session state handler for in-app log viewing
    streamlit_handler = LoggingUtils.create_streamlit_log_handler()
    root_logger.addHandler(streamlit_handler)
    
    # Also configure specific loggers
    app_logger = logging.getLogger('unique_benchmarking')
    app_logger.setLevel(logging.INFO)


def main():
    """Main application entry point."""
    # Setup logging first
    setup_logging()
    
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
    
    # Add logs viewer at the bottom
    if 'logs' in st.session_state and st.session_state.logs:
        st.markdown("---")
        with st.expander("📋 Application Logs", expanded=False):
            # Show last 20 logs
            recent_logs = st.session_state.logs[-20:]
            for log in recent_logs:
                st.text(log)
            
            if st.button("Clear Logs"):
                st.session_state.logs = []
                st.rerun()


if __name__ == "__main__":
    main()
