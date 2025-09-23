"""
API client for communicating with Django backend
"""

import requests
from typing import Dict, Any


class APIClient:
    """Client for interacting with the Django REST API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json() if response.content else {},
                "status_code": response.status_code,
            }
        except requests.exceptions.RequestException as e:
            error_data = {
                "success": False,
                "error": str(e),
                "status_code": getattr(e.response, "status_code", None)
                if hasattr(e, "response")
                else None,
            }

            # Try to get error details from response body
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data["error_details"] = e.response.json()
                except Exception:
                    error_data["error_details"] = e.response.text

            return error_data

    def get_configuration_status(self) -> Dict[str, Any]:
        """Check if system configuration is complete"""
        return self._make_request("GET", "/api/configuration/status/")

    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self._make_request("GET", "/api/configuration/")

    def save_configuration(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save configuration data"""
        return self._make_request("POST", "/api/configuration/", json=config_data)

    def initialize_from_env(self) -> Dict[str, Any]:
        """Initialize configuration from environment file"""
        return self._make_request("POST", "/api/configuration/initialize_from_env/")

    def get_experiments(self, **params) -> Dict[str, Any]:
        """Get list of experiments"""
        return self._make_request("GET", "/api/experiments/", params=params)

    def create_and_run_experiment(
        self, experiment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create and run a new experiment"""
        return self._make_request(
            "POST", "/api/experiments/create_and_run/", json=experiment_data
        )

    def get_experiment_stats(self, experiment_id: str) -> Dict[str, Any]:
        """Get experiment statistics"""
        return self._make_request("GET", f"/api/experiments/{experiment_id}/stats/")

    def get_experiment_details(self, experiment_id: str) -> Dict[str, Any]:
        """Get detailed experiment information"""
        return self._make_request("GET", f"/api/experiments/{experiment_id}/")

    def get_experiment_responses(self, experiment_id: str, **params) -> Dict[str, Any]:
        """Get responses for a specific experiment"""
        params["experiment_id"] = experiment_id
        params["page_size"] = 1000  # Get all responses, not just first page
        return self._make_request("GET", "/api/responses/", params=params)

    def get_experiment_progress(self, experiment_id: str) -> Dict[str, Any]:
        """Get experiment progress information"""
        return self._make_request("GET", f"/api/experiments/{experiment_id}/progress/")

    def run_existing_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """Run an existing experiment"""
        return self._make_request("POST", f"/api/experiments/{experiment_id}/run/")

    def get_golden_answers(self, **params) -> Dict[str, Any]:
        """Get golden answers"""
        return self._make_request("GET", "/api/golden-answers/", params=params)


# Singleton API client instance
# Note: Temporarily disabled caching for development
# @st.cache_resource
def get_api_client() -> APIClient:
    """Get cached API client instance"""
    return APIClient()


def clear_api_client_cache():
    """Clear the cached API client instance (no-op when caching disabled)"""
    pass  # get_api_client.clear()
