from rest_framework import routers
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

from .views import health, info, InsumoViewSet, CategoriaViewSet

router = routers.DefaultRouter()
router.register(r'insumos',InsumoViewSet)
router.register(r'categoria',CategoriaViewSet)

urlpatterns = [
    path("health/", health, name="api-health"),
    path("info/", info, name="api-info"),
    path('api/login/', obtain_auth_token, name='api_login'),

    path('',include(router.urls)),
]
