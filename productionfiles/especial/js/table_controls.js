(function () {
    "use strict";

    var installedSearchClear = false;

    function normalizedTableText(value) {
        return String(value || "")
            .toLocaleLowerCase("es")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    function syncSearchClear(input) {
        if (!input || !input.closest) return;
        var wrap = input.closest(".cef-search-wrap");
        var clear = wrap ? wrap.querySelector("[data-cef-search-clear]") : null;
        if (clear) clear.classList.toggle("is-visible", Boolean(input.value));
    }

    function installSearchClearListeners() {
        if (installedSearchClear) return;
        installedSearchClear = true;
        document.addEventListener("input", function (event) {
            if (event.target && event.target.matches && event.target.matches(".cef-search-wrap input")) {
                syncSearchClear(event.target);
            }
        });
        document.addEventListener("click", function (event) {
            var target = event.target;
            var clear = target && target.closest ? target.closest("[data-cef-search-clear]") : null;
            if (!clear) return;
            var wrap = clear.closest(".cef-search-wrap");
            var input = wrap ? wrap.querySelector("input") : null;
            if (!input) return;
            input.value = "";
            input.focus();
            syncSearchClear(input);
            input.dispatchEvent(new Event("input", { bubbles: true }));
        });
    }

    function tableScope(table) {
        return table.closest(".gestionar-seccion-card, .cef-panel-body, .cef-panel, .cef-modal-body, .cef-modal, .cef-docente-modal") || document;
    }

    function initTable(table) {
        if (!table || table.dataset.cefTableReady === "1") return;
        var root = tableScope(table);
        var search = root.querySelector("[data-cef-table-search]");
        if (!search) return;

        var body = table.tBodies.length ? table.tBodies[0] : null;
        var rows = body
            ? Array.prototype.slice.call(body.rows).filter(function (row) {
                return !row.hasAttribute("data-cef-table-group-row")
                    && !row.hasAttribute("data-cef-table-empty-row");
            })
            : [];
        var groupRows = body
            ? Array.prototype.slice.call(body.rows).filter(function (row) {
                return row.hasAttribute("data-cef-table-group-row");
            })
            : [];
        var size = root.querySelector("[data-cef-page-size]");
        var count = root.querySelector("[data-cef-table-count]");
        var countSingular = count && count.getAttribute("data-cef-count-singular");
        var countPlural = count && count.getAttribute("data-cef-count-plural");
        var pagination = root.querySelector("[data-cef-table-pagination]");
        var page = 1;

        function filteredRows() {
            var term = normalizedTableText(search.value).trim();
            return rows.filter(function (row) {
                return !term || normalizedTableText(row.textContent).indexOf(term) !== -1;
            });
        }

        function renderPagination(pages) {
            if (!pagination) return;
            pagination.replaceChildren();
            if (pages <= 1) return;

            var previous = document.createElement("button");
            previous.type = "button";
            previous.dataset.pagePrev = "true";
            previous.textContent = "Anterior";
            previous.disabled = page === 1;

            var current = document.createElement("span");
            current.className = "page-num";
            current.textContent = page + " / " + pages;

            var next = document.createElement("button");
            next.type = "button";
            next.dataset.pageNext = "true";
            next.textContent = "Siguiente";
            next.disabled = page === pages;

            pagination.append(previous, current, next);
        }

        function render() {
            var visible = filteredRows();
            var pageSize = parseInt(size ? size.value : "10", 10) || 10;
            var pages = Math.max(1, Math.ceil(visible.length / pageSize));
            page = Math.min(page, pages);

            var pageRows = visible.slice((page - 1) * pageSize, page * pageSize);
            rows.forEach(function (row) { row.hidden = true; });
            groupRows.forEach(function (row) { row.hidden = true; });
            pageRows.forEach(function (row) {
                row.hidden = false;
            });
            var visibleGroups = Object.create(null);
            pageRows.forEach(function (row) {
                var group = row.getAttribute("data-cef-table-group-key");
                if (group) visibleGroups[group] = true;
            });
            groupRows.forEach(function (row) {
                var group = row.getAttribute("data-cef-table-group-key");
                row.hidden = !visibleGroups[group];
            });
            if (count && countSingular && countPlural) {
                count.textContent = visible.length + " " + (
                    visible.length === 1 ? countSingular : countPlural
                );
            }
            renderPagination(pages);
            table.classList.add("is-ready");
        }

        table.dataset.cefTableReady = "1";
        search.addEventListener("input", function () {
            page = 1;
            render();
        });
        if (size) {
            size.addEventListener("change", function () {
                page = 1;
                render();
            });
        }
        if (pagination) {
            pagination.addEventListener("click", function (event) {
                if (event.target.hasAttribute("data-page-prev")) page = Math.max(1, page - 1);
                if (event.target.hasAttribute("data-page-next")) page += 1;
                render();
            });
        }
        syncSearchClear(search);
        render();
    }

    function init(root) {
        installSearchClearListeners();
        var scope = root && root.querySelectorAll ? root : document;
        if (root && root.matches && root.matches("table[data-cef-table]")) initTable(root);
        scope.querySelectorAll("table[data-cef-table]").forEach(initTable);
        scope.querySelectorAll(".cef-search-wrap input").forEach(syncSearchClear);
    }

    window.EspecialTableControls = { init: init };
})();
