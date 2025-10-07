from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import OrdenInsumo, OrdenInsumoDetalle, Insumo
from accounts.models import UsuarioApp
from datetime import date, timedelta
from random import choice, randint

class Command(BaseCommand):
    help = "Crea órdenes de insumos de prueba con diferentes estados y detalles."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de órdenes de insumos..."))

        # Obtenemos un superusuario para crear las órdenes
        usuario = UsuarioApp.objects.filter(is_superuser=True).first()
        if not usuario:
            self.stdout.write(self.style.ERROR("No se encontró un superusuario. Ejecuta 'createsuperuser' primero."))
            return

        # Definimos varias órdenes con sus detalles
        ordenes_data = [
            {
                "estado": "PENDIENTE",
                "fecha_offset": 2, # Días atrás
                "detalles": [
                    {"insumo": "Leche Entera", "cantidad": 20},
                    {"insumo": "Azúcar Granulada", "cantidad": 50},
                    {"insumo": "Vasos de Polipapel 4oz", "cantidad": 500},
                ]
            },
            {
                "estado": "EN_CURSO",
                "fecha_offset": 5,
                "detalles": [
                    {"insumo": "Pulpa de Mango", "cantidad": 15},
                    {"insumo": "Cobertura de Chocolate 70%", "cantidad": 10},
                    {"insumo": "Nueces Mariposa", "cantidad": 5},
                ]
            },
            {
                "estado": "CERRADA",
                "fecha_offset": 10,
                "detalles": [
                    {"insumo": "Crema de Leche (35%)", "cantidad": 10},
                    {"insumo": "Cacao Amargo en Polvo", "cantidad": 5},
                ]
            }
        ]

        ordenes_creadas = 0
        for data in ordenes_data:
            fecha_orden = date.today() - timedelta(days=data["fecha_offset"])

            # Creamos la orden principal, usamos get_or_create para no duplicar
            orden, creada = OrdenInsumo.objects.get_or_create(
                usuario=usuario,
                fecha=fecha_orden,
                defaults={'estado': data["estado"]}
            )

            if creada:
                self.stdout.write(self.style.SUCCESS(f"Orden ID {orden.id} creada para el {fecha_orden} con estado '{orden.estado}'."))
                ordenes_creadas += 1

                # Creamos los detalles para la nueva orden
                for detalle_data in data["detalles"]:
                    try:
                        insumo = Insumo.objects.get(nombre=detalle_data["insumo"])
                        OrdenInsumoDetalle.objects.create(
                            orden_insumo=orden,
                            insumo=insumo,
                            cantidad_solicitada=detalle_data["cantidad"]
                        )
                        self.stdout.write(f"  └─ Detalle agregado: {detalle_data['cantidad']} de '{insumo.nombre}'")
                    except Insumo.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f"  └─ ERROR: Insumo '{detalle_data['insumo']}' no encontrado. Saltando detalle."))
            else:
                 self.stdout.write(self.style.WARNING(f"Orden para el {fecha_orden} ya existía. Saltando."))

        self.stdout.write(self.style.SUCCESS(f"\nCarga de órdenes finalizada. Se crearon {ordenes_creadas} nuevas órdenes."))