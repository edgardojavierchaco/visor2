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

    $(document).on('click.bibliotecaPeriodo', '.biblioteca-crud--listado a[href]', function () {
        this.href = agregarPeriodo(this.href);
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
            .addClass(clases.sSortableNone)
            .removeAttr('tabindex aria-controls aria-sort');
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

    $(document).on('preInit.dt.bibliotecaCrud', function (event, settings) {
        if (settings.nTable && settings.nTable.id === 'data') {
            configurarColumnaAcciones(settings);
        }
    });

    $(document).on('init.dt', function (event, settings) {
        if (settings.nTable && settings.nTable.id === 'data') {
            actualizarEnlacesPeriodo(settings.nTable);
            var api = new $.fn.dataTable.Api(settings);

            conectarBuscador(settings.nTable, api);
            conectarOrdenTristado(settings.nTable, api, settings);
        }
    });

    $(document).on('draw.dt.bibliotecaPeriodo', function (event, settings) {
        if (settings.nTable && settings.nTable.id === 'data') {
            actualizarEnlacesPeriodo(settings.nTable);
        }
    });

    $(function () {
        var table = document.getElementById('data');

        if (table && $.fn.dataTable.isDataTable(table)) {
            conectarBuscador(table, new $.fn.dataTable.Api(table));
        }
    });
}(jQuery));
