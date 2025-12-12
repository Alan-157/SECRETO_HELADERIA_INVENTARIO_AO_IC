/**
 * Sistema de confirmaciones con SweetAlert2
 * Uso: agregar atributo data-confirm="mensaje" a enlaces/botones de eliminación
 */

document.addEventListener('DOMContentLoaded', function() {
    // Configurar SweetAlert2 con tema personalizado
    const SwalConfig = {
        customClass: {
            confirmButton: 'btn btn-danger',
            cancelButton: 'btn btn-secondary'
        },
        buttonsStyling: false
    };

    // Interceptar todos los elementos con data-confirm
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function(e) {
            e.preventDefault();
            
            const mensaje = this.getAttribute('data-confirm') || '¿Estás seguro de que deseas eliminar este elemento?';
            const titulo = this.getAttribute('data-confirm-title') || '¿Confirmar eliminación?';
            const tipo = this.getAttribute('data-confirm-type') || 'warning';
            const textoConfirmar = this.getAttribute('data-confirm-text') || 'Sí, eliminar';
            const textoCancelar = this.getAttribute('data-cancel-text') || 'Cancelar';
            
            // Si es un formulario, guardarlo para enviarlo después
            const form = this.closest('form');
            const href = this.getAttribute('href');
            
            Swal.fire({
                title: titulo,
                text: mensaje,
                icon: tipo,
                showCancelButton: true,
                confirmButtonText: textoConfirmar,
                cancelButtonText: textoCancelar,
                reverseButtons: true,
                ...SwalConfig
            }).then((result) => {
                if (result.isConfirmed) {
                    // Si es un formulario POST, enviarlo
                    if (form && form.method.toUpperCase() === 'POST') {
                        form.submit();
                    }
                    // Si es un enlace, navegar
                    else if (href) {
                        window.location.href = href;
                    }
                }
            });
        });
    });

    // Confirmación especial para eliminación de lotes con stock
    document.querySelectorAll('[data-confirm-stock]').forEach(element => {
        element.addEventListener('click', function(e) {
            e.preventDefault();
            
            const stock = this.getAttribute('data-stock-actual') || '0';
            const nombre = this.getAttribute('data-nombre') || 'este lote';
            const href = this.getAttribute('href');
            
            Swal.fire({
                title: '⚠️ Lote con stock activo',
                html: `
                    <p><strong>${nombre}</strong> tiene <strong>${stock}</strong> unidades en stock.</p>
                    <p>Debe registrar una salida para agotarlo antes de eliminarlo.</p>
                `,
                icon: 'warning',
                confirmButtonText: 'Entendido',
                ...SwalConfig
            });
        });
    });

    // Confirmación para desactivar alertas globalmente
    document.querySelectorAll('[data-confirm-alertas]').forEach(element => {
        element.addEventListener('change', function(e) {
            const isChecked = this.checked;
            const form = this.closest('form');
            
            if (!isChecked) {
                // Si están desactivando alertas, pedir confirmación
                e.preventDefault();
                
                Swal.fire({
                    title: '¿Desactivar alertas de stock?',
                    html: `
                        <p>Esto desactivará la generación automática de alertas en todo el sistema.</p>
                        <p class="text-warning"><strong>Las alertas existentes permanecerán, pero no se crearán nuevas.</strong></p>
                    `,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: 'Sí, desactivar',
                    cancelButtonText: 'Cancelar',
                    reverseButtons: true,
                    ...SwalConfig
                }).then((result) => {
                    if (result.isConfirmed) {
                        this.checked = false;
                        if (form) {
                            // Enviar AJAX en lugar de formulario normal
                            enviarFormularioAlertasAJAX(form);
                        }
                    } else {
                        this.checked = true;
                    }
                });
            } else {
                // Si están activando, pedir confirmación también
                Swal.fire({
                    title: '¿Activar alertas de stock?',
                    html: '<p>Se reanudarán la generación automática de alertas en el sistema.</p>',
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: 'Sí, activar',
                    cancelButtonText: 'Cancelar',
                    reverseButtons: true,
                    ...SwalConfig
                }).then((result) => {
                    if (result.isConfirmed) {
                        this.checked = true;
                        if (form) {
                            enviarFormularioAlertasAJAX(form);
                        }
                    } else {
                        this.checked = false;
                    }
                });
            }
        });
    });
});

/**
 * Función helper para mostrar confirmación programática
 */
function confirmarEliminacion(opciones = {}) {
    const config = {
        title: opciones.title || '¿Confirmar eliminación?',
        text: opciones.text || '¿Estás seguro de que deseas eliminar este elemento?',
        icon: opciones.icon || 'warning',
        showCancelButton: true,
        confirmButtonText: opciones.confirmText || 'Sí, eliminar',
        cancelButtonText: opciones.cancelText || 'Cancelar',
        reverseButtons: true,
        customClass: {
            confirmButton: 'btn btn-danger',
            cancelButton: 'btn btn-secondary'
        },
        buttonsStyling: false
    };
    
    return Swal.fire(config);
}

/**
 * Enviar formulario de alertas via AJAX sin recargar página
 */
function enviarFormularioAlertasAJAX(form) {
    const formData = new FormData(form);
    const estadoAlerta = formData.get('alertas_activas') ? 'activadas' : 'desactivadas';
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarToast(`✓ Alertas ${estadoAlerta} exitosamente`, 'success');
            // Actualizar el estado del switch en otros lugares si es necesario
            document.querySelectorAll('[data-confirm-alertas]').forEach(elem => {
                elem.checked = data.estado;
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarToast('❌ Error al actualizar alertas', 'error');
    });
}

/**
 * Toast para notificaciones rápidas
 */
const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true,
    didOpen: (toast) => {
        toast.addEventListener('mouseenter', Swal.stopTimer);
        toast.addEventListener('mouseleave', Swal.resumeTimer);
    }
});

function mostrarToast(mensaje, tipo = 'success') {
    Toast.fire({
        icon: tipo,
        title: mensaje
    });
}
