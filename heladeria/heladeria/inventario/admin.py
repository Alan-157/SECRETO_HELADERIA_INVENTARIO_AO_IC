from django.contrib import admin, messages
from .models import (
    Categoria, Insumo, Ubicacion, Bodega, 
    InsumoLote, Entrada, Salida, AlertaInsumo, 
    OrdenInsumo, OrdenInsumoDetalle, Ordenresumen
)

# --- ACCIÓN PERSONALIZADA: Marcar órdenes (Clase U2 C3) ---
@admin.action(description="Marcar órdenes de insumo como 'CERRADA'")
def marcar_cerrada(modeladmin, request, queryset):
    updated = queryset.update(estado='CERRADA')
    modeladmin.message_user(request, f"{updated} órdenes marcadas como Cerrada.", messages.SUCCESS)


# --- REGISTROS PERSONALIZADOS (Clase U2 C2) ---

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("nombre", "descripcion")
    ordering = ("nombre",)

@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "stock_minimo", "unidad_medida", "is_active")
    search_fields = ("nombre", "categoria__nombre") # Búsqueda por FK
    list_filter = ("categoria", "unidad_medida", "is_active")
    list_select_related = ("categoria",) # Optimiza la carga para list_display
    ordering = ("nombre",)


@admin.register(OrdenInsumo)
class OrdenInsumoAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "estado", "usuario", "updated_at")
    list_filter = ("estado", "fecha")
    search_fields = ("usuario__email", "estado")
    ordering = ("-fecha",)
    actions = [marcar_cerrada] # <-- La acción se aplica aquí


@admin.register(InsumoLote)
class InsumoLoteAdmin(admin.ModelAdmin):
    list_display = ("id", "insumo", "bodega", "cantidad_actual", "fecha_ingreso", "usuario")
    list_filter = ("bodega", "insumo", "fecha_ingreso")
    search_fields = ("insumo__nombre", "bodega__nombre")
    list_select_related = ("insumo", "bodega", "usuario")


# --- REGISTROS SIMPLES ---
admin.site.register(Ubicacion)
admin.site.register(Bodega)
admin.site.register(Ordenresumen)
admin.site.register(Entrada)
admin.site.register(Salida)
admin.site.register(AlertaInsumo)
admin.site.register(OrdenInsumoDetalle)
