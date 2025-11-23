from django.core.management.base import BaseCommand
# Importamos el nuevo modelo UnidadMedida
from inventario.models import Insumo, Categoria, UnidadMedida 

class Command(BaseCommand):
    help = "Crea un catálogo inicial de insumos de prueba para la heladería."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de insumos de prueba..."))
        
        # 1. Definición de Unidades de Medida a crear
        unidades_map = {
            "Litro": {"nombre_corto": "LT", "nombre_largo": "Litro"},
            "Kilo": {"nombre_corto": "KG", "nombre_largo": "Kilo"},
            "Unidad": {"nombre_corto": "UN", "nombre_largo": "Unidad"},
            # Si tienes otros códigos como GR o ML, añádelos aquí.
        }

        # 2. Creamos o verificamos las Unidades de Medida
        self.stdout.write(self.style.NOTICE("Creando Unidades de Medida..."))
        unidades_objects = {}
        for largo, data in unidades_map.items():
            unidad, creado = UnidadMedida.objects.get_or_create(
                nombre_largo=largo,
                defaults=data
            )
            unidades_objects[largo] = unidad
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Unidad '{largo}' creada."))

        self.stdout.write(self.style.NOTICE("Iniciando la creación de Insumos..."))

        insumos_data = [
            # Lácteos
            {"nombre": "Leche Entera", "categoria_nombre": "Lácteos", "unidad_medida_key": "Litro", "stock_minimo": 20, "stock_maximo": 100, "precio_unitario": 1200},
            {"nombre": "Crema de Leche (35%)", "categoria_nombre": "Lácteos", "unidad_medida_key": "Litro", "stock_minimo": 10, "stock_maximo": 50, "precio_unitario": 4500},
            {"nombre": "Leche en Polvo", "categoria_nombre": "Lácteos", "unidad_medida_key": "Kilo", "stock_minimo": 5, "stock_maximo": 25, "precio_unitario": 8000},

            # Frutas Congeladas
            {"nombre": "Pulpa de Frutilla", "categoria_nombre": "Frutas Congeladas", "unidad_medida_key": "Kilo", "stock_minimo": 10, "stock_maximo": 80, "precio_unitario": 3500},
            {"nombre": "Pulpa de Mango", "categoria_nombre": "Frutas Congeladas", "unidad_medida_key": "Kilo", "stock_minimo": 10, "stock_maximo": 80, "precio_unitario": 4200},
            {"nombre": "Arándanos Congelados", "categoria_nombre": "Frutas Congeladas", "unidad_medida_key": "Kilo", "stock_minimo": 5, "stock_maximo": 40, "precio_unitario": 4000},

            # Azúcares y Endulzantes
            {"nombre": "Azúcar Granulada", "categoria_nombre": "Azúcares y Endulzantes", "unidad_medida_key": "Kilo", "stock_minimo": 25, "stock_maximo": 150, "precio_unitario": 1300},
            {"nombre": "Glucosa", "categoria_nombre": "Azúcares y Endulzantes", "unidad_medida_key": "Kilo", "stock_minimo": 5, "stock_maximo": 20, "precio_unitario": 3000},
            {"nombre": "Dextrosa", "categoria_nombre": "Azúcares y Endulzantes", "unidad_medida_key": "Kilo", "stock_minimo": 5, "stock_maximo": 20, "precio_unitario": 3200},

            # Chocolates y Confites
            {"nombre": "Cacao Amargo en Polvo", "categoria_nombre": "Chocolates y Confites", "unidad_medida_key": "Kilo", "stock_minimo": 2, "stock_maximo": 15, "precio_unitario": 15000},
            {"nombre": "Cobertura de Chocolate 70%", "categoria_nombre": "Chocolates y Confites", "unidad_medida_key": "Kilo", "stock_minimo": 5, "stock_maximo": 30, "precio_unitario": 18000},
            {"nombre": "Chips de Chocolate", "categoria_nombre": "Chocolates y Confites", "unidad_medida_key": "Kilo", "stock_minimo": 3, "stock_maximo": 20, "precio_unitario": 9000},

            # Envases y Descartables
            {"nombre": "Conos de Galleta", "categoria_nombre": "Envases y Descartables", "unidad_medida_key": "Unidad", "stock_minimo": 100, "stock_maximo": 500, "precio_unitario": 150},
            {"nombre": "Vasos de Polipapel 4oz", "categoria_nombre": "Envases y Descartables", "unidad_medida_key": "Unidad", "stock_minimo": 200, "stock_maximo": 1000, "precio_unitario": 80},
            {"nombre": "Cucharitas de Helado", "categoria_nombre": "Envases y Descartables", "unidad_medida_key": "Unidad", "stock_minimo": 500, "stock_maximo": 2000, "precio_unitario": 30},
            
            # Frutos Secos
            {"nombre": "Nueces Mariposa", "categoria_nombre": "Frutos Secos", "unidad_medida_key": "Kilo", "stock_minimo": 2, "stock_maximo": 10, "precio_unitario": 12000},
            {"nombre": "Almendras Laminadas", "categoria_nombre": "Frutos Secos", "unidad_medida_key": "Kilo", "stock_minimo": 2, "stock_maximo": 10, "precio_unitario": 14000},
        ]

        insumos_creados = 0
        for data in insumos_data:
            try:
                # 3. Obtenemos los objetos necesarios
                categoria = Categoria.objects.get(nombre=data["categoria_nombre"])
                unidad = unidades_objects[data["unidad_medida_key"]] # <-- Obtenemos el objeto UnidadMedida

                # 4. Preparamos los defaults con el objeto UnidadMedida
                defaults = {
                    "categoria": categoria,
                    "unidad_medida": unidad, # <-- Usamos el objeto
                    "stock_minimo": data["stock_minimo"],
                    "stock_maximo": data["stock_maximo"],
                    "precio_unitario": data["precio_unitario"],
                }
                
                # Creamos o obtenemos el insumo
                insumo, creado = Insumo.objects.get_or_create(
                    nombre=data["nombre"],
                    defaults=defaults
                )

                if creado:
                    self.stdout.write(self.style.SUCCESS(f"Insumo '{insumo.nombre}' creado."))
                    insumos_creados += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Insumo '{insumo.nombre}' ya existe."))

            except Categoria.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"ERROR: La categoría '{data['categoria_nombre']}' no existe. Ejecuta 'seed_categorias' primero. Saltando insumo '{data['nombre']}'."))
            except KeyError:
                 self.stdout.write(self.style.ERROR(f"ERROR: La unidad '{data['unidad_medida_key']}' no fue definida en la lista de unidades. Saltando insumo '{data['nombre']}'."))


        if insumos_creados > 0:
            self.stdout.write(self.style.SUCCESS(f"\n¡Se crearon {insumos_creados} nuevos insumos!"))
        else:
            self.stdout.write(self.style.WARNING("\nNo se crearon insumos nuevos, todos ya existían."))

        self.stdout.write(self.style.SUCCESS("Carga de insumos finalizada."))