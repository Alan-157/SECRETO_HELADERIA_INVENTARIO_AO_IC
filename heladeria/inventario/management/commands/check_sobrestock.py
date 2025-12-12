from django.core.management.base import BaseCommand
from django.db.models import Sum, DecimalField, F, Q
from django.db.models.functions import Coalesce
from inventario.models import Insumo, InsumoLote


class Command(BaseCommand):
    help = "Verifica y reporta insumos en sobrestock (stock actual > stock máximo)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Intenta corregir el sobrestock eliminando lotes más antiguos'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== VERIFICANDO SOBRESTOCK ===\n"))

        # Obtener insumos con sobrestock
        insumos_sobrestock = (
            Insumo.objects
            .annotate(
                stock_actual=Coalesce(
                    Sum(
                        'lotes__cantidad_actual',
                        filter=Q(lotes__is_active=True)
                    ),
                    0,
                    output_field=DecimalField()
                )
            )
            .filter(stock_actual__gt=F('stock_maximo'))
            .order_by('-stock_actual')
        )

        if not insumos_sobrestock.exists():
            self.stdout.write(self.style.SUCCESS("✓ No hay insumos en sobrestock. ¡Perfecto!\n"))
            return

        self.stdout.write(self.style.WARNING(f"⚠ Se encontraron {insumos_sobrestock.count()} insumos en sobrestock:\n"))

        total_exceso = 0
        for insumo in insumos_sobrestock:
            exceso = insumo.stock_actual - insumo.stock_maximo
            total_exceso += exceso
            self.stdout.write(
                f"  • {insumo.nombre}:\n"
                f"    - Stock actual: {insumo.stock_actual:.2f}\n"
                f"    - Stock máximo: {insumo.stock_maximo:.2f}\n"
                f"    - EXCESO: {exceso:.2f}\n"
            )

        self.stdout.write(self.style.WARNING(f"\n📊 TOTAL DE EXCESO: {total_exceso:.2f}\n"))

        if options['fix']:
            self.stdout.write(self.style.NOTICE("\n🔧 Intentando corregir el sobrestock...\n"))
            self._fix_sobrestock(insumos_sobrestock)
        else:
            self.stdout.write(
                self.style.NOTICE(
                    "💡 Para intentar corregir automáticamente, ejecuta: "
                    "python manage.py check_sobrestock --fix\n"
                )
            )

    def _fix_sobrestock(self, insumos_sobrestock):
        """
        Intenta corregir el sobrestock reduciendo la cantidad_actual de lotes antiguos
        """
        for insumo in insumos_sobrestock:
            # Calcular exceso
            exceso = insumo.stock_actual - insumo.stock_maximo

            # Obtener lotes activos, ordenados por fecha_ingreso (más antiguos primero)
            lotes = InsumoLote.objects.filter(
                insumo=insumo,
                is_active=True
            ).order_by('fecha_ingreso')

            reduccion_realizada = 0

            for lote in lotes:
                if exceso <= 0:
                    break

                # Reducir la cantidad_actual del lote
                reduccion = min(lote.cantidad_actual, exceso)
                lote.cantidad_actual -= reduccion
                lote.save(update_fields=['cantidad_actual'])

                reduccion_realizada += reduccion
                exceso -= reduccion

                self.stdout.write(
                    f"  ✓ Lote #{lote.id} ({insumo.nombre}): "
                    f"reducido en {reduccion:.2f} "
                    f"(nuevo stock: {lote.cantidad_actual:.2f})"
                )

            if reduccion_realizada > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✓ {insumo.nombre}: "
                        f"sobrestock corregido en {reduccion_realizada:.2f}\n"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"\n✗ {insumo.nombre}: "
                        f"no se pudo corregir (insuficiente stock en lotes)\n"
                    )
                )
