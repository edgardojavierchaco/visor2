(function () {
    'use strict';

    function vaciar(elemento) {
        while (elemento.firstChild) {
            elemento.removeChild(elemento.firstChild);
        }
    }

    function mostrarCarga(contenedor) {
        vaciar(contenedor);
        var estado = document.createElement('p');
        estado.className = 'biblioteca-informe__estado-carga';

        var icono = document.createElement('i');
        icono.className = 'fas fa-circle-notch fa-spin';
        icono.setAttribute('aria-hidden', 'true');

        estado.appendChild(icono);
        estado.appendChild(document.createTextNode(' Cargando registros…'));
        contenedor.appendChild(estado);
    }

    function mostrarError(contenedor, mensaje, reintentar) {
        vaciar(contenedor);
        var bloque = document.createElement('div');
        bloque.className = 'biblioteca-informe__error';

        var texto = document.createElement('p');
        texto.textContent = mensaje;
        bloque.appendChild(texto);

        var boton = document.createElement('button');
        boton.type = 'button';
        boton.className = 'btn btn-sm btn-outline-secondary';
        boton.textContent = 'Reintentar';
        boton.addEventListener('click', reintentar);
        bloque.appendChild(boton);
        contenedor.appendChild(bloque);
    }

    function mostrarVacio(contenedor) {
        vaciar(contenedor);
        var estado = document.createElement('p');
        estado.className = 'biblioteca-informe__estado-vacio';
        estado.textContent = 'No hay registros cargados en esta sección para el período.';
        contenedor.appendChild(estado);
    }

    var contadorDetalles = 0;

    function validarDetalles(datos) {
        if (datos.detalles === undefined) {
            return;
        }

        if (
            !Array.isArray(datos.detalles) ||
            datos.detalles.length !== datos.filas.length ||
            datos.detalles.some(function (items) {
                return !Array.isArray(items) || items.some(function (item) {
                    return !item ||
                        typeof item.etiqueta !== 'string' ||
                        typeof item.valor !== 'string' && typeof item.valor !== 'number';
                });
            })
        ) {
            throw new Error('La respuesta de datos adicionales no tiene el formato esperado.');
        }
    }

    function tieneDetalles(datos) {
        return Array.isArray(datos.detalles) && datos.detalles.some(function (items) {
            return items.length > 0;
        });
    }

    function crearFilaDetalle(items, columnasTotales, boton) {
        contadorDetalles += 1;
        var detalleId = 'informe-datos-adicionales-' + contadorDetalles;

        boton.setAttribute('aria-controls', detalleId);

        var filaDetalle = document.createElement('tr');
        filaDetalle.id = detalleId;
        filaDetalle.className = 'biblioteca-informe__fila-adicional';
        filaDetalle.hidden = true;

        var celdaDetalle = document.createElement('td');
        celdaDetalle.colSpan = columnasTotales;

        var bloque = document.createElement('div');
        bloque.className = 'biblioteca-informe__datos-adicionales';

        var responsive = document.createElement('div');
        responsive.className = 'table-responsive';

        var tablaDetalle = document.createElement('table');
        tablaDetalle.className = 'table table-sm biblioteca-informe__tabla biblioteca-informe__tabla-adicional';

        var caption = document.createElement('caption');
        caption.className = 'sr-only';
        caption.textContent = 'Datos adicionales del registro';
        tablaDetalle.appendChild(caption);

        var cabecera = document.createElement('thead');
        var filaCabecera = document.createElement('tr');
        var filaValores = document.createElement('tr');

        items.forEach(function (item, indice) {
            var etiqueta = document.createElement('th');
            etiqueta.scope = 'col';

            if (indice === 0) {
                var icono = document.createElement('span');
                icono.className = 'biblioteca-symbol biblioteca-informe__datos-adicionales-icono';
                icono.setAttribute('aria-hidden', 'true');
                icono.textContent = 'info';
                etiqueta.appendChild(icono);
            }

            etiqueta.appendChild(document.createTextNode(item.etiqueta));
            filaCabecera.appendChild(etiqueta);

            var valor = document.createElement('td');
            valor.textContent = String(item.valor);
            filaValores.appendChild(valor);
        });

        cabecera.appendChild(filaCabecera);
        tablaDetalle.appendChild(cabecera);

        var cuerpoDetalle = document.createElement('tbody');
        cuerpoDetalle.appendChild(filaValores);
        tablaDetalle.appendChild(cuerpoDetalle);

        responsive.appendChild(tablaDetalle);
        bloque.appendChild(responsive);
        celdaDetalle.appendChild(bloque);
        filaDetalle.appendChild(celdaDetalle);

        boton.addEventListener('click', function () {
            var abrir = boton.getAttribute('aria-expanded') !== 'true';
            boton.setAttribute('aria-expanded', String(abrir));
            filaDetalle.hidden = !abrir;

            var simbolo = boton.querySelector('.biblioteca-symbol');
            if (simbolo) {
                simbolo.textContent = abrir ? 'expand_less' : 'expand_more';
            }

            var textoBoton = boton.querySelector('[data-detalle-texto]');
            if (textoBoton) {
                textoBoton.textContent = abrir ? 'Ocultar datos' : 'Ver datos';
            }
        });

        return filaDetalle;
    }

    function mostrarTabla(contenedor, datos) {
        validarDetalles(datos);

        if (!datos.filas.length) {
            mostrarVacio(contenedor);
            return;
        }

        vaciar(contenedor);
        var responsive = document.createElement('div');
        responsive.className = 'table-responsive';
        var tabla = document.createElement('table');
        tabla.className = 'table table-sm biblioteca-informe__tabla';

        var caption = document.createElement('caption');
        caption.className = 'sr-only';
        caption.textContent = 'Registros de ' + datos.seccion;
        tabla.appendChild(caption);

        var mostrarDetalles = tieneDetalles(datos);
        var columnasTotales = datos.columnas.length + (mostrarDetalles ? 1 : 0);

        var cabecera = document.createElement('thead');
        var filaCabecera = document.createElement('tr');
        datos.columnas.forEach(function (columna) {
            var celda = document.createElement('th');
            celda.scope = 'col';
            celda.textContent = columna;
            filaCabecera.appendChild(celda);
        });
        if (mostrarDetalles) {
            var cabeceraDetalles = document.createElement('th');
            cabeceraDetalles.scope = 'col';
            cabeceraDetalles.textContent = 'Datos adicionales';
            filaCabecera.appendChild(cabeceraDetalles);
        }
        cabecera.appendChild(filaCabecera);
        tabla.appendChild(cabecera);

        var cuerpo = document.createElement('tbody');
        datos.filas.forEach(function (fila, indice) {
            var filaTabla = document.createElement('tr');
            fila.forEach(function (valor) {
                var celda = document.createElement('td');
                celda.textContent = String(valor);
                filaTabla.appendChild(celda);
            });

            var filaDetalle = null;
            if (mostrarDetalles) {
                var celdaAccion = document.createElement('td');
                var items = datos.detalles[indice];

                if (items.length) {
                    var boton = document.createElement('button');
                    boton.type = 'button';
                    boton.className = 'btn biblioteca-informe__detalle-toggle';
                    boton.setAttribute('aria-expanded', 'false');
                    boton.setAttribute('aria-label', 'Ver datos adicionales del registro');

                    var simbolo = document.createElement('span');
                    simbolo.className = 'biblioteca-symbol';
                    simbolo.setAttribute('aria-hidden', 'true');
                    simbolo.textContent = 'expand_more';
                    boton.appendChild(simbolo);

                    var textoBoton = document.createElement('span');
                    textoBoton.setAttribute('data-detalle-texto', '');
                    textoBoton.textContent = 'Ver datos';
                    boton.appendChild(textoBoton);

                    celdaAccion.appendChild(boton);
                    filaDetalle = crearFilaDetalle(items, columnasTotales, boton);
                } else {
                    celdaAccion.textContent = '—';
                }
                filaTabla.appendChild(celdaAccion);
            }

            cuerpo.appendChild(filaTabla);
            if (filaDetalle) {
                cuerpo.appendChild(filaDetalle);
            }
        });
        tabla.appendChild(cuerpo);
        responsive.appendChild(tabla);
        contenedor.appendChild(responsive);
    }

    function cargarDetalle(panel) {
        if (panel.dataset.cargado === 'true' || panel.dataset.cargando === 'true') {
            return;
        }

        var boton = document.querySelector('[data-target="#' + panel.id + '"]');
        var contenedor = panel.querySelector('[data-informe-detalle]');
        if (!boton || !contenedor) {
            return;
        }

        panel.dataset.cargando = 'true';
        mostrarCarga(contenedor);

        fetch(boton.dataset.detailUrl, {
            credentials: 'same-origin',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        })
            .then(function (respuesta) {
                return respuesta.json().catch(function () {
                    return {};
                }).then(function (datos) {
                    if (!respuesta.ok) {
                        throw new Error(datos.detail || 'No fue posible cargar esta sección.');
                    }
                    return datos;
                });
            })
            .then(function (datos) {
                mostrarTabla(contenedor, datos);
                panel.dataset.cargado = 'true';
            })
            .catch(function (error) {
                mostrarError(contenedor, error.message, function () {
                    cargarDetalle(panel);
                });
            })
            .then(function () {
                panel.dataset.cargando = 'false';
            });
    }

    document.querySelectorAll('[data-informe-panel]').forEach(function (panel) {
        window.jQuery(panel).on('show.bs.collapse', function () {
            cargarDetalle(panel);
        });
    });

    var modalFinalizar = document.getElementById('modalFinalizarInforme');
    if (modalFinalizar) {
        var formularioFinalizar = modalFinalizar.querySelector('[data-informe-finalizar-form]');
        var confirmarFinalizar = modalFinalizar.querySelector('[data-informe-finalizar-confirmar]');
        var cancelarFinalizar = modalFinalizar.querySelector('[data-informe-finalizar-cancelar]');
        var textoConfirmar = modalFinalizar.querySelector('[data-informe-finalizar-confirmar-texto]');
        var iconoConfirmar = modalFinalizar.querySelector('[data-informe-finalizar-confirmar-icono]');

        window.jQuery(modalFinalizar).on('shown.bs.modal', function () {
            if (cancelarFinalizar) {
                cancelarFinalizar.focus();
            }
        });

        window.jQuery(modalFinalizar).on('hidden.bs.modal', function () {
            if (formularioFinalizar) {
                formularioFinalizar.removeAttribute('aria-busy');
            }
            if (confirmarFinalizar) {
                confirmarFinalizar.disabled = false;
                confirmarFinalizar.classList.remove('biblioteca-submit-loading');
            }
            if (iconoConfirmar) {
                iconoConfirmar.textContent = 'picture_as_pdf';
                iconoConfirmar.classList.remove('biblioteca-submit-loading__icon');
            }
            if (textoConfirmar) {
                textoConfirmar.textContent = 'Finalizar y generar PDF';
            }
        });

        if (formularioFinalizar && confirmarFinalizar) {
            formularioFinalizar.addEventListener('submit', function () {
                formularioFinalizar.setAttribute('aria-busy', 'true');
                confirmarFinalizar.disabled = true;
                confirmarFinalizar.classList.add('biblioteca-submit-loading');

                if (iconoConfirmar) {
                    iconoConfirmar.textContent = 'progress_activity';
                    iconoConfirmar.classList.add('biblioteca-submit-loading__icon');
                }

                if (textoConfirmar) {
                    textoConfirmar.textContent = 'Generando PDF...';
                }
            });
        }
    }
}());
