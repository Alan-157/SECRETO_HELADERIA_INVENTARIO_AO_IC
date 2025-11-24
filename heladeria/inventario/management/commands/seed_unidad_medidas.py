from django.core.management.base import BaseCommand
from inventario.models import UnidadMedida

class Command(BaseCommand):
    help = "Crea el catálogo inicial de unidades de medida."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando seed de unidades de medida..."))

        unidades = [
            ("KG", "Kilogramos"),
            ("GR", "Gramos"),
            ("LT", "Litros"),
            ("ML", "Mililitros"),
            ("UN", "Unidades"),
        ]

        creadas = 0
        for codigo, nombre in unidades:
            obj, created = UnidadMedida.objects.get_or_create(
                codigo=codigo,
                defaults={"nombre": nombre}
            )
            if created:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(f"Unidad creada: {codigo} - {nombre}"))
            else:
                self.stdout.write(self.style.WARNING(f"Unidad '{codigo}' ya existía."))

        self.stdout.write(self.style.SUCCESS(
            f"Seed unidades finalizada. {creadas} nuevas creadas."
        ))
