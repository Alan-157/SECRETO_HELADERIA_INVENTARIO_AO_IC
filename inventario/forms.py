# heladeria/inventario/forms.py

from django import forms
from .models import Insumo, Categoria

# --- FORMULARIO DE CATEGORÍA ---
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
        # Excluimos created_at/updated_at/is_active que se manejan en el Admin o BaseModel
        fields = [
            'nombre', 'categoria', 'stock_minimo', 
            'stock_maximo', 'unidad_medida', 'precio_unitario'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}), # select para FK
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_maximo': forms.NumberInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    # Ejemplo de Validación Personalizada (Clase U1 C9)
    def clean_stock_minimo(self):
        minimo = self.cleaned_data.get('stock_minimo')
        if minimo is not None and minimo < 0:
            raise forms.ValidationError("El stock mínimo no puede ser negativo.")
        return minimo