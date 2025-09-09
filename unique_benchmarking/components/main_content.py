"""
Main content component for the Streamlit app.
"""

import streamlit as st
from config import ConfigManager


class MainContentComponent:
    """Handles main content area UI."""

    @staticmethod
    def render() -> None:
        """Render the main content area."""
        st.markdown("---")

        if ConfigManager.is_config_valid():
            MainContentComponent._render_configured_state()
        else:
            MainContentComponent._render_unconfigured_state()

    @staticmethod
    def _render_configured_state() -> None:
        """Render content when configuration is complete."""
        st.success("🎉 Configuration is set! Ready to add more functionality.")

        col1, col2 = st.columns(2)

        with col1:
            MainContentComponent._render_current_config()

        with col2:
            MainContentComponent._render_next_steps()

    @staticmethod
    def _render_unconfigured_state() -> None:
        """Render content when configuration is incomplete."""
        st.info("👈 Please configure your settings in the sidebar to get started.")

        # Add some helpful information
        st.markdown("""
        ### Getting Started
        
        To use this application, you'll need to provide:
        
        1. **User ID** - Your unique user identifier
        2. **Company ID** - Your company's identifier  
        3. **App ID** - The application identifier
        4. **API Key** - Your authentication key
        
        Once configured, your settings will be saved for the duration of your session.
        """)

    @staticmethod
    def _render_current_config() -> None:
        """Render current configuration display."""
        st.subheader("Current Configuration")
        config = ConfigManager.get_config()

        # Configuration details
        st.info(f"""
        **User ID:** {config.user_id}
        
        **Company ID:** {config.company_id}
        
        **App ID:** {config.app_id}
        
        **API Key:** {ConfigManager.get_masked_api_key()}
        
        **Timeout:** {config.timeout} seconds
        """)

        # Env file information
        env_info = ConfigManager.get_env_info()
        if env_info["exists"]:
            import datetime

            modified_time = "Unknown"
            if env_info["modified"]:
                modified_time = datetime.datetime.fromtimestamp(
                    env_info["modified"]
                ).strftime("%Y-%m-%d %H:%M:%S")

            st.success(f"""
            **💾 Configuration File Status:**
            - Status: Active
            - Size: {env_info["size"]} bytes
            - Last Modified: {modified_time}
            - Path: {env_info["path"]}
            """)
        else:
            st.warning("💾 No configuration file found")

    @staticmethod
    def _render_next_steps() -> None:
        """Render next steps information."""
        st.subheader("Next Steps")
        st.markdown("""
        Configuration is complete! You can now:
        
        - ✅ Add new functionality to the app
        - ✅ Configuration persists between app sessions
        - ✅ Use the sidebar to modify settings anytime
        - 🔄 Ready for iterative development
        - 💾 Data is securely cached to `.env.cache`
        """)

        # Placeholder for future functionality
        st.markdown("---")
        st.markdown("**🚀 Ready for new features!**")
        st.markdown(
            "This space is ready for additional functionality to be added iteratively."
        )
