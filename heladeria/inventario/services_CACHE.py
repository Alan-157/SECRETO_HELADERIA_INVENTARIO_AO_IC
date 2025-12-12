"""
Versión SIMPLIFICADA de services.py con control de alertas
USA CACHE - NO requiere modelo ConfiguracionAlertas
"""
from decimal import Decimal
from django.utils import timezone
from .models import Insumo, AlertaInsumo, InsumoLote
from .alertas_config import alertas_activadas  # <-- Importar función del cache

def check_and_create_stock_alerts(insumo=None):
    """
    Verifica niveles de stock y crea alertas si es necesario.
    RESPETA el toggle global de alertas usando cache.
    
    Args:
        insumo: Insumo específico a verificar, o None para todos
    """
    # ⚡ VERIFICAR SI LAS ALERTAS ESTÁN ACTIVAS
    if not alertas_activadas():
        return  # Salir sin crear alertas
    
    # Obtener lista de insumos a verificar
    if insumo:
        insumos = [insumo]
    else:
        insumos = Insumo.objects.all()
    
    for ins in insumos:
        stock_actual = ins.calcular_stock_actual()
        
        # Verificar bajo stock
        if stock_actual <= ins.stock_minimo:
            AlertaInsumo.objects.get_or_create(
                insumo=ins,
                tipo='bajo_stock',
                defaults={
                    'mensaje': f'Stock bajo: {stock_actual} unidades (mínimo: {ins.stock_minimo})',
                    'nivel': 'alto',
                    'is_active': True
                }
            )
        
        # Verificar sobre stock
        if stock_actual >= ins.stock_maximo:
            AlertaInsumo.objects.get_or_create(
                insumo=ins,
                tipo='sobre_stock',
                defaults={
                    'mensaje': f'Sobre stock: {stock_actual} unidades (máximo: {ins.stock_maximo})',
                    'nivel': 'medio',
                    'is_active': True
                }
            )

def check_lote_vencimiento(lote=None):
    """
    Verifica fechas de vencimiento y crea alertas.
    RESPETA el toggle global de alertas.
    
    Args:
        lote: Lote específico a verificar, o None para todos
    """
    # ⚡ VERIFICAR SI LAS ALERTAS ESTÁN ACTIVAS
    if not alertas_activadas():
        return
    
    from datetime import timedelta
    
    if lote:
        lotes = [lote]
    else:
        lotes = InsumoLote.objects.filter(cant_actual__gt=0)
    
    hoy = timezone.now().date()
    
    for lt in lotes:
        if not lt.fecha_vencimiento:
            continue
        
        dias_restantes = (lt.fecha_vencimiento - hoy).days
        
        # Vencido
        if dias_restantes < 0:
            AlertaInsumo.objects.get_or_create(
                insumo=lt.insumo,
                lote=lt,
                tipo='vencido',
                defaults={
                    'mensaje': f'Lote {lt.numero_lote} vencido hace {abs(dias_restantes)} días',
                    'nivel': 'critico',
                    'is_active': True
                }
            )
        # Próximo a vencer (7 días)
        elif dias_restantes <= 7:
            AlertaInsumo.objects.get_or_create(
                insumo=lt.insumo,
                lote=lt,
                tipo='por_vencer',
                defaults={
                    'mensaje': f'Lote {lt.numero_lote} vence en {dias_restantes} días',
                    'nivel': 'alto',
                    'is_active': True
                }
            )

def resolver_alerta(alerta_id):
    """Marca una alerta como resuelta"""
    try:
        alerta = AlertaInsumo.objects.get(pk=alerta_id)
        alerta.is_active = False
        alerta.fecha_resolucion = timezone.now()
        alerta.save()
        return True
    except AlertaInsumo.DoesNotExist:
        return False

def actualizar_alertas_insumo(insumo):
    """
    Actualiza todas las alertas relacionadas a un insumo
    después de cambios en el stock.
    """
    # Resolver alertas que ya no aplican
    stock_actual = insumo.calcular_stock_actual()
    
    # Si el stock está en rango normal, resolver alertas de stock
    if insumo.stock_minimo < stock_actual < insumo.stock_maximo:
        AlertaInsumo.objects.filter(
            insumo=insumo,
            tipo__in=['bajo_stock', 'sobre_stock'],
            is_active=True
        ).update(
            is_active=False,
            fecha_resolucion=timezone.now()
        )
    
    # Crear nuevas alertas si es necesario
    check_and_create_stock_alerts(insumo)
    check_lote_vencimiento()
