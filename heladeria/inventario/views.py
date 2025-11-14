from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from accounts.decorators import perfil_required
from accounts.services import user_has_role
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q, DecimalField, Count, Min, F, Prefetch
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.forms import ModelForm, inlineformset_factory  
from django.views.decorators.http import require_POST
from accounts.services import user_has_role
from django.contrib.auth.decorators import login_required
from .models import (
    Insumo, Categoria, Bodega,
    Entrada, Salida, InsumoLote,
    OrdenInsumo, OrdenInsumoDetalle,
    ESTADO_ORDEN_CHOICES,              
)
from django.urls import reverse
from .forms import (
    InsumoForm, CategoriaForm,
    MovimientoLineaFormSet, BodegaForm,
    EntradaForm, SalidaForm, OrdenInsumoDetalleCreateFormSet, OrdenInsumoDetalleEditFormSet, 
    # =============================================================================
)
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, numbers, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, numbers
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from datetime import date
import csv
from django.http import HttpResponse

from functools import reduce
import operator
from django.db.models import Q
from django.template.loader import render_to_string

from inventario import models


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

# --- DASHBOARD ---
@login_required
def dashboard_view(request):
    total_insumos = Insumo.objects.filter(is_active=True).count()
    total_bodegas = Bodega.objects.filter(is_active=True).count()
    ordenes_pendientes = OrdenInsumo.objects.filter(estado='PENDIENTE').count()
    visitas = request.session.get('visitas', 0)
    request.session['visitas'] = visitas + 1
    categorias = Categoria.objects.filter(is_active=True).order_by('-created_at')[:5]

    context = {
        'total_insumos': total_insumos,
        'total_bodegas': total_bodegas,
        'ordenes_pendientes': ordenes_pendientes,
        'categorias': categorias,
        'visitas': visitas,
    }
    return render(request, 'dashboard.html', context)

# --- CRUD INSUMOS ---
@login_required
@perfil_required(
    allow=("administrador", "Encargado"),
    readonly_for=("Bodeguero",)            # ← bodeguero puede ver listado
)
def listar_insumos(request):
    qs = (
        Insumo.objects.filter(is_active=True)
        .annotate(stock_actual=Coalesce(Sum('lotes__cantidad_actual'), 0, output_field=DecimalField()))
        .select_related('categoria')
    )

    allowed_sort = {"nombre", "categoria", "stock", "unidad"}
    sort = request.GET.get("sort")
    if sort not in allowed_sort:
        sort = request.session.get("sort_insumos", "nombre")
    if sort not in allowed_sort:
        sort = "nombre"
    request.session["sort_insumos"] = sort

    sort_map = {
        "nombre": "nombre",
        "categoria": "categoria__nombre",
        "stock": "stock_actual",
        "unidad": "unidad_medida",
    }
    read_only = not (request.user.is_superuser or user_has_role(request.user, "Administrador", "Admin", "Encargado"))
    return list_with_filters(
        request,
        qs,
        search_fields=["nombre", "categoria__nombre", "unidad_medida"],
        order_field=sort_map[sort],
        session_prefix="insumos",
        context_key="insumos",
        full_template="inventario/listar_insumos.html",
        partial_template="inventario/partials/insumos_results.html",
        default_per_page=10,
        default_order="asc",
        tie_break="id",
        extra_context={"read_only": read_only,"titulo": "Listado de Insumos", "sort": sort},
    )

@login_required
@perfil_required(allow=("administrador", "Encargado"))
def crear_insumo(request):
    if not user_has_role(request.user, "Administrador", "Encargado"):
        messages.error(request, "No tienes permisos para crear insumos.")
        return redirect('inventario:listar_insumos')

    form = InsumoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "✅ Insumo creado correctamente.")
        return redirect('inventario:listar_insumos')

    return render(request, 'inventario/crear_insumo.html', {'form': form, 'titulo': 'Nuevo Insumo'})


@login_required
@perfil_required(allow=("administrador", "Encargado"))
def editar_insumo(request, insumo_id):
    if not user_has_role(request.user, "Administrador", "Encargado"):
        messages.error(request, "No tienes permisos para editar insumos.")
        return redirect('inventario:listar_insumos')

    insumo = get_object_or_404(Insumo, id=insumo_id)
    form = InsumoForm(request.POST or None, instance=insumo)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"El Insumo '{insumo.nombre}' fue actualizado.")
        return redirect('inventario:listar_insumos')

    return render(request, 'inventario/editar_insumo.html', {'form': form, 'titulo': f'Editar {insumo.nombre}'})


@login_required
@perfil_required(allow=("administrador", "Encargado"))
def eliminar_insumo(request, insumo_id):
    # 1. Obtener el Insumo y calcular el stock total de sus lotes activos
    from decimal import Decimal # Re-importación local por si acaso, aunque está global
    insumo = get_object_or_404(
        Insumo.objects.annotate(
            stock_total=Coalesce(
                Sum('lotes__cantidad_actual', filter=Q(lotes__is_active=True)), 
                Decimal("0.00"), 
                output_field=DecimalField()
            )
        ), 
        id=insumo_id
    )
    
    stock_actual = insumo.stock_total

    if request.method == "POST":
        # 2. Regla: NO se puede eliminar si el stock actual es mayor que cero.
        if stock_actual > Decimal("0.00"):
            messages.error(
                request, 
                f"🚫 No se puede eliminar el insumo '{insumo.nombre}' porque tiene stock activo ({stock_actual:.2f})."
            )
            return redirect("inventario:listar_insumos")
            
        # 3. Procede con la eliminación (desactivación) si el stock es cero
        insumo.is_active = False
        insumo.save(update_fields=["is_active"])
        messages.success(request, f"🗑️ El insumo '{insumo.nombre}' fue eliminado.")
        return redirect("inventario:listar_insumos")

    return render(
        request,
        "inventario/confirmar_eliminar.html",
        {"titulo": f"Eliminar Insumo «{insumo.nombre}»", "cancel_url": reverse("inventario:listar_insumos")}
    )

