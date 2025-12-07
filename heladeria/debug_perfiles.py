#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'heladeria.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import UserPerfilAsignacion, UserPerfil

User = get_user_model()

# Buscar todos los usuarios con asignación activa
print("=== USUARIOS CON ASIGNACIÓN ===")
asignaciones = UserPerfilAsignacion.objects.filter(ended_at__isnull=True).select_related('user', 'perfil')
for asg in asignaciones:
    perfil_nombre = asg.perfil.nombre if asg.perfil else "SIN PERFIL"
    email = asg.user.email if hasattr(asg.user, 'email') else "N/A"
    print(f"Usuario: {email:30} | Perfil: {perfil_nombre}")

# Ver todos los perfiles disponibles
print("\n=== PERFILES DISPONIBLES ===")
for perf in UserPerfil.objects.all():
    print(f"  - {perf.nombre}")

# Probar la función user_has_role
print("\n=== TEST user_has_role ===")
from accounts.services import user_has_role

for user in User.objects.filter(active_asignacion__isnull=False):
    email = user.email if hasattr(user, 'email') else str(user)
    resultado = user_has_role(user, "Bodeguero")
    print(f"{email:30} - has_role('Bodeguero'): {resultado}")
