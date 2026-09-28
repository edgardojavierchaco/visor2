(function ($) {
    'use strict';

    function agregarPeriodo(url) {
        var periodoId = window.bibliotecaPeriodoActivoId;

        if (!periodoId || !url) {
            return url;
        }

        var destino = new URL(url, window.location.href);
        if (destino.origin !== window.location.origin) {
            return url;
        }

        destino.searchParams.set('periodo', periodoId);
        return destino.pathname + destino.search + destino.hash;
    }

    $.ajaxPrefilter(function (options) {
        if (options.url === window.location.pathname) {
            options.url = agregarPeriodo(options.url);
        }
    });

    function actualizarEnlacesPeriodo(table) {
        $(table).find('a[href]').each(function () {
            this.href = agregarPeriodo(this.href);
        });
    }

    var menuAccionesEstado = {
        trigger: null,
        celda: null
    };

    function obtenerMenuAcciones() {
        return document.querySelector('[data-biblioteca-action-menu]');
    }

    function cerrarMenuAcciones(devolverFoco) {
        var menu = obtenerMenuAcciones();
        var trigger = menuAccionesEstado.trigger;

        if (trigger) {
            trigger.setAttribute('aria-expanded', 'false');
        }

        menuAccionesEstado.trigger = null;
        menuAccionesEstado.celda = null;

        if (menu) {
            menu.hidden = true;
            menu.style.left = '';
            menu.style.top = '';
        }

        if (devolverFoco && trigger && document.contains(trigger)) {
            trigger.focus();
        }
    }

    function posicionarMenuAcciones(trigger, menu) {
        var rect = trigger.getBoundingClientRect();
        var separacion = 6;
        var margen = 8;
        var ancho = menu.offsetWidth || 166;
        var alto = menu.offsetHeight || 0;
        var left = rect.right - ancho;
        var top = rect.bottom + separacion;

        if (left < margen) {
            left = margen;
        }

        if (left + ancho > window.innerWidth - margen) {
            left = Math.max(margen, window.innerWidth - ancho - margen);
        }

        if (top + alto > window.innerHeight - margen) {
            top = rect.top - alto - separacion;
        }

        menu.style.left = left + 'px';
        menu.style.top = Math.max(margen, top) + 'px';
    }

    function abrirMenuAcciones(trigger, enfocarPrimerItem) {
        var menu = obtenerMenuAcciones();
        var celda = trigger.closest('td');

        if (!menu || !celda) {
            return;
        }

        var editar = celda.querySelector('[data-action-type="edit"]');
        var eliminar = celda.querySelector('[data-action-type="delete"]');
        var detalles = celda.querySelector('[data-biblioteca-action-type="details"]');
        var itemEditar = menu.querySelector('[data-biblioteca-menu-action="edit"]');
        var itemEliminar = menu.querySelector('[data-biblioteca-menu-action="delete"]');
        var itemDetalles = menu.querySelector('[data-biblioteca-menu-action="details"]');
        var divisorPrincipal = menu.querySelector('[data-biblioteca-menu-divider="primary"]');
        var divisorDetalles = menu.querySelector('[data-biblioteca-menu-divider="details"]');

        itemEditar.hidden = !editar;
        itemEliminar.hidden = !eliminar;
        itemDetalles.hidden = !detalles;
        divisorPrincipal.hidden = !(editar && eliminar);
        divisorDetalles.hidden = !(detalles && (editar || eliminar));

        if (detalles) {
            var expandido = detalles.getAttribute('aria-expanded') === 'true';
            var etiquetaDetalles = menu.querySelector('[data-biblioteca-menu-details-label]');
            var iconoDetalles = menu.querySelector('[data-biblioteca-menu-details-icon]');

            etiquetaDetalles.textContent = expandido ? 'Ocultar detalles' : 'Ver detalles';
            iconoDetalles.textContent = expandido ? 'expand_less' : 'expand_more';
        }

        if (!editar && !eliminar && !detalles) {
            cerrarMenuAcciones(false);
            return;
        }

        if (menuAccionesEstado.trigger && menuAccionesEstado.trigger !== trigger) {
            menuAccionesEstado.trigger.setAttribute('aria-expanded', 'false');
        }

        menuAccionesEstado.trigger = trigger;
        menuAccionesEstado.celda = celda;
        trigger.setAttribute('aria-expanded', 'true');
        menu.hidden = false;
        posicionarMenuAcciones(trigger, menu);

        if (enfocarPrimerItem) {
            var primerItem = menu.querySelector('[data-biblioteca-menu-action]:not([hidden])');
            if (primerItem) {
                primerItem.focus();
            }
        }
    }

    function prepararColumnaAccionesResponsive(table) {
        if (!table || table.getAttribute('data-actions-column') !== 'last' || !table.tHead) {
            return;
        }

        var encabezados = table.tHead.querySelectorAll('th');

        if (!encabezados.length) {
            return;
        }

        encabezados[encabezados.length - 1].classList.add('all');
    }

    function normalizarAcciones(table) {
        cerrarMenuAcciones(false);

        var $acciones = $(table).find(
            'tbody .btn-warning, ' +
            'tbody .btn-danger, ' +
            'tbody .biblioteca-personal-list__icon-btn, ' +
            'tbody .biblioteca-crud__action-button'
        );

        $acciones.each(function () {
            var $accion = $(this);
            var esEliminar = (
                $accion.hasClass('btn-danger') ||
                $accion.hasClass('biblioteca-personal-list__icon-btn--danger') ||
                $accion.attr('data-action-type') === 'delete'
            );
            var etiqueta = esEliminar ? 'Eliminar registro' : 'Editar registro';
            var icono = esEliminar ? 'delete_forever' : 'edit_square';
            var tipo = esEliminar ? 'delete' : 'edit';

            if ($.fn.tooltip && $accion.data('bs.tooltip')) {
                $accion.tooltip('dispose');
            }

            $accion
                .removeClass('biblioteca-personal-list__icon-btn biblioteca-personal-list__icon-btn--danger')
                .addClass('biblioteca-crud__action-button biblioteca-crud__source-action')
                .toggleClass('biblioteca-crud__action-button--danger', esEliminar)
                .attr({
                    'aria-label': etiqueta,
                    'aria-hidden': 'true',
                    'data-action-type': tipo,
                    'tabindex': '-1',
                    'title': etiqueta
                });

            var simbolo = this.querySelector('.biblioteca-crud__action-symbol');

            if (!simbolo) {
                simbolo = this.querySelector('.biblioteca-symbol');
            }

            if (!simbolo) {
                simbolo = document.createElement('span');
                simbolo.className = 'biblioteca-symbol';
                simbolo.setAttribute('aria-hidden', 'true');
                this.insertBefore(simbolo, this.firstChild);
            }

            simbolo.classList.add('biblioteca-crud__action-symbol');
            simbolo.textContent = icono;
        });

        $(table).find('tbody tr').each(function () {
            var celda = this.cells && this.cells.length ? this.cells[this.cells.length - 1] : null;

            if (!celda) {
                return;
            }

            var $celda = $(celda);
            var $editar = $celda.find('[data-action-type="edit"]').first();
            var $eliminar = $celda.find('[data-action-type="delete"]').first();
            var $detalles = $celda.find('.biblioteca-personal-list__details-toggle').first();

            if (!$editar.length && !$eliminar.length && !$detalles.length) {
                return;
            }

            if ($detalles.length) {
                $detalles
                    .addClass('biblioteca-crud__source-action')
                    .attr({
                        'aria-hidden': 'true',
                        'data-biblioteca-action-type': 'details',
                        'tabindex': '-1'
                    });
            }

            $celda.addClass('biblioteca-crud__action-cell');

            if (!$celda.find('[data-biblioteca-action-trigger]').length) {
                var trigger = document.createElement('button');
                var simboloTrigger = document.createElement('span');
                var $contenedor = $celda.find('.biblioteca-personal-list__actions').first();

                trigger.type = 'button';
                trigger.className = 'biblioteca-crud__action-trigger';
                trigger.setAttribute('aria-label', 'Abrir acciones del registro');
                trigger.setAttribute('aria-haspopup', 'menu');
                trigger.setAttribute('aria-expanded', 'false');
                trigger.setAttribute('aria-controls', 'bibliotecaCrudActionMenu');
                trigger.setAttribute('data-biblioteca-action-trigger', '');

                simboloTrigger.className = 'biblioteca-symbol';
                simboloTrigger.setAttribute('aria-hidden', 'true');
                simboloTrigger.textContent = 'more_vert';
                trigger.appendChild(simboloTrigger);

                if ($contenedor.length) {
                    $contenedor.append(trigger);
                } else {
                    celda.appendChild(trigger);
                }
            }
        });
    }

    $(document).on('click.bibliotecaCrudActions', '[data-biblioteca-action-trigger]', function (event) {
        event.preventDefault();
        event.stopPropagation();

        if (menuAccionesEstado.trigger === this && !obtenerMenuAcciones().hidden) {
            cerrarMenuAcciones(false);
            return;
        }

        abrirMenuAcciones(
            this,
            Boolean(event.originalEvent && event.originalEvent.detail === 0)
        );
    });

    $(document).on('click.bibliotecaCrudActionsMenu', '[data-biblioteca-menu-action]', function (event) {
        event.preventDefault();

        var tipo = this.getAttribute('data-biblioteca-menu-action');
        var celda = menuAccionesEstado.celda;
        var trigger = menuAccionesEstado.trigger;
        var selector = tipo === 'details'
            ? '[data-biblioteca-action-type="details"]'
            : '[data-action-type="' + tipo + '"]';
        var accionOriginal = celda ? celda.querySelector(selector) : null;

        cerrarMenuAcciones(false);

        if (!accionOriginal) {
            return;
        }

        accionOriginal.click();

        if (tipo === 'details' && trigger && document.contains(trigger)) {
            trigger.focus();
        }
    });

    $(document).on('click.bibliotecaCrudActionsOutside', function (event) {
        if (!menuAccionesEstado.trigger) {
            return;
        }

        if ($(event.target).closest('[data-biblioteca-action-menu], [data-biblioteca-action-trigger]').length) {
            return;
        }

        cerrarMenuAcciones(false);
    });

    $(document).on('keydown.bibliotecaCrudActions', function (event) {
        if (event.key === 'Escape' && menuAccionesEstado.trigger) {
            event.preventDefault();
            cerrarMenuAcciones(true);
        }
    });

    window.addEventListener('resize', function () {
        cerrarMenuAcciones(false);
    });

    window.addEventListener('scroll', function () {
        cerrarMenuAcciones(false);
    }, true);

    $(document).on('click.bibliotecaPeriodo', '.biblioteca-crud--listado a[href]', function () {
        this.href = agregarPeriodo(this.href);
    });

    function obtenerRegistroId(url) {
        try {
            var pathname = new URL(url, window.location.href).pathname;
            var match = pathname.match(/\/delete\/(\d+)\/?$/);
            return match ? match[1] : '';
        } catch (error) {
            return '';
        }
    }

    function mostrarErrorEliminacion(mensaje) {
        var $error = $('[data-biblioteca-delete-error]');
        $error.text(mensaje || 'No se pudo eliminar el registro. Intentá nuevamente.');
        $error.removeAttr('hidden');
    }

    function limpiarErrorEliminacion() {
        $('[data-biblioteca-delete-error]').attr('hidden', true).empty();
    }

    function cambiarEstadoEliminacion(procesando) {
        var $modal = $('#bibliotecaEliminarRegistroModal');
        var $confirmar = $modal.find('[data-biblioteca-delete-confirmar]');
        var $cancelar = $modal.find('[data-biblioteca-delete-cancelar]');
        var $texto = $modal.find('[data-biblioteca-delete-confirmar-texto]');

        $confirmar.prop('disabled', procesando);
        $cancelar.prop('disabled', procesando);
        $modal.find('.close').prop('disabled', procesando);
        $texto.text(procesando ? 'Eliminando...' : 'Eliminar registro');
        $modal.attr('aria-busy', procesando ? 'true' : 'false');
    }

    $(document).on(
        'click.bibliotecaEliminar',
        '.biblioteca-crud--listado a[data-action-type="delete"], .biblioteca-crud--listado a[href*="/delete/"]',
        function (event) {
            if (event.which && event.which !== 1) {
                return;
            }

            event.preventDefault();

            var $modal = $('#bibliotecaEliminarRegistroModal');
            var deleteUrl = agregarPeriodo(this.href);

            if (!$modal.length || !deleteUrl) {
                window.location.href = deleteUrl || this.href;
                return;
            }

            var registroId = obtenerRegistroId(deleteUrl);

            limpiarErrorEliminacion();
            cambiarEstadoEliminacion(false);
            $modal.data('delete-url', deleteUrl);
            $modal.find('[data-biblioteca-delete-record]').text(
                registroId ? 'N.° ' + registroId : 'seleccionado'
            );
            $modal.modal('show');
        }
    );

    $(document).on('submit.bibliotecaEliminar', '[data-biblioteca-delete-form]', function (event) {
        event.preventDefault();

        var $modal = $('#bibliotecaEliminarRegistroModal');
        var deleteUrl = $modal.data('delete-url');
        var csrfToken = document.querySelector(
            '[data-biblioteca-delete-csrf] [name="csrfmiddlewaretoken"]'
        );

        if (!deleteUrl || !csrfToken || !csrfToken.value) {
            mostrarErrorEliminacion('No se pudo preparar la eliminación de forma segura.');
            return;
        }

        limpiarErrorEliminacion();
        cambiarEstadoEliminacion(true);

        $.ajax({
            url: deleteUrl,
            type: 'POST',
            data: {
                action: 'delete'
            },
            headers: {
                'X-CSRFToken': csrfToken.value,
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).done(function (response) {
            if (response && response.error) {
                mostrarErrorEliminacion(
                    response.message || response.error || 'No se pudo eliminar el registro.'
                );
                return;
            }

            $modal.modal('hide');
            window.location.reload();
        }).fail(function (xhr) {
            var response = xhr.responseJSON || {};
            mostrarErrorEliminacion(
                response.message || response.error || 'No se pudo eliminar el registro.'
            );
        }).always(function () {
            cambiarEstadoEliminacion(false);
        });
    });

    $(document).on('hidden.bs.modal', '#bibliotecaEliminarRegistroModal', function () {
        limpiarErrorEliminacion();
        cambiarEstadoEliminacion(false);
        $(this).removeData('delete-url');
    });

    function conectarBuscador(table, api) {
        var input = document.querySelector('.biblioteca-crud--listado [data-crud-list-search]');

        if (!input) {
            return;
        }

        $(input).off('.bibliotecaCrudSearch').on('input.bibliotecaCrudSearch', function () {
            api.search(this.value).draw();
        });

        $(table).off('.bibliotecaCrudSearch').on('search.dt.bibliotecaCrudSearch', function () {
            input.value = api.search();
        });

        if (input.value) {
            if (api.search() !== input.value) {
                api.search(input.value).draw();
            }
        } else {
            input.value = api.search();
        }
    }

    function clonarOrden(order) {
        var copia = [];

        $.each(order || [], function (index, item) {
            copia.push([item[0], item[1]]);
        });

        return copia;
    }

    function configurarColumnaAcciones(settings) {
        if (settings.nTable.getAttribute('data-actions-column') !== 'last' || !settings.aoColumns.length) {
            return;
        }

        var columna = settings.aoColumns[settings.aoColumns.length - 1];
        var clases = settings.oClasses;

        columna.bSortable = false;
        columna.sSortingClass = clases.sSortableNone;

        $(columna.nTh)
            .removeClass([
                clases.sSortable,
                clases.sSortAsc,
                clases.sSortDesc,
                clases.sSortableAsc,
                clases.sSortableDesc
            ].join(' '))
            .addClass(clases.sSortableNone + ' biblioteca-crud__action-heading all')
            .attr('aria-label', 'Acción')
            .removeAttr('tabindex aria-controls aria-sort')
            .text('ACCIÓN');
    }

    function actualizarAriaOrden(settings, estado) {
        $.each(settings.aoColumns, function (index, columna) {
            if (!columna.bSortable) {
                columna.nTh.setAttribute('aria-label', columna.sTitle.replace(/<.*?>/g, ''));
                return;
            }

            var accion = ' ordenar de forma ascendente';

            if (estado.columna === index && estado.paso === 1) {
                accion = ' ordenar de forma descendente';
            } else if (estado.columna === index && estado.paso === 2) {
                accion = ' restaurar el orden inicial';
            }

            columna.nTh.setAttribute('aria-label', columna.sTitle.replace(/<.*?>/g, '') + ':' + accion);
        });
    }

    function conectarOrdenTristado(table, api, settings) {
        var thead = table.tHead;

        if (!thead) {
            return;
        }

        var estado = {
            columna: null,
            paso: 0,
            ordenInicial: clonarOrden(api.order())
        };

        if (table._bibliotecaOrdenTristado) {
            thead.removeEventListener('click', table._bibliotecaOrdenTristado, true);
            thead.removeEventListener('keypress', table._bibliotecaOrdenTristado, true);
        }

        function ordenar(event) {
            if (event.type === 'click' && event.button !== 0) {
                return;
            }

            if (event.type === 'keypress' && event.which !== 13 && event.keyCode !== 13) {
                return;
            }

            var encabezado = $(event.target).closest('th')[0];

            if (!encabezado || !thead.contains(encabezado)) {
                return;
            }

            var indice = api.column(encabezado).index();

            if (indice === undefined || indice === null || !settings.aoColumns[indice].bSortable) {
                return;
            }

            if (event.shiftKey) {
                estado.columna = null;
                estado.paso = 0;
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            if (estado.columna !== indice) {
                estado.columna = indice;
                estado.paso = 0;
            }

            estado.paso += 1;

            if (estado.paso === 1) {
                api.order([[indice, 'asc']]).draw();
            } else if (estado.paso === 2) {
                api.order([[indice, 'desc']]).draw();
            } else {
                api.order(clonarOrden(estado.ordenInicial)).draw();
                estado.paso = 0;
            }

            actualizarAriaOrden(settings, estado);
        }

        table._bibliotecaOrdenTristado = ordenar;
        thead.addEventListener('click', ordenar, true);
        thead.addEventListener('keypress', ordenar, true);
        actualizarAriaOrden(settings, estado);
    }

    function normalizarTituloColumna(valor) {
        return String(valor || '')
            .replace(/<[^>]*>/g, '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[^A-Z0-9]/gi, '')
            .toUpperCase();
    }

    function ocultarContextoPeriodo(settings, api) {
        if (
            !window.bibliotecaPeriodoActivoId ||
            !settings ||
            !settings.nTable ||
            settings.nTable.getAttribute('data-biblioteca-periodo-oculto') === 'true' ||
            settings.aoColumns.length < 4
        ) {
            return;
        }

        var primerasColumnas = settings.aoColumns.slice(0, 3).map(function (columna) {
            return normalizarTituloColumna(columna.sTitle);
        });

        if (
            primerasColumnas[0] !== 'CUEANEXO' ||
            primerasColumnas[1] !== 'MES' ||
            primerasColumnas[2] !== 'ANO'
        ) {
            return;
        }

        [0, 1, 2].forEach(function (indice) {
            settings.aoColumns[indice].bSearchable = false;
        });

        api.columns([0, 1, 2]).visible(false, false);
        api.columns.adjust();
        settings.nTable.setAttribute('data-biblioteca-periodo-oculto', 'true');
    }

    function numeroTotalizable(valor) {
        if (typeof valor === 'number') {
            return Number.isFinite(valor) ? valor : 0;
        }

        if (valor === null || valor === undefined || valor === '') {
            return 0;
        }

        var numero = Number(valor);
        return Number.isFinite(numero) ? numero : 0;
    }

    function sincronizarResumenTotales(settings) {
        var table = settings.nTable;
        var contenedor = table.closest('.biblioteca-crud__table-wrap');
        var resumen = contenedor
            ? contenedor.querySelector('[data-biblioteca-section-totals]')
            : null;

        if (!resumen) {
            return;
        }

        var api = new $.fn.dataTable.Api(settings);
        var registros = api.rows({
            page: 'all',
            search: 'none'
        }).data().toArray();

        resumen.querySelectorAll('[data-biblioteca-total-field]').forEach(function (destino) {
            var campo = destino.getAttribute('data-biblioteca-total-field');
            var total = registros.reduce(function (acumulado, registro) {
                return acumulado + numeroTotalizable(registro ? registro[campo] : 0);
            }, 0);

            destino.textContent = total.toLocaleString('es-AR');
        });

        resumen.querySelectorAll('[data-biblioteca-total-count]').forEach(function (destino) {
            destino.textContent = registros.length.toLocaleString('es-AR');
        });
    }

    function obtenerHijoDirecto(wrapper, elemento) {
        var actual = elemento;

        while (actual && actual.parentNode !== wrapper) {
            actual = actual.parentNode;
        }

        return actual && actual.parentNode === wrapper ? actual : null;
    }

    function textoInformacionTabla(settings) {
        var api = new $.fn.dataTable.Api(settings);
        var pagina = api.page.info();
        var total = pagina.recordsDisplay || 0;

        if (!total) {
            return 'No hay registros para mostrar';
        }

        var inicio = pagina.start + 1;
        var fin = pagina.end;

        if (total === 1) {
            return 'Mostrando 1 de 1 registro';
        }

        return 'Mostrando ' + inicio + '–' + fin + ' de ' + total + ' registros';
    }

    function normalizarMetaTabla(settings) {
        var table = settings.nTable;
        var wrapper = table.closest('.dataTables_wrapper');

        if (!wrapper) {
            return null;
        }

        var info = wrapper.querySelector('.dataTables_info');
        var paginacion = wrapper.querySelector('.dataTables_paginate');

        if (!info && !paginacion) {
            return null;
        }

        var contenedoresPrevios = [
            obtenerHijoDirecto(wrapper, info),
            obtenerHijoDirecto(wrapper, paginacion)
        ].filter(function (elemento, indice, lista) {
            return elemento && lista.indexOf(elemento) === indice;
        });

        var meta = wrapper.querySelector('.biblioteca-crud__table-meta');

        if (!meta) {
            meta = document.createElement('div');
            meta.className = 'biblioteca-crud__table-meta';

            if (contenedoresPrevios.length) {
                wrapper.insertBefore(meta, contenedoresPrevios[0]);
            } else {
                wrapper.appendChild(meta);
            }
        }

        if (info && info.parentNode !== meta) {
            meta.appendChild(info);
        }

        if (paginacion && paginacion.parentNode !== meta) {
            meta.appendChild(paginacion);
        }

        contenedoresPrevios.forEach(function (contenedor) {
            if (
                contenedor !== meta &&
                contenedor.parentNode === wrapper &&
                !contenedor.querySelector('.dataTables_info, .dataTables_paginate') &&
                !contenedor.textContent.trim() &&
                !contenedor.querySelector('table, input, select, button, a')
            ) {
                contenedor.remove();
            }
        });

        if (info) {
            info.textContent = textoInformacionTabla(settings);
        }

        return meta;
    }

    function configurarResumenTotales(settings) {
        var table = settings.nTable;
        var contenedor = table.closest('.biblioteca-crud__table-wrap');
        var resumen = contenedor
            ? contenedor.querySelector('[data-biblioteca-section-totals]')
            : null;

        if (!resumen) {
            return;
        }

        var wrapper = table.closest('.dataTables_wrapper');

        if (wrapper) {
            var meta = normalizarMetaTabla(settings);
            var ancla = meta;

            if (!ancla) {
                var filas = Array.prototype.filter.call(wrapper.children, function (elemento) {
                    return elemento.classList && elemento.classList.contains('row');
                });
                ancla = filas.length ? filas[filas.length - 1] : null;
            }

            if (resumen.parentNode !== wrapper || resumen.nextSibling !== ancla) {
                wrapper.insertBefore(resumen, ancla);
            }
        }

        sincronizarResumenTotales(settings);
    }

    $(document).on('preInit.dt.bibliotecaCrud', function (event, settings) {
        if (settings.nTable && settings.nTable.id === 'data') {
            var api = new $.fn.dataTable.Api(settings);

            prepararColumnaAccionesResponsive(settings.nTable);
            configurarColumnaAcciones(settings);
            ocultarContextoPeriodo(settings, api);
            configurarResumenTotales(settings);
        }
    });

    $(document).on('init.dt', function (event, settings) {
        if (settings.nTable && settings.nTable.id === 'data') {
            var api = new $.fn.dataTable.Api(settings);

            ocultarContextoPeriodo(settings, api);
            normalizarMetaTabla(settings);
            configurarResumenTotales(settings);
            actualizarEnlacesPeriodo(settings.nTable);
            normalizarAcciones(settings.nTable);
            conectarBuscador(settings.nTable, api);
            conectarOrdenTristado(settings.nTable, api, settings);
        }
    });

    $(document).on('draw.dt.bibliotecaPeriodo', function (event, settings) {
        if (settings.nTable && settings.nTable.id === 'data') {
            normalizarMetaTabla(settings);
            configurarResumenTotales(settings);
            actualizarEnlacesPeriodo(settings.nTable);
            normalizarAcciones(settings.nTable);
        }
    });

    $(function () {
        var table = document.getElementById('data');

        if (!table) {
            return;
        }

        prepararColumnaAccionesResponsive(table);

        if ($.fn.dataTable.isDataTable(table)) {
            normalizarAcciones(table);
            conectarBuscador(table, new $.fn.dataTable.Api(table));
        }
    });
}(jQuery));
