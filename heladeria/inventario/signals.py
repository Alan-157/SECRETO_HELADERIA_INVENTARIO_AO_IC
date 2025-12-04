# heladeria/inventario/signals.py (Contenido Corregido)

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Insumo
from .services import check_and_create_stock_alerts # <--- CAMBIO AQUÍ

@receiver(post_save, sender=Insumo)
def insumo_post_save_check_alerts(sender, instance, created, **kwargs):
    """
    Verifica los niveles de stock inmediatamente después de crear o guardar un insumo.
    """
    # Se ejecuta al crear un insumo para generar inmediatamente la alerta si corresponde.
    # También se ejecuta si se guardan campos de actualización (ej. al editar el stock min/max).
    if created or kwargs.get('update_fields'):
        check_and_create_stock_alerts(instance)