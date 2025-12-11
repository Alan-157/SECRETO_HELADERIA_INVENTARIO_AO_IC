import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import ObjectDoesNotExist
# Importaciones necesarias desde los modelos de sus aplicaciones
from inventario import models as inventario_models
from accounts import models as accounts_models 

class Command(BaseCommand):
    help = 'Crea 10,000 registros de movimientos (Entrada y Salida) para pruebas de rendimiento.'

    def handle(self, *args, **kwargs):
        NUM_MOVIMIENTOS = 5000 # 5000 Entradas y 5000 Salidas = 10,000 total
        NUM_LOTES_BASE = 500
        BATCH_SIZE = 1000  # 🔥 Límite de registros por inserción para evitar timeouts

        self.stdout.write(self.style.WARNING(f'Iniciando la creación masiva de movimientos ({NUM_MOVIMIENTOS * 2} total)...'))

        try:
            # 1. Obtener objetos de claves foráneas necesarios.
            user_app = accounts_models.UsuarioApp.objects.filter(is_active=True).first()
            ubicaciones = list(inventario_models.Ubicacion.objects.filter(is_active=True))
            insumos = list(inventario_models.Insumo.objects.filter(is_active=True)[:100])
            proveedores = list(inventario_models.Proveedor.objects.filter(is_active=True))

            if not user_app or not ubicaciones or not insumos or not proveedores:
                self.stdout.write(self.style.ERROR(
                    '❌ Error: No se encontraron usuarios, ubicaciones, insumos o proveedores activos. '
                    'Asegúrese de ejecutar las semillas de datos maestros primero.'
                ))
                return

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al obtener modelos base: {e}'))
            return
        
        # 2. Crear Lotes de Insumos (Necesarios para vincular Entradas y Salidas)
        lotes_a_crear = []
        for i in range(NUM_LOTES_BASE):
            insumo = random.choice(insumos)
            ubicacion = random.choice(ubicaciones)
            proveedor = random.choice(proveedores)
            
            lote = inventario_models.InsumoLote(
                insumo=insumo,
                bodega=ubicacion.bodega,
                proveedor=proveedor,
                fecha_ingreso=date.today() - timedelta(days=random.randint(10, 50)),
                fecha_expiracion=date.today() + timedelta(days=random.randint(30, 365)),
                cantidad_inicial=Decimal(random.randint(100, 500)),
                cantidad_actual=Decimal(random.randint(50, 200)),
                usuario=user_app,
            )
            lotes_a_crear.append(lote)
        
        self.stdout.write(f'Creando {NUM_LOTES_BASE} lotes de insumos base...')
        try:
            with transaction.atomic():
                # 🔥 Se aplica BATCH_SIZE (Incluso si es una lista pequeña, es buena práctica)
                inventario_models.InsumoLote.objects.bulk_create(lotes_a_crear, batch_size=BATCH_SIZE)
            self.stdout.write(self.style.SUCCESS('✅ Lotes creados exitosamente.'))
            lotes = list(inventario_models.InsumoLote.objects.all())
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante bulk_create de lotes: {e}'))
            return

        # 3. Crear Entradas (5000 registros)
        entradas_a_crear = []
        for i in range(NUM_MOVIMIENTOS):
            insumo = random.choice(insumos)
            ubicacion = random.choice(ubicaciones)
            lote = random.choice(lotes)
            
            entrada = inventario_models.Entrada(
                insumo=insumo,
                insumo_lote=lote,
                ubicacion=ubicacion,
                cantidad=Decimal(random.randint(5, 50)),
                fecha=date.today() - timedelta(days=random.randint(0, 10)),
                usuario=user_app,
                tipo="COMPRA_MASIVA",
            )
            entradas_a_crear.append(entrada)

        self.stdout.write(f'Creando {NUM_MOVIMIENTOS} entradas...')
        try:
            with transaction.atomic():
                # 🔥 APLICACIÓN CRÍTICA del BATCH_SIZE
                inventario_models.Entrada.objects.bulk_create(entradas_a_crear, batch_size=BATCH_SIZE)
            self.stdout.write(self.style.SUCCESS('✅ Entradas creadas exitosamente.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante bulk_create de entradas: {e}'))
            return

        # 4. Crear Salidas (5000 registros)
        salidas_a_crear = []
        for i in range(NUM_MOVIMIENTOS):
            insumo = random.choice(insumos)
            ubicacion = random.choice(ubicaciones)
            lote = random.choice(lotes)
            
            salida = inventario_models.Salida(
                insumo=insumo,
                insumo_lote=lote,
                ubicacion=ubicacion,
                cantidad=Decimal(random.randint(1, 20)),
                fecha_generada=date.today() - timedelta(days=random.randint(0, 10)),
                usuario=user_app,
                tipo="PRODUCCION_MASIVA",
            )
            salidas_a_crear.append(salida)
        
        self.stdout.write(f'Creando {NUM_MOVIMIENTOS} salidas...')
        try:
            with transaction.atomic():
                # 🔥 APLICACIÓN CRÍTICA del BATCH_SIZE
                inventario_models.Salida.objects.bulk_create(salidas_a_crear, batch_size=BATCH_SIZE)
            self.stdout.write(self.style.SUCCESS('✅ Salidas creadas exitosamente.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante bulk_create de salidas: {e}'))
            return

        self.stdout.write(self.style.SUCCESS('\n🎉 Proceso de creación masiva de movimientos finalizado.'))