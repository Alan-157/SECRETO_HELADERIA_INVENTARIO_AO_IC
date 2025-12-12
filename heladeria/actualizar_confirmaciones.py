"""
Script para actualizar automáticamente los botones de eliminación 
en los templates con las confirmaciones de SweetAlert2.

USO:
    python actualizar_confirmaciones.py

Este script:
1. Busca todos los templates HTML en inventario/templates/
2. Identifica botones/enlaces con data-delete-form
3. Los actualiza agregando atributos data-confirm
4. Crea un backup antes de modificar
"""

import os
import re
from pathlib import Path
import shutil
from datetime import datetime

# Directorio de templates
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / 'inventario' / 'templates'

# Crear directorio de backups
BACKUP_DIR = BASE_DIR / 'backups_templates' / datetime.now().strftime('%Y%m%d_%H%M%S')
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def backup_file(filepath):
    """Crea un backup del archivo"""
    relative_path = filepath.relative_to(TEMPLATES_DIR)
    backup_path = BACKUP_DIR / relative_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(filepath, backup_path)
    print(f"  ✓ Backup creado: {backup_path}")

def find_delete_buttons(html_content):
    """Encuentra botones de eliminación en el HTML"""
    # Patrón para encontrar elementos con data-delete-form
    pattern = r'<(button|a)[^>]*data-delete-form[^>]*>.*?</\1>'
    matches = re.finditer(pattern, html_content, re.DOTALL | re.IGNORECASE)
    return list(matches)

def extract_context_info(match_obj, html_content):
    """Extrae información contextual para mensajes personalizados"""
    element = match_obj.group(0)
    
    # Buscar nombre del elemento a eliminar en el contexto
    # Ejemplo: {{ proveedor.nombre }}, {{ insumo.nombre }}, etc.
    name_patterns = [
        r'\{\{\s*(\w+)\.nombre\s*\}\}',
        r'\{\{\s*(\w+)\.nombre_empresa\s*\}\}',
        r'#\{\{\s*(\w+)\.id\s*\}\}',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, element)
        if match:
            return match.group(0)
    
    # Buscar en líneas anteriores (contexto)
    lines_before = html_content[:match_obj.start()].split('\n')[-5:]
    for line in reversed(lines_before):
        for pattern in name_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(0)
    
    return None

def update_button(match_obj, html_content):
    """Actualiza un botón añadiendo atributos data-confirm"""
    element = match_obj.group(0)
    
    # Si ya tiene data-confirm, no modificar
    if 'data-confirm' in element:
        return element
    
    # Extraer información contextual
    context = extract_context_info(match_obj, html_content)
    
    # Determinar el tipo de elemento
    if 'proveedor' in element.lower():
        tipo = 'proveedor'
        mensaje = f"¿Estás seguro de eliminar el proveedor {context or 'seleccionado'}?"
    elif 'insumo' in element.lower():
        tipo = 'insumo'
        mensaje = f"¿Estás seguro de eliminar el insumo {context or 'seleccionado'}?"
    elif 'lote' in element.lower():
        tipo = 'lote'
        mensaje = f"¿Estás seguro de eliminar el lote {context or 'seleccionado'}?"
    elif 'entrada' in element.lower():
        tipo = 'entrada'
        mensaje = f"¿Estás seguro de eliminar esta entrada? Esta acción no se puede deshacer."
    elif 'salida' in element.lower():
        tipo = 'salida'
        mensaje = f"¿Estás seguro de eliminar esta salida? Esta acción no se puede deshacer."
    elif 'orden' in element.lower():
        tipo = 'orden'
        mensaje = f"¿Estás seguro de eliminar la orden {context or 'seleccionada'}?"
    elif 'bodega' in element.lower():
        tipo = 'bodega'
        mensaje = f"¿Estás seguro de eliminar la bodega {context or 'seleccionada'}?"
    elif 'categoria' in element.lower():
        tipo = 'categoría'
        mensaje = f"¿Estás seguro de eliminar la categoría {context or 'seleccionada'}?"
    else:
        tipo = 'elemento'
        mensaje = "¿Estás seguro de eliminar este elemento?"
    
    # Construir nuevos atributos
    new_attrs = f'''data-confirm="{mensaje}"
               data-confirm-title="⚠️ Confirmar eliminación de {tipo}"
               data-confirm-text="Sí, eliminar"'''
    
    # Reemplazar data-delete-form con los nuevos atributos
    updated = element.replace('data-delete-form', new_attrs)
    
    return updated

def process_file(filepath):
    """Procesa un archivo HTML"""
    print(f"\n📄 Procesando: {filepath.relative_to(TEMPLATES_DIR)}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Buscar botones de eliminación
        matches = find_delete_buttons(content)
        
        if not matches:
            print("  → No se encontraron botones de eliminación")
            return False
        
        print(f"  → Encontrados {len(matches)} botón(es) de eliminación")
        
        # Crear backup
        backup_file(filepath)
        
        # Actualizar cada botón
        offset = 0
        for match in matches:
            updated_button = update_button(match, content)
            start = match.start() + offset
            end = match.end() + offset
            
            content = content[:start] + updated_button + content[end:]
            offset += len(updated_button) - len(match.group(0))
        
        # Guardar archivo actualizado
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✅ Archivo actualizado exitosamente")
            return True
        else:
            print("  → No se realizaron cambios")
            return False
            
    except Exception as e:
        print(f"  ❌ Error al procesar archivo: {e}")
        return False

def main():
    print("=" * 60)
    print("🔧 ACTUALIZADOR DE CONFIRMACIONES DE ELIMINACIÓN")
    print("=" * 60)
    print(f"\n📂 Directorio de templates: {TEMPLATES_DIR}")
    print(f"💾 Backups en: {BACKUP_DIR}\n")
    
    # Buscar todos los archivos HTML
    html_files = list(TEMPLATES_DIR.rglob('*.html'))
    print(f"📋 Se encontraron {len(html_files)} archivo(s) HTML\n")
    
    # Procesar cada archivo
    updated_count = 0
    for filepath in html_files:
        if process_file(filepath):
            updated_count += 1
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    print(f"✅ Archivos actualizados: {updated_count}")
    print(f"📁 Archivos procesados: {len(html_files)}")
    print(f"💾 Backups guardados en: {BACKUP_DIR}")
    print("\n✨ ¡Proceso completado!")

if __name__ == '__main__':
    main()
