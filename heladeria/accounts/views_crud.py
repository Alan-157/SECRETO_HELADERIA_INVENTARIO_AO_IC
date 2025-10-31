from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UsuarioApp, UserPerfil
from .forms import UsuarioCreateForm, UsuarioUpdateForm
from .decorators import perfil_required
from django.core.paginator import Paginator
from accounts.services import user_has_role 
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.db.models import Q
from functools import reduce
import operator


# --- Función genérica para listas con filtros, orden y paginación ---
def list_with_filters(
    request,
    base_qs,
    *,
    search_fields=None,          # lista de campos para icontains (p.ej. ["name", "email", "active_asignacion__perfil__nombre"])
    order_field=None,            # campo base para ordenar asc/desc (p.ej. "name" o "nombre")
    session_prefix="",           # prefijo para claves de sesión (p.ej. "usuarios" o "perfiles")
    context_key="",              # nombre del PageObj en contexto (p.ej. "usuarios" o "perfiles")
    full_template="",            # template completo (p.ej. "accounts/usuarios_list.html")
    partial_template="",         # template parcial (p.ej. "accounts/partials/usuarios_results.html")
    default_per_page=20,         # 5/10/20 permitido
    default_order="asc",         # "asc" o "desc"
    tie_break="id",              # desempate estable
    extra_context=None,          # dict extra opcional
):
    extra_context = extra_context or {}

    # --- per_page (5/10/20) con sesión por lista ---
    allowed_pp = {"5", "10", "20"}
    per_page = request.GET.get("per_page")
    if per_page in allowed_pp:
        request.session[f"per_page_{session_prefix}"] = int(per_page)
    per_page = request.session.get(f"per_page_{session_prefix}", default_per_page)

    # --- búsqueda ---
    q = (request.GET.get("q") or "").strip()

    if search_fields:
        # Construye OR dinámico de Q(...) para los campos que existan en el modelo
        # (si algún campo no existe en el QS/model, simplemente no se agregará)
        q_objs = []
        for f in search_fields:
            try:
                # Probar acceso vía values() evita fallar por campo inexistente
                base_qs.model._meta.get_field(f.split("__")[0])  # validación simple de primer tramo
                q_objs.append(Q(**{f"{f}__icontains": q}))
            except Exception:
                # Si el primer tramo no es field directo (FK anidada), igual intentamos usarlo
                q_objs.append(Q(**{f"{f}__icontains": q}))
        if q:
            base_qs = base_qs.filter(reduce(operator.or_, q_objs))

    # --- orden ---
    allowed_order = {"asc", "desc"}
    order = request.GET.get("order")
    if order in allowed_order:
        request.session[f"order_{session_prefix}"] = order
    order = request.session.get(f"order_{session_prefix}", default_order)

    if order_field:
        ordering = order_field if order == "asc" else f"-{order_field}"
        base_qs = base_qs.order_by(ordering, tie_break)
    else:
        # Si no hay campo de orden, mantenemos el QS (pero con desempate para determinismo)
        base_qs = base_qs.order_by(tie_break)

    # --- paginación ---
    paginator = Paginator(base_qs, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # --- armar contexto común ---
    context = {
        context_key: page_obj,
        "per_page": per_page,
        "q": q,
        "order": order,
        **extra_context,
        "request": request,  # necesario para preservar GET en links dentro del partial
    }

    # --- respuesta AJAX (solo fragmento) ---
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(partial_template, context, request=request)
        return JsonResponse({"html": html})

    # --- respuesta normal (página completa) ---
    return render(request, full_template, context)

# --- CRUD de Usuarios ---
@login_required
@perfil_required(allow=("admin",))
def usuarios_list(request):
    qs = UsuarioApp.objects.select_related("active_asignacion__perfil")
    read_only = not (request.user.is_superuser or user_has_role(request.user, "admin"))

    # --- Campo de orden (sort) ---
    allowed_sort = {"name", "email"}
    sort = request.GET.get("sort")
    if sort in allowed_sort:
        request.session["sort_usuarios"] = sort
    sort = request.session.get("sort_usuarios", "name")

    # --- Dirección de orden (order) ---
    allowed_order = {"asc", "desc"}
    order = request.GET.get("order")
    if order in allowed_order:
        request.session["order_usuarios"] = order
    order = request.session.get("order_usuarios", "asc")

    # --- Llamada al helper ---
    return list_with_filters(
        request,
        qs,
        search_fields=["name", "email", "active_asignacion__perfil__nombre"],
        order_field=sort,  # ← aquí aplicamos el campo dinámico
        session_prefix="usuarios",
        context_key="usuarios",
        full_template="accounts/usuarios_list.html",
        partial_template="accounts/partials/usuarios_results.html",
        default_per_page=20,
        default_order=order,  # ← dirección dinámica
        tie_break="id",
        extra_context={
            "read_only": read_only,
            "sort": sort,
            "order": order,
        },
    )

@login_required
@perfil_required(allow=("admin",))
def usuarios_create(request):
    if request.method == "POST":
        form = UsuarioCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, " Usuario creado correctamente.")
            return redirect("accounts:usuarios_list")
    else:
        form = UsuarioCreateForm()
    return render(request, "accounts/usuarios_form.html", {"form": form, "titulo": "Nuevo Usuario"})

