from datetime import date
import re
from django.db.models import Sum, Q, DecimalField
from decimal import Decimal
from django.db.models.functions import Coalesce
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
    Proveedor,
    Salida,
    Ubicacion,
    UnidadMedida,
    AlertaInsumo
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
class EntradaLineaForm(forms.Form):
    # Campos base
    insumo = forms.ModelChoiceField(queryset=Insumo.objects.filter(is_active=True), label="Insumo", widget=forms.Select(attrs={"class": "form-select"}))
    ubicacion = forms.ModelChoiceField(queryset=Ubicacion.objects.select_related("bodega"), label="Ubicación", widget=forms.Select(attrs={"class": "form-select"}))
    fecha = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}), label="Fecha de Entrada")
    
    # MODIFICADO: CONVERTIDO A INTEGERFIELD
    cantidad = forms.IntegerField(
        min_value=1, label="Cantidad", 
        validators=[
            MinValueValidator(1, message="La cantidad debe ser un número entero mayor que cero."),
            MaxValueValidator(99999, message="La cantidad no puede exceder 99,999 (5 dígitos enteros).")
        ],
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "1",  # CRÍTICO: Indica al navegador que solo acepte números enteros
            "max": "99999", # Máximo valor (5 dígitos)
            "oninput": "if(this.value.length>5)this.value=this.value.slice(0,5)", # JS para truncar a 5 dígitos
        }),
    )

    # Lote y Expiración (Específicos de ENTRADA)
    # ⚠️ CORRECCIÓN CLAVE: Proveedor ahora es obligatorio (required=True)
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.filter(estado='ACTIVO'), 
        required=True, # ⬅️ OBLIGATORIO
        label="Proveedor", 
        widget=forms.Select(attrs={"class": "form-select"})
    )
    fecha_expiracion = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}), label="Fecha de expiración")
    
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}), label="Observaciones")

    def clean(self):
        cd = super().clean()
        fexp = cd.get('fecha_expiracion')
        fecha = cd.get('fecha')
        insumo = cd.get('insumo')
        cantidad_int = cd.get('cantidad')
        
        # ⚠️ CORRECCIÓN 1: CONVERSIÓN CRÍTICA de int a Decimal para el guardado
        if cantidad_int is not None:
            cd['cantidad'] = Decimal(cantidad_int)
        
        cantidad = cd.get('cantidad') # Obtenemos el Decimal
        
        # Validación de Fecha de Expiración
        if not fexp:
            self.add_error("fecha_expiracion", "La fecha de expiración es requerida para el lote de entrada.")
        if fexp and fecha and fexp < fecha:
            self.add_error("fecha_expiracion", "La fecha de expiración no puede ser anterior a la fecha de entrada.")

        # Validación de Stock Máximo (Si la cantidad es válida)
        if insumo and cantidad and cantidad > 0:
            stock_data = insumo.lotes.filter(is_active=True).aggregate(
                stock_actual=Coalesce(Sum('cantidad_actual'), Decimal("0.00"), output_field=DecimalField())
            )
            stock_actual = stock_data['stock_actual']
            stock_proyectado = stock_actual + cantidad

            if stock_proyectado > insumo.stock_maximo:
                max_permisible = insumo.stock_maximo - stock_actual
                self.add_error("cantidad", f"La entrada excede el stock máximo ({int(insumo.stock_maximo)}). Máximo a entrar: {int(max_permisible)}")

        return cd

