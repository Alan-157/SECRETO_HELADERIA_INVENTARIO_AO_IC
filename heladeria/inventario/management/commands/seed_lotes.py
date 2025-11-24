# inventario/management/commands/seed_lotes.py
from django.core.management.base import BaseCommand
from inventario.models import Insumo, Bodega, InsumoLote, Proveedor
from accounts.models import UsuarioApp
from datetime import date, timedelta
from random import randint

class Command(BaseCommand):
    help = "Crea un inventario inicial con lotes para varios insumos en diferentes bodegas."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de lotes de inventario..."))

        # ============================
        #  USUARIO ADMIN
        # ============================
        usuario_admin = UsuarioApp.objects.filter(is_superuser=True).first()
        if not usuario_admin:
            self.stdout.write(self.style.ERROR(
                "No se encontró un superusuario. Crea uno con 'python manage.py createsuperuser'."
            ))
            return

        # ============================
        #  PROVEEDOR POR DEFECTO
        # ============================
        proveedor_default = Proveedor.objects.filter(is_active=True).first()

        if not proveedor_default:
            self.stdout.write(self.style.WARNING(
                "⚠ No hay proveedores activos. Los lotes se crearán sin proveedor."
            ))

        # ============================
        #  LOTES BASE
        # ============================
        lotes_data = [
            {"insumo": "Leche Entera",                 "bodega": "Bodega Principal",  "cantidad": randint(40, 60)},
            {"insumo": "Crema de Leche (35%)",         "bodega": "Bodega Principal",  "cantidad": randint(20, 30)},
            {"insumo": "Pulpa de Frutilla",            "bodega": "Bodega Frutas",     "cantidad": randint(30, 50)},
            {"insumo": "Pulpa de Mango",               "bodega": "Bodega Frutas",     "cantidad": randint(25, 45)},
            {"insumo": "Azúcar Granulada",             "bodega": "Bodega Principal",  "cantidad": randint(80, 120)},
            {"insumo": "Cacao Amargo en Polvo",        "bodega": "Bodega Secundaria", "cantidad": randint(10, 15)},
            {"insumo": "Conos de Galleta",             "bodega": "Bodega Secundaria", "cantidad": randint(200, 400)},
            {"insumo": "Nueces Mariposa",              "bodega": "Bodega Secundaria", "cantidad": randint(5, 8)},
        ]

        # Caducidad estimada por producto
        shelf_defaults = {
            "Leche Entera": (90, 150),
            "Crema de Leche (35%)": (60, 120),
            "Pulpa de Frutilla": (180, 360),
            "Pulpa de Mango": (180, 360),
            "Azúcar Granulada": (365, 540),
            "Cacao Amargo en Polvo": (365, 720),
            "Conos de Galleta": (180, 360),
            "Nueces Mariposa": (180, 360),
        }

        lotes_creados = 0

        for data in lotes_data:
            try:
                insumo = Insumo.objects.get(nombre=data["insumo"])
                bodega = Bodega.objects.get(nombre=data["bodega"])
                cantidad = data["cantidad"]

                fecha_ingreso = date.today() - timedelta(days=randint(1, 30))

                min_days, max_days = shelf_defaults.get(insumo.nombre, (90, 540))
                fecha_expiracion = fecha_ingreso + timedelta(days=randint(min_days, max_days))

                lote, creado = InsumoLote.objects.get_or_create(
                    insumo=insumo,
                    bodega=bodega,
                    fecha_ingreso=fecha_ingreso,
                    fecha_expiracion=fecha_expiracion,
                    defaults={
                        "cantidad_inicial": cantidad,
                        "cantidad_actual": cantidad,
                        "usuario": usuario_admin,
                        "proveedor": proveedor_default,  # <-- agregado
                    },
                )

                if creado:
                    self.stdout.write(self.style.SUCCESS(
                        f"Lote de '{insumo.nombre}' en '{bodega.nombre}' creado "
                        f"({cantidad} uds, expira {fecha_expiracion})."
                    ))
                    lotes_creados += 1
                else:
                    self.stdout.write(self.style.WARNING(
                        f"Lote de '{insumo.nombre}' ya existía en '{bodega.nombre}' para esa fecha."
                    ))

            except Insumo.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"Insumo '{data['insumo']}' no encontrado. Ejecuta 'seed_insumos'."
                ))
            except Bodega.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"Bodega '{data['bodega']}' no encontrada. Ejecuta 'seed_bodegas'."
                ))

        self.stdout.write(self.style.SUCCESS(
            f"\nCarga de lotes finalizada. Se crearon {lotes_creados} nuevos lotes."
        ))
