(function ($) {
    'use strict';

    function integrarControles(table) {
        var wrapper = table.closest('.dataTables_wrapper');
        var toolbar = document.querySelector('.biblioteca-crud--listado .biblioteca-crud__list-toolbar');

        if (!wrapper || !toolbar) {
            return;
        }

        var filter = wrapper.querySelector('.dataTables_filter');
        var controlsRow = filter ? filter.closest('.row') : null;

        if (!filter || !controlsRow) {
            return;
        }

        var filterSlot = filter.parentElement;
        var toolbarSlot = Array.prototype.find.call(controlsRow.children, function (column) {
            return column !== filterSlot;
        });

        if (!toolbarSlot) {
            toolbarSlot = document.createElement('div');
            toolbarSlot.className = 'col-sm-12 col-md-6';
            controlsRow.insertBefore(toolbarSlot, filterSlot);
        }

        controlsRow.classList.add('biblioteca-crud__datatable-controls');
        toolbarSlot.classList.add('biblioteca-crud__toolbar-slot');
        filterSlot.classList.add('biblioteca-crud__filter-slot');
        toolbarSlot.appendChild(toolbar);

        var label = filter.querySelector('label');
        var input = filter.querySelector('input[type="search"]');

        if (!label || !input) {
            return;
        }

        input.placeholder = 'Buscar registro';
        input.setAttribute('aria-label', 'Buscar registro');

        Array.prototype.slice.call(label.childNodes).forEach(function (node) {
            if (node.nodeType === 3) {
                node.remove();
            }
        });

        if (!label.querySelector('.biblioteca-crud__filter-icon')) {
            var icon = document.createElement('span');
            icon.className = 'biblioteca-symbol biblioteca-crud__filter-icon';
            icon.setAttribute('aria-hidden', 'true');
            icon.textContent = 'document_search';
            label.insertBefore(icon, input);
        }
    }

    $(document).on('init.dt', function (event, settings) {
        if (settings.nTable && settings.nTable.id === 'data') {
            integrarControles(settings.nTable);
        }
    });

    $(function () {
        var table = document.getElementById('data');

        if (table && $.fn.dataTable.isDataTable(table)) {
            integrarControles(table);
        }
    });
}(jQuery));
