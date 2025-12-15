from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """
    Divide una cadena por el separador especificado.
    Uso: {{ "10,25,50"|split:"," }}
    """
    if value is None:
        return []
    return value.split(arg)
