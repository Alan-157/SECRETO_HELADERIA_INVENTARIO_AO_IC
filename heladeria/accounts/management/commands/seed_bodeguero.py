# accounts/management/commands/seed_bodeguero.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Rol, UserPerfil, UserPerfilAsignacion

class Command(BaseCommand):
    help = "Crea el usuario Bodeguero (solo lectura del Inventario)."

    def handle(self, *args, **options):
        User = get_user_model()

        rol, _ = Rol.objects.get_or_create(nombre="Bodeguero", defaults={"is_active": True})
        perfil, _ = UserPerfil.objects.get_or_create(nombre="Perfil Bodega", defaults={"is_active": True})

        user, created = User.objects.get_or_create(
            email="bodeguero@local.cl",
            defaults={
                "name": "Bodeguero General",
                "rol": rol,
                "user_perfil": perfil,
                "is_staff": True,
                "is_superuser": False,
                "is_active": True,
            },
        )
        if created:
            user.set_password("Bodeguero1234")
            user.save()
            UserPerfilAsignacion.objects.create(user=user, perfil=perfil, activo=True)
            self.stdout.write(self.style.SUCCESS("✅ Usuario Bodeguero creado: bodeguero@local.cl / Bodeguero1234"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Bodeguero ya existente."))
