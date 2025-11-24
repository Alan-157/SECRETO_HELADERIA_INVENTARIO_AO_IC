# inventario/views.py
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, F, Sum, DecimalField
from django.db.models.functions import Coalesce

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
from django.forms import formset_factory
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required

from accounts.decorators import perfil_required
from accounts.services import user_has_role

from .models import (
    Categoria, Insumo, Bodega, UnidadMedida,
    InsumoLote, Entrada, Salida,
    OrdenInsumo, OrdenInsumoDetalle, Ubicacion
)
from .forms import (
    CategoriaForm, InsumoForm, BodegaForm,
    UnidadMedidaForm,
    OrdenInsumoDetalleCreateFormSet,
    OrdenInsumoDetalleEditFormSet,
    UbicacionForm, OrdenInsumoForm,
    MovimientoLineaForm,  # <--- IMPORTANTE (se usa con formset_factory)
)

# CRUD genérico
from .views_crud import (
    BaseListView, BaseCreateView, BaseUpdateView, BaseSoftDeleteView
)


# -----------------------------------------------------------
#                    DASHBOARD
# -----------------------------------------------------------
@login_required
def dashboard_view(request):
    total_insumos = Insumo.objects.filter(is_active=True).count()
    total_bodegas = Bodega.objects.filter(is_active=True).count()
    total_lotes = InsumoLote.objects.filter(is_active=True).count()
    ordenes = OrdenInsumo.objects.filter(is_active=True).count()

    return render(request, "dashboard.html", {
        "total_insumos": total_insumos,
        "total_bodegas": total_bodegas,
        "total_lotes": total_lotes,
        "ordenes": ordenes,
    })


# ===========================================================
#            CRUD: UNIDADES DE MEDIDA
# ===========================================================
class UnidadList(BaseListView):
    model = UnidadMedida
    template_name = "inventario/listar_unidades.html"
    partial_template = "inventario/partials/unidad_results.html"
    search_fields = ["nombre", "codigo"]
    session_prefix = "unidad"
    order_default = "nombre"
    allow = ("Administrador", "Encargado")


class UnidadCreate(BaseCreateView):
    model = UnidadMedida
    form_class = UnidadMedidaForm
    success_url = reverse_lazy("inventario:listar_unidades")
    titulo = "Unidad de Medida"
    allow = ("Administrador",)


class UnidadUpdate(BaseUpdateView):
    model = UnidadMedida
    form_class = UnidadMedidaForm
    success_url = reverse_lazy("inventario:listar_unidades")
    titulo = "Unidad de Medida"
    allow = ("Administrador",)


class UnidadDelete(BaseSoftDeleteView):
    model = UnidadMedida
    success_url = reverse_lazy("inventario:listar_unidades")
    titulo = "Unidad de Medida"
    allow = ("Administrador",)


# ===========================================================
#            CRUD: CATEGORÍAS
# ===========================================================
class CategoriaList(BaseListView):
    model = Categoria
    template_name = "inventario/listar_categorias.html"
    partial_template = "inventario/partials/categoria_results.html"
    context_object_name = "categorias"
    search_fields = ["nombre", "descripcion"]
    order_default = "nombre"
    session_prefix = "categoria"
    allow = ("Administrador", "Encargado")

    sort_map = {
        "nombre": "nombre",
        "descripcion": "descripcion",
        "": "nombre",
    }


class CategoriaCreate(BaseCreateView):
    model = Categoria
    form_class = CategoriaForm
    titulo = "Categoría"
    success_url = reverse_lazy("inventario:listar_categorias")
    allow = ("Administrador",)


class CategoriaUpdate(BaseUpdateView):
    model = Categoria
    form_class = CategoriaForm
    titulo = "Categoría"
    success_url = reverse_lazy("inventario:listar_categorias")
    allow = ("Administrador",)


class CategoriaDelete(BaseSoftDeleteView):
    model = Categoria
    titulo = "Categoría"
    success_url = reverse_lazy("inventario:listar_categorias")
    allow = ("Administrador",)


