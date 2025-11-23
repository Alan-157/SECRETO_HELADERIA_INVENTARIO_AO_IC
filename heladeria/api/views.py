from django.http import JsonResponse
from rest_framework import viewsets
from inventario.models import Insumo, Categoria
from .serializers import InsumoSerializer, CategoriaSerializer

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
        "proyecto": "Secreto Heladería Inventario",
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
    