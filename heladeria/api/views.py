from django.http import JsonResponse
from rest_framework import viewsets
from inventario.models import Categoria, Insumo
from .serializers import InsumoSerializer,CategoriaSerializer

def health(request):
    """
    Endpoint de prueba para verificar que la API está viva.
    """
    return JsonResponse({"status": "ok"})

def info(request):
    """
    Endpoint de información del proyecto para la actividad de la clase.
    """
    data = {
        "proyecto": "Secreto Heladería Inventario 33",
        "version": "1.0",
        "autor": "Alonzo Oviedo e Isaac Catalan",
    }
    return JsonResponse(data)

class InsumoViewSet(viewsets.ModelViewSet):
    queryset = Insumo.objects.all()
    serializer_class = InsumoSerializer

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

