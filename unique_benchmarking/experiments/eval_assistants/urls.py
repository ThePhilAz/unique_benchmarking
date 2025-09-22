"""
URL configuration for eval_assistants API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r"experiments", views.ExperimentViewSet)
router.register(r"golden-answers", views.GoldenAnswerViewSet)
router.register(r"responses", views.AssistantResponseViewSet)
router.register(r"configuration", views.ConfigurationViewSet, basename="configuration")

# The API URLs are now determined automatically by the router
urlpatterns = [
    path("api/", include(router.urls)),
]
