from datetime import date, timedelta
from decimal import Decimal
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from inventario.models import (
    Categoria,
    UnidadMedida,
    Insumo,
    Proveedor,
    InsumoLote,
    AlertaInsumo,
    Entrada,
    Salida,
    Bodega,
    Ubicacion,
    OrdenInsumo,
    OrdenInsumoDetalle,
)
from accounts.models import UsuarioApp


class Command(BaseCommand):
    help = (
        "Crea datos masivos de stress (insumos, movimientos, proveedores y alertas) "
        "para pruebas de rendimiento. Úsalo SOLO en entornos controlados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--categorias",
            type=int,
            default=100,
            help="Cantidad de categorías de stress a crear (default: 100)",
        )
        parser.add_argument(
            "--bodegas",
            type=int,
            default=50,
            help="Cantidad de bodegas de stress a crear (default: 50)",
        )
        parser.add_argument(
            "--insumos",
            type=int,
            default=5000,
            help="Cantidad de insumos de stress a crear (default: 5000)",
        )
        parser.add_argument(
            "--lotes",
            type=int,
            default=10000,
            help="Cantidad de lotes de stress a crear (default: 10000)",
        )
        parser.add_argument(
            "--ordenes",
            type=int,
            default=1000,
            help="Cantidad de órdenes de stress a crear (default: 1000)",
        )
        parser.add_argument(
            "--movimientos",
            type=int,
            default=5000,
            help="Cantidad de movimientos (entradas+salidas) a crear (default: 5000)",
        )
        parser.add_argument(
            "--proveedores",
            type=int,
            default=500,
            help="Cantidad de proveedores a crear (default: 500)",
        )
        parser.add_argument(
            "--alertas",
            type=int,
            default=10000,
            help="Cantidad de alertas a crear (default: 10000)",
        )

    # ---------------------------
    #   RUT helper
    # ---------------------------
    def _calcular_dv(self, cuerpo: str) -> str:
        """
        Calcula el dígito verificador (DV) para un RUT chileno dado el cuerpo numérico.
        Misma lógica que usas en el formulario de Proveedor. :contentReference[oaicite:2]{index=2}
        """
        reverso = cuerpo[::-1]
        multiplicador = 2
        suma = 0

        for digito in reverso:
            suma += int(digito) * multiplicador
            multiplicador += 1
            if multiplicador > 7:
                multiplicador = 2

        resto = suma % 11
        dv_int = 11 - resto

        if dv_int == 11:
            return "0"
        elif dv_int == 10:
            return "K"
        return str(dv_int)

    def handle(self, *args, **options):
        num_categorias = options["categorias"]
        num_bodegas = options["bodegas"]
        num_insumos = options["insumos"]
        num_lotes = options["lotes"]
        num_ordenes = options["ordenes"]
        num_movs = options["movimientos"]
        num_provs = options["proveedores"]
        num_alertas = options["alertas"]

        self.stdout.write(self.style.NOTICE("=== SEED DE STRESS (PRODUCCIÓN) ==="))
        self.stdout.write(self.style.NOTICE(f"Categorías a crear:  {num_categorias}"))
        self.stdout.write(self.style.NOTICE(f"Bodegas a crear:     {num_bodegas}"))
        self.stdout.write(self.style.NOTICE(f"Insumos a crear:     {num_insumos}"))
        self.stdout.write(self.style.NOTICE(f"Lotes a crear:       {num_lotes}"))
        self.stdout.write(self.style.NOTICE(f"Órdenes a crear:     {num_ordenes}"))
        self.stdout.write(self.style.NOTICE(f"Movimientos a crear: {num_movs}"))
        self.stdout.write(self.style.NOTICE(f"Proveedores a crear: {num_provs}"))
        self.stdout.write(self.style.NOTICE(f"Alertas a crear:     {num_alertas}"))

        # ---------------------------------------------------------
        # Validaciones base
        # ---------------------------------------------------------
        unidades = list(UnidadMedida.objects.all())
        if not unidades:
            self.stderr.write(
                self.style.ERROR(
                    "Faltan Unidades de Medida. "
                    "Primero ejecuta seed_unidadmedida."
                )
            )
            return

        usuario = UsuarioApp.objects.filter(is_superuser=True).first()
        if not usuario:
            self.stderr.write(
                self.style.ERROR(
                    "No se encontró superusuario. Crea uno con 'python manage.py createsuperuser'."
                )
            )
            return

        # ---------------------------------------------------------
        # 1) Categorías de stress
        # ---------------------------------------------------------
        self._crear_categorias_stress(num_categorias)
        categorias = list(Categoria.objects.all())

        # ---------------------------------------------------------
        # 2) Bodegas y ubicaciones de stress
        # ---------------------------------------------------------
        self._crear_bodegas_stress(num_bodegas)
        bodegas = list(Bodega.objects.all())
        ubicaciones = list(Ubicacion.objects.all())

        if not bodegas or not ubicaciones:
            self.stderr.write(self.style.ERROR("No hay Bodegas/Ubicaciones para continuar."))
            return

        # ---------------------------------------------------------
        # 3) Proveedores de stress
        # ---------------------------------------------------------
        self._crear_proveedores_stress(num_provs)
        proveedores = list(Proveedor.objects.all())

        # ---------------------------------------------------------
        # 4) Insumos de stress
        # ---------------------------------------------------------
        self._crear_insumos_stress(num_insumos, categorias, unidades)
        insumos = list(Insumo.objects.all())

        if not insumos:
            self.stderr.write(self.style.ERROR("No hay Insumos para asociar lotes/alertas."))
            return

        # ---------------------------------------------------------
        # 5) Lotes de stress
        # ---------------------------------------------------------
        self._crear_lotes_stress(num_lotes, insumos, bodegas, proveedores)
        lotes = list(InsumoLote.objects.select_related("insumo", "bodega"))

        # ---------------------------------------------------------
        # 6) Órdenes de stress
        # ---------------------------------------------------------
        self._crear_ordenes_stress(num_ordenes, insumos, usuario)

        # ---------------------------------------------------------
        # 7) Alertas de stress
        # ---------------------------------------------------------
        self._crear_alertas_stress(num_alertas, insumos)

        # ---------------------------------------------------------
        # 8) Movimientos de stress
        # ---------------------------------------------------------
        self._crear_movimientos_stress(num_movs, lotes, usuario)

        self.stdout.write(self.style.SUCCESS("=== SEED DE STRESS TERMINADO CON ÉXITO ==="))

    # =========================================================
    # Helpers
    # =========================================================

    def _crear_categorias_stress(self, cantidad, chunk_size=100):
        self.stdout.write(self.style.NOTICE("\n[1/8] Creando categorías de stress..."))

        start_index = Categoria.objects.count() + 1
        batch = []
        creados_total = 0

        for i in range(cantidad):
            nombre = f"Categoría Stress {start_index + i:04d}"
            cat = Categoria(
                nombre=nombre,
                descripcion=f"Categoría generada automáticamente para pruebas de stress #{start_index + i}",
            )
            batch.append(cat)

            if len(batch) >= chunk_size:
                Categoria.objects.bulk_create(batch, ignore_conflicts=True)
                creados_total += len(batch)
                batch.clear()
                self.stdout.write(
                    self.style.SUCCESS(f"  -> {creados_total} categorías generadas...")
                )

        if batch:
            Categoria.objects.bulk_create(batch, ignore_conflicts=True)
            creados_total += len(batch)

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ Categorías de stress creadas (aprox): {creados_total}")
        )

    def _crear_bodegas_stress(self, cantidad, chunk_size=50):
        self.stdout.write(self.style.NOTICE("\n[2/8] Creando bodegas y ubicaciones de stress..."))

        start_index = Bodega.objects.count() + 1
        batch_bodegas = []
        batch_ubicaciones = []
        creados_bodegas = 0
        creados_ubicaciones = 0

        for i in range(cantidad):
            nombre = f"Bodega Stress {start_index + i:04d}"
            bod = Bodega(
                nombre=nombre,
                direccion=f"Dirección Stress {start_index + i}",
            )
            batch_bodegas.append(bod)

            if len(batch_bodegas) >= chunk_size:
                Bodega.objects.bulk_create(batch_bodegas, ignore_conflicts=True)
                creados_bodegas += len(batch_bodegas)

                # Crear 3 ubicaciones por cada bodega recién creada
                for bod_obj in batch_bodegas:
                    # Necesitamos el id, así que refetch
                    bod_saved = Bodega.objects.filter(nombre=bod_obj.nombre).first()
                    if bod_saved:
                        for j in range(3):
                            ub = Ubicacion(
                                bodega=bod_saved,
                                nombre=f"Ubicación {j+1}",
                            )
                            batch_ubicaciones.append(ub)

                Ubicacion.objects.bulk_create(batch_ubicaciones, ignore_conflicts=True)
                creados_ubicaciones += len(batch_ubicaciones)
                batch_bodegas.clear()
                batch_ubicaciones.clear()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> {creados_bodegas} bodegas, {creados_ubicaciones} ubicaciones generadas..."
                    )
                )

        if batch_bodegas:
            Bodega.objects.bulk_create(batch_bodegas, ignore_conflicts=True)
            creados_bodegas += len(batch_bodegas)

            for bod_obj in batch_bodegas:
                bod_saved = Bodega.objects.filter(nombre=bod_obj.nombre).first()
                if bod_saved:
                    for j in range(3):
                        ub = Ubicacion(
                            bodega=bod_saved,
                            nombre=f"Ubicación {j+1}",
                        )
                        batch_ubicaciones.append(ub)

            Ubicacion.objects.bulk_create(batch_ubicaciones, ignore_conflicts=True)
            creados_ubicaciones += len(batch_ubicaciones)

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ Bodegas: {creados_bodegas}, Ubicaciones: {creados_ubicaciones}"
            )
        )

    def _crear_insumos_stress(self, cantidad, categorias, unidades, chunk_size=1000):
        self.stdout.write(self.style.NOTICE("\n[3/8] Creando insumos de stress..."))

        start_index = Insumo.objects.count() + 1
        batch = []
        creados_total = 0

        for i in range(cantidad):
            nombre = f"Insumo Stress {start_index + i:05d}"
            categoria = random.choice(categorias)
            unidad = random.choice(unidades)

            insumo = Insumo(
                nombre=nombre,
                categoria=categoria,
                unidad_medida=unidad,
                stock_minimo=Decimal(random.randint(5, 50)),
                stock_maximo=Decimal(random.randint(60, 300)),
                precio_unitario=random.randint(500, 5000),
            )
            batch.append(insumo)

            if len(batch) >= chunk_size:
                Insumo.objects.bulk_create(batch, ignore_conflicts=True)
                creados_total += len(batch)
                batch.clear()
                self.stdout.write(
                    self.style.SUCCESS(f"  -> {creados_total} insumos generados...")
                )

        if batch:
            Insumo.objects.bulk_create(batch, ignore_conflicts=True)
            creados_total += len(batch)

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ Insumos de stress creados (aprox): {creados_total}")
        )

    def _crear_lotes_stress(self, cantidad, insumos, bodegas, proveedores, chunk_size=1000):
        self.stdout.write(self.style.NOTICE("\n[4/8] Creando lotes de stress..."))

        if not insumos or not bodegas:
            self.stderr.write(self.style.ERROR("No hay insumos o bodegas para crear lotes."))
            return

        batch = []
        creados_total = 0
        hoy = date.today()
        
        # Rastrear stock actual por insumo para respetar límites
        stock_por_insumo = {}
        for insumo in insumos:
            stock_actual = InsumoLote.objects.filter(
                insumo=insumo, is_active=True
            ).aggregate(total=Sum('cantidad_actual'))['total'] or Decimal('0')
            stock_por_insumo[insumo.id] = stock_actual

        for i in range(cantidad):
            insumo = random.choice(insumos)
            bodega = random.choice(bodegas)
            proveedor = random.choice(proveedores) if proveedores else None

            # Respetar el stock_maximo del insumo
            stock_actual = stock_por_insumo.get(insumo.id, Decimal('0'))
            espacio_disponible = max(Decimal('0'), insumo.stock_maximo - stock_actual)
            
            # Usar una cantidad aleatoria pero dentro del límite
            if espacio_disponible > 0:
                cant_inicial = Decimal(random.randint(10, min(100, int(espacio_disponible))))
                cant_actual = Decimal(random.randint(0, int(cant_inicial)))
            else:
                # Si el insumo ya está en su máximo, usar cantidad mínima
                cant_inicial = Decimal(random.randint(1, 10))
                cant_actual = Decimal('0')

            lote = InsumoLote(
                insumo=insumo,
                bodega=bodega,
                proveedor=proveedor,
                cantidad_inicial=cant_inicial,
                cantidad_actual=cant_actual,
                fecha_ingreso=hoy - timedelta(days=random.randint(0, 180)),
                fecha_expiracion=hoy + timedelta(days=random.randint(30, 365)) if random.random() > 0.2 else None,
            )
            batch.append(lote)
            
            # Actualizar el rastreador de stock para respetar los límites en próximas iteraciones
            stock_por_insumo[insumo.id] = stock_actual + cant_actual

            if len(batch) >= chunk_size:
                InsumoLote.objects.bulk_create(batch, ignore_conflicts=True)
                creados_total += len(batch)
                batch.clear()
                self.stdout.write(
                    self.style.SUCCESS(f"  -> {creados_total} lotes generados...")
                )

        if batch:
            InsumoLote.objects.bulk_create(batch, ignore_conflicts=True)
            creados_total += len(batch)

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ Lotes de stress creados (aprox): {creados_total}")
        )

    def _crear_ordenes_stress(self, cantidad, insumos, usuario, chunk_size=100):
        self.stdout.write(self.style.NOTICE("\n[5/8] Creando órdenes de stress..."))

        if not insumos:
            self.stderr.write(self.style.ERROR("No hay insumos para crear órdenes."))
            return

        creados_total = 0

        for i in range(cantidad):
            tipo = random.choice(["ENTRADA", "SALIDA"])
            estado = random.choice(["PENDIENTE", "EN_CURSO", "CERRADA", "CANCELADA"])

            orden = OrdenInsumo.objects.create(
                tipo_orden=tipo,
                estado=estado,
                usuario=usuario,
            )

            # Crear entre 1 y 5 detalles por orden
            num_detalles = random.randint(1, 5)
            detalles = []
            for _ in range(num_detalles):
                insumo = random.choice(insumos)
                cant_solicitada = Decimal(random.randint(10, 200))
                cant_atendida = Decimal(random.randint(0, int(cant_solicitada)))

                det = OrdenInsumoDetalle(
                    orden_insumo=orden,
                    insumo=insumo,
                    cantidad_solicitada=cant_solicitada,
                    cantidad_atendida=cant_atendida,
                )
                detalles.append(det)

            OrdenInsumoDetalle.objects.bulk_create(detalles)
            creados_total += 1

            if (i + 1) % chunk_size == 0:
                self.stdout.write(
                    self.style.SUCCESS(f"  -> {creados_total} órdenes generadas...")
                )

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ Órdenes de stress creadas: {creados_total}")
        )

    def _crear_proveedores_stress(self, cantidad, chunk_size=500):
        self.stdout.write(self.style.NOTICE("\n[6/8] Creando proveedores de stress..."))

        existentes = Proveedor.objects.count()
        start_index = existentes + 1

        batch = []
        creados_total = 0

        for i in range(cantidad):
            idx = start_index + i
            cuerpo = str(76000000 + idx)
            dv = self._calcular_dv(cuerpo)
            rut = f"{cuerpo}-{dv}"

            prov = Proveedor(
                rut_empresa=rut,
                nombre_empresa=f"Proveedor Stress {idx}",
                email=f"proveedor.stress{idx}@heladeria.test",
                telefono=f"5699{random.randint(1000000, 9999999)}",
                telefono_alternativo="",
                direccion=f"Calle Falsa {idx}",
                ciudad="La Serena",
                region="Coquimbo",
                estado="ACTIVO",
                condiciones_pago="30 días",
                dias_credito=30,
                monto_credito=Decimal(random.randint(100000, 2000000)),
                observaciones="Proveedor generado automáticamente para pruebas de carga.",
            )
            batch.append(prov)

            if len(batch) >= chunk_size:
                Proveedor.objects.bulk_create(batch, ignore_conflicts=True)
                creados_total += len(batch)
                batch.clear()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> {creados_total} proveedores generados..."
                    )
                )

        if batch:
            Proveedor.objects.bulk_create(batch, ignore_conflicts=True)
            creados_total += len(batch)

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ Proveedores de stress creados (aprox): {creados_total}")
        )

    def _crear_alertas_stress(self, cantidad, insumos, chunk_size=1000):
        self.stdout.write(self.style.NOTICE("\n[7/8] Creando alertas de stress..."))

        if not insumos:
            self.stderr.write(self.style.ERROR("No hay insumos para asociar alertas."))
            return

        batch = []
        creadas_total = 0

        for i in range(cantidad):
            insumo = random.choice(insumos)
            msg = f"[STRESS] Alerta #{i+1} para {insumo.nombre}"

            alerta = AlertaInsumo(
                insumo=insumo,
                tipo="STOCK_BAJO",
                mensaje=msg,
            )
            batch.append(alerta)

            if len(batch) >= chunk_size:
                AlertaInsumo.objects.bulk_create(batch)
                creadas_total += len(batch)
                batch.clear()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> {creadas_total} alertas generadas..."
                    )
                )

        if batch:
            AlertaInsumo.objects.bulk_create(batch)
            creadas_total += len(batch)

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ Alertas de stress creadas: {creadas_total}")
        )

    def _crear_movimientos_stress(self, cantidad, lotes, usuario, chunk_size=1000):
        self.stdout.write(self.style.NOTICE("\n[8/8] Creando movimientos de stress..."))

        if not lotes:
            self.stderr.write(self.style.ERROR("No hay lotes para asociar movimientos."))
            return

        entradas_batch = []
        salidas_batch = []
        total_creados = 0

        num_entradas = cantidad // 2
        num_salidas = cantidad - num_entradas
        hoy = date.today()

        # ENTRADAS
        for _ in range(num_entradas):
            lote = random.choice(lotes)
            insumo = lote.insumo
            ubicacion = lote.bodega.ubicaciones.first()
            if not ubicacion:
                continue

            fecha = hoy - timedelta(days=random.randint(0, 60))
            cantidad_e = Decimal(random.randint(1, 50))

            e = Entrada(
                insumo=insumo,
                insumo_lote=lote,
                ubicacion=ubicacion,
                cantidad=cantidad_e,
                fecha=fecha,
                usuario=usuario,
                tipo="COMPRA",
                observaciones="Movimiento de stress (entrada)",
            )
            entradas_batch.append(e)

            if len(entradas_batch) >= chunk_size:
                Entrada.objects.bulk_create(entradas_batch)
                total_creados += len(entradas_batch)
                entradas_batch.clear()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> {total_creados} movimientos (entradas+salidas) creados..."
                    )
                )

        if entradas_batch:
            Entrada.objects.bulk_create(entradas_batch)
            total_creados += len(entradas_batch)

        # SALIDAS
        for _ in range(num_salidas):
            lote = random.choice(lotes)
            insumo = lote.insumo
            ubicacion = lote.bodega.ubicaciones.first()
            if not ubicacion:
                continue

            fecha = hoy - timedelta(days=random.randint(0, 60))
            cantidad_s = Decimal(random.randint(1, 30))

            s = Salida(
                insumo=insumo,
                insumo_lote=lote,
                ubicacion=ubicacion,
                cantidad=cantidad_s,
                fecha_generada=fecha,
                usuario=usuario,
                tipo="USO_PRODUCCION",
                observaciones="Movimiento de stress (salida)",
            )
            salidas_batch.append(s)

            if len(salidas_batch) >= chunk_size:
                Salida.objects.bulk_create(salidas_batch)
                total_creados += len(salidas_batch)
                salidas_batch.clear()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> {total_creados} movimientos (entradas+salidas) creados..."
                    )
                )

        if salidas_batch:
            Salida.objects.bulk_create(salidas_batch)
            total_creados += len(salidas_batch)

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ Movimientos de stress creados: {total_creados}")
        )
