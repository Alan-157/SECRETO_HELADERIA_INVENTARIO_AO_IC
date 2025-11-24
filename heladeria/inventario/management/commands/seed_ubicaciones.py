from django.core.management.base import BaseCommand
from inventario.models import Ubicacion

class Command(BaseCommand):
    """
    Seed de Ubicaciones reales (dirección física).
    Primero se ejecuta este seed, luego seed_bodegas.
    """
    help = "Crea/actualiza ubicaciones reales."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando seed de ubicaciones..."))

        ubicaciones_data = [
            {
                "nombre": "Sucursal La Serena Centro",
                "direccion": "Gabriel Gonzalez Videla 2777, La Serena",
                "tipo": "SUCURSAL",
            },
            {
                "nombre": "Sucursal Coquimbo",
                "direccion": "Pasaje Falso 1234, Coquimbo",
                "tipo": "SUCURSAL",
            },
            {
                "nombre": "Sucursal La Serena Playa",
                "direccion": "Avenida del Mar 5000, La Serena",
                "tipo": "SUCURSAL",
            },
        ]

        creadas = 0
        actualizadas = 0

        for info in ubicaciones_data:
            ubic, created = Ubicacion.objects.get_or_create(
                nombre=info["nombre"],
                defaults={
                    "direccion": info["direccion"],
                    "tipo": info.get("tipo"),
                    "is_active": True,
                }
            )

            if created:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(f"Ubicación creada: {ubic.nombre}"))
            else:
                changed = False
                if ubic.direccion != info["direccion"]:
                    ubic.direccion = info["direccion"]
                    changed = True
                if ubic.tipo != info.get("tipo"):
                    ubic.tipo = info.get("tipo")
                    changed = True
                if not ubic.is_active:
                    ubic.is_active = True
                    changed = True

                if changed:
                    ubic.save(update_fields=["direccion", "tipo", "is_active"])
                    actualizadas += 1
                    self.stdout.write(self.style.WARNING(f"Ubicación actualizada: {ubic.nombre}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Ubicación ya existía: {ubic.nombre}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nSeed ubicaciones listo: {creadas} creadas, {actualizadas} actualizadas."
        ))
