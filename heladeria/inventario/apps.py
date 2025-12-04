from django.apps import AppConfig


class InventarioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventario'

    def ready(self): 
        # Importa el módulo de señales para que se conecten los listeners.
        import inventario.signals