# --- exportar LOTES DE INSUMO ---
@login_required
@perfil_required(allow=("administrador", "Encargado", "Bodeguero"))
def exportar_lotes(request):
    """
    Exporta la lista de lotes de insumos a Excel o PDF, respetando filtros y orden.
    """
    # 1. Preparación del QuerySet (Similar a listar_insumos_lote)
    qs = (
        InsumoLote.objects.filter(is_active=True)
        .select_related("insumo", "bodega")
        .annotate(
            cant_act=Coalesce(F("cantidad_actual"), 0, output_field=DecimalField()),
            cant_ini=Coalesce(F("cantidad_inicial"), 0, output_field=DecimalField()),
        )
    )

    # Filtros de búsqueda (q)
    q = (request.GET.get("q") or "").strip()
    search_fields=["insumo__nombre", "bodega__nombre"]
    if q:
        q_objs = []
        for f in search_fields:
            q_objs.append(Q(**{f"{f}__icontains": q}))
        qs = qs.filter(reduce(operator.or_, q_objs))
    
    # Orden (sort y order)
    allowed_sort = {"insumo", "bodega", "fingreso", "fexpira", "cact", "cini"}
    sort = request.GET.get("sort")
    if sort not in allowed_sort:
        # Aquí no usamos request.session.get porque la exportación no debe depender
        # del estado de la sesión, sino de los parámetros de la URL.
        # Si no viene en GET, usamos un valor por defecto.
        sort = "insumo" 

    sort_map = {
        "insumo":   "insumo__nombre",
        "bodega":   "bodega__nombre",
        "fingreso":"fecha_ingreso",
        "fexpira": "fecha_expiracion",
        "cact":     "cant_act",
        "cini":     "cant_ini",
    }
    
    order = request.GET.get("order")
    allowed_order = {"asc", "desc"}
    if order not in allowed_order:
        order = "asc"
        
    tie_break = "id"
    ordering = sort_map[sort] if order == "asc" else f"-{sort_map[sort]}"
    qs = qs.order_by(ordering, tie_break)
    
    # Obtener todos los datos sin paginación
    lotes = qs.all()
    hoy = date.today()
    
    # 2. Lógica de Exportación
    exportar = request.GET.get("exportar")

    if exportar == "excel":
        # --- Exportar a Excel (openpyxl) ---
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="lotes_{hoy.isoformat()}.xlsx"'

        # Workbook y Worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Lotes de Insumos"

        # Título
        title = "Reporte de Lotes de Insumos"
        ws.merge_cells("A1:G1")
        ws.cell(row=1, column=1, value=title).font = Font(size=14, bold=True)
        ws.cell(row=1, column=1).alignment = Alignment(horizontal="center")
        
        headers = [
            "Insumo", "Bodega", "Fecha de Ingreso", 
            "Fecha de Expiración", "Cantidad Inicial", 
            "Cantidad Actual", "ID Lote"
        ]
        ws.append(headers)
        
        # Estilo para encabezados
        header_row = ws[2]
        header_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type="solid") # Verde claro
        for cell in header_row:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")
            cell.fill = header_fill

        # Datos
        row_num = 3
        for i, lote in enumerate(lotes):
            # Alternar color de fondo de las filas
            bg_color = 'E6E6FA' if i % 2 == 0 else 'FFFFFF' # Lavanda pálida / Blanco
            
            data = [
                lote.insumo.nombre,
                lote.bodega.nombre,
                lote.fecha_ingreso.strftime("%Y-%m-%d") if lote.fecha_ingreso else "",
                lote.fecha_expiracion.strftime("%Y-%m-%d") if lote.fecha_expiracion else "N/A",
                float(lote.cantidad_inicial),
                float(lote.cantidad_actual),
                lote.id
            ]
            ws.append(data)
            
            # Aplicar estilo de fondo y formato de números
            fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
            
            for col_idx in range(1, len(data) + 1):
                cell = ws.cell(row=row_num, column=col_idx)
                cell.fill = fill
                # Formato de números para las cantidades
                if col_idx in [5, 6]:
                    # Usamos FORMAT_NUMBER_COMMA_SEPARATED1 para formato con separador de miles y dos decimales
                    cell.number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1
            row_num += 1

        # Ajustar ancho de columnas
        for col in ws.columns:
            max_length = 0
            column = col[1].column_letter
            for cell in col:
                try: 
                    # Considerar encabezados y datos
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            # Añadir un margen (2 a 4 caracteres)
            adjusted_width = (max_length + 4)
            # Limitar el ancho máximo para columnas con poco contenido
            if column in ('C', 'D', 'E', 'F', 'G') and adjusted_width < 15:
                adjusted_width = 15
            ws.column_dimensions[column].width = adjusted_width
            
        # Guardar en buffer
        buffer = BytesIO()
        wb.save(buffer)
        response.write(buffer.getvalue())
        return response

    elif exportar == "pdf":
        # --- Exportar a PDF (reportlab) ---
        bio = BytesIO()
        doc = SimpleDocTemplate(
            bio,
            pagesize=landscape(A4), # Usar orientación horizontal
            leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20,
        )
        
        story = []
        styles = getSampleStyleSheet()

        # Título
        titulo = Paragraph("<b>Reporte de Lotes de Insumos</b>", styles["h1"])
        story.append(titulo)
        story.append(Spacer(1, 12))

        # Datos de la tabla
        data = [
            ["Insumo", "Bodega", "F. Ingreso", "F. Exp.", "Cant. Inicial", "Cant. Actual", "ID Lote"]
        ]
        
        for lote in lotes:
            data.append([
                lote.insumo.nombre,
                lote.bodega.nombre,
                lote.fecha_ingreso.strftime("%Y-%m-%d") if lote.fecha_ingreso else "",
                lote.fecha_expiracion.strftime("%Y-%m-%d") if lote.fecha_expiracion else "N/A",
                f"{lote.cantidad_inicial:,.2f}",
                f"{lote.cantidad_actual:,.2f}",
                str(lote.id)
            ])
            
        # Estilos
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A86E8')), # Azul para el encabezado
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            # Alineación del contenido (cantidades centradas, texto a la izquierda)
            ('ALIGN', (0, 1), (1, -1), 'LEFT'), # Insumo y Bodega a la izquierda
            ('ALIGN', (2, 1), (-2, -1), 'CENTER'), # Fechas y Cantidades al centro
            ('ALIGN', (-1, 1), (-1, -1), 'CENTER'), # ID Lote al centro
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            # Alternancia de filas (Blanco y Gris Claro)
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F5F5F5'), colors.white]),
        ]
        
        # Crear y añadir la tabla (ajuste de anchos en puntos para A4 horizontal)
        # Ancho total de A4 landscape es ~792. Usamos 752 para el margen de 20px
        # 220 (Insumo) + 120 (Bodega) + 80 (F. Ingreso) + 80 (F. Exp) + 100 (C. Ini) + 100 (C. Act) + 52 (ID) = 752
        t = Table(data, colWidths=[220, 120, 80, 80, 100, 100, 52])
        t.setStyle(TableStyle(table_style))
        story.append(t)
        
        # Construir el documento
        doc.build(story)
        pdf_value = bio.getvalue()
        bio.close()
        response = HttpResponse(pdf_value, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="lotes_{hoy.isoformat()}.pdf"'
        return response

    return HttpResponseBadRequest("Método de exportación no válido.")


# --- LISTAR LOTES DE INSUMO ---
@login_required
@perfil_required(allow=("administrador", "Encargado"), readonly_for=("Bodeguero",))
def listar_insumos_lote(request):
    """
    Listado de lotes de insumos con filtros, orden y paginación (AJAX-friendly).
    """
    qs = (
        InsumoLote.objects.filter(is_active=True)
        .select_related("insumo", "bodega")
        # por si en el futuro hay nulos, Coalesce evita fallas al ordenar/mostrar
        .annotate(
            cant_act=Coalesce(F("cantidad_actual"), 0, output_field=DecimalField()),
            cant_ini=Coalesce(F("cantidad_inicial"), 0, output_field=DecimalField()),
        )
    )

    # sort permitido
    allowed_sort = {"insumo", "bodega", "fingreso", "fexpira", "cact", "cini"}
    sort = request.GET.get("sort")
    if sort not in allowed_sort:
        sort = request.session.get("sort_lotes", "insumo")
    if sort not in allowed_sort:
        sort = "insumo"
    request.session["sort_lotes"] = sort

    sort_map = {
        "insumo":  "insumo__nombre",
        "bodega":  "bodega__nombre",
        "fingreso":"fecha_ingreso",
        "fexpira": "fecha_expiracion",
        "cact":    "cant_act",
        "cini":    "cant_ini",
    }

    read_only = not (request.user.is_superuser or user_has_role(request.user, "Administrador", "Admin", "Encargado"))

    return list_with_filters(
        request,
        qs,
        search_fields=["insumo__nombre", "bodega__nombre"],
        order_field=sort_map[sort],
        session_prefix="lotes",
        context_key="lotes",
        full_template="inventario/listar_insumo_lote.html",             
        partial_template="inventario/partials/insumo_lote_results.html",
        default_per_page=10,
        default_order="asc",
        tie_break="id",
        extra_context={
            "read_only": read_only,
            "titulo": "Lotes de Insumos",
            "sort": sort,
            "today": date.today(),
        },
    )

# --- CATEGORÍAS ---
@login_required
@perfil_required(allow=("administrador", "Encargado"), readonly_for=("Bodeguero",))
def listar_categorias(request):
    allowed_pp = {"5", "10", "20"}
    per_page_get = request.GET.get("per_page")
    if per_page_get in allowed_pp:
        request.session["per_page_categorias"] = int(per_page_get)
    per_page = request.session.get("per_page_categorias", 10)

    # 2) Persistir orden asc/desc en sesión (opcional, simétrico al resto)
    order_get = request.GET.get("order")
    if order_get in ("asc", "desc"):
        request.session["order_categorias"] = order_get
    order = request.session.get("order_categorias", "asc")

    # 3) Búsqueda (no se persiste por diseño, pero puedes hacerlo igual que per_page si lo deseas)
    q = (request.GET.get("q") or "").strip()

    categorias = Categoria.objects.all().order_by("nombre" if order == "asc" else "-nombre")
    if q:
        categorias = categorias.filter(
            Q(nombre__icontains=q) | Q(descripcion__icontains=q)
        )

    paginator = Paginator(categorias, per_page)
    page_number = request.GET.get("page")
    categorias_page = paginator.get_page(page_number)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(
            request,
            "inventario/partials/categorias_results.html",
            {"categorias": categorias_page, "per_page": per_page, "q": q, "order": order},
        )

    return render(
        request,
        "inventario/listar_categorias.html",
        {"categorias": categorias_page, "per_page": per_page, "q": q, "order": order},
    )

@login_required
@perfil_required(allow=("administrador", "Encargado"))
def crear_categoria(request):
    if not user_has_role(request.user, "administrador"):
        messages.error(request, "No tienes permisos.")
        return redirect('inventario:listar_categorias')

    form = CategoriaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "✅ Categoría creada.")
        return redirect('inventario:listar_categorias')

    return render(request, 'inventario/crear_categoria.html', {'form': form, 'titulo': 'Nueva Categoría'})

