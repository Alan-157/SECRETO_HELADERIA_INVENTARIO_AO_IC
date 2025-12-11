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
    help = 'Crea 5,000 registros de Entradas y sus respectivos Lotes para pruebas de rendimiento.'

    def handle(self, *args, **kwargs):
        NUM_ENTRADAS = 5000 
        BATCH_SIZE = 1000  

        self.stdout.write(self.style.WARNING(f'Iniciando la creación masiva de {NUM_ENTRADAS} Entradas y Lotes...'))

        try:
            # 1. Obtener objetos de claves foráneas necesarios.
            user_app = accounts_models.UsuarioApp.objects.filter(is_active=True).first()
            ubicaciones = list(inventario_models.Ubicacion.objects.filter(is_active=True))
            insumos = list(inventario_models.Insumo.objects.filter(is_active=True)[:100])
            proveedores = list(inventario_models.Proveedor.objects.filter(is_active=True))

            if not user_app or not ubicaciones or not insumos or not proveedores:
                self.stdout.write(self.style.ERROR(
                    '❌ Error: No se encontraron usuarios, ubicaciones, insumos o proveedores activos. '
                    'Asegúrese de tener datos maestros.'
                ))
                return

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al obtener modelos base: {e}'))
            return
        
        # --- 2. Crear Lotes de Insumos (Una Entrada = Un Lote) ---
        lotes_a_crear = []
        
        for i in range(NUM_ENTRADAS):
            insumo = random.choice(insumos)
            ubicacion = random.choice(ubicaciones)
            proveedor = random.choice(proveedores)
            
            lote = inventario_models.InsumoLote(
                insumo=insumo,
                bodega=ubicacion.bodega,
                proveedor=proveedor,
                fecha_ingreso=date.today() - timedelta(days=random.randint(10, 50)),
                fecha_expiracion=date.today() + timedelta(days=random.randint(30, 365)),
                cantidad_inicial=Decimal(random.randint(10, 100)),
                cantidad_actual=Decimal(random.randint(10, 100)),
                usuario=user_app,
            )
            lotes_a_crear.append(lote)
        
        self.stdout.write(f'Creando {NUM_ENTRADAS} lotes...')
        
        try:
            # 🔥 PASO 1: Registrar el ID de la última fila ANTES de la inserción
            last_lote = inventario_models.InsumoLote.objects.order_by('-id').first()
            start_pk = last_lote.id + 1 if last_lote else 1

            with transaction.atomic():
                # Inserción masiva de lotes (sin el parámetro return_instance)
                inventario_models.InsumoLote.objects.bulk_create(
                    lotes_a_crear, 
                    batch_size=BATCH_SIZE
                )
            self.stdout.write(self.style.SUCCESS('✅ Lotes creados exitosamente.'))
            
            # 🔥 PASO 2: Recuperar los lotes recién creados usando el rango de IDs
            lotes_creados = list(inventario_models.InsumoLote.objects.filter(
                id__gte=start_pk
            ).order_by('id').select_related('insumo')) # Añadimos select_related para eficiencia
            
            if len(lotes_creados) != NUM_ENTRADAS:
                self.stdout.write(self.style.ERROR('❌ Error de conteo: La cantidad de lotes recuperados no coincide con la cantidad a crear. Abortando Entradas.'))
                return

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante bulk_create de lotes: {e}'))
            return

        # 3. Crear Entradas (5000 registros)
        entradas_a_crear = []
        for lote in lotes_creados:
            # Ahora, 'lote' es un objeto de BD con su ID
            entrada = inventario_models.Entrada(
                insumo=lote.insumo,
                insumo_lote=lote, # Enlace directo al objeto de BD recuperado
                ubicacion=random.choice(ubicaciones),
                cantidad=lote.cantidad_inicial,
                fecha=lote.fecha_ingreso,
                usuario=user_app,
                tipo="COMPRA_MASIVA",
            )
            entradas_a_crear.append(entrada)

        self.stdout.write(f'Creando {NUM_ENTRADAS} entradas...')
        try:
            with transaction.atomic():
                # Aplicación crítica del BATCH_SIZE para Entradas
                inventario_models.Entrada.objects.bulk_create(entradas_a_crear, batch_size=BATCH_SIZE)
            self.stdout.write(self.style.SUCCESS('✅ Entradas creadas exitosamente.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante bulk_create de entradas: {e}'))
            return

        self.stdout.write(self.style.SUCCESS('\n🎉 Proceso de creación masiva de entradas finalizado.'))