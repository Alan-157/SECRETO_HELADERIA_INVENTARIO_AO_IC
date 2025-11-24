# heladeria/inventario/urls.py
from django.urls import path
from . import views
from . import views_reportes as rep

app_name = "inventario"

urlpatterns = [
    # =========================
    # CRUD UNIDAD DE MEDIDA
    # =========================
    path("unidades/", views.UnidadList.as_view(), name="unidad_listar"),
    path("unidades/crear/", views.UnidadCreate.as_view(), name="unidad_crear"),
    path("unidades/editar/<int:pk>/", views.UnidadUpdate.as_view(), name="unidad_editar"),
    path("unidades/eliminar/<int:pk>/", views.UnidadDelete.as_view(), name="unidad_eliminar"),

    # =========================
    # CRUD CATEGORÍAS
    # =========================
    path("categorias/", views.CategoriaList.as_view(), name="listar_categorias"),
    path("categorias/crear/", views.CategoriaCreate.as_view(), name="crear_categoria"),
    path("categorias/editar/<int:pk>/", views.CategoriaUpdate.as_view(), name="editar_categoria"),
    path("categorias/eliminar/<int:pk>/", views.CategoriaDelete.as_view(), name="eliminar_categoria"),

    # =========================
    # CRUD INSUMOS
    # =========================
    path("insumos/", views.InsumoList.as_view(), name="listar_insumos"),
    path("insumos/crear/", views.InsumoCreate.as_view(), name="crear_insumo"),
    path("insumos/editar/<int:pk>/", views.InsumoUpdate.as_view(), name="editar_insumo"),
    path("insumos/eliminar/<int:pk>/", views.InsumoDelete.as_view(), name="eliminar_insumo"),

    # =========================   
    # CRUD UNIDADES DE MEDIDA
    # =========================
    path("unidades/", views.UnidadList.as_view(), name="listar_unidades"),
    path("unidades/crear/", views.UnidadCreate.as_view(), name="crear_unidad"),
    path("unidades/editar/<int:pk>/", views.UnidadUpdate.as_view(), name="editar_unidad"),
    path("unidades/eliminar/<int:pk>/", views.UnidadDelete.as_view(), name="eliminar_unidad"),

    # =========================
    # CRUD BODEGAS
    # =========================
    path("bodegas/", views.BodegaList.as_view(), name="listar_bodegas"),
    path("bodegas/crear/", views.BodegaCreate.as_view(), name="crear_bodega"),
    path("bodegas/editar/<int:pk>/", views.BodegaUpdate.as_view(), name="editar_bodega"),
    path("bodegas/eliminar/<int:pk>/", views.BodegaDelete.as_view(), name="eliminar_bodega"),

    # =========================
    # CRUD UBICACIONES
    # =========================
    path("ubicaciones/", views.UbicacionList.as_view(), name="listar_ubicaciones"),
    path("ubicaciones/crear/", views.UbicacionCreate.as_view(), name="crear_ubicacion"),
    path("ubicaciones/editar/<int:pk>/", views.UbicacionUpdate.as_view(), name="editar_ubicacion"),
    path("ubicaciones/eliminar/<int:pk>/", views.UbicacionDelete.as_view(), name="eliminar_ubicacion"),

    # =========================
    # LOTES
    # =========================
    path("lotes/", views.listar_insumos_lote, name="listar_lotes"),
    path("lotes/exportar/", views.exportar_lotes, name="exportar_lotes"),

    # =========================
    # MOVIMIENTOS
    # =========================
    path("movimientos/", views.listar_movimientos, name="listar_movimientos"),
    path("movimientos/registrar/", views.registrar_movimiento, name="registrar_movimiento"),

    # =========================
    # ÓRDENES
    # =========================
    path("ordenes/", views.listar_ordenes, name="listar_ordenes"),
    path("ordenes/nueva/", views.crear_orden, name="crear_orden"),
    path("ordenes/<int:pk>/editar/", views.editar_orden, name="editar_orden"),
    path("ordenes/<int:pk>/eliminar/", views.eliminar_orden, name="eliminar_orden"),
    path("ordenes/<int:pk>/estado/", views.orden_cambiar_estado, name="orden_cambiar_estado"),
    path("ordenes/<int:pk>/atender/", views.atender_orden, name="atender_orden"),

    # =========================
    # REPORTES
    # =========================
    path("reportes/disponibilidad/", rep.reporte_disponibilidad, name="reporte_disponibilidad"),
    path("reportes/proximos-vencer/", rep.reporte_proximos_vencer, name="reporte_proximos_vencer"),
    path("reportes/movimientos/", rep.reporte_movimientos, name="reporte_movimientos"),
    path("reportes/stock/", rep.reporte_stock_consolidado, name="reporte_stock_consolidado"),
    path("reportes/ordenes/", rep.reporte_ordenes, name="reporte_ordenes"),

    # =========================
    # AJAX
    # =========================
    path("ajax/bodega-ubicacion/", views.ajax_bodega_ubicacion, name="ajax_bodega_ubicacion"),
    path("ajax/lotes-por-insumo/", views.ajax_lotes_por_insumo, name="ajax_lotes_por_insumo"),
    path("ajax/lote-detalle/", views.ajax_lote_detalle, name="ajax_lote_detalle"),
    path("ajax/insumos/", views.ajax_insumos, name="ajax_insumos"),
]
