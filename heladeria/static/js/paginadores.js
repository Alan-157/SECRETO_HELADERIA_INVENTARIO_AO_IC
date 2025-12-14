/**
 * Sistema global para manejar paginadores con AJAX
 * Funciona con cualquier enlace que tenga data-ajax-link
 * y formularios con data-ajax-form
 */

/**
 * Inicializa el paginador AJAX en un contenedor
 * @param {Object} options - Configuración del paginador
 * @param {string} options.formSelector - Selector del formulario de búsqueda
 * @param {string} options.resultsSelector - Selector del contenedor de resultados
 * @param {number} options.searchDelay - Delay para búsqueda en tiempo real (ms)
 */
function initAjaxPaginator(options = {}) {
    const {
        formSelector = '#filter-form',
        resultsSelector = '#results',
        searchDelay = 300
    } = options;

    const form = document.querySelector(formSelector);
    const resultsContainer = document.querySelector(resultsSelector);
    
    if (!form || !resultsContainer) {
        console.warn('Paginador AJAX: No se encontró el formulario o contenedor de resultados');
        return;
    }

    let searchTimeout = null;

    // Handler para búsqueda en tiempo real
    const searchInput = form.querySelector('input[name="q"]');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                submitFormAjax(form, resultsContainer);
            }, searchDelay);
        });
    }

    // Handler para submit del formulario
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        submitFormAjax(form, resultsContainer);
    });
}

/**
 * Envía un formulario por AJAX y actualiza el contenedor de resultados
 * @param {HTMLFormElement} form - Formulario a enviar
 * @param {HTMLElement} resultsContainer - Contenedor donde mostrar resultados
 */
function submitFormAjax(form, resultsContainer) {
    const formData = new FormData(form);
    const queryString = new URLSearchParams(formData).toString();
    const url = form.action ? `${form.action}?${queryString}` : `?${queryString}`;

    loadContentAjax(url, resultsContainer);
}

/**
 * Carga contenido por AJAX en un contenedor
 * @param {string} url - URL a cargar
 * @param {HTMLElement} container - Contenedor donde mostrar el contenido
 */
function loadContentAjax(url, container) {
    const originalHtml = container.innerHTML;
    container.style.opacity = '0.6';
    container.style.pointerEvents = 'none';

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
}

// Auto-inicialización global para todos los links con data-ajax-link
document.addEventListener('DOMContentLoaded', function() {
    // Delegación de eventos para todos los links con data-ajax-link
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a[data-ajax-link]');
        if (!link) return;
        
        e.preventDefault();
        
        const url = link.href;
        const container = link.closest('[data-ajax-container]') || 
                         link.closest('#results') ||
                         link.closest('.table-responsive') || 
                         link.closest('table')?.parentElement ||
                         document.querySelector('main') ||
                         document.body;
        
        loadContentAjax(url, container);
    });
});
