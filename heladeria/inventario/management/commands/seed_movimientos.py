# inventario/management/commands/seed_movimientos.py
from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import Entrada, Salida, Insumo, InsumoLote, OrdenInsumoDetalle
from accounts.models import UsuarioApp
from datetime import date
from decimal import Decimal

class Command(BaseCommand):
    help = "Crea movimientos de entrada y salida vinculados a órdenes (si las hay) y actualiza stock/avance."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de movimientos de prueba..."))

        usuario = UsuarioApp.objects.filter(is_superuser=True).first()
        if not usuario:
            self.stdout.write(self.style.ERROR("No se encontró un superusuario. Crea uno con 'createsuperuser'."))
            return

        # ENTRADAS (intenta vincular a un detalle de orden del mismo insumo)
        entradas_data = [
            {"insumo": "Azúcar Granulada",           "cantidad": Decimal("100"), "obs": "Compra a proveedor A"},
            {"insumo": "Cobertura de Chocolate 70%", "cantidad": Decimal("10"),  "obs": "Parcial orden en curso"},
        ]

        for data in entradas_data:
            insumo = Insumo.objects.filter(nombre=data["insumo"]).first()
            lote = InsumoLote.objects.filter(insumo=insumo).first()
            if not insumo or not lote:
                self.stdout.write(self.style.WARNING(f"Insumo o lote para '{data['insumo']}' no encontrado. Saltando entrada..."))
                continue

            ubicacion = lote.bodega.ubicaciones.first()
            if not ubicacion:
                self.stdout.write(self.style.ERROR(f"La bodega '{lote.bodega.nombre}' no tiene ubicaciones. Ejecuta 'seed_bodegas'."))
                continue

            # Busca un detalle de orden pendiente/en curso para este insumo
            detalle = OrdenInsumoDetalle.objects.filter(
                insumo=insumo,
                orden_insumo__estado__in=["PENDIENTE", "EN_CURSO"]
            ).order_by("orden_insumo__fecha").first()

            entrada = Entrada.objects.create(
                insumo=insumo, insumo_lote=lote, ubicacion=ubicacion,
                cantidad=data["cantidad"], fecha=date.today(),
                usuario=usuario, observaciones=data["obs"],
                orden=(detalle.orden_insumo if detalle else None),
                detalle=detalle
            )
            lote.cantidad_actual = (lote.cantidad_actual or Decimal("0")) + data["cantidad"]
            lote.save(update_fields=["cantidad_actual"])

            # Si hay detalle, suma atendido y recalcula estado de la orden
            if detalle:
                detalle.cantidad_atendida = (detalle.cantidad_atendida or Decimal("0")) + data["cantidad"]
                detalle.save(update_fields=["cantidad_atendida"])
                detalle.orden_insumo.recalc_estado()

            self.stdout.write(self.style.SUCCESS(f"Entrada de {data['cantidad']} de '{insumo.nombre}' registrada."))

        # SALIDAS (no suelen vincularse a orden de compra; mantenemos stock)
        salidas_data = [
            {"insumo": "Leche Entera",      "cantidad": Decimal("5")},
            {"insumo": "Pulpa de Frutilla", "cantidad": Decimal("2")},
        ]
        for data in salidas_data:
            insumo = Insumo.objects.filter(nombre=data["insumo"]).first()
            lote = InsumoLote.objects.filter(insumo=insumo, cantidad_actual__gt=0).first()
            if not insumo or not lote:
                self.stdout.write(self.style.WARNING(f"Insumo o lote con stock para '{data['insumo']}' no encontrado. Saltando salida..."))
                continue

            ubicacion = lote.bodega.ubicaciones.first()
            if not ubicacion:
                self.stdout.write(self.style.ERROR(f"La bodega '{lote.bodega.nombre}' no tiene ubicaciones. Ejecuta 'seed_bodegas'."))
                continue

            cant = min(data["cantidad"], lote.cantidad_actual)
            Salida.objects.create(
                insumo=insumo, insumo_lote=lote, ubicacion=ubicacion,
                cantidad=cant, fecha_generada=date.today(),
                usuario=usuario, tipo="USO_PRODUCCION"
            )
            lote.cantidad_actual = (lote.cantidad_actual or Decimal("0")) - cant
            lote.save(update_fields=["cantidad_actual"])
            self.stdout.write(self.style.SUCCESS(f"Salida de {cant} de '{insumo.nombre}' registrada."))

        self.stdout.write(self.style.SUCCESS("\nCarga de movimientos finalizada."))
