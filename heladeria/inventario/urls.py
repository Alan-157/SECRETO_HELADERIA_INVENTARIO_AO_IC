# heladeria/inventario/urls.py

from django.urls import path
from . import views

app_name = "inventario"
urlpatterns = [
    # --- CRUD de Insumos & AJAX Unidades de Medida ---
    path('insumos/', views.listar_insumos, name='listar_insumos'),
    path('insumos/crear/', views.crear_insumo, name='crear_insumo'),
    path('insumos/editar/<int:insumo_id>/', views.editar_insumo, name='editar_insumo'),
    path('insumos/eliminar/<int:insumo_id>/', views.eliminar_insumo, name='eliminar_insumo'),
    path('ajax/crear_unidad/', views.crear_unidad_medida_ajax, name='crear_unidad_medida_ajax'),
    path('ajax/editar_unidad/<int:pk>/', views.editar_unidad_medida_ajax, name='editar_unidad_medida_ajax'),
    path('ajax/eliminar_unidad/<int:pk>/', views.eliminar_unidad_medida_ajax, name='eliminar_unidad_medida_ajax'),
    
    # --- Alertas ---
    path('alertas/', views.listar_alertas, name='listar_alertas'),
    path('alertas/crear/', views.crear_alerta, name='crear_alerta'),
    path('alertas/eliminar/<int:pk>/', views.eliminar_alerta, name='eliminar_alerta'),
    
    # --- Listados Varios ---
    path('movimientos/', views.listar_movimientos, name='listar_movimientos'),
    path('lotes/exportar/', views.exportar_lotes, name='exportar_lotes'),
    path('lotes/', views.listar_insumos_lote, name='listar_lotes'),

    # --- Creación de Movimientos (NUEVAS VISTAS SEPARADAS) ---
    path("movimientos/entrada/", views.registrar_entrada, name="registrar_entrada"),
    path("movimientos/salida/", views.registrar_salida, name="registrar_salida"),
    path("movimientos/entrada-movimiento/", views.registrar_entrada_movimiento, name="registrar_entrada_movimiento"),
    path("movimientos/salida-movimiento/", views.registrar_salida_movimiento, name="registrar_salida_movimiento"),
    
    # --- Edición y Eliminación de Movimientos ---
    path("movimientos/entrada/<int:pk>/editar/", views.editar_entrada, name="editar_entrada"),
    path("movimientos/entrada/<int:pk>/eliminar/", views.eliminar_entrada, name="eliminar_entrada"),
    path("movimientos/salida/<int:pk>/editar/", views.editar_salida, name="editar_salida"),
    path("movimientos/salida/<int:pk>/eliminar/", views.eliminar_salida, name="eliminar_salida"),

    # --- Órdenes ---
    path("ordenes/", views.listar_ordenes, name="listar_ordenes"),
    path("ordenes/nueva/", views.crear_orden, name="crear_orden"),
    path("ordenes/<int:pk>/editar/", views.editar_orden, name="editar_orden"),
    path("ordenes/<int:pk>/eliminar/", views.eliminar_orden, name="eliminar_orden"),
    path("ordenes/<int:pk>/estado/", views.orden_cambiar_estado, name="orden_cambiar_estado"),

    # --- CRUD de Categorías ---
    path('categorias/', views.listar_categorias, name='listar_categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/editar/<int:categoria_id>/', views.editar_categoria, name='editar_categoria'),
    path('categorias/eliminar/<int:categoria_id>/', views.eliminar_categoria, name='eliminar_categoria'),

    # --- CRUD de Bodegas ---
    path('bodegas/', views.listar_bodegas, name='listar_bodegas'),
    path('bodegas/crear/', views.crear_bodega, name='crear_bodega'),
    path('bodegas/<int:pk>/editar/', views.editar_bodega, name='editar_bodega'),
    path('bodegas/<int:pk>/eliminar/', views.eliminar_bodega, name='eliminar_bodega'),

    # --- Reportes ---
    path('reportes/disponibilidad/', views.reporte_disponibilidad, name='reporte_disponibilidad'),
    
    # Proovedorees
    path('proveedores/', views.listar_proveedores, name='listar_proveedores'),
    path('proveedores/crear/', views.crear_proveedor, name='crear_proveedor'),
    path('proveedores/<int:pk>/editar/', views.editar_proveedor, name='editar_proveedor'),
    path('proveedores/<int:pk>/eliminar/', views.eliminar_proveedor, name='eliminar_proveedor'),
    
    # URL para AJAX que consulta stock y límites
    path('ajax/insumo/<int:insumo_id>/stock-info/', views.get_insumo_stock_info, name='get_insumo_stock_info'),
]