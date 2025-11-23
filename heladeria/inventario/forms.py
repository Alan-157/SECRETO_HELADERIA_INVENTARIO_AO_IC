from datetime import date
from django import forms
from django.core.validators import MinValueValidator
from django.forms import (
    inlineformset_factory,
    BaseInlineFormSet,
    formset_factory,
)
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

TIPO_CHOICES = (("ENTRADA", "Entrada"), ("SALIDA", "Salida"))

# -------------------------------------------------
# CATEGORÍAS
# -------------------------------------------------
class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "is_active"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        qs = Categoria.objects.filter(nombre__iexact=nombre)

        # Si estamos editando, excluir la categoría actual
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe una categoría con este nombre.")
        return nombre

# -------------------------------------------------
# INSUMOS
# -------------------------------------------------
class InsumoForm(forms.ModelForm):
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
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "stock_minimo": forms.NumberInput(attrs={"class": "form-control"}),
            "stock_maximo": forms.NumberInput(attrs={"class": "form-control"}),
            "unidad_medida": forms.Select(attrs={"class": "form-select"}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean_stock_minimo(self):
        minimo = self.cleaned_data.get("stock_minimo")
        if minimo is not None and minimo < 0:
            raise forms.ValidationError("El stock mínimo no puede ser negativo.")
        return minimo

    def clean_stock_maximo(self):
        maximo = self.cleaned_data.get("stock_maximo")
        if maximo is not None and maximo < 0:
            raise forms.ValidationError("El stock máximo no puede ser negativo.")
        return maximo

    def clean_precio_unitario(self):
        precio = self.cleaned_data.get("precio_unitario")
        if precio is not None and precio < 0:
            raise forms.ValidationError("El precio unitario no puede ser negativo.")
        return precio


class UnidadMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadMedida
        fields = ("nombre_corto", "nombre_largo")
        widgets = {
            "nombre_corto": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: KG"}),
            "nombre_largo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Kilogramos"}),
        }

# -------------------------------------------------
# MOVIMIENTOS
# -------------------------------------------------
class EntradaForm(forms.ModelForm):
    # Validación positiva con DecimalField
    cantidad = forms.DecimalField(
        label="Cantidad",
        validators=[MinValueValidator(0.01, message="La cantidad debe ser mayor que cero.")],
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Entrada
        exclude = ["usuario"]
        widgets = {
            "insumo": forms.Select(attrs={"class": "form-select"}),
            "insumo_lote": forms.Select(attrs={"class": "form-select"}),
            "ubicacion": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tipo": forms.TextInput(attrs={"class": "form-control"}),
        }


class SalidaForm(forms.ModelForm):
    cantidad = forms.DecimalField(
        label="Cantidad",
        validators=[MinValueValidator(0.01, message="La cantidad debe ser mayor que cero.")],
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Salida
        exclude = ["usuario"]
        widgets = {
            "insumo": forms.Select(attrs={"class": "form-select"}),
            "insumo_lote": forms.Select(attrs={"class": "form-select"}),
            "ubicacion": forms.Select(attrs={"class": "form-select"}),
            "fecha_generada": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "tipo": forms.TextInput(attrs={"class": "form-control"}),
        }


# -------------------------------------------------
# ÓRDENES (DETALLE)
# -------------------------------------------------
class OrdenInsumoDetalleForm(forms.ModelForm):
    class Meta:
        model = OrdenInsumoDetalle
        fields = ("insumo", "cantidad_solicitada")
        widgets = {
            "insumo": forms.Select(attrs={"class": "form-select"}),
            "cantidad_solicitada": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "0.00", "min": "0.01", "step": "0.01"}
            ),
        }

    def clean_cantidad_solicitada(self):
        v = self.cleaned_data.get("cantidad_solicitada")
        if v is None or v <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0.")
        return v

# Formset base para validar al menos 1 ítem
class BaseOrdenDetalleFormSet(BaseInlineFormSet):
    """Asegura que haya al menos 1 ítem válido e ignora filas vacías."""
    def clean(self):
        super().clean()
        count_valid = 0
        for form in self.forms:
            if getattr(form, "cleaned_data", None) is None:
                continue
            if form.cleaned_data.get("DELETE", False):
                continue
            insumo = form.cleaned_data.get("insumo")
            cant = form.cleaned_data.get("cantidad_solicitada")
            if insumo and cant:
                count_valid += 1
        if count_valid == 0:
            raise forms.ValidationError("Debes agregar al menos un ítem a la orden.")


