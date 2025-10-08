# accounts/management/commands/seed_roles.py
from django.core.management.base import BaseCommand
from accounts.models import Rol

class Command(BaseCommand):
    help = "Crea los roles base para el sistema."

    def handle(self, *args, **options):
        roles = ["Administrador", "Encargado", "Bodeguero"]
        for r in roles:
            rol, created = Rol.objects.get_or_create(nombre=r, defaults={"is_active": True})
            if created:
                self.stdout.write(self.style.SUCCESS(f"✔ Rol '{rol.nombre}' creado"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠ Rol '{rol.nombre}' ya existe"))
        self.stdout.write(self.style.SUCCESS("✅ Todos los roles base verificados."))
