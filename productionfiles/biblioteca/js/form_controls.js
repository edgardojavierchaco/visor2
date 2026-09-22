(function (window, $) {
    'use strict';

    if (!$ || !$.fn) {
        return;
    }

    var SEARCH_THRESHOLD = 7;

    function optionCount(select) {
        return Array.prototype.filter.call(select.options || [], function (option) {
            return option.value !== '' && !option.disabled;
        }).length;
    }

    function initSearchableSelect(select) {
        if (!$.fn.select2 || select.dataset.bibliotecaSelectReady === 'true') {
            return;
        }

        if (optionCount(select) <= SEARCH_THRESHOLD) {
            return;
        }

        var $select = $(select);
        var $wrap = $select.closest('.biblioteca-form__select-wrap');
        var $root = $select.closest('.biblioteca-form-standard');

        $wrap.addClass('biblioteca-form__select-wrap--search');
        $select.select2({
            theme: 'bootstrap4',
            width: '100%',
            dropdownParent: $root.length ? $root : $(document.body),
            minimumResultsForSearch: 0,
            language: {
                noResults: function () { return 'Sin resultados'; },
                searching: function () { return 'Buscando…'; }
            }
        });

        select.dataset.bibliotecaSelectReady = 'true';
    }

    $(function () {
        document.querySelectorAll('.biblioteca-form__select').forEach(initSearchableSelect);
    });
})(window, window.jQuery);
