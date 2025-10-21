from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from urllib import request
from .models import Insumo, Categoria, Bodega, Entrada, Salida, OrdenInsumo, OrdenInsumoDetalle
from datetime import date
from django.contrib import messages
# ¡Importamos los nuevos formularios que crearemos!
from .forms import InsumoForm, EntradaForm, SalidaForm, OrdenInsumoDetalleFormSet, CategoriaForm
# ¡Añadimos Sum, Q y Coalesce para cálculos y búsquedas!
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from django.db import transaction

# --- Helper para roles (ya lo tienes) ---
def user_has_role(user, *roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # Obtenemos el nombre del rol de forma segura
    nombre_rol = (getattr(getattr(user, "rol", None), "nombre", "") or "").strip().lower()
    roles_norm = [r.strip().lower() for r in roles]
    return nombre_rol in roles_norm

# --- VISTAS DEL INVENTARIO ---

# --- 1. VISTA PRINCIPAL (DASHBOARD) ---
@login_required
def dashboard_view(request):
    """Muestra el dashboard con un resumen de la información del inventario."""
    total_insumos = Insumo.objects.filter(is_active=True).count()
    total_bodegas = Bodega.objects.filter(is_active=True).count()
    ordenes_pendientes = OrdenInsumo.objects.filter(estado='PENDIENTE').count()
    visitas = request.session.get('visitas', 0)
    request.session['visitas'] = visitas + 1
    # Obtenemos las 5 categorías más recientes
    categorias = Categoria.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    context = {
        'total_insumos': total_insumos,
        'total_bodegas': total_bodegas,
        'ordenes_pendientes': ordenes_pendientes,
        'categorias': categorias,
        'visitas':visitas,
    }
    return render(request, 'dashboard.html', context)

# --- 2. CRUD DE INSUMOS ---
@login_required
def listar_insumos(request):
    visitas_i = request.session.get('visitas_i', 0)
    request.session['visitas_i'] = visitas_i + 1
    """Muestra una lista de todos los insumos con su stock actual y filtros."""
    query = request.GET.get('q')
    insumos = Insumo.objects.filter(is_active=True).annotate(
        stock_actual=Coalesce(Sum('lotes__cantidad_actual'), 0, output_field=DecimalField())
    ).select_related('categoria').order_by('nombre')

    if query:
        insumos = insumos.filter(
            Q(nombre__icontains=query) |
            Q(categoria__nombre__icontains=query)
        )

    context = {
        'insumos': insumos,
        'titulo': 'Listado de Insumos',
        'visitas_i':visitas_i
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

"""@login_required ESTE ES EL ANTIGUO BOTON DE ELIMINAR
def eliminar_insumo2(request, insumo_id):
    #Maneja la lógica para eliminar (desactivar) un insumo.
    if not user_has_role(request.user, "Administrador"):
        messages.error(request, "No tienes permisos para eliminar insumos.")
        return redirect('inventario:listar_insumos')

    insumo = get_object_or_404(Insumo, id=insumo_id)
    if request.method == 'POST':
        insumo.is_active = False
        insumo.save()
        messages.success(request, f"El insumo '{insumo.nombre}' ha sido eliminado.")
        return redirect('inventario:listar_insumos')

    context = {'insumo': insumo}
    return render(request, 'inventario/eliminar_insumo_confirm.html', context)"""

@login_required
@require_POST #NUEVO BOTON DE ELIMINAR (HECHO POR EL PROFE)
def eliminar_insumo(request, insumo_id):
    """
    Elimina una zona y responde JSON para que el frontend actualice la UI sin recargar.
    """
    # Verifica que la petición sea AJAX
    if not request.headers.get("x-requested-with") == "XMLHttpRequest":
        return HttpResponseBadRequest("Solo AJAX")
    # Verifica permisos y autenticación con pk de zona
    insumo = get_object_or_404(Insumo, id=insumo_id)
    nombre = insumo.nombre
    #insumo.delete()
    insumo.is_active = False
    insumo.save()
    return JsonResponse({"ok": True, "message": f"El insumo '{nombre}' ha sido eliminado."})


# --- 3. CRUD DE CATEGORÍAS ---
@login_required
def listar_categorias(request):
    """Muestra una lista de todas las categorías con opción de búsqueda."""
    query = request.GET.get('q')
    categorias = Categoria.objects.filter(is_active=True).order_by('nombre')
    if query:
        categorias = categorias.filter(nombre__icontains=query)
    
    context = {'categorias': categorias, 'titulo': 'Gestión de Categorías'}
    return render(request, 'inventario/listar_categorias.html', context)

@login_required
def crear_categoria(request):
    visitas_c = request.session.get('visitas_c', 0)
    request.session[visitas_c] = visitas_c + 1
    """Permite crear una categoría solo a Administradores."""
    if not user_has_role(request.user, "Administrador"):
        messages.error(request, "No tienes permisos para crear categorías.")
        return redirect('inventario:listar_categorias')

    form = CategoriaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Categoría creada correctamente.")
        return redirect('inventario:listar_categorias')

    context = {'form': form, 'titulo': 'Crear Nueva Categoría',
            'visitas_c':visitas_c}
    return render(request, 'inventario/crear_categoria.html', context)

@login_required
def editar_categoria(request, categoria_id):
    """Permite editar una categoría solo a Administradores."""
    if not user_has_role(request.user, "Administrador"):
        messages.error(request, "No tienes permisos para editar categorías.")
        return redirect('inventario:listar_categorias')

    categoria = get_object_or_404(Categoria, id=categoria_id)
    form = CategoriaForm(request.POST or None, instance=categoria)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Categoría '{categoria.nombre}' actualizada.")
        return redirect('inventario:listar_categorias')

    context = {'form': form, 'titulo': f'Editar Categoría: {categoria.nombre}'}
    return render(request, 'inventario/editar_categoria.html', context)

@login_required
def eliminar_categoria(request, categoria_id):
    """Permite eliminar (desactivar) una categoría solo a Administradores."""
    if not user_has_role(request.user, "Administrador"):
        messages.error(request, "No tienes permisos para eliminar categorías.")
        return redirect('inventario:listar_categorias')

    categoria = get_object_or_404(Categoria, id=categoria_id)
    if request.method == 'POST':
        categoria.is_active = False
        categoria.save()
        messages.success(request, f"Categoría '{categoria.nombre}' eliminada.")
        return redirect('inventario:listar_categorias')

    context = {'categoria': categoria}
    return render(request, 'inventario/eliminar_categoria_confirm.html', context)


# --- 4. OTROS LISTADOS ---
@login_required
def listar_bodegas(request):
    """Muestra una lista de todas las bodegas con búsqueda."""
    query = request.GET.get('q')
    bodegas = Bodega.objects.filter(is_active=True).order_by('nombre')
    if query:
        bodegas = bodegas.filter(Q(nombre__icontains=query) | Q(direccion__icontains=query))

    context = {'bodegas': bodegas, 'titulo': 'Nuestras Bodegas'}
    return render(request, 'inventario/listar_bodegas.html', context)

@login_required
def listar_movimientos(request):
    """Muestra un historial de entradas y salidas."""
    query = request.GET.get('q')
    entradas = Entrada.objects.select_related('insumo').order_by('-fecha')
    salidas = Salida.objects.select_related('insumo').order_by('-fecha_generada')

    if query:
        entradas = entradas.filter(insumo__nombre__icontains=query)
        salidas = salidas.filter(insumo__nombre__icontains=query)

    context = {
        'entradas': entradas[:20], # Mostramos solo los últimos 20 para no sobrecargar
        'salidas': salidas[:20],
        'titulo': 'Historial de Movimientos'
    }
    return render(request, 'inventario/listar_movimientos.html', context)

@login_required
def listar_ordenes(request):
    """Muestra una lista de todas las órdenes de insumo."""
    query = request.GET.get('q')
    ordenes = OrdenInsumo.objects.prefetch_related('detalles__insumo').select_related('usuario').order_by('-fecha')
    
    if query:
        ordenes = ordenes.filter(
            Q(id__icontains=query) |
            Q(usuario__name__icontains=query) |
            Q(usuario__email__icontains=query) |
            Q(detalles__insumo__nombre__icontains=query)
        ).distinct()

    context = {'ordenes': ordenes, 'titulo': 'Órdenes de Insumo'}
    return render(request, 'inventario/listar_ordenes.html', context)


# --- 5. CREACIÓN DE MOVIMIENTOS Y ÓRDENES ---
@login_required
@transaction.atomic
def crear_entrada(request):
    """Permite registrar una entrada de stock a un lote."""
    if not user_has_role(request.user, "Administrador", "Encargado"):
        messages.error(request, "No tienes permisos para registrar entradas.")
        return redirect('inventario:listar_movimientos')
    
    if request.method == 'POST':
        form = EntradaForm(request.POST)
        if form.is_valid():
            # 👇 AÑADIMOS ESTA VALIDACIÓN DE FECHA
            fecha_movimiento = form.cleaned_data.get('fecha')
            if fecha_movimiento and fecha_movimiento < date.today():
                form.add_error(None, "La fecha de la entrada no puede ser anterior al día de hoy.")
            else:
                # Si la fecha es válida, procedemos a guardar
                entrada = form.save(commit=False)
                entrada.usuario = request.user
                entrada.save()
                
                lote = entrada.insumo_lote
                lote.cantidad_actual += entrada.cantidad
                lote.save()
                
                messages.success(request, f"Entrada de {entrada.cantidad} de '{entrada.insumo.nombre}' registrada.")
                return redirect('inventario:listar_movimientos')
    else:
        form = EntradaForm()
        
    context = {'form': form, 'titulo': 'Registrar Nueva Entrada de Insumo'}
    return render(request, 'inventario/crear_movimiento.html', context)


@login_required
@transaction.atomic
def crear_salida(request):
    """Permite registrar una salida de stock de un lote."""
    if not user_has_role(request.user, "Administrador", "Encargado"):
        messages.error(request, "No tienes permisos para registrar salidas.")
        return redirect('inventario:listar_movimientos')

    if request.method == 'POST':
        form = SalidaForm(request.POST)
        if form.is_valid():
            salida = form.save(commit=False)

            # 👇 AÑADIMOS ESTA VALIDACIÓN DE FECHA
            fecha_movimiento = form.cleaned_data.get('fecha_generada')
            if fecha_movimiento and fecha_movimiento < date.today():
                form.add_error(None, "La fecha de la salida no puede ser anterior al día de hoy.")
            else:
                salida.usuario = request.user
                lote = salida.insumo_lote
                
                if salida.cantidad > lote.cantidad_actual:
                    form.add_error('cantidad', f'No hay stock suficiente. Stock actual: {lote.cantidad_actual}')
                else:
                    salida.save()
                    lote.cantidad_actual -= salida.cantidad
                    lote.save()
                    messages.success(request, f"Salida de {salida.cantidad} de '{salida.insumo.nombre}' registrada.")
                    return redirect('inventario:listar_movimientos')
    else:
        form = SalidaForm()

    context = {'form': form, 'titulo': 'Registrar Nueva Salida de Insumo'}
    return render(request, 'inventario/crear_movimiento.html', context)

@login_required
@transaction.atomic
def crear_orden(request):
    """Permite crear una nueva orden de insumos con múltiples detalles."""
    if not user_has_role(request.user, "Administrador", "Encargado"):
        messages.error(request, "No tienes permisos para registrar salidas.")
        return redirect('inventario:listar_movimientos')

    if request.method == 'POST':
        formset = OrdenInsumoDetalleFormSet(request.POST)
        if formset.is_valid():
            # Creamos la orden principal
            orden = OrdenInsumo.objects.create(usuario=request.user, estado='PENDIENTE')
            
            # Guardamos los detalles (los formularios del formset)
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                    detalle = form.save(commit=False)
                    detalle.orden_insumo = orden
                    detalle.save()
            
            messages.success(request, f"Orden #{orden.id} creada exitosamente.")
            return redirect('inventario:listar_ordenes')
    else:
        formset = OrdenInsumoDetalleFormSet(queryset=OrdenInsumoDetalle.objects.none())

    context = {
        'formset': formset,
        'titulo': 'Crear Nueva Orden de Insumo'
    }
    return render(request, 'inventario/crear_orden.html', context)