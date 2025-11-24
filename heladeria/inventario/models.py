from decimal import Decimal
from django.db import models
from django.db.models import Sum
from accounts.models import BaseModel, UsuarioApp
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

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

TIPO_ORDEN_CHOICES = [
    ("ENTRADA", "Entrada"),
    ("SALIDA", "Salida"),
]

# --- MODELOS DE CATÁLOGO Y ESTRUCTURA ---

class Categoria(BaseModel):
    nombre = models.CharField(max_length=70)
    descripcion = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]
    def __str__(self):
        return self.nombre


class Ubicacion(BaseModel):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)  # ✅ dirección real
    tipo = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} - {self.direccion}"


class Bodega(BaseModel):
    ubicacion = models.ForeignKey(  # ✅ FK a ubicación real
        Ubicacion,
        on_delete=models.PROTECT,
        related_name="bodegas",
        limit_choices_to={"is_active": True},
    )
    nombre = models.CharField(max_length=50)  # ej: “Bodega de frío”
    descripcion = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Bodega"
        verbose_name_plural = "Bodegas"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.ubicacion.nombre})"


# --- NUEVO MODELO CRUD: UNIDAD DE MEDIDA ---

class UnidadMedida(BaseModel):
    """
    Catálogo CRUD de unidades de medida.
    Se usa en Insumo (FK).
    """

    codigo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="Código",
        help_text="Ej: KG, GR, LT, ML, UN, OTRO"
    )
    nombre = models.CharField(
        max_length=50,
        verbose_name="Nombre",
        help_text="Ej: Kilogramos, Gramos, Litros..."
    )
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Unidad de medida"
        verbose_name_plural = "Unidades de medida"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# --- MODELO: PROVEEDOR ---

class Proveedor(BaseModel):
    """Tabla maestra de proveedores"""

    ESTADO_CHOICES = [
        ("ACTIVO", "Activo"),
        ("INACTIVO", "Inactivo"),
        ("SUSPENDIDO", "Suspendido"),
    ]

    nombre_empresa = models.CharField(max_length=100, verbose_name="Nombre Empresa")
    rut_empresa = models.CharField(max_length=20, unique=True, verbose_name="RUT/NIT")
    email = models.EmailField(unique=True, verbose_name="Email")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    telefono_alternativo = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="Teléfono Alternativo"
    )
    direccion = models.CharField(max_length=200, verbose_name="Dirección")
    ciudad = models.CharField(max_length=50, verbose_name="Ciudad")
    region = models.CharField(max_length=50, verbose_name="Región")

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default="ACTIVO",
        verbose_name="Estado",
    )

    condiciones_pago = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Condiciones de Pago"
    )
    dias_credito = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Días de Crédito",
    )
    monto_credito = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        verbose_name="Monto de Crédito",
    )
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["nombre_empresa"]

    def __str__(self):
        return f"{self.nombre_empresa} ({self.rut_empresa})"


# --- MODELOS PRINCIPALES ---

class Insumo(BaseModel):
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="insumos",
        limit_choices_to={"is_active": True},
    )
    nombre = models.CharField(max_length=120)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2)
    stock_maximo = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_medida = models.ForeignKey(
        UnidadMedida,
        on_delete=models.PROTECT,
        related_name="insumos",
        limit_choices_to={"is_active": True},
    )
    precio_unitario = models.IntegerField()

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ["nombre"]
        
    def __str__(self):
        return self.nombre
    def clean(self):
        if self.stock_minimo is not None and self.stock_maximo is not None:
            if self.stock_minimo > self.stock_maximo:
                raise ValidationError({
                    "stock_minimo": "El stock mínimo no puede ser mayor que el stock máximo.",
                    "stock_maximo": "El stock máximo debe ser mayor o igual al stock mínimo.",
                })
        super().clean()


class InsumoLote(BaseModel):
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="lotes",
        limit_choices_to={"is_active": True},
    )
    bodega = models.ForeignKey(
        Bodega,
        on_delete=models.PROTECT,
        related_name="lotes",
        limit_choices_to={"is_active": True},
    )

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="lotes",
        null=True,
        blank=True,
        limit_choices_to={"is_active": True},
    )

    fecha_ingreso = models.DateField()
    fecha_expiracion = models.DateField()
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=2)
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT, related_name="lotes_creados")

    def __str__(self):
        return f"Lote {self.id} de {self.insumo.nombre}"


class OrdenInsumo(BaseModel):
    usuario = models.ForeignKey(
        UsuarioApp,
        on_delete=models.PROTECT,
        related_name="ordenes_creadas"
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_ORDEN_CHOICES,
        default="SALIDA",
    )

    fecha = models.DateField(auto_now_add=True)
    estado = models.CharField(
        max_length=50,
        choices=ESTADO_ORDEN_CHOICES,
        default="PENDIENTE"
    )

    def __str__(self):
        return f"Orden #{self.id} - {self.tipo} - {self.estado}"

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
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        limit_choices_to={"is_active": True},
    )
    cantidad_solicitada = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_atendida = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.insumo.nombre} - {self.cantidad_solicitada}"


class Entrada(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, limit_choices_to={"is_active": True})
    insumo_lote = models.ForeignKey(InsumoLote, on_delete=models.PROTECT, null=True, blank=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, limit_choices_to={"is_active": True})

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
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, limit_choices_to={"is_active": True})
    insumo_lote = models.ForeignKey(InsumoLote, on_delete=models.PROTECT, null=True, blank=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, limit_choices_to={"is_active": True})

    orden = models.ForeignKey(OrdenInsumo, null=True, blank=True, on_delete=models.SET_NULL, related_name="salidas")
    detalle = models.ForeignKey(OrdenInsumoDetalle, null=True, blank=True, on_delete=models.SET_NULL, related_name="salidas")

    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_generada = models.DateField()
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=50, default="VENTA")
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Salida {self.cantidad} de {self.insumo.nombre}"


class AlertaInsumo(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="alertas", limit_choices_to={"is_active": True})
    tipo = models.CharField(max_length=50, default="STOCK_BAJO")
    mensaje = models.TextField()
    fecha = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Alerta {self.tipo} para {self.insumo.nombre}"
    
