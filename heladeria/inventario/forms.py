from django import forms
# Importa el validador de valor mínimo
from django.core.validators import MinValueValidator
from .models import Bodega, Insumo, Categoria, Entrada, Salida, OrdenInsumo, OrdenInsumoDetalle, InsumoLote, Ubicacion
from django.forms import inlineformset_factory
from django.forms import formset_factory



TIPO_CHOICES = (("ENTRADA", "Entrada"), ("SALIDA", "Salida"))


# --- FORMULARIO DE CATEGORÍA (NUEVO) ---
class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'is_active']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# --- FORMULARIO DE INSUMO ---
class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = [
            'nombre', 'categoria', 'stock_minimo', 
            'stock_maximo', 'unidad_medida', 'precio_unitario'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_maximo': forms.NumberInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def clean_stock_minimo(self):
        minimo = self.cleaned_data.get('stock_minimo')
        if minimo is not None and minimo < 0:
            raise forms.ValidationError("El stock mínimo no puede ser negativo.")
        return minimo

# --- FORMULARIOS PARA MOVIMIENTOS (sin cambios) ---

class EntradaForm(forms.ModelForm):
    # Definimos 'cantidad' explícitamente para añadir el validador. El valor 0.01 asegura que la cantidad sea siempre un número positivo.
    cantidad = forms.DecimalField(
        label="Cantidad",
        validators=[MinValueValidator(0.01, message="La cantidad debe ser mayor que cero.")],
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Entrada
        exclude = ['usuario']
        widgets = {
            'insumo': forms.Select(attrs={'class': 'form-select'}),
            'insumo_lote': forms.Select(attrs={'class': 'form-select'}),
            'ubicacion': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo': forms.TextInput(attrs={'class': 'form-control'}),
        }


class SalidaForm(forms.ModelForm):
    cantidad = forms.DecimalField(
        label="Cantidad",
        validators=[MinValueValidator(0.01, message="La cantidad debe ser mayor que cero.")],
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Salida
        exclude = ['usuario']
        widgets = {
            'insumo': forms.Select(attrs={'class': 'form-select'}),
            'insumo_lote': forms.Select(attrs={'class': 'form-select'}),
            'ubicacion': forms.Select(attrs={'class': 'form-select'}),
            'fecha_generada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo': forms.TextInput(attrs={'class': 'form-control'}),
        }

# --- FORMSET PARA DETALLES DE ORDEN (MODIFICADO) ---

OrdenInsumoDetalleFormSet = inlineformset_factory(
    OrdenInsumo,
    OrdenInsumoDetalle,
    fields=('insumo', 'cantidad_solicitada'),
    # Aquí está la magia: le decimos que cree 5 filas vacías
    extra=5,
    # No necesitamos poder eliminar en un formulario de creación
    can_delete=False,
    widgets={
        'insumo': forms.Select(attrs={'class': 'form-select'}),
        'cantidad_solicitada': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
    }
)

class MovimientoLineaForm(forms.Form):
    tipo = forms.ChoiceField(choices=TIPO_CHOICES, initial="ENTRADA", label="Tipo")
    insumo = forms.ModelChoiceField(
        queryset=Insumo.objects.filter(is_active=True),
        label="Insumo"
    )
    # Lote existente (opcional en ENTRADA si se creará uno nuevo)
    insumo_lote = forms.ModelChoiceField(
        queryset=InsumoLote.objects.select_related("insumo","bodega"),
        required=False,
        label="Lote existente"
    )
    # Flag explícito para crear lote (solo ENTRADA)
    crear_nuevo_lote = forms.BooleanField(
        required=False, initial=False, label="Crear nuevo lote"
    )
    fecha_expiracion = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Fecha de expiración (nuevo lote)"
    )

    ubicacion = forms.ModelChoiceField(
        queryset=Ubicacion.objects.select_related("bodega"),
        label="Ubicación"
    )
    cantidad = forms.DecimalField(
        min_value=0.01,
        label="Cantidad",
        validators=[MinValueValidator(0.01, message="La cantidad debe ser mayor que cero.")],
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Fecha"
    )
    observaciones = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Observaciones"
    )

    def clean(self):
        cd = super().clean()
        tipo = cd.get("tipo")
        lote = cd.get("insumo_lote")
        crear = cd.get("crear_nuevo_lote")
        fexp = cd.get("fecha_expiracion")

        if tipo == "ENTRADA":
            if not lote and not crear:
                raise forms.ValidationError(
                    "Para una ENTRADA selecciona un lote existente o marca 'Crear nuevo lote'."
                )
            if crear and not fexp:
                self.add_error("fecha_expiracion", "Requerida para crear un nuevo lote.")
        else:  # SALIDA
            if crear:
                self.add_error("crear_nuevo_lote", "No aplica para SALIDA.")
            if not lote:
                self.add_error("insumo_lote", "Para una SALIDA debes indicar el lote.")
        return cd


MovimientoLineaFormSet = formset_factory(
    MovimientoLineaForm, extra=1, can_delete=True
)

# --- FORMULARIO DE BODEGA  ---
class BodegaForm(forms.ModelForm):
    class Meta:
        model = Bodega
        fields = ("nombre", "direccion")
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de la bodega"}),
            "direccion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Dirección"}),
        }