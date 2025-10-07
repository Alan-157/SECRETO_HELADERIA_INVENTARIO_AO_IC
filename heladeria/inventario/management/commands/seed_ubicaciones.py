from django.core.management.base import BaseCommand
from inventario.models import Bodega, Ubicacion

class Command(BaseCommand):
    help = "Crea o actualiza las bodegas y sus ubicaciones de prueba."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de bodegas y ubicaciones..."))

        # Definimos los datos de las bodegas y sus direcciones en un solo lugar
        bodegas_data = {
            "Bodega Principal": "Gabriel Gonzalez Videla 2777, La Serena",
            "Bodega Secundaria": "Pasaje Falso 1234, Coquimbo",
            "Bodega Frutas": "Avenida del Mar 5000, La Serena"
        }

        bodegas_creadas = 0
        ubicaciones_creadas = 0

        for nombre_bodega, direccion_bodega in bodegas_data.items():
            # 1. Usamos get_or_create para la Ubicacion.
            # Esto la crea si no existe, o la obtiene si ya existe.
            ubicacion, fue_creada_ubicacion = Ubicacion.objects.get_or_create(
                direccion=direccion_bodega,
                defaults={'nombre': f"Ubicación para {nombre_bodega}"} # Añadimos un nombre descriptivo
            )

            if fue_creada_ubicacion:
                self.stdout.write(self.style.SUCCESS(f"Ubicación creada: '{direccion_bodega}'"))
                ubicaciones_creadas += 1

            # 2. Ahora, con la ubicación asegurada, creamos la Bodega.
            bodega, fue_creada_bodega = Bodega.objects.get_or_create(
                nombre=nombre_bodega,
                defaults={'ubicacion': ubicacion}
            )

            if fue_creada_bodega:
                self.stdout.write(self.style.SUCCESS(f"  -> Bodega creada: '{nombre_bodega}'"))
                bodegas_creadas += 1
            else:
                self.stdout.write(self.style.WARNING(f"Bodega '{nombre_bodega}' ya existía."))

        self.stdout.write(self.style.SUCCESS(f"\nCarga finalizada. Se crearon {bodegas_creadas} bodegas y {ubicaciones_creadas} ubicaciones nuevas."))