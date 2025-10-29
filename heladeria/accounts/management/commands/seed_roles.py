# accounts/management/commands/seed_perfiles.py
from django.core.management.base import BaseCommand
from accounts.models import UserPerfil

class Command(BaseCommand):
    help = "Crea los perfiles base para el sistema."

    def handle(self, *args, **options):
        for nombre in ("admin", "encargado", "bodeguero"):
            obj, created = UserPerfil.objects.get_or_create(nombre=nombre)
            self.stdout.write(self.style.SUCCESS(f"{'✔' if created else '•'} Perfil '{obj.nombre}' listo"))
