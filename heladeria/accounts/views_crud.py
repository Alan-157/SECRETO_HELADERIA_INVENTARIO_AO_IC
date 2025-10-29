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

# --- CRUD de Usuarios ---
@login_required
@perfil_required(allow=("admin",), read_only=True)
def usuarios_list(request):
    # --- per_page (5/10/20) con sesión
    allowed_pp = {"5", "10", "20"}
    per_page = request.GET.get("per_page")
    if per_page in allowed_pp:
        request.session["per_page_usuarios"] = int(per_page)
    per_page = request.session.get("per_page_usuarios", 20)

    # --- búsqueda
    q = (request.GET.get("q") or "").strip()

    # --- orden (asc/desc) por nombre
    allowed_order = {"asc", "desc"}
    order = request.GET.get("order")
    if order in allowed_order:
        request.session["order_usuarios"] = order
    order = request.session.get("order_usuarios", "asc")

    ordering = "name" if order == "asc" else "-name"

    usuarios_qs = (
        UsuarioApp.objects
        .select_related("active_asignacion__perfil")
        .filter(
            Q(name__icontains=q) |
            Q(email__icontains=q) |
            Q(active_asignacion__perfil__nombre__icontains=q)
        )
        .order_by(ordering, "id")  # desempate estable
    )

    paginator = Paginator(usuarios_qs, per_page)
    page_number = request.GET.get("page")
    usuarios = paginator.get_page(page_number)

    read_only = not (request.user.is_superuser or user_has_role(request.user, "admin"))

    # --- Respuesta AJAX: devolver solo el fragmento (tabla + paginación)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            "accounts/partials/usuarios_results.html",
            {
                "usuarios": usuarios,
                "read_only": read_only,
                "per_page": per_page,
                "q": q,
                "order": order,
                "request": request,  # para preservar GET en links
            },
            request=request,
        )
        return JsonResponse({"html": html})

    # --- Respuesta normal
    return render(
        request,
        "accounts/usuarios_list.html",
        {
            "usuarios": usuarios,
            "read_only": read_only,
            "per_page": per_page,
            "q": q,
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
            messages.success(request, "✅ Usuario creado correctamente.")
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
        messages.success(request, "📝 Usuario actualizado correctamente.")
        return redirect("accounts:usuarios_list")
    return render(request, "accounts/usuarios_form.html", {"form": form, "titulo": "Editar Usuario"})

@login_required
@perfil_required(allow=("admin",))
def usuarios_delete(request, pk):
    user = get_object_or_404(UsuarioApp, pk=pk)
    if request.method == "POST":
        user.delete()
        messages.success(request, "🗑️ Usuario eliminado correctamente.")
        return redirect("accounts:usuarios_list")
    return render(request, "accounts/usuarios_confirm_delete.html", {"user": user})


# --- CRUD de Perfiles ---
@login_required
@perfil_required(allow=("admin",), read_only=True)
def perfiles_list(request):
    # --- per_page (5/10/20) con sesión
    allowed_pp = {"5", "10", "20"}
    per_page = request.GET.get("per_page")
    if per_page in allowed_pp:
        request.session["per_page_perfiles"] = int(per_page)
    per_page = request.session.get("per_page_perfiles", 20)

    # --- búsqueda y orden
    q = (request.GET.get("q") or "").strip()
    allowed_order = {"asc", "desc"}
    order = request.GET.get("order")
    if order in allowed_order:
        request.session["order_perfiles"] = order
    order = request.session.get("order_perfiles", "asc")
    ordering = "nombre" if order == "asc" else "-nombre"

    perfiles_qs = UserPerfil.objects.filter(nombre__icontains=q).order_by(ordering, "id")

    paginator = Paginator(perfiles_qs, per_page)
    page_number = request.GET.get("page")
    perfiles = paginator.get_page(page_number)

    read_only = not (request.user.is_superuser or user_has_role(request.user, "admin"))

    # --- Respuesta AJAX (devuelve solo el fragmento HTML)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            "accounts/partials/perfiles_results.html",
            {
                "perfiles": perfiles,
                "per_page": per_page,
                "q": q,
                "order": order,
                "read_only": read_only,
                "request": request,
            },
            request=request,
        )
        return JsonResponse({"html": html})

    # --- Respuesta normal
    return render(
        request,
        "accounts/perfiles_list.html",
        {
            "perfiles": perfiles,
            "read_only": read_only,
            "per_page": per_page,
            "q": q,
            "order": order,
        },
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
