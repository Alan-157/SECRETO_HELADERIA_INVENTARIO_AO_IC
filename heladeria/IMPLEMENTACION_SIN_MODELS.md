# 🚀 IMPLEMENTACIÓN SIMPLE - SIN MODIFICAR models.py

## ✨ Sistema de Toggle de Alertas usando Django Cache

Esta implementación **NO requiere**:
- ❌ Modificar `models.py`
- ❌ Crear migraciones
- ❌ Agregar nuevas tablas

Solo usa el **cache de Django** que ya está configurado en tu proyecto.

---

## 📦 Paso 1: Copiar archivos creados

Ya se crearon estos archivos nuevos:
- ✅ `inventario/alertas_config.py` - Funciones para manejar el estado
- ✅ `inventario/services_CACHE.py` - Services actualizado
- ✅ `inventario/vista_alertas_cache.py` - Vista para la configuración
- ✅ `inventario/templates/inventario/configurar_alertas_CACHE.html` - Template

---

## 🔧 Paso 2: Actualizar services.py

Reemplaza el contenido completo de `inventario/services.py` con `services_CACHE.py`:

```bash
cd c:\Users\Alan_\Downloads\SECRETO_HELADERIA_INVENTARIO_AO_IC\heladeria
Copy-Item inventario\services_CACHE.py inventario\services.py -Force
```

---

## 🌐 Paso 3: Agregar vista a views.py

Abre `inventario/views.py` y **copia esta función** (puedes ponerla al final):

```python
from django.contrib.admin.views.decorators import staff_member_required
from .alertas_config import (
    alertas_activadas, 
    activar_alertas, 
    desactivar_alertas,
    get_estado_alertas
)

@staff_member_required
def configurar_alertas(request):
    """Vista para configurar alertas usando cache"""
    if request.method == 'POST':
        nuevo_estado = request.POST.get('alertas_activas') == 'on'
        
        if nuevo_estado:
            activar_alertas()
            messages.success(request, "✓ Alertas activadas exitosamente")
        else:
            desactivar_alertas()
            messages.info(request, "✓ Alertas desactivadas exitosamente")
        
        return redirect('configurar_alertas')
    
    context = get_estado_alertas()
    return render(request, 'inventario/configurar_alertas_CACHE.html', context)
```

---

## 🔗 Paso 4: Agregar URL

Abre `inventario/urls.py` y agrega esta línea en `urlpatterns`:

```python
path('configuracion/alertas/', views.configurar_alertas, name='configurar_alertas'),
```

---

## 🎨 Paso 5: Agregar script de confirmaciones

Abre `inventario/templates/base.html` y busca la línea de SweetAlert2:

```html
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>

<!-- AGREGAR ESTA LÍNEA DESPUÉS: -->
<script src="{% static 'js/confirmaciones.js' %}"></script>
```

---

## 🧪 Paso 6: Probar

```bash
# 1. Iniciar servidor
python manage.py runserver

# 2. Acceder a:
http://127.0.0.1:8000/inventario/configuracion/alertas/

# 3. Probar el toggle:
#    - Activar/desactivar el switch
#    - Debe aparecer confirmación con SweetAlert2
#    - El estado se guarda en cache
```

---

## 🔍 Verificar funcionamiento

```python
# En Python shell:
python manage.py shell

>>> from inventario.alertas_config import alertas_activadas, desactivar_alertas, activar_alertas

# Ver estado actual
>>> alertas_activadas()
True

# Desactivar
>>> desactivar_alertas()
False

# Verificar
>>> alertas_activadas()
False

# Activar nuevamente
>>> activar_alertas()
True
```

---

## ⚙️ Cómo funciona

### Django Cache
El sistema usa `django.core.cache` que por defecto guarda los datos en memoria. Para producción, configura un cache persistente en `settings.py`:

```python
# Para usar base de datos (persistente entre reinicios)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
    }
}
```

Luego ejecuta:
```bash
python manage.py createcachetable
```

### O usar archivo (simple y persistente):
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': 'c:\\tmp\\django_cache',
    }
}
```

---

## 📋 Ventajas de este método

✅ **Sin migraciones** - No modifica la base de datos  
✅ **Implementación rápida** - Solo 4 pasos  
✅ **Sin cambios en models.py** - Usa cache de Django  
✅ **Funciona inmediatamente** - Cache en memoria por defecto  
✅ **Fácil de revertir** - Solo borrar archivos nuevos  

---

## 🎯 Resumen de cambios

1. **Nuevo archivo**: `inventario/alertas_config.py` (funciones del cache)
2. **Nuevo archivo**: `inventario/services_CACHE.py` (services con toggle)
3. **Nuevo archivo**: `inventario/vista_alertas_cache.py` (vista helper)
4. **Nuevo template**: `configurar_alertas_CACHE.html`
5. **Modificar**: `inventario/views.py` (agregar función configurar_alertas)
6. **Modificar**: `inventario/urls.py` (agregar URL)
7. **Modificar**: `base.html` (cargar confirmaciones.js)
8. **Reemplazar**: `services.py` con `services_CACHE.py`

---

## 🔄 Para actualizar templates automáticamente

Si ya tienes el script `actualizar_confirmaciones.py`:

```bash
python actualizar_confirmaciones.py
```

Esto agregará automáticamente `data-confirm` a todos los botones de eliminación.

---

**¡Listo! Sistema funcionando sin tocar models.py 🎉**
