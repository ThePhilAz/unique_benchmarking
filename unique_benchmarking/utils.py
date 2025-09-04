"""
Utility functions for the Streamlit app.
"""

import streamlit as st


class AppUtils:
    """General utility functions for the application."""

    @staticmethod
    def setup_page_config() -> None:
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="Benchmarking App",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    @staticmethod
    def render_header() -> None:
        """Render the main application header."""
        st.title("📊 Benchmarking App")
        st.markdown("""
        Welcome to the Benchmarking App - your tool for iterative development and testing.
        """)

    @staticmethod
    def show_success_message(message: str) -> None:
        """Show a success message."""
        st.success(f"✅ {message}")

    @staticmethod
    def show_error_message(message: str) -> None:
        """Show an error message."""
        st.error(f"❌ {message}")

    @staticmethod
    def show_info_message(message: str) -> None:
        """Show an info message."""
        st.info(f"ℹ️ {message}")

    @staticmethod
    def show_warning_message(message: str) -> None:
        """Show a warning message."""
        st.warning(f"⚠️ {message}")


class ValidationUtils:
    """Validation utility functions."""

    @staticmethod
    def validate_required_fields(**fields) -> tuple[bool, list[str]]:
        """
        Validate that all required fields are provided.

        Args:
            **fields: Keyword arguments representing field names and values

        Returns:
            tuple: (is_valid, list_of_missing_fields)
        """
        missing_fields = []

        for field_name, field_value in fields.items():
            if not field_value or (
                isinstance(field_value, str) and not field_value.strip()
            ):
                missing_fields.append(field_name.replace("_", " ").title())

        return len(missing_fields) == 0, missing_fields

    @staticmethod
    def validate_api_key_format(api_key: str) -> bool:
        """
        Validate API key format (basic validation).

        Args:
            api_key: The API key to validate

        Returns:
            bool: True if format appears valid
        """
        if not api_key:
            return False

        # Basic validation - at least 10 characters, contains alphanumeric
        return len(api_key) >= 10 and any(c.isalnum() for c in api_key)


class DisplayUtils:
    """Display utility functions."""

    @staticmethod
    def create_info_box(title: str, content: str, icon: str = "ℹ️") -> None:
        """Create a styled info box."""
        st.markdown(
            f"""
        <div style="
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f0f2f6;
            border-left: 4px solid #1f77b4;
            margin: 1rem 0;
        ">
            <h4 style="margin: 0 0 0.5rem 0; color: #1f77b4;">
                {icon} {title}
            </h4>
            <p style="margin: 0; color: #333;">
                {content}
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    @staticmethod
    def create_status_badge(text: str, status: str = "success") -> str:
        """
        Create a status badge HTML.

        Args:
            text: Badge text
            status: Badge status (success, warning, error, info)

        Returns:
            str: HTML for the badge
        """
        colors = {
            "success": "#28a745",
            "warning": "#ffc107",
            "error": "#dc3545",
            "info": "#17a2b8",
        }

        color = colors.get(status, colors["info"])

        return f"""
        <span style="
            background-color: {color};
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.875rem;
            font-weight: 500;
        ">
            {text}
        </span>
        """
