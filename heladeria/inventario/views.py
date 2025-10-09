from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Insumo, Categoria,Bodega,OrdenInsumo, Entrada, Salida
from django.contrib import messages
from .forms import InsumoForm
from django.db.models import Q # <-- ¡IMPORTANTE! Añadimos Q para búsquedas complejas

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
@login_required
def dashboard_view(request):
    """Muestra el dashboard con las últimas 5 categorías añadidas."""
    # MODIFICACIÓN: Ordenamos por fecha de creación descendente y tomamos solo 5
    categorias_recientes = Categoria.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    context = {
        'categorias': categorias_recientes, # Le pasamos la lista limitada a la plantilla
    }
    return render(request, 'dashboard.html', context)

# --- CRUD DE INSUMOS ---
@login_required
def listar_insumos(request):
    """Muestra una lista de todos los insumos, con opción de búsqueda."""
    queryset = Insumo.objects.filter(is_active=True).select_related('categoria')
    
    query = request.GET.get('q')
    if query:
        queryset = queryset.filter(
            Q(nombre__icontains=query) |
            Q(categoria__nombre__icontains=query)
        ).distinct()

    insumos = queryset.order_by('nombre')
    
    context = {
        'insumos': insumos,
        'titulo': 'Listado de Insumos'
    }
    return render(request, 'inventario/listar_insumos.html', context)


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


@login_required
def eliminar_insumo(request, insumo_id):
    """
    Maneja la eliminación (borrado suave) de un insumo.
    Solo admite peticiones POST para mayor seguridad.
    """
    if not user_has_role(request.user, "Administrador"):
        messages.error(request, "Solo los administradores pueden eliminar insumos.")
        return redirect('inventario:listar_insumos')

    if request.method == 'POST':
        insumo = get_object_or_404(Insumo, id=insumo_id)
        insumo.is_active = False  # Borrado suave
        insumo.save()
        messages.success(request, f"El insumo '{insumo.nombre}' ha sido eliminado correctamente.")
    else:
        messages.error(request, "Acción no permitida.")
    
    return redirect('inventario:listar_insumos')


# --- VISTAS DE CONSULTA CON BÚSQUEDA ---

@login_required
def listar_bodegas(request):
    queryset = Bodega.objects.filter(is_active=True)
    
    query = request.GET.get('q')
    if query:
        queryset = queryset.filter(
            Q(nombre__icontains=query) |
            Q(direccion__icontains=query)
        )

    bodegas = queryset.order_by('nombre')
    context = {
        'bodegas': bodegas,
        'titulo': 'Nuestras Bodegas'
    }
    return render(request, 'inventario/listar_bodegas.html', context)

@login_required
def listar_movimientos(request):
    entradas_qs = Entrada.objects.select_related('insumo', 'usuario')
    salidas_qs = Salida.objects.select_related('insumo', 'usuario')

    query = request.GET.get('q')
    if query:
        entradas_qs = entradas_qs.filter(
            Q(insumo__nombre__icontains=query) |
            Q(usuario__name__icontains=query)
        )
        salidas_qs = salidas_qs.filter(
            Q(insumo__nombre__icontains=query) |
            Q(usuario__name__icontains=query)
        )
    
    context = {
        'entradas': entradas_qs.order_by('-fecha')[:50],
        'salidas': salidas_qs.order_by('-fecha_generada')[:50],
        'titulo': 'Historial de Movimientos'
    }
    return render(request, 'inventario/listar_movimientos.html', context)

@login_required
def listar_ordenes(request):
    queryset = OrdenInsumo.objects.select_related('usuario')

    query = request.GET.get('q')
    if query:
        search_filter = Q(usuario__name__icontains=query) | Q(estado__icontains=query)
        if query.isdigit():
            search_filter |= Q(id=query)
        
        queryset = queryset.filter(search_filter)

    ordenes = queryset.order_by('-fecha')
    context = {
        'ordenes': ordenes,
        'titulo': 'Historial de Órdenes de Insumo'
    }
    return render(request, 'inventario/listar_ordenes.html', context)
