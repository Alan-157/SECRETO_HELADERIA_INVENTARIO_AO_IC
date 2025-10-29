# inventario/management/commands/seed_ordenes.py
from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import OrdenInsumo, OrdenInsumoDetalle, Insumo
from accounts.models import UsuarioApp
from datetime import date, timedelta
from decimal import Decimal
import random

class Command(BaseCommand):
    help = "Crea órdenes de insumos de prueba con estados coherentes y avance real."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de órdenes de insumos..."))

        usuario = UsuarioApp.objects.filter(is_superuser=True).first()
        if not usuario:
            self.stdout.write(self.style.ERROR("No se encontró un superusuario. Ejecuta 'createsuperuser' primero."))
            return

        ordenes_data = [
            # PENDIENTE: nada atendido
            {
                "estado": "PENDIENTE",
                "fecha_offset": 2,
                "detalles": [
                    {"insumo": "Leche Entera", "cantidad": Decimal("20")},
                    {"insumo": "Azúcar Granulada", "cantidad": Decimal("50")},
                    {"insumo": "Vasos de Polipapel 4oz", "cantidad": Decimal("500")},
                ],
                "avance": "none",
            },
            # EN_CURSO: algunos detalles con avance parcial
            {
                "estado": "EN_CURSO",
                "fecha_offset": 5,
                "detalles": [
                    {"insumo": "Pulpa de Mango", "cantidad": Decimal("15")},
                    {"insumo": "Cobertura de Chocolate 70%", "cantidad": Decimal("10")},
                    {"insumo": "Nueces Mariposa", "cantidad": Decimal("5")},
                ],
                "avance": "partial",
            },
            # CERRADA: todo atendido
            {
                "estado": "CERRADA",
                "fecha_offset": 10,
                "detalles": [
                    {"insumo": "Crema de Leche (35%)", "cantidad": Decimal("10")},
                    {"insumo": "Cacao Amargo en Polvo", "cantidad": Decimal("5")},
                ],
                "avance": "full",
            },
        ]

        creadas = 0
        for data in ordenes_data:
            fecha_orden = date.today() - timedelta(days=data["fecha_offset"])
            orden, creada = OrdenInsumo.objects.get_or_create(
                usuario=usuario,
                fecha=fecha_orden,
                estado=data["estado"],
            )
            if creada:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(f"Orden creada ({orden.estado}) {fecha_orden}."))

                for det in data["detalles"]:
                    try:
                        insumo = Insumo.objects.get(nombre=det["insumo"])
                        d = OrdenInsumoDetalle.objects.create(
                            orden_insumo=orden,
                            insumo=insumo,
                            cantidad_solicitada=det["cantidad"],
                        )
                        # Ajuste de avance según el estado objetivo
                        if data["avance"] == "full":
                            d.cantidad_atendida = d.cantidad_solicitada
                        elif data["avance"] == "partial":
                            # 30–60% aleatorio como ejemplo
                            factor = Decimal(random.randint(30, 60)) / Decimal(100)
                            d.cantidad_atendida = (d.cantidad_solicitada * factor).quantize(Decimal("0.01"))
                        # PENDIENTE => atendida 0 por defecto
                        d.save(update_fields=["cantidad_atendida"])
                        self.stdout.write(f"  └─ {d.cantidad_solicitada} × {insumo.nombre} (atendida: {d.cantidad_atendida})")
                    except Insumo.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f"  └─ Insumo '{det['insumo']}' no existe."))

                # Recalcula para dejar el estado coherente con los datos de avance
                orden.recalc_estado()
            else:
                self.stdout.write(self.style.WARNING(f"Orden del {fecha_orden} ({data['estado']}) ya existía."))

        self.stdout.write(self.style.SUCCESS(f"\nCarga finalizada. {creadas} órdenes nuevas creadas."))
