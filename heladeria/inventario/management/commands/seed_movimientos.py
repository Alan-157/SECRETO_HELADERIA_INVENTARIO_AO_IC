from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import Entrada, Salida, Insumo, InsumoLote, Ubicacion
from accounts.models import UsuarioApp
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = "Crea movimientos de entrada y salida de prueba, actualizando el stock de los lotes."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de movimientos de prueba..."))

        # Obtenemos el primer superusuario para registrar los movimientos
        usuario = UsuarioApp.objects.filter(is_superuser=True).first()
        if not usuario:
            self.stdout.write(self.style.ERROR("No se encontró un superusuario. Por favor, crea uno con 'python manage.py createsuperuser'."))
            return

        # --- Movimientos de ENTRADA (simulando compras) ---
        entradas_data = [
            {'insumo': 'Azúcar', 'cantidad': 100, 'obs': 'Compra a proveedor A'},
            {'insumo': 'Chocolate Cobertura', 'cantidad': 25, 'obs': 'Nuevo stock'},
        ]

        for data in entradas_data:
            insumo = Insumo.objects.filter(nombre=data['insumo']).first()
            lote = InsumoLote.objects.filter(insumo=insumo).first()
            if not insumo or not lote:
                self.stdout.write(self.style.WARNING(f"Insumo o lote para '{data['insumo']}' no encontrado. Saltando entrada..."))
                continue

            # --- CORRECCIÓN AQUÍ ---
            # Obtenemos la primera ubicación asociada a la bodega del lote
            ubicacion = lote.bodega.ubicaciones.first()
            if not ubicacion:
                self.stdout.write(self.style.ERROR(f"La bodega '{lote.bodega.nombre}' no tiene ubicaciones. Saltando..."))
                continue
            
            Entrada.objects.create(
                insumo=insumo, insumo_lote=lote, ubicacion=ubicacion,
                cantidad=data['cantidad'], fecha=date.today(),
                usuario=usuario, observaciones=data['obs']
            )

            # Actualizamos el stock del lote
            lote.cantidad_actual += data['cantidad']
            lote.save()
            self.stdout.write(self.style.SUCCESS(f"Entrada de {data['cantidad']} de '{insumo.nombre}' registrada."))


        # --- Movimientos de SALIDA (simulando uso/venta) ---
        salidas_data = [
            {'insumo': 'Leche Entera', 'cantidad': 5},
            {'insumo': 'Frutilla', 'cantidad': 2},
        ]

        for data in salidas_data:
            insumo = Insumo.objects.filter(nombre=data['insumo']).first()
            lote = InsumoLote.objects.filter(insumo=insumo, cantidad_actual__gt=0).first()
            if not insumo or not lote:
                self.stdout.write(self.style.WARNING(f"Insumo o lote con stock para '{data['insumo']}' no encontrado. Saltando salida..."))
                continue
            
            # --- CORRECCIÓN AQUÍ ---
            # Obtenemos la primera ubicación asociada a la bodega del lote
            ubicacion = lote.bodega.ubicaciones.first()
            if not ubicacion:
                self.stdout.write(self.style.ERROR(f"La bodega '{lote.bodega.nombre}' no tiene ubicaciones. Saltando..."))
                continue

            cantidad_salida = min(data['cantidad'], lote.cantidad_actual) # Para no dejar stock negativo
            Salida.objects.create(
                insumo=insumo, insumo_lote=lote, ubicacion=ubicacion,
                cantidad=cantidad_salida, fecha_generada=date.today(),
                usuario=usuario, tipo="USO_PRODUCCION"
            )

            # Actualizamos el stock del lote
            lote.cantidad_actual -= cantidad_salida
            lote.save()
            self.stdout.write(self.style.SUCCESS(f"Salida de {cantidad_salida} de '{insumo.nombre}' registrada."))

        self.stdout.write(self.style.SUCCESS("\nCarga de movimientos finalizada."))