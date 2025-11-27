from django.core.management.base import BaseCommand
from inventario.models import Proveedor
from decimal import Decimal

class Command(BaseCommand):
    help = "Crea un proveedor de prueba inicial para el sistema."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Intentando crear proveedor de prueba..."))

        try:
            proveedor, creado = Proveedor.objects.get_or_create(
                # Usamos el RUT como clave única para evitar duplicados
                rut_empresa="76123456-K",
                defaults={
                    "nombre_empresa": "Distribuidora Central S.A.",
                    "email": "contacto@central.cl",
                    "telefono": "56955551234",
                    "direccion": "Av. Principal 123, Centro",
                    "ciudad": "Santiago",
                    "region": "Metropolitana",
                    "dias_credito": 30,
                    "monto_credito": Decimal("500000.00"),
                    "observaciones": "Proveedor de prueba para insumos lácteos y envasados.",
                }
            )
            
            if creado:
                self.stdout.write(self.style.SUCCESS(f"✅ Proveedor '{proveedor.nombre_empresa}' creado con éxito."))
            else:
                self.stdout.write(self.style.WARNING(f"⚠ Proveedor 'Distribuidora Central S.A.' ya existía."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error al crear proveedor: {e}"))

        self.stdout.write(self.style.SUCCESS("Carga de proveedores finalizada."))