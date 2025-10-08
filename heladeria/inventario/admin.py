from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from .models import (
    Categoria, Insumo, Ubicacion, Bodega,
    InsumoLote, Entrada, Salida, AlertaInsumo,
    OrdenInsumo, OrdenInsumoDetalle, Ordenresumen
)

User = get_user_model()

# =====================================================
# MIXIN DE PERMISOS POR ROL
# =====================================================
def rol_name(user):
    try:
        return (user.rol.nombre or "").lower()
    except Exception:
        return ""

class RoleScopedInventarioAdminMixin:
    """Controla permisos de acuerdo al rol del usuario logueado."""

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request):
        r = rol_name(request.user)
        if request.user.is_superuser: return True
        if r == "encargado": return True
        if r == "bodeguero": return False
        return False

    def has_change_permission(self, request, obj=None):
        r = rol_name(request.user)
        if request.user.is_superuser: return True
        if r == "encargado": return True
        if r == "bodeguero": return False
        return False

    def has_delete_permission(self, request, obj=None):
        r = rol_name(request.user)
        if request.user.is_superuser: return True
        if r in ["encargado", "bodeguero"]: return False
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        r = rol_name(request.user)
        if request.user.is_superuser or r == "encargado":
            return qs
        if r == "bodeguero" and hasattr(qs.model, "usuario"):
            return qs.filter(usuario=request.user)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        r = rol_name(request.user)
        if db_field.name in ("usuario", "responsable"):
            if request.user.is_superuser:
                return field
            if r == "encargado":
                field.queryset = User.objects.filter(is_active=True)
            elif r == "bodeguero":
                field.queryset = User.objects.filter(pk=request.user.pk)
        return field

# =====================================================
# ACCIÓN PERSONALIZADA
# =====================================================
@admin.action(description="Marcar órdenes de insumo como CERRADAS")
def marcar_cerrada(modeladmin, request, queryset):
    updated = queryset.update(estado="CERRADA")
    modeladmin.message_user(
        request, f"{updated} órdenes marcadas como cerradas.", messages.SUCCESS
    )

# =====================================================
# REGISTROS ADMIN
# =====================================================

@admin.register(Categoria)
class CategoriaAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Bodega)
class BodegaAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "nombre", "direccion")
    search_fields = ("nombre", "direccion")
    ordering = ("nombre",)


@admin.register(Ubicacion)
class UbicacionAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "nombre", "tipo", "bodega")
    search_fields = ("nombre", "bodega__nombre")
    list_filter = ("bodega",)
    list_select_related = ("bodega",)
    ordering = ("bodega", "nombre")


@admin.register(Insumo)
class InsumoAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "nombre", "categoria", "unidad_medida", "stock_minimo", "stock_maximo")
    search_fields = ("nombre", "categoria__nombre")
    list_filter = ("categoria",)
    list_select_related = ("categoria",)
    ordering = ("nombre",)


@admin.register(InsumoLote)
class InsumoLoteAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "insumo", "bodega", "fecha_ingreso", "cantidad_actual", "usuario")
    search_fields = ("insumo__nombre", "bodega__nombre")
    list_filter = ("bodega", "fecha_ingreso")
    list_select_related = ("insumo", "bodega", "usuario")
    ordering = ("-fecha_ingreso",)


@admin.register(Entrada)
class EntradaAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "insumo", "ubicacion", "cantidad", "fecha", "usuario", "tipo")
    list_filter = ("fecha", "tipo", "usuario")
    search_fields = ("insumo__nombre", "usuario__email")
    date_hierarchy = "fecha"
    autocomplete_fields = ("usuario", "ubicacion")
    ordering = ("-fecha",)


@admin.register(Salida)
class SalidaAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "insumo", "ubicacion", "cantidad", "fecha_generada", "usuario", "tipo")
    list_filter = ("fecha_generada", "tipo", "usuario")
    search_fields = ("insumo__nombre", "usuario__email")
    date_hierarchy = "fecha_generada"
    autocomplete_fields = ("usuario", "ubicacion")
    ordering = ("-fecha_generada",)


@admin.register(AlertaInsumo)
class AlertaInsumoAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "insumo", "tipo", "mensaje", "fecha")
    list_filter = ("tipo", "fecha")
    search_fields = ("insumo__nombre", "mensaje")
    date_hierarchy = "fecha"
    ordering = ("-fecha",)


@admin.register(OrdenInsumo)
class OrdenInsumoAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "usuario", "fecha", "estado")
    list_filter = ("estado", "fecha")
    search_fields = ("usuario__email", "estado")
    ordering = ("-fecha",)
    autocomplete_fields = ("usuario",)
    actions = [marcar_cerrada]


@admin.register(OrdenInsumoDetalle)
class OrdenInsumoDetalleAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "orden_insumo", "insumo", "cantidad_solicitada")
    list_filter = ("orden_insumo", "insumo")
    search_fields = ("insumo__nombre",)
    list_select_related = ("orden_insumo", "insumo")
    ordering = ("orden_insumo",)


@admin.register(Ordenresumen)
class OrdenresumenAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
    ordering = ("nombre",)
