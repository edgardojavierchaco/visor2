(function ($) {
    'use strict';

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

    $(document).on('init.dt', function (event, settings) {
        if (settings.nTable && settings.nTable.id === 'data') {
            conectarBuscador(settings.nTable, new $.fn.dataTable.Api(settings));
        }
    });

    $(function () {
        var table = document.getElementById('data');

        if (table && $.fn.dataTable.isDataTable(table)) {
            conectarBuscador(table, new $.fn.dataTable.Api(table));
        }
    });
}(jQuery));
