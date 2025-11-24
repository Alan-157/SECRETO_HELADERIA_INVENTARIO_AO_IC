from django.core.management.base import BaseCommand
from inventario.models import Insumo, Categoria, UnidadMedida

class Command(BaseCommand):
    help = "Crea un catálogo inicial de insumos de prueba para la heladería."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de insumos de prueba..."))

        insumos_data = [
            # Lácteos
            {"nombre": "Leche Entera", "categoria_nombre": "Lácteos", "unidad_medida": "LT", "stock_minimo": 20, "stock_maximo": 100, "precio_unitario": 1200},
            {"nombre": "Crema de Leche (35%)", "categoria_nombre": "Lácteos", "unidad_medida": "LT", "stock_minimo": 10, "stock_maximo": 50, "precio_unitario": 4500},
            {"nombre": "Leche en Polvo", "categoria_nombre": "Lácteos", "unidad_medida": "KG", "stock_minimo": 5, "stock_maximo": 25, "precio_unitario": 8000},

            # Frutas Congeladas
            {"nombre": "Pulpa de Frutilla", "categoria_nombre": "Frutas Congeladas", "unidad_medida": "KG", "stock_minimo": 10, "stock_maximo": 80, "precio_unitario": 3500},
            {"nombre": "Pulpa de Mango", "categoria_nombre": "Frutas Congeladas", "unidad_medida": "KG", "stock_minimo": 10, "stock_maximo": 80, "precio_unitario": 4200},
            {"nombre": "Arándanos Congelados", "categoria_nombre": "Frutas Congeladas", "unidad_medida": "KG", "stock_minimo": 5, "stock_maximo": 40, "precio_unitario": 4000},

            # Azúcares y Endulzantes
            {"nombre": "Azúcar Granulada", "categoria_nombre": "Azúcares y Endulzantes", "unidad_medida": "KG", "stock_minimo": 25, "stock_maximo": 150, "precio_unitario": 1300},
            {"nombre": "Glucosa", "categoria_nombre": "Azúcares y Endulzantes", "unidad_medida": "KG", "stock_minimo": 5, "stock_maximo": 20, "precio_unitario": 3000},
            {"nombre": "Dextrosa", "categoria_nombre": "Azúcares y Endulzantes", "unidad_medida": "KG", "stock_minimo": 5, "stock_maximo": 20, "precio_unitario": 3200},

            # Chocolates y Confites
            {"nombre": "Cacao Amargo en Polvo", "categoria_nombre": "Chocolates y Confites", "unidad_medida": "KG", "stock_minimo": 2, "stock_maximo": 15, "precio_unitario": 15000},
            {"nombre": "Cobertura de Chocolate 70%", "categoria_nombre": "Chocolates y Confites", "unidad_medida": "KG", "stock_minimo": 5, "stock_maximo": 30, "precio_unitario": 18000},
            {"nombre": "Chips de Chocolate", "categoria_nombre": "Chocolates y Confites", "unidad_medida": "KG", "stock_minimo": 3, "stock_maximo": 20, "precio_unitario": 9000},

            # Envases y Descartables
            {"nombre": "Conos de Galleta", "categoria_nombre": "Envases y Descartables", "unidad_medida": "UN", "stock_minimo": 100, "stock_maximo": 500, "precio_unitario": 150},
            {"nombre": "Vasos de Polipapel 4oz", "categoria_nombre": "Envases y Descartables", "unidad_medida": "UN", "stock_minimo": 200, "stock_maximo": 1000, "precio_unitario": 80},
            {"nombre": "Cucharitas de Helado", "categoria_nombre": "Envases y Descartables", "unidad_medida": "UN", "stock_minimo": 500, "stock_maximo": 2000, "precio_unitario": 30},
            
            # Frutos Secos
            {"nombre": "Nueces Mariposa", "categoria_nombre": "Frutos Secos", "unidad_medida": "KG", "stock_minimo": 2, "stock_maximo": 10, "precio_unitario": 12000},
            {"nombre": "Almendras Laminadas", "categoria_nombre": "Frutos Secos", "unidad_medida": "KG", "stock_minimo": 2, "stock_maximo": 10, "precio_unitario": 14000},
        ]

        insumos_creados = 0

        for data in insumos_data:
            categoria_nombre = data["categoria_nombre"]
            um_codigo = data["unidad_medida"]

            # --- Validar categoría ---
            try:
                categoria = Categoria.objects.get(nombre=categoria_nombre)
            except Categoria.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"ERROR: La categoría '{categoria_nombre}' no existe."))
                continue

            # --- Validar unidad de medida ---
            try:
                unidad = UnidadMedida.objects.get(codigo__iexact=um_codigo)
            except UnidadMedida.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"ERROR: La unidad '{um_codigo}' no existe. Ejecuta seed_unidades primero."))
                continue

            defaults = {
                "categoria": categoria,
                "unidad_medida": unidad,
                "stock_minimo": data["stock_minimo"],
                "stock_maximo": data["stock_maximo"],
                "precio_unitario": data["precio_unitario"],
            }

            insumo, creado = Insumo.objects.get_or_create(
                nombre=data["nombre"],
                defaults=defaults
            )

            if creado:
                self.stdout.write(self.style.SUCCESS(f"Insumo '{insumo.nombre}' creado."))
                insumos_creados += 1
            else:
                self.stdout.write(self.style.WARNING(f"Insumo '{insumo.nombre}' ya existe."))

        if insumos_creados > 0:
            self.stdout.write(self.style.SUCCESS(f"\n¡Se crearon {insumos_creados} nuevos insumos!"))
        else:
            self.stdout.write(self.style.WARNING("\nNo se crearon insumos nuevos."))

        self.stdout.write(self.style.SUCCESS("Carga de insumos finalizada."))
