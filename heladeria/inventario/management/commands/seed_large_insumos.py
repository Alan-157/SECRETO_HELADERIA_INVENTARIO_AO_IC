import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import Insumo, Categoria, UnidadMedida
from django.db.models import ObjectDoesNotExist

class Command(BaseCommand):
    help = 'Crea 5000 registros de Insumos para pruebas de rendimiento.'

    def handle(self, *args, **kwargs):
        NUM_INSUMOS = 5000
        
        try:
            # 1. Obtener objetos de claves foráneas necesarios.
            # Se asume que al menos uno de cada uno ya existe en la base de datos.
            default_categoria = Categoria.objects.filter(is_active=True).first()
            default_unidad = UnidadMedida.objects.filter(is_active=True).first()
            
            if not default_categoria or not default_unidad:
                self.stdout.write(self.style.ERROR(
                    '❌ Error: No se encontraron categorías o unidades de medida activas. '
                    'Por favor, cree al menos una categoría y una unidad de medida primero.'
                ))
                return

        except ObjectDoesNotExist:
            self.stdout.write(self.style.ERROR(
                '❌ Error: Asegúrese de que sus modelos estén migrados correctamente.'
            ))
            return
        
        self.stdout.write(self.style.WARNING(f'Iniciando la creación de {NUM_INSUMOS} insumos...'))

        insumos_a_crear = []
        
        for i in range(1, NUM_INSUMOS + 1):
            
            # Generar datos aleatorios y únicos
            nombre = f"Insumo Masivo {i:04d}"
            stock_min = Decimal(random.randint(5, 10))
            stock_max = Decimal(random.randint(50, 100))
            precio = random.randint(100, 5000)

            insumo = Insumo(
                categoria=default_categoria,
                nombre=nombre,
                stock_minimo=stock_min,
                stock_maximo=stock_max,
                unidad_medida=default_unidad,
                precio_unitario=precio,
                # is_active=True por defecto si se hereda de BaseModel
            )
            insumos_a_crear.append(insumo)

        # 2. Inserción Masiva utilizando bulk_create
        try:
            with transaction.atomic():
                Insumo.objects.bulk_create(insumos_a_crear)
            
            self.stdout.write(self.style.SUCCESS(
                f'✅ Se crearon exitosamente {NUM_INSUMOS} registros de insumos.'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante bulk_create: {e}'))