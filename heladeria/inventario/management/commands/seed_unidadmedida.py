from django.core.management.base import BaseCommand
from inventario.models import UnidadMedida

class Command(BaseCommand):
    help = "Crea unidades de medida iniciales para el sistema de inventario."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de Unidades de Medida..."))

        # Las unidades de medida base que necesita el sistema
        unidades_data = {
            "Litro": {"nombre_corto": "LT", "nombre_largo": "Litro"},
            "Kilo": {"nombre_corto": "KG", "nombre_largo": "Kilo"},
            "Unidad": {"nombre_corto": "UN", "nombre_largo": "Unidad"},
        }
        
        unidades_creadas = 0
        for largo, data in unidades_data.items():
            unidad, creado = UnidadMedida.objects.get_or_create(
                nombre_largo=largo,
                defaults=data
            )
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Unidad '{largo}' ({data['nombre_corto']}) creada."))
                unidades_creadas += 1
        
        if unidades_creadas > 0:
            self.stdout.write(self.style.SUCCESS(f"\n¡Se crearon {unidades_creadas} nuevas Unidades de Medida!"))
        else:
            self.stdout.write(self.style.WARNING("\nNo se crearon nuevas unidades, todas ya existían."))

        self.stdout.write(self.style.SUCCESS("Carga de Unidades de Medida finalizada."))