# heladeria/inventario/services.py

from decimal import Decimal
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from inventario.models import Insumo, AlertaInsumo 

# Tipos de alerta que son mutuamente excluyentes (Nivel de Stock)
STOCK_ALERT_TYPES = ["SIN_STOCK", "BAJO_STOCK", "STOCK_EXCESIVO"]

def check_and_create_stock_alerts(insumo: Insumo):
    """
    Verifica el stock actual de un Insumo y crea/actualiza una alerta de 
    SIN_STOCK, BAJO_STOCK o STOCK_EXCESIVO si es necesario.
    """
    
    # 1. Calcular stock actual
    stock_data = insumo.lotes.filter(is_active=True).aggregate(
        stock_actual=Coalesce(
            Sum('cantidad_actual', filter=Q(cantidad_actual__gt=Decimal("0.00"))), 
            Decimal("0.00"), 
            output_field=DecimalField()
        )
    )
    stock_actual = stock_data['stock_actual']
    
    # Alias para la unidad de medida
    unidad_corto = insumo.unidad_medida.nombre_corto
    
    tipo_alerta = None
    mensaje = None

    # --- 2. EVALUACIÓN DE CONDICIONES (Prioridad: Exceso > Faltante Crítico) ---
    
    if stock_actual > insumo.stock_maximo:
        # Stock Excesivo
        tipo_alerta = "STOCK_EXCESIVO"
        stock_str = f"{stock_actual:.2f} {unidad_corto}"
        max_str = f"{insumo.stock_maximo:.2f} {unidad_corto}"
        mensaje = f"Stock excesivo. Actual: {stock_str}. Máximo permitido: {max_str}."

    elif stock_actual <= Decimal("0.00"):
        # Sin Stock (Stock = 0)
        tipo_alerta = "SIN_STOCK"
        mensaje = f"¡AGOTADO! El stock actual es 0 {unidad_corto}. Mínimo requerido: {insumo.stock_minimo:.2f} {unidad_corto}."
    
    elif stock_actual < insumo.stock_minimo:
        # Bajo Stock (Stock > 0 y Stock < Mínimo)
        tipo_alerta = "BAJO_STOCK"
        stock_str = f"{stock_actual:.2f} {unidad_corto}"
        min_str = f"{insumo.stock_minimo:.2f} {unidad_corto}"
        mensaje = f"Stock bajo. Actual: {stock_str}. Mínimo requerido: {min_str}."
    
    # --- 3. PROCESAMIENTO DE ALERTAS (Desactivación Total + Creación/Reactivación) ---
    
    # Desactivar TODAS las alertas de nivel de stock activas para este insumo.
    alertas_a_desactivar = AlertaInsumo.objects.filter(
        insumo=insumo,
        tipo__in=STOCK_ALERT_TYPES,
        is_active=True
    )
    alertas_a_desactivar.update(is_active=False)

    if tipo_alerta:
        # Crea o reactiva la alerta con el tipo y mensaje correctos.
        # update_or_create es más seguro para asegurar la reactivación (is_active=True).
        AlertaInsumo.objects.update_or_create(
            insumo=insumo,
            tipo=tipo_alerta,
            defaults={
                'mensaje': mensaje,
                'is_active': True, # Se reactiva la alerta.
            }
        )
        return True 
    else:
        # Si el stock está óptimo, todas las alertas de stock ya fueron desactivadas arriba.
        return False