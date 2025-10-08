from django.core.management.base import BaseCommand
from inventario.models import Bodega, Ubicacion

class Command(BaseCommand):
    help = "Crea o actualiza las bodegas y sus ubicaciones de prueba."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de bodegas y ubicaciones..."))

        # Definimos los datos de las bodegas y sus direcciones en un solo lugar
        data = {
            "Bodega Principal": {
                "direccion": "Gabriel Gonzalez Videla 2777, La Serena",
                "ubicaciones": ["Área General", "Cámara Fría"],
            },
            "Bodega Secundaria": {
                "direccion": "Pasaje Falso 1234, Coquimbo",
                "ubicaciones": ["Área General"],
            },
            "Bodega Frutas": {
                "direccion": "Avenida del Mar 5000, La Serena",
                "ubicaciones": ["Área General", "Frutas Congeladas"],
            },
        }

        bodegas_creadas = 0
        ubicaciones_creadas = 0

        for nombre_bodega, info in data.items():
            # 1) Crear/obtener Bodega con 'nombre' y 'direccion'
            bodega, bodega_creada = Bodega.objects.get_or_create(
                nombre=nombre_bodega,
                defaults={"direccion": info["direccion"]},
            )
            if bodega_creada:
                bodegas_creadas += 1
                self.stdout.write(self.style.SUCCESS(f"Bodega creada: '{bodega.nombre}'"))
            else:
                # Si la bodega ya existía, puedes opcionalmente sincronizar dirección
                if bodega.direccion != info["direccion"]:
                    bodega.direccion = info["direccion"]
                    bodega.save(update_fields=["direccion"])
                self.stdout.write(self.style.WARNING(f"Bodega '{bodega.nombre}' ya existía."))

            # 2) Crear ubicaciones por bodega: clave compuesta (bodega, nombre)
            for nombre_ubic in info["ubicaciones"]:
                ubic, ubi_creada = Ubicacion.objects.get_or_create(
                    bodega=bodega,
                    nombre=nombre_ubic,
                    defaults={"tipo": "Almacenamiento"},
                )
                if ubi_creada:
                    ubicaciones_creadas += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  -> Ubicación '{nombre_ubic}' creada en '{bodega.nombre}'"
                    ))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCarga finalizada. Se crearon {bodegas_creadas} bodegas y {ubicaciones_creadas} ubicaciones nuevas."
            )
        )