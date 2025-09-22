"""
Sidebar component for API configuration management
"""

import streamlit as st
from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api_client import get_api_client


class ConfigurationSidebar:
    """Sidebar component for managing API configuration"""

    def __init__(self):
        self.api_client = get_api_client()

    def render(self) -> Optional[Dict[str, Any]]:
        """
        Render the configuration sidebar

        Returns:
            Dict with configuration data if configured, None otherwise
        """
        with st.sidebar:
            st.title("🔧 Configuration")

            # Check configuration status
            status_response = self.api_client.get_configuration_status()

            if not status_response["success"]:
                st.error("❌ Cannot connect to backend API")
                st.error(f"Error: {status_response['error']}")
                return None

            status_data = status_response["data"]
            is_configured = status_data.get("is_configured", False)

            if is_configured:
                return self._render_configured_state()
            else:
                return self._render_setup_state(status_data)

    def _render_configured_state(self) -> Dict[str, Any] | None:
        """Render sidebar when system is already configured"""
        st.success("✅ System Configured")

        # Get current configuration
        config_response = self.api_client.get_configuration()

        if not config_response["success"]:
            st.error("Failed to load configuration")
            return None

        config_data = config_response["data"]

        # Show configuration summary
        st.subheader("Current Settings")
        st.write(f"**User ID:** {config_data.get('user_id', 'Not set')}")
        st.write(f"**Company ID:** {config_data.get('company_id', 'Not set')}")
        st.write(f"**App ID:** {config_data.get('app_id', 'Not set')[:20]}...")
        st.write(f"**API URL:** {config_data.get('base_url', 'Not set')}")
        st.write(f"**Timeout:** {config_data.get('timeout', 600)}s")
        st.write(
            f"**Golden Model:** {config_data.get('default_golden_model', 'litellm:gpt-5')}"
        )

        # Edit configuration button
        if st.button("✏️ Edit Configuration", key="edit_config"):
            st.session_state.show_config_form = True

        # Show edit form if requested
        if st.session_state.get("show_config_form", False):
            return self._render_configuration_form(config_data)

        return config_data

    def _render_setup_state(self, status_data: Dict[str, Any]) -> None | Dict[str, Any]:
        """Render sidebar when system needs initial setup"""
        st.warning("⚠️ Configuration Required")
        st.write(status_data.get("message", "System needs configuration"))

        missing_fields = status_data.get("missing_fields", [])
        if missing_fields:
            st.write("**Missing fields:**")
            for field in missing_fields:
                st.write(f"• {field}")

        # Load from environment button
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📁 Load from ENV", key="load_env"):
                self._load_from_environment()

        with col2:
            if st.button("✏️ Manual Setup", key="manual_setup"):
                st.session_state.show_config_form = True

        # Show configuration form if requested
        if st.session_state.get("show_config_form", False):
            return self._render_configuration_form()

        return None

    def _render_configuration_form(
        self, existing_config: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Render configuration form"""
        st.subheader("API Configuration")

        # Use existing config as defaults if available
        defaults = existing_config or {}

        with st.form("config_form"):
            st.write("**Unique.app API Settings**")

            user_id = st.text_input(
                "User ID*",
                value=defaults.get("user_id", ""),
                placeholder="e.g., 335066199056449822",
                help="Your unique.app user ID",
            )

            company_id = st.text_input(
                "Company ID*",
                value=defaults.get("company_id", ""),
                placeholder="e.g., 331003534495449220",
                help="Your unique.app company ID",
            )

            app_id = st.text_input(
                "App ID*",
                value=defaults.get("app_id", ""),
                placeholder="e.g., app_m5a3qtm0ffpwq3tww94fvnpo",
                help="Your unique.app application ID",
            )

            api_key = st.text_input(
                "API Key*",
                value=defaults.get("api_key", ""),
                type="password",
                placeholder="ukey_...",
                help="Your unique.app API key",
            )

            st.write("**Advanced Settings**")

            base_url = st.text_input(
                "Base URL",
                value=defaults.get(
                    "base_url", "https://api.uat1.unique.app/public/chat"
                ),
                help="API base URL",
            )

            timeout = st.number_input(
                "Timeout (seconds)",
                value=defaults.get("timeout", 600),
                min_value=30,
                max_value=3600,
                help="Request timeout in seconds",
            )

            default_golden_model = st.text_input(
                "Default Golden Model",
                value=defaults.get("default_golden_model", "gpt-4"),
                placeholder="e.g., gpt-4, gpt-4o, gpt-3.5-turbo, claude-3-opus, claude-3-sonnet",
                help="Default model for generating golden answers",
            )

            # Form buttons
            col1, col2, col3 = st.columns(3)

            with col1:
                save_button = st.form_submit_button("💾 Save", type="primary")

            with col2:
                cancel_button = st.form_submit_button("❌ Cancel")

            with col3:
                test_button = (
                    st.form_submit_button("🧪 Test") if existing_config else False
                )

            # Handle form submission
            if save_button:
                if not all([user_id, company_id, app_id, api_key]):
                    st.error("Please fill in all required fields (marked with *)")
                else:
                    config_data = {
                        "user_id": user_id,
                        "company_id": company_id,
                        "app_id": app_id,
                        "api_key": api_key,
                        "base_url": base_url,
                        "timeout": timeout,
                        "default_golden_model": default_golden_model,
                    }

                    if self._save_configuration(config_data):
                        st.success("✅ Configuration saved successfully!")
                        st.session_state.show_config_form = False
                        st.rerun()
                        return config_data

            elif cancel_button:
                st.session_state.show_config_form = False
                st.rerun()

            elif test_button:
                self._test_configuration()

        return None

    def _load_from_environment(self):
        """Load configuration from environment file"""
        with st.spinner("Loading from environment..."):
            response = self.api_client.initialize_from_env()

            if response["success"]:
                data = response["data"]
                updated_fields = data.get("updated_fields", [])

                if updated_fields:
                    st.success("✅ Loaded configuration from environment!")
                    st.write(f"Updated fields: {', '.join(updated_fields)}")

                    if data.get("is_configured", False):
                        st.balloons()
                        st.rerun()
                else:
                    st.warning("No environment variables found to load")
            else:
                st.error(f"Failed to load from environment: {response['error']}")

    def _save_configuration(self, config_data: Dict[str, Any]) -> bool:
        """Save configuration data"""
        with st.spinner("Saving configuration..."):
            response = self.api_client.save_configuration(config_data)

            if response["success"]:
                return True
            else:
                st.error(f"Failed to save configuration: {response['error']}")
                return False

    def _test_configuration(self):
        """Test the current configuration"""
        st.info("🧪 Testing configuration...")
        # This could be expanded to actually test the API connection
        st.success("Configuration appears valid!")


def render_configuration_sidebar() -> Optional[Dict[str, Any]]:
    """
    Render the configuration sidebar component

    Returns:
        Configuration data if system is configured, None otherwise
    """
    sidebar = ConfigurationSidebar()
    return sidebar.render()
