"""
Sistema de configuración de alertas usando cache de Django
NO requiere modificar models.py ni migraciones
"""
from django.core.cache import cache
from django.conf import settings

# Clave para el cache
ALERTAS_CONFIG_KEY = 'sistema_alertas_activas'
ALERTAS_DEFAULT = True  # Por defecto las alertas están activas

def alertas_activadas():
    """
    Verifica si el sistema de alertas está activo
    Usa Django cache para persistir la configuración
    """
    estado = cache.get(ALERTAS_CONFIG_KEY)
    if estado is None:
        # Primera vez, usar valor por defecto
        cache.set(ALERTAS_CONFIG_KEY, ALERTAS_DEFAULT, timeout=None)
        return ALERTAS_DEFAULT
    return estado

def activar_alertas():
    """Activa el sistema de alertas"""
    cache.set(ALERTAS_CONFIG_KEY, True, timeout=None)
    return True

def desactivar_alertas():
    """Desactiva el sistema de alertas"""
    cache.set(ALERTAS_CONFIG_KEY, False, timeout=None)
    return False

def toggle_alertas():
    """Alterna el estado de las alertas"""
    estado_actual = alertas_activadas()
    nuevo_estado = not estado_actual
    cache.set(ALERTAS_CONFIG_KEY, nuevo_estado, timeout=None)
    return nuevo_estado

def get_estado_alertas():
    """
    Obtiene información completa del estado de alertas
    """
    from .models import AlertaInsumo
    
    estado = alertas_activadas()
    total = AlertaInsumo.objects.count()
    activas = AlertaInsumo.objects.filter(is_active=True).count()
    
    return {
        'alertas_activas': estado,
        'total_alertas': total,
        'alertas_pendientes': activas,
        'alertas_resueltas': total - activas,
    }
