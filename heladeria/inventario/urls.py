# heladeria/inventario/urls.py

from django.urls import path
from . import views

app_name = "inventario"
urlpatterns = [
    # --- CRUD de Insumos ---
    path('insumos/', views.listar_insumos, name='listar_insumos'),
    path('insumos/crear/', views.crear_insumo, name='crear_insumo'),
    path('insumos/editar/<int:insumo_id>/', views.editar_insumo, name='editar_insumo'),
    path('insumos/eliminar/<int:insumo_id>/', views.eliminar_insumo, name='eliminar_insumo'),
    
    # --- Listados Varios ---
    path('movimientos/', views.listar_movimientos, name='listar_movimientos'),
    path('ordenes/', views.listar_ordenes, name='listar_ordenes'),
    path('lotes/exportar/', views.exportar_lotes, name='exportar_lotes'),
    path('lotes/', views.listar_insumos_lote, name='listar_lotes'),

    # --- Creación de Movimientos ---
    path("movimientos/registrar/", views.registrar_movimiento, name="registrar_movimiento"),
    path("movimientos/entrada/<int:pk>/editar/", views.editar_entrada, name="editar_entrada"),
    path("movimientos/entrada/<int:pk>/eliminar/", views.eliminar_entrada, name="eliminar_entrada"),
    path("movimientos/salida/<int:pk>/editar/", views.editar_salida, name="editar_salida"),
    path("movimientos/salida/<int:pk>/eliminar/", views.eliminar_salida, name="eliminar_salida"),

    # --- Órdenes
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

    # --- Bodegas ---
    path('bodegas/', views.listar_bodegas, name='listar_bodegas'),
    path('bodegas/crear/', views.crear_bodega, name='crear_bodega'),
    path('bodegas/<int:pk>/editar/', views.editar_bodega, name='editar_bodega'),
    path('bodegas/<int:pk>/eliminar/', views.eliminar_bodega, name='eliminar_bodega'),

    # --- Reportes ---
    path('reportes/disponibilidad/', views.reporte_disponibilidad, name='reporte_disponibilidad'),
]