@login_required
@perfil_required(allow=("admin",))
def usuarios_update(request, pk):
    user = get_object_or_404(UsuarioApp, pk=pk)
    form = UsuarioUpdateForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, " Usuario actualizado correctamente.")
        return redirect("accounts:usuarios_list")
    return render(request, "accounts/usuarios_form.html", {"form": form, "titulo": "Editar Usuario"})

@login_required
@perfil_required(allow=("admin",))
def usuarios_delete(request, pk):
    user = get_object_or_404(UsuarioApp, pk=pk)
    if request.method == "POST":
        user.delete()
        messages.success(request, " Usuario eliminado correctamente.")
        return redirect("accounts:usuarios_list")
    return render(request, "accounts/usuarios_confirm_delete.html", {"user": user})


# --- CRUD de Perfiles ---
@login_required
@perfil_required(allow=("admin",))
def perfiles_list(request):
    qs = UserPerfil.objects.all()
    read_only = not (request.user.is_superuser or user_has_role(request.user, "admin"))

    return list_with_filters(
        request,
        qs,
        search_fields=["nombre"],        
        order_field="nombre",
        session_prefix="perfiles",
        context_key="perfiles",
        full_template="accounts/perfiles_list.html",
        partial_template="accounts/partials/perfiles_results.html",
        default_per_page=20,
        default_order="asc",
        tie_break="id",
        extra_context={"read_only": read_only},
    )

@login_required
@perfil_required(allow=("admin",))
def perfiles_create(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        if nombre:
            UserPerfil.objects.create(nombre=nombre)
            messages.success(request, "✅ Perfil creado correctamente.")
            return redirect("accounts:perfiles_list")
        else:
            messages.error(request, "⚠️ Debe ingresar un nombre.")
    return render(request, "accounts/perfiles_form.html", {"titulo": "Nuevo Perfil"})

@login_required
@perfil_required(allow=("admin",))
def perfiles_update(request, pk):
    perfil = get_object_or_404(UserPerfil, pk=pk)
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        perfil.nombre = nombre
        perfil.save()
        messages.success(request, "📝 Perfil actualizado correctamente.")
        return redirect("accounts:perfiles_list")
    return render(request, "accounts/perfiles_form.html", {"perfil": perfil, "titulo": "Editar Perfil"})

@login_required
@perfil_required(allow=("admin",))
def perfiles_delete(request, pk):
    perfil = get_object_or_404(UserPerfil, pk=pk)
    if request.method == "POST":
        perfil.delete()
        messages.success(request, "🗑️ Perfil eliminado correctamente.")
        return redirect("accounts:perfiles_list")
    return render(request, "accounts/perfiles_confirm_delete.html", {"perfil": perfil})
