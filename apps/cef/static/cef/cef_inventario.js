(function () {
    "use strict";

    if (typeof window.initInventarioList === "function") {
        window.initInventarioList(document);
        return;
    }

    function initInventarioList(scope) {
        scope = scope || document;
        var root = scope.matches && scope.matches("[data-cef-table-root]")
            ? scope
            : scope.querySelector("[data-cef-table-root]");
        var table = root ? root.querySelector("[data-inventario-table]") : null;
        if (!root || !table || root.dataset.inventarioReady === "1") return;
        root.dataset.inventarioReady = "1";

        var items = Array.prototype.slice.call(
            table.querySelectorAll("[data-inventario-item]")
        ).map(function (row) {
            var id = row.dataset.inventarioItem;
            return {
                id: id,
                row: row,
                panel: root.querySelector('[data-inventario-panel="' + id + '"]'),
                toggle: row.querySelector("[data-inventario-panel-toggle]")
            };
        });
        var search = root.querySelector("[data-cef-table-search]");
        var size = root.querySelector("[data-cef-page-size]");
        var count = root.querySelector("[data-cef-table-count]");
        var pagination = root.querySelector("[data-cef-table-pagination]");
        var expandedId = "";
        var page = 1;

        items.forEach(function (item) {
            if (item.toggle && item.toggle.getAttribute("aria-expanded") === "true") {
                expandedId = item.id;
            }
        });

        function pageSize() {
            return parseInt(size ? size.value : "10", 10) || 10;
        }

        function filteredItems() {
            var term = search ? search.value.toLowerCase().trim() : "";
            return items.filter(function (item) {
                return !term || (item.row.dataset.inventarioSearch || "").indexOf(term) !== -1;
            });
        }

        function syncPanel(item, open) {
            if (item.panel) item.panel.hidden = !open;
            if (!item.toggle) return;
            item.toggle.setAttribute("aria-expanded", open ? "true" : "false");
            var icon = item.toggle.querySelector("i");
            if (icon) {
                icon.classList.toggle("fa-chevron-up", open);
                icon.classList.toggle("fa-chevron-down", !open);
            }
        }

        function render() {
            var visible = filteredItems();
            var perPage = pageSize();
            var pages = Math.max(1, Math.ceil(visible.length / perPage));
            page = Math.min(page, pages);
            var shown = visible.slice((page - 1) * perPage, page * perPage);
            var shownIds = shown.map(function (item) { return item.id; });

            items.forEach(function (item) {
                var showRow = shownIds.indexOf(item.id) !== -1;
                item.row.hidden = !showRow;
                syncPanel(item, showRow && expandedId === item.id);
            });

            if (count) count.textContent = visible.length + " registros";
            if (pagination) {
                if (pages <= 1) {
                    pagination.innerHTML = "";
                } else {
                    pagination.innerHTML =
                        '<button type="button" data-inventario-page-prev>Anterior</button>' +
                        '<span class="page-num">' + page + " / " + pages + "</span>" +
                        '<button type="button" data-inventario-page-next>Siguiente</button>';
                }
            }
        }

        if (expandedId) {
            var expandedIndex = filteredItems().findIndex(function (item) {
                return item.id === expandedId;
            });
            if (expandedIndex >= 0) {
                page = Math.floor(expandedIndex / pageSize()) + 1;
            }
        }

        root.addEventListener("click", function (event) {
            var toggle = event.target.closest("[data-inventario-panel-toggle]");
            if (toggle) {
                var id = toggle.dataset.inventarioPanelToggle;
                expandedId = expandedId === id && toggle.getAttribute("aria-expanded") === "true"
                    ? ""
                    : id;
                render();
                return;
            }

            if (!pagination) return;
            if (event.target.hasAttribute("data-inventario-page-prev")) {
                page = Math.max(1, page - 1);
                render();
            }
            if (event.target.hasAttribute("data-inventario-page-next")) {
                page += 1;
                render();
            }
        });

        if (search) {
            search.addEventListener("input", function () {
                page = 1;
                render();
            });
        }
        if (size) {
            size.addEventListener("change", function () {
                page = 1;
                render();
            });
        }

        render();

        var estadoForm = root.querySelector("[data-inventario-estado-form]");
        var estadoSelect = estadoForm ? estadoForm.querySelector('select[name="estado"]') : null;
        if (estadoSelect) {
            window.setTimeout(function () {
                if (window.CEFSelects) window.CEFSelects.focus(estadoSelect);
                else estadoSelect.focus();
            }, 0);
        }
    }

    window.initInventarioList = initInventarioList;
    initInventarioList(document);
})();
