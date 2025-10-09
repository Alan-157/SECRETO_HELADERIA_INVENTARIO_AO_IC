# heladeria/inventario/urls.py

from django.urls import path
from . import views

app_name = "inventario"
urlpatterns = [
    # Listar (Read)
    path('insumos/', views.listar_insumos, name='listar_insumos'),
    
    # Crear (Create)
    path('insumos/crear/', views.crear_insumo, name='crear_insumo'),
    
    # Editar (Update) - Requiere el ID del insumo
    path('insumos/editar/<int:insumo_id>/', views.editar_insumo, name='editar_insumo'),
    
    # Eliminar (Delete - Opcional)
    path('insumos/eliminar/<int:insumo_id>/', views.eliminar_insumo, name='eliminar_insumo'), 
]

urlpatterns = [
    # --- CRUD de Insumos ---
    path('insumos/', views.listar_insumos, name='listar_insumos'),
    path('insumos/crear/', views.crear_insumo, name='crear_insumo'),
    path('insumos/editar/<int:insumo_id>/', views.editar_insumo, name='editar_insumo'),
    path('insumos/eliminar/<int:insumo_id>/', views.eliminar_insumo, name='eliminar_insumo'),
    
    # --- Rutas de Consulta ---
    path('bodegas/', views.listar_bodegas, name='listar_bodegas'),
    path('movimientos/', views.listar_movimientos, name='listar_movimientos'),
    path('ordenes/', views.listar_ordenes, name='listar_ordenes'),
]