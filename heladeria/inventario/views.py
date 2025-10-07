from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Insumo, Categoria
from .forms import InsumoForm

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


@login_required
def crear_insumo(request):
    """Maneja la creación de un nuevo insumo."""
    form = InsumoForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        form.save() # Guarda el nuevo registro
        return redirect('inventario:listar_insumos') # Redirige a la lista
        
    context = {
        'form': form,
        'titulo': 'Crear Nuevo Insumo'
    }
    return render(request, 'inventario/crear_insumo.html', context)


@login_required
def editar_insumo(request, insumo_id):
    """Maneja la edición de un insumo existente."""
    # Obtiene el objeto o lanza 404
    insumo = get_object_or_404(Insumo, id=insumo_id)
    form = InsumoForm(request.POST or None, instance=insumo) # Carga los datos del objeto
    
    if request.method == 'POST' and form.is_valid():
        form.save() # Actualiza el registro
        return redirect('inventario:listar_insumos')
        
    context = {
        'form': form,
        'titulo': f'Editar Insumo: {insumo.nombre}'
    }
    return render(request, 'inventario/editar_insumo.html', context)