@login_required
@perfil_required(allow=("administrador", "Encargado"))
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
@perfil_required(allow=("administrador", "Encargado"))
def eliminar_categoria(request, categoria_id):
    # Solo Admin realmente elimina/desactiva
    if not user_has_role(request.user, "Administrador"):
        messages.error(request, "No tienes permisos para eliminar categorías.")
        return redirect("inventario:listar_categorias")

    categoria = get_object_or_404(Categoria, id=categoria_id)

    # Regla: si tiene insumos activos, no se puede eliminar
    tiene_insumos = Insumo.objects.filter(categoria=categoria, is_active=True).exists()
    if request.method == "POST":
        if tiene_insumos:
            messages.error(request, "No se puede eliminar la categoría: tiene insumos activos.")
            return redirect("inventario:listar_categorias")
        categoria.is_active = False
        categoria.save(update_fields=["is_active"])
        messages.success(request, f"Categoría '{categoria.nombre}' eliminada.")
        return redirect("inventario:listar_categorias")

    return render(
        request,
        "confirmar_eliminar.html",
        {"titulo": f"Eliminar Categoría «{categoria.nombre}»", "cancel_url": reverse("inventario:listar_categorias")}
    )

# --- MOVIMIENTOS UNIFICADOS ---
@login_required
@perfil_required(allow=("administrador", "Encargado"))
@transaction.atomic
def registrar_movimiento(request):
    """Registrar entradas/salidas (pueden o no pertenecer a una orden)."""
    if not user_has_role(request.user, "Administrador", "Encargado"):
        messages.error(request, "No tienes permisos para registrar movimientos.")
        return redirect('inventario:listar_movimientos')

    orden_obj = None
    # Si venimos desde una orden (?orden=ID)
    if request.method == "GET":
        orden_id = request.GET.get("orden")
        if orden_id:
            orden_obj = get_object_or_404(OrdenInsumo, id=orden_id)
    else:
        orden_id = request.POST.get("orden_id")
        if orden_id:
            orden_obj = get_object_or_404(OrdenInsumo, id=orden_id)

    if request.method == "POST":
        formset = MovimientoLineaFormSet(request.POST)
        if not formset.is_valid():
            messages.error(request, "Revisa los errores en el formulario.")
            return render(request, "inventario/registrar_movimiento.html", {
                "formset": formset,
                "titulo": "Registrar movimiento",
                "orden": orden_obj,
            })

        lineas = [f.cleaned_data for f in formset if getattr(f, "cleaned_data", None) and not f.cleaned_data.get("DELETE")]
        if not lineas:
            messages.warning(request, "No se ingresó ninguna línea válida.")
            return render(request, "inventario/registrar_movimiento.html", {
                "formset": formset,
                "titulo": "Registrar movimiento",
                "orden": orden_obj,
            })

        # Procesar líneas
        for cd in lineas:
            tipo = cd["tipo"]
            insumo = cd["insumo"]
            ubicacion = cd["ubicacion"]
            cantidad = cd["cantidad"]
            fecha = cd["fecha"]
            obs = cd.get("observaciones", "")
            crear_nuevo = cd.get("crear_nuevo_lote")
            lote = cd.get("insumo_lote")
            fecha_exp = cd.get("fecha_expiracion")

            detalle = None
            if orden_obj:
                # Crear un detalle si no existe
                detalle = OrdenInsumoDetalle.objects.create(
                    orden_insumo=orden_obj,
                    insumo=insumo,
                    cantidad_solicitada=cantidad,
                )

            if tipo == "ENTRADA":
                if crear_nuevo:
                    lote = InsumoLote.objects.create(
                        insumo=insumo,
                        bodega=ubicacion.bodega,
                        fecha_ingreso=fecha,
                        fecha_expiracion=fecha_exp,
                        cantidad_inicial=cantidad,
                        cantidad_actual=Decimal("0.00"), # <-- CORRECCIÓN DOBLE CONTEO
                        usuario=request.user,
                    )
                elif not lote:
                    messages.error(request, "Debes seleccionar o crear un lote para ENTRADA.")
                    raise transaction.TransactionManagementError("Entrada sin lote")

                entrada = Entrada.objects.create(
                    insumo=insumo, insumo_lote=lote, ubicacion=ubicacion,
                    cantidad=cantidad, fecha=fecha, usuario=request.user,
                    observaciones=obs, orden=orden_obj, detalle=detalle
                )
                lote.cantidad_actual += cantidad
                lote.save(update_fields=["cantidad_actual"])

                if detalle:
                    detalle.cantidad_atendida += cantidad
                    detalle.save(update_fields=["cantidad_atendida"])

            elif tipo == "SALIDA":
                # VALIDACIÓN: La SALIDA no debe tener fecha de expiración
                if fecha_exp:
                    messages.error(request, "Una SALIDA no puede registrar una fecha de expiración.")
                    raise transaction.TransactionManagementError("Salida con fecha de expiración")
                    
                if crear_nuevo:
                    messages.error(request, "No aplica 'Crear nuevo lote' para SALIDA.")
                    raise transaction.TransactionManagementError("Salida con crear_nuevo_lote")
                if not lote:
                    messages.error(request, "Para una SALIDA debes indicar el lote.")
                    raise transaction.TransactionManagementError("Salida sin lote")

                cant = min(cantidad, lote.cantidad_actual or Decimal("0"))
                Salida.objects.create(
                    insumo=insumo, insumo_lote=lote, ubicacion=ubicacion,
                    cantidad=cant, fecha_generada=fecha, usuario=request.user,
                    tipo="USO_PRODUCCION", observaciones=obs,
                    orden=orden_obj, detalle=detalle
                )
                lote.cantidad_actual -= cant # <-- Resta de stock (la lógica ya era correcta)
                lote.save(update_fields=["cantidad_actual"])

        if orden_obj:
            orden_obj.recalc_estado()

        messages.success(request, "Movimiento registrado correctamente.")
        return redirect('inventario:listar_movimientos')

    # Bloque GET, modificado para precargar insumo y tipo desde listar_insumos
    formset = MovimientoLineaFormSet()
    
    # Manejar precarga si vienen insumo_id y tipo (desde listar_insumos)
    if request.method == "GET":
        insumo_id = request.GET.get("insumo_id")
        tipo_movimiento = request.GET.get("tipo") # ENTRADA o SALIDA
        
        insumo_obj = None
        if insumo_id:
            try:
                insumo_obj = get_object_or_404(Insumo, id=insumo_id)
            except Exception:
                messages.warning(request, "El insumo solicitado no es válido.")

        # Si hay un insumo válido, precargamos el formset
        if insumo_obj and tipo_movimiento in ("ENTRADA", "SALIDA"):
            initial_data = [{
                'insumo': insumo_obj.id,
                'tipo': tipo_movimiento,
                # Dejamos cantidad y ubicación vacíos para que el usuario los complete
            }]
            formset = MovimientoLineaFormSet(initial=initial_data)

    return render(request, "inventario/registrar_movimiento.html", {
        "formset": formset,
        "titulo": "Registrar movimiento",
        "orden": orden_obj,
    })


