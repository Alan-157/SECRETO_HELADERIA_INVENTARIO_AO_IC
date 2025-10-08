# accounts/management/commands/seed_admin.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Rol, UserPerfil, UserPerfilAsignacion

class Command(BaseCommand):
    help = "Crea el usuario Administrador (superusuario con acceso completo)."

    def handle(self, *args, **options):
        User = get_user_model()

        rol, _ = Rol.objects.get_or_create(nombre="Administrador", defaults={"is_active": True})
        perfil, _ = UserPerfil.objects.get_or_create(nombre="Perfil Administrativo", defaults={"is_active": True})

        user, created = User.objects.get_or_create(
            email="admin@local.cl",
            defaults={
                "name": "Administrador General",
                "rol": rol,
                "user_perfil": perfil,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if created:
            user.set_password("Admin1234")
            user.save()
            UserPerfilAsignacion.objects.create(user=user, perfil=perfil, activo=True)
            self.stdout.write(self.style.SUCCESS("✅ Administrador creado: admin@local.cl / Admin1234"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Administrador ya existente."))
