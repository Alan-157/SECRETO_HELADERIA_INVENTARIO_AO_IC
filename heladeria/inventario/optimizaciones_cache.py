"""
OPTIMIZACIONES DE CACHE PARA MEJORAR RENDIMIENTO
Agregar este código al inicio de views.py después de los imports
"""
from django.core.cache import cache
from django.db.models import Prefetch

# Función helper para cachear conteos
def get_cached_count(cache_key, queryset, timeout=300):
    """
    Obtiene un conteo desde caché o lo calcula y cachea.
    timeout en segundos (300 = 5 minutos)
    """
    count = cache.get(cache_key)
    if count is None:
        count = queryset.count()
        cache.set(cache_key, count, timeout)
    return count

# Función para invalidar caché cuando se crean/modifican registros
def invalidate_counts_cache():
    """Invalida todos los conteos cacheados"""
    cache.delete_many([
        'count_insumos_activos',
        'count_bodegas_activas', 
        'count_ordenes_pendientes',
        'count_alertas_activas',
        'count_lotes_activos',
    ])


# EJEMPLO DE USO EN DASHBOARD:
# En lugar de:
#   total_insumos = Insumo.objects.filter(is_active=True).count()
# 
# Usar:
#   total_insumos = get_cached_count(
#       'count_insumos_activos',
#       Insumo.objects.filter(is_active=True)
#   )