# --- EDITAR / ELIMINAR ENTRADAS Y SALIDAS ---
@login_required
@perfil_required(allow=("administrador", "Encargado"))
@transaction.atomic
def editar_entrada(request, pk):
    entrada = get_object_or_404(Entrada, pk=pk)
    old_qty = Decimal(entrada.cantidad)
    lote = entrada.insumo_lote

    # REMOVIDA: from .forms import EntradaForm (ahora importada globalmente)
    form = EntradaForm(request.POST or None, instance=entrada)
    if request.method == "POST" and form.is_valid():
        nueva = Decimal(form.cleaned_data["cantidad"])
        delta = nueva - old_qty
        
        # Validación de stock futuro: Si la edición reduce la cantidad de stock por debajo de cero, falla.
        if lote.cantidad_actual + delta < 0:
            messages.error(request, f"Error al editar: La nueva cantidad excedería el stock del lote, resultando en stock negativo ({lote.cantidad_actual + delta:.2f}).")
            return render(request, "inventario/editar_movimiento.html", {"form": form, "titulo": "Editar Entrada"})

        lote.cantidad_actual += delta
        lote.save(update_fields=["cantidad_actual"])
        form.save()

        if entrada.detalle_id:
            det = entrada.detalle
            det.cantidad_atendida += delta
            if det.cantidad_atendida < 0:
                det.cantidad_atendida = 0
            det.save(update_fields=["cantidad_atendida"])
            entrada.orden.recalc_estado()

        messages.success(request, "Entrada modificada correctamente.")
        return redirect("inventario:listar_movimientos")

    return render(
    request,
    "inventario/editar_movimiento.html",
    {
        "form": form,
        "titulo": "Editar Entrada",
        "cancel_url": reverse("inventario:listar_movimientos"),
        "campo_fecha": form["fecha"],                 # ✅ BoundField seguro
        "errores_fecha": form["fecha"].errors,       # ✅ errores del campo
    },
)


