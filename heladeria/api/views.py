from django.http import JsonResponse

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