# Formset para CREAR (sin eliminar filas)
OrdenInsumoDetalleCreateFormSet = inlineformset_factory(
    OrdenInsumo,
    OrdenInsumoDetalle,
    form=OrdenInsumoDetalleForm,
    formset=BaseOrdenDetalleFormSet,
    extra=1,
    can_delete=False,
)

# Formset para EDITAR (permitir eliminar filas existentes)
OrdenInsumoDetalleEditFormSet = inlineformset_factory(
    OrdenInsumo,
    OrdenInsumoDetalle,
    form=OrdenInsumoDetalleForm,
    formset=BaseOrdenDetalleFormSet,
    extra=0,
    can_delete=True,
)


# -------------------------------------------------
# Formulario de línea para movimientos múltiples (UI avanzada)
# -------------------------------------------------

class MovimientoLineaForm(forms.Form):
    tipo = forms.ChoiceField(choices=TIPO_CHOICES, initial="ENTRADA", label="Tipo")
    insumo = forms.ModelChoiceField(queryset=Insumo.objects.filter(is_active=True), label="Insumo")
    insumo_lote = forms.ModelChoiceField(
        queryset=InsumoLote.objects.select_related("insumo", "bodega"),
        required=False,
        label="Lote existente",
    )
    crear_nuevo_lote = forms.BooleanField(required=False, initial=False, label="Crear nuevo lote")
    fecha_expiracion = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Fecha de expiración (nuevo lote)")

    ubicacion = forms.ModelChoiceField(queryset=Ubicacion.objects.select_related("bodega"), label="Ubicación")
    cantidad = forms.DecimalField(
        min_value=0.01,
        label="Cantidad",
        validators=[MinValueValidator(0.01, message="La cantidad debe ser mayor que cero.")],
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    fecha = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label="Fecha")
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Observaciones")

    def clean_fecha(self):
        """
        Permite mantener una fecha pasada cuando se edita un movimiento,
        pero impide ingresar una NUEVA fecha pasada al crear o al cambiar la fecha.
        """
        fecha_mov = self.cleaned_data.get("fecha")
        if not fecha_mov:
            return fecha_mov

        if fecha_mov < date.today():
            # Si la fecha ya venía así (edición sin cambiar la fecha), se permite.
            fecha_inicial = self.initial.get("fecha")
            if not fecha_inicial or fecha_mov != fecha_inicial:
                raise forms.ValidationError(
                    "La fecha del movimiento no puede ser anterior al día de hoy."
                )
        return fecha_mov

    def clean(self):
        cd = super().clean()
        tipo  = cd.get("tipo")
        lote  = cd.get("insumo_lote")
        cant  = cd.get("cantidad")
        crear = cd.get("crear_nuevo_lote")
        fexp  = cd.get("fecha_expiracion")
        fecha = cd.get("fecha")

        if tipo == "ENTRADA":
            if not lote and not crear:
                raise forms.ValidationError(
                    "Para una ENTRADA selecciona un lote existente o marca 'Crear nuevo lote'."
                )
            if crear and not fexp:
                self.add_error("fecha_expiracion", "Requerida para crear un nuevo lote.")
            # Expiración no puede ser anterior a la fecha de entrada (tanto en creación como edición)
            if crear and fexp and fecha and fexp < fecha:
                self.add_error(
                    "fecha_expiracion",
                    "La fecha de expiración no puede ser anterior a la fecha de entrada."
                )
        else:  # SALIDA
            if crear:
                self.add_error("crear_nuevo_lote", "No aplica para SALIDA.")
            if not lote:
                self.add_error("insumo_lote", "Para una SALIDA debes indicar el lote.")
            if lote and cant and cant > lote.cantidad_actual:
                self.add_error(
                    "cantidad",
                    f"Error: Stock insuficiente. El stock actual del lote es {lote.cantidad_actual}."
                )
        return cd



MovimientoLineaFormSet = formset_factory(MovimientoLineaForm, extra=1, can_delete=True)


# -------------------------------------------------
# BODEGAS
# -------------------------------------------------

class BodegaForm(forms.ModelForm):
    class Meta:
        model = Bodega
        fields = ("nombre", "direccion")
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de la bodega"}),
            "direccion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Dirección"}),
        }
    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        qs = Bodega.objects.filter(nombre__iexact=nombre)

        # Si editamos, excluir esta misma bodega
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe una bodega con este nombre.")
        return nombre