# --- FORMULARIO DE LÍNEA PARA SALIDA ---
class SalidaLineaForm(forms.Form):
    insumo = forms.ModelChoiceField(queryset=Insumo.objects.filter(is_active=True), label="Insumo", widget=forms.Select(attrs={"class": "form-select"}))
    ubicacion = forms.ModelChoiceField(queryset=Ubicacion.objects.select_related("bodega"), label="Ubicación", widget=forms.Select(attrs={"class": "form-select"}))
    fecha = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}), label="Fecha de Salida")
    
    # MODIFICADO: CONVERTIDO A INTEGERFIELD
    cantidad = forms.IntegerField(
        min_value=1, label="Cantidad", 
        validators=[
            MinValueValidator(1, message="La cantidad debe ser un número entero mayor que cero."),
            MaxValueValidator(99999, message="La cantidad no puede exceder 99,999 (5 dígitos enteros).")
        ],
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "1", # CRÍTICO: Indica al navegador que solo acepte números enteros
            "max": "99999",
            "oninput": "if(this.value.length>5)this.value=this.value.slice(0,5)",
        }),
    )
    
    # Lote Existente (Específico de SALIDA)
    insumo_lote = forms.ModelChoiceField(
        queryset=InsumoLote.objects.select_related("insumo", "bodega"),
        required=True, # Obligatorio para una salida
        label="Lote de Origen",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}), label="Observaciones")

    def clean(self):
        cd = super().clean()
        lote = cd.get('insumo_lote')
        cant_int = cd.get('cantidad')
        
        # ⚠️ CORRECCIÓN 1: CONVERSIÓN CRÍTICA de int a Decimal
        if cant_int is not None:
            cd['cantidad'] = Decimal(cant_int)
        
        cant = cd.get('cantidad')
        
        # Validación de Stock Suficiente
        if lote and cant and cant > lote.cantidad_actual:
            self.add_error("cantidad", f"Stock insuficiente en el lote. Disponible: {lote.cantidad_actual}")
        
        return cd

# --- DEFINICIÓN DE LOS NUEVOS FORMSETS ---
# extra=0: No agrega formularios vacíos. El usuario usa el botón "Agregar Línea" para añadir.
EntradaLineaFormSet = formset_factory(EntradaLineaForm, extra=0, can_delete=True)
SalidaLineaFormSet = formset_factory(SalidaLineaForm, extra=0, can_delete=True)

# --- FORMSETS PARA MOVIMIENTOS (con extra=1 para agregar automáticamente línea) ---
# Estos se usan cuando accedes desde listar_movimientos SIN pre-cargar insumo
EntradaLineaFormSetMovimiento = formset_factory(EntradaLineaForm, extra=1, can_delete=True)
SalidaLineaFormSetMovimiento = formset_factory(SalidaLineaForm, extra=1, can_delete=True)

class EntradaForm(forms.ModelForm):
    # MODIFICADO: De DecimalField a IntegerField (para edición individual)
    cantidad = forms.IntegerField(
        label="Cantidad",
        validators=[
            MinValueValidator(1, message="La cantidad debe ser un número entero mayor que cero."),
            MaxValueValidator(99999, message="La cantidad no puede exceder 99,999 (5 dígitos enteros).")
        ],
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "1",
            "max": "99999",
            "oninput": "if(this.value.length>5)this.value=this.value.slice(0,5)" 
        }),
    )

    class Meta:
        model = Entrada
        # Incluye insumo_lote para que el usuario sepa qué lote está editando
        fields = ["insumo", "insumo_lote", "ubicacion", "cantidad", "fecha", "observaciones", "tipo"]
        exclude = ["usuario", "orden", "detalle"]
        widgets = {
            "insumo": forms.Select(attrs={"class": "form-select", "disabled": True}), # Se bloquea
            "insumo_lote": forms.Select(attrs={"class": "form-select", "disabled": True}), # Se bloquea
            "ubicacion": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tipo": forms.TextInput(attrs={"class": "form-control", "disabled": True}),
        }

class SalidaForm(forms.ModelForm):
    # MODIFICADO: De DecimalField a IntegerField (para edición individual)
    cantidad = forms.IntegerField(
        label="Cantidad",
        validators=[
            MinValueValidator(1, message="La cantidad debe ser un número entero mayor que cero."),
            MaxValueValidator(99999, message="La cantidad no puede exceder 99,999 (5 dígitos enteros).")
        ],
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "1",
            "max": "99999",
            "oninput": "if(this.value.length>5)this.value=this.value.slice(0,5)"
        }),
    )

    class Meta:
        model = Salida
        fields = ["insumo", "insumo_lote", "ubicacion", "cantidad", "fecha_generada", "observaciones", "tipo"]
        exclude = ["usuario", "orden", "detalle"]
        widgets = {
            "insumo": forms.Select(attrs={"class": "form-select", "disabled": True}),
            "insumo_lote": forms.Select(attrs={"class": "form-select", "disabled": True}),
            "ubicacion": forms.Select(attrs={"class": "form-select"}),
            "fecha_generada": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tipo": forms.TextInput(attrs={"class": "form-control", "disabled": True}),
        }

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