# ===========================================================
#            CRUD: INSUMOS
# ===========================================================
class InsumoList(BaseListView):
    model = Insumo
    template_name = "inventario/listar_insumos.html"
    partial_template = "inventario/partials/insumos_results.html"
    context_object_name = "insumos"
    search_fields = ["nombre", "categoria__nombre"]
    order_default = "nombre"
    session_prefix = "insumo"
    allow = ("Administrador", "Encargado")

    sort_map = {
        "nombre": "nombre",
        "categoria": "categoria__nombre",
        "stock": "stock_actual",
        "": "nombre",
    }

    def get_queryset(self):
        qs = (
            Insumo.objects.filter(is_active=True)
            .select_related("categoria", "unidad_medida")
            .annotate(
                stock_actual=Coalesce(
                    Sum("lotes__cantidad_actual"),
                    0,
                    output_field=DecimalField()
                )
            )
        )

        q = (self.request.GET.get("q") or "").strip()
        if q:
            condiciones = Q()
            for f in self.search_fields:
                condiciones |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(condiciones)

        sort = (self.request.GET.get("sort") or "").strip()
        order_dir = (self.request.GET.get("order") or "asc").lower()
        sort_field = self.sort_map.get(sort, "nombre")
        if order_dir == "desc":
            sort_field = f"-{sort_field}"

        return qs.order_by(sort_field)


class InsumoCreate(BaseCreateView):
    model = Insumo
    form_class = InsumoForm
    titulo = "Insumo"
    success_url = reverse_lazy("inventario:listar_insumos")
    allow = ("Administrador", "Encargado")


class InsumoUpdate(BaseUpdateView):
    model = Insumo
    form_class = InsumoForm
    titulo = "Insumo"
    success_url = reverse_lazy("inventario:listar_insumos")
    allow = ("Administrador", "Encargado")


class InsumoDelete(BaseSoftDeleteView):
    model = Insumo
    titulo = "Insumo"
    success_url = reverse_lazy("inventario:listar_insumos")
    allow = ("Administrador", "Encargado")


# ===========================================================
#            CRUD: BODEGAS
# ===========================================================
class BodegaList(BaseListView):
    model = Bodega
    template_name = "inventario/listar_bodegas.html"
    partial_template = "inventario/partials/bodegas_results.html"
    context_object_name = "bodegas"
    search_fields = ["nombre", "direccion", "ubicacion__nombre"]
    order_default = "nombre"
    session_prefix = "bodega"
    allow = ("Administrador", "Encargado")

    sort_map = {
        "nombre": "nombre",
        "direccion": "direccion",
        "ubicacion": "ubicacion__nombre",
        "": "nombre",
    }

    def get_queryset(self):
        return (
            Bodega.objects.filter(is_active=True)
            .select_related("ubicacion")
        )


class BodegaCreate(BaseCreateView):
    model = Bodega
    form_class = BodegaForm
    titulo = "Bodega"
    success_url = reverse_lazy("inventario:listar_bodegas")
    allow = ("Administrador",)


class BodegaUpdate(BaseUpdateView):
    model = Bodega
    form_class = BodegaForm
    titulo = "Bodega"
    success_url = reverse_lazy("inventario:listar_bodegas")
    allow = ("Administrador",)


class BodegaDelete(BaseSoftDeleteView):
    model = Bodega
    titulo = "Bodega"
    success_url = reverse_lazy("inventario:listar_bodegas")
    allow = ("Administrador",)


