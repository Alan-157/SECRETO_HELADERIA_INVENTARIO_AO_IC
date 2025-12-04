# heladeria/inventario/management/commands/check_stock_alerts.py (Contenido Actualizado)

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Q
from inventario.models import Insumo, AlertaInsumo, InsumoLote
from inventario.services import check_and_create_stock_alerts # <--- Función renombrada
from datetime import date, timedelta

class Command(BaseCommand):
    help = "Verifica el stock de insumos contra los límites (mínimo/máximo) y los lotes próximos a vencer, generando alertas."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando verificación de alertas automáticas..."))
        
        # 1. Alertas de Stock (Sin Stock, Bajo Stock, Excesivo)
        self.check_stock_level_alerts() # <--- Método renombrado
        
        # 2. Alertas de Vencimiento
        self.check_expiration_alerts()

        self.stdout.write(self.style.SUCCESS("\nVerificación de alertas finalizada."))

    def check_stock_level_alerts(self): 
        """Genera alertas de Sin Stock, Bajo Stock o Excesivo, reutilizando el servicio."""
        alertas_activas = 0
        
        # Obtener insumos activos
        insumos_a_revisar = Insumo.objects.filter(is_active=True).select_related('unidad_medida')
        
        for insumo in insumos_a_revisar:
            # check_and_create_stock_alerts ahora maneja las tres condiciones de stock.
            if check_and_create_stock_alerts(insumo):
                alertas_activas += 1

        
        self.stdout.write(self.style.SUCCESS(f"-> Verificación de Stock: {alertas_activas} insumos con alerta activa (Sin Stock, Bajo Stock o Excesivo)."))

    def check_expiration_alerts(self):
        """Genera alertas para lotes próximos a vencer (14 días)."""
        alertas_creadas = 0
        hoy = date.today()
        dias_proximos_a_vencer = 14
        limite = hoy + timedelta(days=dias_proximos_a_vencer) 

        # Encontrar insumos con lotes activos que expiran pronto
        insumos_con_lotes_proximos = (
            Insumo.objects.filter(
                is_active=True,
                lotes__is_active=True,
                lotes__cantidad_actual__gt=Decimal("0.00"),
                lotes__fecha_expiracion__gte=hoy,
                lotes__fecha_expiracion__lte=limite,
            )
            .distinct()
        )

        for insumo in insumos_con_lotes_proximos:
            # Crea la alerta si no existe una alerta 'VENCIMIENTO_PROXIMO' activa para este insumo.
            alerta, creada = AlertaInsumo.objects.get_or_create(
                insumo=insumo,
                tipo="VENCIMIENTO_PROXIMO",
                is_active=True,
                defaults={
                    'mensaje': f"Uno o más lotes de {insumo.nombre} vencerán en los próximos {dias_proximos_a_vencer} días."
                }
            )
            
            if creada:
                self.stdout.write(self.style.WARNING(f"Alerta VENCIMIENTO_PROXIMO creada para '{insumo.nombre}'."))
                alertas_creadas += 1

        self.stdout.write(self.style.SUCCESS(f"-> Verificación de Vencimiento: {alertas_creadas} alertas nuevas."))