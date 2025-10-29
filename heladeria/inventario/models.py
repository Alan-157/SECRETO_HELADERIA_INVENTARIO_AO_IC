from decimal import Decimal
from django.db import models
from django.db.models import Sum
from accounts.models import BaseModel, UsuarioApp

# --- CONSTANTES DE OPCIÓN ---
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

# --- MODELOS DE CATÁLOGO Y ESTRUCTURA ---

class Categoria(BaseModel):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.nombre


class Bodega(BaseModel):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
    def __str__(self):
        return self.nombre


class Ubicacion(BaseModel):
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="ubicaciones")
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, blank=True, null=True)
    def __str__(self):
        return f"{self.nombre} ({self.bodega.nombre})"


class Insumo(BaseModel):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="insumos")
    nombre = models.CharField(max_length=100)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2)
    stock_maximo = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_medida = models.CharField(max_length=20)
    precio_unitario = models.IntegerField()

    def __str__(self):
        return self.nombre


# --- MODELOS DE INVENTARIO Y TRANSACCIONES ---

class InsumoLote(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="lotes")
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="lotes")
    fecha_ingreso = models.DateField()
    fecha_expiracion = models.DateField()
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=2)
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT, related_name="lotes_creados")

    def __str__(self):
        return f"Lote {self.id} de {self.insumo.nombre}"


# --- ÓRDENES DE INSUMOS ---

class OrdenInsumo(BaseModel):
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT, related_name="ordenes_creadas")
    fecha = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=50, choices=ESTADO_ORDEN_CHOICES, default="PENDIENTE")

    def __str__(self):
        return f"Orden #{self.id} - {self.estado}"

    # Cálculo automático del estado
    def recalc_estado(self):
        tot_sol = self.detalles.aggregate(s=Sum("cantidad_solicitada"))["s"] or Decimal("0")
        tot_att = self.detalles.aggregate(a=Sum("cantidad_atendida"))["a"] or Decimal("0")
        if tot_sol > 0 and tot_att >= tot_sol:
            self.estado = "CERRADA"
        elif tot_att > 0:
            self.estado = "EN_CURSO"
        else:
            self.estado = "PENDIENTE"
        self.save(update_fields=["estado"])


class OrdenInsumoDetalle(BaseModel):
    orden_insumo = models.ForeignKey(OrdenInsumo, on_delete=models.CASCADE, related_name="detalles")
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    cantidad_solicitada = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_atendida = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.insumo.nombre} - {self.cantidad_solicitada}"


# --- MOVIMIENTOS DE INVENTARIO ---

class Entrada(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    insumo_lote = models.ForeignKey(InsumoLote, on_delete=models.PROTECT, null=True, blank=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT)

    # 🔗 Enlace opcional con Orden / Detalle
    orden = models.ForeignKey(OrdenInsumo, null=True, blank=True, on_delete=models.SET_NULL, related_name="entradas")
    detalle = models.ForeignKey(OrdenInsumoDetalle, null=True, blank=True, on_delete=models.SET_NULL, related_name="entradas")

    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=50, default="COMPRA")
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Entrada {self.cantidad} de {self.insumo.nombre}"


class Salida(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    insumo_lote = models.ForeignKey(InsumoLote, on_delete=models.PROTECT, null=True, blank=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT)

    # 🔗 Enlace opcional con Orden / Detalle
    orden = models.ForeignKey(OrdenInsumo, null=True, blank=True, on_delete=models.SET_NULL, related_name="salidas")
    detalle = models.ForeignKey(OrdenInsumoDetalle, null=True, blank=True, on_delete=models.SET_NULL, related_name="salidas")

    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_generada = models.DateField()
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=50, default="VENTA")
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Salida {self.cantidad} de {self.insumo.nombre}"


# --- ALERTAS DE STOCK ---

class AlertaInsumo(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="alertas")
    tipo = models.CharField(max_length=50, default="STOCK_BAJO")
    mensaje = models.TextField()
    fecha = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Alerta {self.tipo} para {self.insumo.nombre}"
