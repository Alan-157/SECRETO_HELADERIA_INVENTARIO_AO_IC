from django.core.management.base import BaseCommand
from inventario.models import AlertaInsumo


class Command(BaseCommand):
    help = "Elimina todas las alertas inactivas del sistema"

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Elimina TODAS las alertas (activas e inactivas)'
        )
        parser.add_argument(
            '--tipo',
            type=str,
            help='Elimina solo alertas de un tipo específico (SIN_STOCK, BAJO_STOCK, STOCK_EXCESIVO)'
        )

    def handle(self, *args, **options):
        queryset = AlertaInsumo.objects.all()
        
        # Filtrar por tipo si se especifica
        if options['tipo']:
            tipo = options['tipo'].upper()
            queryset = queryset.filter(tipo=tipo)
            tipo_msg = f" de tipo {tipo}"
        else:
            tipo_msg = ""
        
        # Filtrar por estado si no es --all
        if not options['all']:
            queryset = queryset.filter(is_active=False)
            estado_msg = "inactivas"
        else:
            estado_msg = "totales"
        
        # Contar antes de eliminar
        count = queryset.count()
        
        if count == 0:
            self.stdout.write(
                self.style.WARNING(f"No se encontraron alertas {estado_msg}{tipo_msg} para eliminar")
            )
            return
        
        # Confirmar eliminación
        if options['all']:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  ATENCIÓN: Vas a eliminar {count} alertas{tipo_msg}\n"
                )
            )
            confirmacion = input("¿Estás seguro? Escribe 'si' para confirmar: ")
            if confirmacion.lower() != 'si':
                self.stdout.write(self.style.ERROR("Operación cancelada"))
                return
        
        # Eliminar
        eliminadas = queryset.delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ {eliminadas} alerta(s) {estado_msg}{tipo_msg} eliminada(s) exitosamente\n"
            )
        )
