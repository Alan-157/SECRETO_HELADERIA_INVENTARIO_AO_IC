from datetime import date
from django.contrib import admin, messages
from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

from .models import (
    Categoria, Insumo, UnidadMedida,
    Ubicacion, Bodega,
    Proveedor,
    InsumoLote, Entrada, Salida,
    AlertaInsumo,
    OrdenInsumo, OrdenInsumoDetalle,
)

User = get_user_model()

# =====================================================
# FORMULARIOS ADMIN CON VALIDACIONES
# =====================================================

class EntradaAdminForm(forms.ModelForm):
    """Validaciones adicionales para Entrada en admin."""
    cantidad = forms.DecimalField(
        validators=[
            MinValueValidator(0.01, message="La cantidad a ingresar debe ser mayor que cero.")
        ],
        label="Cantidad"
    )

    class Meta:
        model = Entrada
        fields = "__all__"

    def clean_fecha(self):
        f = self.cleaned_data.get("fecha")
        if f and f < date.today():
            raise forms.ValidationError("La fecha de la entrada no puede ser anterior a hoy.")
        return f


class SalidaAdminForm(forms.ModelForm):
    """Validaciones adicionales para Salida en admin."""
    cantidad = forms.DecimalField(
        validators=[
            MinValueValidator(0.01, message="La cantidad de salida debe ser mayor que cero.")
        ],
        label="Cantidad"
    )

    class Meta:
        model = Salida
        fields = "__all__"

    def clean_fecha_generada(self):
        f = self.cleaned_data.get("fecha_generada")
        if f and f < date.today():
            raise forms.ValidationError("La fecha de la salida no puede ser anterior a hoy.")
        return f

    def clean(self):
        cd = super().clean()
        lote = cd.get("insumo_lote")
        cant = cd.get("cantidad")

        if lote and cant and cant > (lote.cantidad_actual or 0):
            raise ValidationError({
                "cantidad": f"Stock insuficiente. Stock actual del lote: {lote.cantidad_actual}."
            })
        return cd


# =====================================================
# MIXIN PERMISOS POR ROL + SOFT DELETE EN ADMIN
# =====================================================

def rol_name(user):
    try:
        return (user.rol.nombre or "").lower()
    except Exception:
        return ""


