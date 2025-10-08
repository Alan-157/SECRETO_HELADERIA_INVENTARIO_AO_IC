from django.core.management.base import BaseCommand
from inventario.models import Insumo, Bodega, InsumoLote
from accounts.models import UsuarioApp  # <-- ¡Importante! Usamos tu modelo de usuario personalizado
from datetime import date, timedelta
from random import randint

class Command(BaseCommand):
    help = "Crea un inventario inicial con lotes para varios insumos en diferentes bodegas."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de lotes de inventario..."))

        # 1. Obtenemos el primer superusuario para asignarlo como responsable
        usuario_admin = UsuarioApp.objects.filter(is_superuser=True).first()
        if not usuario_admin:
            self.stdout.write(self.style.ERROR("No se encontró un superusuario. Por favor, crea uno con 'python manage.py createsuperuser'."))
            return

        # 2. Datos de los lotes que queremos crear
        lotes_data = [
            {"insumo": "Leche Entera", "bodega": "Bodega Principal", "cantidad": randint(40, 60)},
            {"insumo": "Crema de Leche (35%)", "bodega": "Bodega Principal", "cantidad": randint(20, 30)},
            {"insumo": "Pulpa de Frutilla", "bodega": "Bodega Frutas", "cantidad": randint(30, 50)},
            {"insumo": "Pulpa de Mango", "bodega": "Bodega Frutas", "cantidad": randint(25, 45)},
            {"insumo": "Azúcar Granulada", "bodega": "Bodega Principal", "cantidad": randint(80, 120)},
            {"insumo": "Cacao Amargo en Polvo", "bodega": "Bodega Secundaria", "cantidad": randint(10, 15)},
            {"insumo": "Conos de Galleta", "bodega": "Bodega Secundaria", "cantidad": randint(200, 400)},
            {"insumo": "Nueces Mariposa", "bodega": "Bodega Secundaria", "cantidad": randint(5, 8)},
        ]

        lotes_creados = 0
        for data in lotes_data:
            try:
                # 3. Obtenemos los objetos relacionados
                insumo = Insumo.objects.get(nombre=data["insumo"])
                bodega = Bodega.objects.get(nombre=data["bodega"])
                cantidad = data["cantidad"]
                
                # Para que las fechas no sean todas iguales, restamos días aleatorios
                fecha_aleatoria = date.today() - timedelta(days=randint(1, 30))

                # 4. Usamos get_or_create para evitar duplicados del mismo insumo en la misma bodega y fecha
                lote, creado = InsumoLote.objects.get_or_create(
                    insumo=insumo,
                    bodega=bodega,
                    fecha_ingreso=fecha_aleatoria,
                    defaults={
                        'cantidad_inicial': cantidad,
                        'cantidad_actual': cantidad,
                        'usuario': usuario_admin,
                    }
                )

                if creado:
                    self.stdout.write(self.style.SUCCESS(f"Lote de '{insumo.nombre}' creado en '{bodega.nombre}' con {cantidad} unidades."))
                    lotes_creados += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Lote de '{insumo.nombre}' en '{bodega.nombre}' para la fecha {fecha_aleatoria} ya existía."))

            except Insumo.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Insumo '{data['insumo']}' no encontrado. Ejecuta 'seed_insumos'."))
            except Bodega.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Bodega '{data['bodega']}' no encontrada. Ejecuta 'seed_bodegas'."))
        
        self.stdout.write(self.style.SUCCESS(f"\nCarga de lotes finalizada. Se crearon {lotes_creados} nuevos lotes."))