class AlertaForm(forms.ModelForm):
    # Definimos opciones de tipo de alerta, aunque ya pueden estar en el modelo
    TIPO_ALERTA_CHOICES = [
        ("STOCK_BAJO", "Stock Bajo"),
        ("PROX_VENCER", "Próximo a Vencer"),
        ("SIN_STOCK", "Sin Stock"),
        ("OTRO", "Otro"),
    ]

    tipo = forms.ChoiceField(
        choices=TIPO_ALERTA_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Tipo de Alerta"
    )
    
    class Meta:
        model = AlertaInsumo
        fields = ("insumo", "tipo", "mensaje")
        widgets = {
            "insumo": forms.Select(attrs={"class": "form-select"}),
            "mensaje": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        mensaje = cleaned_data.get("mensaje")

        # Relleno automático del mensaje si está vacío (para comodidad del usuario)
        if not mensaje:
            if tipo == "STOCK_BAJO":
                cleaned_data['mensaje'] = "El insumo ha alcanzado el nivel de stock mínimo."
            elif tipo == "PROX_VENCER":
                cleaned_data['mensaje'] = "Revisar lotes con fechas de expiración cercanas."
            elif tipo == "SIN_STOCK":
                cleaned_data['mensaje'] = "El insumo se ha quedado sin stock."
            elif tipo == "OTRO":
                cleaned_data['mensaje'] = "Alerta manual generada por el usuario."
        
        return cleaned_data
    
class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        # Excluimos solo el campo is_active para que los usuarios puedan modificar el estado
        exclude = ["is_active", "created_at", "updated_at"] 
        widgets = {
            "nombre_empresa": forms.TextInput(attrs={"class": "form-control"}),
            "rut_empresa": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "telefono_alternativo": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "ciudad": forms.TextInput(attrs={"class": "form-control"}),
            "region": forms.TextInput(attrs={"class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "condiciones_pago": forms.TextInput(attrs={"class": "form-control"}),
            "dias_credito": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "monto_credito": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_rut_empresa(self):
        rut_input = self.cleaned_data["rut_empresa"].strip()
        
        # 1. Limpiar y Normalizar el RUT
        rut_clean = re.sub(r'[.-]', '', rut_input).upper()
        if not rut_clean:
            # Si está vacío, Django debería haberlo marcado como error requerido,
            # pero lo chequeamos por si acaso
            raise forms.ValidationError("El RUT no puede estar vacío.")

        # Separar el cuerpo (números) del dígito verificador (DV)
        if len(rut_clean) < 2:
            raise forms.ValidationError("El formato del RUT es inválido.")
            
        cuerpo = rut_clean[:-1]
        dv_input = rut_clean[-1]
        
        # Verificar que el cuerpo sean solo dígitos
        if not cuerpo.isdigit():
            raise forms.ValidationError("El cuerpo del RUT debe contener solo números.")

        # 2. Validación de Unicidad (mantenemos la validación existente)
        qs = Proveedor.objects.filter(rut_empresa__iexact=rut_input)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe un proveedor con este RUT/NIT.")
        
        # 3. Validación Matemática (Módulo 11)
        
        reverso = cuerpo[::-1]
        multiplicador = 2
        suma = 0
        
        for digito in reverso:
            suma += int(digito) * multiplicador
            multiplicador += 1
            if multiplicador > 7:
                multiplicador = 2
        
        resto = suma % 11
        dv_calculado_int = 11 - resto
        
        if dv_calculado_int == 11:
            dv_calculado = '0'
        elif dv_calculado_int == 10:
            dv_calculado = 'K'
        else:
            dv_calculado = str(dv_calculado_int)
            
        # 4. Comparación del DV
        if dv_calculado != dv_input:
            raise forms.ValidationError(f"El RUT es inválido. El dígito verificador correcto es '{dv_calculado}'.")
            
        # 5. Si todo es correcto, retornamos el RUT limpio o el original (original por unicidad)
        return rut_input
        
    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        qs = Proveedor.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("⚠ Ya existe un proveedor con este Email.")
        return email
