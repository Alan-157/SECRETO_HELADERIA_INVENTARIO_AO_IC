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
    path('bodegas/', views.listar_bodegas, name='listar_bodegas'),
    path('movimientos/', views.listar_movimientos, name='listar_movimientos'),
    path('ordenes/', views.listar_ordenes, name='listar_ordenes'),

    # --- Creación de Movimientos ---
    path('movimientos/entrada/crear/', views.crear_entrada, name='crear_entrada'),
    path('movimientos/salida/crear/', views.crear_salida, name='crear_salida'),

    # --- Creación de Órdenes ---
    path('ordenes/crear/', views.crear_orden, name='crear_orden'),

    # --- CRUD de Categorías ---
    path('categorias/', views.listar_categorias, name='listar_categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/editar/<int:categoria_id>/', views.editar_categoria, name='editar_categoria'),
    path('categorias/eliminar/<int:categoria_id>/', views.eliminar_categoria, name='eliminar_categoria'),
]