class RoleScopedInventarioAdminMixin:
    """
    Controla permisos por rol y evita hard delete:
    - delete() => soft delete (is_active=False)
    """
    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request):
        r = rol_name(request.user)
        if request.user.is_superuser:
            return True
        return r == "encargado"

    def has_change_permission(self, request, obj=None):
        r = rol_name(request.user)
        if request.user.is_superuser:
            return True
        return r == "encargado"

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        r = rol_name(request.user)
        if request.user.is_superuser or r == "encargado":
            return qs
        if r == "bodeguero" and hasattr(qs.model, "usuario"):
            return qs.filter(usuario=request.user)
        return qs

    def delete_model(self, request, obj):
        """Admin delete => soft delete."""
        if hasattr(obj, "is_active"):
            obj.is_active = False
            obj.save(update_fields=["is_active"])
        else:
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Admin bulk delete => soft delete."""
        for obj in queryset:
            if hasattr(obj, "is_active"):
                obj.is_active = False
                obj.save(update_fields=["is_active"])
            else:
                obj.delete()


@admin.action(description="Marcar órdenes de insumo como CERRADAS")
def marcar_cerrada(modeladmin, request, queryset):
    updated = queryset.update(estado="CERRADA")
    modeladmin.message_user(
        request, f"{updated} órdenes marcadas como cerradas.", messages.SUCCESS
    )


# =====================================================
# ADMIN REGISTERS
# =====================================================

@admin.register(Categoria)
class CategoriaAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display  = ("id", "nombre", "is_active", "created_at")
    search_fields = ("nombre",)
    list_filter   = ("is_active",)
    ordering      = ("nombre",)


@admin.register(UnidadMedida)
class UnidadMedidaAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display  = ("id", "codigo", "nombre", "is_active")
    search_fields = ("codigo", "nombre")
    list_filter   = ("is_active",)
    ordering      = ("codigo",)


@admin.register(Proveedor)
class ProveedorAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display  = ("id", "nombre_empresa", "is_active")
    search_fields = ("nombre_empresa",)
    list_filter   = ("is_active",)
    ordering      = ("nombre_empresa",)


@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    # Bodega tiene: nombre, ubicacion, is_active, created_at
    list_display = ("id", "nombre", "ubicacion", "is_active", "created_at")
    list_filter = ("is_active", "ubicacion")
    search_fields = ("nombre", "ubicacion__nombre", "ubicacion__direccion")
    autocomplete_fields = ("ubicacion",)


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    # Ubicacion tiene: nombre, direccion, tipo, is_active
    list_display = ("id", "nombre", "direccion", "tipo", "is_active")
    list_filter = ("tipo", "is_active")
    search_fields = ("nombre", "direccion")


@admin.register(Insumo)
class InsumoAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display  = ("id", "nombre", "categoria", "unidad_medida", "precio_unitario", "is_active")
    search_fields = ("nombre", "categoria__nombre")
    list_filter   = ("categoria", "unidad_medida", "is_active")
    ordering      = ("nombre",)
    autocomplete_fields = ("categoria", "unidad_medida")


@admin.register(InsumoLote)
class InsumoLoteAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display = (
        "id", "insumo", "bodega", "proveedor",
        "fecha_ingreso", "fecha_expiracion",
        "cantidad_inicial", "cantidad_actual",
        "usuario", "is_active"
    )
    list_filter   = ("bodega", "insumo", "proveedor", "fecha_expiracion", "is_active")
    search_fields = ("insumo__nombre", "bodega__nombre", "proveedor__nombre_empresa", "usuario__email")
    ordering      = ("-fecha_ingreso",)
    autocomplete_fields = ("insumo", "bodega", "proveedor", "usuario")


class OrdenInsumoDetalleInline(admin.TabularInline):
    model = OrdenInsumoDetalle
    extra = 0
    autocomplete_fields = ("insumo",)


@admin.register(OrdenInsumo)
class OrdenInsumoAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display    = ("id", "usuario", "fecha", "estado", "is_active")
    list_filter     = ("estado", "fecha", "is_active")
    search_fields   = ("usuario__name", "usuario__email")
    date_hierarchy  = "fecha"
    ordering        = ("-fecha",)
    actions         = [marcar_cerrada]
    inlines         = [OrdenInsumoDetalleInline]
    autocomplete_fields = ("usuario",)


@admin.register(OrdenInsumoDetalle)
class OrdenInsumoDetalleAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    # El FK real es orden_insumo
    list_display = ("id", "orden_insumo", "insumo", "cantidad_solicitada", "is_active")
    list_filter  = ("orden_insumo", "insumo", "is_active")
    search_fields = ("orden_insumo__id", "insumo__nombre")
    autocomplete_fields = ("orden_insumo", "insumo")
    ordering = ("-id",)


@admin.register(Entrada)
class EntradaAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    form = EntradaAdminForm
    list_display = ("id", "insumo", "cantidad", "fecha", "ubicacion", "usuario")
    list_filter = ("fecha", "ubicacion", "insumo_lote__bodega")
    search_fields = ("insumo__nombre", "ubicacion__nombre", "ubicacion__direccion")
    autocomplete_fields = ("insumo", "insumo_lote", "ubicacion", "usuario")
    date_hierarchy = "fecha"
    ordering      = ("-fecha",)


@admin.register(Salida)
class SalidaAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    form = SalidaAdminForm
    list_display = ("id", "insumo", "cantidad", "fecha_generada", "ubicacion", "usuario")
    list_filter = ("fecha_generada", "ubicacion", "insumo_lote__bodega")
    search_fields = ("insumo__nombre", "ubicacion__nombre", "ubicacion__direccion")
    autocomplete_fields = ("insumo", "insumo_lote", "ubicacion", "usuario")
    date_hierarchy = "fecha_generada"
    ordering      = ("-fecha_generada",)


@admin.register(AlertaInsumo)
class AlertaInsumoAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    list_display  = ("id", "insumo", "tipo", "fecha", "is_active")
    list_filter   = ("tipo", "fecha", "is_active")
    search_fields = ("insumo__nombre", "mensaje")
    ordering      = ("-fecha",)
    autocomplete_fields = ("insumo",)
