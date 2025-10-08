# En el archivo: inventario/management/commands/seed_alertas.py

from django.core.management.base import BaseCommand
from inventario.models import AlertaInsumo, Insumo

class Command(BaseCommand):
    help = "Crea alertas de prueba para insumos existentes."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de alertas de prueba..."))

        # Lista de alertas que queremos crear
        alertas_data = [
            {"insumo_nombre": "Leche Entera", "mensaje": "¡Atención! Stock bajo detectado en leche."},
            {"insumo_nombre": "Pulpa de Frutilla", "mensaje": "¡Urgente! Frutilla en nivel crítico."},
        ]
            # Puedes agregar más alertas aquí

        # Contador para el resumen final
        alertas_creadas = 0

        for data in alertas_data:
            try:
                # 1. Buscamos el insumo por su nombre
                insumo = Insumo.objects.get(nombre=data["insumo_nombre"])

                # 2. Usamos get_or_create para la alerta
                alerta, creada = AlertaInsumo.objects.get_or_create(
                    insumo=insumo,
                    defaults={'mensaje': data["mensaje"]}
                )

                if creada:
                    self.stdout.write(self.style.SUCCESS(f"Alerta creada para '{insumo.nombre}'."))
                    alertas_creadas += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Alerta para '{insumo.nombre}' ya existía."))

            except Insumo.DoesNotExist:
                # Si el insumo no existe, lo informamos y continuamos
                self.stdout.write(self.style.ERROR(f"ERROR: El insumo '{data['insumo_nombre']}' no fue encontrado. Saltando..."))
        
        self.stdout.write(self.style.SUCCESS(f"\nCarga de alertas finalizada. Se crearon {alertas_creadas} nuevas alertas."))