
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from .models import (
    Categoria, Insumo, Ubicacion, Bodega,
    InsumoLote, Entrada, Salida, AlertaInsumo,
    OrdenInsumo, OrdenInsumoDetalle, Ordenresumen
)

# 👇 --- IMPORTACIONES ADICIONALES PARA VALIDACIONES ---
from django import forms
from datetime import date
from django.core.validators import MinValueValidator

User = get_user_model()


# =====================================================
# 👇 --- FORMULARIOS DE ADMIN PERSONALIZADOS CON VALIDACIONES ---
# =====================================================

class EntradaAdminForm(forms.ModelForm):
    """Formulario para el modelo Entrada en el admin con validaciones."""
    # 1. Validación de cantidad positiva (no puede ser 0 o negativo)
    cantidad = forms.DecimalField(
        validators=[MinValueValidator(0.01, message="La cantidad a ingresar debe ser un número positivo.")],
        label="Cantidad"
    )

    class Meta:
        model = Entrada
        fields = '__all__' # Incluye todos los campos del modelo en el form

    # 2. Validación de fecha (no puede ser una fecha pasada)
    def clean_fecha(self):
        fecha_entrada = self.cleaned_data.get('fecha')
        if fecha_entrada and fecha_entrada < date.today():
            raise forms.ValidationError("La fecha de la entrada no puede ser anterior al día de hoy.")
        return fecha_entrada


class SalidaAdminForm(forms.ModelForm):
    """Formulario para el modelo Salida en el admin con validaciones."""
    cantidad = forms.DecimalField(
        validators=[MinValueValidator(0.01, message="La cantidad de salida debe ser un número positivo.")],
        label="Cantidad"
    )

    class Meta:
        model = Salida
        fields = '__all__'

    # Validación de fecha (no puede ser una fecha pasada)
    def clean_fecha_generada(self):
        fecha_salida = self.cleaned_data.get('fecha_generada')
        if fecha_salida and fecha_salida < date.today():
            raise forms.ValidationError("La fecha de la salida no puede ser anterior al día de hoy.")
        return fecha_salida
    
    # Validación para no permitir stock negativo
    def clean(self):
        cleaned_data = super().clean()
        lote = cleaned_data.get('insumo_lote')
        cantidad_salida = cleaned_data.get('cantidad')

        if lote and cantidad_salida and cantidad_salida > lote.cantidad_actual:
            # Lanza un error asociado al campo 'cantidad'
            raise forms.ValidationError({
                'cantidad': f'Error: Stock insuficiente. El stock actual del lote es {lote.cantidad_actual}.'
            })
        return cleaned_data


# =====================================================
# MIXIN DE PERMISOS POR ROL (Sin cambios)
# =====================================================
# ... (tu mixin RoleScopedInventarioAdminMixin y la acción marcar_cerrada no cambian) ...
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

@admin.action(description="Marcar órdenes de insumo como CERRADAS")
def marcar_cerrada(modeladmin, request, queryset):
    updated = queryset.update(estado="CERRADA")
    modeladmin.message_user(
        request, f"{updated} órdenes marcadas como cerradas.", messages.SUCCESS
    )


# =====================================================
# REGISTROS ADMIN (MODIFICADOS)
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
    # 👇 ASIGNAMOS EL FORMULARIO PERSONALIZADO
    form = EntradaAdminForm
    list_display = ("id", "insumo", "ubicacion", "cantidad", "fecha", "usuario", "tipo")
    list_filter = ("fecha", "tipo", "usuario")
    search_fields = ("insumo__nombre", "usuario__email")
    date_hierarchy = "fecha"
    autocomplete_fields = ("usuario", "ubicacion")
    ordering = ("-fecha",)


@admin.register(Salida)
class SalidaAdmin(RoleScopedInventarioAdminMixin, admin.ModelAdmin):
    # 👇 ASIGNAMOS EL FORMULARIO PERSONALIZADO
    form = SalidaAdminForm
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