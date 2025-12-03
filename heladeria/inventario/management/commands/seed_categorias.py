from django.core.management.base import BaseCommand
from inventario.models import Categoria

class Command(BaseCommand):
    help = "Crea o actualiza el catálogo inicial de categorías de insumos."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando la carga de categorías..."))

        # Lista ampliada de categorías para la heladería
        categorias = [
            ("Lácteos", "Productos derivados de la leche como leche, crema, etc."),
            ("Frutas Frescas", "Frutas frescas de temporada para preparación."),
            ("Frutas Congeladas", "Pulpa y frutas congeladas para helados."),
            ("Bases y Neutros", "Bases pre-hechas, neutros y estabilizantes para helados."),
            ("Azúcares y Endulzantes", "Azúcar, glucosa, dextrosa y otros endulzantes."),
            ("Salsas y Toppings", "Salsas de chocolate, caramelo, manjar y toppings variados."),
            ("Frutos Secos", "Nueces, almendras, pistachos y otros frutos secos."),
            ("Chocolates y Confites", "Chips de chocolate, cacao en polvo, grageas y confites."),
            ("Saborizantes y Esencias", "Vainilla, pastas de sabor y esencias concentradas."),
            ("Envases y Descartables", "Conos, vasos, cucharitas, servilletas y envases para llevar."),
            ("Productos de Cafetería", "Café en grano, té, leche para café, etc."),
        ]

        categorias_creadas = 0
        for nombre, descripcion in categorias:
            # Usamos defaults para no sobreescribir la descripción si la categoría ya existe
            categoria, creada = Categoria.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': descripcion}
            )
            
            if creada:
                self.stdout.write(self.style.SUCCESS(f"Categoría creada: '{nombre}'"))
                categorias_creadas += 1
        
        if categorias_creadas > 0:
            self.stdout.write(self.style.SUCCESS(f"\n¡Se crearon {categorias_creadas} nuevas categorías!"))
        else:
            self.stdout.write(self.style.WARNING("\nNo se crearon categorías nuevas, todas ya existían."))

        self.stdout.write(self.style.SUCCESS("Carga de categorías finalizada."))
