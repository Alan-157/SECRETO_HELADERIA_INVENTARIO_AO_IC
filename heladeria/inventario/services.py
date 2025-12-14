"""
Versión SIMPLIFICADA de services.py con control de alertas
USA CACHE - NO requiere modelo ConfiguracionAlertas
"""
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
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
        insumos = Insumo.objects.filter(is_active=True)
    
    for ins in insumos:
        # Calcular stock actual sumando los lotes activos
        stock_actual = ins.lotes.filter(
            is_active=True
        ).aggregate(
            total=Coalesce(Sum('cantidad_actual'), Decimal('0'))
        )['total']
        
        # Verificar SIN STOCK (stock = 0)
        if stock_actual == Decimal('0'):
            # Buscar alerta activa existente o crear nueva
            alerta, created = AlertaInsumo.objects.get_or_create(
                insumo=ins,
                tipo='SIN_STOCK',
                is_active=True,  # Solo buscar alertas activas
                defaults={
                    'mensaje': f'El insumo "{ins.nombre}" no tiene stock disponible',
                }
            )
            if not created:
                # Actualizar mensaje de alerta existente
                alerta.mensaje = f'El insumo "{ins.nombre}" no tiene stock disponible'
                alerta.save(update_fields=['mensaje', 'updated_at'])
                
        # Verificar BAJO STOCK (stock < mínimo pero > 0)
        elif stock_actual < ins.stock_minimo:
            # Buscar alerta activa existente o crear nueva
            alerta, created = AlertaInsumo.objects.get_or_create(
                insumo=ins,
                tipo='BAJO_STOCK',
                is_active=True,  # Solo buscar alertas activas
                defaults={
                    'mensaje': f'Stock bajo: {stock_actual} {ins.unidad_medida.nombre_corto} (mínimo: {ins.stock_minimo})',
                }
            )
            if not created:
                # Actualizar mensaje de alerta existente
                alerta.mensaje = f'Stock bajo: {stock_actual} {ins.unidad_medida.nombre_corto} (mínimo: {ins.stock_minimo})'
                alerta.save(update_fields=['mensaje', 'updated_at'])
                
        # Verificar STOCK EXCESIVO (stock > máximo)
        elif stock_actual > ins.stock_maximo:
            # Buscar alerta activa existente o crear nueva
            alerta, created = AlertaInsumo.objects.get_or_create(
                insumo=ins,
                tipo='STOCK_EXCESIVO',
                is_active=True,  # Solo buscar alertas activas
                defaults={
                    'mensaje': f'Stock excesivo: {stock_actual} {ins.unidad_medida.nombre_corto} (máximo: {ins.stock_maximo})',
                }
            )
            if not created:
                # Actualizar mensaje de alerta existente
                alerta.mensaje = f'Stock excesivo: {stock_actual} {ins.unidad_medida.nombre_corto} (máximo: {ins.stock_maximo})'
                alerta.save(update_fields=['mensaje', 'updated_at'])
                
        else:
            # Stock en rango normal: desactivar alertas de stock existentes
            AlertaInsumo.objects.filter(
                insumo=ins,
                tipo__in=['SIN_STOCK', 'BAJO_STOCK', 'STOCK_EXCESIVO'],
                is_active=True
            ).update(is_active=False)

def check_lote_vencimiento(lote=None):
    """
    Verifica fechas de expiración de lotes y crea alertas.
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
        lotes = InsumoLote.objects.filter(
            is_active=True,
            cantidad_actual__gt=0
        )
    
    hoy = timezone.now().date()
    
    for lt in lotes:
        if not lt.fecha_expiracion:
            continue
        
        dias_restantes = (lt.fecha_expiracion - hoy).days
        
        # Próximo a vencer (dentro de 7 días) o ya vencido
        if dias_restantes <= 7:
            if dias_restantes < 0:
                mensaje = f'Lote #{lt.id} de "{lt.insumo.nombre}" venció hace {abs(dias_restantes)} días'
            else:
                mensaje = f'Lote #{lt.id} de "{lt.insumo.nombre}" vence en {dias_restantes} días'
            
            # Buscar o crear alerta activa, actualizando el mensaje si ya existe
            alerta, created = AlertaInsumo.objects.get_or_create(
                insumo=lt.insumo,
                tipo='VENCIMIENTO_PROXIMO',
                is_active=True,  # Solo buscar alertas activas
                defaults={'mensaje': mensaje}
            )
            if not created:
                # Actualizar mensaje de alerta existente
                alerta.mensaje = mensaje
                alerta.save(update_fields=['mensaje', 'updated_at'])

def resolver_alerta(alerta_id):
    """Marca una alerta como resuelta (inactiva)"""
    try:
        alerta = AlertaInsumo.objects.get(pk=alerta_id)
        alerta.is_active = False
        alerta.save()
        return True
    except AlertaInsumo.DoesNotExist:
        return False

def actualizar_alertas_insumo(insumo):
    """
    Actualiza todas las alertas relacionadas a un insumo
    después de cambios en el stock.
    """
    if not alertas_activadas():
        return
    
    # Crear nuevas alertas si es necesario
    check_and_create_stock_alerts(insumo)
    
    # Verificar vencimientos de lotes de este insumo
    for lote in insumo.lotes.filter(is_active=True, cantidad_actual__gt=0):
        check_lote_vencimiento(lote)