@login_required
@perfil_required(allow=("administrador", "Encargado"))
@transaction.atomic
def eliminar_entrada(request, pk):
    entrada = get_object_or_404(Entrada, pk=pk)
    
    # Se añade validación para evitar stock negativo al eliminar la entrada
    lote = entrada.insumo_lote
    if lote.cantidad_actual - entrada.cantidad < 0:
        messages.error(request, f"Error: No se puede eliminar esta entrada ya que reduciría el stock del lote a un valor negativo ({lote.cantidad_actual - entrada.cantidad:.2f}).")
        return redirect("inventario:listar_movimientos") # Redirige con error

    if request.method == "POST":
        lote.cantidad_actual -= entrada.cantidad
        lote.save(update_fields=["cantidad_actual"])
        if entrada.detalle_id:
            det = entrada.detalle
            det.cantidad_atendida -= entrada.cantidad
            if det.cantidad_atendida < 0:
                det.cantidad_atendida = 0
            det.save(update_fields=["cantidad_atendida"])
            entrada.orden.recalc_estado()
        entrada.delete()
        messages.success(request, "Entrada eliminada correctamente.")
        return redirect("inventario:listar_movimientos")

    return render(request, "inventario/confirmar_eliminar.html", {"obj": entrada, "tipo": "entrada"})


@login_required
@perfil_required(allow=("administrador", "Encargado"))
@transaction.atomic
def editar_salida(request, pk):
    salida = get_object_or_404(Salida, pk=pk)
    old_qty = Decimal(salida.cantidad)
    lote = salida.insumo_lote

    # REMOVIDA: from .forms import SalidaForm (ahora importada globalmente)
    form = SalidaForm(request.POST or None, instance=salida)
    if request.method == "POST" and form.is_valid():
        nueva = Decimal(form.cleaned_data["cantidad"])
        delta = nueva - old_qty
        
        # Validación de stock: la diferencia entre la cantidad actual en lote y el delta
        # no debe ser menor a cero. Si delta es positivo, es una mayor salida, reduce stock.
        if lote.cantidad_actual - delta < 0:
            messages.error(request, f"Error al editar: La nueva salida excede el stock actual del lote, resultando en stock negativo ({lote.cantidad_actual - delta:.2f}).")
            return render(request, "inventario/editar_movimiento.html", {"form": form, "titulo": "Editar Salida"})

        lote.cantidad_actual -= delta
        lote.save(update_fields=["cantidad_actual"])
        form.save()
        messages.success(request, "Salida modificada correctamente.")
        return redirect("inventario:listar_movimientos")

    return render(
    request,
    "inventario/editar_movimiento.html",
    {
        "form": form,
        "titulo": "Editar Salida",
        "cancel_url": reverse("inventario:listar_movimientos"),
        "campo_fecha": form["fecha_generada"],        # ✅ BoundField seguro
        "errores_fecha": form["fecha_generada"].errors,
    },
)


@login_required
@perfil_required(allow=("administrador", "Encargado"))
@transaction.atomic
def eliminar_salida(request, pk):
    salida = get_object_or_404(Salida, pk=pk)
    if request.method == "POST":
        lote = salida.insumo_lote
        # Al eliminar una salida, se revierte el stock
        lote.cantidad_actual += salida.cantidad
        lote.save(update_fields=["cantidad_actual"])
        salida.delete()
        messages.success(request, "Salida eliminada correctamente.")
        return redirect("inventario:listar_movimientos")

    return render(request, "inventario/confirmar_eliminar.html", {"obj": salida, "tipo": "salida"})

# --- LISTAR MOVIMIENTOS (ENTRADAS Y SALIDAS) ---
@login_required
@perfil_required(allow=("administrador", "Encargado")) 
def listar_movimientos(request):
    titulo = "Movimientos de Inventario"
    q = (request.GET.get("q") or "").strip()

    entradas_qs = Entrada.objects.select_related("insumo", "insumo_lote", "ubicacion").order_by("-fecha")
    salidas_qs  = Salida.objects.select_related("insumo", "insumo_lote", "ubicacion").order_by("-fecha_generada")

    if q:
        entradas_qs = entradas_qs.filter(
            Q(insumo__nombre__icontains=q) | Q(ubicacion__nombre__icontains=q) | Q(observaciones__icontains=q)
        )
        salidas_qs = salidas_qs.filter(
            Q(insumo__nombre__icontains=q) | Q(ubicacion__nombre__icontains=q)
        )

    p_e = Paginator(entradas_qs, 20)
    p_s = Paginator(salidas_qs, 20)
    page_e = request.GET.get("page_e")
    page_s = request.GET.get("page_s")
    entradas = p_e.get_page(page_e)
    salidas  = p_s.get_page(page_s)

    can_manage = request.user.is_superuser or user_has_role(request.user, "administrador", "encargado")

    return render(request, "inventario/listar_movimientos.html", {
        "titulo": titulo,
        "entradas": entradas,
        "salidas": salidas,
        "can_manage": can_manage,
        "q": q,
    })



