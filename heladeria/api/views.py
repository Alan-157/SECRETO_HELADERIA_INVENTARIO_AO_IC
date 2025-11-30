from django.http import JsonResponse, Http404
from rest_framework import viewsets, permissions
from inventario.models import Insumo, Categoria
from .serializers import InsumoSerializer, CategoriaSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

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
    permission_classes = [IsAuthenticated, permissions.DjangoModelPermissions]
    
    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            #Mensaje personalizado para IDs no válidos
            raise NotFound ("Categoria no encontrada")

    