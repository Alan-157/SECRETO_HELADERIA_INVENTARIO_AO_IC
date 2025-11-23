from rest_framework import routers
from django.urls import path, include
from .views import health, info, InsumoViewSet, CategoriaViewSet

router = routers.DefaultRouter()
router.register(r'insumos',InsumoViewSet)
router.register(r'categoria',CategoriaViewSet)

urlpatterns = [
    path("health/", health, name="api-health"),
    path("info/", info, name="api-info"),
    path('',include(router.urls)),
]
