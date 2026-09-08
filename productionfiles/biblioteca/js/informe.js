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

    function mostrarTabla(contenedor, datos) {
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

        var cabecera = document.createElement('thead');
        var filaCabecera = document.createElement('tr');
        datos.columnas.forEach(function (columna) {
            var celda = document.createElement('th');
            celda.scope = 'col';
            celda.textContent = columna;
            filaCabecera.appendChild(celda);
        });
        cabecera.appendChild(filaCabecera);
        tabla.appendChild(cabecera);

        var cuerpo = document.createElement('tbody');
        datos.filas.forEach(function (fila) {
            var filaTabla = document.createElement('tr');
            fila.forEach(function (valor) {
                var celda = document.createElement('td');
                celda.textContent = String(valor);
                filaTabla.appendChild(celda);
            });
            cuerpo.appendChild(filaTabla);
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
}());
