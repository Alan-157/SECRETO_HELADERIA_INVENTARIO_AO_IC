from decimal import Decimal
from django.db import models
from django.db.models import Sum
from accounts.models import BaseModel, UsuarioApp
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

# --- CONSTANTES DE OPCIÓN ---
TIPO_MOVIMIENTO_CHOICES = [
    ("ENTRADA", "Entrada"),
    ("SALIDA", "Salida"),
    ("AJUSTE", "Ajuste de Stock"),
]

TIPO_ORDEN_CHOICES = [ 
    ("ENTRADA", "Entrada de Insumos"),
    ("SALIDA", "Salida de Insumos"),
]

ESTADO_ORDEN_CHOICES = [
    ("PENDIENTE", "Pendiente"),
    ("EN_CURSO", "En Curso"),
    ("CERRADA", "Cerrada"),
    ("CANCELADA", "Cancelada"),
]

# Nuevo: Definición de Tipos de Alerta
TIPO_ALERTA_CHOICES = [
    ("SIN_STOCK", "Sin Stock (Stock = 0)"),
    ("BAJO_STOCK", "Stock Bajo (Stock < Mínimo)"),
    ("STOCK_EXCESIVO", "Stock Excesivo (Stock > Máximo)"), # <--- NUEVO
    ("VENCIMIENTO_PROXIMO", "Próximo a Vencer"),
]

# --- MODELOS DE CATÁLOGO Y ESTRUCTURA ---

class Categoria(BaseModel):
    nombre = models.CharField(max_length=40)
    descripcion = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.nombre


class Bodega(BaseModel):
    nombre = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    def __str__(self):
        return self.nombre


class Ubicacion(BaseModel):
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="ubicaciones")
    nombre = models.CharField(max_length=20)
    tipo = models.CharField(max_length=50, blank=True, null=True)
    def __str__(self):
        return f"{self.nombre} ({self.bodega.nombre})"

class UnidadMedida(BaseModel):
    nombre_corto = models.CharField(max_length=5, unique=True, verbose_name="Código (KG, LT)")
    nombre_largo = models.CharField(max_length=50, unique=True, verbose_name="Nombre Completo (Kilogramos, Litros)")
    
    def __str__(self):
        # Aseguramos que el __str__ devuelva el formato que usará el AJAX
        return f"{self.nombre_largo} ({self.nombre_corto})"

class Insumo(BaseModel):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="insumos")
    nombre = models.CharField(max_length=35, db_index=True)  # Índice para búsquedas rápidas
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2)
    stock_maximo = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_medida = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, related_name="insumos_medidos") 
    precio_unitario = models.IntegerField()

    class Meta:
        ordering = ['nombre']  # Ordenamiento por defecto
        indexes = [
            models.Index(fields=['nombre', 'categoria']),  # Índice compuesto para filtros frecuentes
            models.Index(fields=['is_active', 'nombre']),  # Para listar insumos activos
        ]

    def __str__(self):
        return self.nombre

    # Validación de stock (mantenida del paso anterior)
    def clean(self):
        # Asegurarse de que ambos campos tengan un valor antes de comparar
        if self.stock_minimo is not None and self.stock_maximo is not None:
            if self.stock_minimo > self.stock_maximo:
                # Se lanza un ValidationError con un mensaje para cada campo
                raise ValidationError({
                    'stock_minimo': 'El stock mínimo no puede ser mayor que el stock máximo.',
                    'stock_maximo': 'El stock máximo debe ser mayor o igual al stock mínimo.'
                })
        super().clean()
        
class Proveedor(BaseModel):
    """Tabla maestra de proveedores"""

    ESTADO_CHOICES = [
        ("ACTIVO", "Activo"),
        ("INACTIVO", "Inactivo"),
        ("SUSPENDIDO", "Suspendido"),
    ]

    nombre_empresa = models.CharField(max_length=100, db_index=True, verbose_name="Nombre Empresa")
    rut_empresa = models.CharField(max_length=20, unique=True, verbose_name="RUT/NIT")
    # CORREGIDO: max_length reducido para evitar el error 1071 de MySQL en el índice UNIQUE
    email = models.EmailField(max_length=150, unique=True, verbose_name="Email") 
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

