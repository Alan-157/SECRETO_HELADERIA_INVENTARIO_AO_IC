from datetime import date
import re
from decimal import Decimal
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.forms import inlineformset_factory, BaseInlineFormSet, formset_factory
from .models import (
    Bodega,
    Categoria,
    Entrada,
    Insumo,
    InsumoLote,
    OrdenInsumo,
    OrdenInsumoDetalle,
    Salida,
    Ubicacion,
    UnidadMedida,
)


# ============================================================
#   HELPERS / BASE CLASSES
# ============================================================

class OnlyActiveModelChoice(forms.ModelChoiceField):
    """ModelChoiceField que solo muestra registros is_active=True"""
    def __init__(self, queryset, *args, **kwargs):
        qs = queryset.filter(is_active=True)
        super().__init__(qs, *args, **kwargs)


class BaseCleanNameMixin:
    """Valida que un nombre no tenga números y solo letras/espacios."""
    def _clean_name(self, field_name="nombre"):
        nombre = self.cleaned_data[field_name].strip()

        if re.search(r"\d", nombre):
            raise forms.ValidationError("El nombre no puede contener números.")

        if not re.match(r"^[A-Za-zÁÉÍÓÚñÑáéíóú\s]+$", nombre):
            raise forms.ValidationError("El nombre solo puede contener letras y espacios.")

        return nombre


