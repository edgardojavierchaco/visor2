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
                icono.textContent = 'badge';
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
            boton.setAttribute(
                'aria-label',
                abrir ? 'Contraer datos del registro' : 'Expandir datos del registro'
            );
            filaDetalle.hidden = !abrir;

            var simbolo = boton.querySelector('.biblioteca-symbol');
            if (simbolo) {
                simbolo.textContent = abrir ? 'expand_less' : 'expand_more';
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
        var esPersonal = datos.formato === 'actual' || datos.formato === 'historico';
        var columnasTotales = datos.columnas.length + (mostrarDetalles ? 1 : 0);

        if (esPersonal) {
            tabla.classList.add('biblioteca-informe__tabla--personal');
        }

        var cabecera = document.createElement('thead');
        var filaCabecera = document.createElement('tr');

        if (mostrarDetalles) {
            var cabeceraControl = document.createElement('th');
            cabeceraControl.scope = 'col';
            cabeceraControl.className = 'biblioteca-informe__detalle-control';
            cabeceraControl.setAttribute('aria-label', 'Expandir registro');
            filaCabecera.appendChild(cabeceraControl);
        }

        datos.columnas.forEach(function (columna) {
            var celda = document.createElement('th');
            celda.scope = 'col';
            celda.textContent = columna;
            filaCabecera.appendChild(celda);
        });

        cabecera.appendChild(filaCabecera);
        tabla.appendChild(cabecera);

        var cuerpo = document.createElement('tbody');
        datos.filas.forEach(function (fila, indice) {
            var filaTabla = document.createElement('tr');
            var filaDetalle = null;

            if (mostrarDetalles) {
                var celdaControl = document.createElement('td');
                celdaControl.className = 'biblioteca-informe__detalle-control';
                var items = datos.detalles[indice];

                if (items.length) {
                    var boton = document.createElement('button');
                    boton.type = 'button';
                    boton.className = 'btn biblioteca-informe__detalle-toggle';
                    boton.setAttribute('aria-expanded', 'false');
                    boton.setAttribute('aria-label', 'Expandir datos del registro');

                    var simbolo = document.createElement('span');
                    simbolo.className = 'biblioteca-symbol';
                    simbolo.setAttribute('aria-hidden', 'true');
                    simbolo.textContent = 'expand_more';
                    boton.appendChild(simbolo);

                    celdaControl.appendChild(boton);
                    filaDetalle = crearFilaDetalle(items, columnasTotales, boton);
                }

                filaTabla.appendChild(celdaControl);
            }

            fila.forEach(function (valor, indiceValor) {
                var celda = document.createElement('td');

                if (esPersonal && indiceValor === 0) {
                    var persona = document.createElement('span');
                    persona.className = 'biblioteca-informe__persona';

                    var iconoPersona = document.createElement('span');
                    iconoPersona.className = 'biblioteca-informe__persona-icono';
                    iconoPersona.setAttribute('aria-hidden', 'true');

                    var simboloPersona = document.createElement('span');
                    simboloPersona.className = 'biblioteca-symbol biblioteca-symbol--filled';
                    simboloPersona.setAttribute('aria-hidden', 'true');
                    simboloPersona.textContent = 'person';

                    iconoPersona.appendChild(simboloPersona);
                    persona.appendChild(iconoPersona);
                    persona.appendChild(document.createTextNode(String(valor)));
                    celda.appendChild(persona);
                } else {
                    celda.textContent = String(valor);
                }

                filaTabla.appendChild(celda);
            });

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
        var cerrarFinalizar = modalFinalizar.querySelector('.biblioteca-informe__modal-cerrar');
        var textoConfirmar = modalFinalizar.querySelector('[data-informe-finalizar-confirmar-texto]');
        var iconoConfirmar = modalFinalizar.querySelector('[data-informe-finalizar-confirmar-icono]');
        var finalizandoInforme = false;

        function setEstadoFinalizacion(procesando) {
            finalizandoInforme = procesando;

            if (formularioFinalizar) {
                if (procesando) {
                    formularioFinalizar.setAttribute('aria-busy', 'true');
                } else {
                    formularioFinalizar.removeAttribute('aria-busy');
                }
            }

            if (confirmarFinalizar) {
                confirmarFinalizar.disabled = procesando;
                confirmarFinalizar.classList.toggle('biblioteca-submit-loading', procesando);
            }

            if (cancelarFinalizar) {
                cancelarFinalizar.disabled = procesando;
            }

            if (cerrarFinalizar) {
                cerrarFinalizar.disabled = procesando;
            }

            if (iconoConfirmar) {
                iconoConfirmar.textContent = procesando ? 'progress_activity' : 'picture_as_pdf';
                iconoConfirmar.classList.toggle('biblioteca-submit-loading__icon', procesando);
                iconoConfirmar.classList.toggle('biblioteca-guardar-modal__loading', procesando);
            }

            if (textoConfirmar) {
                textoConfirmar.textContent = procesando
                    ? 'Generando PDF...'
                    : 'Finalizar y generar PDF';
            }
        }

        function obtenerNombrePdf(contentDisposition) {
            var coincidencia = /filename="?([^";]+)"?/i.exec(contentDisposition || '');
            return coincidencia && coincidencia[1]
                ? coincidencia[1]
                : 'informe_biblioteca.pdf';
        }

        function mostrarErrorFinalizacion(mensaje) {
            if (window.Swal && typeof window.Swal.fire === 'function') {
                window.Swal.fire({
                    icon: 'error',
                    title: 'No se pudo finalizar el informe',
                    text: mensaje
                });
                return;
            }

            window.alert(mensaje);
        }

        function lanzarErrorRespuesta(response) {
            return response.text().then(function (texto) {
                var mensaje = texto
                    .replace(/<[^>]*>/g, ' ')
                    .replace(/\s+/g, ' ')
                    .trim();

                if (!mensaje || mensaje.length > 300) {
                    mensaje = 'El servidor no pudo finalizar el informe.';
                }

                throw new Error(mensaje);
            });
        }

        window.jQuery(modalFinalizar).on('shown.bs.modal', function () {
            if (cancelarFinalizar && !finalizandoInforme) {
                cancelarFinalizar.focus();
            }
        });

        window.jQuery(modalFinalizar).on('hide.bs.modal', function (event) {
            if (finalizandoInforme) {
                event.preventDefault();
            }
        });

        window.jQuery(modalFinalizar).on('hidden.bs.modal', function () {
            if (!finalizandoInforme) {
                setEstadoFinalizacion(false);
            }
        });

        if (formularioFinalizar && confirmarFinalizar) {
            formularioFinalizar.addEventListener('submit', function (event) {
                event.preventDefault();

                if (finalizandoInforme) {
                    return;
                }

                setEstadoFinalizacion(true);

                fetch(formularioFinalizar.action, {
                    method: 'POST',
                    body: new FormData(formularioFinalizar),
                    credentials: 'same-origin',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                    .then(function (response) {
                        var contentType = (response.headers.get('Content-Type') || '').toLowerCase();

                        if (!response.ok) {
                            return lanzarErrorRespuesta(response);
                        }

                        if (contentType.indexOf('application/pdf') === -1) {
                            return lanzarErrorRespuesta(response);
                        }

                        var nombrePdf = obtenerNombrePdf(
                            response.headers.get('Content-Disposition')
                        );

                        return response.blob().then(function (blob) {
                            if (!blob || blob.size === 0) {
                                throw new Error('El servidor devolvió un PDF vacío.');
                            }

                            return {
                                blob: blob,
                                nombre: nombrePdf
                            };
                        });
                    })
                    .then(function (resultado) {
                        var urlPdf = window.URL.createObjectURL(resultado.blob);
                        var enlace = document.createElement('a');
                        var periodosUrl = formularioFinalizar.getAttribute('data-periodos-url');

                        enlace.href = urlPdf;
                        enlace.download = resultado.nombre;
                        enlace.style.display = 'none';
                        document.body.appendChild(enlace);
                        enlace.click();
                        document.body.removeChild(enlace);

                        window.setTimeout(function () {
                            window.URL.revokeObjectURL(urlPdf);
                            window.location.assign(periodosUrl || window.location.href);
                        }, 250);
                    })
                    .catch(function (error) {
                        setEstadoFinalizacion(false);
                        mostrarErrorFinalizacion(
                            error && error.message
                                ? error.message
                                : 'No se pudo finalizar el informe.'
                        );
                    });
            });
        }
    }
}());
