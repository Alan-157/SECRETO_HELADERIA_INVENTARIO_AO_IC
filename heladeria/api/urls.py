from django.urls import path
from .views import health, info, InsumoViewSet, CategoriaViewSet
from rest_framework import routers
from django.urls import include

router = routers.DefaultRouter()
router.register(r'insumos', InsumoViewSet)
router.register(r'categorias', CategoriaViewSet)

urlpatterns = [
    path("health/", health, name="api-health"),
    path("info/", info, name="api-info"),
    path("", include(router.urls)),
]
