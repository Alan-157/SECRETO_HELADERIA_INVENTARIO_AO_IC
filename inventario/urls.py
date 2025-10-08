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
    # path('insumos/eliminar/<int:insumo_id>/', views.eliminar_insumo, name='eliminar_insumo'), 
]