# --- Bodegas
@login_required
@perfil_required(
    allow=("administrador", "Encargado"),   # puede entrar Admin y Encargado
    readonly_for=("Encargado",)             # Encargado = solo lectura
)
def listar_bodegas(request):
    qs = Bodega.objects.filter(is_active=True)

    allowed_sort = {"nombre", "direccion"}
    sort = request.GET.get("sort")
    if sort not in allowed_sort:
        sort = request.session.get("sort_bodegas", "nombre")
    if sort not in allowed_sort:
        sort = "nombre"
    request.session["sort_bodegas"] = sort

    # NUEVO: dirección de orden
    order = request.GET.get("order")
    if order not in ("asc", "desc"):
        order = request.session.get("order_bodegas", "asc")
    if order not in ("asc", "desc"):
        order = "asc"
    request.session["order_bodegas"] = order

    sort_map = {
        "nombre": "nombre",
        "direccion": "direccion",
    }

    read_only = not (request.user.is_superuser or user_has_role(request.user, "Administrador"))

    return list_with_filters(
        request,
        qs,
        search_fields=["nombre", "direccion"],
        order_field=sort_map[sort],
        session_prefix="bodegas",
        context_key="bodegas",
        full_template="inventario/listar_bodegas.html",
        partial_template="inventario/partials/bodegas_results.html",
        default_per_page=10,
        default_order="asc",   # GET 'order' la sobreescribe
        tie_break="id",
        extra_context={
            "titulo": "Bodegas",
            "sort": sort,
            "order": order,     # <-- importante
            "read_only": read_only,
        },
    )

class OrdenForm(ModelForm):
    class Meta:
        model = OrdenInsumo
        fields = ("estado",)  # el usuario lo fijamos con request.user

DetalleFormSet = inlineformset_factory(
    OrdenInsumo,
    OrdenInsumoDetalle,
    fields=("insumo", "cantidad_solicitada"),
    extra=1,
    can_delete=True
)

@login_required
@perfil_required(allow=("administrador",))
def crear_bodega(request):
    form = BodegaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "✅ Bodega creada correctamente.")
        return redirect("inventario:listar_bodegas")
    return render(request, "inventario/bodega_form.html", {"form": form, "titulo": "Nueva Bodega"})

@login_required
@perfil_required(allow=("administrador",))
def editar_bodega(request, pk):
    obj = get_object_or_404(Bodega, pk=pk, is_active=True)
    form = BodegaForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "📝 Bodega actualizada.")
        return redirect("inventario:listar_bodegas")
    return render(request, "inventario/bodega_form.html", {"form": form, "titulo": f"Editar: {obj.nombre}"})

@login_required
@perfil_required(allow=("administrador",))
def eliminar_bodega(request, pk):
    bodega = get_object_or_404(Bodega, pk=pk)

    # Regla: si tiene lotes activos asociados, no se puede eliminar
    tiene_lotes = InsumoLote.objects.filter(bodega=bodega, is_active=True).exists()

    if request.method == "POST":
        if tiene_lotes:
            messages.error(request, "No se puede eliminar la bodega: tiene lotes activos asociados.")
            return redirect("inventario:listar_bodegas")
        bodega.is_active = False
        bodega.save(update_fields=["is_active"])
        messages.success(request, f"Bodega '{bodega.nombre}' eliminada.")
        return redirect("inventario:listar_bodegas")

    return render(
        request,
        "confirmar_eliminar.html",
        {"titulo": f"Eliminar Bodega «{bodega.nombre}»", "cancel_url": reverse("inventario:listar_bodegas")}
    )


# --- LISTAR ÓRDENES ---
ESTADOS_ORDEN = ("PENDIENTE", "EN_CURSO", "CERRADA", "CANCELADA")

@login_required
@perfil_required(allow=("administrador", "Encargado"), readonly_for=("Bodeguero",))
def listar_ordenes(request):
    """Lista las órdenes y permite actualizar su estado manualmente."""
    qs = OrdenInsumo.objects.all().select_related("usuario")

    # --- Búsqueda
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(usuario__name__icontains=q) | Q(usuario__email__icontains=q))

    # --- Filtro por estado
    estado_f = request.GET.get("estado")
    if estado_f in ESTADOS_ORDEN:
        qs = qs.filter(estado=estado_f)

    # --- Orden
    allowed_sort = {"id", "fecha", "estado", "usuario", "creado", "actualizado"}
    sort = request.GET.get("sort")
    if sort not in allowed_sort:
        sort = "fecha"

    sort_map = {
        "id": "id",
        "fecha": "fecha",
        "estado": "estado",
        "usuario": "usuario__name",
        "creado": "created_at",
        "actualizado": "updated_at",
    }

    read_only = not (request.user.is_superuser or user_has_role(request.user, "Administrador", "Admin", "Encargado"))

    return list_with_filters(
        request,
        qs,
        search_fields=[],
        order_field=sort_map[sort],
        session_prefix="ordenes",
        context_key="ordenes",
        full_template="inventario/listar_ordenes.html",
        partial_template="inventario/partials/ordenes_results.html",
        default_per_page=10,
        default_order="desc",
        tie_break="id",
        extra_context={
            "titulo": "Órdenes de Insumo",
            "q": q,
            "estado": estado_f,
            "sort": sort,
            "ESTADOS_ORDEN": ESTADOS_ORDEN,
            "read_only": read_only,   # ← IMPORTANTE
        },
    )

@login_required
@perfil_required(allow=("administrador", "Encargado"))
def orden_cambiar_estado(request, pk):
    orden = get_object_or_404(OrdenInsumo, pk=pk)
    nuevo = request.POST.get("estado")
    if nuevo not in ESTADOS_ORDEN:
        return HttpResponseBadRequest("Estado inválido")

    if orden.estado != nuevo:
        orden.estado = nuevo
        orden.save(update_fields=["estado", "updated_at"])
        messages.success(request, f"Estado de la orden #{orden.id} actualizado a {nuevo}.")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect("inventario:listar_ordenes")

