# inventario/management/commands/seed_proveedores.py
from decimal import Decimal
from django.core.management.base import BaseCommand
from inventario.models import Proveedor

class Command(BaseCommand):
    help = "Crea o actualiza proveedores de prueba para la heladería."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de proveedores..."))

        proveedores_data = [
            {
                "nombre_empresa": "Lácteos del Valle SpA",
                "rut_empresa": "76.123.456-7",
                "email": "ventas@lacteosdelvalle.cl",
                "telefono": "+56 9 1111 1111",
                "telefono_alternativo": "+56 51 222 2222",
                "direccion": "Av. Balmaceda 1200",
                "ciudad": "La Serena",
                "region": "Coquimbo",
                "estado": "ACTIVO",
                "condiciones_pago": "Transferencia 30 días",
                "dias_credito": 30,
                "monto_credito": Decimal("500000.00"),
                "observaciones": "Proveedor principal de lácteos."
            },
            {
                "nombre_empresa": "Frutícola Elqui Ltda.",
                "rut_empresa": "77.987.654-3",
                "email": "contacto@fruticolaelqui.cl",
                "telefono": "+56 9 2222 2222",
                "telefono_alternativo": None,
                "direccion": "Ruta 41 Km 16",
                "ciudad": "Vicuña",
                "region": "Coquimbo",
                "estado": "ACTIVO",
                "condiciones_pago": "Efectivo/Transferencia",
                "dias_credito": 0,
                "monto_credito": Decimal("0.00"),
                "observaciones": "Fruta fresca y pulpas congeladas."
            },
            {
                "nombre_empresa": "Distribuidora Dulce Norte",
                "rut_empresa": "78.555.444-1",
                "email": "ventas@dulcenorte.cl",
                "telefono": "+56 9 3333 3333",
                "telefono_alternativo": "+56 51 233 4455",
                "direccion": "Los Perales 455",
                "ciudad": "Coquimbo",
                "region": "Coquimbo",
                "estado": "ACTIVO",
                "condiciones_pago": "Crédito 15 días",
                "dias_credito": 15,
                "monto_credito": Decimal("250000.00"),
                "observaciones": "Azúcares, confites y toppings."
            },
            {
                "nombre_empresa": "Envases Pacífico",
                "rut_empresa": "79.111.222-9",
                "email": "ventas@envasespacifico.cl",
                "telefono": "+56 9 4444 4444",
                "telefono_alternativo": None,
                "direccion": "Av. del Mar 500",
                "ciudad": "La Serena",
                "region": "Coquimbo",
                "estado": "ACTIVO",
                "condiciones_pago": "OC / Factura 30 días",
                "dias_credito": 30,
                "monto_credito": Decimal("300000.00"),
                "observaciones": "Conos, vasos, cucharitas, descartables."
            },
            {
                "nombre_empresa": "Cacao Andes Import",
                "rut_empresa": "80.333.222-0",
                "email": "importaciones@cacaoandes.cl",
                "telefono": "+56 9 5555 5555",
                "telefono_alternativo": None,
                "direccion": "Providencia 1010",
                "ciudad": "Santiago",
                "region": "Metropolitana",
                "estado": "SUSPENDIDO",
                "condiciones_pago": "Solo contado",
                "dias_credito": 0,
                "monto_credito": Decimal("0.00"),
                "observaciones": "Suspendido por retrasos en entregas."
            },
        ]

        creados = 0
        actualizados = 0

        for data in proveedores_data:
            # Usamos rut_empresa como identificador fuerte (es unique)
            rut = data["rut_empresa"]

            proveedor, creado = Proveedor.objects.get_or_create(
                rut_empresa=rut,
                defaults=data
            )

            if creado:
                creados += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Proveedor creado: {proveedor.nombre_empresa} ({proveedor.rut_empresa})"
                ))
            else:
                # Si existe, actualizamos los campos por si cambian datos de prueba
                changed = False
                for k, v in data.items():
                    if getattr(proveedor, k) != v:
                        setattr(proveedor, k, v)
                        changed = True

                if changed:
                    proveedor.save()
                    actualizados += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Proveedor actualizado: {proveedor.nombre_empresa} ({proveedor.rut_empresa})"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"Proveedor ya existía sin cambios: {proveedor.nombre_empresa}"
                    ))

        self.stdout.write(self.style.SUCCESS(
            f"\nCarga finalizada. {creados} creados, {actualizados} actualizados."
        ))
