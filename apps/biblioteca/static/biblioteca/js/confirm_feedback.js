(function (window, document, $) {
    'use strict';

    if (!$ || !$.fn || !$.fn.modal) {
        return;
    }

    var modal = document.getElementById('bibliotecaGuardarModal');
    var feedbackModal = document.getElementById('bibliotecaFeedbackModal');
    var sectionInfoModal = document.getElementById('bibliotecaSectionInfoModal');

    if (!modal || !feedbackModal || !sectionInfoModal) {
        return;
    }

    var $modal = $(modal);
    var $feedbackModal = $(feedbackModal);
    var $sectionInfoModal = $(sectionInfoModal);

    var confirmar = modal.querySelector('[data-biblioteca-guardar-confirmar]');
    var cancelar = modal.querySelector('[data-biblioteca-guardar-cancelar]');
    var confirmarTexto = modal.querySelector('[data-biblioteca-guardar-confirmar-texto]');
    var confirmarIcono = confirmar ? confirmar.querySelector('.biblioteca-symbol') : null;

    var feedbackTitulo = feedbackModal.querySelector('[data-biblioteca-feedback-title]');
    var feedbackMensaje = feedbackModal.querySelector('[data-biblioteca-feedback-message]');
    var feedbackIcono = feedbackModal.querySelector('[data-biblioteca-feedback-icon]');

    var sectionInfoTitulo = sectionInfoModal.querySelector('[data-biblioteca-section-info-title]');
    var sectionInfoMensaje = sectionInfoModal.querySelector('[data-biblioteca-section-info-message]');
    var sectionInfoIcono = sectionInfoModal.querySelector('[data-biblioteca-section-info-icon]');
    var sectionInfoFields = sectionInfoModal.querySelector('[data-biblioteca-section-info-fields]');

    var accionPendiente = null;
    var procesando = false;

    function setProcesando(valor) {
        procesando = Boolean(valor);

        if (confirmar) {
            confirmar.disabled = procesando;
        }
        if (cancelar) {
            cancelar.disabled = procesando;
        }

        if (confirmarTexto) {
            confirmarTexto.textContent = procesando ? 'Guardando...' : 'Sí, guardar';
        }

        if (confirmarIcono) {
            confirmarIcono.textContent = procesando ? 'progress_activity' : 'save';
            confirmarIcono.classList.toggle('biblioteca-guardar-modal__loading', procesando);
        }

        modal.setAttribute('aria-busy', procesando ? 'true' : 'false');
    }

    function agregarMensajes(destino, valor) {
        if (!valor) {
            return;
        }

        if (Array.isArray(valor)) {
            valor.forEach(function (item) {
                agregarMensajes(destino, item);
            });
            return;
        }

        if (typeof valor === 'object') {
            if (typeof valor.message === 'string' && valor.message) {
                destino.push(valor.message);
                return;
            }

            Object.keys(valor).forEach(function (clave) {
                agregarMensajes(destino, valor[clave]);
            });
            return;
        }

        destino.push(String(valor));
    }

    function limpiarMensaje(texto) {
        return String(texto || '')
            .replace(/^\s*⚠\uFE0F?\s*/u, '')
            .trim();
    }

    function mensajesDeError(data) {
        var mensajes = [];

        if (!data) {
            return ['No se pudo guardar el registro.'];
        }

        if (typeof data === 'string') {
            agregarMensajes(mensajes, data);
        } else {
            if (typeof data.message === 'string' && data.message) {
                agregarMensajes(mensajes, data.message);
            }

            if (data.errors) {
                agregarMensajes(mensajes, data.errors);
            } else if (data.error && typeof data.error !== 'boolean') {
                agregarMensajes(mensajes, data.error);
            }
        }

        var unicos = [];
        var vistos = {};

        mensajes.forEach(function (mensaje) {
            var limpio = limpiarMensaje(mensaje);
            var clave;

            if (!limpio) {
                return;
            }

            clave = limpio.toLocaleLowerCase('es');
            if (!vistos[clave]) {
                vistos[clave] = true;
                unicos.push(limpio);
            }
        });

        var duplicadoAmigable = unicos.find(function (mensaje) {
            return /ya existe este registro para el mismo cue/i.test(mensaje);
        });

        if (duplicadoAmigable) {
            return [duplicadoAmigable];
        }

        return unicos.length ? unicos : ['Revisá los datos ingresados e intentá nuevamente.'];
    }

    function esDuplicado(mensajes) {
        return mensajes.some(function (mensaje) {
            return /ya existe este registro|registro.*ya existe|con este cueanexo.*existe/i.test(mensaje);
        });
    }

    function abrirFeedback(data) {
        var mensajes = mensajesDeError(data);
        var duplicado = esDuplicado(mensajes);

        feedbackModal.classList.toggle('biblioteca-feedback-modal--warning', duplicado);
        feedbackModal.classList.toggle('biblioteca-feedback-modal--error', !duplicado);

        if (feedbackTitulo) {
            feedbackTitulo.textContent = duplicado ? 'Registro duplicado' : 'No se pudo guardar';
        }

        if (feedbackIcono) {
            feedbackIcono.textContent = duplicado ? 'content_copy' : 'error';
        }

        if (feedbackMensaje) {
            feedbackMensaje.textContent = mensajes.join('\n');
        }

        $feedbackModal.modal({
            backdrop: true,
            keyboard: true,
            show: true
        });
    }

    function mostrarError(data) {
        if ($modal.hasClass('show')) {
            $modal.one('hidden.bs.modal.bibliotecaFeedback', function () {
                abrirFeedback(data);
            });
            $modal.modal('hide');
            return;
        }

        abrirFeedback(data);
    }

    function crearCampoInfo(etiqueta, icono) {
        var field = document.createElement('div');
        var iconWrap = document.createElement('span');
        var icon = document.createElement('span');
        var label = document.createElement('span');

        field.className = 'biblioteca-section-info-modal__field';
        iconWrap.className = 'biblioteca-section-info-modal__field-icon';
        iconWrap.setAttribute('aria-hidden', 'true');

        icon.className = 'biblioteca-symbol';
        icon.textContent = icono || 'label';

        label.className = 'biblioteca-section-info-modal__field-label';
        label.textContent = etiqueta;

        iconWrap.appendChild(icon);
        field.appendChild(iconWrap);
        field.appendChild(label);

        return field;
    }

    function abrirInfoSeccion(origen, mensajeAlternativo) {
        var titulo = 'Información';
        var mensaje = mensajeAlternativo || '';
        var iconoSeccion = 'info';
        var items = [];

        if (origen && origen.nodeType === 1) {
            titulo = origen.getAttribute('data-info-title') || titulo;
            mensaje = origen.getAttribute('data-info-text') || '';
            iconoSeccion = origen.getAttribute('data-info-section-icon') || iconoSeccion;

            for (var i = 1; i <= 6; i += 1) {
                var etiqueta = origen.getAttribute('data-info-item-' + i);
                if (!etiqueta) {
                    continue;
                }

                items.push({
                    etiqueta: etiqueta,
                    icono: origen.getAttribute('data-info-icon-' + i) || 'label'
                });
            }
        } else if (typeof origen === 'string' && origen) {
            titulo = origen;
        }

        if (sectionInfoTitulo) {
            sectionInfoTitulo.textContent = titulo;
        }

        if (sectionInfoMensaje) {
            sectionInfoMensaje.textContent = mensaje;
        }

        if (sectionInfoIcono) {
            sectionInfoIcono.textContent = iconoSeccion;
        }

        if (sectionInfoFields) {
            sectionInfoFields.replaceChildren();

            items.forEach(function (item) {
                sectionInfoFields.appendChild(crearCampoInfo(item.etiqueta, item.icono));
            });

            sectionInfoFields.hidden = items.length === 0;
        }

        $sectionInfoModal.modal({
            backdrop: true,
            keyboard: true,
            show: true
        });
    }

    function cerrarModal() {
        if (!procesando) {
            $modal.modal('hide');
        }
    }

    window.biblioteca_mostrar_error_guardado = mostrarError;
    window.biblioteca_mostrar_info_seccion = abrirInfoSeccion;

    document.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-biblioteca-section-info]');

        if (!trigger) {
            return;
        }

        abrirInfoSeccion(trigger);
    });

    window.biblioteca_confirmar_guardado = function (accion) {
        if (typeof accion !== 'function') {
            return;
        }

        accionPendiente = accion;
        setProcesando(false);

        $modal.modal({
            backdrop: 'static',
            keyboard: false,
            show: true
        });
    };

    window.biblioteca_submit_with_ajax = function (url, title, content, parameters, callback) {
        window.biblioteca_confirmar_guardado(function () {
            return $.ajax({
                url: url,
                type: 'POST',
                data: parameters,
                processData: false,
                contentType: false,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).done(function (response) {
                if (response && response.error) {
                    mostrarError(response);
                    return;
                }

                if (typeof callback === 'function') {
                    callback(response);
                }
            }).fail(function (xhr) {
                mostrarError(xhr.responseJSON || {
                    message: 'No se pudo guardar el registro.'
                });
            });
        });
    };

    if (cancelar) {
        cancelar.addEventListener('click', cerrarModal);
    }

    if (confirmar) {
        confirmar.addEventListener('click', function () {
            if (procesando || typeof accionPendiente !== 'function') {
                return;
            }

            setProcesando(true);

            var resultado;
            try {
                resultado = accionPendiente();
            } catch (error) {
                setProcesando(false);
                mostrarError({
                    message: error && error.message ? error.message : 'No se pudo guardar el registro.'
                });
                return;
            }

            if (resultado && typeof resultado.always === 'function') {
                resultado.always(function () {
                    if (!document.body.contains(modal)) {
                        return;
                    }

                    setProcesando(false);
                    $modal.modal('hide');
                });
                return;
            }

            if (resultado && typeof resultado.finally === 'function') {
                Promise.resolve(resultado).finally(function () {
                    if (!document.body.contains(modal)) {
                        return;
                    }

                    setProcesando(false);
                    $modal.modal('hide');
                });
                return;
            }

            setProcesando(false);
            $modal.modal('hide');
        });
    }

    $modal.on('hidden.bs.modal', function () {
        accionPendiente = null;
        setProcesando(false);
    });
})(window, document, window.jQuery);