@login_required
@perfil_required(allow=("administrador", "Encargado", "Bodeguero"))
@transaction.atomic
def crear_orden(request):
    orden = OrdenInsumo()  # instancia vacía (aún no guardada)
    formset = OrdenInsumoDetalleCreateFormSet(request.POST or None, instance=orden)

    if request.method == "POST":
        if formset.is_valid():
            orden.save()      # crea la orden
            formset.save()    # crea sus detalles
            messages.success(request, "Orden creada correctamente.")
            return redirect("inventario:listar_ordenes")
        messages.error(request, "Revisa los errores en los ítems de la orden.")

    return render(request, "inventario/crear_orden.html", {
        "titulo": "Crear orden",
        "formset": formset
    })

@login_required
@perfil_required(allow=("administrador", "Encargado"))
@transaction.atomic
def editar_orden(request, pk):
    orden = get_object_or_404(OrdenInsumo, pk=pk)
    formset = OrdenInsumoDetalleEditFormSet(request.POST or None, instance=orden)

    if request.method == "POST":
        if formset.is_valid():
            formset.save()  # crea/actualiza/elimina detalles según DELETE
            messages.success(request, "Orden actualizada.")
            return redirect("inventario:listar_ordenes")
        messages.error(request, "Revisa los errores en los ítems de la orden.")

    return render(request, "inventario/crear_orden.html", {
        "titulo": f"Editar orden #{orden.pk}",
        "formset": formset
    })

@login_required
@perfil_required(allow=("administrador", "Encargado"))
@transaction.atomic
def eliminar_orden(request, pk):
    orden = get_object_or_404(OrdenInsumo, pk=pk)
    if not user_has_role(request.user, "administrador", "Encargado"):
        messages.error(request, "No tienes permisos para eliminar órdenes.")
        return redirect("inventario:listar_ordenes")

    if request.method == "POST":
        orden.delete()
        messages.success(request, "Orden eliminada.")
        return redirect("inventario:listar_ordenes")

    # puedes reutilizar una plantilla genérica de confirmación
    return render(request, "inventario/confirmar_eliminar.html", {
        "titulo": f"Eliminar Orden #{orden.id}",
        "obj": orden,
        "tipo": "orden",
    })

