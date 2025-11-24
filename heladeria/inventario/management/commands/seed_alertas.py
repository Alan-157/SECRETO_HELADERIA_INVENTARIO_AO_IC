# inventario/management/commands/seed_alertas.py

from django.core.management.base import BaseCommand
from inventario.models import AlertaInsumo, Insumo

class Command(BaseCommand):
    help = "Crea alertas de prueba para insumos existentes."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de alertas de prueba..."))

        # Lista de alertas de prueba
        alertas_data = [
            {"insumo_nombre": "Leche Entera", "mensaje": "¡Atención! Stock bajo detectado en leche."},
            {"insumo_nombre": "Pulpa de Frutilla", "mensaje": "¡Urgente! Frutilla en nivel crítico."},
            # Puedes agregar más alertas aquí
        ]

        alertas_creadas = 0

        for data in alertas_data:
            nombre = data["insumo_nombre"]
            mensaje = data["mensaje"]

            try:
                insumo = Insumo.objects.get(nombre=nombre)

                alerta, creada = AlertaInsumo.objects.get_or_create(
                    insumo=insumo,
                    defaults={"mensaje": mensaje}
                )

                if creada:
                    self.stdout.write(self.style.SUCCESS(
                        f"Alerta creada para '{insumo.nombre}'."
                    ))
                    alertas_creadas += 1
                else:
                    self.stdout.write(self.style.WARNING(
                        f"Alerta para '{insumo.nombre}' ya existía."
                    ))

            except Insumo.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"ERROR: Insumo '{nombre}' no existe. Ejecuta seed_insumos primero."
                ))

        self.stdout.write(self.style.SUCCESS(
            f"\nCarga de alertas finalizada. {alertas_creadas} nuevas alertas creadas."
        ))