# ===========================================================
#      HELPER PARA LOTES (NO DUPLICAR LÓGICA)
# ===========================================================
def _qs_lotes_filtrado(request):
    hoy = date.today()

    qs = (
        InsumoLote.objects.filter(is_active=True)
        .select_related("insumo", "bodega", "proveedor")
        .annotate(
            cant_act=Coalesce(F("cantidad_actual"), 0, output_field=DecimalField()),
            cant_ini=Coalesce(F("cantidad_inicial"), 0, output_field=DecimalField()),
        )
    )

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(insumo__nombre__icontains=q) |
            Q(bodega__nombre__icontains=q)
        )

    filtro_vencimiento = request.GET.get("vencimiento", "todos")
    dias_proximos = request.GET.get("dias", 30)
    try:
        dias_proximos = int(dias_proximos)
        if dias_proximos < 1 or dias_proximos > 365:
            dias_proximos = 30
    except:
        dias_proximos = 30

    if filtro_vencimiento == "proximos" or request.GET.get("proximos") == "1":
        limite = hoy + timedelta(days=dias_proximos)
        qs = qs.filter(fecha_expiracion__lte=limite)

    sort = request.GET.get("sort", "insumo")
    order = request.GET.get("order", "asc")

    sort_map = {
        "insumo": "insumo__nombre",
        "bodega": "bodega__nombre",
        "fingreso": "fecha_ingreso",
        "fexpira": "fecha_expiracion",
        "cact": "cant_act",
        "cini": "cant_ini",
    }
    sort_field = sort_map.get(sort, "insumo__nombre")
    if order == "desc":
        sort_field = f"-{sort_field}"

    qs = qs.order_by(sort_field)

    meta = {
        "q": q,
        "filtro_vencimiento": filtro_vencimiento,
        "dias_proximos": dias_proximos,
        "sort": sort,
        "order": order,
    }
    return qs, meta


