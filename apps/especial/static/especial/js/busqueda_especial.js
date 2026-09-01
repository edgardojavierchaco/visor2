(function () {
    "use strict";

    var SERVER_DEBOUNCE_MS = 180;
    var CLIENT_PAGE_SIZE = 10;

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

    function readTerm(control) {
        var input = control && control.querySelector("[data-especial-search-input]");
        return input ? String(input.value || "").trim() : "";
    }

    function normalizeSearchValue(value) {
        return String(value || "")
            .trim()
            .toLocaleLowerCase("es")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/(\d)[,./-](?=\d)/g, "$1")
            .replace(/[\s,./-]+/g, " ")
            .trim();
    }

    function searchTokens(value) {
        var normalized = normalizeSearchValue(value);
        return normalized ? normalized.split(" ").filter(Boolean) : [];
    }

    function resultsElement(control) {
        return control && control.querySelector("[data-especial-search-results]");
    }

    function searchMode(control) {
        var results = resultsElement(control);
        return results ? (results.getAttribute("data-especial-search-mode") || "server") : "server";
    }

    function syncAppliedState(control) {
        var searchWrap = control && control.querySelector(".cef-search-wrap");
        if (!searchWrap) return;
        var applied = Boolean(readTerm(control));
        searchWrap.classList.toggle("is-search-applied", applied);
        if (applied) searchWrap.setAttribute("data-especial-search-active", "true");
        else searchWrap.removeAttribute("data-especial-search-active");
    }

    function readConfig(control) {
        var input = control.querySelector("[data-especial-search-input]");
        var resetParams = (control.getAttribute("data-especial-search-reset-params") || "")
            .split(",")
            .map(function (param) { return param.trim(); })
            .filter(Boolean);
        return {
            termParam: control.getAttribute("data-especial-search-term-param") || (input && input.name) || "q",
            viewParam: control.getAttribute("data-especial-search-view-param") || "",
            view: control.getAttribute("data-especial-search-view") || "",
            pageParam: control.getAttribute("data-especial-search-page-param") || "page",
            resultsSelector: control.getAttribute("data-especial-search-results-selector") || "",
            resetParams: resetParams
        };
    }

    function buildSearchUrl(control) {
        var config = readConfig(control);
        var url = new URL(window.location.href);
        var term = readTerm(control);

        if (config.viewParam && config.view) {
            url.searchParams.set(config.viewParam, config.view);
        }
        if (config.pageParam) url.searchParams.set(config.pageParam, "1");
        config.resetParams.forEach(function (param) {
            url.searchParams.delete(param);
        });
        if (term) {
            url.searchParams.set(config.termParam, term);
        } else {
            url.searchParams.delete(config.termParam);
        }
        return url;
    }

    function buildClientSearchUrl(control) {
        var config = readConfig(control);
        var url = new URL(window.location.href);
        var term = readTerm(control);

        if (config.viewParam && config.view) {
            url.searchParams.set(config.viewParam, config.view);
        }
        if (term) {
            url.searchParams.set(config.termParam, term);
        } else {
            url.searchParams.delete(config.termParam);
        }
        if (config.pageParam) url.searchParams.delete(config.pageParam);
        config.resetParams.forEach(function (param) {
            url.searchParams.delete(param);
        });
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
                    config.termParam,
                    url.searchParams.get(config.termParam) || ""
                );
            } else {
                linkUrl.searchParams.delete(config.termParam);
            }
            if (config.pageParam) {
                if (link.dataset.especialSubview === "historial") {
                    linkUrl.searchParams.set(config.pageParam, "1");
                } else {
                    linkUrl.searchParams.delete(config.pageParam);
                }
            }
            config.resetParams.forEach(function (param) {
                linkUrl.searchParams.delete(param);
            });
            link.href = linkUrl.toString();
        });
    }

    function syncClientUrl(control) {
        var config = readConfig(control);
        var url = buildClientSearchUrl(control);
        syncStateLinks(control, url, config);
        if (!isCurrentUrl(url)) {
            window.history.replaceState(window.history.state, "", url.toString());
        }
        return url;
    }

    function clientSearchRows(control) {
        var results = resultsElement(control);
        return results
            ? Array.prototype.slice.call(results.querySelectorAll("[data-especial-search-row]"))
            : [];
    }

    function matchesClientSearch(row, tokens) {
        if (!tokens.length) return true;
        var haystack = normalizeSearchValue(row.getAttribute("data-especial-search-text"));
        return tokens.every(function (token) {
            return haystack.indexOf(token) !== -1;
        });
    }

    function renderClientPagination(pagination, page, pages) {
        if (!pagination) return;
        pagination.replaceChildren();
        if (pages <= 1) return;

        var previous = document.createElement("button");
        previous.className = "btn btn-outline-primary btn-sm";
        previous.type = "button";
        previous.textContent = "Anterior";
        previous.disabled = page === 1;
        previous.setAttribute("data-especial-client-page", String(page - 1));

        var current = document.createElement("span");
        current.className = "page-num";
        current.textContent = "Página " + page + " de " + pages;

        var next = document.createElement("button");
        next.className = "btn btn-outline-primary btn-sm";
        next.type = "button";
        next.textContent = "Siguiente";
        next.disabled = page === pages;
        next.setAttribute("data-especial-client-page", String(page + 1));

        pagination.append(previous, current, next);
    }

    function renderClientSearch(control) {
        if (searchMode(control) !== "client") return;
        var results = resultsElement(control);
        if (!results) return;

        var rows = clientSearchRows(control);
        var tokens = searchTokens(readTerm(control));
        var filteredRows = rows.filter(function (row) {
            return matchesClientSearch(row, tokens);
        });
        var pages = Math.max(1, Math.ceil(filteredRows.length / CLIENT_PAGE_SIZE));
        var page = Math.min(
            Math.max(parseInt(control._especialSearchClientPage, 10) || 1, 1),
            pages
        );
        control._especialSearchClientPage = page;

        var pageRows = filteredRows.slice(
            (page - 1) * CLIENT_PAGE_SIZE,
            page * CLIENT_PAGE_SIZE
        );
        var pageRowSet = new Set(pageRows);
        rows.forEach(function (row) {
            row.hidden = !pageRowSet.has(row);
        });

        var table = results.querySelector("table[data-especial-search-table]");
        var tableWrap = table && table.closest(".cef-table-wrap");
        if (tableWrap) tableWrap.hidden = filteredRows.length === 0;
        var emptyState = results.querySelector("[data-especial-client-empty]");
        if (emptyState) emptyState.hidden = filteredRows.length !== 0;

        var count = results.querySelector("[data-cef-table-count]");
        if (count) count.textContent = filteredRows.length + " alumnos";
        renderClientPagination(
            results.querySelector("[data-especial-client-pagination]"),
            page,
            pages
        );
    }

    function applyClientSearch(control) {
        syncAppliedState(control);
        control._especialSearchHasActiveTerm = Boolean(readTerm(control));
        syncClientUrl(control);
        renderClientSearch(control);
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
        syncAppliedState(control);
        control._especialSearchHasActiveTerm = Boolean(readTerm(control));
        navigate(control, buildSearchUrl(control));
    }

    function schedule(control) {
        if (searchMode(control) === "client") return;
        if (control._especialSearchTimer) {
            window.clearTimeout(control._especialSearchTimer);
            control._especialSearchTimer = null;
        }
        var term = readTerm(control);
        if (!term && !control._especialSearchHasActiveTerm) return;
        control._especialSearchTimer = window.setTimeout(function () {
            control._especialSearchTimer = null;
            applySearch(control);
        }, SERVER_DEBOUNCE_MS);
    }

    function initControl(control) {
        if (!control || control.dataset.especialSearchReady === "1") return;
        var input = control.querySelector("[data-especial-search-input]");
        if (!input) return;

        control.dataset.especialSearchReady = "1";
        control._especialSearchClientPage = 1;
        control._especialSearchHasActiveTerm = Boolean(readTerm(control));
        control._especialSearchOnInput = function () {
            syncAppliedState(control);
            control._especialSearchClientPage = 1;
            if (searchMode(control) === "client") applyClientSearch(control);
            else schedule(control);
        };
        control._especialSearchOnPaginationClick = function (event) {
            var pageButton = event.target.closest("[data-especial-client-page]");
            if (!pageButton || !control.contains(pageButton)) return;
            event.preventDefault();
            if (searchMode(control) !== "client" || pageButton.disabled) return;
            var page = parseInt(pageButton.getAttribute("data-especial-client-page"), 10);
            if (!page || page < 1) return;
            control._especialSearchClientPage = page;
            renderClientSearch(control);
        };
        syncAppliedState(control);
        input.addEventListener("input", control._especialSearchOnInput);
        control.addEventListener("click", control._especialSearchOnPaginationClick);
        if (searchMode(control) === "client") applyClientSearch(control);
    }

    function init(root) {
        searchControls(root).forEach(initControl);
    }

    function refresh(root) {
        searchControls(root).forEach(function (control) {
            if (control.dataset.especialSearchReady !== "1") {
                initControl(control);
                return;
            }
            syncAppliedState(control);
            if (searchMode(control) === "client") {
                control._especialSearchClientPage = 1;
                applyClientSearch(control);
            }
        });
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
            var input = control.querySelector("[data-especial-search-input]");
            if (control._especialSearchTimer) {
                window.clearTimeout(control._especialSearchTimer);
                control._especialSearchTimer = null;
            }
            if (input && control._especialSearchOnInput) {
                input.removeEventListener("input", control._especialSearchOnInput);
            }
            if (control._especialSearchOnPaginationClick) {
                control.removeEventListener("click", control._especialSearchOnPaginationClick);
            }
            if (owns(root, control)) {
                delete control.dataset.especialSearchReady;
                delete control._especialSearchOnInput;
                delete control._especialSearchOnPaginationClick;
                delete control._especialSearchHasActiveTerm;
                delete control._especialSearchClientPage;
            }
        });
    }

    window.EspecialBusqueda = {
        init: init,
        destroy: destroy,
        refresh: refresh
    };
})();
