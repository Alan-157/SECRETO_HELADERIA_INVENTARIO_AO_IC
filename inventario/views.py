from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Insumo, Categoria
from django.contrib import messages
from .forms import InsumoForm

# --- Helper para roles ---
def user_has_role(user, *roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    nombre = getattr(getattr(user, "rol", None), "nombre", "")
    return nombre in roles

# --- VISTAS DEL INVENTARIO ---

# --- 1. VISTA PRINCIPAL (DASHBOARD) ---
@login_required # <-- Protegida con login (Clase U1-2 C11)
def dashboard_view(request):
    """Muestra el dashboard, incluyendo datos de ejemplo como categorías."""
    # Consulta (Clase U1 C8)
    categorias = Categoria.objects.filter(is_active=True).order_by('nombre')
    
    context = {
        'categorias': categorias,
    }
    return render(request, 'dashboard.html', context)

@login_required
def listar_insumos(request):
    """Muestra una lista de todos los insumos."""
    # Uso de ORM (Consultas - Clase U1 C8) para listar todos y optimizar la carga de la FK (Categoria)
    insumos = Insumo.objects.filter(is_active=True).select_related('categoria').order_by('nombre')
    
    context = {
        'insumos': insumos,
        'titulo': 'Listado de Insumos'
    }
    return render(request, 'inventario/listar_insumos.html', context)

# --- BLOQUEADOS PARA BODEGUERO ---
@login_required
def crear_insumo(request):
    """Permite crear un insumo solo a Administrador o Encargado."""
    if not user_has_role(request.user, "Administrador", "Encargado"):
        messages.error(request, "No tienes permisos para crear insumos.")
        return redirect('inventario:listar_insumos')

    form = InsumoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Insumo creado correctamente.")
        return redirect('inventario:listar_insumos')

    context = {'form': form, 'titulo': 'Crear Nuevo Insumo'}
    return render(request, 'inventario/crear_insumo.html', context)

@login_required
def editar_insumo(request, insumo_id):
    """Permite editar un insumo solo a Administrador o Encargado."""
    if not user_has_role(request.user, "Administrador", "Encargado"):
        messages.error(request, "No tienes permisos para editar insumos.")
        return redirect('inventario:listar_insumos')

    insumo = get_object_or_404(Insumo, id=insumo_id)
    form = InsumoForm(request.POST or None, instance=insumo)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Insumo '{insumo.nombre}' actualizado correctamente.")
        return redirect('inventario:listar_insumos')

    context = {'form': form, 'titulo': f'Editar Insumo: {insumo.nombre}'}
    return render(request, 'inventario/editar_insumo.html', context)