# ===========================================================
#          LISTAR INSUMO LOTES (AJAX)
# ===========================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado", "Bodeguero"))
def listar_insumos_lote(request):
    qs, meta = _qs_lotes_filtrado(request)

    per_page = request.GET.get("per_page", 10)
    try:
        per_page = int(per_page)
        if per_page not in (5, 10, 20, 25, 50, 100):
            per_page = 10
    except:
        per_page = 10

    paginator = Paginator(qs, per_page)
    page_number = request.GET.get("page", 1)
    lotes = paginator.get_page(page_number)

    ctx = {
        "titulo": "Lotes de Insumo",
        "lotes": lotes,
        "per_page": per_page,
        "today": date.today(),
        **meta,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render(
            request,
            "inventario/partials/insumo_lote_results.html",
            ctx
        ).content.decode("utf-8")
        return JsonResponse({"html": html})

    return render(request, "inventario/listar_insumo_lote.html", ctx)


# ===========================================================
#              EXPORTAR LOTES (MISMA LÓGICA)
# ===========================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado"))
def exportar_lotes(request):
    qs, meta = _qs_lotes_filtrado(request)
    tipo = (request.GET.get("exportar") or "excel").lower()

    try:
        from .exports import exportar_lotes_excel, exportar_lotes_pdf
    except Exception:
        exportar_lotes_excel = exportar_lotes_pdf = None

    if tipo == "pdf":
        if exportar_lotes_pdf:
            return exportar_lotes_pdf(qs, meta)
        return HttpResponseBadRequest("Exportación PDF no configurada.")
    else:
        if exportar_lotes_excel:
            return exportar_lotes_excel(qs, meta)
        return HttpResponseBadRequest("Exportación Excel no configurada.")


# ===========================================================
#            ORDENES
# ===========================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado", "Bodeguero"))
def crear_orden(request):
    orden = OrdenInsumo(usuario=request.user)

    form_orden = OrdenInsumoForm(request.POST or None, instance=orden)
    formset = OrdenInsumoDetalleCreateFormSet(request.POST or None, instance=orden)

    if request.method == "POST" and form_orden.is_valid() and formset.is_valid():
        form_orden.save()
        formset.save()
        messages.success(request, "Orden creada correctamente.")
        return redirect("inventario:listar_ordenes")

    return render(request, "inventario/orden/form.html", {
        "form_orden": form_orden,
        "formset": formset,
        "titulo": "Nueva Orden",
    })


@login_required
@perfil_required(allow=("Administrador", "Encargado"))
def editar_orden(request, pk):
    orden = get_object_or_404(OrdenInsumo, pk=pk, is_active=True)

    form_orden = OrdenInsumoForm(request.POST or None, instance=orden)
    formset = OrdenInsumoDetalleEditFormSet(request.POST or None, instance=orden)

    if request.method == "POST" and form_orden.is_valid() and formset.is_valid():
        form_orden.save()
        formset.save()
        messages.success(request, "Orden actualizada.")
        return redirect("inventario:listar_ordenes")

    return render(request, "inventario/orden/form.html", {
        "form_orden": form_orden,
        "formset": formset,
        "titulo": f"Editar Orden #{orden.id}",
    })


@login_required
@perfil_required(allow=("Administrador", "Encargado"))
def eliminar_orden(request, pk):
    orden = get_object_or_404(OrdenInsumo, pk=pk)

    if request.method == "POST":
        orden.is_active = False
        orden.save(update_fields=["is_active"])
        messages.success(request, "Orden eliminada.")
        return redirect("inventario:listar_ordenes")

    return render(request, "inventario/confirmar_eliminar.html", {
        "titulo": f"Eliminar Orden #{orden.id}",
        "obj": orden,
    })


# ===========================================================
#            LISTAR ÓRDENES (AJAX)
# ===========================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado"), readonly_for="Bodeguero")
def listar_ordenes(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()

    qs = (
        OrdenInsumo.objects.filter(is_active=True)
        .select_related("usuario")
        .prefetch_related("detalles__insumo")
        .order_by("-fecha")
    )

    if q:
        qs = qs.filter(
            Q(id__icontains=q) |
            Q(usuario__name__icontains=q) |
            Q(usuario__email__icontains=q)
        )

    if estado:
        qs = qs.filter(estado=estado)

    sort = request.GET.get("sort", "fecha")
    order = request.GET.get("order", "desc")

    sort_map = {
        "fecha": "fecha",
        "id": "id",
        "estado": "estado",
        "usuario": "usuario__name",
    }
    sort_field = sort_map.get(sort, "fecha")
    if order == "desc":
        sort_field = f"-{sort_field}"
    qs = qs.order_by(sort_field)

    per_page = request.GET.get("per_page", 10)
    try:
        per_page = int(per_page)
        if per_page not in (5, 10, 20, 25, 50, 100):
            per_page = 10
    except:
        per_page = 10

    paginator = Paginator(qs, per_page)
    page_number = request.GET.get("page", 1)
    ordenes = paginator.get_page(page_number)

    ESTADOS_ORDEN = [c[0] for c in OrdenInsumo._meta.get_field("estado").choices]

    ctx = {
        "titulo": "Órdenes",
        "ordenes": ordenes,
        "per_page": per_page,
        "q": q,
        "estado": estado,
        "sort": sort,
        "order": order,
        "ESTADOS_ORDEN": ESTADOS_ORDEN,
        "read_only": False,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render(
            request,
            "inventario/partials/ordenes_results.html",
            ctx
        ).content.decode("utf-8")
        return JsonResponse({"html": html})

    return render(request, "inventario/listar_ordenes.html", ctx)


# ===========================================================
#     CAMBIAR ESTADO DE ORDEN (AJAX / POST)
# ===========================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado"))
def orden_cambiar_estado(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("Método no permitido.")

    orden = get_object_or_404(OrdenInsumo, pk=pk, is_active=True)
    nuevo_estado = (request.POST.get("estado") or "").strip()

    estados_validos = [c[0] for c in OrdenInsumo._meta.get_field("estado").choices]
    if nuevo_estado not in estados_validos:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "msg": "Estado inválido."}, status=400)
        messages.error(request, "Estado inválido.")
        return redirect("inventario:listar_ordenes")

    orden.estado = nuevo_estado
    orden.save(update_fields=["estado"])

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "estado": nuevo_estado})

    messages.success(request, "Estado actualizado.")
    return redirect("inventario:listar_ordenes")


@login_required
@perfil_required(allow=("Administrador", "Encargado"))
def atender_orden(request, pk):
    orden = get_object_or_404(OrdenInsumo, pk=pk, is_active=True)

    if orden.estado in ("CERRADA", "CANCELADA"):
        messages.warning(request, "Esta orden no puede atenderse.")
        return redirect("inventario:listar_ordenes")

    # ✅ usar la misma key que registrar_movimiento
    return redirect(f"{reverse_lazy('inventario:registrar_movimiento')}?orden={orden.id}")


