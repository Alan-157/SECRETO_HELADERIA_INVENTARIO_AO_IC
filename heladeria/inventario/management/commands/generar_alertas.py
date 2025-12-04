# heladeria/inventario/management/commands/generar_alertas.py

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from inventario.models import Insumo, InsumoLote, AlertaInsumo

class Command(BaseCommand):
    help = 'Verifica el inventario y genera/actualiza las alertas.'

    def handle(self, *args, **options):
        # Configuración: Días de anticipación para la alerta de vencimiento
        DIAS_AVISO_VENCIMIENTO = 30
        
        self.stdout.write(self.style.SUCCESS("--- Iniciando Chequeo de Inventario ---"))
        
        # Procesar alertas de stock (mínimo, máximo, cero)
        self._check_stock_levels()

        # Procesar alertas de vencimiento de lotes
        self._check_lot_expirations(DIAS_AVISO_VENCIMIENTO)

        self.stdout.write(self.style.SUCCESS("--- Chequeo de Inventario Finalizado ---"))

    def _create_or_update_alert(self, insumo, tipo, mensaje):
        """Crea o actualiza una alerta existente para un tipo dado de insumo."""
        AlertaInsumo.objects.update_or_create(
            insumo=insumo,
            tipo=tipo,
            defaults={'mensaje': mensaje, 'fecha': timezone.now().date()}
        )
        # Opcional: Agregar logs o notificaciones

    def _check_stock_levels(self):
        """Revisa stock contra mínimo/máximo/cero y limpia alertas cuando el stock es normal."""
        for insumo in Insumo.objects.filter(is_active=True):
            stock_actual = insumo.stock_actual
            
            # Sin Stock (Máxima prioridad)
            if stock_actual == Decimal('0.00'):
                mensaje = "El insumo está AGOTADO. Stock actual: 0."
                self._create_or_update_alert(insumo, "SIN_STOCK", mensaje)
                continue 

            # Stock Bajo (Si no está en cero)
            if stock_actual <= insumo.stock_minimo:
                mensaje = f"Stock bajo. Actual: {stock_actual}, Mínimo: {insumo.stock_minimo}."
                self._create_or_update_alert(insumo, "STOCK_BAJO", mensaje)
                # Borra alerta de SIN_STOCK si existía, ya que el stock no es cero
                AlertaInsumo.objects.filter(insumo=insumo, tipo="SIN_STOCK").delete()
                
            # Stock Excesivo
            elif stock_actual > insumo.stock_maximo:
                mensaje = f"Stock alto. Actual: {stock_actual}, Máximo: {insumo.stock_maximo}."
                self._create_or_update_alert(insumo, "STOCK_ALTO", mensaje)
                
            # Stock Normal: Eliminar alertas de stock si las había
            else:
                AlertaInsumo.objects.filter(insumo=insumo).filter(
                    Q(tipo="SIN_STOCK") | Q(tipo="STOCK_BAJO") | Q(tipo="STOCK_ALTO")
                ).delete()

    def _check_lot_expirations(self, dias_aviso):
        """Revisa los lotes que están por vencer o ya vencieron."""
        fecha_limite = timezone.now().date() + timedelta(days=dias_aviso)
        
        # Filtra insumos que tienen lotes activos con stock y que vencen pronto
        insumos_a_alertar = Insumo.objects.filter(
            is_active=True,
            lotes__is_active=True,
            lotes__cantidad_actual__gt=Decimal('0.00'),
            lotes__fecha_expiracion__lte=fecha_limite
        ).distinct()

        # Genera una alerta de vencimiento por cada insumo afectado
        for insumo in insumos_a_alertar:
            lotes_exp = insumo.lotes.filter(
                is_active=True,
                cantidad_actual__gt=Decimal('0.00'),
                fecha_expiracion__lte=fecha_limite
            ).order_by('fecha_expiracion')
            
            # Construye un mensaje detallado con los lotes a vencer
            mensaje = f"Se detectaron {lotes_exp.count()} lotes próximos a vencer o vencidos."
            for i, lote in enumerate(lotes_exp[:5]): # Muestra el detalle de los primeros 5 lotes
                dias_restantes = (lote.fecha_expiracion - timezone.now().date()).days
                estado = "VENCIDO" if dias_restantes < 0 else f"VENCE en {dias_restantes} días"
                mensaje += f"\n- Lote {lote.id} ({lote.cantidad_actual} {insumo.unidad_medida.nombre_corto}), Vencimiento: {lote.fecha_expiracion}, Estado: {estado}"
            
            self._create_or_update_alert(insumo, "PROXIMO_VENCIMIENTO", mensaje)
            
        # Limpia alertas de vencimiento para insumos que ya no tienen lotes en el rango
        insumos_sin_alerta = Insumo.objects.filter(is_active=True).exclude(
            lotes__is_active=True,
            lotes__cantidad_actual__gt=Decimal('0.00'),
            lotes__fecha_expiracion__lte=fecha_limite
        ).distinct()
        
        AlertaInsumo.objects.filter(insumo__in=insumos_sin_alerta, tipo="PROXIMO_VENCIMIENTO").delete()