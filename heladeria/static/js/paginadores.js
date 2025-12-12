/**
 * Sistema global para manejar paginadores con AJAX
 * Funciona con cualquier enlace que tenga data-ajax-link
 */

document.addEventListener('DOMContentLoaded', function() {
    // Delegación de eventos para todos los links con data-ajax-link
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a[data-ajax-link]');
        if (!link) return;
        
        e.preventDefault();
        
        const url = link.href;
        const container = link.closest('[data-ajax-container]') || 
                         link.closest('.table-responsive') || 
                         link.closest('table')?.parentElement ||
                         document.querySelector('main') ||
                         document.body;
        
        // Mostrar indicador de carga
        const originalHtml = container.innerHTML;
        container.style.opacity = '0.6';
        container.style.pointerEvents = 'none';
        
        // Hacer request AJAX
        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('Error en la respuesta');
            return response.text();
        })
        .then(data => {
            // Intentar parsear como JSON primero
            try {
                const json = JSON.parse(data);
                if (json.html) {
                    container.innerHTML = json.html;
                } else {
                    container.innerHTML = data;
                }
            } catch (e) {
                // Si no es JSON, usar como HTML directo
                container.innerHTML = data;
            }
            
            container.style.opacity = '1';
            container.style.pointerEvents = 'auto';
            
            // Scroll suave al contenedor
            setTimeout(() => {
                container.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        })
        .catch(error => {
            console.error('Error cargando página:', error);
            container.innerHTML = originalHtml;
            container.style.opacity = '1';
            container.style.pointerEvents = 'auto';
            alert('Error al cargar la página. Intenta de nuevo.');
        });
    });
});
