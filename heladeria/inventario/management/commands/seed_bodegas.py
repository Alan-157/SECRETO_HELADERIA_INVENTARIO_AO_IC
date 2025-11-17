from django.core.management.base import BaseCommand
from inventario.models import Bodega, Ubicacion

class Command(BaseCommand):
    """
    Crea bodegas de prueba y una ubicación por defecto para cada una,
    siguiendo el modelo donde Bodega tiene la dirección.
    """
    help = "Crea bodegas de prueba y una ubicación por defecto para cada una."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de bodegas y ubicaciones..."))

        bodegas_data = [
            {"nombre": "Bodega Principal", "direccion": "Gabriel Gonzalez Videla 2777, La Serena","descripcion":"bodega1"},
            {"nombre": "Bodega Secundaria", "direccion": "Pasaje Falso 1234, Coquimbo","descripcion":"bodeg2"},
            {"nombre": "Bodega Frutas", "direccion": "Avenida del Mar 5000, La Serena","descripcion":"bodega3"},
        ]

        bodegas_creadas = 0
        ubicaciones_creadas = 0

        for data in bodegas_data:
            # 1. Creamos o obtenemos la BODEGA usando su nombre y dirección.
            bodega, fue_creada_bodega = Bodega.objects.get_or_create(
                nombre=data["nombre"],
                defaults={'direccion': data["direccion"]}
            )

            if fue_creada_bodega:
                self.stdout.write(self.style.SUCCESS(f"Bodega creada: '{bodega.nombre}'"))
                bodegas_creadas += 1

                # 2. Si la bodega es nueva, creamos una UBICACIÓN por defecto dentro de ella.
                ubicacion, fue_creada_ubicacion = Ubicacion.objects.get_or_create(
                    nombre="Área General",
                    bodega=bodega,
                    defaults={'tipo': 'Almacenamiento'}
                )
                if fue_creada_ubicacion:
                    self.stdout.write(self.style.SUCCESS(f"  -> Ubicación por defecto 'Área General' creada para {bodega.nombre}"))
                    ubicaciones_creadas += 1
            else:
                self.stdout.write(self.style.WARNING(f"Bodega '{data['nombre']}' ya existía."))