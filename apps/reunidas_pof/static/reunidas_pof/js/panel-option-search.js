(function () {
    "use strict";

    function normalizeText(value) {
        var text = String(value == null ? "" : value).toLocaleLowerCase("es");

        return typeof text.normalize === "function"
            ? text.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
            : text;
    }

    /**
     * Reutiliza reglas comunes de filtros POF entre paneles y dialogos.
     *
     * - Normaliza texto ignorando mayusculas, minusculas y diacriticos.
     * - Evita que Enter en el buscador interno dispare el formulario.
     * - Restaura todas las opciones con Escape y conserva el filtrado local sin requests.
     */
    function bindDialogOptionSearch(input, optionsRoot) {
        if (!input || !optionsRoot) {
            return;
        }

        function applySearch() {
            var query = normalizeText(input.value.trim());
            var visible = 0;

            optionsRoot.querySelectorAll(".pof-visual-dialog-option").forEach(function (option) {
                var label = option.querySelector("span");
                var text = normalizeText(label ? label.textContent : option.textContent);
                var matches = !query || text.indexOf(query) !== -1;
                option.hidden = !matches;
                if (matches) {
                    visible += 1;
                }
            });

            optionsRoot.querySelectorAll("[data-option-section]").forEach(function (section) {
                section.hidden = Boolean(
                    query
                    && !section.querySelector(".pof-visual-dialog-option:not([hidden])")
                );
            });

            return visible;
        }

        input.addEventListener("input", applySearch);
        input.addEventListener("search", applySearch);
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
            } else if (event.key === "Escape") {
                input.value = "";
                applySearch();
                event.preventDefault();
            }
        });

        applySearch();
    }

    var filterOperatorPresets = {
        text: [
            { value: "0", label: "parecido a" },
            { value: "1", label: "no parecido a" },
            { value: "2", label: "igual a" },
            { value: "7", label: "distinto de" }
        ],
        exact: [
            { value: "2", label: "igual a" },
            { value: "7", label: "distinto de" }
        ],
        numeric: [
            { value: "2", label: "igual a" },
            { value: "7", label: "distinto de" },
            { value: "3", label: "mayor a" },
            { value: "4", label: "mayor o igual a" },
            { value: "5", label: "menor a" },
            { value: "6", label: "menor o igual a" }
        ]
    };

    function normalizeFilterValues(values) {
        return (Array.isArray(values) ? values : [])
            .map(function (value) { return String(value == null ? "" : value).trim(); })
            .filter(Boolean)
            .sort();
    }

    function sameFilterCriterion(left, right) {
        return Boolean(left && right)
            && String(left.operator || "") === String(right.operator || "")
            && JSON.stringify(normalizeFilterValues(left.values))
                === JSON.stringify(normalizeFilterValues(right.values));
    }

    function firstOperatorForConfig(config) {
        var operators = filterOperatorPresets[config.operators] || filterOperatorPresets.text;
        return operators.length ? operators[0].value : "0";
    }

    function hasUsefulFilterCriterion(config, criterion) {
        var operators = config && filterOperatorPresets[config.operators]
            ? filterOperatorPresets[config.operators]
            : filterOperatorPresets.text;
        var selectedOperator = operators.find(function (operator) {
            return String(operator.value) === String(criterion && criterion.operator || "");
        });

        if (selectedOperator && selectedOperator.requiresValue === false) {
            return Boolean(String(criterion.operator || "").trim());
        }
        return normalizeFilterValues(criterion && criterion.values).length > 0;
    }

    /**
     * Captura solo los controles funcionales de un formulario de filtros.
     *
     * - Excluye por nombre los auxiliares como paginacion.
     * - Normaliza espacios, valores multiples y el orden de selecciones.
     * - Permite comparar el estado visible con el estado aplicado sin tocar la URL.
     */
    function getFilterFormState(form, fieldNames) {
        var names = Array.isArray(fieldNames) ? fieldNames : [];

        return names.map(function (name) {
            var values = [];

            Array.prototype.forEach.call(form ? form.elements : [], function (control) {
                var type = String(control.type || "").toLowerCase();

                if (control.name !== name || control.disabled) {
                    return;
                }
                if ((type === "checkbox" || type === "radio") && !control.checked) {
                    return;
                }
                if (control.tagName && control.tagName.toLowerCase() === "select" && control.multiple) {
                    Array.prototype.forEach.call(control.selectedOptions, function (option) {
                        values.push(option.value);
                    });
                    return;
                }
                values.push(control.value);
            });

            return [
                String(name),
                values.map(function (value) {
                    return String(value == null ? "" : value).trim();
                }).filter(Boolean).sort()
            ];
        });
    }

    function sameFilterFormState(left, right) {
        return JSON.stringify(left || []) === JSON.stringify(right || []);
    }

    /**
     * Mantiene Aplicar filtros deshabilitado mientras el formulario no difiera
     * del estado que la pagina recibio. El submit tambien se protege para que
     * Enter no genere una navegacion redundante cuando el boton esta disabled.
     */
    function bindFilterFormState(form) {
        if (!form || form.dataset.pofFilterStateBound === "1") {
            return;
        }

        var fieldNames = String(form.dataset.pofFilterFields || "")
            .split(",")
            .map(function (name) { return name.trim(); })
            .filter(Boolean);
        var applyButton = form.querySelector(".pof-filter-apply-btn");

        if (!fieldNames.length || !applyButton) {
            return;
        }

        var appliedState = getFilterFormState(form, fieldNames);
        var controls = Array.prototype.filter.call(form.elements, function (control) {
            return fieldNames.indexOf(control.name) !== -1;
        });

        function sync() {
            applyButton.disabled = sameFilterFormState(
                appliedState,
                getFilterFormState(form, fieldNames)
            );
        }

        controls.forEach(function (control) {
            control.addEventListener("input", sync);
            control.addEventListener("change", sync);
        });
        form.addEventListener("submit", function (event) {
            sync();
            if (applyButton.disabled) {
                event.preventDefault();
            }
        });
        form.dataset.pofFilterStateBound = "1";
        sync();
    }

    window.POFCommonFilterUI = window.POFCommonFilterUI || {};
    window.POFCommonFilterUI.normalizeText = normalizeText;
    window.POFCommonFilterUI.bindDialogOptionSearch = bindDialogOptionSearch;
    window.POFCommonFilterUI.filterOperatorPresets = filterOperatorPresets;
    window.POFCommonFilterUI.normalizeFilterValues = normalizeFilterValues;
    window.POFCommonFilterUI.sameFilterCriterion = sameFilterCriterion;
    window.POFCommonFilterUI.firstOperatorForConfig = firstOperatorForConfig;
    window.POFCommonFilterUI.hasUsefulFilterCriterion = hasUsefulFilterCriterion;
    window.POFCommonFilterUI.getFilterFormState = getFilterFormState;
    window.POFCommonFilterUI.sameFilterFormState = sameFilterFormState;
    window.POFCommonFilterUI.bindFilterFormState = bindFilterFormState;

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

    /**
     * Inicializa los buscadores locales declarados por cada panel POF.
     *
     * - Admite paneles identificados semanticamente sin depender de un ID de pantalla.
     * - Conserva los IDs historicos de Visualizador como fallback retrocompatible.
     * - Evita duplicar controles cuando un panel coincide con ambos mecanismos.
     */
    function initialize() {
        var filtersPanel = document.getElementById("visualizacionPanelFiltros");
        var columnsPanel = document.getElementById("visualizacionPanelColumnas");

        document.querySelectorAll("[data-panel-option-search-type]").forEach(function (panel) {
            var type = panel.getAttribute("data-panel-option-search-type");
            if (type === "filters" || type === "columns") {
                createSearch(panel, type);
            }
        });

        if (filtersPanel) {
            createSearch(filtersPanel, "filters");
        }

        if (columnsPanel) {
            createSearch(columnsPanel, "columns");
        }

        document.querySelectorAll("[data-pof-filter-form]").forEach(bindFilterFormState);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
}());