# --- REPORTES ---
@login_required
@perfil_required(allow=("administrador", "Encargado"))
def reporte_disponibilidad(request):
    """
    Reporte de disponibilidad de insumos con:
    - Filtro por insumos (nombre) via checkboxes.
    - Flags de columnas a mostrar.
    - Lotes indentados por insumo (en HTML).
    Export: CSV/XLSX/PDF (respetan filtro de insumos).
    """
    hoy = date.today()

    # -------- flags de columnas (HTML) --------
    # por defecto mostramos: stock_total, precio_unitario, prox_vencimiento, lotes
    def _b(name, default=True):
        """
        Lee tanto 'show_*' (nuevo) como 'col_*' (legado) y devuelve bool.
        """
        raw = request.GET.get(name, None)
        if raw is None and name.startswith("show_"):
            raw = request.GET.get(name.replace("show_", "col_"), None)  # compat con col_*
        if raw is None:
            return default
        return str(raw).lower() in ("1", "true", "on", "yes")

    show_precio_unitario = _b("show_precio_unitario", True)
    show_stock_total     = _b("show_stock_total", True)
    show_prox_venc       = _b("show_prox_venc", True)
    show_lotes           = _b("show_lotes", True)
    show_categorias      = _b("show_categorias", False)
    show_precio_acum     = _b("show_precio_acum", False)

    # -------- selección por insumo (nombres) --------
    selected_insumos = request.GET.getlist("insumo")   # lista de nombres exactos

    # Base queryset de insumos (activos + categoría activa)
    insumos_base = (
        Insumo.objects.filter(is_active=True, categoria__is_active=True)
        .select_related("categoria")
    )

    # Si vienen seleccionados, filtramos por nombre (case-insensitive)
    if selected_insumos:
        insumos_base = insumos_base.filter(nombre__in=selected_insumos)

    # Prefetch de lotes activos para cada insumo (ordenados por fecha de expiración)
    lotes_qs = (InsumoLote.objects
                .filter(is_active=True)
                .select_related("bodega")
                .order_by("fecha_expiracion", "id"))

    # Anotaciones de stock total, #lotes con stock, prox venc
    insumos_qs = (
        insumos_base
        .annotate(
            stock_total=Coalesce(
                Sum(
                    "lotes__cantidad_actual",
                    filter=Q(lotes__is_active=True),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                0,
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            lotes_con_stock=Count(
                "lotes",
                filter=Q(lotes__is_active=True, lotes__cantidad_actual__gt=0),
                distinct=True,
            ),
            prox_vencimiento=Min(
                "lotes__fecha_expiracion",
                filter=Q(lotes__is_active=True, lotes__cantidad_actual__gt=0),
            ),
        )
        .prefetch_related(Prefetch("lotes", queryset=lotes_qs, to_attr="lotes_vis"))
        .order_by("categoria__nombre", "nombre")
    )

    # Dataset para checkboxes (todos los nombres disponibles, ordenados)
    all_insumo_names = list(
        Insumo.objects.filter(is_active=True, categoria__is_active=True)
        .order_by("nombre")
        .values_list("nombre", flat=True)
    )

    # Agrupado por categoría (para HTML)
    categorias = []
    cat_actual = None
    buffer = []
    for i in insumos_qs:
        if not cat_actual or i.categoria_id != cat_actual.id:
            if buffer:
                categorias.append({"categoria": cat_actual, "insumos": buffer})
                buffer = []
            cat_actual = i.categoria
        # cálculo auxiliar para HTML
        i.precio_acumulado = (i.stock_total or 0) * (i.precio_unitario or 0)
        buffer.append(i)
    if buffer:
        categorias.append({"categoria": cat_actual, "insumos": buffer})

    total_stock = sum((i.stock_total or 0) for i in insumos_qs)
    total_valor = sum(((i.stock_total or 0) * (i.precio_unitario or 0)) for i in insumos_qs)

    fmt = (request.GET.get("format") or "").lower()

    # ------- EXPORTS (respetan filtro de insumos, mantienen columnas clásicas) -------
    if fmt == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="reporte_disponibilidad_{hoy.isoformat()}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Categoría", "Insumo", "Unidad", "Precio Unitario", "Stock Total", "Lotes con Stock", "Próx. Vencimiento"])
        for bloque in categorias:
            for i in bloque["insumos"]:
                writer.writerow([
                    bloque["categoria"].nombre if bloque["categoria"] else "",
                    i.nombre,
                    i.unidad_medida,
                    f"{i.precio_unitario}",
                    f"{i.stock_total:.2f}",
                    i.lotes_con_stock,
                    i.prox_vencimiento.isoformat() if i.prox_vencimiento else "—",
                ])
        writer.writerow([])
        writer.writerow(["", "", "", "TOTALES", f"{Decimal(total_stock):.2f}", "", ""])
        writer.writerow(["", "", "", "VALOR TOTAL", f"{Decimal(total_valor):.2f}", "", ""])
        return response

    # ---------- XLSX ----------
    if fmt in ("xlsx", "excel"):
        wb = Workbook()
        ws = wb.active
        ws.title = "Disponibilidad"

        title = f"Reporte de Disponibilidad de Insumos - {hoy.isoformat()}"
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
        ws.cell(row=1, column=1, value=title).font = Font(size=14, bold=True)
        ws.cell(row=1, column=1).alignment = Alignment(horizontal="center")

        headers = ["Categoría", "Insumo", "Unidad", "Precio Unitario", "Stock Total", "Lotes con Stock", "Próx. Vencimiento"]
        ws.append(headers)
        for col in range(1, len(headers) + 1):
            ws.cell(row=2, column=col).font = Font(bold=True)
            ws.cell(row=2, column=col).alignment = Alignment(horizontal="center")

        for bloque in categorias:
            for i in bloque["insumos"]:
                ws.append([
                    bloque["categoria"].nombre,
                    i.nombre,
                    i.unidad_medida,
                    float(i.precio_unitario or 0),
                    float(i.stock_total or 0),
                    int(i.lotes_con_stock or 0),
                    (i.prox_vencimiento.isoformat() if i.prox_vencimiento else "—"),
                ])

        # Totales
        ws.append([])
        ws.append(["", "", "", "TOTALES", float(total_stock), "", ""])
        ws.append(["", "", "", "VALOR TOTAL", float(total_valor), "", ""])

        # Estilos y tamaños
        col_widths = [18, 30, 10, 16, 14, 16, 16]
        for idx, width in enumerate(col_widths, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = width

        # Formatos numéricos
        for row in ws.iter_rows(min_row=3, min_col=4, max_col=5, max_row=ws.max_row):
            for cell in row:
                if cell.column == 4:
                    cell.number_format = numbers.FORMAT_CURRENCY_USD_SIMPLE  # ajusta si deseas CLP personalizado
                elif cell.column == 5:
                    cell.number_format = "0.00"

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        response = HttpResponse(
            bio.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="reporte_disponibilidad_{hoy.isoformat()}.xlsx"'
        return response

    # ---------- PDF ----------
    if fmt == "pdf":
        bio = BytesIO()
        doc = SimpleDocTemplate(
            bio,
            pagesize=landscape(A4),
            leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20,
            title="Reporte de Disponibilidad de Insumos",
        )
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"Reporte de Disponibilidad de Insumos - {hoy.isoformat()}", styles["Title"]))
        story.append(Spacer(1, 8))

        table_head = ["Insumo", "Unidad", "Precio Unitario", "Stock Total", "Lotes con Stock", "Próx. Vencimiento"]

        for bloque in categorias:
            story.append(Paragraph(f"Categoría: {bloque['categoria'].nombre}", styles["Heading3"]))
            data = [table_head]
            for i in bloque["insumos"]:
                data.append([
                    i.nombre,
                    i.unidad_medida,
                    f"{(i.precio_unitario or 0):,.0f}",
                    f"{(i.stock_total or 0):,.2f}",
                    int(i.lotes_con_stock or 0),
                    (i.prox_vencimiento.strftime("%Y-%m-%d") if i.prox_vencimiento else "—"),
                ])
            t = Table(data, colWidths=[140, 60, 90, 90, 90, 110])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("TEXTCOLOR", (0,0), (-1,0), colors.black),
                ("ALIGN", (2,1), (-2,-1), "RIGHT"),
                ("ALIGN", (0,0), (-1,0), "CENTER"),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
            ]))
            story.append(t)
            story.append(Spacer(1, 10))

        # Totales
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Stock total:</b> {Decimal(total_stock):,.2f}", styles["Normal"]))
        story.append(Paragraph(f"<b>Precio total:</b> {Decimal(total_valor):,.0f}", styles["Normal"]))

        doc.build(story)
        pdf_value = bio.getvalue()
        bio.close()
        response = HttpResponse(pdf_value, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="reporte_disponibilidad_{hoy.isoformat()}.pdf"'
        return response

    # ---------- HTML (por defecto) ----------
    colspan_lotes = 2 \
    + int(show_categorias) \
    + int(show_precio_unitario) \
    + int(show_stock_total) \
    + int(show_prox_venc) \
    + int(show_precio_acum)

    context = {
        "categorias": categorias,
        "total_stock": total_stock,
        "total_valor": total_valor,
        "hoy": hoy,
        "titulo": "Reporte de Disponibilidad de Insumos",
        # flags UI
        "show_precio_unitario": show_precio_unitario,
        "show_stock_total": show_stock_total,
        "show_prox_venc": show_prox_venc,
        "show_lotes": show_lotes,
        "show_categorias": show_categorias,
        "show_precio_acum": show_precio_acum,
        # selección de insumos
        "all_insumo_names": all_insumo_names,
        "selected_insumos": set(selected_insumos),
        "colspan_lotes": colspan_lotes,   # <- NUEVO
        "request": request,
    }

    return render(request, "inventario/reporte_disponibilidad.html", context)