from django.urls import path
from .views import health, info

urlpatterns = [
    path("health/", health, name="api-health"),
    path("info/", info, name="api-info"),
]
