# inventario/management/commands/seed_movimientos.py
from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import (
    Entrada, Salida, Insumo, InsumoLote,
    OrdenInsumoDetalle
)
from accounts.models import UsuarioApp
from datetime import date
from decimal import Decimal


class Command(BaseCommand):
    help = "Crea movimientos de entrada y salida y actualiza stock."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de movimientos..."))

        # Usuario
        usuario = UsuarioApp.objects.filter(is_superuser=True).first()
        if not usuario:
            self.stdout.write(self.style.ERROR("No existe SUPERUSUARIO. Ejecute createsuperuser."))
            return

        # ==========================================================
        # ENTRADAS
        # ==========================================================
        entradas_data = [
            {"insumo": "Azúcar Granulada", "cantidad": Decimal("100"), "obs": "Compra proveedor A"},
            {"insumo": "Cobertura de Chocolate 70%", "cantidad": Decimal("10"), "obs": "Ingreso parcial orden"},
        ]

        for data in entradas_data:
            insumo = Insumo.objects.filter(nombre=data["insumo"]).first()
            lote = InsumoLote.objects.filter(insumo=insumo).first()

            if not insumo or not lote:
                self.stdout.write(self.style.WARNING(f"Insumo o lote para '{data['insumo']}' no encontrado."))
                continue

            # Ubicación correcta según el modelo actual
            ubicacion = lote.bodega.ubicacion

            # Buscar una orden/Detalle pendiente o en curso
            detalle = OrdenInsumoDetalle.objects.filter(
                insumo=insumo,
                orden_insumo__estado__in=["PENDIENTE", "EN_CURSO"]
            ).order_by("orden_insumo__fecha").first()

            entrada = Entrada.objects.create(
                insumo=insumo,
                insumo_lote=lote,
                ubicacion=ubicacion,
                cantidad=data["cantidad"],
                fecha=date.today(),
                usuario=usuario,
                observaciones=data["obs"],
                orden=(detalle.orden_insumo if detalle else None),
                detalle=detalle,
            )

            # Actualizar stock
            lote.cantidad_actual = (lote.cantidad_actual or Decimal("0")) + data["cantidad"]
            lote.save(update_fields=["cantidad_actual"])

            # Actualizar avance en orden
            if detalle:
                detalle.cantidad_atendida = (detalle.cantidad_atendida or Decimal("0")) + data["cantidad"]
                detalle.save(update_fields=["cantidad_atendida"])
                detalle.orden_insumo.recalc_estado()

            self.stdout.write(self.style.SUCCESS(
                f"Entrada registrada: +{data['cantidad']} {insumo.nombre}"
            ))

        # ==========================================================
        # SALIDAS
        # ==========================================================
        salidas_data = [
            {"insumo": "Leche Entera", "cantidad": Decimal("5")},
            {"insumo": "Pulpa de Frutilla", "cantidad": Decimal("2")},
        ]

        for data in salidas_data:
            insumo = Insumo.objects.filter(nombre=data["insumo"]).first()
            lote = InsumoLote.objects.filter(insumo=insumo, cantidad_actual__gt=0).first()

            if not insumo or not lote:
                self.stdout.write(self.style.WARNING(
                    f"No hay stock para salida de '{data['insumo']}'."
                ))
                continue

            ubicacion = lote.bodega.ubicacion

            cant = min(data["cantidad"], lote.cantidad_actual)

            Salida.objects.create(
                insumo=insumo,
                insumo_lote=lote,
                ubicacion=ubicacion,
                cantidad=cant,
                fecha_generada=date.today(),
                usuario=usuario,
                tipo="USO_PRODUCCION",
            )

            lote.cantidad_actual -= cant
            lote.save(update_fields=["cantidad_actual"])

            self.stdout.write(self.style.SUCCESS(
                f"Salida registrada: -{cant} {insumo.nombre}"
            ))

        self.stdout.write(self.style.SUCCESS("\nMovimientos generados correctamente."))
