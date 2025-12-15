# GUÍA DE PRUEBA - SISTEMA DE BÚSQUEDA AJAX DE INSUMOS

## 📋 Lista de Verificación Pre-Prueba

Antes de comenzar las pruebas, asegúrate de que:

- [ ] El servidor Django está corriendo (`python manage.py runserver`)
- [ ] Tienes al menos 20-30 insumos en la base de datos
- [ ] Los insumos tienen categorías asignadas
- [ ] Tienes un usuario con permisos de Administrador o Encargado

## 🧪 Casos de Prueba

### Prueba 1: Formulario de Registro de Entrada
**URL:** `/inventario/movimientos/entrada/`

**Pasos:**
1. Navegar a la URL
2. Observar el campo "Insumo" en la primera línea
3. Hacer clic en el campo de insumo

**Resultados Esperados:**
- ✅ El campo está vacío inicialmente
- ✅ Al hacer clic, muestra el placeholder "Buscar insumo..."
- ✅ Muestra un dropdown con los primeros 20 insumos
- ✅ Cada insumo muestra formato: "Nombre (Categoría)"

**Prueba de Búsqueda:**
4. Escribir parte del nombre de un insumo (ej: "lech")
5. Esperar 250ms

**Resultados Esperados:**
- ✅ Muestra "Buscando..." mientras busca
- ✅ Filtra resultados que contienen el texto
- ✅ Búsqueda case-insensitive
- ✅ Resultados aparecen en <500ms

**Prueba de Selección:**
6. Seleccionar un insumo del dropdown
7. Rellenar los demás campos del formulario

**Resultados Esperados:**
- ✅ El insumo seleccionado aparece en el campo
- ✅ Se puede continuar con el resto del formulario

**Prueba de Líneas Dinámicas:**
8. Hacer clic en "Agregar línea" o similar
9. Observar el nuevo campo de insumo

**Resultados Esperados:**
- ✅ El nuevo campo también tiene Select2 configurado
- ✅ Funciona igual que el primero

---

### Prueba 2: Formulario de Registro de Salida
**URL:** `/inventario/movimientos/salida/`

**Pasos:** Repetir los mismos pasos de la Prueba 1

**Resultados Esperados:** Idénticos a la Prueba 1

---

### Prueba 3: Formulario de Crear Orden
**URL:** `/inventario/ordenes/crear/` (verificar URL exacta en urls.py)

**Pasos:** Repetir los pasos básicos de la Prueba 1

**Resultados Esperados:** Idénticos a la Prueba 1

---

### Prueba 4: Formulario de Crear Alerta
**URL:** `/inventario/alertas/crear/`

**Pasos:**
1. Navegar a la URL
2. Observar el campo "Insumo"
3. Hacer clic en el campo

**Resultados Esperados:**
- ✅ Select2 configurado correctamente
- ✅ Búsqueda funciona igual que en otros formularios

---

### Prueba 5: Paginación de Resultados
**URL:** Cualquier formulario con campo de insumo

**Pre-requisito:** Tener más de 20 insumos en la BD

**Pasos:**
1. Hacer clic en el campo de insumo sin escribir nada
2. Scroll down hasta el final de la lista
3. Observar el comportamiento

**Resultados Esperados:**
- ✅ Muestra "Cargando más resultados..." al hacer scroll
- ✅ Carga automáticamente los siguientes 20 resultados
- ✅ No hay duplicados en la lista

---

### Prueba 6: Edición de Movimiento (Entrada)
**URL:** `/inventario/movimientos/entrada/<id>/editar/`

**Pasos:**
1. Ir a la lista de movimientos
2. Editar una entrada existente
3. Observar el campo de insumo

**Resultados Esperados:**
- ✅ El insumo actual aparece seleccionado
- ✅ El campo está deshabilitado (no editable)
- ✅ No hay error de carga

---

### Prueba 7: Sin Resultados
**URL:** Cualquier formulario con campo de insumo

**Pasos:**
1. Escribir un texto que no coincida con ningún insumo
   (ej: "xyz123abcnonexiste")
2. Observar el comportamiento

**Resultados Esperados:**
- ✅ Muestra mensaje "No se encontraron insumos"
- ✅ No hay error JavaScript en la consola
- ✅ Se puede seguir escribiendo/buscando

---

### Prueba 8: Rendimiento
**URL:** Cualquier formulario con campo de insumo

**Herramientas:** Chrome DevTools (F12) > Network tab

**Pasos:**
1. Abrir DevTools antes de cargar la página
2. Navegar al formulario
3. Observar el Network tab

**Mediciones:**
- Tiempo de carga de la página HTML: _____ms
- Tamaño del HTML: _____KB

**Pasos Adicionales:**
4. Abrir el campo de insumo
5. Escribir "a" para buscar
6. Observar la llamada AJAX en Network

**Mediciones:**
- URL de la llamada: `/inventario/api/buscar-insumos/?q=a&page=1`
- Tiempo de respuesta: _____ms
- Tamaño de respuesta: _____KB
- Número de resultados: _____

**Resultados Esperados:**
- ✅ Página carga en <1 segundo
- ✅ Respuesta AJAX en <500ms
- ✅ Tamaño HTML reducido significativamente
- ✅ Máximo 20 resultados por página

---

### Prueba 9: Compatibilidad de Navegadores

**Navegadores a Probar:**
- [ ] Chrome (última versión)
- [ ] Firefox (última versión)
- [ ] Edge (última versión)
- [ ] Safari (si está disponible)