class BaseModelForm(forms.ModelForm):
    """Base para todos los CRUD, agrega clase .form-control automáticamente."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget

            # No modificar checkboxes
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                continue

            classes = widget.attrs.get("class", "")
            widget.attrs["class"] = (classes + " form-control").strip()


class BasePositiveNumberMixin:
    """Validación estandarizada para campos numéricos positivos."""
    def _clean_positive(self, field_name, max_value=None):
        value = self.cleaned_data.get(field_name)

        if value is None or value < 0:
            raise forms.ValidationError("El valor debe ser un número positivo.")

        if max_value and value > max_value:
            raise forms.ValidationError(f"El valor no puede exceder {max_value}.")

        return value


# ============================================================
#   CATEGORÍA
# ============================================================

class CategoriaForm(BaseModelForm, BaseCleanNameMixin):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "is_active"]

    def clean_nombre(self):
        nombre = self._clean_name("nombre")

        qs = Categoria.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe una categoría con este nombre.")

        return nombre


# ============================================================
#   INSUMO
# ============================================================

class InsumoForm(BaseModelForm, BaseCleanNameMixin, BasePositiveNumberMixin):
    class Meta:
        model = Insumo
        fields = [
            "nombre",
            "categoria",
            "stock_minimo",
            "stock_maximo",
            "unidad_medida",
            "precio_unitario",
        ]

    def clean_nombre(self):
        nombre = self._clean_name("nombre")

        qs = Insumo.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe otro insumo con este nombre.")

        return nombre

    def clean_stock_minimo(self):
        return self._clean_positive("stock_minimo")

    def clean_stock_maximo(self):
        maximo = self._clean_positive("stock_maximo")
        minimo = self.cleaned_data.get("stock_minimo")

        if minimo is not None and maximo < minimo:
            raise forms.ValidationError("El stock máximo no puede ser menor que el stock mínimo.")

        return maximo

    def clean_precio_unitario(self):
        return self._clean_positive("precio_unitario", max_value=99999)


# ============================================================
#   MOVIMIENTOS: Entradas y Salidas
# ============================================================

class EntradaForm(BaseModelForm):
    cantidad = forms.DecimalField(
        label="Cantidad",
        validators=[MinValueValidator(0.01), MaxValueValidator(99999)],
        widget=forms.NumberInput(attrs={"max": "99999.99"}),
    )

    class Meta:
        model = Entrada
        exclude = ["usuario"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }


class SalidaForm(BaseModelForm):
    cantidad = forms.DecimalField(
        label="Cantidad",
        validators=[MinValueValidator(0.01), MaxValueValidator(99999)],
    )

    class Meta:
        model = Salida
        exclude = ["usuario"]
        widgets = {
            "fecha_generada": forms.DateInput(attrs={"type": "date"}),
        }


# ============================================================
#   ORDENES DE INSUMO
# ============================================================

class OrdenInsumoDetalleForm(BaseModelForm):
    class Meta:
        model = OrdenInsumoDetalle
        fields = ("insumo", "cantidad_solicitada")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Añadir data-unidad a cada option del select
        qs = self.fields["insumo"].queryset.select_related("unidad_medida")
        self.fields["insumo"].choices = [
            (
                i.pk,
                f"{i.nombre}",
                {"data-unidad": i.unidad_medida.codigo}
            )
            for i in qs
        ]


class BaseOrdenDetalleFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        insumos_usados = set()
        count = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            data = form.cleaned_data

            if data.get("DELETE"):
                continue

            insumo = data.get("insumo")
            cantidad = data.get("cantidad_solicitada")

            if not insumo and not cantidad:
                continue

            count += 1

            if insumo:
                if insumo.id in insumos_usados:
                    form.add_error("insumo", "Este insumo ya está incluido en la orden.")
                else:
                    insumos_usados.add(insumo.id)

        if count == 0:
            raise forms.ValidationError("Debe ingresar al menos un ítem.")

OrdenInsumoDetalleCreateFormSet = inlineformset_factory(
    OrdenInsumo,
    OrdenInsumoDetalle,
    form=OrdenInsumoDetalleForm,
    formset=BaseOrdenDetalleFormSet,
    extra=1,
    can_delete=False,
)

OrdenInsumoDetalleEditFormSet = inlineformset_factory(
    OrdenInsumo,
    OrdenInsumoDetalle,
    form=OrdenInsumoDetalleForm,
    formset=BaseOrdenDetalleFormSet,
    extra=0,
    can_delete=True,
)


class OrdenInsumoForm(BaseModelForm):
    class Meta:
        model = OrdenInsumo
        fields = ("tipo",)
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select js-orden-tipo"}),
        }


# ============================================================
#   BODEGAS
# ============================================================

class BodegaForm(BaseModelForm, BaseCleanNameMixin):
    class Meta:
        model = Bodega
        fields = ("nombre", "ubicacion", "descripcion", "is_active")
        widgets = {
            "ubicacion": forms.Select(attrs={"class": "form-select"}),
        }

# ============================================================
#   UBICACIONES
# ============================================================

class UbicacionForm(BaseModelForm, BaseCleanNameMixin):
    class Meta:
        model = Ubicacion
        fields = ["nombre", "direccion", "tipo", "is_active"]
        
# ============================================================
#   UNIDAD DE MEDIDA
# ===========================================================

class UnidadMedidaForm(BaseModelForm):

    class Meta:
        model = UnidadMedida
        fields = ("nombre", "codigo")  # ajusta si tu modelo tiene más campos visibles

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip().upper()
        if not codigo:
            raise forms.ValidationError("El código es obligatorio.")

        qs = UnidadMedida.objects.filter(codigo__iexact=codigo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe una unidad con este código.")

        return codigo

    def clean_nombre(self):
        nombre = self._clean_name("nombre")

        qs = UnidadMedida.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe una unidad con este nombre.")

        return nombre
    
# ============================================================
#   MOVIMIENTOS — FORMULARIO GENERAL + FORMSET (BD OFICIAL)
#   Flujo correcto: seleccionar BODEGA -> ubicación se deriva
# ============================================================

TIPO_MOVIMIENTO_CHOICES = [
    ("ENTRADA", "Entrada"),
    ("SALIDA", "Salida"),
    ("AJUSTE", "Ajuste de Stock"),
]

class MovimientoLineaForm(BasePositiveNumberMixin, forms.Form):
    tipo = forms.ChoiceField(
        label="Tipo",
        choices=TIPO_MOVIMIENTO_CHOICES,
        widget=forms.Select(attrs={"class": "form-select js-tipo"})
    )

    insumo = forms.ModelChoiceField(
        label="Insumo",
        queryset=Insumo.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            "class": "form-select js-insumo",
            "disabled": "disabled"
        }),
        required=False,
    )

    bodega = forms.ModelChoiceField(
        label="Bodega",
        queryset=Bodega.objects.filter(is_active=True).select_related("ubicacion"),
        widget=forms.Select(attrs={
            "class": "form-select js-bodega",
            "disabled": "disabled"
        }),
        required=False,
    )

    ubicacion = forms.ModelChoiceField(
        label="Ubicación",
        queryset=Ubicacion.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select js-ubicacion",
            "disabled": "disabled"
        })
    )

    insumo_lote = forms.ModelChoiceField(
        label="Lote existente",
        queryset=InsumoLote.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select js-lote",
            "disabled": "disabled"
        })
    )

    crear_nuevo_lote = forms.BooleanField(
        label="Crear nuevo lote",
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input js-nuevo-lote",
            "disabled": "disabled"
        })
    )

    fecha_expiracion = forms.DateField(
        label="Expiración (si es nuevo lote)",
        required=False,
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control js-expiracion",
            "disabled": "disabled"
        })
    )

    cantidad = forms.DecimalField(
        label="Cantidad",
        decimal_places=2,
        max_digits=10,
        validators=[MinValueValidator(Decimal("0.01"))],
        widget=forms.NumberInput(attrs={
            "class": "form-control js-cantidad",
            "step": "0.01",
            "disabled": "disabled"
        })
    )

    fecha = forms.DateField(
        label="Fecha",
        initial=date.today,
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control js-fecha",
            "readonly": "readonly",
            "disabled": "disabled"
        })
    )

    observaciones = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control js-obs",
            "rows": 3,   # más grande
            "disabled": "disabled",
            "style": "min-height:70px;"
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        data = self.data or None
        tipo = (data.get(self.add_prefix("tipo")) if data else None)
        insumo_id = (data.get(self.add_prefix("insumo")) if data else None)
        bodega_id = (data.get(self.add_prefix("bodega")) if data else None)

        # Filtrar lotes según selección
        lotes_qs = InsumoLote.objects.filter(is_active=True)
        if insumo_id:
            lotes_qs = lotes_qs.filter(insumo_id=insumo_id)
        if bodega_id:
            lotes_qs = lotes_qs.filter(bodega_id=bodega_id)
        self.fields["insumo_lote"].queryset = lotes_qs

        # Habilitar insumo cuando hay tipo
        if tipo in ("ENTRADA", "SALIDA", "AJUSTE"):
            self.fields["insumo"].required = True

        for f in self.fields.values():
            if "disabled" in f.widget.attrs:
                del f.widget.attrs["disabled"]

    def clean_cantidad(self):
        return self._clean_positive("cantidad")

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        insumo = cleaned.get("insumo")
        bodega = cleaned.get("bodega")
        lote = cleaned.get("insumo_lote")
        crear_nuevo = cleaned.get("crear_nuevo_lote")
        fecha = cleaned.get("fecha") or date.today()
        fexp = cleaned.get("fecha_expiracion")
        cantidad = cleaned.get("cantidad")

        # fecha fija hoy
        cleaned["fecha"] = date.today()

        # Derivar ubicacion desde bodega/lote
        if lote:
            cleaned["bodega"] = lote.bodega
            cleaned["ubicacion"] = lote.bodega.ubicacion
        elif bodega:
            cleaned["ubicacion"] = bodega.ubicacion

        if tipo == "ENTRADA":
            if not insumo:
                self.add_error("insumo", "Selecciona un insumo.")
            if not bodega:
                self.add_error("bodega", "Selecciona una bodega.")

            # Si crea nuevo, no debe venir lote existente
            if crear_nuevo and lote:
                self.add_error("insumo_lote", "Si creas nuevo lote no puedes elegir lote existente.")
            if not crear_nuevo and not lote:
                self.add_error("insumo_lote", "Selecciona lote existente o marca 'nuevo lote'.")

            if crear_nuevo:
                if not fexp:
                    self.add_error("fecha_expiracion", "Debes indicar fecha de expiración.")
                else:
                    hoy = date.today()
                    if fexp < hoy:
                        self.add_error("fecha_expiracion", "No puede ser menor a hoy.")
                    if fexp < fecha:
                        self.add_error("fecha_expiracion", "No puede ser menor a la fecha de ingreso.")

        if tipo == "SALIDA":
            if crear_nuevo:
                self.add_error("crear_nuevo_lote", "En salida no puedes crear lote nuevo.")
            if not lote:
                self.add_error("insumo_lote", "Debes elegir un lote existente.")
            else:
                # no sacar más de lo disponible
                if cantidad and lote.cantidad_actual < cantidad:
                    self.add_error("cantidad", f"No puedes retirar más de {lote.cantidad_actual}.")

        return cleaned


# ------------ FORMSET ------------
class BaseMovimientoLineaFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()

        tiene_lineas = any(
            form.cleaned_data and not form.cleaned_data.get("DELETE", False)
            for form in self.forms
        )
        if not tiene_lineas:
            raise forms.ValidationError("Debe ingresar al menos un movimiento.")


MovimientoLineaFormSet = formset_factory(
    MovimientoLineaForm,
    formset=BaseMovimientoLineaFormSet,
    extra=1,
    can_delete=True,
)

OrdenInsumoDetalleCreateFormSet = inlineformset_factory(
    OrdenInsumo,
    OrdenInsumoDetalle,
    form=OrdenInsumoDetalleForm,
    formset=BaseOrdenDetalleFormSet,
    extra=1,
    can_delete=False,
)

OrdenInsumoDetalleEditFormSet = inlineformset_factory(
    OrdenInsumo,
    OrdenInsumoDetalle,
    form=OrdenInsumoDetalleForm,
    formset=BaseOrdenDetalleFormSet,
    extra=0,
    can_delete=True,
)