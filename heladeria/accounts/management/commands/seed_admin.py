# accounts/management/commands/seed_admin.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import UserPerfil, UserPerfilAsignacion

class Command(BaseCommand):
    help = "Crea el administrador + asignación de perfil admin (vigente)."

    def handle(self, *args, **options):
        User = get_user_model()
        perfil_admin, _ = UserPerfil.objects.get_or_create(nombre="admin")

        user, created = User.objects.get_or_create(
            email="admin@local.cl",
            defaults={"name": "Administrador", "is_staff": True, "is_superuser": False, "is_active": True},
        )
        if created:
            user.set_password("Admin1234")
            user.save()

        # Finaliza cualquier vigente previa (no usar None)
        UserPerfilAsignacion.objects.filter(user=user, ended_at__isnull=True).update(ended_at=timezone.now())

        # Crea nueva vigente y apunta puntero
        asg = UserPerfilAsignacion.objects.create(user=user, perfil=perfil_admin)  # ended_at=None -> vigente
        user.active_asignacion = asg
        user.save(update_fields=["active_asignacion"])

        self.stdout.write(self.style.SUCCESS("✅ admin@local.cl / Admin1234 listo"))