**Para cada navegador:**
1. Cargar cualquier formulario con insumo
2. Realizar búsqueda
3. Seleccionar un insumo

**Resultados Esperados:**
- ✅ Funciona igual en todos los navegadores
- ✅ No hay errores en la consola

---

### Prueba 10: Validación de Formulario
**URL:** `/inventario/movimientos/entrada/`

**Pasos:**
1. Seleccionar un insumo usando Select2
2. Rellenar otros campos obligatorios
3. Dejar un campo requerido vacío
4. Enviar el formulario

**Resultados Esperados:**
- ✅ El insumo seleccionado se mantiene
- ✅ Muestra errores de validación apropiados
- ✅ No se pierde la selección del insumo

**Prueba de Envío Exitoso:**
5. Corregir los errores
6. Enviar nuevamente

**Resultados Esperados:**
- ✅ Formulario se envía correctamente
- ✅ El movimiento se crea en la BD
- ✅ Redirección exitosa

---

## 🐛 Problemas Comunes y Soluciones

### Problema 1: Campo de insumo no muestra Select2
**Síntomas:** Campo aparece como select HTML normal

**Verificar:**
1. Abrir consola del navegador (F12)
2. Buscar errores JavaScript

**Posibles Causas:**
- jQuery no se cargó correctamente
- Select2 no se cargó
- `insumo-select2.js` no se encontró
- Error en la inicialización

**Solución:**
```html
<!-- Verificar que estos estén en el template -->
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
<script src="{% static 'js/insumo-select2.js' %}"></script>
```

---

### Problema 2: Búsqueda no devuelve resultados
**Síntomas:** Al escribir, siempre dice "No se encontraron insumos"

**Verificar:**
1. Network tab: ¿La llamada AJAX se está haciendo?
2. ¿Cuál es la respuesta del servidor?

**Posibles Causas:**
- URL de la API incorrecta
- CSRF token faltante
- Permisos de usuario

**Solución:**
```javascript
// Verificar que la URL es correcta
const apiUrl = "{% url 'inventario:api_buscar_insumos' %}";
console.log('API URL:', apiUrl); // Debe mostrar /inventario/api/buscar-insumos/
```

---

### Problema 3: Error "queryset has no attribute 'value'"
**Síntomas:** Error 500 al cargar el formulario

**Causa:** El queryset del campo es `None` en vez de `.none()`

**Solución en forms.py:**
```python
# INCORRECTO
insumo = forms.ModelChoiceField(queryset=None, ...)

# CORRECTO
insumo = forms.ModelChoiceField(queryset=Insumo.objects.none(), ...)
```

---

### Problema 4: Insumo no se precarga al editar
**Síntomas:** Campo vacío al editar un registro existente

**Verificar en forms.py:**
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if self.instance and self.instance.pk and self.instance.insumo:
        # Cargar solo el insumo de la instancia
        self.fields['insumo'].queryset = Insumo.objects.filter(
            id=self.instance.insumo.id
        )
```

---

### Problema 5: Select2 no funciona en líneas dinámicas
**Síntomas:** La primera línea funciona, pero líneas añadidas no

**Verificar en el template:**
```javascript
// Debe tener código similar a esto
document.getElementById('add-row').addEventListener('click', function() {
    setTimeout(function() {
        const newSelect = document.querySelector('select[name*="insumo"]:not([data-select2-initialized])');
        if (newSelect) {
            window.initializeInsumoSelect2(newSelect, apiUrl);
        }
    }, 100);
});
```

---

## 📊 Métricas de Éxito

### Antes de la Implementación
- Tiempo de carga: _____ segundos
- Tamaño HTML: _____ MB
- Queries a BD: _____ queries

### Después de la Implementación
- Tiempo de carga: _____ segundos (objetivo: <1s)
- Tamaño HTML: _____ KB (objetivo: <100KB)
- Queries a BD: _____ queries (objetivo: solo al buscar)

### Mejora Estimada
- Reducción de tiempo: _____%
- Reducción de tamaño: _____%

---

## ✅ Checklist de Aceptación

Marcar como completado cuando todos los criterios se cumplan:

- [ ] Todos los formularios cargan en <1 segundo
- [ ] La búsqueda funciona correctamente
- [ ] Los resultados se filtran en tiempo real
- [ ] La paginación funciona (>20 insumos)
- [ ] Select2 funciona en líneas dinámicas
- [ ] Los valores se mantienen al editar
- [ ] No hay errores en la consola del navegador
- [ ] La validación de formularios funciona
- [ ] Compatible con Chrome, Firefox, Edge
- [ ] El sistema funciona con 100+ insumos sin problemas

---

## 📝 Reporte de Pruebas

**Fecha:** _______________
**Probado por:** _______________
**Entorno:** Desarrollo / Producción
**Navegador:** _______________
**Versión Django:** _______________

### Resumen de Resultados
- Pruebas Pasadas: ___ / 10
- Pruebas Fallidas: ___ / 10
- Bugs Encontrados: ___

### Bugs/Problemas Identificados
1. _______________________________
2. _______________________________
3. _______________________________

### Comentarios Adicionales
_______________________________
_______________________________
_______________________________

---

**Nota:** Si encuentras problemas durante las pruebas, consulta:
1. `BUSQUEDA_AJAX_INSUMOS.md` - Documentación técnica completa
2. `RESUMEN_IMPLEMENTACION_AJAX.md` - Resumen de cambios
3. Consola del navegador (F12) - Errores JavaScript
4. Logs de Django - Errores del servidor
