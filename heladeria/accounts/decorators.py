# accounts/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def perfil_required(allow=("admin",), read_only=False):
    def wrap(view):
        @wraps(view)
        def _inner(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Debes iniciar sesión.")
                return redirect("accounts:login")
            asg = getattr(request.user, "active_asignacion", None)
            perfil = (getattr(asg, "perfil", None) and asg.perfil.nombre or "").lower()
            # superusuario siempre puede
            if request.user.is_superuser:
                return view(request, *args, **kwargs)
            # acceso FULL
            if perfil in [p.lower() for p in allow]:
                return view(request, *args, **kwargs)
            # solo vista
            if read_only and perfil == "encargado":
                return view(request, *args, **kwargs)
            messages.error(request, "No tienes permisos para esta sección.")
            return redirect("dashboard")
        return _inner
    return wrap
