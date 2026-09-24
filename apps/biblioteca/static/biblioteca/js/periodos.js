(function () {
    'use strict';

    var PLACEHOLDER_SECCION = '__seccion__';

    function vaciar(elemento) {
        while (elemento.firstChild) {
            elemento.removeChild(elemento.firstChild);
        }
    }

    function crearSimbolo(nombre, claseAdicional) {
        var simbolo = document.createElement('span');
        simbolo.className = 'biblioteca-symbol' + (claseAdicional ? ' ' + claseAdicional : '');
        simbolo.setAttribute('aria-hidden', 'true');
        simbolo.textContent = nombre;
        return simbolo;
    }

    function mostrarCarga(contenedor, mensaje) {
        vaciar(contenedor);
        var estado = document.createElement('p');
        estado.className = 'biblioteca-informe__estado-carga';
        estado.setAttribute('role', 'status');

        var icono = document.createElement('i');
        icono.className = 'fas fa-circle-notch fa-spin';
        icono.setAttribute('aria-hidden', 'true');

        estado.appendChild(icono);
        estado.appendChild(document.createTextNode(' ' + mensaje));
        contenedor.appendChild(estado);
    }

    function mostrarError(contenedor, mensaje, reintentar) {
        vaciar(contenedor);
        var bloque = document.createElement('div');
        bloque.className = 'biblioteca-informe__error';
        bloque.setAttribute('role', 'alert');

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

    function leerRespuesta(respuesta, mensajePredeterminado) {
        return respuesta.json().catch(function () {
            return {};
        }).then(function (datos) {
            if (!respuesta.ok) {
                var detalle = typeof datos.detail === 'string' ? datos.detail : mensajePredeterminado;
                throw new Error(detalle);
            }
            return datos;
        });
    }

    function cerrarSeccion(boton) {
        boton.setAttribute('aria-expanded', 'false');
        var panel = document.getElementById(boton.getAttribute('aria-controls'));
        if (panel) {
            panel.hidden = true;
        }
    }

    function cerrarSecciones(registro) {
        registro.querySelectorAll('[data-historico-seccion-accion][aria-expanded="true"]').forEach(function (boton) {
            cerrarSeccion(boton);
        });
    }

    function actualizarRelevamiento(registro, abierto) {
        var boton = registro.querySelector('[data-historico-accion]');
        var panel = registro.querySelector('[data-historico-panel]');
        var texto = registro.querySelector('[data-historico-accion-texto]');
        var icono = boton ? boton.querySelector('.biblioteca-symbol') : null;
        if (!boton || !panel || !texto || !icono) {
            return;
        }

        boton.setAttribute('aria-expanded', String(abierto));
        panel.hidden = !abierto;
        registro.classList.toggle('biblioteca-periodos__historico--abierto', abierto);
        texto.textContent = abierto ? 'Ocultar relevamiento' : 'Ver relevamiento';
        icono.textContent = abierto ? 'expand_less' : 'visibility';

        if (!abierto) {
            cerrarSecciones(registro);
        }
    }

    function cerrarOtrosRelevamientos(actual) {
        document.querySelectorAll('[data-periodo-historico]').forEach(function (registro) {
            if (registro !== actual) {
                actualizarRelevamiento(registro, false);
            }
        });
    }

    function textoCantidad(cantidad) {
        if (cantidad === 0) {
            return 'Sin registros';
        }
        return cantidad + (cantidad === 1 ? ' registro' : ' registros');
    }

    function mesVisible(mes) {
        var texto = String(mes).toLocaleLowerCase('es-AR');
        return texto.charAt(0).toLocaleUpperCase('es-AR') + texto.slice(1);
    }

    function validarResumen(datos) {
        var periodoId = Number(datos && datos.periodo && datos.periodo.id);
        var anio = Number(datos && datos.periodo && datos.periodo.anio);
        if (
            !datos ||
            !datos.periodo ||
            !Number.isInteger(periodoId) ||
            periodoId < 1 ||
            typeof datos.periodo.cueanexo !== 'string' ||
            typeof datos.periodo.mes !== 'string' ||
            !Number.isInteger(anio) ||
            datos.periodo.estado !== 'ENVIADO' ||
            !Array.isArray(datos.secciones)
        ) {
            throw new Error('La respuesta del relevamiento no tiene el formato esperado.');
        }

        datos.periodo.id = periodoId;
        datos.periodo.anio = anio;

        datos.secciones.forEach(function (seccion) {
            var cantidad = Number(seccion && seccion.cantidad);
            if (
                !seccion ||
                typeof seccion.clave !== 'string' ||
                !/^[a-z0-9-]+$/.test(seccion.clave) ||
                typeof seccion.nombre !== 'string' ||
                typeof seccion.material_icon !== 'string' ||
                !Number.isInteger(cantidad) ||
                cantidad < 0
            ) {
                throw new Error('La respuesta del relevamiento no tiene el formato esperado.');
            }
            seccion.cantidad = cantidad;
        });
    }

    function validarDetalle(datos) {
        if (
            !datos ||
            typeof datos.seccion !== 'string' ||
            !Array.isArray(datos.columnas) ||
            !Array.isArray(datos.filas) ||
            datos.columnas.some(function (columna) { return typeof columna !== 'string'; }) ||
            datos.filas.some(function (fila) { return !Array.isArray(fila); })
        ) {
            throw new Error('La respuesta de la sección no tiene el formato esperado.');
        }

        if (datos.detalles !== undefined) {
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

        if (!datos.totales || typeof datos.totales.tipo !== 'string') {
            throw new Error('La respuesta de la sección no tiene el formato esperado.');
        }

        if (datos.totales.tipo === 'sumas') {
            if (
                !Array.isArray(datos.totales.valores) ||
                datos.totales.valores.length !== datos.columnas.length ||
                !datos.totales.valores.some(function (valor) {
                    return valor !== null;
                }) ||
                datos.totales.valores.some(function (valor) {
                    return valor !== null && (!Number.isInteger(valor) || valor < 0);
                })
            ) {
                throw new Error('La respuesta de la sección no tiene el formato esperado.');
            }
        } else if (
            datos.totales.tipo !== 'conteo' ||
            typeof datos.totales.etiqueta !== 'string' ||
            !datos.totales.etiqueta ||
            !Number.isInteger(datos.totales.valor) ||
            datos.totales.valor < 0
        ) {
            throw new Error('La respuesta de la sección no tiene el formato esperado.');
        }
    }

    function mostrarVacio(contenedor) {
        vaciar(contenedor);
        var estado = document.createElement('p');
        estado.className = 'biblioteca-informe__estado-vacio';
        estado.textContent = 'No hay registros para consultar en esta sección.';
        contenedor.appendChild(estado);
    }

    var contadorDetalles = 0;

    function tieneDetalles(datos) {
        return Array.isArray(datos.detalles) && datos.detalles.some(function (items) {
            return items.length > 0;
        });
    }

    function crearFilaDetalle(items, columnasTotales, boton) {
        contadorDetalles += 1;
        var detalleId = 'periodo-datos-adicionales-' + contadorDetalles;

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
                etiqueta.appendChild(
                    crearSimbolo('badge', 'biblioteca-informe__datos-adicionales-icono')
                );
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

    function agregarCeldasValores(fila, valores, indiceInicial) {
        valores.slice(indiceInicial).forEach(function (valor) {
            var celda = document.createElement('td');
            if (valor !== null) {
                celda.textContent = String(valor);
            }
            fila.appendChild(celda);
        });
    }

    function agregarPie(tabla, datos) {
        var pie = document.createElement('tfoot');

        if (datos.totales.tipo === 'conteo') {
            var filaConteo = document.createElement('tr');
            var celdaConteo = document.createElement('th');
            celdaConteo.scope = 'row';
            celdaConteo.colSpan = datos.columnas.length + (tieneDetalles(datos) ? 1 : 0);
            celdaConteo.textContent = datos.totales.etiqueta + ': ' + datos.totales.valor;
            filaConteo.appendChild(celdaConteo);
            pie.appendChild(filaConteo);
        } else {
            var valores = datos.totales.valores;
            var primerIndiceTotal = valores.findIndex(function (valor) {
                return valor !== null;
            });

            if (primerIndiceTotal === 0) {
                var filaEtiqueta = document.createElement('tr');
                var celdaEtiqueta = document.createElement('th');
                celdaEtiqueta.scope = 'row';
                celdaEtiqueta.colSpan = valores.length;
                celdaEtiqueta.textContent = 'TOTALES';
                filaEtiqueta.appendChild(celdaEtiqueta);
                pie.appendChild(filaEtiqueta);

                var filaValores = document.createElement('tr');
                agregarCeldasValores(filaValores, valores, 0);
                pie.appendChild(filaValores);
            } else {
                var filaPie = document.createElement('tr');
                var celdaEtiqueta = document.createElement('th');
                celdaEtiqueta.scope = 'row';
                celdaEtiqueta.colSpan = primerIndiceTotal;
                celdaEtiqueta.textContent = 'TOTALES';
                filaPie.appendChild(celdaEtiqueta);
                agregarCeldasValores(filaPie, valores, primerIndiceTotal);
                pie.appendChild(filaPie);
            }
        }

        tabla.appendChild(pie);
    }

    function mostrarTabla(contenedor, datos) {
        validarDetalle(datos);
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
        caption.textContent = 'Registros históricos de ' + datos.seccion;
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
                    boton.appendChild(crearSimbolo('expand_more'));

                    celdaControl.appendChild(boton);
                    filaDetalle = crearFilaDetalle(items, columnasTotales, boton);
                }

                filaTabla.appendChild(celdaControl);
            }

            fila.forEach(function (valor, indiceValor) {
                var celda = document.createElement('td');
                var textoValor = valor === null || valor === undefined ? '' : String(valor);

                if (esPersonal && indiceValor === 0) {
                    var persona = document.createElement('span');
                    persona.className = 'biblioteca-informe__persona';

                    var iconoPersona = document.createElement('span');
                    iconoPersona.className = 'biblioteca-informe__persona-icono';
                    iconoPersona.setAttribute('aria-hidden', 'true');
                    iconoPersona.appendChild(
                        crearSimbolo('person', 'biblioteca-symbol--filled')
                    );

                    persona.appendChild(iconoPersona);
                    persona.appendChild(document.createTextNode(textoValor));
                    celda.appendChild(persona);
                } else {
                    celda.textContent = textoValor;
                }

                filaTabla.appendChild(celda);
            });

            cuerpo.appendChild(filaTabla);
            if (filaDetalle) {
                cuerpo.appendChild(filaDetalle);
            }
        });
        tabla.appendChild(cuerpo);
        agregarPie(tabla, datos);
        responsive.appendChild(tabla);
        contenedor.appendChild(responsive);
    }

    function cargarDetalle(panel, url) {
        if (panel.dataset.cargado === 'true' || panel.dataset.cargando === 'true') {
            return;
        }

        var contenedor = panel.querySelector('[data-historico-detalle]');
        if (!contenedor) {
            return;
        }

        panel.dataset.cargando = 'true';
        mostrarCarga(contenedor, 'Cargando registros…');

        fetch(url, {
            credentials: 'same-origin',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        })
            .then(function (respuesta) {
                return leerRespuesta(respuesta, 'No fue posible cargar esta sección.');
            })
            .then(function (datos) {
                mostrarTabla(contenedor, datos);
                panel.dataset.cargado = 'true';
            })
            .catch(function (error) {
                mostrarError(contenedor, error.message, function () {
                    cargarDetalle(panel, url);
                });
            })
            .then(function () {
                panel.dataset.cargando = 'false';
            });
    }

    function crearSeccion(registro, seccion, indice, periodoId) {
        var articulo = document.createElement('article');
        articulo.className = 'biblioteca-informe__seccion';
        var encabezado = document.createElement('div');
        encabezado.className = 'biblioteca-informe__seccion-encabezado';
        var titulo = document.createElement('h3');
        var boton = document.createElement('button');
        boton.type = 'button';
        boton.className = 'biblioteca-informe__desplegar biblioteca-periodos__seccion-boton';

        var numero = document.createElement('span');
        numero.className = 'biblioteca-seccion__numero';
        numero.textContent = ('0' + (indice + 1)).slice(-2);
        boton.appendChild(numero);

        var marcoIcono = document.createElement('span');
        marcoIcono.className = 'biblioteca-seccion__icono';
        marcoIcono.appendChild(crearSimbolo(seccion.material_icon));
        boton.appendChild(marcoIcono);

        var contenido = document.createElement('span');
        contenido.className = 'biblioteca-seccion__contenido';
        var nombre = document.createElement('strong');
        nombre.textContent = seccion.nombre;
        contenido.appendChild(nombre);
        var cantidad = document.createElement('span');
        cantidad.className = 'biblioteca-seccion__cantidad';
        cantidad.textContent = textoCantidad(seccion.cantidad);
        contenido.appendChild(cantidad);
        boton.appendChild(contenido);

        if (seccion.cantidad === 0) {
            articulo.classList.add('biblioteca-periodos__seccion--vacia');
            boton.disabled = true;
            boton.setAttribute('aria-disabled', 'true');
        } else {
            var botonId = 'periodo-' + periodoId + '-seccion-' + (indice + 1) + '-accion';
            var panelId = 'periodo-' + periodoId + '-seccion-' + (indice + 1) + '-panel';
            boton.id = botonId;
            boton.setAttribute('aria-expanded', 'false');
            boton.setAttribute('aria-controls', panelId);
            boton.setAttribute('data-historico-seccion-accion', '');
            boton.appendChild(crearSimbolo('expand_more', 'biblioteca-informe__chevron'));

            var panel = document.createElement('div');
            panel.id = panelId;
            panel.className = 'biblioteca-periodos__seccion-panel';
            panel.setAttribute('role', 'region');
            panel.setAttribute('aria-labelledby', botonId);
            panel.hidden = true;

            var detalle = document.createElement('div');
            detalle.className = 'biblioteca-informe__detalle';
            detalle.setAttribute('data-historico-detalle', '');
            detalle.setAttribute('aria-live', 'polite');
            panel.appendChild(detalle);

            var plantilla = registro.dataset.detailUrlTemplate;
            if (!plantilla || plantilla.indexOf(PLACEHOLDER_SECCION) === -1) {
                throw new Error('No fue posible preparar el acceso a esta sección.');
            }
            var url = plantilla.replace(PLACEHOLDER_SECCION, encodeURIComponent(seccion.clave));
            boton.addEventListener('click', function () {
                var abrir = boton.getAttribute('aria-expanded') !== 'true';
                registro.querySelectorAll('[data-historico-seccion-accion][aria-expanded="true"]').forEach(function (otroBoton) {
                    if (otroBoton !== boton) {
                        cerrarSeccion(otroBoton);
                    }
                });
                boton.setAttribute('aria-expanded', String(abrir));
                panel.hidden = !abrir;
                if (abrir) {
                    cargarDetalle(panel, url);
                }
            });

            titulo.appendChild(boton);
            encabezado.appendChild(titulo);
            articulo.appendChild(encabezado);
            articulo.appendChild(panel);
            return articulo;
        }

        titulo.appendChild(boton);
        encabezado.appendChild(titulo);
        articulo.appendChild(encabezado);
        return articulo;
    }

    function renderizarResumen(registro, contenedor, datos) {
        validarResumen(datos);
        vaciar(contenedor);

        var encabezado = document.createElement('div');
        encabezado.className = 'biblioteca-periodos__relevamiento-encabezado';
        var identidad = document.createElement('div');
        var titulo = document.createElement('h4');
        titulo.textContent = 'Relevamiento enviado · ' + mesVisible(datos.periodo.mes) + ' ' + datos.periodo.anio;
        identidad.appendChild(titulo);
        var cueanexo = document.createElement('p');
        cueanexo.textContent = 'CUE-Anexo ' + datos.periodo.cueanexo;
        identidad.appendChild(cueanexo);
        encabezado.appendChild(identidad);

        var soloLectura = document.createElement('span');
        soloLectura.className = 'biblioteca-estado biblioteca-periodos__solo-lectura';
        soloLectura.appendChild(crearSimbolo('lock'));
        soloLectura.appendChild(document.createTextNode(' SOLO LECTURA'));
        encabezado.appendChild(soloLectura);
        contenedor.appendChild(encabezado);

        var secciones = document.createElement('div');
        secciones.className = 'biblioteca-informe__acordeon biblioteca-periodos__secciones';
        secciones.setAttribute('data-historico-secciones', '');
        datos.secciones.forEach(function (seccion, indice) {
            secciones.appendChild(crearSeccion(registro, seccion, indice, datos.periodo.id));
        });
        contenedor.appendChild(secciones);
    }

    function cargarResumen(registro) {
        if (registro.dataset.cargado === 'true' || registro.dataset.cargando === 'true') {
            return;
        }

        var contenedor = registro.querySelector('[data-historico-contenido]');
        if (!contenedor) {
            return;
        }

        registro.dataset.cargando = 'true';
        mostrarCarga(contenedor, 'Cargando relevamiento…');

        fetch(registro.dataset.summaryUrl, {
            credentials: 'same-origin',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        })
            .then(function (respuesta) {
                return leerRespuesta(respuesta, 'No fue posible cargar el relevamiento.');
            })
            .then(function (datos) {
                renderizarResumen(registro, contenedor, datos);
                registro.dataset.cargado = 'true';
            })
            .catch(function (error) {
                mostrarError(contenedor, error.message, function () {
                    cargarResumen(registro);
                });
            })
            .then(function () {
                registro.dataset.cargando = 'false';
            });
    }

    document.querySelectorAll('[data-periodo-historico]').forEach(function (registro) {
        var boton = registro.querySelector('[data-historico-accion]');
        if (!boton) {
            return;
        }

        boton.addEventListener('click', function () {
            var abrir = boton.getAttribute('aria-expanded') !== 'true';
            if (abrir) {
                cerrarOtrosRelevamientos(registro);
            }
            actualizarRelevamiento(registro, abrir);
            if (abrir) {
                cargarResumen(registro);
            }
        });
    });

    var modalEliminar = document.getElementById('modalEliminarPeriodo');
    if (modalEliminar) {
        var formularioEliminar = modalEliminar.querySelector('[data-periodo-eliminar-form]');
        var confirmarEliminar = modalEliminar.querySelector('[data-periodo-eliminar-confirmar]');
        var cancelarEliminar = modalEliminar.querySelector('[data-periodo-eliminar-cancelar]');

        $(modalEliminar).on('show.bs.modal', function (evento) {
            var accion = evento.relatedTarget;
            if (!accion || !formularioEliminar) {
                return;
            }

            formularioEliminar.action = accion.dataset.deleteUrl;
            modalEliminar.querySelector('[data-periodo-eliminar-mes]').textContent = accion.dataset.periodoMes;
            modalEliminar.querySelector('[data-periodo-eliminar-anio]').textContent = accion.dataset.periodoAnio;
            modalEliminar.querySelector('[data-periodo-eliminar-cue]').textContent = accion.dataset.periodoCue;
        });

        $(modalEliminar).on('shown.bs.modal', function () {
            if (cancelarEliminar) {
                cancelarEliminar.focus();
            }
        });

        $(modalEliminar).on('hidden.bs.modal', function () {
            formularioEliminar.removeAttribute('aria-busy');
            confirmarEliminar.disabled = false;
        });

        formularioEliminar.addEventListener('submit', function () {
            formularioEliminar.setAttribute('aria-busy', 'true');
            confirmarEliminar.disabled = true;
        });
    }
}());
