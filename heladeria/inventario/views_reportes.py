# inventario/views_reportes.py
from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Q, Sum, Min, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required

from accounts.decorators import perfil_required
from .models import Insumo, InsumoLote, Entrada, Salida, OrdenInsumo


# ================================================================
#   REPORTE DISPONIBILIDAD (ya lo tienes funcional)
# ================================================================
from django.db.models import Prefetch

@login_required
@perfil_required(allow=("Administrador", "Encargado"))
def reporte_disponibilidad(request):
    from .exports import (
        exportar_disponibilidad_csv,
        exportar_disponibilidad_excel,
        exportar_disponibilidad_pdf,
    )

    q = (request.GET.get("q") or "").strip()
    selected_insumos = request.GET.getlist("insumo")

    show_stock_total     = "show_stock_total" in request.GET if request.GET else True
    show_precio_unitario = "show_precio_unitario" in request.GET
    show_prox_venc       = "show_prox_venc" in request.GET
    show_lotes           = "show_lotes" in request.GET
    show_categorias      = "show_categorias" in request.GET if request.GET else True
    show_precio_acum     = "show_precio_acum" in request.GET

    lotes_qs = InsumoLote.objects.filter(is_active=True).select_related("bodega")

    qs = (
        Insumo.objects.filter(is_active=True)
        .select_related("categoria", "unidad_medida")
        .annotate(
            stock_total=Coalesce(Sum("lotes__cantidad_actual", filter=Q(lotes__is_active=True)),
                                 Decimal("0"), output_field=DecimalField()),
            prox_vencimiento=Min("lotes__fecha_expiracion",
                                 filter=Q(lotes__is_active=True, lotes__cantidad_actual__gt=0))
        )
    )

    if show_lotes:
        qs = qs.prefetch_related(
            Prefetch("lotes", queryset=lotes_qs.order_by("fecha_expiracion"), to_attr="lotes_vis")
        )

    if selected_insumos:
        qs = qs.filter(nombre__in=selected_insumos)

    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(categoria__nombre__icontains=q)
        )

    qs = qs.annotate(
        precio_acumulado=ExpressionWrapper(
            F("stock_total") * F("precio_unitario"),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        )
    ).order_by("categoria__nombre", "nombre")

    # Agrupación por categorías
    bloques = []
    actual_cat = None
    for ins in qs:
        if actual_cat != ins.categoria:
            bloques.append({"categoria": ins.categoria, "insumos": []})
            actual_cat = ins.categoria
        bloques[-1]["insumos"].append(ins)

    ctx = {
        "titulo": "Disponibilidad de Insumos",
        "categorias": bloques,
        "all_insumo_names": list(Insumo.objects.filter(is_active=True).order_by("nombre").values_list("nombre", flat=True)),
        "selected_insumos": selected_insumos,
        "show_stock_total": show_stock_total,
        "show_precio_unitario": show_precio_unitario,
        "show_prox_venc": show_prox_venc,
        "show_lotes": show_lotes,
        "show_categorias": show_categorias,
        "show_precio_acum": show_precio_acum,
        "total_stock": sum(i.stock_total or 0 for i in qs),
        "total_valor": sum(i.precio_acumulado or 0 for i in qs),
        "colspan_lotes": 2 + show_categorias + show_precio_unitario + show_stock_total + show_prox_venc + show_precio_acum,
        "q": q,
        "today": date.today(),
    }

    # EXPORTS
    fmt = (request.GET.get("format") or "").lower()
    if fmt == "csv":
        return exportar_disponibilidad_csv(qs, ctx)
    if fmt in ("xlsx", "excel"):
        return exportar_disponibilidad_excel(qs, ctx)
    if fmt == "pdf":
        return exportar_disponibilidad_pdf(qs, ctx)

    # AJAX
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render(request, "inventario/partials/reporte_disponibilidad_results.html", ctx).content.decode("utf-8")
        return JsonResponse({"html": html})

    return render(request, "inventario/reporte_disponibilidad.html", ctx)

