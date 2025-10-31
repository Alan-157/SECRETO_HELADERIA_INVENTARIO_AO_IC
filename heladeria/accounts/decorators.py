# accounts/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

def perfil_required(allow=(), readonly_for=()):
    """
    - allow: roles con acceso total
    - readonly_for: roles con acceso SOLO LECTURA (métodos seguros)
    - superuser siempre pasa
    """
    allow = tuple(r.lower() for r in allow)
    readonly_for = tuple(r.lower() for r in readonly_for)

    def deco(view):
        @wraps(view)
        def _inner(request, *args, **kwargs):
            u = request.user
            if not u.is_authenticated:
                return redirect("accounts:login")

            if u.is_superuser:
                return view(request, *args, **kwargs)

            rol = ""
            try:
                rol = (u.active_asignacion.perfil.nombre or "").lower()
            except Exception:
                pass

            if rol in allow:
                return view(request, *args, **kwargs)

            if rol in readonly_for and request.method in SAFE_METHODS:
                return view(request, *args, **kwargs)

            messages.error(request, "No tienes permisos para esta sección.")
            return redirect("dashboard")
        return _inner
    return deco