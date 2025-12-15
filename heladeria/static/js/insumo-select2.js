/**
 * Configuración global de Select2 para selectores de insumos
 * Usar en cualquier formulario que tenga selección de insumos
 */

(function() {
    'use strict';

    /**
     * Inicializa Select2 en un selector de insumo
     * @param {HTMLElement} selectElement - El elemento <select> a inicializar
     * @param {string} apiUrl - URL de la API de búsqueda de insumos
     */
    window.initializeInsumoSelect2 = function(selectElement, apiUrl) {
        if (!selectElement || selectElement.hasAttribute('data-select2-initialized')) {
            return;
        }

        const $select = $(selectElement);
        
        // Si el select está deshabilitado, no inicializar Select2
        if (selectElement.hasAttribute('disabled')) {
            return;
        }

        // Guardar el valor y texto actual si existe
        const currentValue = $select.val();
        const currentText = $select.find('option:selected').text();
        
        // Configuración de Select2
        $select.select2({
            theme: 'bootstrap-5',
            placeholder: 'Buscar insumo...',
            allowClear: true,
            width: '100%',
            language: {
                noResults: function() {
                    return "No se encontraron insumos";
                },
                searching: function() {
                    return "Buscando...";
                },
                inputTooShort: function() {
                    return "Escribe para buscar";
                },
                loadingMore: function() {
                    return "Cargando más resultados...";
                }
            },
            ajax: {
                url: apiUrl,
                dataType: 'json',
                delay: 250,
                data: function (params) {
                    return {
                        q: params.term,
                        page: params.page || 1
                    };
                },
                processResults: function (data) {
                    return {
                        results: data.results,
                        pagination: data.pagination
                    };
                },
                cache: true
            },
            minimumInputLength: 0
        });

        // Si hay un valor preseleccionado, mantenerlo
        if (currentValue && currentText && currentText.trim() !== '' && currentText.trim() !== '---------') {
            const newOption = new Option(currentText, currentValue, true, true);
            $select.empty().append(newOption).trigger('change');
        }

        // Marcar como inicializado
        selectElement.setAttribute('data-select2-initialized', 'true');
    };

    /**
     * Inicializa todos los selectores de insumo en el documento
     * @param {string} apiUrl - URL de la API de búsqueda de insumos
     * @param {string} selector - Selector CSS personalizado (opcional)
     */
    window.initializeAllInsumoSelects = function(apiUrl, selector) {
        const defaultSelector = 'select[name*="insumo"]:not([name*="lote"]):not([name*="orden"]):not([disabled])';
        const selectorToUse = selector || defaultSelector;
        
        document.querySelectorAll(selectorToUse).forEach(function(select) {
            window.initializeInsumoSelect2(select, apiUrl);
        });
    };

    /**
     * Destruye Select2 de un selector (útil para resetear formularios)
     * @param {HTMLElement} selectElement - El elemento <select>
     */
    window.destroyInsumoSelect2 = function(selectElement) {
        if (selectElement && selectElement.hasAttribute('data-select2-initialized')) {
            $(selectElement).select2('destroy');
            selectElement.removeAttribute('data-select2-initialized');
        }
    };

})();
