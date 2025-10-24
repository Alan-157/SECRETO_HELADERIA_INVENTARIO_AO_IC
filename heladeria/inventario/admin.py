
from django.contrib import admin, messages
from django import forms
from datetime import date
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from .models import (
    Categoria, Insumo, Ubicacion, Bodega,
    InsumoLote, Entrada, Salida, AlertaInsumo,
    OrdenInsumo, OrdenInsumoDetalle
)

# 👇 --- IMPORTACIONES ADICIONALES PARA VALIDACIONES ---
from django import forms
from datetime import date
from django.core.validators import MinValueValidator

User = get_user_model()
# --- FORMULARIOS DE ADMIN PERSONALIZADOS CON VALIDACIONES ---

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
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "is_active", "created_at")
    search_fields = ("nombre",)
    list_filter = ("is_active",)
    ordering = ("nombre",)

@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "direccion", "is_active")
    search_fields = ("nombre", "direccion")
    list_filter = ("is_active",)

@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "bodega", "tipo", "is_active")
    list_filter = ("bodega", "tipo", "is_active")
    search_fields = ("nombre",)

class OrdenInsumoDetalleInline(admin.TabularInline):
    model = OrdenInsumoDetalle
    extra = 0

@admin.register(OrdenInsumo)
class OrdenInsumoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "fecha", "estado")
    list_filter = ("estado", "fecha")
    search_fields = ("usuario__name", "usuario__email")
    date_hierarchy = "fecha"
    inlines = [OrdenInsumoDetalleInline]

@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "categoria", "unidad_medida", "precio_unitario", "is_active")
    search_fields = ("nombre",)
    list_filter = ("categoria", "is_active")

@admin.register(InsumoLote)
class InsumoLoteAdmin(admin.ModelAdmin):
    list_display = ("id", "insumo", "bodega", "fecha_ingreso", "fecha_expiracion",
                    "cantidad_inicial", "cantidad_actual", "usuario", "is_active")
    list_filter = ("bodega", "insumo", "fecha_expiracion", "is_active")
    search_fields = ("insumo__nombre",)

@admin.register(Entrada)
class EntradaAdmin(admin.ModelAdmin):
    list_display = ("id", "insumo", "insumo_lote", "ubicacion", "cantidad",
                    "fecha", "usuario", "orden", "detalle")
    list_filter = ("fecha", "usuario", "ubicacion__bodega", "insumo")
    search_fields = ("insumo__nombre", "usuario__email")
    date_hierarchy = "fecha"

@admin.register(Salida)
class SalidaAdmin(admin.ModelAdmin):
    list_display = ("id", "insumo", "insumo_lote", "ubicacion", "cantidad",
                    "fecha_generada", "usuario", "orden", "detalle")
    list_filter = ("fecha_generada", "usuario", "ubicacion__bodega", "insumo")
    search_fields = ("insumo__nombre", "usuario__email")
    date_hierarchy = "fecha_generada"