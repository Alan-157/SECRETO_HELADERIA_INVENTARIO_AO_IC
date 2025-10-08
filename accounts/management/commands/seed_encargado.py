# accounts/management/commands/seed_encargado.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Rol, UserPerfil, UserPerfilAsignacion

class Command(BaseCommand):
    help = "Crea el usuario Encargado (acceso total a Inventario, sin acceso a usuarios)."

    def handle(self, *args, **options):
        User = get_user_model()

        rol, _ = Rol.objects.get_or_create(nombre="Encargado", defaults={"is_active": True})
        perfil, _ = UserPerfil.objects.get_or_create(nombre="Perfil Inventario", defaults={"is_active": True})

        user, created = User.objects.get_or_create(
            email="encargado@local.cl",
            defaults={
                "name": "Encargado Inventario",
                "rol": rol,
                "user_perfil": perfil,
                "is_staff": True,
                "is_superuser": False,
                "is_active": True,
            },
        )
        if created:
            user.set_password("Encargado1234")
            user.save()
            UserPerfilAsignacion.objects.create(user=user, perfil=perfil, activo=True)
            self.stdout.write(self.style.SUCCESS("✅ Usuario Encargado creado: encargado@local.cl / Encargado1234"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Encargado ya existente."))
