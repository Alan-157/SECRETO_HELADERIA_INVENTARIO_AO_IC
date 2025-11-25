from datetime import date
import re
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
    UnidadMedida
)


TIPO_CHOICES = (("ENTRADA", "Entrada"), ("SALIDA", "Salida"))


# ==========================================
#  CATEGORÍAS
# ==========================================
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

        # Validar que solo contenga letras
        if re.search(r"\d", nombre):
            raise forms.ValidationError("El nombre no puede contener números.")

        if not re.match(r"^[A-Za-zÁÉÍÓÚñÑáéíóú\s]+$", nombre):
            raise forms.ValidationError("El nombre solo puede contener letras y espacios.")

        qs = Categoria.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe una categoría con este nombre.")

        return nombre


# ==========================================
#  INSUMOS
# ==========================================
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
            "precio_unitario": forms.NumberInput(attrs={
                "class": "form-control",
                "max": "99999", # Límite de 5 dígitos
                "oninput": "if(this.value.length>5)this.value=this.value.slice(0,5)"
            }),
        }
    
    def clean_nombre(self):
        """Asegura que no existan insumos con el mismo nombre (case-insensitive)."""
        nombre = self.cleaned_data["nombre"].strip()
        qs = Insumo.objects.filter(nombre__iexact=nombre)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe otro insumo con este nombre.")
        return nombre

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
        MAX_VALUE = 99999
        
        if precio is not None:
            if precio < 0:
                raise forms.ValidationError("El precio unitario no puede ser negativo.")
            
            if precio > MAX_VALUE:
                raise forms.ValidationError(f"El precio unitario no puede exceder los {MAX_VALUE:,} (5 dígitos).")
                
        return precio

    # -----------------------------------------------------
    # VALIDACIÓN CRUZADA: Stock Mínimo < Stock Máximo
    # -----------------------------------------------------
    def clean(self):
        cleaned_data = super().clean()
        minimo = cleaned_data.get("stock_minimo")
        maximo = cleaned_data.get("stock_maximo")

        # Solo validamos si ambos campos pasaron su clean_campo individual
        if minimo is not None and maximo is not None:
            if minimo >= maximo:
                # Usamos add_error para asociar el error a un campo específico
                self.add_error(
                    'stock_minimo', 
                    'El Stock Mínimo debe ser estrictamente menor que el Stock Máximo.'
                )
                self.add_error(
                    'stock_maximo', 
                    'El Stock Máximo debe ser mayor que el Stock Mínimo.'
                )

        return cleaned_data


#UNIDAD DE MEDIDA
class UnidadMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadMedida
        fields = ("nombre_corto", "nombre_largo")
        widgets = {
            "nombre_corto": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: KG"}),
            "nombre_largo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Kilogramos"}),
        }

# ==========================================
#  MOVIMIENTOS (Entradas / Salidas)
# ==========================================
class EntradaForm(forms.ModelForm):
    cantidad = forms.DecimalField(
        label="Cantidad",
        validators=[
            MinValueValidator(0.01, message="La cantidad debe ser mayor que cero."),
            MaxValueValidator(99999, message="La cantidad no puede exceder 99.999."),
        ],
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "max": "99999.99",
            "oninput": "this.value = this.value.replace(/[^0-9.]/g,'')"
        }),
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
        validators=[
            MinValueValidator(0.01, message="La cantidad debe ser mayor que cero."),
            MaxValueValidator(99999, message="La cantidad no puede exceder 99.999."),
        ],
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "oninput": "this.value = this.value.replace(/[^0-9.]/g,'')"
        }),
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


# ==========================================
#  ÓRDENES
# ==========================================
class OrdenInsumoDetalleForm(forms.ModelForm):
    class Meta:
        model = OrdenInsumoDetalle
        fields = ("insumo", "cantidad_solicitada")
        widgets = {
            "insumo": forms.Select(attrs={"class": "form-select"}),
            "cantidad_solicitada": forms.NumberInput(
                attrs={"class": "form-control", "min": "0.01", "step": "0.01"}
            ),
        }

    def clean_cantidad_solicitada(self):
        v = self.cleaned_data.get("cantidad_solicitada")
        if v is None or v <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0.")
        return v


class BaseOrdenDetalleFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        insumos_vistos = set()
        count_valid = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cd = form.cleaned_data

            if cd.get("DELETE", False):
                continue

            insumo = cd.get("insumo")
            cantidad = cd.get("cantidad_solicitada")

            if not insumo and not cantidad:
                continue

            count_valid += 1

            if insumo:
                if insumo.id in insumos_vistos:
                    form.add_error(
                        "insumo",
                        f"El insumo '{insumo.nombre}' está duplicado en la orden."
                    )
                else:
                    insumos_vistos.add(insumo.id)

        if count_valid == 0:
            raise forms.ValidationError("Debes agregar al menos un ítem a la orden.")


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


# ==========================================
#  MULTI-LÍNEA MOVIMIENTOS
# ==========================================
class MovimientoLineaForm(forms.Form):
    tipo = forms.ChoiceField(choices=TIPO_CHOICES, initial="ENTRADA", label="Tipo")
    insumo = forms.ModelChoiceField(queryset=Insumo.objects.filter(is_active=True), label="Insumo")
    insumo_lote = forms.ModelChoiceField(
        queryset=InsumoLote.objects.select_related("insumo", "bodega"),
        required=False,
        label="Lote existente",
    )
    crear_nuevo_lote = forms.BooleanField(required=False, label="Crear nuevo lote")
    fecha_expiracion = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Fecha de expiración"
    )

    ubicacion = forms.ModelChoiceField(queryset=Ubicacion.objects.select_related("bodega"), label="Ubicación")
    cantidad = forms.DecimalField(
        min_value=0.01,
        label="Cantidad",
        validators=[MinValueValidator(0.01, "La cantidad debe ser mayor a cero.")],
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    fecha = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label="Fecha")
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Observaciones")


    def clean_fecha(self):
        fecha_mov = self.cleaned_data.get("fecha")

        if fecha_mov and fecha_mov < date.today():
            fecha_ini = self.initial.get("fecha")
            if not fecha_ini or fecha_mov != fecha_ini:
                raise forms.ValidationError("La fecha del movimiento no puede ser pasada.")
        return fecha_mov


    def clean(self):
        cd = super().clean()
        tipo = cd.get("tipo")
        lote = cd.get("insumo_lote")
        cant = cd.get("cantidad")
        crear = cd.get("crear_nuevo_lote")
        fexp = cd.get("fecha_expiracion")
        fecha = cd.get("fecha")

        if tipo == "ENTRADA":
            if not lote and not crear:
                raise forms.ValidationError("Debes seleccionar un lote o crear uno nuevo.")

            if crear and not fexp:
                self.add_error("fecha_expiracion", "Requerida al crear un lote.")

            if crear and fexp and fecha and fexp < fecha:
                self.add_error("fecha_expiracion", "La expiración no puede ser antes de la fecha de entrada.")

        else:  # SALIDA
            if crear:
                self.add_error("crear_nuevo_lote", "No aplica para SALIDA.")

            if not lote:
                self.add_error("insumo_lote", "Debes indicar el lote.")

            if lote and cant and cant > lote.cantidad_actual:
                self.add_error(
                    "cantidad",
                    f"Stock insuficiente. Stock actual: {lote.cantidad_actual}."
                )

        return cd


MovimientoLineaFormSet = formset_factory(MovimientoLineaForm, extra=1, can_delete=True)


# ==========================================
#  BODEGAS
# ==========================================
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

        if re.search(r"\d", nombre):
            raise forms.ValidationError("El nombre no puede contener números.")

        qs = Bodega.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe una bodega con este nombre.")

        return nombre
