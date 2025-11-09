# accounts/management/commands/seed_encargado.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import UserPerfil, UserPerfilAsignacion

class Command(BaseCommand):
    help = "Crea usuario Encargado (inventario completo, sin usuarios)."

    def handle(self, *args, **options):
        User = get_user_model()
        perfil, _ = UserPerfil.objects.get_or_create(nombre="encargado")

        user, created = User.objects.get_or_create(
            email="encargado@local.cl",
            defaults={"name": "Encargado", "is_staff": True, "is_superuser": False, "is_active": True, "phone":"999999998"},
        )
        if created:
            user.set_password("Encargado1234")
            user.save()

        UserPerfilAsignacion.objects.filter(user=user, ended_at__isnull=True).update(ended_at=timezone.now())
        asg = UserPerfilAsignacion.objects.create(user=user, perfil=perfil)
        user.active_asignacion = asg
        user.save(update_fields=["active_asignacion"])

        self.stdout.write(self.style.SUCCESS("✅ encargado@local.cl / Encargado1234 listo"))
