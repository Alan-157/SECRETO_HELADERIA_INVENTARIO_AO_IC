from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UsuarioApp, UserPerfil
from .forms import UsuarioCreateForm, UsuarioUpdateForm
from .decorators import perfil_required
from django.core.paginator import Paginator
from accounts.services import user_has_role 

# --- CRUD de Usuarios ---
@login_required
@perfil_required(allow=("admin",), read_only=True)
def usuarios_list(request):
    usuarios_qs = UsuarioApp.objects.select_related("active_asignacion__perfil").order_by("email")
    paginator = Paginator(usuarios_qs, 20)
    page_number = request.GET.get("page")
    usuarios = paginator.get_page(page_number)
    read_only = not (request.user.is_superuser or user_has_role(request.user, "admin"))
    return render(request, "accounts/usuarios_list.html", {"usuarios": usuarios, "read_only": read_only})

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
    perfiles_qs = UserPerfil.objects.all().order_by("nombre")
    paginator = Paginator(perfiles_qs, 20)  # ← 20 por página
    page_number = request.GET.get("page")
    perfiles = paginator.get_page(page_number)
    read_only = not (request.user.is_superuser or user_has_role(request.user, "admin"))
    return render(request, "accounts/perfiles_list.html", {"perfiles": perfiles, "read_only": read_only})

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
