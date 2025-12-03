# accounts/management/commands/seed_bodeguero.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import UserPerfil, UserPerfilAsignacion
from django.core.files import File
import os
from django.conf import settings

class Command(BaseCommand):
    help = "Crea usuario Bodeguero (solo lectura de inventario)."

    def handle(self, *args, **options):
        User = get_user_model()
        perfil, _ = UserPerfil.objects.get_or_create(nombre="bodeguero")

        user, created = User.objects.get_or_create(
            email="bodeguero@local.cl",
            defaults={"name": "Bodeguero", "is_staff": True, "is_superuser": False, "is_active": True, "phone":"999999999"},
        )
        if created:
            user.set_password("Bodeguero1234")
            user.save()

            avatar_path = os.path.join(settings.MEDIA_ROOT, "users", "Alastor_Chuncho.jpg")
            if os.path.exists(avatar_path):
                with open(avatar_path, "rb") as img:
                    user.avatar.save("bodeguero.jpg", File(img), save=True)


        UserPerfilAsignacion.objects.filter(user=user, ended_at__isnull=True).update(ended_at=timezone.now())
        asg = UserPerfilAsignacion.objects.create(user=user, perfil=perfil)
        user.active_asignacion = asg
        user.save(update_fields=["active_asignacion"])

        self.stdout.write(self.style.SUCCESS("✅ bodeguero@local.cl / Bodeguero1234 listo"))
