"""
Configuration management for the Streamlit app.
Handles session state initialization, configuration validation, and persistent storage.
"""

import streamlit as st
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    """Data class for application configuration."""

    user_id: str = ""
    company_id: str = ""
    app_id: str = ""
    api_key: str = ""
    base_url: str = ""
    timeout: int = 120
    config_saved: bool = False


class ConfigManager:
    """Manages application configuration, session state, and persistent storage."""

    CONFIG_KEYS = [
        "user_id",
        "company_id",
        "app_id",
        "api_key",
        "base_url",
        "timeout",
        "config_saved",
    ]
    EXPERIMENT_KEYS = [
        "experiment_assistant_ids",
        "experiment_questions",
        "experiment_configured",
    ]
    ENV_FILE = "unique.env"
    EXPERIMENT_CACHE_FILE = ".experiment.cache"
    EXPERIMENT_HISTORY_FILE = ".experiment_history.json"

    @staticmethod
    def _get_env_file_path() -> Path:
        """Get the path to the env file."""
        return Path(ConfigManager.ENV_FILE)

    @staticmethod
    def _load_from_env() -> Optional[Dict[str, Any]]:
        """Load configuration from unique.env file."""
        env_file = ConfigManager._get_env_file_path()

        if not env_file.exists():
            return None

        try:
            config_data = {}
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Map env keys to config keys
                        if key == "USER_ID":
                            config_data["user_id"] = value
                        elif key == "COMPANY_ID":
                            config_data["company_id"] = value
                        elif key == "APP_ID":
                            config_data["app_id"] = value
                        elif key == "API_KEY":
                            config_data["api_key"] = value
                        elif key == "BASE_URL":
                            config_data["base_url"] = value
                        elif key == "TIMEOUT":
                            try:
                                config_data["timeout"] = int(value)
                            except ValueError:
                                config_data["timeout"] = 120

            # Mark as saved if we have the required fields
            if all(
                key in config_data
                for key in ["user_id", "company_id", "app_id", "api_key", "base_url"]
            ):
                config_data["config_saved"] = True
            else:
                config_data["config_saved"] = False

            return config_data
        except Exception as e:
            st.error(f"Error loading env file: {e}")
            return None

    @staticmethod
    def _save_to_env(config_data: Dict[str, Any]) -> bool:
        """Save configuration to unique.env file."""
        try:
            env_file = ConfigManager._get_env_file_path()

            with open(env_file, "w") as f:
                f.write(f"USER_ID={config_data.get('user_id', '')}\n")
                f.write(f"COMPANY_ID={config_data.get('company_id', '')}\n")
                f.write("\n")  # Empty line for readability
                f.write(f"APP_ID={config_data.get('app_id', '')}\n")
                f.write(f"API_KEY={config_data.get('api_key', '')}\n")
                f.write(f"BASE_URL={config_data.get('base_url', '')}\n")
                f.write(f"TIMEOUT={config_data.get('timeout', 120)}\n")
                f.write(f"CONFIG_SAVED={config_data.get('config_saved', False)}\n")

            return True
        except Exception as e:
            st.error(f"Error saving env file: {e}")
            return False

    @staticmethod
    def _delete_env() -> bool:
        """Delete the env file."""
        try:
            env_file = ConfigManager._get_env_file_path()
            if env_file.exists():
                env_file.unlink()
            return True
        except Exception as e:
            st.error(f"Error deleting env file: {e}")
            return False

    @staticmethod
    def initialize_session_state() -> None:
        """Initialize session state with default values, loading from env file if available."""
        defaults = {
            "user_id": "",
            "company_id": "",
            "app_id": "",
            "api_key": "",
            "base_url": "",
            "timeout": 120,
            "config_saved": False,
        }

        # Try to load from env file first
        env_data = ConfigManager._load_from_env()

        for key, default_value in defaults.items():
            if key not in st.session_state:
                # Use env value if available, otherwise use default
                if env_data and key in env_data:
                    st.session_state[key] = env_data[key]
                else:
                    st.session_state[key] = default_value

    @staticmethod
    def get_config() -> AppConfig:
        """Get current configuration from session state."""
        return AppConfig(
            user_id=st.session_state.get("user_id", ""),
            company_id=st.session_state.get("company_id", ""),
            app_id=st.session_state.get("app_id", ""),
            api_key=st.session_state.get("api_key", ""),
            base_url=st.session_state.get("base_url", ""),
            timeout=st.session_state.get("timeout", 120),
            config_saved=st.session_state.get("config_saved", False),
        )

    @staticmethod
    def save_config(
        user_id: str,
        company_id: str,
        app_id: str,
        api_key: str,
        base_url: str,
        timeout: int = 120,
    ) -> bool:
        """
        Save configuration to session state and persistent cache.

        Args:
            user_id: User ID
            company_id: Company ID
            app_id: Application ID
            api_key: API Key
            timeout: Timeout in seconds (default: 120)

        Returns:
            bool: True if all fields are provided and saved, False otherwise
        """
        if not all([user_id, company_id, app_id, api_key]):
            return False

        # Update session state
        st.session_state.user_id = user_id
        st.session_state.company_id = company_id
        st.session_state.app_id = app_id
        st.session_state.api_key = api_key
        st.session_state.base_url = base_url
        st.session_state.timeout = timeout
        st.session_state.config_saved = True

        # Save to env file
        config_data = {
            "user_id": user_id,
            "company_id": company_id,
            "app_id": app_id,
            "api_key": api_key,
            "base_url": base_url,
            "timeout": timeout,
            "config_saved": True,
        }

        env_saved = ConfigManager._save_to_env(config_data)
        if not env_saved:
            st.warning("Configuration saved to session but failed to save to env file.")

        return True

    @staticmethod
    def clear_config() -> None:
        """Clear all configuration from session state and delete persistent cache."""
        # Clear session state
        for key in ConfigManager.CONFIG_KEYS:
            if key == "config_saved":
                st.session_state[key] = False
            elif key == "timeout":
                st.session_state[key] = 120
            else:
                st.session_state[key] = ""

        # Delete env file
        env_deleted = ConfigManager._delete_env()
        if not env_deleted:
            st.warning("Session cleared but failed to delete env file.")

    @staticmethod
    def is_config_valid() -> bool:
        """Check if current configuration is valid and complete."""
        config = ConfigManager.get_config()
        return all(
            [
                config.user_id,
                config.company_id,
                config.app_id,
                config.base_url,
                config.api_key,
                config.config_saved,
            ]
        )

    @staticmethod
    def get_masked_api_key() -> str:
        """Get masked API key for display purposes."""
        api_key = st.session_state.get("api_key", "")
        return "*" * len(api_key) if api_key else ""

    @staticmethod
    def env_exists() -> bool:
        """Check if env file exists."""
        return ConfigManager._get_env_file_path().exists()

    @staticmethod
    def get_env_info() -> Dict[str, Any]:
        """Get information about the env file."""
        env_file = ConfigManager._get_env_file_path()

        if not env_file.exists():
            return {
                "exists": False,
                "path": str(env_file),
                "size": 0,
                "modified": None,
            }

        try:
            stat = env_file.stat()
            return {
                "exists": True,
                "path": str(env_file),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }
        except Exception:
            return {
                "exists": True,
                "path": str(env_file),
                "size": 0,
                "modified": None,
            }

    @staticmethod
    def save_experiment_state(assistant_ids: List[str], questions: List[str]) -> bool:
        """
        Save experiment configuration to cache.

        Args:
            assistant_ids: List of assistant IDs
            questions: List of questions

        Returns:
            bool: True if saved successfully
        """
        try:
            experiment_data = {
                "experiment_assistant_ids": assistant_ids,
                "experiment_questions": questions,
                "experiment_configured": True,
            }

            cache_file = Path(ConfigManager.EXPERIMENT_CACHE_FILE)
            with open(cache_file, "w") as f:
                json.dump(experiment_data, f, indent=2)

            return True
        except Exception as e:
            st.error(f"Error saving experiment state: {e}")
            return False

    @staticmethod
    def load_experiment_state() -> Optional[Dict[str, Any]]:
        """Load experiment configuration from cache."""
        cache_file = Path(ConfigManager.EXPERIMENT_CACHE_FILE)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading experiment state: {e}")
            return None

    @staticmethod
    def clear_experiment_state() -> bool:
        """Clear experiment state cache."""
        try:
            cache_file = Path(ConfigManager.EXPERIMENT_CACHE_FILE)
            if cache_file.exists():
                cache_file.unlink()
            return True
        except Exception as e:
            st.error(f"Error clearing experiment state: {e}")
            return False

    @staticmethod
    def load_experiment_history() -> List[Dict[str, Any]]:
        """Load experiment history by scanning experiments directory."""
        experiments_dir = Path("experiments")

        if not experiments_dir.exists():
            return []

        history = []

        try:
            # Scan all experiment directories
            for exp_dir in experiments_dir.iterdir():
                if exp_dir.is_dir() and exp_dir.name.startswith("experiment_"):
                    # Try to load experiment summary
                    summary_file = exp_dir / "experiment_summary.json"
                    config_file = exp_dir / "experiment_config.json"

                    if summary_file.exists():
                        try:
                            with open(summary_file, "r") as f:
                                summary_data = json.load(f)

                            # Count actual result files in success/error directories
                            success_dir = exp_dir / "success"
                            error_dir = exp_dir / "error"

                            success_count = 0
                            error_count = 0
                            total_execution_time = 0

                            if success_dir.exists():
                                success_files = [
                                    f
                                    for f in success_dir.iterdir()
                                    if f.is_file() and f.name.endswith(".json")
                                ]
                                success_count = len(success_files)

                                # Try to get execution time from individual result files
                                for result_file in success_files:
                                    try:
                                        with open(result_file, "r") as f:
                                            result_data = json.load(f)
                                        test_info = result_data.get("test_info", {})
                                        total_execution_time += test_info.get(
                                            "execution_time", 0
                                        )
                                    except Exception:
                                        continue

                            if error_dir.exists():
                                error_files = [
                                    f
                                    for f in error_dir.iterdir()
                                    if f.is_file() and f.name.endswith(".json")
                                ]
                                error_count = len(error_files)

                                # Try to get execution time from error files too
                                for result_file in error_files:
                                    try:
                                        with open(result_file, "r") as f:
                                            result_data = json.load(f)
                                        test_info = result_data.get("test_info", {})
                                        total_execution_time += test_info.get(
                                            "execution_time", 0
                                        )
                                    except Exception:
                                        continue

                            total_tests = success_count + error_count
                            success_rate = (
                                (success_count / total_tests * 100)
                                if total_tests > 0
                                else 0
                            )

                            # Use actual counts instead of potentially incorrect summary data
                            experiment_data = {
                                "date": summary_data.get("start_time", "N/A"),
                                "end_date": summary_data.get("end_time", "N/A"),
                                "total_tests": total_tests,
                                "completed_tests": success_count,
                                "failed_tests": error_count,
                                "success_rate": success_rate,
                                "execution_time": total_execution_time,
                                "directory": str(exp_dir),
                                "experiment_name": exp_dir.name,
                            }

                            # Try to get assistant and question counts from config
                            if config_file.exists():
                                try:
                                    with open(config_file, "r") as f:
                                        config_data = json.load(f)

                                    setup = config_data.get("experiment_setup", {})
                                    experiment_data["num_assistants"] = len(
                                        setup.get("assistant_ids", [])
                                    )
                                    experiment_data["num_questions"] = len(
                                        setup.get("questions", [])
                                    )
                                except Exception:
                                    # Fallback: try to infer from actual result files
                                    experiment_data["num_assistants"] = 0
                                    experiment_data["num_questions"] = 0

                                    # Try to extract from result files
                                    all_result_files = []
                                    if success_dir.exists():
                                        all_result_files.extend(
                                            success_dir.glob("*.json")
                                        )
                                    if error_dir.exists():
                                        all_result_files.extend(
                                            error_dir.glob("*.json")
                                        )

                                    assistants = set()
                                    questions = set()

                                    for result_file in all_result_files:
                                        try:
                                            with open(result_file, "r") as f:
                                                result_data = json.load(f)
                                            test_info = result_data.get("test_info", {})
                                            if test_info.get("assistant_id"):
                                                assistants.add(
                                                    test_info["assistant_id"]
                                                )
                                            if test_info.get("question"):
                                                questions.add(test_info["question"])
                                        except Exception:
                                            continue

                                    experiment_data["num_assistants"] = len(assistants)
                                    experiment_data["num_questions"] = len(questions)
                            else:
                                # No config file, try to infer from result files
                                all_result_files = []
                                if success_dir.exists():
                                    all_result_files.extend(success_dir.glob("*.json"))
                                if error_dir.exists():
                                    all_result_files.extend(error_dir.glob("*.json"))

                                assistants = set()
                                questions = set()

                                for result_file in all_result_files:
                                    try:
                                        with open(result_file, "r") as f:
                                            result_data = json.load(f)
                                        test_info = result_data.get("test_info", {})
                                        if test_info.get("assistant_id"):
                                            assistants.add(test_info["assistant_id"])
                                        if test_info.get("question"):
                                            questions.add(test_info["question"])
                                    except Exception:
                                        continue

                                experiment_data["num_assistants"] = len(assistants)
                                experiment_data["num_questions"] = len(questions)

                            history.append(experiment_data)

                        except Exception as e:
                            print(f"Error loading experiment {exp_dir.name}: {e}")
                            continue

            # Sort by date (most recent first)
            history.sort(key=lambda x: x.get("date", ""), reverse=True)

        except Exception as e:
            print(f"Error scanning experiments directory: {e}")

        return history

    @staticmethod
    def save_experiment_to_history(experiment_data: Dict[str, Any]) -> bool:
        """
        Add an experiment to the history.

        Args:
            experiment_data: Dictionary containing experiment information

        Returns:
            bool: True if saved successfully
        """
        try:
            # Load existing history
            history = ConfigManager.load_experiment_history()

            # Add new experiment to the beginning of the list
            history.insert(0, experiment_data)

            # Keep only the last 100 experiments to prevent file from growing too large
            history = history[:100]

            # Save updated history
            history_file = Path(ConfigManager.EXPERIMENT_HISTORY_FILE)
            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving experiment to history: {e}")
            return False

    @staticmethod
    def clear_experiment_history() -> bool:
        """Clear all experiment history."""
        try:
            history_file = Path(ConfigManager.EXPERIMENT_HISTORY_FILE)
            if history_file.exists():
                history_file.unlink()
            return True
        except Exception as e:
            print(f"Error clearing experiment history: {e}")
            return False
