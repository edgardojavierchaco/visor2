(function () {
    "use strict";

    var selectSelector = "select[data-cef-select]";
    var jqueryUrl = "https://code.jquery.com/jquery-3.6.0.min.js";
    var select2Url = "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js";

    function loadScript(id, src, callback) {
        var script = document.getElementById(id) || document.querySelector('script[src="' + src + '"]');
        if (script) {
            script.addEventListener("load", callback, { once: true });
            return;
        }

        script = document.createElement("script");
        script.id = id;
        script.src = src;
        script.addEventListener("load", callback, { once: true });
        document.head.appendChild(script);
    }

    function ensureSelect2(callback) {
        function loadSelect2() {
            if (window.jQuery.fn && window.jQuery.fn.select2) {
                callback();
                return;
            }
            loadScript("cef-select2-script", select2Url, callback);
        }

        if (window.jQuery) {
            loadSelect2();
            return;
        }
        loadScript("cef-jquery-script", jqueryUrl, loadSelect2);
    }

    function selectsIn(root) {
        root = root || document;
        var selects = [];
        if (root.matches && root.matches(selectSelector)) selects.push(root);
        if (root.querySelectorAll) {
            selects = selects.concat(Array.prototype.slice.call(root.querySelectorAll(selectSelector)));
        }
        return selects;
    }

    function searchThreshold(select) {
        return select.dataset.cefSelectSearch === "always" ? 0 : Infinity;
    }

    function dropdownParent(select) {
        return select.closest(".modal, .cef-docente-overlay, .cef-overlay")
            || select.closest("[role='dialog'][aria-modal='true']");
    }

    function visualViewportSize() {
        var viewport = window.visualViewport;
        return {
            width: viewport ? viewport.width : (document.documentElement.clientWidth || window.innerWidth),
            height: viewport ? viewport.height : (document.documentElement.clientHeight || window.innerHeight)
        };
    }

    function constrainOpenDropdown() {
        if (!window.jQuery) return;
        var size = visualViewportSize();
        var maxWidth = Math.max(0, size.width - 24);
        var maxHeight = Math.max(96, Math.min(320, size.height - 144));
        var $dropdown = window.jQuery(".cef-select2-dropdown").last();
        $dropdown.css("max-width", maxWidth + "px");
        $dropdown.find(".select2-results__options").css("max-height", maxHeight + "px");
    }

    function initSelect(select) {
        if (!select.isConnected) return;
        var $ = window.jQuery;
        var $select = $(select);
        if ($select.data("select2")) return;

        var parent = dropdownParent(select);
        var config = {
            width: "100%",
            dropdownCssClass: "cef-select2-dropdown",
            minimumResultsForSearch: searchThreshold(select),
            language: {
                searching: function () { return "Buscando..."; },
                noResults: function () { return "No se encontraron resultados"; }
            }
        };
        if (parent) config.dropdownParent = $(parent);

        $select.select2(config);
        $select.on("select2:open.cefSelect", function () {
            window.setTimeout(constrainOpenDropdown, 0);
        });
    }

    function init(root, callback) {
        var selects = selectsIn(root);
        if (!selects.length) {
            if (callback) callback();
            return;
        }

        ensureSelect2(function () {
            selects.forEach(initSelect);
            if (callback) callback();
        });
    }

    function destroy(root) {
        if (!window.jQuery || !window.jQuery.fn || !window.jQuery.fn.select2) return;
        selectsIn(root).forEach(function (select) {
            var $select = window.jQuery(select);
            if ($select.data("select2")) {
                $select.off(".cefSelect");
                $select.select2("destroy");
            }
        });
    }

    function sync(select) {
        if (!select || !window.jQuery) return;
        var $select = window.jQuery(select);
        if ($select.data("select2")) $select.trigger("change.select2");
    }

    function focus(select) {
        if (!select) return;
        init(select, function () {
            var instance = window.jQuery(select).data("select2");
            if (instance && instance.$selection) instance.$selection.trigger("focus");
            else select.focus();
        });
    }

    window.initCefSelects = init;
    window.CEFSelects = {
        destroy: destroy,
        focus: focus,
        init: init,
        sync: sync
    };

    window.addEventListener("resize", constrainOpenDropdown);
    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", constrainOpenDropdown);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { init(document); }, { once: true });
    } else {
        init(document);
    }
})();
