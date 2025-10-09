from django.db import models
from accounts.models import BaseModel, UsuarioApp # Importación correcta de clases base y usuario

# --- CONSTANTES DE OPCIÓN (Clase 6 y 7) ---
TIPO_MOVIMIENTO_CHOICES = [
    ("ENTRADA", "Entrada"),
    ("SALIDA", "Salida"),
    ("AJUSTE", "Ajuste de Stock"),
]
ESTADO_ORDEN_CHOICES = [
    ("PENDIENTE", "Pendiente"),
    ("EN_CURSO", "En Curso"),
    ("CERRADA", "Cerrada"),
    ("CANCELADA", "Cancelada"),
]

# Modelo intermedio necesario para la referencia de Entrada/Salida
class Ordenresumen(BaseModel): 
    nombre = models.CharField(max_length=100)
    def __str__(self): 
        return self.nombre

class Categoria(BaseModel):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True) # Descripción opcional
    def __str__(self):
        return self.nombre

class Bodega(BaseModel): # Tabla principal de almacenes
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
    def __str__(self):
        return self.nombre

class Ubicacion(BaseModel): # Ubicación interna dentro de una Bodega (racks, zonas, etc.)
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="ubicaciones") # FK a Bodega
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, blank=True, null=True) # Campo tipo de tu ERD
    def __str__(self):
        return f"{self.nombre} ({self.bodega.nombre})"

class Insumo(BaseModel):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="insumos")
    nombre = models.CharField(max_length=100)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2)
    stock_maximo = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_medida = models.CharField(max_length=20)
    precio_unitario = models.IntegerField()
    # Campo 'cantidad_actual' no se define aquí, se calcula desde Lotes.
    def __str__(self):
        return self.nombre

# --- MODELOS DE INVENTARIO Y TRANSACCIONES (Heredan de BaseModel) ---

class InsumoLote(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="lotes")
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="lotes")
    fecha_ingreso = models.DateField()
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=2)
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT, related_name="lotes_creados") # FK a UsuarioApp
    def __str__(self):
        return f"Lote {self.id} de {self.insumo.nombre}"

class Entrada(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    insumo_lote = models.ForeignKey(InsumoLote, on_delete=models.PROTECT, null=True, blank=True) # FK a Lote (ERD)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT)
    ordenresumen = models.ForeignKey(Ordenresumen, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField() # Campo 'fecha' de tu ERD
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT) # FK a UsuarioApp (ERD)
    tipo = models.CharField(max_length=50, default="COMPRA") # Tipo de entrada
    observaciones = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"Entrada {self.cantidad} de {self.insumo.nombre}"

class Salida(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    insumo_lote = models.ForeignKey(InsumoLote, on_delete=models.PROTECT, null=True, blank=True) # FK a Lote (ERD)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT)
    ordenresumen = models.ForeignKey(Ordenresumen, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_generada = models.DateField() # Campo 'fecha_generada' de tu ERD
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT) # FK a UsuarioApp
    tipo = models.CharField(max_length=50, default="VENTA") # Tipo de salida
    def __str__(self):
        return f"Salida {self.cantidad} de {self.insumo.nombre}"

class AlertaInsumo(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="alertas")
    tipo = models.CharField(max_length=50, default="STOCK_BAJO") # Tipo de alerta de tu ERD
    mensaje = models.TextField()
    fecha = models.DateField(auto_now_add=True)
    def __str__(self):
        return f"Alerta {self.tipo} para {self.insumo.nombre}"

class OrdenInsumo(BaseModel):
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT, related_name="ordenes_creadas") # FK a UsuarioApp
    fecha = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=50, choices=ESTADO_ORDEN_CHOICES, default="PENDIENTE")
    def __str__(self):
        return f"Orden #{self.id} - {self.estado}"

class OrdenInsumoDetalle(BaseModel):
    orden_insumo = models.ForeignKey(OrdenInsumo, on_delete=models.CASCADE, related_name="detalles")
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    cantidad_solicitada = models.DecimalField(max_digits=10, decimal_places=2)
    # Puede llevar campos de auditoría heredados como created_at
    def __str__(self):
        return f"{self.insumo.nombre} - {self.cantidad_solicitada}"