# ===========================================================
#            REGISTRO DE MOVIMIENTOS
# ===========================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado"))
@transaction.atomic
def registrar_movimiento(request):
    orden_id = request.GET.get("orden")
    orden = None
    detalles = None

    if orden_id:
        orden = get_object_or_404(OrdenInsumo, pk=orden_id, is_active=True)
        detalles = orden.detalles.all()

    MovimientoFormSet = formset_factory(MovimientoLineaForm, extra=0)

    if request.method == "GET" and orden:
        initial = [
            {
                "tipo": orden.tipo,
                "insumo": d.insumo.id,
                "cantidad": d.cantidad_solicitada,
            }
            for d in detalles
        ]
        formset = MovimientoFormSet(initial=initial)
    else:
        formset = MovimientoFormSet(request.POST or None)

    if request.method == "POST":
        if formset.is_valid():
            for form in formset:
                cd = form.cleaned_data
                if not cd:
                    continue

                tipo = cd["tipo"]
                insumo = cd["insumo"]
                bodega = cd.get("bodega")
                lote = cd.get("insumo_lote")
                crear_nuevo = cd.get("crear_nuevo_lote")
                fexp = cd.get("fecha_expiracion")
                cantidad = cd["cantidad"]
                fecha = date.today()
                obs = cd.get("observaciones", "")

                # ------------------ ENTRADA ------------------
                if tipo == "ENTRADA":
                    if crear_nuevo:
                        lote = InsumoLote.objects.create(
                            insumo=insumo,
                            bodega=bodega,
                            proveedor=None,
                            fecha_ingreso=fecha,
                            fecha_expiracion=fexp,
                            cantidad_inicial=cantidad,
                            cantidad_actual=cantidad,
                            usuario=request.user,
                        )
                    else:
                        if not lote:
                            form.add_error("insumo_lote", "Debes seleccionar un lote existente.")
                            continue
                        lote.cantidad_actual += cantidad
                        lote.save(update_fields=["cantidad_actual"])

                    Entrada.objects.create(
                        insumo=insumo,
                        insumo_lote=lote,
                        ubicacion=lote.bodega.ubicacion,
                        orden=orden,
                        detalle=None,
                        cantidad=cantidad,
                        fecha=fecha,
                        usuario=request.user,
                        tipo="COMPRA",
                        observaciones=obs,
                    )

                # ------------------ SALIDA ------------------
                elif tipo == "SALIDA":
                    if not lote:
                        form.add_error("insumo_lote", "Debes seleccionar un lote para la salida.")
                        continue

                    lote.cantidad_actual -= cantidad
                    lote.save(update_fields=["cantidad_actual"])

                    Salida.objects.create(
                        insumo=insumo,
                        insumo_lote=lote,
                        ubicacion=lote.bodega.ubicacion,
                        orden=orden,
                        detalle=None,
                        cantidad=cantidad,
                        fecha_generada=fecha,
                        usuario=request.user,
                        tipo="VENTA",
                        observaciones=obs,
                    )

            if orden:
                orden.recalc_estado()

            messages.success(request, "Movimiento registrado correctamente.")
            return redirect("inventario:listar_movimientos")

    return render(
        request,
        "inventario/registrar_movimiento.html",
        {
            "formset": formset,
            "orden": orden,
        }
    )


# ===========================================================
#            LISTAR MOVIMIENTOS
# ===========================================================
@login_required
@perfil_required(allow=("Administrador", "Encargado", "Bodeguero"))
def listar_movimientos(request):
    q = (request.GET.get("q") or "").strip()

    entradas_qs = Entrada.objects.filter(is_active=True)
    salidas_qs = Salida.objects.filter(is_active=True)

    if q:
        entradas_qs = entradas_qs.filter(
            Q(insumo__nombre__icontains=q) |
            Q(ubicacion__nombre__icontains=q)
        )
        salidas_qs = salidas_qs.filter(
            Q(insumo__nombre__icontains=q) |
            Q(ubicacion__nombre__icontains=q)
        )

    entradas_qs = entradas_qs.order_by("-fecha")
    salidas_qs = salidas_qs.order_by("-fecha_generada")

    page_e = request.GET.get("page_e", 1)
    page_s = request.GET.get("page_s", 1)

    entradas = Paginator(entradas_qs, 10).get_page(page_e)
    salidas = Paginator(salidas_qs, 10).get_page(page_s)

    can_manage = user_has_role(request.user, "Administrador", "Encargado")

    return render(request, "inventario/listar_movimientos.html", {
        "titulo": "Movimientos",
        "entradas": entradas,
        "salidas": salidas,
        "q": q,
        "can_manage": can_manage,
    })


