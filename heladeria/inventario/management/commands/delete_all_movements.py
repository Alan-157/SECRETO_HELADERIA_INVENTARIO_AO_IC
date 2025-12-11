from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import Entrada, Salida, InsumoLote
from django.db import connection

class Command(BaseCommand):
    help = 'Elimina todos los registros de Entradas, Salidas e InsumoLotes.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('⚠️ Iniciando la ELIMINACIÓN de datos masivos (Entradas, Salidas y Lotes)...'))

        try:
            with transaction.atomic():
                
                # 1. Eliminar Salidas
                count_salidas = Salida.objects.all().count()
                Salida.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'   ✅ Eliminadas {count_salidas} filas de Salida.'))

                # 2. Eliminar Entradas
                count_entradas = Entrada.objects.all().count()
                Entrada.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'   ✅ Eliminadas {count_entradas} filas de Entrada.'))

                # 3. Eliminar InsumoLote (Deben eliminarse después de Entradas/Salidas)
                count_lotes = InsumoLote.objects.all().count()
                InsumoLote.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'   ✅ Eliminados {count_lotes} registros de InsumoLote.'))

            self.stdout.write(self.style.SUCCESS('\n🎉 Eliminación completada. Las tablas de movimientos están limpias.'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error crítico durante la eliminación: {e}'))