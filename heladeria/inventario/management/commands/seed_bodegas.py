from django.core.management.base import BaseCommand
from inventario.models import Ubicacion, Bodega

class Command(BaseCommand):
    """
    Seed de Bodegas internas de cada Ubicación real.
    Requiere que seed_ubicaciones ya esté ejecutado.
    """
    help = "Crea/actualiza bodegas asociadas a ubicaciones."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Iniciando seed de bodegas..."))

        # Mapa: Ubicación real -> bodegas internas
        data = {
            "Sucursal La Serena Centro": [
                {"nombre": "Bodega Principal", "descripcion": "Bodega general de insumos"},
                {"nombre": "Bodega Cámara Fría", "descripcion": "Insumos refrigerados/congelados"},
            ],
            "Sucursal Coquimbo": [
                {"nombre": "Bodega Secundaria", "descripcion": "Bodega de apoyo"},
            ],
            "Sucursal La Serena Playa": [
                {"nombre": "Bodega Frutas", "descripcion": "Frutas y pulpas"},
                {"nombre": "Bodega Frutas Congeladas", "descripcion": "Fruta congelada"},
            ],
        }

        bodegas_creadas = 0
        bodegas_actualizadas = 0

        for nombre_ubic, bodegas in data.items():
            try:
                ubicacion = Ubicacion.objects.get(nombre=nombre_ubic, is_active=True)
            except Ubicacion.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"No existe la ubicación '{nombre_ubic}'. Ejecuta seed_ubicaciones primero."
                ))
                continue

            for info_bodega in bodegas:
                bodega, created = Bodega.objects.get_or_create(
                    ubicacion=ubicacion,
                    nombre=info_bodega["nombre"],
                    defaults={
                        "descripcion": info_bodega.get("descripcion", ""),
                        "is_active": True,
                    }
                )

                if created:
                    bodegas_creadas += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Bodega creada: {bodega.nombre} ({ubicacion.nombre})"
                    ))
                else:
                    changed = False
                    if bodega.descripcion != info_bodega.get("descripcion", ""):
                        bodega.descripcion = info_bodega.get("descripcion", "")
                        changed = True
                    if not bodega.is_active:
                        bodega.is_active = True
                        changed = True

                    if changed:
                        bodega.save(update_fields=["descripcion", "is_active"])
                        bodegas_actualizadas += 1
                        self.stdout.write(self.style.WARNING(
                            f"Bodega actualizada: {bodega.nombre} ({ubicacion.nombre})"
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"Bodega ya existía: {bodega.nombre} ({ubicacion.nombre})"
                        ))

        self.stdout.write(self.style.SUCCESS(
            f"\nSeed bodegas listo: {bodegas_creadas} creadas, {bodegas_actualizadas} actualizadas."
        ))