# ================================================================
#   REPORTE: LOTES PRÓXIMOS A VENCER  + EXPORT
# ================================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado"))
def reporte_proximos_vencer(request):
    today = date.today()

    # dias con validación
    dias = request.GET.get("dias", 30)
    try:
        dias = int(dias)
        if dias < 1 or dias > 365:
            dias = 30
    except:
        dias = 30

    limite = today + timedelta(days=dias)

    items = (
        InsumoLote.objects.filter(
            is_active=True,
            fecha_expiracion__lte=limite
        )
        .select_related("insumo", "bodega")
        .order_by("fecha_expiracion")
    )

    ctx = {
        "titulo": "Próximos a vencer",
        "items": items,
        "dias": dias,
        "today": today,
    }

    # ✅ respuesta AJAX con partial
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render(
            request,
            "inventario/partials/proximos_vencer_results.html",
            ctx
        ).content.decode("utf-8")
        return JsonResponse({"html": html})

    return render(request, "inventario/proximos_vencer.html", ctx)

# ================================================================
#   REPORTE MOVIMIENTOS + EXPORT
# ================================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado"))
def reporte_movimientos(request):
    from .exports import exportar_mov_excel, exportar_mov_pdf

    q = (request.GET.get("q") or "").strip()

    entradas = Entrada.objects.filter(is_active=True)
    salidas = Salida.objects.filter(is_active=True)

    if q:
        entradas = entradas.filter(Q(insumo__nombre__icontains=q) | Q(ubicacion__nombre__icontains=q))
        salidas = salidas.filter(Q(insumo__nombre__icontains=q) | Q(ubicacion__nombre__icontains=q))

    entradas = entradas.order_by("-fecha")
    salidas  = salidas.order_by("-fecha_generada")

    fmt = (request.GET.get("format") or "").lower()

    if fmt == "excel":
        return exportar_mov_excel(entradas, salidas, q)
    if fmt == "pdf":
        return exportar_mov_pdf(entradas, salidas, q)

    return render(request, "inventario/reporte_movimientos.html", {
        "entradas": entradas,
        "salidas": salidas,
        "q": q,
        "titulo": "Historial de Movimientos",
    })

# ================================================================
#   STOCK CONSOLIDADO  + EXPORT
# ================================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado"))
def reporte_stock_consolidado(request):
    from .exports import exportar_stock_excel, exportar_stock_pdf

    qs = (
        Insumo.objects.filter(is_active=True)
        .annotate(
            stock_total=Coalesce(Sum("lotes__cantidad_actual"), Decimal("0")),
            stock_min_storage=F("stock_minimo"),
            stock_max_storage=F("stock_maximo"),
        )
        .order_by("nombre")
    )

    fmt = (request.GET.get("format") or "").lower()

    if fmt == "excel":
        return exportar_stock_excel(qs)
    if fmt == "pdf":
        return exportar_stock_pdf(qs)

    return render(request, "inventario/stock_consolidado.html", {
        "items": qs,
        "titulo": "Stock Consolidado",
    })

# ================================================================
#   REPORTE ORDENES + EXPORT
# ================================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado"))
def reporte_ordenes(request):
    from .exports import exportar_ordenes_excel, exportar_ordenes_pdf

    estado = request.GET.get("estado", "")

    qs = OrdenInsumo.objects.filter(is_active=True).select_related("usuario").order_by("-fecha")

    if estado:
        qs = qs.filter(estado=estado)

    fmt = (request.GET.get("format") or "").lower()

    if fmt == "excel":
        return exportar_ordenes_excel(qs, estado)
    if fmt == "pdf":
        return exportar_ordenes_pdf(qs, estado)

    return render(request, "inventario/ordenes.html", {
        "items": qs,
        "estado": estado,
        "titulo": "Reporte de Órdenes",
    })
