
(function() {
    "use strict";

    if (window.__CEF_LOCALIZACIONES_PADRON_FINAL__) {
        return;
    }
    window.__CEF_LOCALIZACIONES_PADRON_FINAL__ = true;

    var filterOptions = {};
    var columnsConfig = [];
    var ajaxController = null;
    var ajaxPendingUrl = "";
    var liveSearchTimer = null;
    var cefSelectorTimer = null;
    var select2Loaded = false;
    var suppressCefChange = false;
    var defaultCols = {};
    var cefOptions = [];
    var cefOptionsMap = {};
    var initialPageSize = document.querySelector('#filterForm input[name="page_size"]').value || "10";
    var checklistFilterFields = {
        region_loc: true,
        localidad: true,
        departamento: true
    };
    var operatorLabels = {
        "0": "parecido a",
        "1": "no parecido a",
        "2": "igual a",
        "3": "mayor a",
        "4": "mayor o igual a",
        "5": "menor a",
        "6": "menor o igual a",
        "7": "distinto de"
    };

    try {
        var filterOptionsData = document.getElementById("cefFilterOptionsData");
        filterOptions = filterOptionsData ? JSON.parse(filterOptionsData.textContent || "{}") : {};
    } catch (error) {
        filterOptions = {};
    }

    try {
        var columnsConfigData = document.getElementById("cefColumnsConfigData");
        columnsConfig = columnsConfigData ? JSON.parse(columnsConfigData.textContent || "[]") : [];
    } catch (error) {
        columnsConfig = [];
    }

    try {
        var cefOptionsData = document.getElementById("cefOptionsData");
        cefOptions = cefOptionsData ? JSON.parse(cefOptionsData.textContent || "[]") : [];
    } catch (error) {
        cefOptions = [];
    }

    columnsConfig.forEach(function(column) {
        defaultCols["col-" + column.slug] = column.default !== false;
    });

    cefOptions.forEach(function(option) {
        if (option && option.cueanexo) {
            cefOptionsMap[String(option.cueanexo)] = option.nom_est || "";
        }
    });

    function rebuildCefOptionsMap(options) {
        cefOptions = Array.isArray(options) ? options : [];
        cefOptionsMap = {};
        cefOptions.forEach(function(option) {
            if (option && option.cueanexo) {
                cefOptionsMap[String(option.cueanexo)] = option.nom_est || "";
            }
        });
    }

    function loadCefOptionsFromDom() {
        var data = qs("#cefOptionsData");
        if (!data) {
            return;
        }
        try {
            rebuildCefOptionsMap(JSON.parse(data.textContent || "[]"));
        } catch (error) {
            rebuildCefOptionsMap([]);
        }
    }

    function loadFilterOptionsFromDom(root) {
        var data = qs("#cefFilterOptionsData", root || document);

        if (!data) {
            return;
        }

        try {
            filterOptions = JSON.parse(data.textContent || "{}") || {};
        } catch (error) {
            filterOptions = {};
        }
    }

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function qsa(selector, root) {
        return Array.prototype.slice.call((root || document).querySelectorAll(selector));
    }

    function closest(element, selector) {
        return element && element.closest ? element.closest(selector) : null;
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function escapeCssValue(value) {
        if (window.CSS && typeof window.CSS.escape === "function") {
            return window.CSS.escape(value);
        }
        return String(value || "").replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    }

    function getParams() {
        return new URLSearchParams(window.location.search);
    }

    function makeUrl(params) {
        var query = params.toString();
        return window.location.pathname + (query ? "?" + query : "");
    }

    function labelForField(field) {
        var found = columnsConfig.find(function(column) {
            return column.key === field;
        });
        return found ? found.label : field;
    }

    function setBusy(active) {
        document.documentElement.classList.toggle("cef-soft-updating", !!active);
    }

    function showCefModal(modalEl) {
        if (!modalEl) {
            return;
        }
        if (modalEl.classList.contains("filter-dialog")) {
            modalEl.classList.add("is-visible");
            modalEl.setAttribute("aria-hidden", "false");
            document.body.classList.add("modal-open");
            return;
        }
        if (window.bootstrap && window.bootstrap.Modal) {
            try {
                window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
                return;
            } catch (error) {
                // Fallback manual para layouts que mezclan Bootstrap 4/5.
            }
        }
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.modal) {
            try {
                window.jQuery(modalEl).modal("show");
                return;
            } catch (error) {
                // Fallback manual para layouts sin plugin modal estable.
            }
        }
        modalEl.style.display = "block";
        modalEl.removeAttribute("aria-hidden");
        modalEl.setAttribute("aria-modal", "true");
        modalEl.setAttribute("role", "dialog");
        modalEl.classList.add("show");
        document.body.classList.add("modal-open");
    }

    function hideCefModal(modalEl) {
        if (!modalEl) {
            return;
        }
        if (modalEl.classList.contains("filter-dialog")) {
            modalEl.classList.remove("is-visible");
            modalEl.setAttribute("aria-hidden", "true");
            document.body.classList.remove("modal-open");
            return;
        }
        if (window.bootstrap && window.bootstrap.Modal) {
            try {
                window.bootstrap.Modal.getOrCreateInstance(modalEl).hide();
                return;
            } catch (error) {
                // Fallback manual para layouts que mezclan Bootstrap 4/5.
            }
        }
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.modal) {
            try {
                window.jQuery(modalEl).modal("hide");
                return;
            } catch (error) {
                // Fallback manual para layouts sin plugin modal estable.
            }
        }
        modalEl.classList.remove("show");
        modalEl.style.display = "none";
        modalEl.setAttribute("aria-hidden", "true");
        modalEl.removeAttribute("aria-modal");
        modalEl.removeAttribute("role");
        document.body.classList.remove("modal-open");
    }

    function openGuideModal() {
        showCefModal(qs("#guiaUsoModal"));
    }

    function bindDirectUiHandlers() {
        qsa("#btnToggleFiltros, #btnToggleColumnas, #btnGuiaUso").forEach(function(el) {
            el.dataset.cefBound = "1";
        });
    }

    function restoreCefTableOpacity() {
        qsa(".table-shell .table-responsive").forEach(function(viewport) {
            viewport.style.opacity = "";
        });
    }

    function normalizeAjaxUrl(url) {
        var normalized = new URL(url, window.location.href);
        normalized.searchParams.delete("fragmento");
        normalized.hash = "";
        return normalized.toString();
    }

    function buildAjaxRequestUrl(url) {
        var requestUrl = new URL(url, window.location.href);
        requestUrl.searchParams.set("fragmento", "resultados");
        requestUrl.hash = "";
        return requestUrl.toString();
    }

    function getRefreshFocusSelector(source) {
        var element = source || document.activeElement;
        var header;

        if (!element) {
            return "";
        }

        if (element.id) {
            return "#" + element.id;
        }

        header = closest(element, "th[data-dbcol]");
        if (header && header.dataset.dbcol) {
            return 'th[data-dbcol="' + header.dataset.dbcol + '"] a';
        }

        if (closest(element, "#pagination-container")) {
            return "#pagination-container .page-item.active .page-link";
        }

        return "";
    }

    function captureRefreshState(trigger) {
        var viewport = qs(".table-shell .table-responsive");
        return {
            scrollLeft: viewport ? viewport.scrollLeft : 0,
            scrollTop: viewport ? viewport.scrollTop : 0,
            windowScrollY: window.scrollY || window.pageYOffset || 0,
            focusSelector: getRefreshFocusSelector(trigger)
        };
    }

    function restoreRefreshState(state) {
        if (!state) {
            return;
        }

        window.requestAnimationFrame(function() {
            window.requestAnimationFrame(function() {
                var viewport = qs(".table-shell .table-responsive");
                var focusTarget = state.focusSelector ? qs(state.focusSelector) : null;

                if (viewport) {
                    viewport.scrollLeft = state.scrollLeft || 0;
                    viewport.scrollTop = state.scrollTop || 0;
                }

                window.scrollTo(window.scrollX || 0, state.windowScrollY || 0);

                if (focusTarget && typeof focusTarget.focus === "function") {
                    focusTarget.focus({ preventScroll: true });
                }
            });
        });
    }

    function syncCefExcelLinks() {
        syncExcelLinks();
    }

    function syncCefSelectorFormFromParams() {
        var form = qs("#cefSelectorForm");
        var params = getParams();

        if (!form) {
            return;
        }

        qsa('input[type="hidden"]', form).forEach(function(input) {
            input.remove();
        });

        params.forEach(function(value, key) {
            if (key === "establecimientos" || key === "page" || key === "formato") {
                return;
            }
            form.insertAdjacentHTML("afterbegin", '<input type="hidden" name="' + escapeHtml(key) + '" value="' + escapeHtml(value) + '">');
        });
    }

    function syncCefSelectorFromParams() {
        var select = qs("#cefSelectorSelect");
        var params = getParams();
        var selected = params.getAll("establecimientos");
        var selectedMap = {};
        var title = qs("#cefSelectorShell .cef-selector-copy strong");

        if (!select) {
            return;
        }

        selected.forEach(function(value) {
            selectedMap[String(value)] = true;
        });

        suppressCefChange = true;
        qsa("option", select).forEach(function(option) {
            option.selected = !!selectedMap[String(option.value)];
        });

        if (window.jQuery && window.jQuery(select).data("select2")) {
            window.jQuery(select).val(selected).trigger("change.select2");
        }

        select.dataset.lastAppliedCefs = cefSelectionKey(select);
        suppressCefChange = false;

        if (title) {
            title.textContent = selected.length ? selected.length + " seleccionados" : "Todos los establecimientos";
        }

        updateCefPlaceholder();
    }

    function syncCefFilterFormFromParams() {
        var form = qs("#filterForm");
        var pageSizeInput;
        var params = getParams();

        if (!form) {
            return;
        }

        qsa('input[name="establecimientos"]', form).forEach(function(input) {
            input.remove();
        });

        params.getAll("establecimientos").forEach(function(value) {
            form.insertAdjacentHTML("afterbegin", '<input type="hidden" name="establecimientos" value="' + escapeHtml(value) + '">');
        });

        pageSizeInput = qs('input[name="page_size"]', form);
        if (pageSizeInput) {
            pageSizeInput.value = params.get("page_size") || initialPageSize;
        }
    }

    function syncCefLiveSearchFromParams() {
        var params = getParams();
        var input = qs("#liveSearchInput");
        var select = qs("#liveSearchSelect");
        var field = params.get("smart_ui_col") || (params.get("q") ? "all" : "cueanexo");
        var value = params.get("smart_ui_val") || params.get("q") || "";

        if (input && input.value !== value) {
            input.value = value;
        }

        if (select) {
            select.value = field;
            if (select.value !== field) {
                select.value = "cueanexo";
            }
        }

        syncSearchClear();
    }

    function syncCefColumnState() {
        syncColumns();
        ensureActiveColumns();
        queueContractedTableLayout({ instant: true });
    }

    function hydrateCefTableFragments() {
        hydrateFilterHiddens();
        syncCefFilterFormFromParams();
        syncCefSelectorFormFromParams();
        syncCefSelectorFromParams();
        syncCefLiveSearchFromParams();
        renderBadges();
        syncCefColumnState();
        syncTableSortHeaders();
        scheduleReapplyHighlights();
    }

    function initCefPagination(baseUrl) {
        var nav = qs("#pagination-nav");
        var paginationList = qs("#paginador-lista");

        if (!nav) {
            return;
        }

        qsa(".edge-first, .edge-last, .edge-boundary, .edge-gap", nav).forEach(function(item) {
            item.parentNode.removeChild(item);
        });

        if (!paginationList) {
            return;
        }

        var currentPage = parseInt(nav.getAttribute("data-current-page") || "1", 10);
        var totalPages = parseInt(nav.getAttribute("data-total-pages") || "0", 10);
        var pageItems = qsa("li.page-item", paginationList);
        var firstItem = pageItems[0];
        var lastItem = pageItems[pageItems.length - 1];
        var visibleNumbers = pageItems.map(function(item) {
            var value = parseInt((item.textContent || "").trim(), 10);
            return isNaN(value) ? null : value;
        }).filter(function(value) {
            return value !== null;
        });
        var firstVisible = visibleNumbers.length ? Math.min.apply(Math, visibleNumbers) : currentPage;
        var lastVisible = visibleNumbers.length ? Math.max.apply(Math, visibleNumbers) : currentPage;

        function buildPageUrl(page) {
            var url = new URL(baseUrl || window.location.href, window.location.href);
            url.searchParams.set("page", page);
            url.searchParams.delete("formato");
            return url.toString();
        }

        if (totalPages > 1 && firstItem && lastItem) {
            firstItem.insertAdjacentHTML(
                "afterend",
                currentPage <= 1
                    ? '<li class="page-item edge-first disabled"><span class="page-link" aria-disabled="true"><i class="fa-solid fa-angles-left"></i></span></li>'
                    : '<li class="page-item edge-first"><a class="page-link" href="' + buildPageUrl(1) + '" aria-label="Primera página"><i class="fa-solid fa-angles-left"></i></a></li>'
            );
            lastItem.insertAdjacentHTML(
                "beforebegin",
                currentPage >= totalPages
                    ? '<li class="page-item edge-last disabled"><span class="page-link" aria-disabled="true"><i class="fa-solid fa-angles-right"></i></span></li>'
                    : '<li class="page-item edge-last"><a class="page-link" href="' + buildPageUrl(totalPages) + '" aria-label="Última página"><i class="fa-solid fa-angles-right"></i></a></li>'
            );

            if (firstVisible > 1) {
                paginationList.querySelector(".edge-first").insertAdjacentHTML("afterend", '<li class="page-item edge-boundary"><a class="page-link" href="' + buildPageUrl(1) + '">1</a></li>' + (firstVisible > 2 ? '<li class="page-item edge-gap"><span class="page-link border-0 text-muted bg-transparent">...</span></li>' : ""));
            }

            if (lastVisible < totalPages) {
                paginationList.querySelector(".edge-last").insertAdjacentHTML("beforebegin", (lastVisible < totalPages - 1 ? '<li class="page-item edge-gap"><span class="page-link border-0 text-muted bg-transparent">...</span></li>' : "") + '<li class="page-item edge-boundary"><a class="page-link" href="' + buildPageUrl(totalPages) + '">' + totalPages + "</a></li>");
            }
        }
    }

    function replaceCefTableFragments(parsedDocument, options) {
        var opts = options || {};
        var currentFragment = qs("#localizacionesResultsFragment");
        var nextFragment = qs("#localizacionesResultsFragment", parsedDocument);
        var viewport = qs(".table-shell .table-responsive");

        // CEF_PATCH_LOCALIZACIONES_REFRESH_COMO_RESPONSABLES_20260515
        if (!currentFragment || !nextFragment) {
            throw new Error("No se pudieron actualizar los resultados.");
        }

        if (opts.useFade !== false && viewport) {
            viewport.style.opacity = "0.82";
        }

        currentFragment.replaceWith(nextFragment);
        initCefPagination(opts.currentUrl);
        loadCefOptionsFromDom();
        loadFilterOptionsFromDom();
        syncCefExcelLinks();

        window.requestAnimationFrame(function() {
            restoreCefTableOpacity();
        });
        window.setTimeout(restoreCefTableOpacity, 220);
    }

    function refreshUrl(url, options) {
        var opts = options || {};
        var controller;
        var currentUrl;
        var requestUrl;
        var refreshState;

        if (!url) {
            return;
        }

        currentUrl = normalizeAjaxUrl(url);

        if (new URL(currentUrl, window.location.href).searchParams.has("formato")) {
            return;
        }

        if (!opts.force && ajaxPendingUrl && ajaxPendingUrl === currentUrl) {
            return;
        }

        if (!opts.force && currentUrl === normalizeAjaxUrl(window.location.href) && !ajaxController) {
            return;
        }

        if (ajaxController && ajaxPendingUrl !== currentUrl) {
            ajaxController.abort();
        }

        opts.currentUrl = currentUrl;
        requestUrl = buildAjaxRequestUrl(currentUrl);
        refreshState = captureRefreshState(opts.trigger);
        controller = new AbortController();
        ajaxController = controller;
        ajaxPendingUrl = currentUrl;
        setBusy(true);

        fetch(requestUrl, {
            method: "GET",
            credentials: "same-origin",
            headers: {
                "Accept": "text/html",
                "X-Requested-With": "XMLHttpRequest"
            },
            signal: controller.signal
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error("No se pudo actualizar la consulta.");
            }
            return response.text();
        })
        .then(function(html) {
            if (ajaxController !== controller || controller.signal.aborted) {
                return;
            }
            var doc = new DOMParser().parseFromString(html, "text/html");
            replaceCefTableFragments(doc, opts);

            if (opts.replaceHistory) {
                window.history.replaceState({}, "", currentUrl);
            } else if (opts.pushHistory !== false) {
                window.history.pushState({}, "", currentUrl);
            }

            hydrateCefTableFragments();
            restoreRefreshState(refreshState);
        })
        .catch(function(error) {
            if (error && error.name === "AbortError") {
                return;
            }
            window.location.href = currentUrl;
        })
        .finally(function() {
            if (ajaxController === controller) {
                ajaxController = null;
                ajaxPendingUrl = "";
                setBusy(false);
                window.requestAnimationFrame(restoreCefTableOpacity);
                window.setTimeout(restoreCefTableOpacity, 220);
            }
        });
    }

    function loadScript(src, callback) {
        var existing = qsa("script").find(function(script) {
            return script.src === src;
        });
        if (existing) {
            existing.addEventListener("load", callback, { once: true });
            if (existing.dataset.loaded === "1") {
                callback();
            }
            return;
        }

        var script = document.createElement("script");
        script.src = src;
        script.async = true;
        script.onload = function() {
            script.dataset.loaded = "1";
            callback();
        };
        document.head.appendChild(script);
    }

    function ensureSelect2(callback) {
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
            select2Loaded = true;
            callback();
            return;
        }

        if (select2Loaded) {
            callback();
            return;
        }

        var loadSelect2 = function() {
            loadScript("https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js", function() {
                select2Loaded = true;
                callback();
            });
        };

        if (window.jQuery) {
            loadSelect2();
            return;
        }

        loadScript("https://code.jquery.com/jquery-3.6.0.min.js", loadSelect2);
    }

    function selectedCefValues() {
        var select = qs("#cefSelectorSelect");
        return select ? qsa("option:checked", select).map(function(option) { return option.value; }).filter(Boolean) : [];
    }

    function cefSelectionKey(select) {
        return (select ? qsa("option:checked", select).map(function(option) { return option.value; }).filter(Boolean) : [])
            .sort()
            .join("|");
    }

    function submitCefSelectorIfChanged() {
        var select = qs("#cefSelectorSelect");
        var currentKey;
        var lastKey;

        if (!select) {
            return;
        }

        currentKey = cefSelectionKey(select);
        lastKey = select.dataset.lastAppliedCefs || "";

        if (currentKey === lastKey) {
            return;
        }

        select.dataset.lastAppliedCefs = currentKey;
        submitCefSelector();
    }

    function updateCefPlaceholder() {
        // CEF_PATCH_SELECTOR_NEXTALL_SYNC_FIX_20260515
        if (!window.jQuery) {
            return;
        }

        var $select = window.jQuery("#cefSelectorSelect");
        if (!$select.length) {
            return;
        }

        var selected = $select.val() || selectedCefValues();
        var _s2 = $select.data("select2");
        var $container = _s2 && _s2.$container
            ? _s2.$container
            : $select.nextAll(".select2-container").first();
        var $selection = $container.find(".select2-selection--multiple");
        var $searchInput = $container.find(".select2-search__field");
        var text = "Todos los establecimientos";
        var stateClass = "is-empty";
        var displayText;
        var shell = qs("#cefSelectorShell");

        if (typeof selected === "string") {
            selected = selected ? [selected] : [];
        }
        selected = (selected || []).filter(Boolean);

        if (!$container.length) {
            return;
        }

        if (selected.length === 1) {
            text = getCefOptionLabel(selected[0]) || String(selected[0] || "");
            stateClass = "is-single";
        } else if (selected.length > 1) {
            text = selected.length + " establecimientos seleccionados";
            stateClass = "is-multiple";
        }

        if ($selection.length) {
            $selection
                .attr("data-cef-display", text)
                .attr("aria-label", text)
                .removeClass("is-empty is-single is-multiple")
                .addClass(stateClass);

            displayText = $selection.find(".cef-selector-display-text");
            if (!displayText.length) {
                displayText = window.jQuery("<span></span>")
                    .addClass("cef-selector-display-text")
                    .attr("aria-hidden", "true");
                $selection.append(displayText);
            }

            displayText
                .removeClass("is-empty is-single is-multiple")
                .addClass(stateClass)
                .text(text)
                .attr("title", text);
        }

        if ($searchInput.length) {
            $searchInput.removeClass("empty-placeholder multi-placeholder")
                .prop("readonly", true)
                .attr("aria-readonly", "true")
                .attr("placeholder", "")
                .val("");

            if (!selected.length) {
                $searchInput.attr("placeholder", "Todos los establecimientos").addClass("empty-placeholder");
            } else if (selected.length === 1) {
                $searchInput.attr("placeholder", text);
            } else {
                $searchInput.attr("placeholder", text).addClass("multi-placeholder");
            }
        }

            if (shell) {
            shell.classList.add("cef-selector-ready");
         }
    }

    function getSelectedCefMap() {
        // CEF_PATCH_DROPDOWN_VISUAL_SYNC_FIX_20260617
        var map = {};
        var select = qs("#cefSelectorSelect");
        var values = [];
        var $select;

        if (window.jQuery) {
            $select = window.jQuery("#cefSelectorSelect");

            if ($select.length && $select.data("select2")) {
                values = $select.val() || [];
            } else if ($select.length) {
                values = selectedCefValues();
            }
        } else if (select) {
            values = selectedCefValues();
        }

        if (typeof values === "string") {
            values = values ? [values] : [];
        }

        values = values || [];

        values.forEach(function(value) {
            value = String(value || "").trim();
            if (value) {
                map[value] = true;
            }
        });

        return map;
    }

    function isCefValueSelected(value) {
        value = String(value || "").trim();
        return !!(value && getSelectedCefMap()[value]);
    }

    function extractCefValueFromText(text) {
        var match = String(text || "").match(/^\\s*([0-9]{6,})\\s*(?:-|$)/);
        return match ? match[1] : "";
    }

    function getCefValueFromResultOption($option, selectedMap) {
        var rowValue = $option.find("[data-cef-value]").first().attr("data-cef-value");
        var data = $option.data("data");
        var textValue;
        var idAttr;
        var parts;
        var i;

        if (rowValue) {
            return String(rowValue);
        }

        if (data && data.id !== undefined && data.id !== null && String(data.id).trim()) {
            return String(data.id).trim();
        }

        textValue = extractCefValueFromText($option.text());
        if (textValue) {
            return textValue;
        }

        idAttr = String($option.attr("id") || "");
        if (idAttr) {
            parts = idAttr.split("-");
            for (i = parts.length - 1; i >= 0; i -= 1) {
                if (selectedMap && selectedMap[parts[i]]) {
                    return parts[i];
                }
            }
        }

        return "";
    }

    function syncCefDropdownSelectedVisual() {
        // CEF_PATCH_DROPDOWN_VISUAL_SYNC_FIX_20260617
        if (!window.jQuery) {
            return;
        }

        var $ = window.jQuery;
        var selectedMap = getSelectedCefMap();

        $(".select2-container--open .select2-results__option, .cef-selector-select2-dropdown .select2-results__option").each(function() {
            var $option = $(this);
            var value;
            var isSelected;

            if ($option.hasClass("select2-results__message")) {
                return;
            }

            value = getCefValueFromResultOption($option, selectedMap);

            if (!value) {
                $option
                    .removeAttr("data-cef-value")
                    .removeAttr("data-cef-selected")
                    .removeClass("cef-option-selected select2-results__option--selected")
                    .attr("aria-selected", "false");

                $option.find(".cef-result-row").removeClass("cef-result-selected");
                return;
            }

            isSelected = !!selectedMap[value];

            $option.attr("data-cef-value", value)
                .toggleClass("cef-option-selected", isSelected)
                .toggleClass("select2-results__option--selected", isSelected)
                .attr("aria-selected", isSelected ? "true" : "false");

            if (isSelected) {
                $option.attr("data-cef-selected", "1");
            } else {
                $option.removeAttr("data-cef-selected");
            }

            $option.find(".cef-result-row").toggleClass("cef-result-selected", isSelected);
        });
    }

    function scheduleCefDropdownSelectedVisual() {
        syncCefDropdownSelectedVisual();
        window.setTimeout(syncCefDropdownSelectedVisual, 0);
        window.setTimeout(syncCefDropdownSelectedVisual, 25);
        window.setTimeout(syncCefDropdownSelectedVisual, 80);
        window.setTimeout(syncCefDropdownSelectedVisual, 160);
    }

    function installCefDropdownVisualObserver() {
        var target = qs(".select2-container--open .select2-results__options");

        if (syncCefDropdownSelectedVisual._observer) {
            syncCefDropdownSelectedVisual._observer.disconnect();
            syncCefDropdownSelectedVisual._observer = null;
        }

        if (!target || !window.MutationObserver) {
            return;
        }

        syncCefDropdownSelectedVisual._observer = new MutationObserver(function() {
            scheduleCefDropdownSelectedVisual();
        });

        syncCefDropdownSelectedVisual._observer.observe(target, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["aria-selected", "class"]
        });
    }

    function formatCefResult(data) {
        var $row;
        var value;

        if (!data || !data.id) {
            return data && data.text ? data.text : "";
        }

        value = String(data.id || "");
        $row = window.jQuery("<span></span>")
            .addClass("cef-result-row")
            .attr("data-cef-value", value)
            .text(data.text || "");

        if (isCefValueSelected(value)) {
            $row.addClass("cef-result-selected");
        }

        return $row;
    }

    function initCefSelect2() {
        var select = qs("#cefSelectorSelect");
        if (!select) {
            return;
        }

        ensureSelect2(function() {
            var $ = window.jQuery;
            var $select = $("#cefSelectorSelect");

            if (!$select.length) {
                return;
            }

            $select[0].dataset.lastAppliedCefs = cefSelectionKey($select[0]);

            if (!$select.data("select2")) {
                $select.select2({
                    placeholder: "",
                    allowClear: true,
                    closeOnSelect: false,
                    width: "100%",
                    dropdownCssClass: "cef-selector-select2-dropdown",
                    language: {
                        searching: function() { return "Buscando..."; },
                        noResults: function() { return "No se encontraron resultados"; }
                    }
                });

                $select.on("select2:clearing", function() {
                    $(this).data("preventOpen", true);
                });

                $select.on("select2:clear", function() {
                    updateCefPlaceholder();
                    window.setTimeout(submitCefSelectorIfChanged, 0);
                });

                $select.on("select2:opening", function(event) {
                    if ($(this).data("preventOpen")) {
                        event.preventDefault();
                        $(this).removeData("preventOpen");
                    }
                });

                $select.next(".select2-container").on("mousedown", ".select2-selection", function(event) {
                    var instance;
                    if ($(event.target).closest(".select2-selection__clear").length) {
                        return;
                    }
                    instance = $select.data("select2");
                    if (instance && instance.isOpen()) {
                        $select.data("preventOpen", true);
                        $select.select2("close");
                    }
                });

                $select.next(".select2-container").on("keydown paste input", ".select2-selection .select2-search__field", function(event) {
                    event.preventDefault();
                    $(this).val("");
                });

                // CEF_PATCH_DROPDOWN_SELECTED_VISUAL_20260515
                $select.on("select2:open", function() {
                    var $dropdown = $(".select2-dropdown");
                    window.setTimeout(function() {
                        $(".select2-container--open .select2-search--dropdown .select2-search__field")
                            .trigger("focus")
                            .off("input.cefVisual keyup.cefVisual")
                            .on("input.cefVisual keyup.cefVisual", function() {
                                scheduleCefDropdownSelectedVisual();
                            });
                        scheduleCefDropdownSelectedVisual();
                    }, 0);
                    if (!$dropdown.find(".close-select2-btn").length) {
                        $dropdown.append('<div class="close-select2-btn"><i class="fa-solid fa-chevron-up me-1"></i>Ocultar opciones</div>');
                        $dropdown.find(".close-select2-btn").on("click", function() {
                            $select.select2("close");
                        });
                    }
                    scheduleCefDropdownSelectedVisual();
                });
                $select.on("select2:select select2:unselect change", function() {
                    updateCefPlaceholder();

                    scheduleCefDropdownSelectedVisual();

                    if (window.requestAnimationFrame) {
                        window.requestAnimationFrame(scheduleCefDropdownSelectedVisual);
                    }

                    window.setTimeout(scheduleCefDropdownSelectedVisual, 220);
                    window.setTimeout(scheduleCefDropdownSelectedVisual, 360);
                });

                $select.on("select2:close", function() {
                    submitCefSelectorIfChanged();
                });
            }

            updateCefPlaceholder();
        });
    }

    function buildParamsFromForm(form) {
        var formData = new FormData(form);
        var params = new URLSearchParams();

        formData.forEach(function(value, key) {
            if (value !== null && String(value).trim() !== "") {
                params.append(key, value);
            }
        });

        params.delete("formato");
        params.delete("page");
        params.set("page", "1");
        return params;
    }

    function submitCefSelector() {
        var form = qs("#cefSelectorForm");
        if (!form) {
            return;
        }
        clearTimeout(cefSelectorTimer);
        refreshUrl(makeUrl(buildParamsFromForm(form)), { pushHistory: true });
    }

    function scheduleCefSelectorSubmit() {
        clearTimeout(cefSelectorTimer);
        cefSelectorTimer = setTimeout(submitCefSelector, 160);
    }

    function clearCefSelector() {
        var select = qs("#cefSelectorSelect");
        var params = getParams();

        params.delete("establecimientos");
        params.delete("page");
        params.delete("formato");

        if (select) {
            suppressCefChange = true;
            qsa("option", select).forEach(function(option) {
                option.selected = false;
            });
            if (window.jQuery && window.jQuery(select).data("select2")) {
                window.jQuery(select).val(null).trigger("change.select2");
            }
            suppressCefChange = false;
        }

        refreshUrl(makeUrl(params), { pushHistory: true });
    }

    function clearAllFilters() {
        var params = getParams();
        var pageSize = params.get("page_size") || initialPageSize;
        var input = qs("#liveSearchInput");
        var searchSelect = qs("#liveSearchSelect");
        var cefSelect = qs("#cefSelectorSelect");

        ["q", "smart_ui_col", "smart_ui_val", "campo_filtro", "operador_filtro", "valor_filtro", "establecimientos", "cueanexo", "page", "formato"].forEach(function(key) {
            params.delete(key);
        });

        columnsConfig.forEach(function(column) {
            params.delete(column.key);
        });

        if (pageSize) {
            params.set("page_size", pageSize);
        }

        if (input) {
            input.value = "";
        }
        if (searchSelect) {
            searchSelect.value = "all";
        }
        if (cefSelect) {
            suppressCefChange = true;
            if (window.jQuery && window.jQuery(cefSelect).data("select2")) {
                window.jQuery(cefSelect).val(null).trigger("change.select2");
            } else {
                qsa("option", cefSelect).forEach(function(option) {
                    option.selected = false;
                });
            }
            suppressCefChange = false;
            updateCefPlaceholder();
        }

        syncSearchClear();
        refreshUrl(makeUrl(params), { pushHistory: true });
    }

    function hydrateFilterHiddens() {
        var target = qs("#appliedFiltersHidden");
        var params = getParams();
        var campos = params.getAll("campo_filtro");
        var ops = params.getAll("operador_filtro");
        var vals = params.getAll("valor_filtro");

        if (!target) {
            return;
        }

        target.innerHTML = "";
        campos.forEach(function(campo, index) {
            if (!campo || !vals[index]) {
                return;
            }
            target.insertAdjacentHTML("beforeend", '<input type="hidden" name="campo_filtro" value="' + escapeHtml(campo) + '">');
            target.insertAdjacentHTML("beforeend", '<input type="hidden" name="operador_filtro" value="' + escapeHtml(ops[index] || "0") + '">');
            target.insertAdjacentHTML("beforeend", '<input type="hidden" name="valor_filtro" value="' + escapeHtml(vals[index] || "") + '">');
        });
    }

    function removeTripleFilter(params, index) {
        var campos = params.getAll("campo_filtro");
        var ops = params.getAll("operador_filtro");
        var vals = params.getAll("valor_filtro");

        params.delete("campo_filtro");
        params.delete("operador_filtro");
        params.delete("valor_filtro");

        campos.forEach(function(campo, i) {
            if (i === index) {
                return;
            }
            params.append("campo_filtro", campo);
            params.append("operador_filtro", ops[i] || "0");
            params.append("valor_filtro", vals[i] || "");
        });

        params.delete("page");
    }

    function removeExistingFieldFilters(params, field) {
        var campos = params.getAll("campo_filtro");
        var ops = params.getAll("operador_filtro");
        var vals = params.getAll("valor_filtro");

        params.delete("campo_filtro");
        params.delete("operador_filtro");
        params.delete("valor_filtro");

        campos.forEach(function(campo, index) {
            if (campo === field) {
                return;
            }
            params.append("campo_filtro", campo);
            params.append("operador_filtro", ops[index] || "0");
            params.append("valor_filtro", vals[index] || "");
        });
    }

    function normalizeFilterOption(option) {
        var value;
        var label;

        if (option && typeof option === "object") {
            value = String(option.value == null ? option.label || "" : option.value).trim();
            label = String(option.label == null ? value : option.label).trim();
        } else {
            value = String(option == null ? "" : option).trim();
            label = value;
        }

        if (!value || !label) {
            return null;
        }

        return {
            value: value,
            label: label
        };
    }

    function normalizedFilterOptions(field) {
        var seen = {};
        return (filterOptions[field] || []).map(normalizeFilterOption).filter(function(option) {
            var key;
            if (!option) {
                return false;
            }
            key = option.value.toLocaleLowerCase();
            if (seen[key]) {
                return false;
            }
            seen[key] = true;
            return true;
        });
    }

    function activeFilterValuesForField(field) {
        var params = getParams();
        var campos = params.getAll("campo_filtro");
        var vals = params.getAll("valor_filtro");
        var active = {};

        campos.forEach(function(campo, index) {
            var value = vals[index] || "";
            if (campo === field && value) {
                active[value] = true;
            }
        });

        return active;
    }

    function getCefOptionLabel(value) {
        var normalized = String(value || "");
        var option = qs('#cefSelectorSelect option[value="' + escapeCssValue(value) + '"]');
        var nombre = cefOptionsMap[normalized];
        if (nombre) {
            return normalized + " - " + nombre;
        }
        return option ? option.textContent.replace(/\s+/g, " ").trim() : value;
    }

    function getUniqueCefValues(values) {
        // CEF_PATCH_BADGES_INDIVIDUALES_FINAL_20260515
        var seen = {};
        var unique = [];

        (values || []).forEach(function(value) {
            var normalized = String(value || "").trim();
            if (!normalized || seen[normalized]) {
                return;
            }
            seen[normalized] = true;
            unique.push(normalized);
        });

        return unique;
    }

    function removeSingleCefParam(params, value) {
        var targetValue = String(value || "").trim();
        var current = getUniqueCefValues(params.getAll("establecimientos"));

        params.delete("establecimientos");
        current.forEach(function(item) {
            if (String(item) !== targetValue) {
                params.append("establecimientos", item);
            }
        });
        params.delete("page");
        params.delete("formato");
    }

    function summarizeCefs(values) {
        values = getUniqueCefValues(values);
        if (!values.length) {
            return "";
        }
        if (values.length === 1) {
            return getCefOptionLabel(values[0]);
        }
        return values.length + " establecimientos seleccionados";
    }

    function renderBadges() {
        var container = qs("#serverBadgesContainer");
        var params = getParams();
        var html = [];
        var smartField = params.get("smart_ui_col");
        var smartValue = params.get("smart_ui_val");
        var campos = params.getAll("campo_filtro");
        var ops = params.getAll("operador_filtro");
        var vals = params.getAll("valor_filtro");
        // CEF_PATCH_BADGES_UN_TAG_POR_CEF_20260515
        var cefs = getUniqueCefValues(params.getAll("establecimientos"));

        if (!container) {
            return;
        }

        if (params.get("q")) {
            html.push('<span class="server-filter-badge">Búsqueda: ' + escapeHtml(params.get("q")) + '<button type="button" data-remove-param="q"><i class="fa-solid fa-xmark"></i></button></span>');
        }

        if (smartField && smartValue) {
            html.push('<span class="server-filter-badge">Búsqueda rápida en ' + escapeHtml(labelForField(smartField)) + ": " + escapeHtml(smartValue) + '<button type="button" data-remove-smart-search="1"><i class="fa-solid fa-xmark"></i></button></span>');
        }

        // CEF_PATCH_BADGES_FORZAR_INDIVIDUALES_20260515
        cefs.forEach(function(cef) {
            html.push('<span class="server-filter-badge server-filter-badge-cef"><span class="server-filter-badge__text">Estab.: ' + escapeHtml(getCefOptionLabel(cef)) + '</span><button type="button" data-remove-cef-value="' + escapeHtml(cef) + '" title="Quitar este establecimiento"><i class="fa-solid fa-xmark"></i></button></span>');
        });

        campos.forEach(function(campo, index) {
            if (!campo || !vals[index]) {
                return;
            }
            html.push('<span class="server-filter-badge">' + escapeHtml(labelForField(campo)) + " " + escapeHtml(operatorLabels[ops[index] || "0"] || "parecido a") + ": " + escapeHtml(vals[index]) + '<button type="button" data-remove-filter-index="' + index + '"><i class="fa-solid fa-xmark"></i></button></span>');
        });

        container.innerHTML = html.join("");
    }

    function clearHighlights() {
        qsa(".table-padron td.highlight-search").forEach(function(cell) {
            cell.classList.remove("highlight-search");
        });
    }

    function highlightColumnByField(field) {
        var columnClass;

        if (!field || field === "all") {
            return;
        }

        columnClass = fieldToCol(field);
        if (!qs(".table-padron thead th." + columnClass)) {
            return;
        }

        qsa(".table-padron tbody td." + columnClass).forEach(function(cell) {
            cell.classList.add("highlight-search");
        });
    }

    function reapplyHighlights() {
        var params = getParams();
        var campos = params.getAll("campo_filtro");
        var vals = params.getAll("valor_filtro");
        var smartField = params.get("smart_ui_col") || "";
        var smartValue = params.get("smart_ui_val") || "";

        clearHighlights();

        campos.forEach(function(campo, index) {
            if (vals[index]) {
                highlightColumnByField(campo);
            }
        });

        if (smartField && smartValue) {
            highlightColumnByField(smartField);
        }

        columnsConfig.forEach(function(column) {
            if (params.get(column.key)) {
                highlightColumnByField(column.key);
            }
        });
    }

    function scheduleReapplyHighlights() {
        reapplyHighlights();
        window.requestAnimationFrame(function() {
            window.requestAnimationFrame(reapplyHighlights);
        });
    }

    function getPanelToggleButton(panelId) {
        if (panelId === "#pnlFiltros") {
            return qs("#btnToggleFiltros");
        }
        if (panelId === "#pnlColumnas") {
            return qs("#btnToggleColumnas");
        }
        return null;
    }

    function syncPanelToggleState(panelId, isOpen) {
        var button = getPanelToggleButton(panelId);
        var chevron = button ? qs(".toggle-chevron", button) : null;

        if (button) {
            button.classList.toggle("is-active", !!isOpen);
            button.setAttribute("aria-expanded", isOpen ? "true" : "false");
        }

        if (chevron) {
            chevron.classList.toggle("fa-chevron-down", !isOpen);
            chevron.classList.toggle("fa-chevron-up", !!isOpen);
        }
    }

    function closePanel(panelId) {
        var panel = qs(panelId);
        if (!panel) {
            syncPanelToggleState(panelId, false);
            return;
        }

        syncPanelToggleState(panelId, false);
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.slideUp) {
            window.jQuery(panel).stop(true, true).slideUp(130, function() {
                panel.classList.remove("is-open");
                panel.style.display = "";
            });
            return;
        }

        panel.classList.remove("is-open");
    }

    function openPanel(panelId) {
        var panel = qs(panelId);
        if (!panel) {
            syncPanelToggleState(panelId, false);
            return;
        }

        ["#pnlFiltros", "#pnlColumnas"].forEach(function(id) {
            if (id !== panelId) {
                closePanel(id);
            }
        });

        panel.classList.add("is-open");
        syncPanelToggleState(panelId, true);
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.slideDown) {
            window.jQuery(panel).stop(true, true).hide().slideDown(140, function() {
                panel.style.display = "";
            });
        }
    }

    function togglePanel(panelId) {
        var panel = qs(panelId);
        if (!panel) {
            return;
        }

        if (panel.classList.contains("is-open")) {
            closePanel(panelId);
        } else {
            openPanel(panelId);
        }
    }

    function applyColumnVisibility(columnClass, visible) {
        qsa("." + columnClass).forEach(function(cell) {
            cell.style.display = visible ? "" : "none";
        });
    }

    function colInputs() {
        return qsa(".toggle-col");
    }

    function visibleColumnsForExcel() {
        var visible = [];

        colInputs().forEach(function(input) {
            if (input.checked) {
                visible.push(input.dataset.column.replace(/^col-/, "").replace(/-/g, "_"));
            }
        });

        return visible;
    }

    function buildCefExcelExportUrl(formato) {
        var url = formato === "excel_todo"
            ? new URL(window.location.pathname, window.location.origin)
            : new URL(window.location.href);

        url.searchParams.delete("page");
        url.searchParams.delete("visible_col");
        url.searchParams.set("formato", formato);

        if (formato === "excel_pagina") {
            visibleColumnsForExcel().forEach(function(col) {
                url.searchParams.append("visible_col", col);
            });
        }

        return url;
    }

    function syncExcelLinks() {
        var filtros = qs("#btnExcelFiltros");
        var todo = qs("#btnExcelTodo");
        var filtrosUrl;
        var todoUrl;

        if (filtros) {
            filtrosUrl = buildCefExcelExportUrl("excel_pagina");
            filtros.setAttribute("href", filtrosUrl.pathname + filtrosUrl.search);
        }

        if (todo) {
            todoUrl = buildCefExcelExportUrl("excel_todo");
            todo.setAttribute("href", todoUrl.pathname + todoUrl.search);
        }
    }

    function setExcelButtonBusy(button, busy) {
        if (!button) {
            return;
        }
        if (busy) {
            button.dataset.originalHtml = button.innerHTML;
            button.classList.add("disabled");
            button.setAttribute("aria-disabled", "true");
            button.style.pointerEvents = "none";
            button.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin me-1"></i> Generando...';
            return;
        }
        button.classList.remove("disabled");
        button.removeAttribute("aria-disabled");
        button.style.pointerEvents = "";
        if (button.dataset.originalHtml) {
            button.innerHTML = button.dataset.originalHtml;
            delete button.dataset.originalHtml;
        }
    }

    function descargarExcelCef(url, button, filename) {
        setExcelButtonBusy(button, true);
        fetch(url.toString(), {
            method: "GET",
            credentials: "same-origin",
            headers: {
                "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error("No se pudo generar el Excel.");
            }
            return response.blob();
        })
        .then(function(blob) {
            var objectUrl = window.URL.createObjectURL(blob);
            var anchor = document.createElement("a");
            anchor.href = objectUrl;
            anchor.download = filename;
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
            window.setTimeout(function() {
                window.URL.revokeObjectURL(objectUrl);
            }, 250);
        })
        .catch(function(error) {
            console.error("CEF_PATCH_LOCALIZACIONES_UI_EXPORT", error);
            window.alert(error && error.message ? error.message : "No se pudo descargar el Excel.");
        })
        .finally(function() {
            setExcelButtonBusy(button, false);
            syncExcelLinks();
        });
    }

    window.__cefLocalizacionesExcelExport = {
        buildUrl: buildCefExcelExportUrl,
        download: descargarExcelCef
    };

    function updateColumnCounter() {
        var total = colInputs().length;
        var visible = colInputs().filter(function(input) { return input.checked; }).length;
        var label = qs("#colCounterLabel");
        var topLabel = qs("#colCounterTopLabel");
        if (label) {
            label.textContent = visible + "/" + total + " columnas visibles";
        }
        if (topLabel) {
            topLabel.textContent = "Mostrando " + visible + " de " + total + " columnas";
        }
    }

    function totalTableColumns() {
        return columnsConfig.length || qsa(".table-padron thead th").length || 1;
    }

    function emptyRowHtml() {
        return '<tr class="padron-table-empty-row"><td colspan="' + totalTableColumns() + '"><span class="padron-empty-inline"><i class="fa-solid fa-circle-info"></i>Prueba quitando algunos filtros o ajustando la búsqueda para volver a ver resultados.</span></td></tr>';
    }

    function warningColsHtml() {
        return '<tr class="warning-cols"><td colspan="' + totalTableColumns() + '" class="text-start text-muted py-3"><span class="padron-empty-inline"><i class="fa-solid fa-eye-slash"></i>Ha ocultado todas las columnas. Seleccione al menos una columna para ver resultados.</span></td></tr>';
    }

    function syncColumnEmptyStates() {
        var tbody = qs(".table-padron tbody");
        var visible = colInputs().filter(function(input) { return input.checked; }).length;
        var dataRows;

        if (!tbody) {
            return;
        }

        qsa("tr.warning-cols", tbody).forEach(function(row) { row.remove(); });

        if (visible === 0) {
            qsa("tr.padron-table-empty-row", tbody).forEach(function(row) { row.remove(); });
            tbody.insertAdjacentHTML("beforeend", warningColsHtml());
            return;
        }

        dataRows = qsa("tr", tbody).filter(function(row) {
            return !row.classList.contains("warning-cols") && !row.classList.contains("padron-table-empty-row");
        });

        if (!dataRows.length && !qs("tr.padron-table-empty-row", tbody)) {
            tbody.insertAdjacentHTML("beforeend", emptyRowHtml());
        }
    }

    function syncColumns() {
        colInputs().forEach(function(input) {
            var key = "cef_localizaciones_" + input.dataset.column;
            var stored = localStorage.getItem(key);
            if (stored !== null) {
                input.checked = stored === "true";
            }
            applyColumnVisibility(input.dataset.column, input.checked);
        });
        syncExcelLinks();
        updateColumnCounter();
        syncColumnEmptyStates();
    }

    function setAllColumns(checked) {
        colInputs().forEach(function(input) {
            input.checked = checked;
            localStorage.setItem("cef_localizaciones_" + input.dataset.column, checked ? "true" : "false");
            applyColumnVisibility(input.dataset.column, checked);
        });
        syncExcelLinks();
        updateColumnCounter();
        syncColumnEmptyStates();
        queueContractedTableLayout();
    }

    function setDefaultColumns() {
        colInputs().forEach(function(input) {
            var checked = defaultCols[input.dataset.column] !== false;
            input.checked = checked;
            localStorage.setItem("cef_localizaciones_" + input.dataset.column, checked ? "true" : "false");
            applyColumnVisibility(input.dataset.column, checked);
        });
        syncExcelLinks();
        updateColumnCounter();
        syncColumnEmptyStates();
        queueContractedTableLayout();
    }

    function fieldToCol(field) {
        return "col-" + String(field || "").replace(/_/g, "-");
    }

    function ensureColumnByField(field) {
        var column = fieldToCol(field);
        var input = qs('.toggle-col[data-column="' + column + '"]');
        if (input && !input.checked) {
            input.checked = true;
            localStorage.setItem("cef_localizaciones_" + input.dataset.column, "true");
            applyColumnVisibility(input.dataset.column, true);
        }
    }

    function ensureActiveColumns() {
        var params = getParams();
        params.getAll("campo_filtro").forEach(ensureColumnByField);
        if (params.get("smart_ui_col")) {
            ensureColumnByField(params.get("smart_ui_col"));
        }
        syncExcelLinks();
        updateColumnCounter();
        syncColumnEmptyStates();
    }

    function getContractedMode() {
        return localStorage.getItem("cef_localizaciones_contraida") === "true";
    }

    function getTableViewport() {
        var shell = qs(".table-shell");
        return shell ? qs(".table-responsive", shell) : null;
    }

    function ensureCompactTableTrack() {
        var viewport = getTableViewport();
        var track;
        var table;

        if (!viewport) {
            return null;
        }

        track = qs(".compact-table-track", viewport);
        table = qs(".table-padron", viewport);

        if (!track && table) {
            track = document.createElement("div");
            track.className = "compact-table-track";
            table.parentNode.insertBefore(track, table);
            track.appendChild(table);
        }

        return track;
    }

    function setContractedButtonState(active) {
        var btn = qs("#btnContraerTabla");

        if (btn) {
            btn.classList.toggle("is-active", !!active);
            btn.setAttribute("aria-pressed", active ? "true" : "false");
            btn.setAttribute("title", active ? "Volver al tamaño normal de la tabla" : "Ajustar la tabla al ancho visible");
            btn.innerHTML = active ? '<i class="fa-solid fa-expand me-1"></i>Expandir Columnas' : '<i class="fa-solid fa-compress me-1"></i>Contraer Columnas';
        }
    }

    function applyContractedTableLayout(options) {
        var minScale = 0.82;
        var opts = options || {};
        var active = getContractedMode();
        var viewport = getTableViewport();
        var track;
        var table;
        var naturalWidth;
        var viewportWidth;
        var scale;
        var scaledWidth;

        function resetTableStyles(tableNode) {
            if (!tableNode) {
                return;
            }

            tableNode.style.removeProperty("transform");
            tableNode.style.removeProperty("transform-origin");
            tableNode.style.removeProperty("will-change");
            tableNode.style.removeProperty("width");
            tableNode.style.removeProperty("min-width");
        }

        function unwrapCompactTrack() {
            var currentTrack;
            var currentTable;

            if (!viewport) {
                return null;
            }

            currentTrack = qs(".compact-table-track", viewport);

            if (!currentTrack) {
                return qs(".table-padron", viewport);
            }

            currentTable = qs(".table-padron", currentTrack);

            if (currentTable) {
                currentTrack.parentNode.insertBefore(currentTable, currentTrack);
            }

            currentTrack.parentNode.removeChild(currentTrack);

            return currentTable || qs(".table-padron", viewport);
        }

        setContractedButtonState(active);

        if (!viewport) {
            return;
        }

        viewport.classList.toggle("compact-instant", !!opts.instant);
        viewport.classList.remove("is-contracted");
        viewport.style.overflowX = "auto";
        viewport.style.height = "";
        viewport.style.minHeight = "";

        /*
        * Importante:
        * Si NO está activo "Contraer Columnas", no envolvemos la tabla.
        * Antes se creaba compact-table-track siempre, incluso con el botón apagado,
        * y eso causaba un salto visual al cargar la página.
        */
        if (!active) {
            table = unwrapCompactTrack();
            resetTableStyles(table);
            return;
        }

        track = ensureCompactTableTrack();
        table = track ? qs(".table-padron", track) : null;

        if (track) {
            track.style.removeProperty("width");
            track.style.removeProperty("min-width");
            track.style.removeProperty("overflow");
        }

        resetTableStyles(table);

        if (!track || !table) {
            return;
        }

        viewport.classList.add("is-contracted");

        naturalWidth = Math.max(
            table.scrollWidth || 0,
            table.offsetWidth || 0,
            Math.ceil(table.getBoundingClientRect().width || 0)
        );

        viewportWidth = Math.max(
            viewport.clientWidth || 0,
            Math.ceil(viewport.getBoundingClientRect().width || 0)
        );

        if (!naturalWidth || !viewportWidth) {
            return;
        }

        scale = Math.max(minScale, Math.min(1, viewportWidth / naturalWidth));
        scaledWidth = Math.max(viewportWidth, Math.ceil(naturalWidth * scale));

        track.style.setProperty("width", scaledWidth + "px", "important");
        track.style.setProperty("min-width", scaledWidth + "px", "important");
        track.style.setProperty("overflow", "hidden");

        table.style.setProperty("width", naturalWidth + "px", "important");
        table.style.setProperty("min-width", naturalWidth + "px", "important");
        table.style.setProperty("transform", "scaleX(" + scale.toFixed(4) + ")");
        table.style.setProperty("transform-origin", "top left");
        table.style.setProperty("will-change", "transform");
    }

    function queueContractedTableLayout(options) {
        var opts = options || {};

        if (opts.instant) {
            applyContractedTableLayout(opts);
            return;
        }

        window.requestAnimationFrame(function() {
            window.requestAnimationFrame(function() {
                applyContractedTableLayout(opts);
            });
        });
    }

    function setContracted(active, options) {
        localStorage.setItem("cef_localizaciones_contraida", active ? "true" : "false");
        queueContractedTableLayout(options);
    }

    function syncSearchClear() {
        var input = qs("#liveSearchInput");
        var clear = qs("#liveSearchClear");
        if (!clear || !input) {
            return;
        }

        clear.classList.toggle("is-visible", Boolean(input.value.trim()));
    }

    function applyLiveSearch(replaceHistory, trigger) {
        var input = qs("#liveSearchInput");
        var select = qs("#liveSearchSelect");
        var params = getParams();
        var value = input ? input.value.trim() : "";
        var field = select ? select.value : "all";

        params.delete("q");
        params.delete("smart_ui_col");
        params.delete("smart_ui_val");
        params.delete("page");
        params.delete("formato");

        if (value) {
            if (field && field !== "all") {
                params.set("smart_ui_col", field);
                params.set("smart_ui_val", value);
            } else {
                params.set("q", value);
            }
        }

        refreshUrl(makeUrl(params), { replaceHistory: !!replaceHistory, trigger: trigger || input || select });
    }

    function clearLiveSearch(trigger) {
        var input = qs("#liveSearchInput");
        var params = getParams();
        if (input) {
            input.value = "";
        }
        params.delete("q");
        params.delete("smart_ui_col");
        params.delete("smart_ui_val");
        params.delete("page");
        params.delete("formato");
        syncSearchClear();
        refreshUrl(makeUrl(params), { pushHistory: true, trigger: trigger || input || qs("#liveSearchClear") });
    }

    function getTableSortState() {
        var params = getParams();
        var orden = (params.get("orden") || "").trim();
        var descending = orden.charAt(0) === "-";
        var field = descending ? orden.slice(1) : orden;
        return {
            field: field,
            descending: descending && !!field
        };
    }

    function buildTableSortUrl(field) {
        var params = getParams();
        var state = getTableSortState();

        if (!field) {
            return makeUrl(params);
        }

        if (state.field === field && !state.descending) {
            params.set("orden", "-" + field);
        } else if (state.field === field && state.descending) {
            params.delete("orden");
        } else {
            params.set("orden", field);
        }

        return makeUrl(params);
    }

    function syncTableSortHeaders() {
        var state = getTableSortState();

        qsa(".table-padron thead th[data-dbcol]").forEach(function(th) {
            var field = th.dataset.dbcol || "";
            var link = qs("a", th);
            var indicator = link ? qs(".sort-indicator", link) : null;
            var active = field && state.field === field;

            th.setAttribute("aria-sort", active ? (state.descending ? "descending" : "ascending") : "none");

            if (!link) {
                return;
            }

            link.href = buildTableSortUrl(field);

            if (!indicator) {
                indicator = document.createElement("span");
                indicator.className = "sort-indicator";
                indicator.setAttribute("aria-hidden", "true");
                link.appendChild(indicator);
            }

            indicator.textContent = active ? (state.descending ? "\u25BC" : "\u25B2") : "";
            indicator.hidden = !active;
        });
    }

    document.addEventListener("DOMContentLoaded", syncTableSortHeaders);

    function openFilterDialog(field, label) {
        var modalEl = qs("#dialog_filtro");
        var title = qs("#dialogFiltroLabel");
        var fieldInput = qs("#filterField");
        var valueInput = qs("#filterValue");
        var operatorSelect = qs("#filterOperator");
        var manualColumn = qs("#filterManualGroup");
        var list = qs("#filterOptionsList");
        var options = normalizedFilterOptions(field);
        var activeValues = activeFilterValuesForField(field);

        if (!modalEl || !fieldInput || !list) {
            return;
        }

        fieldInput.value = field;
        if (title) {
            title.innerHTML = '<i class="fa-solid fa-filter me-2 text-primary"></i>Agregar Filtro: ' + escapeHtml(label);
        }
        if (operatorSelect && checklistFilterFields[field]) {
            operatorSelect.value = "2";
        } else if (operatorSelect) {
            operatorSelect.value = "0";
        }
        if (valueInput) {
            valueInput.value = "";
        }
        if (manualColumn) {
            manualColumn.style.display = checklistFilterFields[field] ? "none" : "";
        }

        if (options.length) {
            list.innerHTML = '<div class="filter-dialog-checklist-grid">' + options.map(function(option, index) {
                var id = "filterOption_" + field + "_" + index;
                var checked = activeValues[option.value] ? " checked" : "";
                return '<label class="filter-dialog-check" for="' + id + '"><input id="' + id + '" class="form-check-input filter-dialog-option" type="checkbox" value="' + escapeHtml(option.value) + '" data-label="' + escapeHtml(option.label) + '"' + checked + '><span>' + escapeHtml(option.label) + "</span></label>";
            }).join("") + "</div>";
        } else {
            list.innerHTML = '<div class="text-muted small">Sin opciones precargadas para este campo. Usa el valor manual.</div>';
            if (manualColumn) {
                manualColumn.style.display = "";
            }
        }

        showCefModal(modalEl);
    }

    function applyFilterDialog() {
        var fieldEl = qs("#filterField");
        var opEl = qs("#filterOperator");
        var valueEl = qs("#filterValue");
        var params = getParams();
        var field = fieldEl ? fieldEl.value : "";
        var operator = opEl ? opEl.value || "0" : "0";
        var manual = valueEl ? valueEl.value.trim() : "";
        var values = qsa(".filter-dialog-option:checked").map(function(input) { return input.value; });
        var modalEl = qs("#dialog_filtro");

        if (!values.length && manual) {
            values.push(manual);
        }

        if (!field || !values.length) {
            return;
        }

        if (checklistFilterFields[field]) {
            removeExistingFieldFilters(params, field);
        }

        values.forEach(function(value) {
            params.append("campo_filtro", field);
            params.append("operador_filtro", operator);
            params.append("valor_filtro", value);
        });

        params.delete("page");
        params.delete("formato");

        hideCefModal(modalEl);

        refreshUrl(makeUrl(params), { pushHistory: true });
    }

    document.addEventListener("submit", function(event) {
        var selectorForm = closest(event.target, "#cefSelectorForm");
        var filterForm = closest(event.target, "#filterForm");

        if (selectorForm) {
            event.preventDefault();
            event.stopPropagation();
            submitCefSelector();
            return;
        }

        if (filterForm) {
            event.preventDefault();
            event.stopPropagation();
            refreshUrl(makeUrl(buildParamsFromForm(filterForm)), { pushHistory: true });
        }
    }, true);

    document.addEventListener("click", function(event) {
        var target = event.target;
        var params;
        var link = closest(target, "a");
        var columnCard = closest(target, "#pnlColumnas .form-check");
        var input;

        if (closest(target, "#btnExcelFiltros")) {
            event.__cefLocalizacionesHandled = true;
            event.preventDefault();
            descargarExcelCef(buildCefExcelExportUrl("excel_pagina"), closest(target, "#btnExcelFiltros"), "localizaciones_cef_filtros.xlsx");
            return;
        }

        if (closest(target, "#btnExcelTodo")) {
            event.__cefLocalizacionesHandled = true;
            event.preventDefault();
            descargarExcelCef(buildCefExcelExportUrl("excel_todo"), closest(target, "#btnExcelTodo"), "localizaciones_cef_todo.xlsx");
            return;
        }

        if (closest(target, "#btnToggleFiltros")) {
            event.__cefLocalizacionesHandled = true;
            event.preventDefault();
            togglePanel("#pnlFiltros");
            return;
        }

        if (closest(target, "#btnToggleColumnas")) {
            event.__cefLocalizacionesHandled = true;
            event.preventDefault();
            togglePanel("#pnlColumnas");
            return;
        }

        if (closest(target, "#btnGuiaUso")) {
            event.__cefLocalizacionesHandled = true;
            event.preventDefault();
            openGuideModal();
            return;
        }

        if (closest(target, "#btnContraerTabla")) {
            event.__cefLocalizacionesHandled = true;
            event.preventDefault();
            setContracted(!getContractedMode());
            return;
        }

        if (closest(target, "#btnRestaurarCols")) {
            event.preventDefault();
            setAllColumns(true);
            return;
        }

        if (closest(target, "#btnOcultarCols")) {
            event.preventDefault();
            setAllColumns(false);
            return;
        }

        if (closest(target, "#btnPorDefectoCols")) {
            event.preventDefault();
            setDefaultColumns();
            return;
        }

        if (closest(target, ".cef-selector-clear")) {
            event.preventDefault();
            clearCefSelector();
            return;
        }

        if (closest(target, "#liveSearchClear")) {
            event.preventDefault();
            clearLiveSearch(closest(target, "#liveSearchClear"));
            return;
        }

        if (closest(target, "#btnClearFilters")) {
            event.preventDefault();
            clearAllFilters();
            return;
        }

        if (closest(target, "#btnApplyFilterDialog")) {
            event.__cefLocalizacionesHandled = true;
            event.preventDefault();
            applyFilterDialog();
            return;
        }

        if (closest(target, "#dialog_filtro [data-bs-dismiss], #dialog_filtro .btn-close")) {
            event.__cefLocalizacionesHandled = true;
            event.preventDefault();
            hideCefModal(qs("#dialog_filtro"));
            return;
        }

        if (closest(target, "#guiaUsoModal [data-bs-dismiss], #guiaUsoModal .btn-close")) {
            event.__cefLocalizacionesHandled = true;
            event.preventDefault();
            hideCefModal(qs("#guiaUsoModal"));
            return;
        }

        if (target === qs("#dialog_filtro")) {
            event.__cefLocalizacionesHandled = true;
            hideCefModal(qs("#dialog_filtro"));
            return;
        }

        if (target === qs("#guiaUsoModal")) {
            event.__cefLocalizacionesHandled = true;
            hideCefModal(qs("#guiaUsoModal"));
            return;
        }

        if (closest(target, ".filter-btn-field")) {
            event.__cefLocalizacionesHandled = true;
            event.preventDefault();
            openFilterDialog(target.closest(".filter-btn-field").dataset.field, target.closest(".filter-btn-field").dataset.label || target.textContent.trim());
            return;
        }

        if (closest(target, "#serverBadgesContainer button")) {
            event.preventDefault();
            params = getParams();

            if (closest(target, "[data-remove-smart-search]")) {
                params.delete("smart_ui_col");
                params.delete("smart_ui_val");
                params.delete("q");
                params.delete("page");
                refreshUrl(makeUrl(params), { pushHistory: true });
                return;
            }

            if (closest(target, "[data-remove-param]")) {
                params.delete(closest(target, "[data-remove-param]").dataset.removeParam);
                params.delete("page");
                refreshUrl(makeUrl(params), { pushHistory: true });
                return;
            }

            if (closest(target, "[data-remove-cef-value]")) {
                removeSingleCefParam(params, closest(target, "[data-remove-cef-value]").dataset.removeCefValue);
                refreshUrl(makeUrl(params), { pushHistory: true });
                return;
            }

            if (closest(target, "[data-remove-establecimientos]")) {
                params.delete("establecimientos");
                params.delete("page");
                params.delete("formato");
                refreshUrl(makeUrl(params), { pushHistory: true });
                return;
            }

            if (closest(target, "[data-remove-filter-index]")) {
                removeTripleFilter(params, parseInt(closest(target, "[data-remove-filter-index]").dataset.removeFilterIndex, 10));
                refreshUrl(makeUrl(params), { pushHistory: true });
                return;
            }
        }

        if (columnCard && !closest(target, "input, label, button, a")) {
            input = qs(".toggle-col", columnCard);
            if (input) {
                event.preventDefault();
                input.checked = !input.checked;
                input.dispatchEvent(new Event("change", { bubbles: true }));
            }
            return;
        }

        if (link && link.closest("#pagination-container")) {
            event.preventDefault();
            refreshUrl(link.href, { pushHistory: true, trigger: link });
            return;
        }

        if (link && link.closest(".table-padron thead")) {
            event.preventDefault();
            refreshUrl(buildTableSortUrl(link.closest("th") ? link.closest("th").dataset.dbcol : ""), { pushHistory: true, trigger: link });
            return;
        }

    }, true);

    document.addEventListener("change", function(event) {
        var target = event.target;
        var params;

        if (target.matches("#cefSelectorSelect")) {
            updateCefPlaceholder();
            return;
        }

        if (target.matches(".toggle-col")) {
            localStorage.setItem("cef_localizaciones_" + target.dataset.column, target.checked ? "true" : "false");
            applyColumnVisibility(target.dataset.column, target.checked);
            syncExcelLinks();
            updateColumnCounter();
            syncColumnEmptyStates();
            queueContractedTableLayout();
            return;
        }

        if (target.matches("#pageSizeSelector, #pageSizeSelectorMain")) {
            params = getParams();
            params.set("page_size", target.value);
            params.delete("page");
            params.delete("formato");
            refreshUrl(makeUrl(params), { pushHistory: true, trigger: target });
            return;
        }

        if (target.matches("#liveSearchSelect") && qs("#liveSearchInput") && qs("#liveSearchInput").value.trim()) {
            applyLiveSearch(false, target);
        }
    }, true);

    document.addEventListener("input", function(event) {
        if (!event.target.matches("#liveSearchInput")) {
            return;
        }

        syncSearchClear();
        clearTimeout(liveSearchTimer);
        liveSearchTimer = setTimeout(function() {
            applyLiveSearch(true, event.target);
        }, 280);
    }, true);

    document.addEventListener("keydown", function(event) {
        if (event.target.matches("#liveSearchInput") && event.key === "Enter") {
            event.preventDefault();
            clearTimeout(liveSearchTimer);
            applyLiveSearch(false, event.target);
        }
    }, true);

    window.addEventListener("resize", function() {
        queueContractedTableLayout();
    });

    window.addEventListener("popstate", function() {
        refreshUrl(window.location.href, { pushHistory: false, force: true });
    });

    function boot() {
        bindDirectUiHandlers();
        loadCefOptionsFromDom();
        loadFilterOptionsFromDom();
        hydrateFilterHiddens();
        renderBadges();
        syncColumns();
        ensureActiveColumns();
        syncSearchClear();
        initCefSelect2();
        initCefPagination();
        queueContractedTableLayout({ instant: true });
        scheduleReapplyHighlights();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();

(function() {
    "use strict";

    if (window.__CEF_LOCALIZACIONES_CHROME_FALLBACK__) {
        return;
    }
    window.__CEF_LOCALIZACIONES_CHROME_FALLBACK__ = true;

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function getPanelToggleButton(selector) {
        if (selector === "#pnlFiltros") {
            return qs("#btnToggleFiltros");
        }
        if (selector === "#pnlColumnas") {
            return qs("#btnToggleColumnas");
        }
        return null;
    }

    function syncPanelToggleState(selector, isOpen) {
        var button = getPanelToggleButton(selector);
        var chevron = button ? qs(".toggle-chevron", button) : null;

        if (button) {
            button.classList.toggle("is-active", !!isOpen);
            button.setAttribute("aria-expanded", isOpen ? "true" : "false");
        }

        if (chevron) {
            chevron.classList.toggle("fa-chevron-down", !isOpen);
            chevron.classList.toggle("fa-chevron-up", !!isOpen);
        }
    }

    function closePanel(selector) {
        var panel = qs(selector);
        syncPanelToggleState(selector, false);
        if (!panel) {
            return;
        }
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.slideUp) {
            window.jQuery(panel).stop(true, true).slideUp(130, function() {
                panel.classList.remove("is-open");
                panel.style.display = "";
            });
            return;
        }
        panel.classList.remove("is-open");
    }

    function openPanel(selector) {
        var panel = qs(selector);
        if (!panel) {
            syncPanelToggleState(selector, false);
            return;
        }
        ["#pnlFiltros", "#pnlColumnas"].forEach(function(id) {
            if (id !== selector) {
                closePanel(id);
            }
        });
        panel.classList.add("is-open");
        syncPanelToggleState(selector, true);
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.slideDown) {
            window.jQuery(panel).stop(true, true).hide().slideDown(140, function() {
                panel.style.display = "";
            });
        }
    }

    function togglePanel(selector) {
        var panel = qs(selector);
        if (!panel) {
            return;
        }
        if (panel.classList.contains("is-open")) {
            closePanel(selector);
        } else {
            openPanel(selector);
        }
    }

    function showModal(modalEl) {
        if (!modalEl) {
            return;
        }
        if (modalEl.classList.contains("filter-dialog")) {
            modalEl.classList.add("is-visible");
            modalEl.setAttribute("aria-hidden", "false");
            document.body.classList.add("modal-open");
            return;
        }
        if (window.bootstrap && window.bootstrap.Modal) {
            try {
                window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
                return;
            } catch (error) {}
        }
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.modal) {
            try {
                window.jQuery(modalEl).modal("show");
                return;
            } catch (error) {}
        }
        modalEl.style.display = "block";
        modalEl.removeAttribute("aria-hidden");
        modalEl.setAttribute("aria-modal", "true");
        modalEl.setAttribute("role", "dialog");
        modalEl.classList.add("show");
        document.body.classList.add("modal-open");
    }

    function openGuideModal() {
        showModal(qs("#guiaUsoModal"));
    }

    function closeModal(modalEl) {
        if (!modalEl) {
            return;
        }
        if (modalEl.classList.contains("filter-dialog")) {
            modalEl.classList.remove("is-visible");
            modalEl.setAttribute("aria-hidden", "true");
            document.body.classList.remove("modal-open");
            return;
        }
        modalEl.classList.remove("show");
        modalEl.style.display = "none";
        modalEl.setAttribute("aria-hidden", "true");
        modalEl.removeAttribute("aria-modal");
        modalEl.removeAttribute("role");
        document.body.classList.remove("modal-open");
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function fallbackFilterOptions(field) {
        var data = qs("#cefFilterOptionsData");
        var parsed = {};
        try {
            parsed = JSON.parse(data ? data.textContent || "{}" : "{}") || {};
        } catch (error) {
            parsed = {};
        }
        return (parsed[field] || []).filter(Boolean);
    }

    function openFilterDialog(button) {
        var field = button ? button.getAttribute("data-field") : "";
        var label = button ? button.getAttribute("data-label") || button.textContent.trim() : field;
        var modalEl = qs("#dialog_filtro");
        var title = qs("#dialogFiltroLabel");
        var fieldInput = qs("#filterField");
        var operator = qs("#filterOperator");
        var valueInput = qs("#filterValue");
        var manualColumn = qs("#filterManualGroup");
        var list = qs("#filterOptionsList");
        var options = fallbackFilterOptions(field);

        if (!modalEl || !fieldInput || !list) {
            return;
        }

        fieldInput.value = field;
        if (title) {
            title.innerHTML = '<i class="fa-solid fa-filter me-2 text-primary"></i>Agregar Filtro: ' + escapeHtml(label);
        }
        if (operator) {
            operator.value = ["region_loc", "localidad", "departamento"].indexOf(field) >= 0 ? "2" : "0";
        }
        if (valueInput) {
            valueInput.value = "";
        }
        if (manualColumn) {
            manualColumn.style.display = ["region_loc", "localidad", "departamento"].indexOf(field) >= 0 ? "none" : "";
        }
        list.innerHTML = options.length
            ? '<div class="filter-dialog-checklist-grid">' + options.map(function(option, index) {
                var value = typeof option === "object" ? option.value || option.label || "" : option;
                var text = typeof option === "object" ? option.label || value : value;
                return '<label class="filter-dialog-check" for="fallbackFilterOption_' + index + '"><input id="fallbackFilterOption_' + index + '" class="form-check-input filter-dialog-option" type="checkbox" value="' + escapeHtml(value) + '"><span>' + escapeHtml(text) + '</span></label>';
            }).join("") + "</div>"
            : '<div class="text-muted small">Sin opciones precargadas para este campo. Usa el valor manual.</div>';

        showModal(modalEl);
    }

    function applyFilterDialog() {
        var fieldEl = qs("#filterField");
        var operatorEl = qs("#filterOperator");
        var valueEl = qs("#filterValue");
        var field = fieldEl ? fieldEl.value : "";
        var operator = operatorEl ? operatorEl.value || "0" : "0";
        var manual = valueEl ? valueEl.value.trim() : "";
        var values = Array.prototype.slice.call(document.querySelectorAll(".filter-dialog-option:checked")).map(function(input) {
            return input.value;
        });
        var params = new URLSearchParams(window.location.search);

        if (!values.length && manual) {
            values.push(manual);
        }
        if (!field || !values.length) {
            return;
        }

        values.forEach(function(value) {
            params.append("campo_filtro", field);
            params.append("operador_filtro", operator);
            params.append("valor_filtro", value);
        });
        params.delete("page");
        params.delete("formato");
        window.location.href = window.location.pathname + (params.toString() ? "?" + params.toString() : "");
    }

    function toggleContractedFallback() {
        var viewport = qs(".table-shell .table-responsive");
        var button = qs("#btnContraerTabla");
        var active = localStorage.getItem("cef_localizaciones_contraida") !== "true";

        localStorage.setItem("cef_localizaciones_contraida", active ? "true" : "false");
        if (viewport) {
            viewport.classList.toggle("is-contracted", active);
        }
        if (button) {
            button.classList.toggle("is-active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
            button.innerHTML = active
                ? '<i class="fa-solid fa-expand me-1"></i>Expandir Columnas'
                : '<i class="fa-solid fa-compress me-1"></i>Contraer Columnas';
        }
    }

    document.addEventListener("click", function(event) {
        var target = event.target;

        if (event.__cefLocalizacionesHandled || !target || !target.closest) {
            return;
        }

        if (target.closest("#btnExcelFiltros") && window.__cefLocalizacionesExcelExport) {
            event.preventDefault();
            window.__cefLocalizacionesExcelExport.download(
                window.__cefLocalizacionesExcelExport.buildUrl("excel_pagina"),
                target.closest("#btnExcelFiltros"),
                "localizaciones_cef_filtros.xlsx"
            );
            return;
        }

        if (target.closest("#btnExcelTodo") && window.__cefLocalizacionesExcelExport) {
            event.preventDefault();
            window.__cefLocalizacionesExcelExport.download(
                window.__cefLocalizacionesExcelExport.buildUrl("excel_todo"),
                target.closest("#btnExcelTodo"),
                "localizaciones_cef_todo.xlsx"
            );
            return;
        }

        if (target.closest("#btnToggleFiltros")) {
            event.preventDefault();
            togglePanel("#pnlFiltros");
            return;
        }

        if (target.closest("#btnToggleColumnas")) {
            event.preventDefault();
            togglePanel("#pnlColumnas");
            return;
        }

        if (target.closest("#btnGuiaUso")) {
            event.preventDefault();
            openGuideModal();
            return;
        }

        if (target.closest("#btnApplyFilterDialog")) {
            event.preventDefault();
            applyFilterDialog();
            return;
        }

        if (target.closest(".filter-btn-field")) {
            event.preventDefault();
            openFilterDialog(target.closest(".filter-btn-field"));
            return;
        }

        if (target.closest("#dialog_filtro [data-bs-dismiss], #dialog_filtro .btn-close")) {
            event.preventDefault();
            closeModal(qs("#dialog_filtro"));
            return;
        }

        if (target.closest("#guiaUsoModal [data-bs-dismiss], #guiaUsoModal .btn-close")) {
            event.preventDefault();
            closeModal(qs("#guiaUsoModal"));
            return;
        }

        if (target.closest("#btnContraerTabla")) {
            event.preventDefault();
            toggleContractedFallback();
        }
    }, true);
})();
