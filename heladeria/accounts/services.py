from django.utils import timezone
from .models import UserPerfilAsignacion

def activar_asignacion(user, perfil):
    # Finaliza la vigente (si existe)
    UserPerfilAsignacion.objects.filter(user=user, ended_at__isnull=True)\
        .update(ended_at=timezone.now())
    # Crea nueva
    asg = UserPerfilAsignacion.objects.create(user=user, perfil=perfil)
    # Actualiza puntero del usuario
    user.active_asignacion = asg
    user.save(update_fields=["active_asignacion"])
    return asg

def user_has_role(user, *roles):
    """True si el usuario es superuser o su perfil vigente está en la lista."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    name = (getattr(user, "role", "") or "").strip().lower()
    return name in {r.strip().lower() for r in roles}