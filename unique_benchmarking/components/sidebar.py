"""
Sidebar component for configuration management.
"""

import streamlit as st
from config import ConfigManager


class SidebarComponent:
    """Handles sidebar UI and configuration management."""

    @staticmethod
    def render() -> None:
        """Render the sidebar configuration interface."""
        st.sidebar.header("Configuration")

        # Get current configuration
        config = ConfigManager.get_config()

        # Input fields
        user_id = st.sidebar.text_input(
            "User ID", value=config.user_id, help="Enter your user ID"
        )

        company_id = st.sidebar.text_input(
            "Company ID", value=config.company_id, help="Enter your company ID"
        )

        app_id = st.sidebar.text_input(
            "App ID", value=config.app_id, help="Enter your app ID"
        )

        api_key = st.sidebar.text_input(
            "API Key", value=config.api_key, type="password", help="Enter your API key"
        )

        # Action buttons
        SidebarComponent._render_action_buttons(user_id, company_id, app_id, api_key)

        # Status display
        SidebarComponent._render_status_display()

    @staticmethod
    def _render_action_buttons(
        user_id: str, company_id: str, app_id: str, api_key: str
    ) -> None:
        """Render save and clear configuration buttons."""
        col1, col2 = st.sidebar.columns(2)

        with col1:
            if st.button("Save Config", width="content"):
                if ConfigManager.save_config(user_id, company_id, app_id, api_key):
                    st.sidebar.success("Configuration saved!")
                else:
                    st.sidebar.error("Please fill all fields.")

        with col2:
            if st.button("Clear Config", width="content"):
                ConfigManager.clear_config()
                st.sidebar.info("Configuration cleared.")
                st.rerun()

    @staticmethod
    def _render_status_display() -> None:
        """Render configuration status and saved values."""
        if ConfigManager.is_config_valid():
            st.sidebar.success("✅ Configuration is saved")

            # Show cache status
            cache_info = ConfigManager.get_cache_info()
            if cache_info["exists"]:
                st.sidebar.info("💾 Persistent cache: Active")
            else:
                st.sidebar.warning("💾 Persistent cache: Not found")

            # Show saved configuration
            st.sidebar.markdown("**Saved Configuration:**")
            config = ConfigManager.get_config()

            st.sidebar.text(f"User ID: {config.user_id}")
            st.sidebar.text(f"Company ID: {config.company_id}")
            st.sidebar.text(f"App ID: {config.app_id}")
            st.sidebar.text(f"API Key: {ConfigManager.get_masked_api_key()}")
        else:
            st.sidebar.warning("⚠️ Please save your configuration")

            # Show cache status even when not configured
            cache_info = ConfigManager.get_cache_info()
            if cache_info["exists"]:
                st.sidebar.info("💾 Previous cache found - will load on save")