# --- MODELOS DE INVENTARIO Y TRANSACCIONES ---
class InsumoLote(BaseModel):
    # Clave Foránea a Insumo (Limitada a activos)
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="lotes",
        limit_choices_to={"is_active": True},
    )
    # Clave Foránea a Bodega (Limitada a activos)
    bodega = models.ForeignKey(
        Bodega,
        on_delete=models.PROTECT,
        related_name="lotes",
        limit_choices_to={"is_active": True},
    )

    # NUEVA CLAVE FORÁNEA: Proveedor (Opcional y limitada a activos)
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="lotes",
        null=True,
        blank=True,
        limit_choices_to={"is_active": True},
    )

    fecha_ingreso = models.DateField(db_index=True)  # Índice para ordenar por fecha
    fecha_expiracion = models.DateField(db_index=True)  # Índice para filtrar vencimientos
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)  # Para filtrar stock>0
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT, related_name="lotes_creados")

    class Meta:
        ordering = ['-fecha_ingreso']  # Más recientes primero
        indexes = [
            models.Index(fields=['insumo', 'is_active', 'cantidad_actual']),  # Para listar lotes activos con stock
            models.Index(fields=['fecha_expiracion', 'is_active']),  # Para alertas de vencimiento
            models.Index(fields=['bodega', 'insumo']),  # Para buscar por bodega e insumo
        ]

    def __str__(self):
        return f"Lote {self.id} de {self.insumo.nombre}"

# --- ÓRDENES DE INSUMOS ---

class OrdenInsumo(BaseModel):
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT, related_name="ordenes_creadas")
    fecha = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=50, choices=ESTADO_ORDEN_CHOICES, default="PENDIENTE")
    
    # NUEVO CAMPO: Define si la orden es de entrada o salida
    tipo_orden = models.CharField(
        max_length=40, 
        choices=TIPO_ORDEN_CHOICES, 
        default="ENTRADA",
        verbose_name="Tipo de Orden"
    )

    def __str__(self):
        # MODIFICADO: Incluir el tipo de orden
        return f"Orden #{self.id} - {self.tipo_orden} - {self.estado}"

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
    orden = models.ForeignKey(OrdenInsumo, null=True, blank=True, on_delete=models.SET_NULL, related_name="entradas")
    detalle = models.ForeignKey(OrdenInsumoDetalle, null=True, blank=True, on_delete=models.SET_NULL, related_name="entradas")
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(db_index=True)
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=50, default="COMPRA")
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Entrada {self.cantidad} de {self.insumo.nombre}"


class Salida(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    insumo_lote = models.ForeignKey(InsumoLote, on_delete=models.PROTECT, null=True, blank=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT)
    orden = models.ForeignKey(OrdenInsumo, null=True, blank=True, on_delete=models.SET_NULL, related_name="salidas")
    detalle = models.ForeignKey(OrdenInsumoDetalle, null=True, blank=True, on_delete=models.SET_NULL, related_name="salidas")
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_generada = models.DateField(db_index=True)
    usuario = models.ForeignKey(UsuarioApp, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=50, default="VENTA")
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Salida {self.cantidad} de {self.insumo.nombre}"


# --- ALERTAS DE STOCK ---


class AlertaInsumo(BaseModel):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="alertas") #
    tipo = models.CharField( #
        max_length=50, 
        choices=TIPO_ALERTA_CHOICES, # <--- MODIFICADO
        default="BAJO_STOCK",         # <--- MODIFICADO el default
        db_index=True  # Para filtrar por tipo rápidamente
    )
    mensaje = models.TextField() #
    fecha = models.DateField(auto_now_add=True) #

    class Meta:
        ordering = ['-fecha', '-id']  # Más recientes primero
        indexes = [
            models.Index(fields=['insumo', 'is_active', 'tipo']),  # Para filtrar alertas activas por insumo y tipo
            models.Index(fields=['is_active', 'fecha']),  # Para listar alertas activas ordenadas
        ]
