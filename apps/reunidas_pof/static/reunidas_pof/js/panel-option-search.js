(function () {
    "use strict";

    function normalizeText(value) {
        var text = String(value || "").toLocaleLowerCase("es");

        return typeof text.normalize === "function"
            ? text.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
            : text;
    }

    function getOptions(panel, type) {
        var selector = type === "filters"
            ? ".pof-visual-filter-btn"
            : ".pof-visual-column-check";

        return Array.prototype.map.call(
            panel.querySelectorAll(selector),
            function (control) {
                var option = type === "filters"
                    ? control.closest(".pof-visual-filter-grid > div")
                    : control.closest(".pof-visual-column-option");
                var label;

                if (type === "filters") {
                    label =
                        control.getAttribute("data-filter-label") ||
                        control.textContent;
                } else {
                    label =
                        ((option && option.querySelector("span")) || control)
                            .textContent;
                }

                return {
                    element: option,
                    searchText: normalizeText(label)
                };
            }
        ).filter(function (option) {
            return !!option.element;
        });
    }

    function createSearch(panel, type) {
        var options = getOptions(panel, type);
        var label = type === "filters"
            ? "Buscar filtro"
            : "Buscar columna";
        var wrapper;
        var group;
        var icon;
        var input;
        var clearButton;
        var clearIcon;
        var emptyMessage;
        var panelHead;

        if (!options.length || panel.querySelector("[data-panel-option-search]")) {
            return;
        }

        wrapper = document.createElement("div");
        wrapper.className = "padron-panel-option-search mb-2";
        wrapper.setAttribute("data-panel-option-search", type);

        group = document.createElement("div");
        group.className = "input-group input-group-sm";

        icon = document.createElement("span");
        icon.className = "input-group-text";
        icon.innerHTML =
            '<svg viewBox="0 0 24 24" aria-hidden="true">' +
                '<circle cx="11" cy="11" r="7"></circle>' +
                '<path d="m20 20-4-4"></path>' +
            '</svg>';

        input = document.createElement("input");
        input.type = "search";
        input.className = "form-control";
        input.placeholder = label + "...";
        input.setAttribute("aria-label", label);
        input.setAttribute("autocomplete", "off");

        clearButton = document.createElement("button");
        clearButton.type = "button";
        clearButton.className =
            "btn btn-outline-secondary padron-panel-option-search-clear";
        clearButton.setAttribute("aria-label", "Limpiar búsqueda");
        clearButton.title = "Limpiar búsqueda";

        clearIcon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        clearIcon.setAttribute("viewBox", "0 0 24 24");
        clearIcon.setAttribute("aria-hidden", "true");
        clearIcon.innerHTML = '<path d="M6 6l12 12M18 6 6 18"></path>';
        clearButton.appendChild(clearIcon);

        emptyMessage = document.createElement("div");
        emptyMessage.className = "padron-panel-option-search-empty d-none";
        emptyMessage.textContent = "No hay opciones que coincidan.";

        function applySearch() {
            var query = normalizeText(input.value.trim());
            var visible = 0;

            options.forEach(function (option) {
                var matches =
                    !query ||
                    option.searchText.indexOf(query) !== -1;

                option.element.classList.toggle(
                    "padron-panel-option-hidden",
                    !matches
                );

                if (matches) {
                    visible += 1;
                }
            });

            emptyMessage.classList.toggle("d-none", visible !== 0);
            clearButton.disabled = !input.value;
        }

        input.addEventListener("input", applySearch);
        input.addEventListener("search", applySearch);
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
            }

            if (event.key === "Escape") {
                input.value = "";
                applySearch();
            }
        });

        clearButton.addEventListener("click", function () {
            input.value = "";
            applySearch();
            input.focus();
        });

        group.appendChild(icon);
        group.appendChild(input);
        group.appendChild(clearButton);
        wrapper.appendChild(group);
        wrapper.appendChild(emptyMessage);

        panelHead = panel.querySelector(".pof-visual-panel-head");
        if (panelHead) {
            panelHead.insertAdjacentElement("afterend", wrapper);
        } else {
            panel.insertBefore(wrapper, panel.firstChild);
        }

        applySearch();
    }

    function initialize() {
        var filtersPanel = document.getElementById("visualizacionPanelFiltros");
        var columnsPanel = document.getElementById("visualizacionPanelColumnas");

        if (filtersPanel) {
            createSearch(filtersPanel, "filters");
        }

        if (columnsPanel) {
            createSearch(columnsPanel, "columns");
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
}());
