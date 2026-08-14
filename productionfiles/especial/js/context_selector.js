(function () {
    "use strict";

    var JQUERY_SRC = "https://code.jquery.com/jquery-3.6.0.min.js";
    var SELECT2_SRC = "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js";

    function loadScript(src, callback) {
        var existing = document.querySelector('script[src="' + src + '"]');
        if (existing) {
            if (existing.dataset.loaded === "1") callback();
            else existing.addEventListener("load", callback, { once: true });
            return;
        }
        var script = document.createElement("script");
        script.src = src;
        script.onload = function () {
            script.dataset.loaded = "1";
            callback();
        };
        document.head.appendChild(script);
    }

    function findContextSelect(root) {
        if (root && root.matches && root.matches("#id_contexto_cueanexo")) return root;
        var scope = root && root.querySelector ? root : document;
        return scope.querySelector("#id_contexto_cueanexo");
    }

    function initSelect(select) {
        if (!select || !window.jQuery || !window.jQuery.fn || !window.jQuery.fn.select2) return;
        var $select = window.jQuery(select);
        if ($select.data("select2")) return;

        $select.select2({
            width: "100%",
            minimumResultsForSearch: 0,
            dropdownCssClass: "cef-context-select2-dropdown",
            language: {
                noResults: function () { return "No se encontraron establecimientos"; },
                searching: function () { return "Buscando..."; }
            }
        });

        $select.on("select2:open.especialContextSelector", function () {
            window.setTimeout(function () {
                var search = document.querySelector(".cef-context-select2-dropdown .select2-search__field");
                if (search) search.focus();
            }, 0);
        });
    }

    function ensureDependencies(select) {
        if (!select) return;
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
            initSelect(select);
            return;
        }

        var startSelect2 = function () {
            loadScript(SELECT2_SRC, function () { initSelect(select); });
        };
        if (window.jQuery) startSelect2();
        else loadScript(JQUERY_SRC, startSelect2);
    }

    function init(root) {
        ensureDependencies(findContextSelect(root));
    }

    function destroy(root) {
        var select = findContextSelect(root);
        if (!select || !window.jQuery || !window.jQuery.fn || !window.jQuery.fn.select2) return;
        var $select = window.jQuery(select);
        if (!$select.data("select2")) return;
        $select.off(".especialContextSelector");
        $select.select2("destroy");
    }

    window.EspecialContextSelector = {
        init: init,
        destroy: destroy
    };
})();
