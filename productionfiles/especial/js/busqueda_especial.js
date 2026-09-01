(function () {
    "use strict";

    var DEBOUNCE_MS = 280;

    function searchControls(root) {
        var scope = root && root.querySelectorAll ? root : document;
        var controls = [];
        if (root && root.matches && root.matches("[data-especial-search]")) {
            controls.push(root);
        }
        if (scope.querySelectorAll) {
            Array.prototype.push.apply(
                controls,
                scope.querySelectorAll("[data-especial-search]")
            );
        }
        return controls;
    }

    function selectedOption(field) {
        if (!field || !field.options || field.selectedIndex < 0) return null;
        return field.options[field.selectedIndex] || null;
    }

    function readTerm(control) {
        var input = control && control.querySelector("[data-especial-search-input]");
        return input ? String(input.value || "").trim() : "";
    }

    function readConfig(control) {
        var field = control.querySelector("[data-especial-search-field]");
        var input = control.querySelector("[data-especial-search-input]");
        var resetParams = (control.getAttribute("data-especial-search-reset-params") || "")
            .split(",")
            .map(function (param) { return param.trim(); })
            .filter(Boolean);
        return {
            fieldParam: control.getAttribute("data-especial-search-field-param") || (field && field.name) || "field",
            termParam: control.getAttribute("data-especial-search-term-param") || (input && input.name) || "q",
            viewParam: control.getAttribute("data-especial-search-view-param") || "",
            view: control.getAttribute("data-especial-search-view") || "",
            pageParam: control.getAttribute("data-especial-search-page-param") || "page",
            resultsSelector: control.getAttribute("data-especial-search-results-selector") || "",
            resetParams: resetParams
        };
    }

    function updatePlaceholder(control) {
        var field = control && control.querySelector("[data-especial-search-field]");
        var input = control && control.querySelector("[data-especial-search-input]");
        var option = selectedOption(field);
        if (!field || !input) return;
        var placeholder = option && option.getAttribute("data-placeholder");
        placeholder = placeholder
            || input.getAttribute("data-especial-search-default-placeholder")
            || input.getAttribute("placeholder")
            || "Buscar...";
        input.placeholder = placeholder;
        input.setAttribute("aria-label", placeholder);
    }

    function buildSearchUrl(control) {
        var field = control.querySelector("[data-especial-search-field]");
        var config = readConfig(control);
        var url = new URL(window.location.href);
        var criterion = field ? field.value : "";
        var term = readTerm(control);

        if (config.viewParam && config.view) {
            url.searchParams.set(config.viewParam, config.view);
        }
        if (config.pageParam) url.searchParams.set(config.pageParam, "1");
        config.resetParams.forEach(function (param) {
            url.searchParams.delete(param);
        });
        if (term) {
            url.searchParams.set(config.fieldParam, criterion);
            url.searchParams.set(config.termParam, term);
        } else {
            url.searchParams.delete(config.fieldParam);
            url.searchParams.delete(config.termParam);
        }
        return url;
    }

    function isCurrentUrl(url) {
        return url.pathname === window.location.pathname
            && url.search === window.location.search;
    }

    function syncStateLinks(control, url, config) {
        control.querySelectorAll("[data-especial-search-state-link]").forEach(function (link) {
            var linkUrl = new URL(link.href, window.location.href);
            if (url.searchParams.has(config.termParam)) {
                linkUrl.searchParams.set(
                    config.fieldParam,
                    url.searchParams.get(config.fieldParam) || ""
                );
                linkUrl.searchParams.set(
                    config.termParam,
                    url.searchParams.get(config.termParam) || ""
                );
            } else {
                linkUrl.searchParams.delete(config.fieldParam);
                linkUrl.searchParams.delete(config.termParam);
            }
            if (config.pageParam) linkUrl.searchParams.set(config.pageParam, "1");
            config.resetParams.forEach(function (param) {
                linkUrl.searchParams.delete(param);
            });
            link.href = linkUrl.toString();
        });
    }

    function navigate(control, url) {
        var config = readConfig(control);
        if (isCurrentUrl(url)) return;
        syncStateLinks(control, url, config);
        if (
            window.EspecialPartialNavigation
            && typeof window.EspecialPartialNavigation.navigate === "function"
        ) {
            window.EspecialPartialNavigation.navigate(url, "replace", {
                targetSelector: config.resultsSelector
            });
            return;
        }
        window.location.replace(url.toString());
    }

    function applySearch(control) {
        control._especialSearchHasActiveTerm = Boolean(readTerm(control));
        navigate(control, buildSearchUrl(control));
    }

    function schedule(control) {
        if (control._especialSearchTimer) {
            window.clearTimeout(control._especialSearchTimer);
            control._especialSearchTimer = null;
        }
        var term = readTerm(control);
        if (!term && !control._especialSearchHasActiveTerm) return;
        control._especialSearchTimer = window.setTimeout(function () {
            control._especialSearchTimer = null;
            applySearch(control);
        }, DEBOUNCE_MS);
    }

    function initControl(control) {
        if (!control || control.dataset.especialSearchReady === "1") return;
        var field = control.querySelector("[data-especial-search-field]");
        var input = control.querySelector("[data-especial-search-input]");
        if (!field || !input) return;

        control.dataset.especialSearchReady = "1";
        control._especialSearchHasActiveTerm = Boolean(readTerm(control));
        control._especialSearchOnFieldChange = function () {
            updatePlaceholder(control);
            if (readTerm(control)) schedule(control);
        };
        control._especialSearchOnInput = function () {
            schedule(control);
        };
        control._especialSearchOnClick = function (event) {
            var clear = event.target.closest("[data-especial-search-clear]");
            if (!clear || !control.contains(clear)) return;
            event.preventDefault();
            if (control._especialSearchTimer) {
                window.clearTimeout(control._especialSearchTimer);
                control._especialSearchTimer = null;
            }
            input.value = "";
            applySearch(control);
            input.focus();
        };
        updatePlaceholder(control);
        field.addEventListener("change", control._especialSearchOnFieldChange);
        input.addEventListener("input", control._especialSearchOnInput);
        control.addEventListener("click", control._especialSearchOnClick);
    }

    function init(root) {
        searchControls(root).forEach(initControl);
    }

    function owns(root, control) {
        return Boolean(
            root
            && control
            && (root === control || (root.contains && root.contains(control)))
        );
    }

    function destroy(root) {
        searchControls(root).forEach(function (control) {
            var field = control.querySelector("[data-especial-search-field]");
            var input = control.querySelector("[data-especial-search-input]");
            if (control._especialSearchTimer) {
                window.clearTimeout(control._especialSearchTimer);
                control._especialSearchTimer = null;
            }
            if (field && control._especialSearchOnFieldChange) {
                field.removeEventListener("change", control._especialSearchOnFieldChange);
            }
            if (input && control._especialSearchOnInput) {
                input.removeEventListener("input", control._especialSearchOnInput);
            }
            if (control._especialSearchOnClick) {
                control.removeEventListener("click", control._especialSearchOnClick);
            }
            if (owns(root, control)) {
                delete control.dataset.especialSearchReady;
                delete control._especialSearchOnFieldChange;
                delete control._especialSearchOnInput;
                delete control._especialSearchOnClick;
                delete control._especialSearchHasActiveTerm;
            }
        });
    }

    window.EspecialBusqueda = {
        init: init,
        destroy: destroy
    };
})();