# ===========================================================
#            CRUD: UBICACIONES
# ===========================================================
class UbicacionList(BaseListView):
    model = Ubicacion
    template_name = "inventario/listar_ubicaciones.html"
    partial_template = "inventario/partials/ubicaciones_results.html"
    context_object_name = "ubicaciones"
    search_fields = ["nombre", "direccion"]
    order_default = "nombre"
    session_prefix = "ubicacion"
    allow = ("Administrador", "Encargado")

    sort_map = {
        "nombre": "nombre",
        "direccion": "direccion",
        "": "nombre",
    }


class UbicacionCreate(BaseCreateView):
    model = Ubicacion
    form_class = UbicacionForm
    titulo = "Ubicación"
    success_url = reverse_lazy("inventario:listar_ubicaciones")
    allow = ("Administrador",)


class UbicacionUpdate(BaseUpdateView):
    model = Ubicacion
    form_class = UbicacionForm
    titulo = "Ubicación"
    success_url = reverse_lazy("inventario:listar_ubicaciones")
    allow = ("Administrador",)


class UbicacionDelete(BaseSoftDeleteView):
    model = Ubicacion
    titulo = "Ubicación"
    success_url = reverse_lazy("inventario:listar_ubicaciones")
    allow = ("Administrador",)


# ===========================================================
#            AJAX HELPERS
# ===========================================================
@login_required
def ajax_insumos(request):
    q = (request.GET.get("q") or "").strip()
    page = int(request.GET.get("page") or 1)
    per_page = int(request.GET.get("per_page") or 5)

    qs = (
        Insumo.objects.filter(is_active=True)
        .select_related("categoria", "unidad_medida")
    )

    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(categoria__nombre__icontains=q)
        )

    qs = qs.order_by("nombre")

    paginator = Paginator(qs, per_page)
    p = paginator.get_page(page)

    data = [{
        "id": i.id,
        "text": f"{i.nombre} ({i.categoria.nombre})" if i.categoria_id else i.nombre
    } for i in p.object_list]

    return JsonResponse({
        "ok": True,
        "results": data,
        "page": p.number,
        "num_pages": paginator.num_pages,
        "has_next": p.has_next(),
        "has_prev": p.has_previous(),
    })


@login_required
def ajax_bodega_ubicacion(request):
    bodega_id = request.GET.get("bodega_id")
    if not bodega_id:
        return JsonResponse({"ok": False})

    bodega = get_object_or_404(Bodega, pk=bodega_id, is_active=True)
    u = bodega.ubicacion
    return JsonResponse({
        "ok": True,
        "ubicacion_id": u.id,
        "ubicacion_text": str(u),
    })


@login_required
def ajax_lotes_por_insumo(request):
    insumo_id = request.GET.get("insumo_id")
    bodega_id = request.GET.get("bodega_id")

    qs = InsumoLote.objects.filter(is_active=True)

    if insumo_id:
        qs = qs.filter(insumo_id=insumo_id)
    if bodega_id:
        qs = qs.filter(bodega_id=bodega_id)

    data = [{
        "id": l.id,
        "text": f"Lote #{l.id} | {l.bodega.nombre} | disp: {l.cantidad_actual} | exp: {l.fecha_expiracion}"
    } for l in qs.order_by("-fecha_ingreso")]

    return JsonResponse({"ok": True, "lotes": data})


@login_required
def ajax_lote_detalle(request):
    lote_id = request.GET.get("lote_id")
    if not lote_id:
        return JsonResponse({"ok": False})

    lote = get_object_or_404(InsumoLote, pk=lote_id, is_active=True)

    return JsonResponse({
        "ok": True,
        "bodega_id": lote.bodega_id,
        "bodega_text": lote.bodega.nombre,
        "ubicacion_id": lote.bodega.ubicacion_id,
        "ubicacion_text": str(lote.bodega.ubicacion),
        # ✅ tolerante a None
        "fecha_expiracion": lote.fecha_expiracion.strftime("%Y-%m-%d") if lote.fecha_expiracion else "",
        "cantidad_actual": str(lote.cantidad_actual),
        "insumo_id": lote.insumo_id,
    })
