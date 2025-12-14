#!/usr/bin/env python
"""
Script de prueba para verificar el funcionamiento de la API de búsqueda AJAX de insumos.
"""

import requests
import json
from urllib.parse import urljoin

# Configuración
BASE_URL = "http://localhost:8000"  # Cambiar según tu configuración
API_ENDPOINT = "/inventario/api/buscar-insumos/"

def test_api_search():
    """Prueba la búsqueda básica de insumos."""
    print("=" * 60)
    print("PRUEBA 1: Búsqueda básica")
    print("=" * 60)
    
    url = urljoin(BASE_URL, API_ENDPOINT)
    params = {"q": "leche", "page": 1}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Resultados encontrados: {len(data.get('results', []))}")
        print(f"✅ Hay más páginas: {data.get('pagination', {}).get('more', False)}")
        
        if data.get('results'):
            print("\n📦 Primer resultado:")
            print(json.dumps(data['results'][0], indent=2, ensure_ascii=False))
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la solicitud: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Error al decodificar JSON: {e}")
        return False

def test_api_pagination():
    """Prueba la paginación de resultados."""
    print("\n" + "=" * 60)
    print("PRUEBA 2: Paginación")
    print("=" * 60)
    
    url = urljoin(BASE_URL, API_ENDPOINT)
    
    # Primera página
    params = {"page": 1}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        total_page1 = len(data.get('results', []))
        has_more = data.get('pagination', {}).get('more', False)
        
        print(f"✅ Página 1: {total_page1} resultados")
        print(f"✅ Tiene más páginas: {has_more}")
        
        if has_more:
            # Segunda página
            params = {"page": 2}
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            total_page2 = len(data.get('results', []))
            
            print(f"✅ Página 2: {total_page2} resultados")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la solicitud: {e}")
        return False

def test_api_by_ids():
    """Prueba la búsqueda por IDs específicos."""
    print("\n" + "=" * 60)
    print("PRUEBA 3: Búsqueda por IDs")
    print("=" * 60)
    
    url = urljoin(BASE_URL, API_ENDPOINT)
    params = {"ids": "1,2,3"}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Resultados encontrados: {len(data.get('results', []))}")
        
        if data.get('results'):
            print("\n📦 Resultados por IDs:")
            for result in data['results']:
                print(f"  - ID: {result['id']}, Texto: {result['text']}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la solicitud: {e}")
        return False

def test_api_empty_search():
    """Prueba la búsqueda sin parámetros (todos los insumos)."""
    print("\n" + "=" * 60)
    print("PRUEBA 4: Búsqueda sin parámetros (lista completa)")
    print("=" * 60)
    
    url = urljoin(BASE_URL, API_ENDPOINT)
    params = {}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Resultados encontrados: {len(data.get('results', []))}")
        print(f"✅ Total máximo por página: 20")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la solicitud: {e}")
        return False

def test_api_no_results():
    """Prueba la búsqueda que no encuentra resultados."""
    print("\n" + "=" * 60)
    print("PRUEBA 5: Búsqueda sin resultados")
    print("=" * 60)
    
    url = urljoin(BASE_URL, API_ENDPOINT)
    params = {"q": "insumo_que_no_existe_xyz123"}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Resultados encontrados: {len(data.get('results', []))}")
        
        if len(data.get('results', [])) == 0:
            print("✅ Correctamente devuelve array vacío")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la solicitud: {e}")
        return False

def main():
    """Ejecuta todas las pruebas."""
    print("\n🚀 INICIANDO PRUEBAS DE API DE BÚSQUEDA DE INSUMOS")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"🔗 Endpoint: {API_ENDPOINT}\n")
    
    tests = [
        test_api_search,
        test_api_pagination,
        test_api_by_ids,
        test_api_empty_search,
        test_api_no_results
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Excepción en {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    print(f"✅ Pruebas exitosas: {passed}")
    print(f"❌ Pruebas fallidas: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
    else:
        print(f"\n⚠️  {failed} prueba(s) fallaron. Revisar logs arriba.")

if __name__ == "__main__":
    print("\n⚠️  NOTA: Este script requiere que el servidor esté corriendo.")
    print("⚠️  Ejecutar primero: python manage.py runserver")
    print("⚠️  Si el servidor corre en otro puerto/host, editar BASE_URL en el script.\n")
    
    input("Presiona ENTER para continuar con las pruebas...")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Pruebas interrumpidas por el usuario.")
